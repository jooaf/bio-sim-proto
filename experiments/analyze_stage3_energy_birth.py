"""Analyze the preregistered Stage 3 energy-funded birth campaign."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run
from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater
from experiments.analyze_stage3_energy_liveness import summarize as summarize_energy
from experiments.analyze_stage3r_reproduction_liveness import event_count, lineage_depth
from experiments.stringmol.analyze_locality import paired_bootstrap_interval


BIRTH_COST = "reproduction.birth_energy_cost"


def summarize(run_dir: Path) -> dict[str, Any]:
    """Return frozen birth, energy, lineage, and mechanical outcomes."""

    summary = summarize_energy(run_dir)
    data = load_run(run_dir)
    events = data.table("events")
    lineage = data.table("lineage")
    births = event_count(events, "offspring_born")
    blocked_energy = event_count(events, "reproduction_blocked_energy")
    blocked_pool = event_count(events, "reproduction_blocked_pool")
    summary.update(
        {
            "birth_energy_cost": data.config.reproduction.birth_energy_cost,
            "births": births,
            "blocked_energy": blocked_energy,
            "blocked_pool": blocked_pool,
            "max_lineage_depth": lineage_depth(lineage),
            "birth_mechanical_feasible": bool(
                summary["successful_exit"]
                and summary["conserved"]
                and int(summary["invariant_failures"]) == 0
                and float(summary["max_relative_energy_error"]) <= 1e-9
                and 0.40 <= float(summary["late_mean_occupied_fraction"]) <= 0.95
                and float(summary["late_active_interaction_fraction"]) > 0.0
                and int(summary["late_successful_writes"]) > 0
                and int(summary["late_pool_changes"]) > 0
            ),
        }
    )
    return summary


def paired_effects(
    runs: pd.DataFrame,
) -> tuple[np.ndarray[Any, np.dtype[np.float64]], float, float, float]:
    """Return cost-zero minus cost-five birth inference."""

    pivot = runs.pivot(index="seed", columns="birth_energy_cost", values="births")
    if 0.0 not in pivot.columns or 5.0 not in pivot.columns or len(pivot) != 10:
        raise ValueError("energy-birth campaign requires ten complete pairs")
    differences = (pivot[0.0] - pivot[5.0]).to_numpy(dtype=np.float64)
    p_value = exact_paired_sign_flip_greater(differences)
    lower, upper = paired_bootstrap_interval(
        differences, resamples=10_000, seed=20260915
    )
    return differences, p_value, lower, upper


def group_summary(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate treatment mechanics."""

    return (
        runs.groupby("birth_energy_cost", sort=True)
        .agg(
            runs=("seed", "size"),
            feasible=("birth_mechanical_feasible", "sum"),
            median_births=("births", "median"),
            energy_block_runs=("blocked_energy", lambda values: int((values > 0).sum())),
            energy_blocks=("blocked_energy", "sum"),
            pool_blocks=("blocked_pool", "sum"),
            median_depth=("max_lineage_depth", "median"),
            median_occupancy=("late_mean_occupied_fraction", "median"),
            median_tape_energy=("final_mean_tape_energy", "median"),
            median_dissipated=("dissipated_fraction", "median"),
            max_energy_error=("max_relative_energy_error", "max"),
            conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
        )
        .reset_index()
    )


def passes_gate(runs: pd.DataFrame, groups: pd.DataFrame) -> bool:
    """Apply all frozen energy-constraint criteria."""

    differences, p_value, lower, _ = paired_effects(runs)
    control = groups[groups["birth_energy_cost"] == 0.0].iloc[0]
    costly = groups[groups["birth_energy_cost"] == 5.0].iloc[0]
    control_births = float(cast(Any, control["median_births"]))
    costly_births = float(cast(Any, costly["median_births"]))
    return bool(
        float(differences.mean()) > 0.0
        and lower > 0.0
        and p_value <= 0.05
        and int(np.count_nonzero(differences > 0.0)) >= 8
        and int(cast(Any, costly["energy_block_runs"])) >= 8
        and control_births >= 50
        and 10 <= costly_births < 0.90 * control_births
        and len(runs) == 20
        and runs["successful_exit"].all()
        and runs["conserved"].all()
        and int(runs["invariant_failures"].sum()) == 0
        and (runs["max_relative_energy_error"] <= 1e-9).all()
        and runs["birth_mechanical_feasible"].all()
    )


def write_report(runs: pd.DataFrame, groups: pd.DataFrame, target: Path) -> None:
    """Write the frozen energy-funded birth decision."""

    differences, p_value, lower, upper = paired_effects(runs)
    lines = [
        "# Stage 3 energy-funded birth result",
        "",
        "## Decision",
        "",
        f"Preregistered energy constraint supported: **{passes_gate(runs, groups)}**.",
        "",
        f"- Mean cost-0 minus cost-5 births: {float(differences.mean()):.3f}",
        f"- Median paired effect: {float(np.median(differences)):.3f}",
        f"- 95% paired bootstrap interval: [{lower:.3f}, {upper:.3f}]",
        f"- Exact one-sided sign-flip p: {p_value:.6f}",
        f"- Positive effects: {int(np.count_nonzero(differences > 0.0))}/10",
        "",
        "| cost | feasible | births | blocked runs | blocks | pool blocks | depth | occupancy | tape energy | dissipated | energy error |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(
            f"| {float(row['birth_energy_cost']):g} | {int(row['feasible'])}/{int(row['runs'])} | "
            f"{float(row['median_births']):.0f} | {int(row['energy_block_runs'])}/{int(row['runs'])} | "
            f"{int(row['energy_blocks'])} | {int(row['pool_blocks'])} | "
            f"{float(row['median_depth']):.1f} | {float(row['median_occupancy']):.3f} | "
            f"{float(row['median_tape_energy']):.3f} | {float(row['median_dissipated']):.3f} | "
            f"{float(row['max_energy_error']):.3e} |"
        )
    lines += [
        "",
        "## Paired effects",
        "",
        f"- {', '.join(f'{value:.0f}' for value in differences)}",
        "",
        "Scheduled births remain exogenous; this test concerns energetic constraint only.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage3_energy_birth_runs.csv"))
    parser.add_argument("--groups-output", type=Path, default=Path("reports/stage3_energy_birth_groups.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage3_energy_birth_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", BIRTH_COST}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"energy-birth index missing columns: {sorted(missing)}")
    runs = pd.DataFrame(
        [
            summarize(Path(str(row["run_dir"])))
            for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))
        ]
    ).sort_values(["birth_energy_cost", "seed"], ignore_index=True)
    if len(runs) != 20 or runs.groupby("birth_energy_cost")["seed"].nunique().min() != 10:
        raise ValueError("energy-birth campaign requires two complete ten-seed cells")
    groups = group_summary(runs)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    groups.to_csv(args.groups_output, index=False)
    write_report(runs, groups, args.report)
    print(args.runs_output)
    print(args.groups_output)
    print(args.report)


if __name__ == "__main__":
    main()
