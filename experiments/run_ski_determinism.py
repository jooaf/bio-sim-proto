"""Run and persist the Phase 1 SKI byte-identical determinism check."""

from __future__ import annotations

import json
from pathlib import Path

from analysis.load import TABLE_NAMES
from analysis.report import parquet_digest
from soup.config import Config
from soup.simulation import Simulation


def main() -> None:
    config = Config.load("experiments/configs/stage1_ski.toml")
    config.run.n_ticks = 100
    config.logging.interaction_log_rate = 1.0
    config.logging.tape_snapshot_interval = 10
    config.logging.full_tape_snapshot_interval = 10
    root = Path("experiments/phase1_runs/ski_determinism")
    first = Simulation(config, run_dir=root / "first").run()
    second = Simulation(config, run_dir=root / "second").run()
    digest_first = parquet_digest(first)
    digest_second = parquet_digest(second)
    tables_equal = {
        name: (first / f"{name}.parquet").read_bytes() == (second / f"{name}.parquet").read_bytes()
        for name in TABLE_NAMES
    }
    result = {
        "digest_first": digest_first,
        "digest_second": digest_second,
        "all_tables_byte_identical": all(tables_equal.values()),
        "tables": tables_equal,
    }
    target = Path("reports/phase1_ski_determinism.json")
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not result["all_tables_byte_identical"]:
        raise RuntimeError("SKI Parquet output is not byte-identical")
    print(target)


if __name__ == "__main__":
    main()
