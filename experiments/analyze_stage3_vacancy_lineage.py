"""Analyze the preregistered vacancy-controlled lineage-patch campaign."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater
from experiments.analyze_stage3r_lineage_patch import summarize_patch_run
from experiments.stringmol.analyze_locality import paired_bootstrap_interval


PLACEMENT_RADIUS = "reproduction.placement_radius"


def summarize_groups(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate mechanics and descriptive lineage outcomes by radius."""

    groups = (
        runs.groupby("placement_radius", sort=True)
        .agg(
            runs=("seed", "size"),
            feasible=("lineage_patch_feasible", "sum"),
            median_births=("reproductive_births", "median"),
            attempts=("reproduction_attempts_observed", "sum"),
            no_parent_blocks=("reproduction_blocked_no_parent", "sum"),
            pool_blocks=("reproduction_blocked_pool", "sum"),
            median_depth=("max_lineage_depth", "median"),
            median_occupancy=("late_mean_occupied_fraction", "median"),
            mean_family_excess=("family_neighbor_excess", "mean"),
            significant_family=("family_neighbor_p", lambda values: int((values <= 0.05).sum())),
            mean_root_excess=("root_neighbor_excess", "mean"),
            mean_descendant_fraction=("live_reproductive_descendant_fraction", "mean"),
            mean_family_q1=("neutral_family_q1", "mean"),
            mean_opcode_js_excess=("opcode_js_excess", "mean"),
            conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
        )
        .reset_index()
    )
    groups["no_parent_fraction"] = groups["no_parent_blocks"] / groups[
        "attempts"
    ].clip(lower=1)
    return groups


def paired_effects(
    runs: pd.DataFrame,
) -> tuple[np.ndarray[Any, np.dtype[np.float64]], float, float, float]:
    """Return frozen paired family-excess inference."""

    pivot = runs.pivot(
        index="seed", columns="placement_radius", values="family_neighbor_excess"
    )
    if 1 not in pivot.columns or 8 not in pivot.columns or len(pivot) != 10:
        raise ValueError("vacancy lineage campaign requires ten complete pairs")
    differences = (pivot[1] - pivot[8]).to_numpy(dtype=np.float64)
    p_value = exact_paired_sign_flip_greater(differences)
    lower, upper = paired_bootstrap_interval(
        differences, resamples=10_000, seed=20260913
    )
    return differences, p_value, lower, upper


def passes_gate(runs: pd.DataFrame, groups: pd.DataFrame) -> bool:
    """Apply every frozen confirmatory criterion."""

    differences, p_value, lower, _ = paired_effects(runs)
    births = groups.set_index("placement_radius")["median_births"]
    birth_ratio = float(births.min() / births.max()) if births.max() else 0.0
    return bool(
        float(differences.mean()) > 0.0
        and lower > 0.0
        and p_value <= 0.05
        and int(np.count_nonzero(differences > 0.0)) >= 8
        and len(runs) == 20
        and runs["successful_exit"].all()
        and runs["conserved"].all()
        and int(runs["invariant_failures"].sum()) == 0
        and (groups["feasible"] >= 8).all()
        and (groups["median_births"] >= 100).all()
        and birth_ratio >= 0.90
        and (groups["no_parent_fraction"] <= 0.02).all()
        and int(groups["pool_blocks"].sum()) == 0
    )


def write_report(runs: pd.DataFrame, groups: pd.DataFrame, target: Path) -> None:
    """Write the frozen placement decision and declared secondary outcomes."""

    differences, p_value, lower, upper = paired_effects(runs)
    births = groups.set_index("placement_radius")["median_births"]
    birth_ratio = float(births.min() / births.max()) if births.max() else 0.0
    lines = [
        "# Stage 3 vacancy-controlled lineage-patch result",
        "",
        "## Decision",
        "",
        f"Preregistered vacancy-controlled placement effect supported: **{passes_gate(runs, groups)}**.",
        "",
        f"- Mean radius-1 minus radius-8 family-neighbor excess: {float(differences.mean()):.6f}",
        f"- Median paired effect: {float(np.median(differences)):.6f}",
        f"- 95% paired bootstrap interval: [{lower:.6f}, {upper:.6f}]",
        f"- Exact one-sided sign-flip p: {p_value:.6f}",
        f"- Positive effects: {int(np.count_nonzero(differences > 0.0))}/10",
        f"- Median-birth ratio: {birth_ratio:.3f}",
        "",
        "| radius | feasible | births | attempts | no-parent | fraction | pool blocks | family excess | significant | root excess | descendants | depth | opcode JS | occupancy |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(
            f"| {int(row['placement_radius'])} | {int(row['feasible'])}/{int(row['runs'])} | "
            f"{float(row['median_births']):.0f} | {int(row['attempts'])} | "
            f"{int(row['no_parent_blocks'])} | {float(row['no_parent_fraction']):.4f} | "
            f"{int(row['pool_blocks'])} | {float(row['mean_family_excess']):.6f} | "
            f"{int(row['significant_family'])}/{int(row['runs'])} | "
            f"{float(row['mean_root_excess']):.6f} | {float(row['mean_descendant_fraction']):.3f} | "
            f"{float(row['median_depth']):.1f} | {float(row['mean_opcode_js_excess']):.6f} | "
            f"{float(row['median_occupancy']):.3f} |"
        )
    lines += [
        "",
        "## Matched effects",
        "",
        f"- {', '.join(f'{value:.6f}' for value in differences)}",
        "",
        "## Integrity",
        "",
        f"- Successful: {int(runs['successful_exit'].sum())}/{len(runs)}",
        f"- Conserved: {int(runs['conserved'].sum())}/{len(runs)}",
        f"- Invariant failures: {int(runs['invariant_failures'].sum())}",
        "",
        "Scheduled birth remains exogenous. Neutral families are measurement labels, not organisms.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--permutations", type=int, default=999)
    parser.add_argument("--analysis-seed", type=int, default=20260913)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage3_vacancy_lineage_runs.csv"))
    parser.add_argument("--groups-output", type=Path, default=Path("reports/stage3_vacancy_lineage_groups.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage3_vacancy_lineage_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", PLACEMENT_RADIUS}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"vacancy lineage index missing columns: {sorted(missing)}")
    runs = pd.DataFrame(
        [
            summarize_patch_run(
                Path(str(row["run_dir"])),
                permutations=args.permutations,
                analysis_seed=args.analysis_seed,
            )
            for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))
        ]
    ).sort_values(["placement_radius", "seed"], ignore_index=True)
    if len(runs) != 20 or runs.groupby("placement_radius")["seed"].nunique().min() != 10:
        raise ValueError("vacancy lineage campaign requires two complete ten-seed cells")
    groups = summarize_groups(runs)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    groups.to_csv(args.groups_output, index=False)
    write_report(runs, groups, args.report)
    print(args.runs_output)
    print(args.groups_output)
    print(args.report)


if __name__ == "__main__":
    main()
