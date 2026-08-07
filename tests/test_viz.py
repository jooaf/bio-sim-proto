from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from pytest import MonkeyPatch

from soup.config import Config
from soup.viz.app import dominant_opcode_color, hash_color, run_visual


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
    assert len(pd.read_parquet(run_dir / "ticks.parquet")) == 2
