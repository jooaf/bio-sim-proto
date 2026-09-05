"""Analyze the preregistered 50,000-tick opcode-composition campaign."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run
from analysis.spatial import (
    neighbor_bff_opcode_js_test,
    pooled_neighbor_bff_opcode_js_test,
)
from experiments.analyze_phase2_liveness_pilot import summarize_run
from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater
from experiments.stringmol.analyze_locality import paired_bootstrap_interval
from soup.config import Config


RADIUS = "world.interaction_radius"


def summarize_temporal_run(
    run_dir: Path,
    *,
    primary_permutations: int,
    diagnostic_permutations: int,
    analysis_seed: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Return pooled final-window outcomes and all full-snapshot diagnostics."""

    config = Config.load(run_dir / "config.toml")
    summary = summarize_run(
        run_dir,
        dissolution_rate=config.dissolution.spontaneous_rate,
        reseed_rate=config.world.reseed_rate,
        permutations=19,
        analysis_seed=analysis_seed + 30_000,
    )
    data = load_run(run_dir)
    tapes = data.table("tapes")
    complete = tapes[tapes["full_bytes"].notna()]
    snapshots = [
        (int(cast(Any, tick)), snapshot.reset_index(drop=True))
        for tick, snapshot in complete.groupby("tick", sort=True)
    ]
    final_start = int(np.floor(config.run.n_ticks * 0.9))
    final_snapshots = [snapshot for tick, snapshot in snapshots if tick >= final_start]
    if len(final_snapshots) != 10:
        raise ValueError(
            f"expected ten final-window full snapshots, found {len(final_snapshots)}"
        )
    pooled = pooled_neighbor_bff_opcode_js_test(
        final_snapshots,
        width=config.world.width,
        height=config.world.height,
        permutations=primary_permutations,
        rng=np.random.default_rng(analysis_seed + config.run.seed),
    )
    trajectory_rows: list[dict[str, Any]] = []
    for tick, snapshot in snapshots:
        result = neighbor_bff_opcode_js_test(
            snapshot,
            width=config.world.width,
            height=config.world.height,
            permutations=diagnostic_permutations,
            rng=np.random.default_rng(analysis_seed + config.run.seed + tick),
        )
        trajectory_rows.append(
            {
                "run_dir": str(run_dir),
                "seed": config.run.seed,
                "radius": config.world.interaction_radius,
                "tick": tick,
                "window": "final" if tick >= final_start else "earlier",
                "observed": result.observed,
                "null_mean": result.null_mean,
                "excess": result.excess,
                "p_value": result.p_value,
            }
        )
    trajectory = pd.DataFrame(trajectory_rows)
    early = trajectory[trajectory["tick"] < config.run.n_ticks * 0.1]
    final = trajectory[trajectory["window"] == "final"]
    summary.update(
        {
            "radius": config.world.interaction_radius,
            "pooled_js_similarity": pooled.observed,
            "pooled_js_null_mean": pooled.null_mean,
            "pooled_js_excess": pooled.excess,
            "pooled_js_p": pooled.p_value,
            "pooled_snapshot_count": len(final_snapshots),
            "early_mean_js_excess": float(early["excess"].mean()),
            "final_mean_diagnostic_js_excess": float(final["excess"].mean()),
            "positive_final_snapshots": int((final["excess"] > 0.0).sum()),
            "temporal_mechanically_feasible": bool(
                summary["mechanically_feasible"]
                and float(summary["late_mean_occupied_fraction"]) >= 0.25
            ),
        }
    )
    return summary, trajectory


def paired_results(
    runs: pd.DataFrame,
) -> tuple[np.ndarray[Any, np.dtype[np.float64]], float, float, float]:
    """Return the frozen radius-1-minus-radius-8 pooled effects."""

    pivot = runs.pivot(index="seed", columns="radius", values="pooled_js_excess")
    if 1 not in pivot.columns or 8 not in pivot.columns or len(pivot) != 10 or pivot.isna().any().any():
        raise ValueError("temporal campaign requires ten complete matched pairs")
    differences = (pivot[1] - pivot[8]).to_numpy(dtype=np.float64)
    p_value = exact_paired_sign_flip_greater(differences)
    lower, upper = paired_bootstrap_interval(
        differences,
        resamples=10_000,
        seed=20260906,
    )
    return differences, p_value, lower, upper


