"""Outcome-independent tests for the frozen prospective protocol."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from experiments import analyze_ac_p004_prospective_controlled_convergence as ac
from experiments import analyze_ac_p001_high_resource_origin_viability as origin
from experiments import analyze_ac_p003_functional_origin_convergence as previous


def control(index: int = 0) -> ac.ControlledOrigin:
    tapes = np.full((3, 64), index + 100, dtype=np.uint8)
    tapes[0] = 0
    tapes[0, 0] = ord("+")
    tapes[2] = index + 120
    scores = np.array([64, 0, 63], dtype=np.int64)
    counts = np.array([3, 2, 1], dtype=np.int64)
    ranks = np.array([1, 2], dtype=np.int64)
    checkpoint = previous.Checkpoint(ac.RUNS[index], 1001, tapes, counts, scores, 0, ranks, {})
    return ac.ControlledOrigin(checkpoint, 901, tapes.copy(), counts, scores, ranks)


def test_rank_blocks_use_origin_rank_not_prior_score_or_size() -> None:
    scores = np.full(200, 64, dtype=np.int64)
    scores[[3, 63, 130, 199]] = [1, 63, 0, 1]
    assert ac.local_pool(scores, 70).tolist() == [3, 63]
    assert ac.local_pool(scores, 130).tolist() == [130]
    assert ac.local_pool(scores, 1023).tolist() == [199]
    scores[75] = 63
    assert ac.local_pool(scores, 70).tolist() == [75]
    assert not len(ac.local_pool(np.full(5, 64, dtype=np.int64), 1023))


def test_reference_integer_oracle_and_rejection_wrap(monkeypatch: pytest.MonkeyPatch) -> None:
    def mix(value: int) -> int:
        value = (value + 11400714819323198485) % 2**64
        value = ((value ^ (value >> 30)) * 13787848793156543929) % 2**64
        value = ((value ^ (value >> 27)) * 10723151780598845931) % 2**64
        return value ^ (value >> 31)

    for n in (6, 7, 10, 20):
        for size in (1, 3, 64, 2**63 + 1):
            for r, i in ((0, 0), (1, n - 1), (9999, 3)):
                base = 0xAC004 ^ mix(r * n + i)
                k = 0
                while mix(base + k) >= (2**64 // size) * size:
                    k += 1
                assert ac.reference_index(size, r, i, n) == mix(base + k) % size
    calls = []
    answers = iter([previous.MASK ^ 0xAC004, previous.MASK, 8])

    def fake(value: int) -> int:
        calls.append(value)
        return next(answers)

    monkeypatch.setattr(ac, "splitmix64", fake)
    assert ac.reference_index(3, 2, 4, 7) == 2
    assert calls == [18, previous.MASK, 0]


def test_reference_uses_prior_bytes_and_original_ranks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ac, "REPLICATES", 9)
    controls = [control(i) for i in range(7)]
    for c in controls:
        c.candidates[:, :32] = 9
    h, d = ac.reference_medians(controls)
    for r in range(9):
        tapes = np.stack([c.candidates[c.pool_ranks[ac.reference_index(len(c.pool_ranks), r, i, 7)]]
                          for i, c in enumerate(controls)])
        direct_h, direct_d = previous.pairwise(tapes)
        assert h[r] == np.median(direct_h[np.triu_indices(7, 1)])
        assert d[r] == np.median(direct_d[np.triu_indices(7, 1)])


def test_acquisition_stops_before_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(_: Any) -> Any:
        pytest.fail("reference must not run")
    monkeypatch.setattr(ac, "reference_medians", forbidden)
    controls = [control(i) for i in range(6)]
    assert ac.evaluate(controls, False)["decision"] == "UNEVALUABLE"
    controls[0].pool_ranks = np.array([], dtype=np.int64)
    result = ac.evaluate(controls, True)
    assert result["decision"] == "UNEVALUABLE" and result["usable_origins"] == 5
    assert "metrics" not in result and not result["acquisition_gate"]


def test_gates_inclusive_tail_effect_and_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    controls = [control(i) for i in range(6)]
    controls[0].checkpoint.candidates[0, 0] = ord("-")
    h = np.full((6, 6), 0.75)
    np.fill_diagonal(h, 0)
    monkeypatch.setattr(previous, "pairwise", lambda _: (h, h.copy()))
    reference = np.ones(10000)
    reference[:99] = 0.75
    monkeypatch.setattr(ac, "reference_medians", lambda _: (reference, reference.copy()))
    result = ac.evaluate(controls, True)
    assert result["decision"] == "PASS"
    assert result["metrics"]["hamming"]["reference_tail_probability"] == 100 / 10001
    reference[99] = 0.75
    assert not ac.evaluate(controls, True)["gates"]["hamming_tail"]
    reference[99] = 1
    h[h > 0] = 0.750001
    assert not ac.evaluate(controls, True)["gates"]["hamming_effect"]
    h[h > 0] = 0.75
    controls[1].checkpoint.candidates[0, 0] = ord("-")
    assert not ac.evaluate(controls, True)["gates"]["nonempty_signature_80_percent"]
    for c in controls:
        c.checkpoint.candidates[0] = 0
    assert ac.evaluate(controls, True)["decision"] == "VALID NON-PASS"
    reference[:] = 0
    result = ac.evaluate(controls, True)
    assert not result["gates"]["hamming_effect"]
    assert result["metrics"]["hamming"]["reference_tail_probability"] == 1


@pytest.fixture
def run_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> Path:
    from experiments import paper_probe, phase1_probe
    monkeypatch.setattr(origin, "POPULATION", 16)
    monkeypatch.setattr(origin, "EPOCHS", 11)
    monkeypatch.setattr(origin, "CALLBACK", 1)
    original = paper_probe.complexity_row

    def high_entropy(*args: Any, **kwargs: Any) -> dict[str, Any]:
        row = original(*args, **kwargs)
        row["high_order_entropy"] = 1.0 if getattr(request, "param", True) else 0.0
        return row

    def evaluator(tapes: ac.U8, seed: int) -> ac.I64:
        assert seed == 0 and len(tapes) == 16
        result = np.zeros(len(tapes), dtype=np.int64)
        result[1] = 64
        return result

    monkeypatch.setattr(phase1_probe, "complexity_row", high_entropy)
    monkeypatch.setattr(phase1_probe, "score_selfrep_candidates", evaluator)
    monkeypatch.setattr(paper_probe, "score_selfrep_candidates", evaluator)
    return phase1_probe.run_probe(population_size=16, epochs=11, seed=ac.RUNS[0].seed,
                                  mutation_rate=1 / 4096, pool_multiplier=16, callback_interval=1,
                                  functional_observation=True, prospective_control_observation=True,
                                  output_dir=tmp_path / "runs")


def rehash(root: Path, name: str) -> None:
    path = root / "manifest.json"
    manifest = json.loads(path.read_text())
    digest = origin.sha256(root / name)
    manifest["artifact_checksums"][name] = digest
    if name == "pre_origin_control.npz":
        manifest["pre_origin_control_sha256"] = digest
    path.write_text(json.dumps(manifest))


def test_full_integrity_and_original_rank_replay(run_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    replay = previous.verify_scores
    calls = []

    def verify(candidates: ac.U8, scores: ac.I64) -> None:
        calls.append(candidates.copy())
        replay(candidates, scores)

    monkeypatch.setattr(previous, "verify_scores", verify)
    c = ac.load_run(run_dir, ac.RUNS[0])
    assert c is not None and c.checkpoint.epoch == 10 and c.prior_epoch == 9
    assert c.pool_ranks.tolist() == [0, *range(2, 16)]
    assert len(calls) == 2 and all(t.shape == (16, 64) for t in calls)
    assert np.array_equal(calls[1], c.candidates)


@pytest.mark.parametrize("damage", ["checksum", "missing", "local_epoch", "absolute_epoch", "origin_local_epoch",
                                    "evaluator_seed", "control_version", "observation_version", "scores",
                                    "candidates", "abundances", "config", "ledger", "later_assay"])
def test_corruption_fails_closed(run_dir: Path, damage: str) -> None:
    name = "pre_origin_control.npz"
    if damage == "missing":
        (run_dir / name).unlink()
    elif damage == "checksum":
        with (run_dir / name).open("ab") as handle:
            handle.write(b"corrupt")
    elif damage == "config":
        path = run_dir / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["config"]["prospective_control_spec"]["evaluator_seed"] = 1
        path.write_text(json.dumps(manifest))
    elif damage == "ledger":
        name = "symbols.csv"
        frame = pd.read_csv(run_dir / name)
        frame.loc[frame.index == 0, "returns"] += 1
        frame.to_csv(run_dir / name, index=False)
        rehash(run_dir, name)
    else:
        if damage == "later_assay":
            name = "functional_assays/epoch_000011.npz"
        with np.load(run_dir / name, allow_pickle=False) as saved:
            arrays = dict(saved)
        if damage in {"control_version", "observation_version"}:
            arrays[damage] = np.array(["wrong"])
        elif damage == "candidates":
            arrays[damage] = arrays[damage][::-1]
        elif damage == "later_assay":
            arrays["scores"][1] = 0
        else:
            arrays[damage][0] += 1
        np.savez_compressed(run_dir / name, **arrays)
        rehash(run_dir, name)
    with pytest.raises((ValueError, OSError)):
        ac.load_run(run_dir, ac.RUNS[0])


def test_prior_assay_requires_exact_bytes_counts_and_scores(run_dir: Path) -> None:
    checkpoint = previous.load_checkpoint(run_dir, ac.RUNS[0])
    with np.load(run_dir / "pre_origin_control.npz", allow_pickle=False) as saved:
        arrays = dict(saved)
    path = run_dir / "functional_assays/epoch_000009.npz"
    np.savez_compressed(path, **arrays)
    assert ac.load_control(run_dir, checkpoint).prior_epoch == 9
    arrays["abundances"][0] += 1
    np.savez_compressed(path, **arrays)
    with pytest.raises(ValueError, match="exactness"):
        ac.load_control(run_dir, checkpoint)


def test_all_twenty_read_in_seed_order_and_outputs_repeat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    visited = []

    def load(root: Path, run: previous.Run) -> ac.ControlledOrigin | None:
        visited.append(root.name)
        i = ac.RUNS.index(run)
        return control(i) if i < 7 else None

    monkeypatch.setattr(ac, "load_run", load)
    rows, result = ac.analyze(tmp_path)
    assert visited == [r.name + "_prectrlv1" for r in ac.RUNS]
    assert len(rows) == 20 and result["usable_origins"] == 7
    assert result["decision"] == "PASS" and len(result["order"]) == 7
    for directory in (tmp_path / "a", tmp_path / "b"):
        ac.write_outputs(rows, json.loads(json.dumps(result, sort_keys=directory.name == "b")), directory)
    assert {p.name: p.read_bytes() for p in (tmp_path / "a").iterdir()} == {
        p.name: p.read_bytes() for p in (tmp_path / "b").iterdir()}


def test_integrity_failure_does_not_skip_remaining_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    visited = []

    def load(root: Path, run: previous.Run) -> ac.ControlledOrigin:
        visited.append(run.seed)
        if run == ac.RUNS[1]:
            raise ValueError("broken")
        return control(ac.RUNS.index(run))

    monkeypatch.setattr(ac, "load_run", load)
    rows, result = ac.analyze(tmp_path)
    assert len(visited) == len(rows) == 20
    assert result["decision"] == "UNEVALUABLE" and not result["all_twenty_integrity"]
    assert result["errors"] == {str(ac.RUNS[1].seed): "ValueError: broken"}


@pytest.mark.parametrize("run_dir", [False], indirect=True)
def test_no_origin_integrity_and_forbidden_control(run_dir: Path) -> None:
    assert ac.load_run(run_dir, ac.RUNS[0]) is None
    name = "pre_origin_control.npz"
    np.savez_compressed(run_dir / name, candidates=np.zeros((1, 64), dtype=np.uint8))
    rehash(run_dir, name)
    with pytest.raises(ValueError, match="control presence"):
        ac.load_run(run_dir, ac.RUNS[0])


def test_all_usable_origins_included_and_empty_pool_excluded(monkeypatch: pytest.MonkeyPatch) -> None:
    controls = [control(i) for i in range(20)]
    controls[2].pool_ranks = np.array([], dtype=np.int64)
    seen: list[int] = []

    def reference(selected: list[ac.ControlledOrigin]) -> tuple[ac.F64, ac.F64]:
        seen.extend(c.checkpoint.run.seed for c in selected)
        return np.ones(10000), np.ones(10000)

    monkeypatch.setattr(ac, "reference_medians", reference)
    result = ac.evaluate(controls, True)
    assert result["decision"] == "PASS" and result["usable_origins"] == 19
    assert seen == [r.seed for i, r in enumerate(ac.RUNS) if i != 2]
    assert result["pair_count"] == 171
