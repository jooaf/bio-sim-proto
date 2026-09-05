"""Analyze the preregistered matched continuous opcode-composition campaign."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run
from analysis.spatial import (
    bff_opcode_signature_snapshot,
    neighbor_bff_opcode_js_test,
)
from experiments.analyze_phase2_liveness_pilot import summarize_run
from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater
from experiments.stringmol.analyze_locality import paired_bootstrap_interval
from soup.config import Config


RADIUS = "world.interaction_radius"


def summarize_js_run(
    run_dir: Path,
    *,
    primary_permutations: int,
    secondary_permutations: int,
    analysis_seed: int,
) -> dict[str, Any]:
    """Return primary JS and frozen secondary/mechanical outcomes for one run."""

    config = Config.load(run_dir / "config.toml")
    summary = summarize_run(
        run_dir,
        dissolution_rate=config.dissolution.spontaneous_rate,
        reseed_rate=config.world.reseed_rate,
        permutations=secondary_permutations,
        analysis_seed=analysis_seed + 20_000,
    )
    data = load_run(run_dir)
    tapes = data.table("tapes")
    complete = tapes[tapes["full_bytes"].notna()]
    tick = int(cast(Any, complete["tick"].max()))
    snapshot = complete[complete["tick"] == tick].reset_index(drop=True)
    js_result = neighbor_bff_opcode_js_test(
        snapshot,
        width=config.world.width,
        height=config.world.height,
        permutations=primary_permutations,
        rng=np.random.default_rng(analysis_seed + config.run.seed),
    )
    ordered = bff_opcode_signature_snapshot(snapshot)
    counts = ordered["content_hash"].value_counts()
    summary.update(
        {
            "radius": config.world.interaction_radius,
            "primary_snapshot_tick": tick,
            "opcode_js_similarity": js_result.observed,
            "opcode_js_null_mean": js_result.null_mean,
            "opcode_js_excess": js_result.excess,
            "opcode_js_p": js_result.p_value,
            "opcode_js_edges": js_result.edges,
            "ordered_unique_fraction": float(len(counts) / len(ordered)),
            "ordered_singleton_tape_fraction": float(
                ordered["content_hash"].map(counts).eq(1).sum() / len(ordered)
            ),
            "js_mechanically_feasible": bool(
                summary["mechanically_feasible"]
                and float(summary["late_mean_occupied_fraction"]) >= 0.25
            ),
        }
    )
    return summary


def paired_results(runs: pd.DataFrame) -> tuple[np.ndarray[Any, np.dtype[np.float64]], float, float, float]:
    """Return radius-1-minus-radius-8 effects, exact p, and bootstrap limits."""

    pivot = runs.pivot(index="seed", columns="radius", values="opcode_js_excess")
    if 1 not in pivot.columns or 8 not in pivot.columns or len(pivot) != 10 or pivot.isna().any().any():
        raise ValueError("continuous campaign requires ten complete radius-1/radius-8 pairs")
    differences = (pivot[1] - pivot[8]).to_numpy(dtype=np.float64)
    p_value = exact_paired_sign_flip_greater(differences)
    lower, upper = paired_bootstrap_interval(
        differences,
        resamples=10_000,
        seed=20260905,
    )
    return differences, p_value, lower, upper


def treatment_summary(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate both radii without selecting a treatment."""

    return (
        runs.groupby("radius", sort=True)
        .agg(
            runs=("seed", "size"),
            feasible=("js_mechanically_feasible", "sum"),
            conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
            median_occupancy=("late_mean_occupied_fraction", "median"),
            mean_js_similarity=("opcode_js_similarity", "mean"),
            mean_js_null=("opcode_js_null_mean", "mean"),
            mean_js_excess=("opcode_js_excess", "mean"),
            median_within_run_p=("opcode_js_p", "median"),
            positive_js_excess=("opcode_js_excess", lambda values: int((values > 0).sum())),
            mean_byte_excess=("neighbor_byte_identity_excess", "mean"),
            mean_ordered_beta8_excess=("opcode_q1_beta_excess", "mean"),
            mean_unique_fraction=("ordered_unique_fraction", "mean"),
            mean_singleton_fraction=("ordered_singleton_tape_fraction", "mean"),
        )
        .reset_index()
    )


