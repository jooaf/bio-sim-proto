"""Analyze the preregistered Stage 3 population-regulation experiment."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.conservation import conservation_residuals
from analysis.load import load_run
from analysis.spatial import neighbor_identity_test
from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater
from experiments.analyze_stage3r_lineage_patch import parent_map, root_map
from experiments.analyze_stage3r_reproduction_liveness import event_count, lineage_depth
from experiments.stringmol.analyze_locality import paired_bootstrap_interval
from soup.config import Config


RATE = "dissolution.spontaneous_rate"
PILOT_RATES = (0.00002, 0.00003, 0.00005, 0.0001)
PILOT_SEEDS = set(range(202609180, 202609183))
CONFIRMATION_SEEDS = set(range(202609183, 202609193))
CAPACITY = 32 * 32


def _pool_changes(ticks: pd.DataFrame) -> int:
    histograms = [np.asarray(value, dtype=np.int64) for value in ticks["pool_histogram"]]
    return sum(
        not np.array_equal(left, right)
        for left, right in zip(histograms, histograms[1:])
    )


def mechanics(run_dir: Path) -> dict[str, Any]:
    """Compute only outcomes allowed for mechanics-only rate selection."""

    data = load_run(run_dir)
    config = data.config
    ticks = data.table("ticks").sort_values("tick", ignore_index=True)
    tapes = data.table("tapes")
    events = data.table("events")
    lineage = data.table("lineage")
    if ticks.empty or tapes.empty:
        raise ValueError(f"population-regulation run has no tick/tape facts: {run_dir}")
    counts = tapes.groupby("tick").size()
    for checkpoint in (10_000, 19_900):
        if checkpoint not in counts.index:
            raise ValueError(f"missing frozen occupancy checkpoint {checkpoint}: {run_dir}")
    late_counts = counts[(counts.index >= 15_000) & (counts.index <= 19_900)]
    if len(late_counts) != 50:
        raise ValueError(f"expected 50 frozen late occupancy snapshots: {run_dir}")
    occupancy_10k = float(counts.loc[10_000] / CAPACITY)
    occupancy_19900 = float(counts.loc[19_900] / CAPACITY)
    late_occupancy = float((late_counts / CAPACITY).mean())
    occupancy_change = occupancy_19900 - occupancy_10k
    births = event_count(events, "offspring_born")
    pool_blocks = event_count(events, "reproduction_blocked_pool")
    space_blocks = event_count(events, "reproduction_blocked_no_space")
    dissolutions = int(ticks["n_dissolutions"].sum())
    placements = int((events["event_type"] == "random_tape_placed").sum())
    late_ticks = ticks[(ticks["tick"] >= 15_000) & (ticks["tick"] <= 19_900)]
    residuals = conservation_residuals(ticks, tapes)
    conserved = bool(len(residuals) and residuals["conserved"].all())
    invariant_path = run_dir / "invariant_log.jsonl"
    invariant_failures = sum(
        bool(line)
        for line in invariant_path.read_text(encoding="utf-8").splitlines()
    )
    result = {
        "run_dir": str(run_dir),
        "seed": config.run.seed,
        "dissolution_rate": config.dissolution.spontaneous_rate,
        "successful_exit": data.manifest.get("exit_status") == "success",
        "conserved": conserved,
        "max_conservation_residual": (
            int(residuals["max_abs_residual"].max()) if len(residuals) else -1
        ),
        "invariant_failures": invariant_failures,
        "occupancy_10000": occupancy_10k,
        "occupancy_19900": occupancy_19900,
        "occupancy_change": occupancy_change,
        "late_mean_occupied_fraction": late_occupancy,
        "reproductive_births": births,
        "dissolutions": dissolutions,
        "placements": placements,
        "reproduction_blocked_pool": pool_blocks,
        "reproduction_blocked_no_space": space_blocks,
        "max_lineage_depth": lineage_depth(lineage),
        "late_active_interaction_fraction": float(
            (late_ticks["n_interactions"] > 0).mean()
        ),
        "late_successful_writes": int(late_ticks["n_writes_success"].sum()),
        "late_pool_changes": _pool_changes(late_ticks),
    }
    result["regulation_feasible"] = bool(
        result["successful_exit"]
        and result["conserved"]
        and invariant_failures == 0
        and 0.50 <= late_occupancy <= 0.90
        and 0.50 <= occupancy_19900 <= 0.90
        and abs(occupancy_change) <= 0.05
        and births >= 100
        and dissolutions >= 100
        and placements > 0
        and result["late_active_interaction_fraction"] > 0.0
        and result["late_successful_writes"] > 0
        and result["late_pool_changes"] > 0
        and pool_blocks <= births
        and result["max_lineage_depth"] >= 3
    )
    return result


def pilot_groups(runs: pd.DataFrame) -> pd.DataFrame:
    """Apply the frozen eligibility and ranking rule."""

    groups = (
        runs.groupby("dissolution_rate", sort=True)
        .agg(
            runs=("seed", "size"),
            feasible=("regulation_feasible", "sum"),
            median_births=("reproductive_births", "median"),
            median_dissolutions=("dissolutions", "median"),
            median_occupancy=("late_mean_occupied_fraction", "median"),
            median_abs_change=("occupancy_change", lambda values: float(np.median(np.abs(values)))),
            median_depth=("max_lineage_depth", "median"),
            conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
        )
        .reset_index()
    )
    groups["eligible"] = groups["feasible"] >= 2
    groups["occupancy_distance"] = (groups["median_occupancy"] - 0.75).abs()
    groups["turnover_imbalance"] = (
        groups["median_births"] - groups["median_dissolutions"]
    ).abs()
    return groups.sort_values(
        [
            "eligible",
            "feasible",
            "median_abs_change",
            "occupancy_distance",
            "turnover_imbalance",
            "dissolution_rate",
        ],
        ascending=[False, False, True, True, True, True],
        ignore_index=True,
    )


def selected_rate(groups: pd.DataFrame) -> float | None:
    eligible = groups[groups["eligible"]]
    return None if eligible.empty else float(cast(Any, eligible.iloc[0]["dissolution_rate"]))


def confirmation_summary(run_dir: Path, *, analysis_seed: int = 20260918) -> dict[str, Any]:
    """Add the frozen held-out lineage endpoint to mechanical outcomes."""

    summary = mechanics(run_dir)
    data = load_run(run_dir)
    tapes = data.table("tapes")
    lineage = data.table("lineage")
    snapshot = tapes[tapes["tick"] == 19_900].reset_index(drop=True)
    ids = [int(value) for value in snapshot["tape_id"]]
    roots = root_map(parent_map(lineage), ids)
    family_snapshot = snapshot.copy()
    family_snapshot["content_hash"] = [str(roots[tape_id] % 16) for tape_id in ids]
    family = neighbor_identity_test(
        family_snapshot,
        width=data.config.world.width,
        height=data.config.world.height,
        permutations=499,
        rng=np.random.default_rng(analysis_seed + data.config.run.seed + 19_900),
    )
    root_snapshot = snapshot.copy()
    root_snapshot["content_hash"] = [str(roots[tape_id]) for tape_id in ids]
    root = neighbor_identity_test(
        root_snapshot,
        width=data.config.world.width,
        height=data.config.world.height,
        permutations=199,
        rng=np.random.default_rng(
            analysis_seed + 1_000_000 + data.config.run.seed + 19_900
        ),
    )
    summary.update(
        {
            "final_family_excess": family.excess,
            "final_family_p": family.p_value,
            "final_root_excess": root.excess,
            "final_root_p": root.p_value,
        }
    )
    return summary


def confirmation_inference(runs: pd.DataFrame) -> tuple[float, float, float, float]:
    values = runs["final_family_excess"].to_numpy(dtype=np.float64)
    if len(values) != 10:
        raise ValueError("population-regulation confirmation requires ten runs")
    lower, upper = paired_bootstrap_interval(values, resamples=10_000, seed=20260918)
    return float(values.mean()), lower, upper, exact_paired_sign_flip_greater(values)


def confirmation_passes(runs: pd.DataFrame) -> bool:
    mean, lower, _, p_value = confirmation_inference(runs)
    return bool(
        int(runs["regulation_feasible"].sum()) >= 8
        and mean > 0.0
        and lower > 0.0
        and p_value <= 0.05
        and int((runs["final_family_excess"] > 0.0).sum()) >= 8
        and int((runs["final_family_p"] <= 0.05).sum()) >= 8
        and len(runs) == 10
        and runs["successful_exit"].all()
        and runs["conserved"].all()
        and int(runs["invariant_failures"].sum()) == 0
    )


def write_pilot_report(groups: pd.DataFrame, target: Path) -> None:
    rate = selected_rate(groups)
    lines = [
        "# Stage 3 population-regulation mechanics pilot",
        "",
        "## Decision",
        "",
        (f"Selected spontaneous dissolution rate: **{rate:g}**." if rate is not None else "**No rate selected; stop before lineage analysis.**"),
        "",
        "No family-neighbor or exact-root spatial endpoint was computed for selection.",
        "",
        "| rate | feasible | occupancy | abs change | births | dissolutions | depth | eligible |",
        "|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(
            f"| {float(row['dissolution_rate']):g} | {int(row['feasible'])}/{int(row['runs'])} | "
            f"{float(row['median_occupancy']):.3f} | {float(row['median_abs_change']):.3f} | "
            f"{float(row['median_births']):.0f} | {float(row['median_dissolutions']):.0f} | "
            f"{float(row['median_depth']):.1f} | {bool(row['eligible'])} |"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_confirmation_report(runs: pd.DataFrame, target: Path) -> None:
    mean, lower, upper, p_value = confirmation_inference(runs)
    lines = [
        "# Stage 3 regulated lineage positive-control confirmation",
        "",
        "## Decision",
        "",
        f"Regulated lineage positive control supported: **{confirmation_passes(runs)}**.",
        "",
        f"- Selected spontaneous dissolution rate: {float(runs['dissolution_rate'].iloc[0]):g}",
        f"- Mechanically feasible: {int(runs['regulation_feasible'].sum())}/10",
        f"- Mean final family-neighbor excess: {mean:.6f}",
        f"- 95% bootstrap interval: [{lower:.6f}, {upper:.6f}]",
        f"- Exact one-sided sign-flip p: {p_value:.6f}",
        f"- Positive final excesses: {int((runs['final_family_excess'] > 0).sum())}/10",
        f"- Significant within-run tests: {int((runs['final_family_p'] <= 0.05).sum())}/10",
        f"- Median late occupancy: {float(runs['late_mean_occupied_fraction'].median()):.3f}",
        f"- Median births: {float(runs['reproductive_births'].median()):.0f}",
        "",
        "A pass supports a neutral scheduled-birth control, not endogenous reproduction or self-maintenance.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def _load_index(index: Path, *, expected_seeds: set[int]) -> pd.DataFrame:
    frame = pd.read_parquet(index)
    required = {"run_dir", "seed", RATE}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"population-regulation index missing columns: {sorted(missing)}")
    if set(frame["seed"].astype(int)) != expected_seeds:
        raise ValueError("population-regulation index has unexpected seeds")
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="phase", required=True)
    pilot = subparsers.add_parser("pilot")
    pilot.add_argument("index", type=Path)
    pilot.add_argument("--runs-output", type=Path, default=Path("reports/stage3_population_regulation_pilot_runs.csv"))
    pilot.add_argument("--groups-output", type=Path, default=Path("reports/stage3_population_regulation_pilot_groups.csv"))
    pilot.add_argument("--report", type=Path, default=Path("reports/stage3_population_regulation_pilot_report.md"))
    confirmation = subparsers.add_parser("confirm")
    confirmation.add_argument("index", type=Path)
    confirmation.add_argument("--runs-output", type=Path, default=Path("reports/stage3_population_regulation_confirmation_runs.csv"))
    confirmation.add_argument("--report", type=Path, default=Path("reports/stage3_population_regulation_confirmation_report.md"))
    args = parser.parse_args()
    if args.phase == "pilot":
        index = _load_index(args.index, expected_seeds=PILOT_SEEDS)
        if len(index) != 12 or set(index[RATE].astype(float)) != set(PILOT_RATES):
            raise ValueError("pilot requires four complete three-seed cells")
        runs = pd.DataFrame(
            [mechanics(Path(str(row["run_dir"]))) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))]
        ).sort_values(["dissolution_rate", "seed"], ignore_index=True)
        groups = pilot_groups(runs)
        args.runs_output.parent.mkdir(parents=True, exist_ok=True)
        runs.to_csv(args.runs_output, index=False)
        groups.to_csv(args.groups_output, index=False)
        write_pilot_report(groups, args.report)
        print(args.runs_output)
        print(args.groups_output)
        print(args.report)
    else:
        index = _load_index(args.index, expected_seeds=CONFIRMATION_SEEDS)
        if len(index) != 10 or index[RATE].nunique() != 1:
            raise ValueError("confirmation requires one complete ten-seed cell")
        runs = pd.DataFrame(
            [confirmation_summary(Path(str(row["run_dir"]))) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))]
        ).sort_values("seed", ignore_index=True)
        args.runs_output.parent.mkdir(parents=True, exist_ok=True)
        runs.to_csv(args.runs_output, index=False)
        write_confirmation_report(runs, args.report)
        print(args.runs_output)
        print(args.report)


if __name__ == "__main__":
    main()
