from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from experiments.metabolic_trace_probe import run_trace
from experiments.paper_probe import initialize_soup, run_probe as run_paper_probe
from experiments.phase1_probe import run_probe


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_paper_probe_initial_soup_and_offset(tmp_path: Path) -> None:
    soup = initialize_soup(16, 7)
    checkpoint = tmp_path / "checkpoint.npy"
    np.save(checkpoint, soup)

    first = run_paper_probe(
        population_size=16,
        epochs=4,
        seed=7,
        mutation_rate=1.0 / 4096.0,
        callback_interval=1,
        output=tmp_path / "offset0.csv",
        initial_soup=checkpoint,
        epoch_offset=0,
    )
    shifted = run_paper_probe(
        population_size=16,
        epochs=4,
        seed=7,
        mutation_rate=1.0 / 4096.0,
        callback_interval=1,
        output=tmp_path / "offset3.csv",
        initial_soup=checkpoint,
        epoch_offset=3,
    )
    first_rows = _rows(first)
    shifted_rows = _rows(shifted)
    assert len(first_rows) == len(shifted_rows) == 4
    assert "dominant_tape_fraction" in first_rows[0]
    assert "distinct_tapes" in first_rows[0]
    # The epoch offset changes the shuffle/mutation stream from the first
    # epoch, so trajectories must diverge immediately.
    assert first_rows[0]["character_reads"] != shifted_rows[0]["character_reads"]

    # Fresh-run equivalence: no initial soup and offset 0 keeps the legacy path.
    legacy = run_paper_probe(
        population_size=16,
        epochs=4,
        seed=7,
        mutation_rate=1.0 / 4096.0,
        callback_interval=1,
        output=tmp_path / "legacy.csv",
    )
    legacy_rows = _rows(legacy)
    assert legacy_rows[0]["character_reads"] == first_rows[0]["character_reads"]
    assert legacy_rows[0]["dominant_tape_fraction"] == first_rows[0]["dominant_tape_fraction"]
    assert legacy_rows[3]["high_order_entropy"] == first_rows[3]["high_order_entropy"]


def test_phase1_probe_initial_soup_conserved(tmp_path: Path) -> None:
    soup = initialize_soup(16, 7)
    checkpoint = tmp_path / "checkpoint.npy"
    np.save(checkpoint, soup)

    run_dir = run_probe(
        population_size=16,
        epochs=6,
        seed=7,
        mutation_rate=1.0 / 4096.0,
        pool_multiplier=2.0,
        callback_interval=2,
        max_steps=256,
        output_dir=tmp_path / "runs",
        initial_soup=checkpoint,
        epoch_offset=2433,
    )
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["exit_status"] == "success"
    assert manifest["max_conservation_residual"] == 0
    config = manifest["config"]
    assert config["initial_soup"] == str(checkpoint)
    assert config["epoch_offset"] == 2433
    assert run_dir.name.endswith("_cont")
    rows = _rows(run_dir / "aggregate.csv")
    assert len(rows) == 4  # epochs 1, 3, 5, plus the final epoch 6
    assert all(int(row["max_conservation_residual"]) == 0 for row in rows)

    # Pool is histogram-matched to the loaded soup, not a fresh seed-7 draw
    # of a different population: totals must match the loaded checkpoint.
    expected_pool_total = int(np.rint(np.bincount(soup.ravel(), minlength=256) * 2.0).sum())
    assert int(rows[0]["pool_total"]) == expected_pool_total


def test_metabolic_trace_windowed_flow_matches_aggregate(tmp_path: Path) -> None:
    run_dir = run_trace(
        population_size=8,
        epochs=12,
        seed=3,
        mutation_rate=1.0 / 512.0,
        pool_multiplier=2.0,
        callback_interval=4,
        sample_denominator=2,
        max_events=1000,
        max_steps=512,
        flow_window=5,
        output_dir=tmp_path / "trace",
    )
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["exit_status"] == "success"
    assert manifest["config"]["flow_window"] == 5

    windows: dict[tuple[int, int], int] = {}
    for row in _rows(run_dir / "flow_edges_windows.csv"):
        key = (int(row["donor_tape"]), int(row["receiver_tape"]))
        windows[key] = windows.get(key, 0) + int(row["token_transfers"])
    aggregate = {
        (int(row["donor_tape"]), int(row["receiver_tape"])): int(row["token_transfers"])
        for row in _rows(run_dir / "flow_edges.csv")
    }
    assert windows == aggregate

    window_counts = {int(row["window"]) for row in _rows(run_dir / "flow_edges_windows.csv")}
    assert max(window_counts) == 2  # epochs 1-5, 6-10, 11-12
