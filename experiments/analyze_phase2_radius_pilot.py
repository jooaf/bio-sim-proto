"""Analyze the preregistered matched-seed Phase 2 interaction-radius pilot."""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from experiments.analyze_phase2_liveness_pilot import summarize_run
from soup.config import Config


RADIUS_COLUMN = "world.interaction_radius"


def exact_paired_sign_flip_greater(differences: NDArray[np.float64]) -> float:
    """Return exact one-sided p for a positive mean paired difference."""

    values = np.asarray(differences, dtype=np.float64)
    if values.ndim != 1 or len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("differences must be a nonempty finite vector")
    observed = float(np.mean(values))
    null = np.asarray(
        [
            np.mean(values * np.asarray(signs, dtype=np.float64))
            for signs in itertools.product((-1.0, 1.0), repeat=len(values))
        ],
        dtype=np.float64,
    )
    return float(np.mean(null >= observed - 1e-15))


def summarize_radius_groups(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate outcomes by radius without assuming monotonicity."""

    return (
        runs.groupby("radius", sort=True)
        .agg(
            runs=("seed", "size"),
            feasible_seeds=("mechanically_feasible", "sum"),
            all_conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
            median_late_occupancy=("late_mean_occupied_fraction", "median"),
            total_dissolutions=("dissolutions", "sum"),
            total_placements=("placements", "sum"),
            median_byte_excess=("neighbor_byte_identity_excess", "median"),
            median_byte_p=("neighbor_byte_identity_p", "median"),
            median_opcode_beta_excess=("opcode_q1_beta_excess", "median"),
            median_opcode_beta_p=("opcode_q1_beta_p", "median"),
        )
        .reset_index()
    )


def paired_contrast(
    runs: pd.DataFrame, outcome: str
) -> tuple[NDArray[np.float64], float]:
    """Return matched radius-1 minus radius-8 effects and exact p-value."""

    pivot = runs.pivot(index="seed", columns="radius", values=outcome)
    if 1 not in pivot.columns or 8 not in pivot.columns or pivot[[1, 8]].isna().any().any():
        raise ValueError(f"outcome {outcome!r} lacks complete radius-1/radius-8 pairs")
    differences = (pivot[1] - pivot[8]).to_numpy(dtype=np.float64)
    return differences, exact_paired_sign_flip_greater(differences)


def write_report(runs: pd.DataFrame, groups: pd.DataFrame, target: Path) -> None:
    """Write mechanical integrity, all radii, and focused paired contrasts."""

    byte_differences, byte_p = paired_contrast(runs, "neighbor_byte_identity_excess")
    opcode_differences, opcode_p = paired_contrast(runs, "opcode_q1_beta_excess")
    lines = [
        "# Phase 2 matched interaction-radius pilot",
        "",
        "## Scope",
        "",
        "This is a five-seed, 5,000-tick pilot. It estimates radius effects but cannot pass the 500,000-tick Phase 2 acceptance gate.",
        "",
        "## Radius summary",
        "",
        "| radius | feasible | median late occupancy | dissolutions | placements | median byte-identity excess | median within-run p | median opcode q=1 beta excess | median within-run p |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    records = cast(list[dict[str, Any]], groups.to_dict(orient="records"))
    for row in records:
        lines.append(
            f"| {int(row['radius'])} | {int(row['feasible_seeds'])}/{int(row['runs'])} | "
            f"{float(row['median_late_occupancy']):.3f} | "
            f"{int(row['total_dissolutions'])} | {int(row['total_placements'])} | "
            f"{float(row['median_byte_excess']):.6f} | {float(row['median_byte_p']):.4f} | "
            f"{float(row['median_opcode_beta_excess']):.6f} | "
            f"{float(row['median_opcode_beta_p']):.4f} |"
        )
    lines += [
        "",
        "## Focused matched contrast: radius 1 minus radius 8",
        "",
        f"- Byte-identity excess differences: {', '.join(f'{value:.6f}' for value in byte_differences)}",
        f"- Mean byte-identity difference: {float(np.mean(byte_differences)):.6f}",
        f"- Exact one-sided paired sign-flip p-value: {byte_p:.6f}",
        f"- Opcode q=1 beta-excess differences: {', '.join(f'{value:.6f}' for value in opcode_differences)}",
        f"- Mean opcode beta-excess difference: {float(np.mean(opcode_differences)):.6f}",
        f"- Exact one-sided paired sign-flip p-value: {opcode_p:.6f}",
        "",
        "The exact test has only 2⁵ = 32 sign assignments, so its smallest possible one-sided p-value is 0.03125. Effect sizes and seed consistency are primary for this pilot.",
        "",
        "## Integrity",
        "",
        f"- Runs analyzed: {len(runs)}",
        f"- Successful exits: {int(runs['successful_exit'].sum())}/{len(runs)}",
        f"- Exactly conserved runs: {int(runs['conserved'].sum())}/{len(runs)}",
        f"- Total invariant failures: {int(runs['invariant_failures'].sum())}",
        f"- Mechanically feasible runs: {int(runs['mechanically_feasible'].sum())}/{len(runs)}",
        "",
        "Exact-hash effects remain in the run table but are non-identifiable when all hashes are singletons. No monotonic radius response was assumed, and all four radii are reported.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument(
        "--runs-output", type=Path, default=Path("reports/phase2_radius_pilot_runs.csv")
    )
    parser.add_argument(
        "--groups-output", type=Path, default=Path("reports/phase2_radius_pilot_groups.csv")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("reports/phase2_radius_pilot_report.md")
    )
    parser.add_argument("--permutations", type=int, default=999)
    parser.add_argument("--analysis-seed", type=int, default=20260825)
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", RADIUS_COLUMN}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"radius index is missing columns: {sorted(missing)}")
    records = cast(list[dict[str, Any]], index.to_dict(orient="records"))
    rows: list[dict[str, Any]] = []
    for row in records:
        run_dir = Path(str(row["run_dir"]))
        config = Config.load(run_dir / "config.toml")
        summary = summarize_run(
            run_dir,
            dissolution_rate=config.dissolution.spontaneous_rate,
            reseed_rate=config.world.reseed_rate,
            permutations=args.permutations,
            analysis_seed=args.analysis_seed,
        )
        summary["radius"] = int(row[RADIUS_COLUMN])
        rows.append(summary)
    runs = pd.DataFrame(rows).sort_values(["radius", "seed"], ignore_index=True)
    groups = summarize_radius_groups(runs)
    expected_radii = {1, 2, 4, 8}
    if set(runs["radius"].astype(int)) != expected_radii:
        raise ValueError(f"radius campaign must contain {sorted(expected_radii)}")
    if runs.groupby("radius")["seed"].nunique().min() < 5:
        raise ValueError("radius pilot requires at least five matched seeds per radius")
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    groups.to_csv(args.groups_output, index=False)
    write_report(runs, groups, args.report)
    print(args.runs_output)
    print(args.groups_output)
    print(args.report)


if __name__ == "__main__":
    main()
