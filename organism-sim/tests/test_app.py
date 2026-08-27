import sys
from types import SimpleNamespace

from organism_sim.app import App, main
from organism_sim.config import BehaviorModel, Scheduler


def scheduler(ticks_per_second: float) -> App:
    app = object.__new__(App)
    app.accumulator = 0.0
    app.config = SimpleNamespace(ticks_per_second=ticks_per_second)
    return app


def test_tick_scheduler_never_replays_more_than_one_tick_of_debt() -> None:
    app = scheduler(20.0)

    assert app._tick_due(1.0)
    assert app.accumulator == 1.0

    # Even repeated one-second stalls remain capped. The run loop can therefore
    # return to pygame event handling after every individual simulation tick.
    assert app._tick_due(1.0)
    assert app.accumulator == 1.0


def test_tick_scheduler_retains_fractional_time_when_engine_is_on_budget() -> None:
    app = scheduler(20.0)

    assert not app._tick_due(0.02)
    assert app._tick_due(0.03)
    assert app.accumulator == 0.0


def test_gui_cli_auto_prefers_native_kernel(monkeypatch) -> None:
    import organism_sim.app as app_module
    import organism_sim.native_app as native_module
    from organism_sim import rust_kernel

    called: list[str] = []

    def fake(name: str) -> SimpleNamespace:
        return SimpleNamespace(run=lambda: called.append(name))

    monkeypatch.setattr(
        sys,
        "argv",
        ["organism-sim", "--fresh", "--no-save-settings"],
    )
    monkeypatch.setattr(rust_kernel, "extension_available", lambda: True)
    monkeypatch.setattr(native_module, "NativeApp", lambda *args, **kwargs: fake("rust"))
    monkeypatch.setattr(app_module, "App", lambda *args, **kwargs: fake("python"))

    main()

    assert called == ["rust"]


def test_gui_cli_accepts_parallel_scheduler_flags(monkeypatch) -> None:
    import organism_sim.native_app as native_module
    from organism_sim import rust_kernel

    received = []
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "organism-sim",
            "--engine",
            "rust",
            "--fresh",
            "--no-save-settings",
            "--behavior-model",
            "recurrent_intent_v2",
            "--scheduler",
            "parallel-v3",
            "--parallel-workers",
            "4",
        ],
    )
    monkeypatch.setattr(rust_kernel, "extension_available", lambda: True)
    monkeypatch.setattr(
        native_module,
        "NativeApp",
        lambda config, **kwargs: SimpleNamespace(
            run=lambda: received.append(config)
        ),
    )

    main()

    assert len(received) == 1
    assert received[0].behavior_model == BehaviorModel.RECURRENT_INTENT_V2
    assert received[0].scheduler == Scheduler.PARALLEL_V3
    assert received[0].parallel_workers == 4


def test_gui_cli_can_force_python_kernel(monkeypatch) -> None:
    import organism_sim.app as app_module

    called: list[str] = []
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "organism-sim",
            "--engine",
            "python",
            "--fresh",
            "--no-save-settings",
        ],
    )
    monkeypatch.setattr(
        app_module,
        "App",
        lambda *args, **kwargs: SimpleNamespace(
            run=lambda: called.append("python")
        ),
    )

    main()

    assert called == ["python"]
