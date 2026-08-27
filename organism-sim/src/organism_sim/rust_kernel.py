from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from types import ModuleType

from .config import Scheduler, SimulationConfig


class RustKernelUnavailableError(RuntimeError):
    """Raised when the compiled Rust extension is not installed."""


def _module() -> ModuleType:
    try:
        return import_module("organism_sim_kernel")
    except ImportError as exc:  # pragma: no cover - exercised in user envs
        raise RustKernelUnavailableError(
            "organism_sim_kernel is not installed; run "
            "`uv run maturin develop --release --manifest-path rust/Cargo.toml`"
        ) from exc


def extension_available() -> bool:
    try:
        _module()
    except RustKernelUnavailableError:
        return False
    return True


def config_sha256(config: SimulationConfig) -> str:
    payload = json.dumps(asdict(config), separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def scheduler_metadata(config: SimulationConfig) -> dict[str, object]:
    """Version the selected simulation law independently of kernel builds."""

    parallel = config.scheduler == Scheduler.PARALLEL_V3
    return {
        "scheduler": config.scheduler.value,
        "scheduler_schema_version": 3 if parallel else 2,
        "configured_workers": config.parallel_workers,
        "partition_strategy": (
            "rayon-maintenance-intents-components-v2"
            if parallel
            else "serial-shuffled-v2"
        ),
        "rng_derivation_version": 2 if parallel else 0,
        "conflict_resolver_version": 2 if parallel else 0,
    }


@lru_cache(maxsize=1)
def rust_build_metadata() -> dict[str, str]:
    """Identify the compiled kernel that actually executes simulation dynamics."""

    module = _module()
    binary_path = Path(module.__file__).resolve()
    digest = hashlib.sha256()
    with binary_path.open("rb") as binary:
        while chunk := binary.read(1024 * 1024):
            digest.update(chunk)
    return {
        "kernel_version": str(getattr(module, "__version__", "unknown")),
        "kernel_binary_sha256": digest.hexdigest(),
    }


class RustKernelSimulation:
    """Thin Python loader around the coarse-step Rust simulation kernel."""

    def __init__(self, config: SimulationConfig | None = None):
        self.config = config or SimulationConfig()
        self.config.validate()
        self._kernel = _module().KernelSimulation(asdict(self.config))

    def step(self, ticks: int = 1) -> None:
        self._kernel.step(ticks)

    def step_one(self) -> None:
        self._kernel.step_one()

    def profile_step(self, ticks: int = 1) -> dict[str, object]:
        """Advance with native phase timers enabled."""
        return self._kernel.profile_step(ticks)

    def snapshot(self) -> dict[str, object]:
        return self._kernel.snapshot()

    def gui_snapshot(
        self,
        bounds: tuple[int, int, int, int],
        *,
        include_heat: bool = False,
        include_food: bool = True,
        selected_id: int | None = None,
    ) -> dict[str, object]:
        """Return a bounded immutable snapshot optimized for pygame."""
        return self._kernel.gui_snapshot(
            bounds,
            include_heat=include_heat,
            include_food=include_food,
            selected_id=selected_id,
        )

    def update_config(self, **changes: object) -> None:
        """Apply validated runtime-safe configuration changes."""
        self._kernel.update_config(changes)

    def stats_dict(self) -> dict[str, object]:
        return self._kernel.stats_dict()

    def season_state(self, after_event: int = 0) -> dict[str, object]:
        """Return active season state plus events after the supplied cursor."""
        return self._kernel.season_state(after_event)

    def compressibility_metrics(self) -> dict[str, object]:
        """Return observation-only event/cohort compression diagnostics."""
        return self._kernel.compressibility_metrics()

    def audit(self) -> dict[str, object]:
        return self._kernel.audit()

    def digest(self) -> int:
        return int(self._kernel.digest())

    @property
    def tick(self) -> int:
        return int(self._kernel.tick)

    @property
    def population(self) -> int:
        return int(self._kernel.population)

    @property
    def species_count(self) -> int:
        return int(self._kernel.species_count)


__all__ = [
    "RustKernelSimulation",
    "RustKernelUnavailableError",
    "config_sha256",
    "extension_available",
    "rust_build_metadata",
    "scheduler_metadata",
]
