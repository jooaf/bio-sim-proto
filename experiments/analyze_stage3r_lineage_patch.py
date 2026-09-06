"""Analyze the preregistered Stage 3R neutral lineage-patch campaign."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.diversity import hill_number
from analysis.load import load_run
from analysis.spatial import neighbor_bff_opcode_js_test, neighbor_identity_test
from experiments.analyze_phase2_liveness_pilot import summarize_run
from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater
from experiments.analyze_stage3r_reproduction_liveness import event_count, lineage_depth
from experiments.stringmol.analyze_locality import paired_bootstrap_interval
from soup.config import Config


PLACEMENT_RADIUS = "reproduction.placement_radius"


def parent_map(lineage: pd.DataFrame) -> dict[int, int]:
    """Return one recorded reproductive parent per child."""

    result: dict[int, int] = {}
    for row in lineage.itertuples(index=False):
        progenitors = list(cast(Any, row.progenitor_ids))
        if len(progenitors) == 1:
            child = int(cast(Any, row.tape_id))
            parent = int(progenitors[0])
            previous = result.setdefault(child, parent)
            if previous != parent:
                raise ValueError(f"child {child} has inconsistent parents")
    return result


def root_map(parents: dict[int, int], tape_ids: list[int]) -> dict[int, int]:
    """Resolve transitive roots with cycle detection."""

    roots: dict[int, int] = {}

    def root(tape_id: int, visiting: set[int]) -> int:
        if tape_id in roots:
            return roots[tape_id]
        if tape_id in visiting:
            raise ValueError("lineage contains a cycle")
        parent = parents.get(tape_id)
        value = tape_id if parent is None else root(parent, visiting | {tape_id})
        roots[tape_id] = value
        return value

    return {tape_id: root(tape_id, set()) for tape_id in tape_ids}


def summarize_patch_run(
    run_dir: Path, *, permutations: int, analysis_seed: int
) -> dict[str, Any]:
    """Return neutral lineage spatial, lifecycle, and mechanical outcomes."""

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
    lineage = data.table("lineage")
    events = data.table("events")
    final_tick = int(cast(Any, tapes["tick"].max()))
    snapshot = tapes[tapes["tick"] == final_tick].reset_index(drop=True)
    tape_ids = [int(value) for value in snapshot["tape_id"]]
    parents = parent_map(lineage)
    roots = root_map(parents, tape_ids)

    family_snapshot = snapshot.copy()
    family_snapshot["content_hash"] = [str(roots[tape_id] % 16) for tape_id in tape_ids]
    family_result = neighbor_identity_test(
        family_snapshot,
        width=config.world.width,
        height=config.world.height,
        permutations=permutations,
        rng=np.random.default_rng(analysis_seed + config.run.seed),
    )
    root_snapshot = snapshot.copy()
    root_snapshot["content_hash"] = [str(roots[tape_id]) for tape_id in tape_ids]
    root_result = neighbor_identity_test(
        root_snapshot,
        width=config.world.width,
        height=config.world.height,
        permutations=199,
        rng=np.random.default_rng(analysis_seed + 10_000 + config.run.seed),
    )
    complete = tapes[tapes["full_bytes"].notna()]
    byte_tick = int(cast(Any, complete["tick"].max()))
    byte_snapshot = complete[complete["tick"] == byte_tick].reset_index(drop=True)
    js_result = neighbor_bff_opcode_js_test(
        byte_snapshot,
        width=config.world.width,
        height=config.world.height,
        permutations=199,
        rng=np.random.default_rng(analysis_seed + 20_000 + config.run.seed),
    )
    births = int((events["event_type"] == "offspring_born").sum())
    blocked_pool = event_count(events, "reproduction_blocked_pool")
    blocked_space = event_count(events, "reproduction_blocked_no_space")
    family_counts = family_snapshot["content_hash"].value_counts().to_numpy(dtype=np.int64)
    max_depth = lineage_depth(lineage)
    summary.update(
        {
            "placement_radius": config.reproduction.placement_radius,
            "reproductive_births": births,
            "reproduction_blocked_pool": blocked_pool,
            "reproduction_blocked_no_space": blocked_space,
            "max_lineage_depth": max_depth,
            "live_reproductive_descendant_fraction": sum(tape_id in parents for tape_id in tape_ids) / len(tape_ids),
            "neutral_family_q1": hill_number(family_counts, 1.0),
            "family_neighbor_observed": family_result.observed,
            "family_neighbor_null": family_result.null_mean,
            "family_neighbor_excess": family_result.excess,
            "family_neighbor_p": family_result.p_value,
            "root_neighbor_excess": root_result.excess,
            "root_neighbor_p": root_result.p_value,
            "opcode_js_excess": js_result.excess,
            "lineage_patch_feasible": bool(
                summary["successful_exit"]
                and summary["conserved"]
                and int(summary["invariant_failures"]) == 0
                and 0.40 <= float(summary["late_mean_occupied_fraction"]) <= 0.95
                and float(summary["late_active_interaction_fraction"]) > 0.0
                and int(summary["late_successful_writes"]) > 0
                and int(summary["dissolutions"]) > 0
                and int(summary["placements"]) > 0
                and int(summary["late_pool_changes"]) > 0
                and births > 0
                and blocked_pool <= births
            ),
        }
    )
    return summary


def paired_results(runs: pd.DataFrame) -> tuple[np.ndarray[Any, np.dtype[np.float64]], float, float, float]:
    """Return local-minus-wide family-neighbor effects and frozen inference."""

    pivot = runs.pivot(index="seed", columns="placement_radius", values="family_neighbor_excess")
    if 1 not in pivot.columns or 8 not in pivot.columns or len(pivot) != 10 or pivot.isna().any().any():
        raise ValueError("patch campaign requires ten complete matched pairs")
    differences = (pivot[1] - pivot[8]).to_numpy(dtype=np.float64)
    p_value = exact_paired_sign_flip_greater(differences)
    lower, upper = paired_bootstrap_interval(differences, resamples=10_000, seed=20260909)
    return differences, p_value, lower, upper


def group_summary(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate both offspring placement treatments."""

    return (
        runs.groupby("placement_radius", sort=True)
        .agg(
            runs=("seed", "size"),
            feasible=("lineage_patch_feasible", "sum"),
            median_births=("reproductive_births", "median"),
            median_depth=("max_lineage_depth", "median"),
            median_occupancy=("late_mean_occupied_fraction", "median"),
            mean_family_excess=("family_neighbor_excess", "mean"),
            significant_family=("family_neighbor_p", lambda values: int((values <= 0.05).sum())),
            mean_root_excess=("root_neighbor_excess", "mean"),
            mean_descendant_fraction=("live_reproductive_descendant_fraction", "mean"),
            mean_family_q1=("neutral_family_q1", "mean"),
            mean_opcode_js_excess=("opcode_js_excess", "mean"),
            pool_blocks=("reproduction_blocked_pool", "sum"),
            space_blocks=("reproduction_blocked_no_space", "sum"),
            conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
        )
        .reset_index()
    )