def treatment_summary(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate both radii without selecting a treatment."""

    return (
        runs.groupby("radius", sort=True)
        .agg(
            runs=("seed", "size"),
            feasible=("temporal_mechanically_feasible", "sum"),
            conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
            median_occupancy=("late_mean_occupied_fraction", "median"),
            mean_pooled_js=("pooled_js_similarity", "mean"),
            mean_pooled_null=("pooled_js_null_mean", "mean"),
            mean_pooled_excess=("pooled_js_excess", "mean"),
            median_pooled_p=("pooled_js_p", "median"),
            mean_early_excess=("early_mean_js_excess", "mean"),
            mean_final_excess=("final_mean_diagnostic_js_excess", "mean"),
            positive_final_snapshots=("positive_final_snapshots", "mean"),
        )
        .reset_index()
    )


def checkpoint_contrasts(trajectory: pd.DataFrame) -> pd.DataFrame:
    """Return mean matched radius contrasts at each relative checkpoint."""

    pivot = trajectory.pivot(index=["seed", "tick"], columns="radius", values="excess")
    if 1 not in pivot.columns or 8 not in pivot.columns:
        raise ValueError("trajectory lacks both radius treatments")
    paired = (pivot[1] - pivot[8]).rename("paired_effect").reset_index()
    return (
        paired.groupby("tick", sort=True)
        .agg(
            mean_paired_effect=("paired_effect", "mean"),
            positive_seed_pairs=("paired_effect", lambda values: int((values > 0).sum())),
        )
        .reset_index()
    )


def write_report(
    runs: pd.DataFrame,
    groups: pd.DataFrame,
    checkpoints: pd.DataFrame,
    target: Path,
) -> None:
    """Apply the frozen persistence criteria and report temporal diagnostics."""

    differences, p_value, lower, upper = paired_results(runs)
    positives = int(np.count_nonzero(differences > 0.0))
    feasible = runs.groupby("radius")["temporal_mechanically_feasible"].sum()
    supported = bool(
        float(differences.mean()) > 0.0
        and lower > 0.0
        and p_value <= 0.05
        and positives >= 8
        and int(feasible.loc[1]) >= 8
        and int(feasible.loc[8]) >= 8
    )
    final_checkpoints = checkpoints[checkpoints["tick"] >= 45_000]
    positive_final_checkpoints = int((final_checkpoints["mean_paired_effect"] > 0.0).sum())
    lines = [
        "# Long-horizon opcode-composition locality result",
        "",
        "## Decision",
        "",
        f"Preregistered 50,000-tick temporal-persistence result supported: **{supported}**.",
        "",
        f"- Mean paired pooled-JS effect: {float(differences.mean()):.6f}",
        f"- Median paired effect: {float(np.median(differences)):.6f}",
        f"- 95% paired bootstrap interval: [{lower:.6f}, {upper:.6f}]",
        f"- Exact one-sided sign-flip p: {p_value:.6f}",
        f"- Positive seed effects: {positives}/10",
        f"- Positive mean final-window checkpoint contrasts: {positive_final_checkpoints}/{len(final_checkpoints)}",
        f"- Mechanically feasible: radius 1 = {int(feasible.loc[1])}/10; radius 8 = {int(feasible.loc[8])}/10",
        "",
        "This result cannot retroactively alter the categorical Phase 2 acceptance NO-GO.",
        "",
        "## Radius summary",
        "",
        "| radius | feasible | pooled JS | pooled null | pooled excess | median p | early excess | final excess | positive final snapshots/run | occupancy |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    records = cast(list[dict[str, Any]], groups.to_dict(orient="records"))
    for row in records:
        lines.append(
            f"| {int(row['radius'])} | {int(row['feasible'])}/{int(row['runs'])} | "
            f"{float(row['mean_pooled_js']):.6f} | {float(row['mean_pooled_null']):.6f} | "
            f"{float(row['mean_pooled_excess']):.6f} | {float(row['median_pooled_p']):.3f} | "
            f"{float(row['mean_early_excess']):.6f} | {float(row['mean_final_excess']):.6f} | "
            f"{float(row['positive_final_snapshots']):.1f}/10 | {float(row['median_occupancy']):.3f} |"
        )
    lines += [
        "",
        "## Matched pooled effects",
        "",
        f"- {', '.join(f'{value:.6f}' for value in differences)}",
        "",
        "## Integrity",
        "",
        f"- Runs: {len(runs)}",
        f"- Successful exits: {int(runs['successful_exit'].sum())}/{len(runs)}",
        f"- Exactly conserved: {int(runs['conserved'].sum())}/{len(runs)}",
        f"- Invariant failures: {int(runs['invariant_failures'].sum())}",
        f"- Mechanically feasible: {int(runs['temporal_mechanically_feasible'].sum())}/{len(runs)}",
        "",
        "JS similarity is a graded syntax-composition statistic. It does not establish phenotype, heredity, or organism identity.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--primary-permutations", type=int, default=999)
    parser.add_argument("--diagnostic-permutations", type=int, default=99)
    parser.add_argument("--analysis-seed", type=int, default=20260906)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/phase2_opcode_js_temporal_runs.csv"))
    parser.add_argument("--groups-output", type=Path, default=Path("reports/phase2_opcode_js_temporal_groups.csv"))
    parser.add_argument("--trajectory-output", type=Path, default=Path("reports/phase2_opcode_js_temporal_trajectory.csv"))
    parser.add_argument("--checkpoints-output", type=Path, default=Path("reports/phase2_opcode_js_temporal_checkpoints.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/phase2_opcode_js_temporal_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", RADIUS}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"temporal campaign index missing columns: {sorted(missing)}")
    outputs = [
        summarize_temporal_run(
            Path(str(row["run_dir"])),
            primary_permutations=args.primary_permutations,
            diagnostic_permutations=args.diagnostic_permutations,
            analysis_seed=args.analysis_seed,
        )
        for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))
    ]
    runs = pd.DataFrame([row for row, _ in outputs]).sort_values(["radius", "seed"], ignore_index=True)
    trajectory = pd.concat([frame for _, frame in outputs], ignore_index=True)
    if len(runs) != 20 or runs.groupby("radius")["seed"].nunique().min() != 10:
        raise ValueError("temporal campaign requires two complete ten-seed cells")
    groups = treatment_summary(runs)
    checkpoints = checkpoint_contrasts(trajectory)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    groups.to_csv(args.groups_output, index=False)
    trajectory.to_csv(args.trajectory_output, index=False)
    checkpoints.to_csv(args.checkpoints_output, index=False)
    write_report(runs, groups, checkpoints, args.report)
    for path in (args.runs_output, args.groups_output, args.trajectory_output, args.checkpoints_output, args.report):
        print(path)


if __name__ == "__main__":
    main()
