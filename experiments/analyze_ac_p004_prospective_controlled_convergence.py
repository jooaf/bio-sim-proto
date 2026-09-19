"""Frozen AC-P004 analysis; seed order, original ranks, and linear quantiles.

All campaign artifacts are checksummed and validated using the AC-P001 validator.
Only first origins contribute; full original candidate sets are replayed before
control exclusion. A prior snapshot is the authoritative candidate set: no prior
full soup is persisted. Ordering, callback metadata, composition bounds, and
full-rank evaluator replay are checked, plus exact agreement with a separate
prior assay when present. No later-origin replacement or seed extension.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from zipfile import BadZipFile

import numpy as np
import pandas as pd

from experiments import analyze_ac_p001_high_resource_origin_viability as origin
from experiments import analyze_ac_p003_functional_origin_convergence as previous

U8 = previous.U8
I64 = previous.I64
F64 = previous.F64
require = origin.require
splitmix64 = previous.splitmix64
REPLICATES = 10_000
RUNS = tuple(previous.Run("AC-P004", 16, seed) for seed in range(202614000, 202614020))
CONTROL_SPEC = {"version": "pre-origin-control-v1", "snapshot": "immediately preceding scheduled callback",
                "candidate_order": "descending abundance; lexicographic stable ties",
                "candidate_limit": 1024, "evaluator_seed": 0}


@dataclass
class ControlledOrigin:
    checkpoint: previous.Checkpoint
    prior_epoch: int
    candidates: U8
    abundances: I64
    scores: I64
    pool_ranks: I64


def local_pool(scores: I64, witness_rank: int) -> I64:
    # The witness rank belongs to the ORIGIN assay and can exceed the prior size.
    require(scores.ndim == 1 and witness_rank >= 0 and
            np.issubdtype(scores.dtype, np.integer) and
            bool(((scores >= 0) & (scores <= 64)).all()), "invalid control scores/rank")
    eligible = np.flatnonzero(scores < 64).astype(np.int64)
    if not len(eligible):
        return eligible
    block = witness_rank // 64
    selected = min(set((eligible // 64).tolist()), key=lambda b: (abs(b - block), b))
    return cast(I64, eligible[eligible // 64 == selected])


def load_control(root: Path, checkpoint: previous.Checkpoint) -> ControlledOrigin:
    manifest = json.loads((root / "manifest.json").read_text())
    name = "pre_origin_control.npz"
    require(name in manifest["artifacts"], "control not published")
    digest = origin.sha256(root / name)
    require(digest == manifest.get("pre_origin_control_sha256") == manifest["artifact_checksums"].get(name),
            "control checksum mismatch")
    aggregate = pd.read_csv(root / "aggregate.csv")
    epochs = aggregate.epoch.tolist()
    index = epochs.index(checkpoint.epoch)
    require(index > 0, "no preceding callback")
    epoch = int(epochs[index - 1])
    with np.load(root / name, allow_pickle=False) as saved:
        for key, value in (("local_epoch", epoch), ("absolute_epoch", epoch),
                           ("origin_local_epoch", checkpoint.epoch), ("evaluator_seed", 0),
                           ("observation_version", origin.SPEC["version"]),
                           ("control_version", CONTROL_SPEC["version"])):
            require(saved[key].tolist() == [value], f"control {key} mismatch")
        candidates, counts, scores = saved["candidates"], saved["abundances"], saved["scores"]
        n = min(1024, int(aggregate.iloc[index - 1].distinct_tapes))
        require(n > 0 and candidates.dtype == np.uint8 and candidates.shape == (n, 64), "invalid control candidates")
        previous.integer_array(counts, (n,), "control abundances")
        previous.integer_array(scores, (n,), "control scores")
        require(bool((counts > 0).all()) and int(counts.sum()) <= origin.POPULATION
                and bool((scores <= 64).all()), "invalid control values")
        prior = aggregate.iloc[index - 1]
        omitted = int(prior.distinct_tapes) - n
        remaining = origin.POPULATION - int(counts.sum())
        require(int(counts[0]) == prior.dominant_tape_count and
                omitted <= remaining <= omitted * int(counts[-1]), "control abundance coverage mismatch")
        symbols = pd.read_csv(root / "symbols.csv")
        prior_symbols = symbols[symbols.epoch == epoch]
        composition = (previous.initial_histogram(checkpoint.run.seed) * (checkpoint.run.multiplier + 1)
                       - prior_symbols.pool_count.to_numpy())
        represented = np.zeros(256, dtype=np.int64)
        for tape, count in zip(candidates, counts, strict=True):
            represented += np.bincount(tape, minlength=256) * int(count)
        require(bool((represented <= composition).all()), "control composition exceeds conserved soup")
        keys = [(-int(c), t.tobytes()) for c, t in zip(counts, candidates, strict=True)]
        require(keys == sorted(keys) and len({k[1] for k in keys}) == n, "control order/uniqueness")
        # An independently persisted contemporaneous assay, when eligible, must
        # agree in every byte, abundance, and original-rank score.
        assay_path = root / "functional_assays" / f"epoch_{epoch:06d}.npz"
        if assay_path.exists():
            with np.load(assay_path, allow_pickle=False) as assay:
                require(all(np.array_equal(saved[k], assay[k]) for k in
                            ("candidates", "abundances", "scores", "local_epoch", "absolute_epoch",
                             "evaluator_seed", "observation_version")), "prior assay exactness mismatch")
        previous.verify_scores(candidates, scores)
    checkpoint.checksums[name] = digest
    return ControlledOrigin(checkpoint, epoch, candidates, counts, scores,
                            local_pool(scores, checkpoint.witness_rank))


def load_run(root: Path, run: previous.Run) -> ControlledOrigin | None:
    summary, _, _ = origin.summarize(root, allowed_seeds={run.seed})
    require(summary["integrity"], summary["error"])
    manifest = json.loads((root / "manifest.json").read_text())
    config = manifest["config"]
    require(config.get("prospective_control_observation") is True and
            config.get("prospective_control_spec") == CONTROL_SPEC, "prospective config mismatch")
    present = (root / "pre_origin_control.npz").exists()
    require(present == bool(summary["origin"]), "control presence mismatch")
    if not summary["origin"]:
        require("pre_origin_control_sha256" not in manifest and
                "pre_origin_control.npz" not in manifest["artifacts"], "unexpected control metadata")
        return None
    return load_control(root, previous.load_checkpoint(root, run))


def reference_index(size: int, replicate: int, checkpoint: int, n: int) -> int:
    require(0 < size <= 1 << 64 and replicate >= 0 and 6 <= n <= 20 and
            0 <= checkpoint < n, "invalid reference draw arguments")
    base = 0xAC004 ^ splitmix64(replicate * n + checkpoint)
    limit = ((1 << 64) // size) * size
    k = 0
    while True:
        draw = splitmix64((base + k) & previous.MASK)
        if draw < limit:
            return draw % size
        k += 1


def reference_medians(controls: list[ControlledOrigin]) -> tuple[F64, F64]:
    n = len(controls)
    require(6 <= n <= 20 and all(len(c.pool_ranks) for c in controls), "invalid reference pools")
    draws = np.asarray([[reference_index(len(c.pool_ranks), r, i, n) for i, c in enumerate(controls)]
                        for r in range(REPLICATES)], dtype=np.int64)
    pools = [c.candidates[c.pool_ranks] for c in controls]
    compositions = [previous.histograms(p) for p in pools]
    h, d = np.empty((REPLICATES, n * (n - 1) // 2)), np.empty((REPLICATES, n * (n - 1) // 2))
    pair = 0
    for i in range(n):
        for j in range(i + 1, n):
            distances = np.mean(pools[i][:, None, :] != pools[j][None, :, :], axis=-1)
            divergences = previous.jsd(compositions[i][:, None, :], compositions[j][None, :, :])
            h[:, pair] = distances[draws[:, i], draws[:, j]]
            d[:, pair] = divergences[draws[:, i], draws[:, j]]
            pair += 1
    return np.median(h, axis=1), np.median(d, axis=1)


def evaluate(controls: list[ControlledOrigin], integrity: bool) -> dict[str, Any]:
    usable = [c for c in controls if len(c.pool_ranks)]
    n = len(usable)
    result: dict[str, Any] = {"decision": "UNEVALUABLE", "all_twenty_integrity": integrity,
                              "usable_origins": n, "acquisition_gate": n >= 6,
                              "order": [c.checkpoint.run.label for c in usable]}
    if not integrity or n < 6:
        result["reason"] = "Run-level integrity failure." if not integrity else "Fewer than six usable origins; stop without a convergence claim or seed extension."
        return result
    checkpoints = [c.checkpoint for c in usable]
    require(len({c.run.seed for c in checkpoints}) == n, "duplicate initialization")
    matrices = previous.pairwise(np.stack([c.witness for c in checkpoints]))
    references = reference_medians(usable)
    metrics: dict[str, Any] = {}
    for name, matrix, reference in zip(("hamming", "composition_jsd"), matrices, references, strict=True):
        observed = float(np.median(matrix[np.triu_indices(n, 1)]))
        metrics[name] = {"observed_median": observed,
                         "reference_quantiles": dict(zip(("0.025", "0.5", "0.975"), np.quantile(reference, [0.025, 0.5, 0.975], method="linear").tolist(), strict=True)),
                         "reference_tail_probability": (1 + int(np.count_nonzero(reference <= observed))) / (REPLICATES + 1)}
    signatures = previous.classes(checkpoints, signatures=True)
    largest = max((c["count"] for c in signatures if c["value"]), default=0)
    null = metrics["hamming"]["reference_quantiles"]["0.5"]
    gates = {"all_twenty_integrity": integrity, "acquisition": n >= 6,
             "nonempty_signature_80_percent": largest >= (4 * n + 4) // 5,
             "hamming_effect": null > 0 and metrics["hamming"]["observed_median"] <= 0.75 * null,
             "hamming_tail": metrics["hamming"]["reference_tail_probability"] <= 0.01}
    result.update(decision="PASS" if all(gates.values()) else "VALID NON-PASS", gates=gates,
                  metrics=metrics, signature_classes=signatures,
                  exact_tape_classes=previous.classes(checkpoints, signatures=False), pair_count=n * (n - 1) // 2)
    return result


def analyze(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    controls = []
    for run in RUNS:
        row: dict[str, Any] = {"seed": run.seed, "integrity": False, "origin": None, "usable": False, "error": ""}
        try:
            control = load_run(root / (run.name + "_prectrlv1"), run)
            row.update(integrity=True, origin=control is not None)
            if control is not None:
                controls.append(control)
                c = control.checkpoint
                selected = int(control.pool_ranks[0] // 64) if len(control.pool_ranks) else None
                row.update(usable=bool(len(control.pool_ranks)), origin_epoch=c.epoch,
                           prior_epoch=control.prior_epoch, witness_rank=c.witness_rank,
                           witness_abundance=int(c.abundances[c.witness_rank]), witness_hex=c.witness.tobytes().hex(),
                           signature=previous.opcode_signature(c.witness), witness_block=c.witness_rank // 64,
                           selected_block=selected, block_distance=abs(selected - c.witness_rank // 64) if selected is not None else None,
                           pool_ranks=control.pool_ranks.tolist(), pool_size=len(control.pool_ranks),
                           prior_score64_count=int(np.count_nonzero(control.scores == 64)),
                           **{f"symbol_{symbol}_share": float(np.mean(c.witness == symbol)) for symbol in previous.SYMBOLS},
                           structural_symbol_share=float(np.isin(c.witness, previous.SYMBOLS).mean()))
        except (OSError, ValueError, KeyError, TypeError, IndexError, EOFError, BadZipFile) as error:
            row["error"] = f"{type(error).__name__}: {error}"
        rows.append(row)
    result = evaluate(controls, all(r["integrity"] for r in rows))
    result.update(campaign="AC-P004", replicates=REPLICATES, expected_runs=20,
                  origins=sum(r["origin"] is True for r in rows),
                  errors={str(r["seed"]): r["error"] for r in rows if r["error"]},
                  checksums={c.checkpoint.run.label: c.checkpoint.checksums for c in controls},
                  reference_interpretation="Conditional on the frozen local-control model; not general exchangeability-based significance.")
    return rows, result


def write_outputs(rows: list[dict[str, Any]], result: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output / "runs.csv", index=False, float_format="%.17g", lineterminator="\n")
    (output / "decision.json").write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n")
    next_step = {"PASS": "Preregister a fresh transplantation experiment comparing the modal static class with prospectively matched below-64 tapes.",
                 "VALID NON-PASS": "The prospective convergence criterion was not met; stop structural-class claims.",
                 "UNEVALUABLE": "Repair only demonstrated implementation/artifact defects; no control substitution, seed extension, or threshold tuning."}
    details = []
    for name, metric in sorted(result.get("metrics", {}).items()):
        details.append(f"- {name}: median {metric['observed_median']:.8g}; reference quantiles "
                       f"{metric['reference_quantiles']}; lower-tail probability {metric['reference_tail_probability']:.8g}")
    details.extend(f"- {name}: {passed}" for name, passed in sorted(result.get("gates", {}).items()))
    (output / "report.md").write_text(f"# AC-P004\n\n**{result['decision']}**; {result['usable_origins']}/20 usable origins.\n\n"
                                     + result.get("reason", next_step[result["decision"]]) + "\n\n"
                                     + "\n".join(details) + "\n\n" + result["reference_interpretation"] + "\n\nNo outcome establishes heredity, maintenance, adaptation, organization, ecology, or organism identity.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=Path("sweeps/ac_p004_prospective_controlled_convergence/runs"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.resolve().is_relative_to(args.runs_root.resolve()) and
            not args.runs_root.resolve().is_relative_to(args.output_dir.resolve()), "output must be separate from run roots")
    rows, result = analyze(args.runs_root)
    write_outputs(rows, result, args.output_dir)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