def write_report(runs: pd.DataFrame, groups: pd.DataFrame, target: Path) -> None:
    """Apply the frozen continuous-locality decision and report all pairs."""

    differences, p_value, lower, upper = paired_results(runs)
    positives = int(np.count_nonzero(differences > 0.0))
    feasible_by_radius = runs.groupby("radius")["js_mechanically_feasible"].sum()
    supported = bool(
        float(differences.mean()) > 0.0
        and lower > 0.0
        and p_value <= 0.05
        and positives >= 8
        and int(feasible_by_radius.loc[1]) >= 8
        and int(feasible_by_radius.loc[8]) >= 8
    )
    lines = [
        "# Phase 2 continuous opcode-composition locality follow-up",
        "",
        "## Decision",
        "",
        f"Preregistered continuous locality result supported: **{supported}**.",
        "",
        f"- Mean radius-1-minus-radius-8 JS-excess effect: {float(differences.mean()):.6f}",
        f"- Median paired effect: {float(np.median(differences)):.6f}",
        f"- 95% paired bootstrap interval: [{lower:.6f}, {upper:.6f}]",
        f"- Exact one-sided sign-flip p: {p_value:.6f}",
        f"- Positive matched effects: {positives}/10",
        f"- Mechanically feasible radius-1 runs: {int(feasible_by_radius.loc[1])}/10",
        f"- Mechanically feasible radius-8 runs: {int(feasible_by_radius.loc[8])}/10",
        "",
        "This follow-up cannot retroactively pass the frozen Phase 2 opcode-beta gate.",
        "",
        "## Radius summary",
        "",
        "| radius | feasible | mean JS | null mean | mean excess | median within-run p | positive excess | byte excess | ordered beta-8 excess | unique fraction | singleton fraction |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    records = cast(list[dict[str, Any]], groups.to_dict(orient="records"))
    for row in records:
        lines.append(
            f"| {int(row['radius'])} | {int(row['feasible'])}/{int(row['runs'])} | "
            f"{float(row['mean_js_similarity']):.6f} | {float(row['mean_js_null']):.6f} | "
            f"{float(row['mean_js_excess']):.6f} | {float(row['median_within_run_p']):.3f} | "
            f"{int(row['positive_js_excess'])}/{int(row['runs'])} | "
            f"{float(row['mean_byte_excess']):.6f} | "
            f"{float(row['mean_ordered_beta8_excess']):.6f} | "
            f"{float(row['mean_unique_fraction']):.3f} | "
            f"{float(row['mean_singleton_fraction']):.3f} |"
        )
    lines += [
        "",
        "## Matched effects",
        "",
        f"- {', '.join(f'{value:.6f}' for value in differences)}",
        "",
        "## Integrity",
        "",
        f"- Runs: {len(runs)}",
        f"- Successful exits: {int(runs['successful_exit'].sum())}/{len(runs)}",
        f"- Exactly conserved: {int(runs['conserved'].sum())}/{len(runs)}",
        f"- Invariant failures: {int(runs['invariant_failures'].sum())}",
        f"- Mechanically feasible: {int(runs['js_mechanically_feasible'].sum())}/{len(runs)}",
        "",
        "JS similarity measures graded instruction composition, including aggregate non-instruction density. It is not evidence of phenotype, lineage, or organism identity.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--primary-permutations", type=int, default=999)
    parser.add_argument("--secondary-permutations", type=int, default=199)
    parser.add_argument("--analysis-seed", type=int, default=20260905)
    parser.add_argument(
        "--runs-output", type=Path, default=Path("reports/phase2_opcode_js_followup_runs.csv")
    )
    parser.add_argument(
        "--groups-output", type=Path, default=Path("reports/phase2_opcode_js_followup_groups.csv")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("reports/phase2_opcode_js_followup_report.md")
    )
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", RADIUS}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"continuous campaign index missing columns: {sorted(missing)}")
    rows = [
        summarize_js_run(
            Path(str(row["run_dir"])),
            primary_permutations=args.primary_permutations,
            secondary_permutations=args.secondary_permutations,
            analysis_seed=args.analysis_seed,
        )
        for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))
    ]
    runs = pd.DataFrame(rows).sort_values(["radius", "seed"], ignore_index=True)
    if len(runs) != 20 or runs.groupby("radius")["seed"].nunique().min() != 10:
        raise ValueError("continuous campaign requires two complete ten-seed cells")
    groups = treatment_summary(runs)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    groups.to_csv(args.groups_output, index=False)
    write_report(runs, groups, args.report)
    print(args.runs_output)
    print(args.groups_output)
    print(args.report)


if __name__ == "__main__":
    main()
