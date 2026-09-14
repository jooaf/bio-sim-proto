from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from experiments import analyze_ac_i001_origin_filter_confirmation as analysis


def campaign(control: int = 5, friction: int = 5, natural: int = 0) -> pd.DataFrame:
    totals = {"control": control, "friction": friction, "natural_six": natural}
    return pd.DataFrame([
        {"seed": seed, "arm": arm, "integrity": True, "origin": index < totals[arm], "total_blocks": 100}
        for index, seed in enumerate(analysis.SEEDS) for arm in analysis.ARMS
    ])


@pytest.mark.parametrize("b,c,expected", [(0, 0, 1), (5, 0, 1 / 32), (4, 0, 1 / 16),
                                          (0, 5, 1), (5, 1, 7 / 64), (20, 0, 1 / 2**20)])
def test_exact_one_sided_discordance(b: int, c: int, expected: float) -> None:
    assert analysis.exact_discordance(b, c) == expected


def test_zero_incidence_is_positive_control_failure() -> None:
    decision, pairs, incidence = analysis.evaluate(campaign(0, 0, 0))
    assert decision["gates"]["integrity"]
    assert decision["gates"]["mechanical_match"]
    assert not decision["gates"]["positive_controls"]
    assert not decision["class_specific_support"]
    assert "stop AC-I002" in decision["decision"]
    assert incidence["origins"].tolist() == [0, 0, 0]
    assert len(pairs) == 20
    assert all(row["p_one_sided"] == 1 for row in decision["comparisons"])


def test_all_gates_pass_and_row_order_does_not_matter() -> None:
    rows = campaign(7, 5)
    first = analysis.evaluate(rows)
    second = analysis.evaluate(rows.sample(frac=1, random_state=9))
    assert first[0] == second[0]
    pd.testing.assert_frame_equal(first[1], second[1])
    assert first[0]["class_specific_support"]
    assert all(first[0]["gates"].values())


def test_viability_bound_and_incidence_significance_are_separate() -> None:
    decision, _, _ = analysis.evaluate(campaign(8, 5))
    assert decision["gates"]["selective_incidence_contrast"]
    assert not decision["gates"]["nonspecific_control_viability"]
    assert not decision["class_specific_support"]
    decision, _, _ = analysis.evaluate(campaign(5, 5, 1))
    assert decision["gates"]["positive_controls"]
    assert all(row["incidence_difference"] == 0.2 for row in decision["comparisons"])
    assert not decision["gates"]["selective_incidence_contrast"]  # four favorable discordants: p=.0625


def test_pairing_not_unpaired_incidence() -> None:
    rows = campaign(5, 5)
    rows.loc[(rows.arm == "natural_six") & rows.seed.isin(analysis.SEEDS[5:10]), "origin"] = True
    decision, _, _ = analysis.evaluate(rows)
    assert all(row["favored_only"] == row["natural_only"] == 5 for row in decision["comparisons"])
    assert not decision["class_specific_support"]


@pytest.mark.parametrize("ratio,passed", [(0.8, True), (1.25, True), (0.79, False), (1.26, False)])
def test_median_match_inclusive(ratio: float, passed: bool) -> None:
    rows = campaign()
    rows.loc[rows.arm == "friction", "total_blocks"] = round(100 * ratio)
    decision, _, _ = analysis.evaluate(rows)
    assert decision["gates"]["mechanical_match"] is passed


@pytest.mark.parametrize("bad_pairs,passed", [(4, True), (5, False)])
def test_paired_match_requires_sixteen(bad_pairs: int, passed: bool) -> None:
    rows = campaign()
    rows.loc[(rows.arm == "friction") & rows.seed.isin(analysis.SEEDS[:bad_pairs]), "total_blocks"] = 151
    decision, _, _ = analysis.evaluate(rows)
    assert decision["median_block_ratio"] == 1
    assert decision["matched_pairs"] == 20 - bad_pairs
    assert decision["gates"]["mechanical_match"] is passed


def test_zero_denominators_fail_match() -> None:
    rows = campaign()
    rows["total_blocks"] = 0
    decision, _, _ = analysis.evaluate(rows)
    assert decision["median_block_ratio"] is None
    assert decision["matched_pairs"] == 0
    assert not decision["class_specific_support"]


@pytest.mark.parametrize("damage", ["missing", "duplicate", "seed", "invalid"])
def test_integrity_matrix_fail_closed(damage: str) -> None:
    rows = campaign()
    if damage == "missing":
        rows = rows.iloc[:-1]
    elif damage == "duplicate":
        rows = pd.concat([rows.iloc[:-1], rows.iloc[:1]], ignore_index=True)
    elif damage == "seed":
        rows.loc[0, "seed"] = 202610099
    else:
        rows.loc[0, "integrity"] = False
        rows["origin"] = rows["origin"].astype(object)
        rows.loc[0, "origin"] = None
    decision, pairs, _ = analysis.evaluate(rows)
    assert not decision["gates"]["integrity"]
    assert not decision["class_specific_support"]
    assert pairs.empty


