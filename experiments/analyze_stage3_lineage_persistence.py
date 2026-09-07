"""Analyze the preregistered Stage 3 lineage switch-off persistence campaign."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run
from analysis.spatial import neighbor_identity_test
from experiments.analyze_phase2_liveness_pilot import summarize_run
from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater
from experiments.analyze_stage3r_lineage_patch import parent_map, root_map
from experiments.analyze_stage3r_reproduction_liveness import event_count, lineage_depth
from experiments.stringmol.analyze_locality import paired_bootstrap_interval
from soup.config import Config


STOP_TICK = "reproduction.stop_tick"
CHECKPOINTS = (10_000, 12_000, 15_000, 19_900)


def summarize(
    run_dir: Path, *, permutations: int, analysis_seed: int
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return run mechanics and frozen checkpoint family/root outcomes."""

    config = Config.load(run_dir / "config.toml")
    summary = summarize_run(
        run_dir,
        dissolution_rate=config.dissolution.spontaneous_rate,
        reseed_rate=config.world.reseed_rate,
        permutations=19,
        analysis_seed=analysis_seed + 50_000,
    )
    data = load_run(run_dir)
    tapes = data.table("tapes")
    lineage = data.table("lineage")
    events = data.table("events")
    parents = parent_map(lineage)
    curves: list[dict[str, Any]] = []
    for tick in CHECKPOINTS:
        snapshot = tapes[tapes["tick"] == tick].reset_index(drop=True)
        if snapshot.empty:
            raise ValueError(f"missing frozen tape checkpoint {tick}: {run_dir}")
        ids = [int(value) for value in snapshot["tape_id"]]
        roots = root_map(parents, ids)
        family_snapshot = snapshot.copy()
        family_snapshot["content_hash"] = [str(roots[tape_id] % 16) for tape_id in ids]
        family = neighbor_identity_test(
            family_snapshot,
            width=config.world.width,
            height=config.world.height,
            permutations=permutations,
            rng=np.random.default_rng(analysis_seed + config.run.seed + tick),
        )
        root_snapshot = snapshot.copy()
        root_snapshot["content_hash"] = [str(roots[tape_id]) for tape_id in ids]
        root = neighbor_identity_test(
            root_snapshot,
            width=config.world.width,
            height=config.world.height,
            permutations=199,
            rng=np.random.default_rng(
                analysis_seed + 1_000_000 + config.run.seed + tick
            ),
        )
        curves.append(
            {
                "seed": config.run.seed,
                "stop_tick": config.reproduction.stop_tick,
                "tick": tick,
                "family_observed": family.observed,
                "family_null": family.null_mean,
                "family_excess": family.excess,
                "family_p": family.p_value,
                "root_excess": root.excess,
                "root_p": root.p_value,
                "occupied": len(snapshot),
            }
        )
    curve = pd.DataFrame(curves).set_index("tick")
    switch_excess = float(cast(Any, curve.loc[10_000, "family_excess"]))
    final_excess = float(cast(Any, curve.loc[19_900, "family_excess"]))
    births = event_count(events, "offspring_born")
    summary.update(
        {
            "stop_tick": config.reproduction.stop_tick,
            "births": births,
            "max_lineage_depth": lineage_depth(lineage),
            "switch_family_excess": switch_excess,
            "final_family_excess": final_excess,
            "final_family_p": float(cast(Any, curve.loc[19_900, "family_p"])),
            "final_root_excess": float(cast(Any, curve.loc[19_900, "root_excess"])),
            "retention_ratio": (
                final_excess / switch_excess if switch_excess > 0.0 else np.nan
            ),
            "persistence_feasible": bool(
                summary["successful_exit"]
                and summary["conserved"]
                and int(summary["invariant_failures"]) == 0
                and 0.40 <= float(summary["late_mean_occupied_fraction"]) <= 0.95
                and float(summary["late_active_interaction_fraction"]) > 0.0
                and int(summary["late_successful_writes"]) > 0
                and int(summary["dissolutions"]) > 0
                and int(summary["placements"]) > 0
                and int(summary["late_pool_changes"]) > 0
            ),
        }
    )
    return summary, curves


