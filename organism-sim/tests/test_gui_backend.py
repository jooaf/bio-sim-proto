from __future__ import annotations

from time import monotonic, sleep

from organism_sim.config import SimulationConfig
from organism_sim.gui_backend import RustGuiWorker


class FakeSimulation:
    def __init__(self, _config: SimulationConfig) -> None:
        self._tick = 0
        self.updates: list[dict[str, object]] = []
        self.snapshot_requests: list[
            tuple[tuple[int, int, int, int], bool, bool, int | None]
        ] = []

    @property
    def tick(self) -> int:
        return self._tick

    def step(self, ticks: int = 1) -> None:
        sleep(0.001)
        self._tick += ticks

    def gui_snapshot(
        self,
        bounds: tuple[int, int, int, int],
        *,
        include_heat: bool = False,
        include_food: bool = True,
        selected_id: int | None = None,
    ) -> dict[str, object]:
        self.snapshot_requests.append((bounds, include_heat, include_food, selected_id))
        return {"tick": self._tick, "bounds": bounds}

    def update_config(self, **changes: object) -> None:
        self.updates.append(changes)

    def audit(self) -> dict[str, object]:
        return {"elements_ok": True, "energy_ok": True}


def wait_until(predicate, timeout: float = 2.0) -> None:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if predicate():
            return
        sleep(0.005)
    raise AssertionError("condition did not become true")


def test_worker_pause_step_and_latest_snapshot() -> None:
    simulations: list[FakeSimulation] = []

    def factory(config: SimulationConfig) -> FakeSimulation:
        simulation = FakeSimulation(config)
        simulations.append(simulation)
        return simulation

    worker = RustGuiWorker(
        SimulationConfig(founder_count=10),
        snapshot_hz=100,
        start_paused=True,
        simulation_factory=factory,
    )
    worker.start()
    try:
        initial = worker.poll_snapshot()
        assert initial is not None
        initial_sequence, initial_snapshot = initial
        assert initial_snapshot["tick"] == 0

        worker.step_once()
        wait_until(lambda: worker.status.tick == 1)
        stepped = worker.poll_snapshot(initial_sequence)
        assert stepped is not None
        assert stepped[1]["tick"] == 1

        worker.set_paused(False)
        wait_until(lambda: worker.status.tick >= 5)
        worker.set_paused(True)
        wait_until(lambda: worker.status.paused)
        paused_tick = worker.status.tick
        sleep(0.05)
        assert worker.status.tick == paused_tick
    finally:
        worker.stop()

    assert worker.status.final_audit == {"elements_ok": True, "energy_ok": True}
    assert simulations


def test_worker_overwrites_viewport_and_config_updates() -> None:
    simulations: list[FakeSimulation] = []

    def factory(config: SimulationConfig) -> FakeSimulation:
        simulation = FakeSimulation(config)
        simulations.append(simulation)
        return simulation

    worker = RustGuiWorker(
        SimulationConfig(founder_count=10),
        snapshot_hz=100,
        start_paused=True,
        simulation_factory=factory,
    )
    worker.start()
    try:
        previous = worker.status.snapshot_sequence
        worker.set_viewport(
            (-10, -20, 30, 40),
            include_heat=True,
            include_food=False,
            selected_id=7,
        )
        worker.update_config(heat_diffusion=0.12, mutation_multiplier=2.0)
        wait_until(lambda: worker.status.snapshot_sequence > previous)
        wait_until(lambda: bool(simulations[0].updates))

        latest = worker.poll_snapshot(previous)
        assert latest is not None
        assert latest[1]["bounds"] == (-10, -20, 30, 40)
        assert simulations[0].snapshot_requests[-1] == (
            (-10, -20, 30, 40),
            True,
            False,
            7,
        )
        expected_update = {
            "heat_diffusion": 0.12,
            "mutation_multiplier": 2.0,
        }
        assert simulations[0].updates[-1] == expected_update
        applied = worker.drain_applied_config_updates()
        assert len(applied) == 1
        assert applied[0].tick == 0
        assert applied[0].changes == expected_update
        assert worker.drain_applied_config_updates() == []
    finally:
        worker.stop()


def test_latest_snapshot_retains_unpolled_season_events() -> None:
    class SeasonalFake(FakeSimulation):
        def gui_snapshot(self, bounds, **kwargs):
            snapshot = super().gui_snapshot(bounds, **kwargs)
            event_index = len(self.snapshot_requests) - 1
            snapshot["season"] = {
                "enabled": True,
                "events": [{"index": event_index}],
            }
            return snapshot

    config = SimulationConfig(founder_count=10)
    simulation = SeasonalFake(config)
    worker = RustGuiWorker(config, start_paused=True, simulation_factory=SeasonalFake)
    request = worker._viewport

    worker._publish(simulation, request)
    worker._publish(simulation, request)
    latest = worker.poll_snapshot()
    assert latest is not None
    assert [event["index"] for event in latest[1]["season"]["events"]] == [0, 1]

    worker._publish(simulation, request)
    next_snapshot = worker.poll_snapshot(latest[0])
    assert next_snapshot is not None
    assert [event["index"] for event in next_snapshot[1]["season"]["events"]] == [2]


def test_worker_rejects_invalid_rates_and_viewports() -> None:
    config = SimulationConfig(founder_count=10)
    try:
        RustGuiWorker(config, snapshot_hz=0)
    except ValueError as error:
        assert "snapshot_hz" in str(error)
    else:
        raise AssertionError("zero snapshot rate should fail")

    worker = RustGuiWorker(config, start_paused=True, simulation_factory=FakeSimulation)
    try:
        worker.set_target_ticks_per_second(0)
    except ValueError as error:
        assert "positive" in str(error)
    else:
        raise AssertionError("zero tick rate should fail")

    try:
        worker.set_viewport(
            (5, 5, 5, 10),
            include_heat=False,
            include_food=True,
            selected_id=None,
        )
    except ValueError as error:
        assert "ordered" in str(error)
    else:
        raise AssertionError("empty viewport should fail")