@pytest.fixture
def run_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> Path:
    """Exercise real publication/ledgers with a bounded synthetic observation."""
    from experiments import phase1_probe
    monkeypatch.setattr(analysis, "POPULATION", 16)
    monkeypatch.setattr(analysis, "EPOCHS", 11)
    monkeypatch.setattr(analysis, "CALLBACK", 1)
    original = phase1_probe.complexity_row
    entropy, score = getattr(request, "param", (1.0, 64))

    def high_entropy(*args, **kwargs):
        row = original(*args, **kwargs)
        row["high_order_entropy"] = entropy
        return row

    def scores(values, counts):
        tapes, abundances = phase1_probe.ranked_functional_candidates(values, counts)
        result = np.zeros(len(tapes), dtype=np.int64)
        result[0] = score
        return tapes, abundances, result

    monkeypatch.setattr(phase1_probe, "complexity_row", high_entropy)
    monkeypatch.setattr(phase1_probe, "functional_scores", scores)
    return phase1_probe.run_probe(population_size=16, epochs=11, seed=analysis.SEEDS[0],
                                  mutation_rate=1 / 4096, pool_multiplier=2, callback_interval=1,
                                  functional_observation=True, output_dir=tmp_path / "runs")


def rehash(root: Path) -> None:
    path = root / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["artifact_checksums"] = {str(p.relative_to(root)): analysis.sha256(p)
                                       for p in root.rglob("*") if p.is_file() and p != path}
    path.write_text(json.dumps(manifest))


def test_complete_assays_checkpoint_and_composition(run_dir: Path) -> None:
    result, entropy, witnesses = analysis.summarize(run_dir)
    assert result["integrity"], result["error"]
    assert result["origin_epoch"] == 10
    assert result["eligible_callbacks"] == 2
    assert result["max_functional_score"] == 64
    assert sum(json.loads(result["final_composition"])) == 16 * 64
    assert len(entropy) == 11 and len(witnesses) == 2


@pytest.mark.parametrize("run_dir,expected", [((0.5, 0), None), ((1.0, 63), 63)], indirect=["run_dir"])
def test_nonorigins_preserve_missing_vs_measured_score(run_dir: Path, expected: int | None) -> None:
    result, _, witnesses = analysis.summarize(run_dir)
    assert result["integrity"], result["error"]
    assert result["origin"] is False
    assert result["origin_epoch"] is None
    assert result["max_functional_score"] == expected
    assert not witnesses


@pytest.mark.parametrize("damage", ["checksum", "missing_assay", "streak", "scores", "ordering", "seed", "manifest_origin", "writes", "residual"])
def test_artifact_and_endpoint_corruption_fails_closed(run_dir: Path, damage: str) -> None:
    if damage == "checksum":
        with (run_dir / "writes.csv").open("a") as handle:
            handle.write("\n")
    elif damage == "missing_assay":
        (run_dir / "functional_assays" / "epoch_000010.npz").unlink()
    elif damage in ("scores", "ordering", "seed"):
        path = run_dir / "functional_assays" / "epoch_000010.npz"
        with np.load(path) as saved:
            arrays = dict(saved)
        if damage == "scores":
            arrays["scores"][0] = 63
        elif damage == "ordering":
            arrays["candidates"] = arrays["candidates"][::-1]
        else:
            arrays["evaluator_seed"][0] = 1
        np.savez_compressed(path, **arrays)
        rehash(run_dir)
    elif damage == "manifest_origin":
        path = run_dir / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["functional_origin_epoch"] = 11
        path.write_text(json.dumps(manifest))
    else:
        path = run_dir / ("writes.csv" if damage == "writes" else "aggregate.csv")
        frame = pd.read_csv(path)
        if damage == "writes":
            frame = frame.iloc[:-1]
        elif damage == "residual":
            frame.loc[0, "max_conservation_residual"] = 1
        else:
            frame.loc[0, "functional_entropy_streak"] = 10
        frame.to_csv(path, index=False)
        rehash(run_dir)
    result, _, _ = analysis.summarize(run_dir)
    assert not result["integrity"]
    assert result["origin"] is None
    assert result["error"]


def test_outputs_are_deterministic_and_incomplete_campaign_cannot_pass(run_dir: Path, tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    decision = analysis.analyze(run_dir.parent, a)
    assert not decision["class_specific_support"]
    assert decision == analysis.analyze(run_dir.parent, b)
    assert {p.name: p.read_bytes() for p in a.iterdir()} == {p.name: p.read_bytes() for p in b.iterdir()}
    assert "No class-specific support" in (a / "report.md").read_text()
