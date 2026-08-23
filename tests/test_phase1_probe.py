from __future__ import annotations

import csv
import json
from pathlib import Path

from experiments.phase1_probe import run_probe


def test_phase1_probe_is_conserved_and_deterministic(tmp_path: Path) -> None:
    first = run_probe(
        population_size=16,
        epochs=4,
        seed=7,
        mutation_rate=1.0 / 4096.0,
        pool_multiplier=0.5,
        callback_interval=1,
        max_steps=128,
        output_dir=tmp_path / "first",
    )
    second = run_probe(
        population_size=16,
        epochs=4,
        seed=7,
        mutation_rate=1.0 / 4096.0,
        pool_multiplier=0.5,
        callback_interval=1,
        max_steps=128,
        output_dir=tmp_path / "second",
    )

    assert (first / "writes.csv").read_bytes() == (second / "writes.csv").read_bytes()
    assert (first / "symbols.csv").read_bytes() == (second / "symbols.csv").read_bytes()
    with (first / "aggregate.csv").open(newline="", encoding="utf-8") as handle:
        first_rows = list(csv.DictReader(handle))
    with (second / "aggregate.csv").open(newline="", encoding="utf-8") as handle:
        second_rows = list(csv.DictReader(handle))
    for row in first_rows + second_rows:
        row.pop("elapsed_seconds")
    assert first_rows == second_rows

    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["exit_status"] == "success"
    assert manifest["max_conservation_residual"] == 0

    with (first / "aggregate.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert all(int(row["max_conservation_residual"]) == 0 for row in rows)
    assert all(int(row["pool_total"]) == int(rows[0]["pool_total"]) for row in rows)
