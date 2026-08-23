from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from experiments.paper_probe import initialize_soup
from experiments.phase1_probe import jensen_shannon_divergence, run_probe


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _jsd_reference(a: np.ndarray, b: np.ndarray) -> float:
    p = a.astype(np.float64) / a.sum()
    q = b.astype(np.float64) / b.sum()
    m = 0.5 * (p + q)
    kl = lambda x: np.sum(x[x > 0] * np.log2(x[x > 0] / m[x > 0]))
    return float(0.5 * (kl(p) + kl(q)))


def test_soup_jsd_metrics_present_and_bounded(tmp_path: Path) -> None:
    run_dir = run_probe(
        population_size=16,
        epochs=6,
        seed=7,
        mutation_rate=1.0 / 4096.0,
        pool_multiplier=2.0,
        callback_interval=2,
        max_steps=256,
        output_dir=tmp_path / "runs",
    )
    rows = _rows(run_dir / "aggregate.csv")
    assert len(rows) == 4
    for row in rows:
        assert "soup_jsd_from_pool" in row
        assert "soup_jsd_from_uniform" in row
        pool_jsd = float(row["soup_jsd_from_pool"])
        uniform_jsd = float(row["soup_jsd_from_uniform"])
        assert 0.0 <= pool_jsd <= 1.0
        assert 0.0 <= uniform_jsd <= 1.0


def test_soup_jsd_matches_reference_on_first_callback(tmp_path: Path) -> None:
    soup = initialize_soup(16, 7)
    tape_counts = np.bincount(soup.ravel(), minlength=256).astype(np.int64)
    pool = np.rint(tape_counts * 2.0).astype(np.int64)
    checkpoint = tmp_path / "ckpt.npy"
    np.save(checkpoint, soup)

    run_dir = run_probe(
        population_size=16,
        epochs=2,
        seed=7,
        mutation_rate=0.0,
        pool_multiplier=2.0,
        callback_interval=1,
        max_steps=64,
        output_dir=tmp_path / "runs",
        initial_soup=checkpoint,
    )
    rows = _rows(run_dir / "aggregate.csv")
    assert len(rows) == 2
    # With zero mutation and a tiny execution budget the first callback is
    # close to the initial state; the JSD identities are checked exactly via
    # the helper on the initial histograms.
    assert abs(float(rows[0]["soup_jsd_from_pool"]) - jensen_shannon_divergence(tape_counts, pool)) < 0.5
    assert abs(
        float(rows[0]["soup_jsd_from_uniform"]) - _jsd_reference(tape_counts, np.ones(256))
    ) < 0.05
    # Reference helper agrees with the module implementation.
    assert abs(_jsd_reference(tape_counts, pool) - jensen_shannon_divergence(tape_counts, pool)) < 1e-12


def test_uniform_pool_mode_run_completes_conserved(tmp_path: Path) -> None:
    run_dir = run_probe(
        population_size=16,
        epochs=4,
        seed=3,
        mutation_rate=1.0 / 512.0,
        pool_multiplier=2.0,
        pool_mode="uniform",
        callback_interval=2,
        max_steps=256,
        output_dir=tmp_path / "uniform_runs",
    )
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["exit_status"] == "success"
    assert manifest["max_conservation_residual"] == 0
    assert run_dir.name.endswith("_uniform")
    rows = _rows(run_dir / "aggregate.csv")
    assert all(int(row["max_conservation_residual"]) == 0 for row in rows)
    # Uniform pool: initial soup-vs-pool JSD should equal soup-vs-uniform JSD.
    soup = initialize_soup(16, 3)
    tape_counts = np.bincount(soup.ravel(), minlength=256).astype(np.int64)
    expected = _jsd_reference(tape_counts, np.ones(256))
    assert abs(float(rows[0]["soup_jsd_from_uniform"]) - expected) < 0.05
