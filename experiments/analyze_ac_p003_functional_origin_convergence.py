"""Frozen AC-P003 analysis (preregistration 46ea61b); no later assay payloads.

Checkpoint indices follow preregistration order after excluding the shared-seed
m2 run; sensitivity replaces its m16 counterpart in place. Replicates are
zero-based, arithmetic is uint64, and quantiles use linear interpolation.
Only the eleven specified run directories are accessed. Checksums cover the
checkpoint, first-origin assay and supporting config/CSV artifacts, not later
assay payloads. Saved scores remain authoritative; verification replays the
entire original candidate ordering with its original evaluator seed.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, cast
from zipfile import BadZipFile

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from experiments import analyze_ac_p001_high_resource_origin_viability as origin

U8 = NDArray[np.uint8]
I64 = NDArray[np.int64]
F64 = NDArray[np.float64]
MASK = (1 << 64) - 1
REPLICATES = 10_000
OPCODES = frozenset(b"<>{}-+.,[]")
SYMBOLS = (0, 44, 60, 91, 93, 125)
require = origin.require


@dataclass(frozen=True)
class Run:
    campaign: str
    multiplier: int
    seed: int

    @property
    def name(self) -> str:
        return f"p1_m{self.multiplier}_n32768_s{self.seed}_funcv1"

    @property
    def label(self) -> str:
        return f"{self.campaign}_m{self.multiplier}_s{self.seed}"


RUNS = tuple(
    [Run("AC-P001", 16, seed) for seed in (202612001, 202612003, 202612008, 202612009)]
    + [Run("AC-P002", 16, seed) for seed in (202613001, 202613008, 202613010, 202613013, 202613018)]
    + [Run("AC-P002", 2, seed) for seed in (202613013, 202613015)]
)
PRIMARY = (0, 1, 2, 3, 4, 5, 6, 7, 8, 10)
REPLACEMENT = (0, 1, 2, 3, 4, 5, 6, 9, 8, 10)


@dataclass
class Checkpoint:
    run: Run
    epoch: int
    candidates: U8
    abundances: I64
    scores: I64
    witness_rank: int
    pool_ranks: I64
    checksums: dict[str, str]

    @property
    def witness(self) -> U8:
        return cast(U8, self.candidates[self.witness_rank])


def splitmix64(value: int) -> int:
    """The paper_probe SplitMix64 function with explicit unsigned wraparound."""
    z = (value + 0x9E3779B97F4A7C15) & MASK
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
    return (z ^ (z >> 31)) & MASK


def reference_index(n: int, replicate: int, checkpoint: int) -> int:
    require(0 < n <= 1 << 64 and replicate >= 0 and 0 <= checkpoint < 10,
            "invalid reference draw arguments")
    base = 0xAC003 ^ splitmix64(replicate * 10 + checkpoint)
    limit = ((1 << 64) // n) * n
    k = 0
    while True:
        draw = splitmix64((base + k) & MASK)
        if draw < limit:
            return draw % n
        k += 1


def local_pool(scores: I64, witness_rank: int) -> I64:
    """Return original assay ranks, including the specified nearest-block tie rule."""
    require(scores.ndim == 1 and 0 <= witness_rank < len(scores), "invalid witness rank")
    require(bool(((scores >= 0) & (scores <= 64)).all()) and scores[witness_rank] == 64,
            "invalid local-pool scores")
    eligible = np.flatnonzero(scores < 64).astype(np.int64)
    if not len(eligible):
        return eligible
    block = witness_rank // 64
    selected = min(set((eligible // 64).tolist()), key=lambda other: (abs(other - block), other))
    return cast(I64, eligible[eligible // 64 == selected])


def opcode_signature(tape: U8) -> str:
    return bytes(int(byte) for byte in tape if int(byte) in OPCODES).decode("ascii")


def histograms(tapes: U8) -> F64:
    return np.asarray([np.bincount(tape, minlength=256) / 64 for tape in tapes], dtype=np.float64)


def jsd(p: F64, q: F64) -> F64:
    """Base-2 Jensen-Shannon divergence on the final axis, with 0 log 0 = 0."""
    midpoint = (p + q) / 2
    def term(a: F64) -> F64:
        ratio = np.divide(a, midpoint, out=np.ones_like(midpoint), where=midpoint > 0)
        logs = np.log2(ratio, out=np.zeros_like(midpoint), where=ratio > 0)
        return np.asarray(np.sum(a * logs, axis=-1), dtype=np.float64)
    return np.asarray((term(p) + term(q)) / 2, dtype=np.float64)


def pairwise(tapes: U8) -> tuple[F64, F64]:
    hamming = np.mean(tapes[:, None, :] != tapes[None, :, :], axis=-1)
    composition = histograms(tapes)
    return hamming, jsd(composition[:, None, :], composition[None, :, :])


def reference_medians(checkpoints: list[Checkpoint]) -> tuple[F64, F64]:
    require(len(checkpoints) == 10 and all(len(c.pool_ranks) for c in checkpoints),
            "reference requires ten nonempty pools")
    draws = np.asarray([[reference_index(len(c.pool_ranks), r, i) for i, c in enumerate(checkpoints)]
                        for r in range(REPLICATES)], dtype=np.int64)
    pools = [c.candidates[c.pool_ranks] for c in checkpoints]
    compositions = [histograms(pool) for pool in pools]
    hamming, composition = np.empty((REPLICATES, 45)), np.empty((REPLICATES, 45))
    pair = 0
    for i in range(10):
        for j in range(i + 1, 10):
            h = np.mean(pools[i][:, None, :] != pools[j][None, :, :], axis=-1)
            d = jsd(compositions[i][:, None, :], compositions[j][None, :, :])
            hamming[:, pair] = h[draws[:, i], draws[:, j]]
            composition[:, pair] = d[draws[:, i], draws[:, j]]
            pair += 1
    return np.median(hamming, axis=1), np.median(composition, axis=1)


def integer_array(array: NDArray[Any], shape: tuple[int, ...], name: str) -> None:
    require(array.shape == shape and np.issubdtype(array.dtype, np.integer)
            and (array >= 0).all(), f"invalid {name}")


def verify_scores(candidates: U8, scores: I64) -> None:
    from experiments.paper_probe import score_selfrep_candidates
    evaluator = cast(Callable[[U8, int], I64], score_selfrep_candidates)
    require(np.array_equal(evaluator(candidates, 0), scores), "original-rank evaluator scores mismatch")


def initial_histogram(seed: int) -> I64:
    from experiments.paper_probe import initialize_soup
    initialize = cast(Callable[[int, int], U8], initialize_soup)
    return np.asarray(np.bincount(initialize(origin.POPULATION, seed).ravel(), minlength=256), dtype=np.int64)


def load_checkpoint(root: Path, run: Run) -> Checkpoint:
    """Fail closed; decode just the authorized first-origin assay and checkpoint."""
    manifest = json.loads((root / "manifest.json").read_text())
    config = manifest["config"]
    origin.validate_config(config, pool_multiplier=run.multiplier, allowed_seeds={run.seed})
    require(manifest.get("status") == manifest.get("exit_status") == "success", "unsuccessful run")
    require(manifest.get("max_conservation_residual") == 0, "manifest conservation residual")
    epoch = manifest["functional_origin_epoch"]
    require(type(epoch) is int and 1 <= epoch <= origin.EPOCHS, "invalid first-origin epoch")
    assay_name = f"functional_assays/epoch_{epoch:06d}.npz"
    names = ("config.json", "aggregate.csv", "writes.csv", "symbols.csv", "functional_scores.csv",
             "origin_checkpoint.npz", assay_name)
    require(set(names[1:-1]) | {"functional_assays"} <= set(manifest["artifacts"]),
            "incomplete published artifact inventory")
    checksums: dict[str, str] = {}
    for name in names[:-2]:
        path = root / name
        require(path.resolve().is_relative_to(root.resolve()), "artifact outside run")
        digest = origin.sha256(path)
        require(digest == manifest["artifact_checksums"].get(name), f"checksum mismatch: {name}")
        checksums[name] = digest
    checksums["manifest.json"] = origin.sha256(root / "manifest.json")
    require(json.loads((root / "config.json").read_text()) == config, "config file mismatch")
    aggregate = pd.read_csv(root / "aggregate.csv")
    callbacks = sorted(set(range(1, origin.EPOCHS + 1, origin.CALLBACK)) | {origin.EPOCHS})
    require(aggregate["epoch"].tolist() == callbacks, "invalid callback schedule")
    require(aggregate["max_conservation_residual"].eq(0).all(), "aggregate conservation residual")
    prior = aggregate[aggregate.epoch <= epoch]
    require(len(prior) > 0 and prior.iloc[-1]["epoch"] == epoch, "origin is not a callback")
    streak = 0
    for row in prior.to_dict("records"):
        entropy = float(row["high_order_entropy"])
        require(np.isfinite(entropy), "nonfinite entropy")
        streak = streak + 1 if entropy >= 1 else 0
        require(row["functional_entropy_streak"] == streak, "incorrect entropy streak")
    eligible = prior[prior.functional_entropy_streak >= 10].epoch.tolist()
    require(np.array_equal(origin.bool_column(prior["functional_scoring_performed"]),
                           prior.epoch.isin(eligible)), "assay eligibility mismatch")
    # Read only metadata columns: later callback witness bytes are never decoded.
    metadata = ["epoch", "absolute_epoch", "entropy_streak", "candidate_count", "max_score",
                "score_64_count", "origin_qualified"]
    functional = pd.read_csv(root / "functional_scores.csv", usecols=metadata)
    functional = functional[functional.epoch <= epoch]
    require(functional.epoch.tolist() == eligible, "missing/extra first-origin callback assays")
    hits = functional.loc[origin.bool_column(functional.origin_qualified), "epoch"].tolist()
    require(hits and hits[0] == epoch, "manifest is not the first qualifying origin")
    require(prior.loc[origin.bool_column(prior.functional_origin_qualified), "epoch"].tolist() == [epoch],
            "aggregate first-origin mismatch")
    require(np.array_equal(origin.bool_column(functional.origin_qualified), functional.score_64_count > 0)
            and np.array_equal(functional.max_score == 64, functional.score_64_count > 0),
            "functional qualification metadata mismatch")
    scored = prior[prior.epoch.isin(eligible)]
    for key in ("candidate_count", "max_score", "score_64_count", "origin_qualified"):
        require(np.array_equal(functional[key], scored[f"functional_{key}"]),
                f"callback metadata mismatch: {key}")
    require(np.array_equal(functional.absolute_epoch, functional.epoch)
            and np.array_equal(functional.entropy_streak, scored.functional_entropy_streak),
            "callback epoch/streak metadata mismatch")
    unscored = prior[~prior.epoch.isin(eligible)]
    require(all(unscored[f"functional_{key}"].isna().all()
                for key in ("candidate_count", "max_score", "score_64_count")),
            "unscored callback has score metadata")
    a, f = prior.iloc[-1], functional.iloc[-1]
    require(f["absolute_epoch"] == epoch and f["entropy_streak"] == streak and streak >= 10,
            "origin epoch/streak mismatch")
    # Only after metadata establishes the first origin may its payloads be opened.
    for name in names[-2:]:
        path = root / name
        require(path.resolve().is_relative_to(root.resolve()), "artifact outside run")
        digest = origin.sha256(path)
        require(digest == manifest["artifact_checksums"].get(name), f"checksum mismatch: {name}")
        checksums[name] = digest
    require(checksums["origin_checkpoint.npz"] == manifest["origin_checkpoint_sha256"],
            "checkpoint published checksum mismatch")
    with np.load(root / assay_name, allow_pickle=False) as assay:
        candidates, counts, scores = assay["candidates"], assay["abundances"], assay["scores"]
        n = min(1024, int(a["distinct_tapes"]))
        require(n > 0 and candidates.dtype == np.uint8 and candidates.shape == (n, 64), "invalid candidates")
        integer_array(counts, (n,), "abundances")
        integer_array(scores, (n,), "scores")
        require((counts > 0).all() and (scores <= 64).all(), "invalid assay values")
        keys = [(-int(c), tape.tobytes()) for c, tape in zip(counts, candidates, strict=True)]
        require(keys == sorted(keys) and len({key[1] for key in keys}) == n, "candidate order/uniqueness")
        for key, value in (("evaluator_seed", 0), ("local_epoch", epoch), ("absolute_epoch", epoch),
                           ("observation_version", origin.SPEC["version"])):
            require(assay[key].tolist() == [value], f"assay {key} mismatch")
        qualified = np.flatnonzero(scores == 64)
        require(len(qualified) > 0, "no score-64 witness")
        witness_rank = int(qualified[0])
        for key, value in (("candidate_count", n), ("max_score", 64), ("score_64_count", len(qualified))):
            require(f[key] == a[f"functional_{key}"] == value, f"assay summary mismatch: {key}")
    # Stop the CSV reader at the first origin; do not load later witness strings.
    first_rows = pd.read_csv(root / "functional_scores.csv", nrows=len(functional), dtype={"witness_hex": str})
    witness_row = first_rows.iloc[-1]
    require(witness_row.witness_rank == witness_rank and witness_row.witness_abundance == counts[witness_rank]
            and witness_row.witness_hex == candidates[witness_rank].tobytes().hex(), "CSV witness mismatch")
    initial = initial_histogram(run.seed)
    symbols = pd.read_csv(root / "symbols.csv")
    symbols = symbols[symbols.epoch == epoch]
    require(symbols.symbol.tolist() == list(range(256)), "invalid origin symbol schedule")
    require(all(np.issubdtype(cast(np.dtype[Any], symbols[c].dtype), np.integer)
                and symbols[c].ge(0).all() for c in symbols), "invalid symbol counts")
    require(np.array_equal(symbols.initial_pool_count, initial * run.multiplier), "initial pool mismatch")
    require(np.array_equal(symbols.initial_pool_count + symbols.returns - symbols.withdrawals,
                           symbols.pool_count), "symbol conservation ledger mismatch")
    with np.load(root / "origin_checkpoint.npz", allow_pickle=False) as saved:
        require(saved["local_epoch"].tolist() == saved["absolute_epoch"].tolist() == [epoch],
                "checkpoint is not first origin")
        require(json.loads(str(saved["config_json"][0])) == config, "checkpoint config mismatch")
        soup, pool, totals = saved["soup"], saved["pool"], saved["conserved_totals"]
        require(soup.dtype == np.uint8 and soup.shape == (origin.POPULATION, 64), "invalid checkpoint soup")
        integer_array(pool, (256,), "checkpoint pool")
        integer_array(totals, (256,), "checkpoint totals")
        require(np.array_equal(totals, initial * (run.multiplier + 1)), "checkpoint initial reservoir mismatch")
        require(np.array_equal(np.bincount(soup.ravel(), minlength=256) + pool, totals), "checkpoint conservation")
        require(np.array_equal(pool, symbols.pool_count) and int(pool.sum()) == a.pool_total, "checkpoint pool ledger")
        for saved_key, symbol_key in (("withdrawals", "withdrawals"), ("returns", "returns"),
                                     ("execution_blocked_by_symbol", "execution_blocked"),
                                     ("mutation_blocked_by_symbol", "mutation_blocked"),
                                     ("friction_blocked_by_symbol", "friction_blocked"),
                                     ("cross_a_to_b", "cross_a_to_b"), ("cross_b_to_a", "cross_b_to_a")):
            integer_array(saved[saved_key], (256,), saved_key)
            require(np.array_equal(saved[saved_key], symbols[symbol_key]), f"checkpoint ledger: {saved_key}")
        cumulative_keys = ["character_reads", "cumulative_execution_writes_success",
                           "cumulative_execution_scarcity_blocked", "cumulative_execution_friction_blocked",
                           "cumulative_mutation_writes_success", "cumulative_mutation_scarcity_blocked",
                           "cumulative_mutation_friction_blocked", "cumulative_cross_tape_copy_success",
                           "cumulative_cross_tape_copy_blocked"]
        require(saved["cumulative"].tolist() == [int(a[k]) for k in cumulative_keys], "checkpoint cumulative counters")
        require(saved["changing_write_counter"].tolist() == [int(a.cumulative_changing_write_attempts)],
                "checkpoint changing counter")
        require(saved["entropy_streak"].tolist() == [streak], "checkpoint streak")
        values, abundance = np.unique(soup, axis=0, return_counts=True)
        order = np.argsort(-abundance, kind="stable")[:1024]
        require(len(values) == a.distinct_tapes and np.array_equal(values[order], candidates)
                and np.array_equal(abundance[order], counts), "checkpoint candidate mismatch")
        require(saved["witness_rank"].tolist() == [witness_rank] and saved["witness_score"].tolist() == [64]
                and saved["witness_abundance"].tolist() == [int(counts[witness_rank])]
                and saved["evaluator_seed"].tolist() == [0]
                and saved["witness"].dtype == np.uint8 and saved["witness"].shape == (64,)
                and np.array_equal(saved["witness"], candidates[witness_rank]), "checkpoint witness mismatch")
    verify_scores(candidates, scores)
    return Checkpoint(run, epoch, candidates, counts, scores, witness_rank, local_pool(scores, witness_rank), checksums)


def classes(checkpoints: list[Checkpoint], *, signatures: bool) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for checkpoint in checkpoints:
        key = opcode_signature(checkpoint.witness) if signatures else checkpoint.witness.tobytes().hex()
        grouped[key].append(checkpoint.run.label)
    return [{"value": key, "count": len(members), "members": members}
            for key, members in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))]


def evaluate(checkpoints: list[Checkpoint], integrity: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"order": [c.run.label for c in checkpoints], "decision": "UNEVALUABLE",
                              "all_eleven_integrity": integrity,
                              "empty_control_pools": [c.run.label for c in checkpoints if not len(c.pool_ranks)]}
    if not integrity or len(checkpoints) != 10 or any(not len(c.pool_ranks) for c in checkpoints):
        result["reason"] = "All eleven checkpoints must pass integrity; all analysis pools must be nonempty."
        return result
    tapes = np.stack([c.witness for c in checkpoints])
    h, d = pairwise(tapes)
    upper = np.triu_indices(10, 1)
    reference_h, reference_d = reference_medians(checkpoints)
    metrics: dict[str, Any] = {}
    for name, matrix, reference in (("hamming", h, reference_h), ("composition_jsd", d, reference_d)):
        observed = float(np.median(matrix[upper]))
        metrics[name] = {"observed_median": observed,
                         "reference_quantiles": dict(zip(("0.025", "0.5", "0.975"),
                                                         np.quantile(reference, [0.025, 0.5, 0.975], method="linear").tolist(), strict=True)),
                         "reference_tail_probability": (1 + int(np.count_nonzero(reference <= observed))) / (REPLICATES + 1)}
    signature_classes = classes(checkpoints, signatures=True)
    largest = max((row["count"] for row in signature_classes if row["value"]), default=0)
    null_median = metrics["hamming"]["reference_quantiles"]["0.5"]
    gates = {"integrity_and_controls": True, "signature_8_of_10": largest >= 8,
             "hamming_effect": null_median > 0 and metrics["hamming"]["observed_median"] <= 0.75 * null_median,
             "hamming_tail": metrics["hamming"]["reference_tail_probability"] <= 0.01}
    result.update(decision="PASS" if all(gates.values()) else "VALID NON-PASS", gates=gates,
                  metrics=metrics, signature_classes=signature_classes,
                  exact_tape_classes=classes(checkpoints, signatures=False), pair_count=45)
    return result


def analyze(p001_root: Path, p002_root: Path) -> tuple[list[dict[str, Any]], list[Checkpoint], dict[str, Any]]:
    loaded: dict[int, Checkpoint] = {}
    rows: list[dict[str, Any]] = []
    for i, run in enumerate(RUNS):
        row: dict[str, Any] = {"run": run.label, "integrity": False, "error": ""}
        try:
            checkpoint = load_checkpoint((p001_root if run.campaign == "AC-P001" else p002_root) / run.name, run)
            loaded[i] = checkpoint
            row.update(integrity=True, epoch=checkpoint.epoch, witness_rank=checkpoint.witness_rank,
                       abundance=int(checkpoint.abundances[checkpoint.witness_rank]),
                       pool_ranks=checkpoint.pool_ranks.tolist(), pool_size=len(checkpoint.pool_ranks),
                       witness_hex=checkpoint.witness.tobytes().hex(), signature=opcode_signature(checkpoint.witness),
                       structural_symbol_share=float(np.isin(checkpoint.witness, SYMBOLS).mean()),
                       **{f"symbol_{symbol}_share": float(np.mean(checkpoint.witness == symbol)) for symbol in SYMBOLS})
        except (OSError, ValueError, KeyError, TypeError, IndexError, BadZipFile) as error:
            row["error"] = f"{type(error).__name__}: {error}"
        rows.append(row)
    integrity = len(loaded) == 11
    primary = evaluate([loaded[i] for i in PRIMARY if i in loaded], integrity)
    replacement = evaluate([loaded[i] for i in REPLACEMENT if i in loaded], integrity)
    result = {"preregistration_commit": "46ea61b", "replicates": REPLICATES, "decision": primary["decision"],
              "primary": primary, "replacement_sensitivity": replacement,
              "checksum_scope": "Authorized origin checkpoint, first-origin assay, config and supporting CSVs only; later assay payloads not read.",
              "reference_interpretation": "Deterministic rank-local reference-tail probabilities; not general exchangeability-based significance.",
              "checksums": {c.run.label: c.checksums for c in loaded.values()},
              "errors": {row["run"]: row["error"] for row in rows if not row["integrity"]},
              "descriptive_signature_classes": classes(list(loaded.values()), signatures=True),
              "descriptive_exact_tape_classes": classes(list(loaded.values()), signatures=False)}
    return rows, list(loaded.values()), result


def write_outputs(rows: list[dict[str, Any]], checkpoints: list[Checkpoint], result: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output / "witnesses.csv", index=False)
    labels = [c.run.label for c in checkpoints]
    h, d = pairwise(np.stack([c.witness for c in checkpoints])) if checkpoints else (np.empty((0, 0)), np.empty((0, 0)))
    for name, matrix in (("hamming", h), ("composition_jsd", d)):
        pd.DataFrame(matrix, index=labels, columns=labels).to_csv(output / f"{name}_matrix.csv", index_label="run")
    (output / "decision.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    lines = ["# AC-P003 functional-origin static structural convergence", "", f"**{result['decision']}**", "",
             "Primary: ten distinct initializations; all eleven checkpoints required to pass integrity.",
             "Sensitivity replaces shared-seed m16 with m2 in the same checkpoint-index slot.", ""]
    for name in ("primary", "replacement_sensitivity"):
        analysis = result[name]
        lines += [f"{name}: **{analysis['decision']}**", ""]
        if "metrics" in analysis:
            for metric, values in analysis["metrics"].items():
                lines.append(f"- {metric}: observed median {values['observed_median']:.8g}; "
                             f"reference quantiles {values['reference_quantiles']}; "
                             f"reference-tail probability {values['reference_tail_probability']:.8g}")
            lines += [f"- {gate}: {passed}" for gate, passed in analysis["gates"].items()]
        else:
            lines.append(analysis["reason"])
            if analysis["empty_control_pools"]:
                lines.append("Empty below-64 pools: " + ", ".join(analysis["empty_control_pools"]) + ".")
        lines.append("")
    next_steps = {"PASS": "Preregister a fresh functional transplantation assay of the modal structural class against matched controls.",
                  "VALID NON-PASS": "The preregistered convergence criterion was not met. Stop convergence/class claims; this does not establish structural diversity.",
                  "UNEVALUABLE": "Repair only demonstrated artifact/implementation defects and rerun the frozen analysis; missing evidence is not structural diversity."}
    lines += [next_steps[result["decision"]], "", "Sensitivity cannot override the primary decision.",
              result["reference_interpretation"], result["checksum_scope"],
              "No resource effect, heredity, maintenance, adaptation, ecology, organization, or organism identity is established.", ""]
    lines += [f"- {run}: {error}" for run, error in result["errors"].items()]
    (output / "report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p001-root", type=Path, default=Path("sweeps/ac_p001_high_resource_origin_viability/runs"))
    parser.add_argument("--p002-root", type=Path, default=Path("sweeps/ac_p002_resource_abundance_origin/runs"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    # Prevent accidental artifact overwrites; generated reports belong outside run roots.
    for root in (args.p001_root, args.p002_root):
        require(not args.output_dir.resolve().is_relative_to(root.resolve()), "output must be outside run roots")
    rows, checkpoints, result = analyze(args.p001_root, args.p002_root)
    write_outputs(rows, checkpoints, result, args.output_dir)
    print(json.dumps({"decision": result["decision"], "errors": result["errors"]}, indent=2))


if __name__ == "__main__":
    main()
