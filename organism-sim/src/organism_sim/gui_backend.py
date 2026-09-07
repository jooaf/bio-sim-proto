from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass, replace
from threading import Event, Lock, Thread
from time import monotonic, perf_counter
from typing import Any, Protocol

from .config import SimulationConfig
from .rust_kernel import RustKernelSimulation

Bounds = tuple[int, int, int, int]
Snapshot = dict[str, Any]


class NativeSimulation(Protocol):
    @property
    def tick(self) -> int: ...

    def step(self, ticks: int = 1) -> None: ...

    def gui_snapshot(
        self,
        bounds: Bounds,
        *,
        include_heat: bool = False,
        include_food: bool = True,
        selected_id: int | None = None,
    ) -> Snapshot: ...

    def update_config(self, **changes: object) -> None: ...

    def audit(self) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class ViewportRequest:
    bounds: Bounds
    include_heat: bool = False
    include_food: bool = True
    selected_id: int | None = None
    revision: int = 0


@dataclass(frozen=True, slots=True)
class AppliedConfigUpdate:
    tick: int
    changes: dict[str, object]


@dataclass(frozen=True, slots=True)
class WorkerStatus:
    running: bool = False
    paused: bool = False
    tick: int = 0
    ticks_per_second: float = 0.0
    target_ticks_per_second: float | None = None
    batch_ticks: int = 1
    snapshot_sequence: int = 0
    error: str = ""
    final_audit: dict[str, object] | None = None