def group_summary(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate arm-level mechanics and final persistence."""

    return (
        runs.groupby("stop_tick", sort=True)
        .agg(
            runs=("seed", "size"),
            feasible=("persistence_feasible", "sum"),
            median_births=("births", "median"),
            median_depth=("max_lineage_depth", "median"),
            median_occupancy=("late_mean_occupied_fraction", "median"),
            mean_switch_excess=("switch_family_excess", "mean"),
            mean_final_excess=("final_family_excess", "mean"),
            positive_final=("final_family_excess", lambda values: int((values > 0).sum())),
            significant_final=("final_family_p", lambda values: int((values <= 0.05).sum())),
            median_retention=("retention_ratio", "median"),
            mean_final_root=("final_root_excess", "mean"),
            conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
        )
        .reset_index()
    )


def stopped_inference(
    runs: pd.DataFrame,
) -> tuple[np.ndarray[Any, np.dtype[np.float64]], float, float, float]:
    """Return frozen inference for stopped-arm final excess against zero."""

    values = runs.loc[runs["stop_tick"] == 10_000, "final_family_excess"].to_numpy(
        dtype=np.float64
    )
    if len(values) != 10:
        raise ValueError("persistence campaign requires ten stopped runs")
    p_value = exact_paired_sign_flip_greater(values)
    lower, upper = paired_bootstrap_interval(values, resamples=10_000, seed=20260916)
    return values, p_value, lower, upper


def passes_gate(runs: pd.DataFrame, groups: pd.DataFrame) -> bool:
    """Apply all frozen switch-off persistence criteria."""

    values, p_value, lower, _ = stopped_inference(runs)
    indexed = groups.set_index("stop_tick")
    return bool(
        float(values.mean()) > 0.0
        and lower > 0.0
        and p_value <= 0.05
        and int(np.count_nonzero(values > 0.0)) >= 8
        and int(cast(Any, indexed.loc[10_000, "significant_final"])) >= 8
        and float(cast(Any, indexed.loc[10_000, "median_retention"])) >= 0.25
        and int(cast(Any, indexed.loc[0, "positive_final"])) >= 8
        and len(runs) == 20
        and runs["successful_exit"].all()
        and runs["conserved"].all()
        and int(runs["invariant_failures"].sum()) == 0
        and (groups["feasible"] >= 8).all()
    )


def write_report(runs: pd.DataFrame, groups: pd.DataFrame, target: Path) -> None:
    """Write the frozen switch-off persistence decision."""

    values, p_value, lower, upper = stopped_inference(runs)
    final_pivot = runs.pivot(
        index="seed", columns="stop_tick", values="final_family_excess"
    )
    continued_minus_stopped = (final_pivot[0] - final_pivot[10_000]).to_numpy(
        dtype=np.float64
    )
    lines = [
        "# Stage 3 neutral lineage-patch persistence result",
        "",
        "## Decision",
        "",
        f"Preregistered switch-off persistence supported: **{passes_gate(runs, groups)}**.",
        "",
        f"- Mean stopped-arm final family excess: {float(values.mean()):.6f}",
        f"- Median stopped-arm final excess: {float(np.median(values)):.6f}",
        f"- 95% bootstrap interval: [{lower:.6f}, {upper:.6f}]",
        f"- Exact one-sided sign-flip p: {p_value:.6f}",
        f"- Positive stopped-arm final excesses: {int(np.count_nonzero(values > 0.0))}/10",
        f"- Mean continued-minus-stopped final excess: {float(continued_minus_stopped.mean()):.6f}",
        "",
        "| stop tick | feasible | births | depth | occupancy | switch excess | final excess | positive | significant | retention | root excess |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(
            f"| {int(row['stop_tick'])} | {int(row['feasible'])}/{int(row['runs'])} | "
            f"{float(row['median_births']):.0f} | {float(row['median_depth']):.1f} | "
            f"{float(row['median_occupancy']):.3f} | {float(row['mean_switch_excess']):.6f} | "
            f"{float(row['mean_final_excess']):.6f} | {int(row['positive_final'])}/{int(row['runs'])} | "
            f"{int(row['significant_final'])}/{int(row['runs'])} | {float(row['median_retention']):.3f} | "
            f"{float(row['mean_final_root']):.6f} |"
        )
    lines += [
        "",
        "Neutral-family persistence is not organismal self-maintenance.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--permutations", type=int, default=499)
    parser.add_argument("--analysis-seed", type=int, default=20260916)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage3_lineage_persistence_runs.csv"))
    parser.add_argument("--groups-output", type=Path, default=Path("reports/stage3_lineage_persistence_groups.csv"))
    parser.add_argument("--curves-output", type=Path, default=Path("reports/stage3_lineage_persistence_curves.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage3_lineage_persistence_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", STOP_TICK}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"persistence index missing columns: {sorted(missing)}")
    summaries: list[dict[str, Any]] = []
    curves: list[dict[str, Any]] = []
    for row in cast(list[dict[str, Any]], index.to_dict(orient="records")):
        summary, run_curves = summarize(
            Path(str(row["run_dir"])),
            permutations=args.permutations,
            analysis_seed=args.analysis_seed,
        )
        summaries.append(summary)
        curves.extend(run_curves)
    runs = pd.DataFrame(summaries).sort_values(["stop_tick", "seed"], ignore_index=True)
    curve_frame = pd.DataFrame(curves).sort_values(["stop_tick", "seed", "tick"], ignore_index=True)
    if len(runs) != 20 or runs.groupby("stop_tick")["seed"].nunique().min() != 10:
        raise ValueError("persistence campaign requires two complete ten-seed cells")
    groups = group_summary(runs)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    groups.to_csv(args.groups_output, index=False)
    curve_frame.to_csv(args.curves_output, index=False)
    write_report(runs, groups, args.report)
    print(args.runs_output)
    print(args.groups_output)
    print(args.curves_output)
    print(args.report)


if __name__ == "__main__":
    main()
