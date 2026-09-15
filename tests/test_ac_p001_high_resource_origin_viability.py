from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from numpy.typing import NDArray

from experiments import analyze_ac_p001_high_resource_origin_viability as analysis


def campaign(origins: int) -> pd.DataFrame:
    return pd.DataFrame([{"seed": seed, "integrity": True, "origin": index < origins}
                         for index, seed in enumerate(analysis.SEEDS)])


@pytest.mark.parametrize("origins,passed", [(0, False), (2, False), (3, True), (10, True)])
def test_incidence_gate(origins: int, passed: bool) -> None:
    rows = campaign(origins)
    decision = analysis.evaluate(rows)
    assert decision["gates"]["integrity"]
    assert decision["positive_control_viability"] is passed
    assert decision["origins"] == origins
    assert decision == analysis.evaluate(rows.sample(frac=1, random_state=7))
    assert ("held-out" if passed else "Stop the BFF") in decision["next_step"]


@pytest.mark.parametrize("damage", ["missing", "duplicate", "seed", "invalid", "unknown", "extra"])
def test_campaign_integrity_fail_closed(damage: str) -> None:
    rows = campaign(10)
    if damage == "missing":
        rows = rows.iloc[:-1]
    elif damage == "duplicate":
        rows = pd.concat([rows.iloc[:-1], rows.iloc[:1]], ignore_index=True)
    elif damage == "seed":
        rows.loc[0, "seed"] = 202611000
    elif damage == "invalid":
        rows.loc[0, "integrity"] = False
    elif damage == "extra":
        rows = pd.concat([rows, rows.iloc[:1]], ignore_index=True)
    else:
        rows["origin"] = rows["origin"].astype(object)
        rows.loc[0, "origin"] = None
    decision = analysis.evaluate(rows)
    assert not decision["gates"]["integrity"]
    assert not decision["positive_control_viability"]


@pytest.fixture
def run_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> Path:
    """Exercise real publication/ledgers with a bounded synthetic observation."""
    from experiments import phase1_probe
    monkeypatch.setattr(analysis, "POPULATION", 16)
    monkeypatch.setattr(analysis, "EPOCHS", 11)
    monkeypatch.setattr(analysis, "CALLBACK", 1)
    from experiments.paper_probe import complexity_row
    original = complexity_row
    entropy, score = getattr(request, "param", (1.0, 64))

    def high_entropy(*args: Any, **kwargs: Any) -> dict[str, Any]:
        row = original(*args, **kwargs)
        row["high_order_entropy"] = entropy[int(row["epoch"]) - 1] if isinstance(entropy, list) else entropy
        return row

    def scores(values: NDArray[np.uint8], counts: NDArray[np.int64]) -> tuple[NDArray[np.uint8], NDArray[np.int64], NDArray[np.int64]]:
        tapes, abundances = phase1_probe.ranked_functional_candidates(values, counts)
        result = np.zeros(len(tapes), dtype=np.int64)
        result[0] = score
        return tapes, abundances, result

    monkeypatch.setattr(phase1_probe, "complexity_row", high_entropy)
    monkeypatch.setattr(phase1_probe, "functional_scores", scores)
    return phase1_probe.run_probe(population_size=16, epochs=11, seed=analysis.SEEDS[0],
                                  mutation_rate=1 / 4096, pool_multiplier=16, callback_interval=1,
                                  functional_observation=True, output_dir=tmp_path / "runs")


def rehash(root: Path) -> None:
    path = root / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["artifact_checksums"] = {str(p.relative_to(root)): analysis.sha256(p)
                                       for p in root.rglob("*") if p.is_file() and p != path}
    if (root / "origin_checkpoint.npz").exists():
        manifest["origin_checkpoint_sha256"] = analysis.sha256(root / "origin_checkpoint.npz")
    path.write_text(json.dumps(manifest))


def test_complete_assays_checkpoint_and_composition(run_dir: Path) -> None:
    result, entropy, witnesses = analysis.summarize(run_dir)
    assert result["integrity"], result["error"]
    assert result["origin_epoch"] == 10
    assert result["eligible_callbacks"] == 2
    assert result["max_functional_score"] == 64
    assert sum(json.loads(result["final_composition"])) == 16 * 64
    assert len(entropy) == 11 and len(witnesses) == 1
    assert witnesses[0]["epoch"] == 10