class RustGuiWorker:
    """Own a Rust kernel in one worker and publish only its newest snapshot.

    No simulation object escapes the worker thread. Control state is latest-only
    rather than queued, so mouse movement and slider drags cannot create an
    unbounded backlog. Rust releases the GIL while stepping.
    """

    def __init__(
        self,
        config: SimulationConfig,
        *,
        snapshot_hz: float = 10.0,
        target_ticks_per_second: float | None = None,
        start_paused: bool = False,
        simulation_factory: Callable[
            [SimulationConfig], NativeSimulation
        ] = RustKernelSimulation,
    ) -> None:
        if snapshot_hz <= 0:
            raise ValueError("snapshot_hz must be positive")
        if target_ticks_per_second is not None and target_ticks_per_second <= 0:
            raise ValueError("target_ticks_per_second must be positive or None")
        self._config = config.evolved()
        self._snapshot_period = 1.0 / snapshot_hz
        self._simulation_factory = simulation_factory
        self._stop = Event()
        self._ready = Event()
        self._control_lock = Lock()
        self._snapshot_lock = Lock()
        self._status_lock = Lock()
        self._paused = start_paused
        self._step_requests = 0
        self._target_ticks_per_second = target_ticks_per_second
        self._viewport = ViewportRequest(
            bounds=(0, 0, config.width, config.height),
            revision=1,
        )
        self._config_updates: dict[str, object] = {}
        self._applied_config_updates: list[AppliedConfigUpdate] = []
        self._latest_snapshot: Snapshot | None = None
        self._pending_season_events: list[dict[str, object]] = []
        self._snapshot_sequence = 0
        self._status = WorkerStatus(
            paused=start_paused,
            target_ticks_per_second=target_ticks_per_second,
        )
        self._thread = Thread(
            target=self._run, name="organism-sim-rust-gui", daemon=True
        )

    def start(self, timeout: float = 30.0) -> None:
        if self._thread.is_alive():
            return
        self._thread.start()
        if not self._ready.wait(timeout):
            raise TimeoutError("native GUI worker did not initialize")
        status = self.status
        if status.error:
            raise RuntimeError(status.error)

    def stop(self, timeout: float = 30.0) -> None:
        """Signal shutdown and wait for the worker to finish its final work.

        Once the stop flag is set the worker exits the loop after at most one
        step batch, one snapshot, and one conservation audit. That bounded
        tail can still exceed a short fixed budget on heavy worlds, and the
        thread is a daemon that exits with the process, so a slow tail warns
        rather than crashing a clean app exit.
        """
        self._stop.set()
        started = monotonic()
        while self._thread.is_alive():
            self._thread.join(0.5)
            if self._thread.is_alive() and monotonic() - started >= timeout:
                print(
                    "warning: native GUI worker is finishing its final audit; "
                    f"releasing after {timeout:.0f}s (it will exit with the process)",
                    file=sys.stderr,
                )
                break

    def set_paused(self, paused: bool) -> None:
        with self._control_lock:
            self._paused = paused

    def step_once(self) -> None:
        with self._control_lock:
            self._step_requests += 1

    def set_target_ticks_per_second(self, target: float | None) -> None:
        if target is not None and target <= 0:
            raise ValueError("target must be positive or None")
        with self._control_lock:
            self._target_ticks_per_second = target

    def set_viewport(
        self,
        bounds: Bounds,
        *,
        include_heat: bool,
        include_food: bool,
        selected_id: int | None,
    ) -> None:
        x0, y0, x1, y1 = bounds
        if x1 <= x0 or y1 <= y0:
            raise ValueError("viewport bounds must be ordered")
        with self._control_lock:
            self._viewport = ViewportRequest(
                bounds=bounds,
                include_heat=include_heat,
                include_food=include_food,
                selected_id=selected_id,
                revision=self._viewport.revision + 1,
            )

    def update_config(self, **changes: object) -> None:
        with self._control_lock:
            self._config_updates.update(changes)

    def poll_snapshot(self, after_sequence: int = 0) -> tuple[int, Snapshot] | None:
        with self._snapshot_lock:
            if (
                self._latest_snapshot is None
                or self._snapshot_sequence <= after_sequence
            ):
                return None
            result = self._snapshot_sequence, self._latest_snapshot
            self._pending_season_events = []
            return result

    def drain_applied_config_updates(self) -> list[AppliedConfigUpdate]:
        """Return live updates after the worker has applied them to the kernel."""

        with self._control_lock:
            updates = self._applied_config_updates
            self._applied_config_updates = []
            return updates

    @property
    def status(self) -> WorkerStatus:
        with self._status_lock:
            return self._status

    def _read_control(
        self,
    ) -> tuple[bool, bool, float | None, ViewportRequest, dict[str, object]]:
        with self._control_lock:
            paused = self._paused
            step_once = self._step_requests > 0
            if step_once:
                self._step_requests -= 1
            updates = self._config_updates
            self._config_updates = {}
            return (
                paused,
                step_once,
                self._target_ticks_per_second,
                self._viewport,
                updates,
            )

    def _record_applied_config_update(
        self, tick: int, changes: dict[str, object]
    ) -> None:
        with self._control_lock:
            self._applied_config_updates.append(
                AppliedConfigUpdate(tick=tick, changes=dict(changes))
            )

    def _publish(self, simulation: NativeSimulation, request: ViewportRequest) -> None:
        snapshot = simulation.gui_snapshot(
            request.bounds,
            include_heat=request.include_heat,
            include_food=request.include_food,
            selected_id=request.selected_id,
        )
        with self._snapshot_lock:
            season = snapshot.get("season")
            if season is not None:
                self._pending_season_events.extend(season.get("events", []))
                season["events"] = list(self._pending_season_events)
            self._snapshot_sequence += 1
            self._latest_snapshot = snapshot
            sequence = self._snapshot_sequence
        with self._status_lock:
            self._status = replace(
                self._status,
                tick=simulation.tick,
                snapshot_sequence=sequence,
            )

    def _run(self) -> None:
        simulation: NativeSimulation | None = None
        try:
            simulation = self._simulation_factory(self._config)
            _, _, target, viewport, updates = self._read_control()
            if updates:
                simulation.update_config(**updates)
                self._record_applied_config_update(simulation.tick, updates)
            self._publish(simulation, viewport)
            with self._status_lock:
                self._status = replace(self._status, running=True, tick=simulation.tick)
            self._ready.set()

            batch_ticks = 8
            last_snapshot_at = perf_counter()
            published_revision = viewport.revision
            rate_started = perf_counter()
            rate_tick = simulation.tick
            measured_tps = 0.0

            while not self._stop.is_set():
                paused, step_once, target, viewport, updates = self._read_control()
                if updates:
                    simulation.update_config(**updates)
                    self._record_applied_config_update(simulation.tick, updates)

                stepped = False
                if not paused or step_once:
                    ticks = 1 if paused else batch_ticks
                    step_started = perf_counter()
                    simulation.step(ticks)
                    step_seconds = max(perf_counter() - step_started, 1e-9)
                    stepped = True

                    seconds_per_tick = step_seconds / ticks
                    adaptive = max(1, min(64, round(0.04 / seconds_per_tick)))
                    if target is not None:
                        adaptive = min(adaptive, max(1, round(target * 0.04)))
                        target_seconds = ticks / target
                        self._stop.wait(max(0.0, target_seconds - step_seconds))
                    batch_ticks = adaptive

                now = perf_counter()
                publish_due = (
                    now - last_snapshot_at >= self._snapshot_period
                    or viewport.revision != published_revision
                    or (paused and step_once)
                )
                if publish_due:
                    self._publish(simulation, viewport)
                    last_snapshot_at = perf_counter()
                    published_revision = viewport.revision

                rate_seconds = now - rate_started
                if rate_seconds >= 0.5:
                    measured_tps = (simulation.tick - rate_tick) / rate_seconds
                    rate_started = now
                    rate_tick = simulation.tick

                with self._status_lock:
                    self._status = replace(
                        self._status,
                        paused=paused,
                        tick=simulation.tick,
                        ticks_per_second=measured_tps,
                        target_ticks_per_second=target,
                        batch_ticks=batch_ticks,
                    )

                if paused and not step_once:
                    self._stop.wait(0.01)
                elif not stepped:
                    self._stop.wait(0.001)
        except Exception as error:  # noqa: BLE001 - worker surfaces failures to pygame
            with self._status_lock:
                self._status = replace(self._status, running=False, error=str(error))
            self._ready.set()
        finally:
            final_audit = None
            if simulation is not None:
                try:
                    final_audit = simulation.audit()
                except Exception:  # noqa: BLE001 - preserve original worker failure
                    final_audit = None
            # Must run unconditionally so callers observe a finished worker
            # even when the final audit raises.
            with self._status_lock:
                self._status = replace(
                    self._status,
                    running=False,
                    final_audit=final_audit,
                )
            self._ready.set()


__all__ = [
    "AppliedConfigUpdate",
    "RustGuiWorker",
    "ViewportRequest",
    "WorkerStatus",
]
