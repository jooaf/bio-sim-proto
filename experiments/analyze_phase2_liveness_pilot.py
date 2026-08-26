"""Summarize the preregistered Phase 2 liveness operating-point pilot."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.conservation import conservation_residuals
from analysis.load import load_run
from analysis.spatial import block_beta_permutation_test, neighbor_identity_test


DISSOLUTION_COLUMN = "dissolution.spontaneous_rate"
RESEED_COLUMN = "world.reseed_rate"


def _longest_true_run(values: pd.Series) -> int:
    longest = 0
    current = 0
    for value in values.astype(bool):
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def _count_pool_changes(values: pd.Series) -> int:
    histograms = [np.asarray(value, dtype=np.int64) for value in values]
    return sum(
        not np.array_equal(left, right)
        for left, right in zip(histograms, histograms[1:])
    )


def summarize_run(
    run_dir: Path,
    *,
    dissolution_rate: float,
    reseed_rate: float,
    permutations: int,
    analysis_seed: int,
) -> dict[str, Any]:
    """Compute one run's mechanical and descriptive spatial outcomes."""

    data = load_run(run_dir)
    ticks = data.table("ticks").sort_values("tick", ignore_index=True)
    tapes = data.table("tapes")
    events = data.table("events")
    if ticks.empty or tapes.empty:
        raise ValueError(f"pilot run has no tick/tape facts: {run_dir}")
    capacity = data.config.world.width * data.config.world.height
    final_window_size = max(1, len(ticks) // 10)
    late = ticks.iloc[-final_window_size:]
    occupied_fraction = late["n_tapes"] / capacity
    active_fraction = float((late["n_interactions"] > 0).mean())
    longest_clogged = _longest_true_run(ticks["n_free_cells"] == 0)
    dissolutions = int(ticks["n_dissolutions"].sum())
    placements = int((events["event_type"] == "random_tape_placed").sum())
    pool_changes = _count_pool_changes(late["pool_histogram"])
    residuals = conservation_residuals(ticks, tapes)
    conserved = bool(len(residuals) and residuals["conserved"].all())
    max_residual = int(residuals["max_abs_residual"].max()) if not residuals.empty else -1
    invariant_path = run_dir / "invariant_log.jsonl"
    invariant_failures = len(
        [line for line in invariant_path.read_text(encoding="utf-8").splitlines() if line]
    )
    final_tick = int(cast(Any, tapes["tick"].max()))
    final_snapshot = tapes[tapes["tick"] == final_tick]
    rng = np.random.default_rng(analysis_seed + data.config.run.seed)
    identity = neighbor_identity_test(
        final_snapshot,
        width=data.config.world.width,
        height=data.config.world.height,
        permutations=permutations,
        rng=rng,
    )
    beta = block_beta_permutation_test(
        final_snapshot,
        width=data.config.world.width,
        height=data.config.world.height,
        block_size=2,
        permutations=permutations,
        q_values=(1.0,),
        rng=rng,
    ).iloc[0]
    successful_exit = data.manifest.get("exit_status") == "success"
    late_writes = int(late["n_writes_success"].sum())
    mechanically_feasible = bool(
        successful_exit
        and invariant_failures == 0
        and conserved
        and int(ticks["n_tapes"].min()) > 0
        and float(occupied_fraction.mean()) >= 0.20
        and longest_clogged <= 1_000
        and active_fraction >= 0.90
        and late_writes > 0
        and dissolutions > 0
        and placements > 0
        and pool_changes > 0
    )
    return {
        "run_dir": str(run_dir),
        "seed": data.config.run.seed,
        "dissolution_rate": dissolution_rate,
        "reseed_rate": reseed_rate,
        "successful_exit": successful_exit,
        "invariant_failures": invariant_failures,
        "conserved": conserved,
        "max_conservation_residual": max_residual,
        "minimum_tapes": int(ticks["n_tapes"].min()),
        "late_mean_occupied_fraction": float(occupied_fraction.mean()),
        "longest_clogged_ticks": longest_clogged,
        "late_active_interaction_fraction": active_fraction,
        "late_successful_writes": late_writes,
        "dissolutions": dissolutions,
        "placements": placements,
        "late_pool_changes": pool_changes,
        "mechanically_feasible": mechanically_feasible,
        "final_snapshot_tick": final_tick,
        "final_tapes": len(final_snapshot),
        "final_unique_hashes": int(final_snapshot["content_hash"].nunique()),
        "neighbor_identity_excess": identity.excess,
        "neighbor_identity_p": identity.p_value,
        "q1_beta": float(beta["observed_beta"]),
        "q1_beta_null_mean": float(beta["null_mean_beta"]),
        "q1_beta_excess": float(beta["beta_excess"]),
        "q1_beta_p": float(beta["p_value"]),
    }


def treatment_summary(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate matched seeds and apply the preregistered selection ranking."""

    grouped = runs.groupby(["dissolution_rate", "reseed_rate"], sort=True)
    summary = grouped.agg(
        runs=("seed", "size"),
        feasible_seeds=("mechanically_feasible", "sum"),
        all_exits_successful=("successful_exit", "all"),
        all_conserved=("conserved", "all"),
        total_invariant_failures=("invariant_failures", "sum"),
        median_late_occupied_fraction=("late_mean_occupied_fraction", "median"),
        min_population_across_seeds=("minimum_tapes", "min"),
        total_dissolutions=("dissolutions", "sum"),
        total_placements=("placements", "sum"),
        median_neighbor_excess=("neighbor_identity_excess", "median"),
        median_q1_beta_excess=("q1_beta_excess", "median"),
    ).reset_index()
    summary["occupancy_distance_from_0_8"] = (
        summary["median_late_occupied_fraction"] - 0.8
    ).abs()
    summary["eligible"] = summary["feasible_seeds"] >= 2
    return summary.sort_values(
        [
            "feasible_seeds",
            "occupancy_distance_from_0_8",
            "dissolution_rate",
            "reseed_rate",
        ],
        ascending=[False, True, True, True],
        ignore_index=True,
    )


def write_report(
    runs: pd.DataFrame,
    treatments: pd.DataFrame,
    target: Path,
    *,
    confirmation: bool = False,
) -> None:
    """Write a compact pilot or scale-confirmation report."""

    selected = treatments[treatments["eligible"]].head(1)
    if selected.empty:
        decision = (
            "**OPERATING POINT NOT CONFIRMED.** Fewer than 2 of 3 seeds were mechanically feasible."
            if confirmation
            else "**NO OPERATING POINT SELECTED.** No treatment met the 2-of-3 feasibility rule."
        )
    else:
        selected_row = selected.iloc[0]
        prefix = "Larger-lattice operating point confirmed:" if confirmation else "Selected for larger-lattice confirmation:"
        decision = (
            f"{prefix} spontaneous dissolution "
            f"`{float(selected_row['dissolution_rate']):g}` and "
            f"reseed `{float(selected_row['reseed_rate']):g}` "
            f"({int(selected_row['feasible_seeds'])}/{int(selected_row['runs'])} feasible seeds)."
        )
    title = (
        "# Phase 2 liveness larger-lattice confirmation"
        if confirmation
        else "# Phase 2 liveness operating-point pilot"
    )
    lines = [
        title,
        "",
        "## Decision",
        "",
        decision,
        "",
        (
            "This is a 5,000-tick scale confirmation, not the 500,000-tick acceptance result. Spatial statistics are descriptive and did not affect the mechanical decision."
            if confirmation
            else "This is a short parameter-selection pilot, not the 500,000-tick acceptance result. Spatial statistics are descriptive and were not used for treatment selection."
        ),
        "",
        "## Treatment summary",
        "",
        "| dissolution | reseed | feasible | median late occupancy | min tapes | dissolutions | placements | median neighbor excess | median q=1 beta excess |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    treatment_records = cast(list[dict[str, Any]], treatments.to_dict(orient="records"))
    for treatment in treatment_records:
        lines.append(
            f"| {float(treatment['dissolution_rate']):g} | "
            f"{float(treatment['reseed_rate']):g} | "
            f"{int(treatment['feasible_seeds'])}/{int(treatment['runs'])} | "
            f"{float(treatment['median_late_occupied_fraction']):.3f} | "
            f"{int(treatment['min_population_across_seeds'])} | "
            f"{int(treatment['total_dissolutions'])} | "
            f"{int(treatment['total_placements'])} | "
            f"{float(treatment['median_neighbor_excess']):.6f} | "
            f"{float(treatment['median_q1_beta_excess']):.6f} |"
        )
    all_final_hashes_unique = bool((runs["final_tapes"] == runs["final_unique_hashes"]).all())
    lines += [
        "",
        "## Spatial-screening limitation",
        "",
        (
            "Every final tape hash was unique in every run. Exact-hash neighbor identity and hash-label beta permutation effects are therefore degenerate: relabeling unique hashes cannot change either statistic. The zero excesses are **uninformative**, not evidence that locality has no effect. The radius campaign needs replicated types, a coarser preregistered type definition, or an additional sequence-similarity statistic before these tests can answer the spatial question."
            if all_final_hashes_unique
            else "At least one final snapshot contained a repeated exact content hash, so the exact-hash spatial screen was not universally degenerate."
        ),
        "",
        "## Integrity",
        "",
        f"- Runs analyzed: {len(runs)}",
        f"- Successful exits: {int(runs['successful_exit'].sum())}/{len(runs)}",
        f"- Exactly conserved runs: {int(runs['conserved'].sum())}/{len(runs)}",
        f"- Total invariant failures: {int(runs['invariant_failures'].sum())}",
        f"- Mechanically feasible runs: {int(runs['mechanically_feasible'].sum())}/{len(runs)}",
        f"- Every final hash unique in every run: **{all_final_hashes_unique}**",
        "",
        (
            "Mechanical liveness is confirmed at 32×32, but the radius sweep remains blocked until its non-degenerate spatial metric is frozen."
            if confirmation and not selected.empty
            else "The selected treatment, if any, must pass a larger-lattice confirmation before the matched radius sweep."
        ),
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument(
        "--runs-output",
        type=Path,
        default=Path("reports/phase2_liveness_pilot_runs.csv"),
    )
    parser.add_argument(
        "--treatments-output",
        type=Path,
        default=Path("reports/phase2_liveness_pilot_treatments.csv"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/phase2_liveness_pilot_report.md"),
    )
    parser.add_argument("--permutations", type=int, default=199)
    parser.add_argument("--analysis-seed", type=int, default=20260825)
    parser.add_argument("--confirmation", action="store_true")
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", DISSOLUTION_COLUMN, RESEED_COLUMN}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"pilot index is missing columns: {sorted(missing)}")
    index_records = cast(list[dict[str, Any]], index.to_dict(orient="records"))
    rows = [
        summarize_run(
            Path(str(row["run_dir"])),
            dissolution_rate=float(row[DISSOLUTION_COLUMN]),
            reseed_rate=float(row[RESEED_COLUMN]),
            permutations=args.permutations,
            analysis_seed=args.analysis_seed,
        )
        for row in index_records
    ]
    runs = pd.DataFrame(rows).sort_values(
        ["dissolution_rate", "reseed_rate", "seed"], ignore_index=True
    )
    treatments = treatment_summary(runs)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    treatments.to_csv(args.treatments_output, index=False)
    write_report(runs, treatments, args.report, confirmation=args.confirmation)
    print(args.runs_output)
    print(args.treatments_output)
    print(args.report)


if __name__ == "__main__":
    main()
