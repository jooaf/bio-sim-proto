"""Frozen AC-P005 held-out composition-convergence replication analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from zipfile import BadZipFile

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from experiments import analyze_ac_p003_functional_origin_convergence as structural
from experiments import analyze_ac_p004_prospective_controlled_convergence as prospective

RUNS = tuple(structural.Run("AC-P005", 16, seed) for seed in range(202615000, 202615020))
REPLICATES = 10_000
MASK = (1 << 64) - 1


def reference_index(size: int, replicate: int, checkpoint: int, n: int) -> int:
    structural.require(0 < size <= 1 << 64 and replicate >= 0 and 6 <= n <= 20
                       and 0 <= checkpoint < n, "invalid reference draw arguments")
    base = 0xAC005 ^ structural.splitmix64(replicate * n + checkpoint)
    limit = ((1 << 64) // size) * size
    k = 0
    while True:
        draw = structural.splitmix64((base + k) & MASK)
        if draw < limit:
            return draw % size
        k += 1


def reference_composition_medians(
    controls: list[prospective.ControlledOrigin],
) -> NDArray[np.float64]:
    n = len(controls)
    structural.require(6 <= n <= 20 and all(len(control.pool_ranks) for control in controls),
                       "invalid reference pools")
    draws = np.asarray([
        [reference_index(len(control.pool_ranks), replicate, index, n)
         for index, control in enumerate(controls)]
        for replicate in range(REPLICATES)
    ], dtype=np.int64)
    pools = [control.candidates[control.pool_ranks] for control in controls]
    compositions = [structural.histograms(pool) for pool in pools]
    distances = np.empty((REPLICATES, n * (n - 1) // 2))
    pair = 0
    for first in range(n):
        for second in range(first + 1, n):
            divergences = structural.jsd(
                compositions[first][:, None, :], compositions[second][None, :, :]
            )
            distances[:, pair] = divergences[draws[:, first], draws[:, second]]
            pair += 1
    return np.asarray(np.median(distances, axis=1), dtype=np.float64)


def evaluate(controls: list[prospective.ControlledOrigin], integrity: bool) -> dict[str, Any]:
    usable = [control for control in controls if len(control.pool_ranks)]
    n = len(usable)
    result: dict[str, Any] = {
        "decision": "UNEVALUABLE", "all_twenty_integrity": integrity,
        "usable_origins": n, "acquisition_gate": n >= 6,
        "order": [control.checkpoint.run.label for control in usable],
    }
    if not integrity or n < 6:
        result["reason"] = (
            "Run-level integrity failure." if not integrity
            else "Fewer than six usable origins; stop without a composition conclusion."
        )
        return result
    structural.require(
        len({control.checkpoint.run.seed for control in usable}) == n,
        "duplicate initialization",
    )
    witnesses = np.stack([control.checkpoint.witness for control in usable])
    matrix = structural.pairwise(witnesses)[1]
    observed = float(np.median(matrix[np.triu_indices(n, 1)]))
    reference = reference_composition_medians(usable)
    quantiles = dict(zip(
        ("0.025", "0.5", "0.975"),
        np.quantile(reference, [0.025, 0.5, 0.975], method="linear").tolist(),
        strict=True,
    ))
    probability = (1 + int(np.count_nonzero(reference <= observed))) / (REPLICATES + 1)
    gates = {
        "all_twenty_integrity": integrity,
        "acquisition": n >= 6,
        "positive_reference_median": quantiles["0.5"] > 0,
        "composition_effect": observed <= 0.99 * quantiles["0.5"],
        "composition_tail": probability <= 0.01,
    }
    result.update(
        decision="PASS" if all(gates.values()) else "VALID NON-PASS",
        gates=gates,
        observed_median=observed,
        reference_quantiles=quantiles,
        reference_tail_probability=probability,
        pair_count=n * (n - 1) // 2,
    )
    return result


def analyze(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    controls: list[prospective.ControlledOrigin] = []
    for run in RUNS:
        row: dict[str, Any] = {
            "seed": run.seed, "integrity": False, "origin": None,
            "usable": False, "error": "",
        }
        try:
            control = prospective.load_run(root / (run.name + "_prectrlv1"), run)
            row.update(integrity=True, origin=control is not None)
            if control is not None:
                controls.append(control)
                checkpoint = control.checkpoint
                selected = int(control.pool_ranks[0] // 64) if len(control.pool_ranks) else None
                row.update(
                    usable=bool(len(control.pool_ranks)), origin_epoch=checkpoint.epoch,
                    prior_epoch=control.prior_epoch, witness_rank=checkpoint.witness_rank,
                    witness_abundance=int(checkpoint.abundances[checkpoint.witness_rank]),
                    witness_hex=checkpoint.witness.tobytes().hex(),
                    pool_size=len(control.pool_ranks), selected_block=selected,
                    prior_score64_count=int(np.count_nonzero(control.scores == 64)),
                )
        except (OSError, ValueError, KeyError, TypeError, IndexError, EOFError, BadZipFile) as error:
            row["error"] = f"{type(error).__name__}: {error}"
        rows.append(row)
    result = evaluate(controls, all(row["integrity"] for row in rows))
    result.update(
        campaign="AC-P005", expected_runs=20, replicates=REPLICATES,
        origins=sum(row["origin"] is True for row in rows),
        errors={str(row["seed"]): row["error"] for row in rows if row["error"]},
        reference_interpretation=(
            "Conditional on the frozen immediate pre-origin local-control model; "
            "not a general exchangeability-based significance test."
        ),
    )
    return rows, result


def write_outputs(rows: list[dict[str, Any]], result: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output / "runs.csv", index=False, float_format="%.17g", lineterminator="\n")
    (output / "decision.json").write_text(
        json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    next_step = {
        "PASS": "Support bounded replicated composition-level convergence; any causal perturbation requires a new design.",
        "VALID NON-PASS": "Retain AC-P004's composition signal as exploratory only and stop convergence work.",
        "UNEVALUABLE": "Repair only demonstrated implementation/artifact defects; do not add seeds or controls.",
    }
    details = ""
    if "observed_median" in result:
        details = (
            f"- Observed median composition JSD: {result['observed_median']:.8g}\n"
            f"- Reference quantiles: {result['reference_quantiles']}\n"
            f"- Lower-tail reference probability: {result['reference_tail_probability']:.8g}\n"
            + "\n".join(
                f"- {gate}: {'PASS' if passed else 'FAIL'}"
                for gate, passed in sorted(result["gates"].items())
            ) + "\n"
        )
    (output / "report.md").write_text(
        f"# AC-P005 compositional convergence replication\n\n"
        f"**{result['decision']}**; {result['usable_origins']}/20 usable origins.\n\n"
        f"{next_step[result['decision']]}\n\n{details}\n"
        f"{result['reference_interpretation']}\n\n"
        "No structural class, heredity, maintenance, adaptation, organization, ecology, or organism identity is established.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=Path("sweeps/ac_p005_compositional_convergence/runs"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    rows, result = analyze(args.runs_root)
    write_outputs(rows, result, args.output_dir)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
