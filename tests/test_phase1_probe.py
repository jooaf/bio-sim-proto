from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from experiments import phase1_probe
from experiments.paper_probe import score_selfrep_candidates
from experiments.phase1_probe import (
    functional_scores,
    next_entropy_streak,
    ranked_functional_candidates,
    run_probe,
)


def test_functional_candidate_order_and_paper_score_agreement() -> None:
    values = np.asarray([[2] * 64, [0] * 64, [1] * 64], dtype=np.uint8)
    counts = np.asarray([4, 5, 5], dtype=np.int64)
    candidates, abundances = ranked_functional_candidates(values, counts, limit=3)
    assert candidates[:, 0].tolist() == [0, 1, 2]
    assert abundances.tolist() == [5, 5, 4]
    observed_candidates, observed_abundances, observed_scores = functional_scores(values, counts)
    assert np.array_equal(observed_candidates, candidates)
    assert np.array_equal(observed_abundances, abundances)
    assert np.array_equal(observed_scores, score_selfrep_candidates(candidates, 0))


def test_entropy_streak_is_contemporaneous() -> None:
    streak = 0
    for _ in range(9):
        streak = next_entropy_streak(streak, 1.0)
    assert streak == 9
    assert next_entropy_streak(streak, 0.999) == 0
    assert next_entropy_streak(streak, 1.0) == 10


def test_functional_observation_saves_first_qualified_checkpoint(
    tmp_path: Path, monkeypatch: object
) -> None:
    original_complexity = phase1_probe.complexity_row

    def high_entropy(*args: object, **kwargs: object) -> dict[str, int | float]:
        row = original_complexity(*args, **kwargs)
        row["high_order_entropy"] = 1.0
        return row

    def qualifying_scores(
        values: np.ndarray, counts: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        candidates, abundances = ranked_functional_candidates(values, counts)
        scores = np.zeros(len(candidates), dtype=np.int64)
        scores[0] = 64
        return candidates, abundances, scores

    monkeypatch.setattr(phase1_probe, "complexity_row", high_entropy)  # type: ignore[attr-defined]
    monkeypatch.setattr(phase1_probe, "functional_scores", qualifying_scores)  # type: ignore[attr-defined]
    run_dir = run_probe(
        population_size=16, epochs=11, seed=17, mutation_rate=1.0 / 4096.0,
        pool_multiplier=2.0, callback_interval=1, max_steps=128,
        functional_observation=True, output_dir=tmp_path,
    )
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["functional_origin_epoch"] == 10
    with np.load(run_dir / "origin_checkpoint.npz") as checkpoint:
        assert int(checkpoint["local_epoch"][0]) == 10
        assert int(checkpoint["witness_score"][0]) == 64
        tape_counts = np.bincount(checkpoint["soup"].ravel(), minlength=256)
        assert np.array_equal(tape_counts + checkpoint["pool"], checkpoint["conserved_totals"])
    assay_files = sorted((run_dir / "functional_assays").glob("*.npz"))
    assert [path.name for path in assay_files] == ["epoch_000010.npz", "epoch_000011.npz"]
    with (run_dir / "functional_scores.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [int(row["epoch"]) for row in rows] == [10, 11]
    assert all(row["origin_qualified"] == "True" for row in rows)


def test_functional_observation_does_not_change_trajectory(tmp_path: Path) -> None:
    disabled_final = tmp_path / "disabled.npy"
    enabled_final = tmp_path / "enabled.npy"
    common = dict(
        population_size=16, epochs=4, seed=19, mutation_rate=1.0 / 64.0,
        pool_multiplier=2.0, callback_interval=1, max_steps=128,
    )
    run_probe(**common, final_soup=disabled_final, output_dir=tmp_path / "disabled")
    run_probe(
        **common, functional_observation=True, final_soup=enabled_final,
        output_dir=tmp_path / "enabled",
    )
    assert disabled_final.read_bytes() == enabled_final.read_bytes()


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
