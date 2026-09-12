from __future__ import annotations

import csv
import json
from pathlib import Path

from experiments.phase1_probe import run_probe


def test_friction_rejection_is_deterministic_conserved_and_separate(tmp_path: Path) -> None:
    first_final = tmp_path / "first_final.npy"
    second_final = tmp_path / "second_final.npy"
    first = run_probe(
        population_size=16,
        epochs=4,
        seed=11,
        mutation_rate=1.0 / 64.0,
        pool_multiplier=2.0,
        callback_interval=1,
        max_steps=128,
        friction_rejection_rate=1.0,
        final_soup=first_final,
        output_dir=tmp_path / "friction_first",
    )
    second = run_probe(
        population_size=16,
        epochs=4,
        seed=11,
        mutation_rate=1.0 / 64.0,
        pool_multiplier=2.0,
        callback_interval=1,
        max_steps=128,
        friction_rejection_rate=1.0,
        final_soup=second_final,
        output_dir=tmp_path / "friction_second",
    )
    assert first_final.read_bytes() == second_final.read_bytes()
    with (first / "writes.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert sum(int(row["execution_friction_blocked"]) for row in rows) > 0
    assert sum(int(row["mutation_friction_blocked"]) for row in rows) > 0
    assert sum(int(row["execution_scarcity_blocked"]) for row in rows) == 0
    assert json.loads((first / "manifest.json").read_text(encoding="utf-8"))["max_conservation_residual"] == 0


def test_zero_friction_preserves_legacy_trajectory(tmp_path: Path) -> None:
    default_final = tmp_path / "default.npy"
    explicit_final = tmp_path / "explicit.npy"
    run_probe(
        population_size=16, epochs=4, seed=13, mutation_rate=1.0 / 64.0,
        pool_multiplier=2.0, callback_interval=1, max_steps=128,
        final_soup=default_final, output_dir=tmp_path / "default",
    )
    run_probe(
        population_size=16, epochs=4, seed=13, mutation_rate=1.0 / 64.0,
        pool_multiplier=2.0, callback_interval=1, max_steps=128,
        friction_rejection_rate=0.0, final_soup=explicit_final,
        output_dir=tmp_path / "explicit",
    )
    assert default_final.read_bytes() == explicit_final.read_bytes()


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
