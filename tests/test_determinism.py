from __future__ import annotations

from pathlib import Path

from analysis.load import load_run
from analysis.report import parquet_digest, write_stage0_report
from soup.config import Config
from soup.simulation import Simulation


def short_config() -> Config:
    config = Config()
    config.run.seed = 12345
    config.run.n_ticks = 12
    config.run.epoch_length = 2
    config.substrate.tape_length = 16
    config.substrate.max_steps = 64
    config.substrate.noop_density = 0.8
    config.world.population_size = 16
    config.world.interactions_per_tick = 16
    config.logging.flush_interval = 4
    config.logging.tape_snapshot_interval = 1
    config.logging.full_tape_snapshot_interval = 4
    return config


def test_same_seed_produces_byte_identical_parquet(tmp_path: Path) -> None:
    first = Simulation(short_config(), run_dir=tmp_path / "first").run()
    second = Simulation(short_config(), run_dir=tmp_path / "second").run()
    assert parquet_digest(first) == parquet_digest(second)
    for first_file in sorted(first.glob("*.parquet")):
        assert first_file.read_bytes() == (second / first_file.name).read_bytes()


def test_logs_load_and_report_without_manual_intervention(tmp_path: Path) -> None:
    run_dir = Simulation(short_config(), run_dir=tmp_path / "run").run()
    loaded = load_run(run_dir)
    assert len(loaded.table("ticks")) == short_config().run.n_ticks
    report = write_stage0_report(run_dir)
    assert report.exists()


def test_golden_short_run_parquet_digest(tmp_path: Path) -> None:
    run_dir = Simulation(short_config(), run_dir=tmp_path / "golden").run()
    assert parquet_digest(run_dir) == "f5cbbe69c6083390556a74c11a1ff68df6d58bd2b87105a1d767dc6e139a7906"