@pytest.mark.parametrize("run_dir,expected", [((0.5, 0), None), ((1.0, 0), 0), ((1.0, 63), 63),
                                            (([1.0] * 9 + [0.9, 1.0], 64), None)], indirect=["run_dir"])
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
    assert not decision["positive_control_viability"]
    assert decision == analysis.analyze(run_dir.parent, b)
    assert {p.name: p.read_bytes() for p in a.iterdir()} == {p.name: p.read_bytes() for p in b.iterdir()}
    assert "unknown outcomes" in (a / "report.md").read_text()


@pytest.mark.parametrize("damage", ["pool", "soup", "totals", "witness", "epoch", "counter", "config"])
def test_rehashed_checkpoint_corruption(run_dir: Path, damage: str) -> None:
    path = run_dir / "origin_checkpoint.npz"
    with np.load(path, allow_pickle=False) as saved:
        arrays = dict(saved)
    if damage == "pool":
        arrays["pool"][0] += 1
    elif damage == "soup":
        arrays["soup"][0, 0] ^= 1
    elif damage == "totals":
        # Internally conserved, but no longer the preregistered reservoir.
        arrays["pool"][0] += 1
        arrays["conserved_totals"][0] += 1
        symbols = pd.read_csv(run_dir / "symbols.csv")
        symbols.loc[(symbols.epoch == 10) & (symbols.symbol == 0), "pool_count"] += 1
        symbols.to_csv(run_dir / "symbols.csv", index=False)
    elif damage == "witness":
        arrays["witness_score"][0] = 63
    elif damage == "epoch":
        arrays["local_epoch"][0] = 11
    elif damage == "counter":
        arrays["changing_write_counter"][0] += 1
    else:
        arrays["config_json"] = np.array(["{}"])
    np.savez_compressed(path, **arrays)
    rehash(run_dir)
    result, _, _ = analysis.summarize(run_dir)
    assert not result["integrity"]
    assert result["origin"] is None
    assert "checkpoint" in result["error"] or "pool total" in result["error"]


@pytest.mark.parametrize("damage", ["ledger", "initial_pool", "negative", "schedule", "block_totals"])
def test_rehashed_symbol_corruption(run_dir: Path, damage: str) -> None:
    path = run_dir / "symbols.csv"
    frame = pd.read_csv(path)
    key = {"ledger": "returns", "initial_pool": "initial_pool_count", "negative": "pool_count",
           "schedule": "symbol", "block_totals": "execution_blocked"}[damage]
    frame.loc[0, key] = -1 if damage == "negative" else int(frame[key].iloc[0]) + 1
    frame.to_csv(path, index=False)
    rehash(run_dir)
    result, _, _ = analysis.summarize(run_dir)
    assert not result["integrity"]
    assert result["origin"] is None


@pytest.mark.parametrize("key,value", [("pool_multiplier", 2), ("seed", 202611000),
                                       ("initial_soup", "resume.npz"), ("epoch_offset", 1),
                                       ("friction_rejection_rate", 0.1), ("max_steps", 4096),
                                       ("pool_mode", "excluded_list"), ("callback_interval", 2)])
def test_unregistered_config(run_dir: Path, key: str, value: Any) -> None:
    config = json.loads((run_dir / "config.json").read_text())
    config[key] = value
    with pytest.raises(ValueError):
        analysis.validate_config(config)


def test_empty_campaign_and_output_guard(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    root.mkdir()
    decision = analysis.analyze(root, tmp_path / "output")
    assert decision["origins"] == decision["verified_runs"] == 0
    assert not decision["positive_control_viability"]
    with pytest.raises(ValueError, match="separate"):
        analysis.analyze(root, root / "analysis")


def test_unlisted_artifact_is_rejected(run_dir: Path) -> None:
    (run_dir / "extra.txt").write_text("unexpected")
    result, _, _ = analysis.summarize(run_dir)
    assert "checksum inventory" in result["error"]
