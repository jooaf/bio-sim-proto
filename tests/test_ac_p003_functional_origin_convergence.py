"""Synthetic, outcome-independent tests of the frozen AC-P003 protocol."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from experiments import analyze_ac_p003_functional_origin_convergence as ac
from experiments import analyze_ac_p001_high_resource_origin_viability as origin


def checkpoint(index: int = 0, *, empty: bool = False) -> ac.Checkpoint:
    tapes = np.full((3, 64), index + 100, dtype=np.uint8)
    tapes[0] = 0
    tapes[0, 0] = ord("+")
    tapes[2] = index + 120
    scores = np.array([64, 0, 63], dtype=np.int64)
    return ac.Checkpoint(ac.RUNS[index], 10, tapes, np.array([3, 2, 1], dtype=np.int64),
                         scores, 0, np.array([] if empty else [1, 2], dtype=np.int64), {})


@pytest.mark.parametrize("value,expected", [(0, 0xE220A8397B1DCDAF), (1, 0x910A2DEC89025CC1),
                                           (0xFFFFFFFFFFFFFFFF, 0xE4D971771B652C20)])
def test_splitmix_known_answers_and_wrap(value: int, expected: int) -> None:
    assert ac.splitmix64(value) == expected
    assert ac.splitmix64(value + (1 << 64)) == expected


def test_rejection_sampler_rejects_limit_and_wraps(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    answers = iter([ac.MASK ^ 0xAC003, ac.MASK, 8])

    def fake(value: int) -> int:
        calls.append(value)
        return next(answers)

    monkeypatch.setattr(ac, "splitmix64", fake)
    assert ac.reference_index(3, 2, 4) == 2
    assert calls == [24, ac.MASK, 0]


def test_reference_index_matches_independent_integer_implementation() -> None:
    def mix(value: int) -> int:
        modulus = 2**64
        value = (value + 11400714819323198485) % modulus
        value = ((value ^ (value >> 30)) * 13787848793156543929) % modulus
        value = ((value ^ (value >> 27)) * 10723151780598845931) % modulus
        return value ^ (value >> 31)

    for n in (1, 3, 63, 64, 65, 2**63 + 1):
        for r, i in ((0, 0), (1, 9), (9999, 7)):
            base = 0xAC003 ^ mix(r * 10 + i)
            k = 0
            while mix(base + k) >= (2**64 // n) * n:
                k += 1
            assert ac.reference_index(n, r, i) == mix(base + k) % n


def test_rank_local_pool_fallback_ties_and_original_ranks() -> None:
    scores = np.full(200, 64, dtype=np.int64)
    scores[[3, 63, 130, 199]] = [1, 63, 0, 1]
    assert ac.local_pool(scores, 70).tolist() == [3, 63]
    assert ac.local_pool(scores, 129).tolist() == [130]
    scores[75] = 63
    assert ac.local_pool(scores, 70).tolist() == [75]
    assert not len(ac.local_pool(np.full(5, 64, dtype=np.int64), 0))


def test_byte_hamming_jsd_and_static_opcode_definition() -> None:
    tapes = np.zeros((3, 64), dtype=np.uint8)
    tapes[1] = 1
    tapes[2, :32] = 1
    h, d = ac.pairwise(tapes)
    assert h[0, 1] == d[0, 1] == 1
    assert h[0, 2] == 0.5
    assert d[0, 2] == pytest.approx(0.31127812445913283)
    assert np.array_equal(np.diag(d), np.zeros(3))
    assert np.array_equal(d, d.T)
    assert ac.opcode_signature(np.frombuffer(b"a<\x00>{}-+.,[]:!b", dtype=np.uint8)) == "<>{}-+.,[]"
    shifted = np.roll(tapes[2], 32)
    h, d = ac.pairwise(np.stack([tapes[2], shifted]))
    assert h[0, 1] == 1 and d[0, 1] == 0


def test_reference_matches_direct_whole_set_calculation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ac, "REPLICATES", 7)
    checkpoints = [checkpoint(i) for i in ac.PRIMARY]
    h, d = ac.reference_medians(checkpoints)
    for r in range(7):
        tapes = np.stack([c.candidates[c.pool_ranks[ac.reference_index(len(c.pool_ranks), r, i)]]
                          for i, c in enumerate(checkpoints)])
        direct_h, direct_d = ac.pairwise(tapes)
        assert h[r] == np.median(direct_h[np.triu_indices(10, 1)])
        assert d[r] == np.median(direct_d[np.triu_indices(10, 1)])


def test_composite_gate_ties_empty_signatures_and_zero_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    checkpoints = [checkpoint(i) for i in ac.PRIMARY]
    monkeypatch.setattr(ac, "reference_medians", lambda _: (np.ones(10000), np.ones(10000)))
    result = ac.evaluate(checkpoints, True)
    assert result["decision"] == "PASS"
    assert result["metrics"]["hamming"]["reference_tail_probability"] == 1 / 10001
    for c in checkpoints[:3]:
        c.candidates[0, 0] = 0
    assert ac.evaluate(checkpoints, True)["decision"] == "VALID NON-PASS"
    for c in checkpoints:
        c.candidates[0] = 0
    assert not ac.evaluate(checkpoints, True)["gates"]["signature_8_of_10"]
    monkeypatch.setattr(ac, "reference_medians", lambda _: (np.zeros(10000), np.zeros(10000)))
    result = ac.evaluate(checkpoints, True)
    assert not result["gates"]["hamming_effect"]
    assert result["metrics"]["hamming"]["reference_tail_probability"] == 1
    assert ac.evaluate(checkpoints, False)["decision"] == "UNEVALUABLE"
    checkpoints[0].pool_ranks = np.array([], dtype=np.int64)
    assert ac.evaluate(checkpoints, True)["decision"] == "UNEVALUABLE"


def test_primary_replacement_scope_and_no_sensitivity_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    visited: list[str] = []

    def load(root: Path, run: ac.Run) -> ac.Checkpoint:
        visited.append(root.name)
        return checkpoint(ac.RUNS.index(run))

    def evaluate(checkpoints: list[ac.Checkpoint], integrity: bool) -> dict[str, Any]:
        assert integrity
        indices = [ac.RUNS.index(c.run) for c in checkpoints]
        assert len({c.run.seed for c in checkpoints}) == 10
        return {"decision": "PASS" if 9 in indices else "VALID NON-PASS", "indices": indices}

    monkeypatch.setattr(ac, "load_checkpoint", load)
    monkeypatch.setattr(ac, "evaluate", evaluate)
    _, _, result = ac.analyze(tmp_path / "p1", tmp_path / "p2")
    assert visited == [run.name for run in ac.RUNS]
    assert result["primary"]["indices"] == list(ac.PRIMARY)
    assert result["replacement_sensitivity"]["indices"] == list(ac.REPLACEMENT)
    assert result["decision"] == "VALID NON-PASS"
    assert result["replacement_sensitivity"]["decision"] == "PASS"


@pytest.fixture
def run_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from experiments import phase1_probe
    monkeypatch.setattr(origin, "POPULATION", 16)
    monkeypatch.setattr(origin, "EPOCHS", 11)
    monkeypatch.setattr(origin, "CALLBACK", 1)
    from experiments.paper_probe import complexity_row
    original = complexity_row

    def high_entropy(*args: Any, **kwargs: Any) -> dict[str, Any]:
        row = original(*args, **kwargs)
        row["high_order_entropy"] = 1.0
        return row

    def scores(values: ac.U8, counts: ac.I64) -> tuple[ac.U8, ac.I64, ac.I64]:
        tapes, abundances = phase1_probe.ranked_functional_candidates(values, counts)
        result = np.zeros(len(tapes), dtype=np.int64)
        result[1] = 64
        return tapes, abundances, result

    def verify(candidates: ac.U8, scores: ac.I64) -> None:
        assert len(candidates) == 16
        expected = np.zeros(16, dtype=np.int64)
        expected[1] = 64
        ac.require(np.array_equal(expected, scores), "original-rank evaluator scores mismatch")

    monkeypatch.setattr(phase1_probe, "complexity_row", high_entropy)
    monkeypatch.setattr(phase1_probe, "functional_scores", scores)
    monkeypatch.setattr(ac, "verify_scores", verify)
    return phase1_probe.run_probe(population_size=16, epochs=11, seed=ac.RUNS[0].seed,
                                  mutation_rate=1 / 4096, pool_multiplier=16, callback_interval=1,
                                  functional_observation=True, output_dir=tmp_path / "runs")


def rehash(root: Path, name: str) -> None:
    path = root / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["artifact_checksums"][name] = origin.sha256(root / name)
    if name == "origin_checkpoint.npz":
        manifest["origin_checkpoint_sha256"] = manifest["artifact_checksums"][name]
    path.write_text(json.dumps(manifest))


def test_integrity_and_no_later_assay_access(run_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_load = np.load
    opened: list[str] = []

    def restricted_load(file: Any, *args: Any, **kwargs: Any) -> Any:
        opened.append(str(file))
        assert "epoch_000011" not in str(file)
        return original_load(file, *args, **kwargs)

    monkeypatch.setattr(np, "load", restricted_load)
    result = ac.load_checkpoint(run_dir, ac.RUNS[0])
    assert result.epoch == 10 and result.witness_rank == 1
    assert result.pool_ranks.tolist() == [0, *range(2, 16)]
    assert len(opened) == 2
    assert "functional_assays/epoch_000011.npz" not in result.checksums


@pytest.mark.parametrize("damage", ["checksum", "missing", "pool", "reservoir", "witness", "rank", "epoch",
                                    "counter", "config", "assay_seed", "assay_score", "assay_order", "ledger",
                                    "manifest_origin", "streak", "earlier_origin", "csv_witness"])
def test_corrupt_artifacts_fail_closed(run_dir: Path, damage: str) -> None:
    name = "origin_checkpoint.npz"
    if damage == "checksum":
        with (run_dir / name).open("ab") as handle:
            handle.write(b"corruption")
    elif damage == "missing":
        (run_dir / name).unlink()
    elif damage in {"pool", "reservoir", "witness", "rank", "epoch", "counter", "config"}:
        with np.load(run_dir / name, allow_pickle=False) as saved:
            arrays = dict(saved)
        if damage == "pool":
            arrays["pool"][0] += 1
        elif damage == "reservoir":
            arrays["pool"][0] += 1
            arrays["conserved_totals"][0] += 1
        elif damage == "witness":
            arrays["witness"][0] ^= 1
        elif damage == "rank":
            arrays["witness_rank"][0] = 2
        elif damage == "epoch":
            arrays["local_epoch"][0] = 11
        elif damage == "counter":
            arrays["changing_write_counter"][0] += 1
        else:
            arrays["config_json"] = np.array(["{}"])
        np.savez_compressed(run_dir / name, **arrays)
        rehash(run_dir, name)
    elif damage.startswith("assay_"):
        name = "functional_assays/epoch_000010.npz"
        with np.load(run_dir / name, allow_pickle=False) as saved:
            arrays = dict(saved)
        if damage == "assay_seed":
            arrays["evaluator_seed"][0] = 1
        elif damage == "assay_score":
            arrays["scores"][2] = 3
        else:
            arrays["candidates"] = arrays["candidates"][::-1]
        np.savez_compressed(run_dir / name, **arrays)
        rehash(run_dir, name)
    elif damage == "manifest_origin":
        path = run_dir / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["functional_origin_epoch"] = 11
        path.write_text(json.dumps(manifest))
    else:
        name = "symbols.csv" if damage == "ledger" else "aggregate.csv" if damage in {"streak", "earlier_origin"} else "functional_scores.csv"
        frame = pd.read_csv(run_dir / name)
        if damage == "ledger":
            frame.loc[frame.epoch == 10, "returns"] += 1
        elif damage == "streak":
            frame.loc[0, "functional_entropy_streak"] = 10
        elif damage == "earlier_origin":
            frame.loc[0, "functional_origin_qualified"] = True
        else:
            frame.loc[0, "witness_hex"] = "00" * 64
        frame.to_csv(run_dir / name, index=False)
        rehash(run_dir, name)
    with pytest.raises((ValueError, OSError)):
        ac.load_checkpoint(run_dir, ac.RUNS[0])


def test_original_rank_replay_uses_full_assay(monkeypatch: pytest.MonkeyPatch) -> None:
    from experiments import paper_probe
    candidates = checkpoint().candidates
    scores = np.array([0, 64, 63], dtype=np.int64)
    calls: list[tuple[ac.U8, int]] = []

    def evaluator(tapes: ac.U8, seed: int) -> ac.I64:
        calls.append((tapes, seed))
        return scores.copy()

    monkeypatch.setattr(paper_probe, "score_selfrep_candidates", evaluator)
    ac.verify_scores(candidates, scores)
    assert calls[0][0] is candidates and calls[0][1] == 0
    with pytest.raises(ValueError, match="evaluator"):
        ac.verify_scores(candidates, np.array([0, 63, 64], dtype=np.int64))


def test_missing_checkpoint_unevaluable_and_deterministic_outputs(tmp_path: Path) -> None:
    rows, checkpoints, result = ac.analyze(tmp_path / "missing1", tmp_path / "missing2")
    assert result["decision"] == "UNEVALUABLE" and len(result["errors"]) == 11
    assert result["replacement_sensitivity"]["decision"] == "UNEVALUABLE"
    for output in (tmp_path / "a", tmp_path / "b"):
        ac.write_outputs(rows, checkpoints, result, output)
    assert {p.name: p.read_bytes() for p in (tmp_path / "a").iterdir()} == {
        p.name: p.read_bytes() for p in (tmp_path / "b").iterdir()}
    assert "missing evidence is not structural diversity" in (tmp_path / "a" / "report.md").read_text()


def test_successful_outputs_include_all_descriptive_witnesses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ac, "load_checkpoint", lambda root, run: checkpoint(ac.RUNS.index(run)))
    rows, checkpoints, result = ac.analyze(tmp_path, tmp_path)
    ac.write_outputs(rows, checkpoints, result, tmp_path / "out")
    assert result["decision"] == "PASS"
    matrix = pd.read_csv(tmp_path / "out" / "hamming_matrix.csv", index_col=0)
    assert matrix.shape == (11, 11)
    witnesses = pd.read_csv(tmp_path / "out" / "witnesses.csv")
    assert len(witnesses) == 11
    assert "symbol_0_share" in witnesses
    assert json.loads((tmp_path / "out" / "decision.json").read_text()) == result
    ac.write_outputs(rows, checkpoints, result, tmp_path / "repeat")
    assert {p.name: p.read_bytes() for p in (tmp_path / "out").iterdir()} == {
        p.name: p.read_bytes() for p in (tmp_path / "repeat").iterdir()}
    # An incomplete rerun must not leave matrices from a previous successful run.
    ac.write_outputs(rows, [], result, tmp_path / "out")
    assert (tmp_path / "out" / "hamming_matrix.csv").read_text() == "run\n"


def test_effect_and_tail_thresholds_are_inclusive(monkeypatch: pytest.MonkeyPatch) -> None:
    checkpoints = [checkpoint(i) for i in ac.PRIMARY]
    # Eight shared signatures must suffice; the two outsiders cannot create a pass.
    for c in checkpoints[:2]:
        c.candidates[0, 0] = ord("-")
    h = np.full((10, 10), 0.75)
    np.fill_diagonal(h, 0)
    monkeypatch.setattr(ac, "pairwise", lambda _: (h, h.copy()))
    reference = np.ones(10000)
    reference[:99] = 0.75
    monkeypatch.setattr(ac, "reference_medians", lambda _: (reference, reference.copy()))
    assert ac.evaluate(checkpoints, True)["decision"] == "PASS"
    reference[99] = 0.75
    result = ac.evaluate(checkpoints, True)
    assert result["decision"] == "VALID NON-PASS"
    assert not result["gates"]["hamming_tail"]
    reference[99] = 1
    h[h > 0] = 0.750001
    assert not ac.evaluate(checkpoints, True)["gates"]["hamming_effect"]


def test_replacement_integrity_required_but_its_pool_is_sensitivity_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def load(root: Path, run: ac.Run) -> ac.Checkpoint:
        return checkpoint(ac.RUNS.index(run), empty=run == ac.RUNS[9])

    monkeypatch.setattr(ac, "load_checkpoint", load)
    monkeypatch.setattr(ac, "reference_medians", lambda _: (np.ones(10000), np.ones(10000)))
    _, _, result = ac.analyze(tmp_path, tmp_path)
    assert result["decision"] == "PASS"
    assert result["replacement_sensitivity"]["decision"] == "UNEVALUABLE"
    assert result["replacement_sensitivity"]["empty_control_pools"] == [ac.RUNS[9].label]

    def broken(root: Path, run: ac.Run) -> ac.Checkpoint:
        if run == ac.RUNS[9]:
            raise ValueError("invalid replacement witness")
        return load(root, run)

    monkeypatch.setattr(ac, "load_checkpoint", broken)
    _, _, result = ac.analyze(tmp_path, tmp_path)
    assert result["decision"] == "UNEVALUABLE"
    assert result["primary"]["all_eleven_integrity"] is False


def test_manifest_later_origin_rejected_before_payload_access(run_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = run_dir / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["functional_origin_epoch"] = 11
    path.write_text(json.dumps(manifest))

    def forbidden_load(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("must reject a later manifest origin before opening any payload")

    monkeypatch.setattr(np, "load", forbidden_load)
    with pytest.raises(ValueError, match="first qualifying origin"):
        ac.load_checkpoint(run_dir, ac.RUNS[0])