def write_report(runs: pd.DataFrame, groups: pd.DataFrame, target: Path) -> None:
    """Apply the frozen neutral lineage-patch decision."""

    differences, p_value, lower, upper = paired_results(runs)
    positives = int(np.count_nonzero(differences > 0.0))
    feasible = runs.groupby("placement_radius")["lineage_patch_feasible"].sum()
    births = runs.groupby("placement_radius")["reproductive_births"].median()
    depths = runs.groupby("placement_radius")["max_lineage_depth"].median()
    supported = bool(
        float(differences.mean()) > 0.0
        and lower > 0.0
        and p_value <= 0.05
        and positives >= 8
        and int(feasible.loc[1]) >= 8
        and int(feasible.loc[8]) >= 8
        and float(births.loc[1]) >= 75
        and float(births.loc[8]) >= 75
        and float(depths.loc[1]) >= 2
        and float(depths.loc[8]) >= 2
    )
    lines = [
        "# Stage 3R neutral lineage-patch result",
        "",
        "## Decision",
        "",
        f"Preregistered neutral lineage-patch mechanism supported: **{supported}**.",
        "",
        f"- Mean placement-radius-1 minus radius-8 family-neighbor excess: {float(differences.mean()):.6f}",
        f"- Median paired effect: {float(np.median(differences)):.6f}",
        f"- 95% paired bootstrap interval: [{lower:.6f}, {upper:.6f}]",
        f"- Exact one-sided sign-flip p: {p_value:.6f}",
        f"- Positive effects: {positives}/10",
        "",
        "| placement radius | feasible | births | depth | occupancy | family excess | significant | exact-root excess | live descendants | family q1 | opcode JS excess | pool blocks | space blocks |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(
            f"| {int(row['placement_radius'])} | {int(row['feasible'])}/{int(row['runs'])} | "
            f"{float(row['median_births']):.0f} | {float(row['median_depth']):.0f} | "
            f"{float(row['median_occupancy']):.3f} | {float(row['mean_family_excess']):.6f} | "
            f"{int(row['significant_family'])}/{int(row['runs'])} | {float(row['mean_root_excess']):.6f} | "
            f"{float(row['mean_descendant_fraction']):.3f} | {float(row['mean_family_q1']):.2f} | "
            f"{float(row['mean_opcode_js_excess']):.6f} | {int(row['pool_blocks'])} | {int(row['space_blocks'])} |"
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
        "",
        "Neutral modulo-root families are an offline measurement device. Scheduled clone birth and family clustering do not establish endogenous replication, organisms, or adaptation.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--permutations", type=int, default=999)
    parser.add_argument("--analysis-seed", type=int, default=20260909)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage3r_lineage_patch_runs.csv"))
    parser.add_argument("--groups-output", type=Path, default=Path("reports/stage3r_lineage_patch_groups.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage3r_lineage_patch_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", PLACEMENT_RADIUS}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"patch index missing columns: {sorted(missing)}")
    runs = pd.DataFrame(
        [summarize_patch_run(Path(str(row["run_dir"])), permutations=args.permutations, analysis_seed=args.analysis_seed) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))]
    ).sort_values(["placement_radius", "seed"], ignore_index=True)
    if len(runs) != 20 or runs.groupby("placement_radius")["seed"].nunique().min() != 10:
        raise ValueError("patch campaign requires two complete ten-seed cells")
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
