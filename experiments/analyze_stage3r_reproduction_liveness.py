"""Analyze and select the preregistered Stage 3R reproduction liveness rate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import pandas as pd

from analysis.load import load_run
from experiments.analyze_phase2_liveness_pilot import summarize_run
from soup.config import Config


RATE = "reproduction.rate"


def event_count(events: pd.DataFrame, event_type: str) -> int:
    """Count singleton events or aggregate count fields for one event type."""

    selected = events[events["event_type"] == event_type]
    total = 0
    for details in selected["details_json"]:
        parsed = json.loads(str(details))
        total += int(parsed.get("count", 1))
    return total


def lineage_depth(lineage: pd.DataFrame) -> int:
    """Return maximum one-parent reproductive lineage depth."""

    parents: dict[int, int] = {}
    for row in lineage.itertuples(index=False):
        progenitors = list(cast(Any, row.progenitor_ids))
        if len(progenitors) == 1:
            parents[int(cast(Any, row.tape_id))] = int(cast(Any, progenitors[0]))
    depths: dict[int, int] = {}

    def depth(tape_id: int, visiting: set[int]) -> int:
        if tape_id in depths:
            return depths[tape_id]
        if tape_id in visiting:
            raise ValueError("lineage contains a cycle")
        parent = parents.get(tape_id)
        value = 0 if parent is None else 1 + depth(parent, visiting | {tape_id})
        depths[tape_id] = value
        return value

    ids = set(parents) | set(parents.values())
    return max((depth(tape_id, set()) for tape_id in ids), default=0)


def summarize(run_dir: Path) -> dict[str, Any]:
    """Return frozen non-spatial selection outcomes for one liveness run."""

    config = Config.load(run_dir / "config.toml")
    summary = summarize_run(
        run_dir,
        dissolution_rate=config.dissolution.spontaneous_rate,
        reseed_rate=config.world.reseed_rate,
        permutations=19,
        analysis_seed=20260906,
    )
    data = load_run(run_dir)
    events = data.table("events")
    lineage = data.table("lineage")
    births = int((events["event_type"] == "offspring_born").sum())
    blocked_space = event_count(events, "reproduction_blocked_no_space")
    blocked_pool = event_count(events, "reproduction_blocked_pool")
    max_depth = lineage_depth(lineage)
    summary.update(
        {
            "reproduction_rate": config.reproduction.rate,
            "reproductive_births": births,
            "reproduction_blocked_no_space": blocked_space,
            "reproduction_blocked_pool": blocked_pool,
            "reproduction_attempts_observed": births + blocked_space + blocked_pool,
            "max_lineage_depth": max_depth,
            "reproduction_feasible": bool(
                summary["successful_exit"]
                and summary["conserved"]
                and int(summary["invariant_failures"]) == 0
                and 0.40 <= float(summary["late_mean_occupied_fraction"]) <= 0.90
                and births >= 25
                and int(summary["dissolutions"]) > 0
                and int(summary["placements"]) > 0
                and float(summary["late_active_interaction_fraction"]) > 0.0
                and int(summary["late_successful_writes"]) > 0
                and int(summary["late_pool_changes"]) > 0
                and blocked_pool <= births
                and max_depth >= 2
            ),
        }
    )
    return summary


def group_summary(runs: pd.DataFrame) -> pd.DataFrame:
    """Apply the frozen eligibility and ranking fields."""

    groups = (
        runs.groupby("reproduction_rate", sort=True)
        .agg(
            runs=("seed", "size"),
            feasible=("reproduction_feasible", "sum"),
            median_births=("reproductive_births", "median"),
            median_occupancy=("late_mean_occupied_fraction", "median"),
            median_pool_blocks=("reproduction_blocked_pool", "median"),
            median_space_blocks=("reproduction_blocked_no_space", "median"),
            median_max_depth=("max_lineage_depth", "median"),
            conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
        )
        .reset_index()
    )
    groups["eligible"] = groups["feasible"] >= 2
    groups["birth_distance"] = (groups["median_births"] - 75).abs()
    groups["occupancy_distance"] = (groups["median_occupancy"] - 0.75).abs()
    return groups.sort_values(
        ["eligible", "feasible", "birth_distance", "occupancy_distance", "reproduction_rate"],
        ascending=[False, False, True, True, True],
        ignore_index=True,
    )


def write_report(groups: pd.DataFrame, target: Path) -> None:
    """Write the frozen rate selection without spatial family outcomes."""

    eligible = groups[groups["eligible"]]
    selected = None if eligible.empty else float(cast(Any, eligible.iloc[0]["reproduction_rate"]))
    lines = [
        "# Stage 3R reproduction liveness pilot",
        "",
        "## Decision",
        "",
        (f"Selected reproduction rate: **{selected:g}**." if selected is not None else "**No reproduction rate selected.**"),
        "",
        "No lineage-family spatial statistic was computed for selection.",
        "",
        "| rate | feasible | births | occupancy | pool blocks | space blocks | lineage depth | eligible |",
        "|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(
            f"| {float(row['reproduction_rate']):g} | {int(row['feasible'])}/{int(row['runs'])} | "
            f"{float(row['median_births']):.0f} | {float(row['median_occupancy']):.3f} | "
            f"{float(row['median_pool_blocks']):.0f} | {float(row['median_space_blocks']):.0f} | "
            f"{float(row['median_max_depth']):.0f} | {bool(row['eligible'])} |"
        )
    lines += [
        "",
        "Stage 3R scheduled cloning remains a neutral mechanism probe, not endogenous self-replication or the energy-ledger Stage 3 gate.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage3r_reproduction_liveness_runs.csv"))
    parser.add_argument("--groups-output", type=Path, default=Path("reports/stage3r_reproduction_liveness_groups.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage3r_reproduction_liveness_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", RATE}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"liveness index missing columns: {sorted(missing)}")
    runs = pd.DataFrame(
        [summarize(Path(str(row["run_dir"]))) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))]
    ).sort_values(["reproduction_rate", "seed"], ignore_index=True)
    if len(runs) != 12 or runs.groupby("reproduction_rate")["seed"].nunique().min() != 3:
        raise ValueError("liveness pilot requires four complete three-seed cells")
    groups = group_summary(runs)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    groups.to_csv(args.groups_output, index=False)
    write_report(groups, args.report)
    print(args.runs_output)
    print(args.groups_output)
    print(args.report)


if __name__ == "__main__":
    main()
