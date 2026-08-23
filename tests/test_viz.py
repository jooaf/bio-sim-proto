from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pygame
from pytest import MonkeyPatch

from soup.config import Config
from soup.simulation import Simulation
from soup.viz.app import SoupViewer, dominant_opcode_color, hash_color, run_visual


def test_visual_colours_are_stable() -> None:
    assert hash_color("001122" + "00" * 13) == hash_color("001122" + "ff" * 13)
    tape = np.asarray([ord("+"), ord("+"), ord("-"), 1], dtype=np.uint8)
    assert dominant_opcode_color(tape) != dominant_opcode_color(np.asarray([1, 2, 3], dtype=np.uint8))


def test_dummy_visual_run_finalizes_truthful_logs(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    config = Config()
    config.run.n_ticks = 5
    config.run.output_dir = str(tmp_path / "runs")
    config.substrate.tape_length = 8
    config.substrate.max_steps = 8
    config.world.population_size = 4
    config.world.interactions_per_tick = 4
    config.logging.flush_interval = 2
    config.viz.enabled = True
    config.viz.cell_px = 8
    config.viz.fps_cap = 1000
    path = tmp_path / "visual.toml"
    config.save(path)

    run_dir = run_visual(path, max_frames=2)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["exit_status"] == "stopped_by_user"
    assert manifest["parameter_change_count"] == 0
    assert (run_dir / "effective_config.toml").exists()
    assert len(pd.read_parquet(run_dir / "ticks.parquet")) == 2


def test_keyboard_adjusts_selected_live_parameter(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    config = Config()
    config.viz.live_tunable = ["world.mutation_rate"]
    simulation = Simulation(config, run_dir=tmp_path / "keyboard")
    viewer = SoupViewer(simulation)
    pygame.init()
    try:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHTBRACKET, mod=0))
        assert viewer._handle_events()
    finally:
        pygame.quit()
        simulation.writer.close(exit_status="stopped_by_user")

    assert config.world.mutation_rate == 1.0 / 4096.0
    assert simulation.writer.parameter_change_count == 1


def test_live_parameter_changes_are_validated_and_logged(tmp_path: Path) -> None:
    config = Config()
    config.run.n_ticks = 2
    config.substrate.tape_length = 8
    config.substrate.max_steps = 8
    config.world.population_size = 4
    config.world.interactions_per_tick = 2
    simulation = Simulation(config, run_dir=tmp_path / "tunable")
    viewer = SoupViewer(simulation)

    viewer._set_parameter_value("world.mutation_rate", 0.25)
    viewer._set_parameter_value("substrate.max_steps", 32)
    viewer._set_parameter_value("world.interactions_per_tick", 0)
    simulation.writer.close(exit_status="stopped_by_user")

    changes = [json.loads(line) for line in (simulation.writer.run_dir / "parameter_changes.jsonl").read_text().splitlines()]
    events = pd.read_parquet(simulation.writer.run_dir / "events.parquet")
    initial = Config.load(simulation.writer.run_dir / "config.toml")
    effective = Config.load(simulation.writer.run_dir / "effective_config.toml")
    manifest = json.loads((simulation.writer.run_dir / "manifest.json").read_text())
    assert [change["path"] for change in changes] == ["world.mutation_rate", "substrate.max_steps"]
    assert (events["event_type"] == "parameter_changed").sum() == 2
    assert initial.world.mutation_rate == 0.0
    assert effective.world.mutation_rate == 0.25
    assert effective.substrate.max_steps == 32
    assert simulation.scheduler.budget.max_steps == 32
    assert manifest["parameter_change_count"] == 2
    assert viewer.state.parameter_message.startswith("Rejected:")
