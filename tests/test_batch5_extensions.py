from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from experiments.paper_probe import initialize_soup
from experiments.phase1_probe import run_probe


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _excluded_pool_run(tmp_path: Path, exclude_top: int) -> tuple[Path, np.ndarray, np.ndarray]:
    soup = initialize_soup(32, 11)
    # Force clear enrichment: columns 0..4 hold symbols 0..4 on every tape.
    for i in range(5):
        soup[:, i] = i
    checkpoint = tmp_path / f"ckpt_{exclude_top}.npy"
    np.save(checkpoint, soup)
    run_dir = run_probe(
        population_size=32,
        epochs=6,
        seed=11,
        mutation_rate=1.0 / 512.0,
        pool_multiplier=2.0,
        pool_mode="excluded_top",
        pool_exclude_top=exclude_top,
        callback_interval=2,
        max_steps=256,
        output_dir=tmp_path / "runs",
        initial_soup=checkpoint,
    )
    tape_counts = np.bincount(soup.ravel(), minlength=256).astype(np.int64)
    matched = np.rint(tape_counts * 2.0).astype(np.int64)
    return run_dir, tape_counts, matched


def test_excluded_top_pool_zero_for_top_symbols(tmp_path: Path) -> None:
    run_dir, tape_counts, matched = _excluded_pool_run(tmp_path, 3)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["exit_status"] == "success"
    assert manifest["max_conservation_residual"] == 0
    assert manifest["config"]["pool_mode"] == "excluded_top"
    assert manifest["config"]["pool_exclude_top"] == 3
    assert run_dir.name.endswith("_excl3_cont")

    symbols = _rows(run_dir / "symbols.csv")
    first_epoch = min(int(row["epoch"]) for row in symbols)
    initial = {int(row["symbol"]): int(row["initial_pool_count"]) for row in symbols if int(row["epoch"]) == first_epoch}
    top3 = set(np.argsort(-tape_counts, kind="stable")[:3].tolist())
    for symbol in top3:
        assert initial[symbol] == 0, f"symbol {symbol} should have zero pool stock"
    # Mass preserved: total pool equals the matched pool total.
    assert sum(initial.values()) == int(matched.sum())
    # All mass went to non-excluded symbols.
    for symbol, count in initial.items():
        if symbol not in top3:
            assert count >= 0


def test_excluded_top_conservation_and_blocking(tmp_path: Path) -> None:
    run_dir, _, _ = _excluded_pool_run(tmp_path, 2)
    aggregate = _rows(run_dir / "aggregate.csv")
    assert all(int(row["max_conservation_residual"]) == 0 for row in aggregate)
    # Writes to excluded symbols must block at least sometimes under mutation.
    symbols = _rows(run_dir / "symbols.csv")
    first_epoch = min(int(row["epoch"]) for row in symbols)
    excluded = {
        int(row["symbol"])
        for row in symbols
        if int(row["epoch"]) == first_epoch and int(row["initial_pool_count"]) == 0
    }
    assert len(excluded) == 2
    blocked_excluded = sum(
        int(row["execution_blocked"]) + int(row["mutation_blocked"])
        for row in symbols
        if int(row["symbol"]) in excluded
    )
    blocked_total = sum(
        int(row["execution_blocked"]) + int(row["mutation_blocked"]) for row in symbols
    )
    if blocked_total:
        assert blocked_excluded > 0


def test_excluded_top_validation(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError):
        run_probe(
            population_size=16,
            epochs=2,
            seed=1,
            mutation_rate=0.0,
            pool_multiplier=2.0,
            pool_mode="excluded_top",
            pool_exclude_top=0,
            callback_interval=1,
            output_dir=tmp_path / "runs",
        )
    with pytest.raises(ValueError):
        run_probe(
            population_size=16,
            epochs=2,
            seed=1,
            mutation_rate=0.0,
            pool_multiplier=2.0,
            pool_mode="uniform",
            pool_exclude_top=3,
            callback_interval=1,
            output_dir=tmp_path / "runs",
        )
