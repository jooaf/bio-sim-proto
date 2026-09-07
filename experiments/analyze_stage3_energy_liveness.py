"""Analyze and select the preregistered Stage 3 energy operating point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run
from experiments.analyze_phase2_liveness_pilot import summarize_run
from soup.config import Config


INFLUX = "energy.influx_rate"


def starvation_deaths(events: pd.DataFrame) -> int:
    """Count death events whose factual cause includes starvation."""

    selected = events[events["event_type"] == "tape_dissolved"]
    count = 0
    for details in selected["details_json"]:
        cause = str(json.loads(str(details)).get("cause", ""))
        count += int("starved" in cause.split("+"))
    return count


def summarize(run_dir: Path) -> dict[str, Any]:
    """Return frozen energy-accounting and liveness outcomes."""

    config = Config.load(run_dir / "config.toml")
    summary = summarize_run(
        run_dir,
        dissolution_rate=config.dissolution.spontaneous_rate,
        reseed_rate=config.world.reseed_rate,
        permutations=19,
        analysis_seed=20260914,
    )
    data = load_run(run_dir)
    ticks = data.table("ticks")
    events = data.table("events")
    expected = ticks["energy_influx_cum"].to_numpy(dtype=np.float64)
    accounted = (
        ticks["energy_field_total"].to_numpy(dtype=np.float64)
        + ticks["energy_tape_total"].to_numpy(dtype=np.float64)
        + ticks["energy_dissipated_cum"].to_numpy(dtype=np.float64)
    )
    relative_error = np.abs(accounted - expected) / np.maximum(1.0, expected)
    final = ticks.iloc[-1]
    final_influx = float(final["energy_influx_cum"])
    dissipated_fraction = (
        float(final["energy_dissipated_cum"]) / final_influx
        if final_influx > 0.0
        else 0.0
    )
    starved = starvation_deaths(events)
    initial_population = round(
        config.world.width
        * config.world.height
        * config.symbols.initial_tape_fill
    )
    feasible = bool(
        summary["successful_exit"]
        and summary["conserved"]
        and int(summary["invariant_failures"]) == 0
        and float(relative_error.max(initial=0.0)) <= 1e-9
        and 0.40 <= float(summary["late_mean_occupied_fraction"]) <= 0.90
        and float(summary["late_active_interaction_fraction"]) >= 0.50
        and int(summary["late_successful_writes"]) > 0
        and int(summary["late_pool_changes"]) > 0
        and 0.01 <= float(final["mean_tape_energy"]) <= 9.0
        and 0.05 <= dissipated_fraction <= 0.99
        and starved <= 0.5 * initial_population
    )
    summary.update(
        {
            "energy_influx_rate": config.energy.influx_rate,
            "max_relative_energy_error": float(relative_error.max(initial=0.0)),
            "final_field_energy": float(final["energy_field_total"]),
            "final_tape_energy": float(final["energy_tape_total"]),
            "final_mean_tape_energy": float(final["mean_tape_energy"]),
            "final_dissipated_energy": float(final["energy_dissipated_cum"]),
            "final_cumulative_influx": final_influx,
            "dissipated_fraction": dissipated_fraction,
            "starvation_deaths": starved,
            "energy_feasible": feasible,
        }
    )
    return summary


def group_summary(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate frozen selection fields by influx."""

    groups = (
        runs.groupby("energy_influx_rate", sort=True)
        .agg(
            runs=("seed", "size"),
            feasible=("energy_feasible", "sum"),
            max_energy_error=("max_relative_energy_error", "max"),
            median_active=("late_active_interaction_fraction", "median"),
            median_writes=("late_successful_writes", "median"),
            median_occupancy=("late_mean_occupied_fraction", "median"),
            median_mean_energy=("final_mean_tape_energy", "median"),
            median_dissipated_fraction=("dissipated_fraction", "median"),
            starvation_deaths=("starvation_deaths", "sum"),
            conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
        )
        .reset_index()
    )
    groups["eligible"] = groups["feasible"] == groups["runs"]
    return groups


def write_report(groups: pd.DataFrame, target: Path) -> None:
    """Apply the frozen lowest-eligible-influx selection rule."""

    eligible = groups[groups["eligible"]].sort_values("energy_influx_rate")
    selected = (
        None
        if eligible.empty
        else float(cast(Any, eligible.iloc[0]["energy_influx_rate"]))
    )
    lines = [
        "# Stage 3 energy-ledger liveness pilot",
        "",
        "## Decision",
        "",
        (
            "**No energy operating point selected.**"
            if selected is None
            else f"Selected total influx per tick: **{selected:g}**."
        ),
        "",
        "No lineage, composition, trophic, organization, or fitness endpoint was computed for selection.",
        "",
        "| influx | feasible | energy error | interactions | writes | occupancy | tape energy | dissipated | starvation | conserved | invariants | eligible |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---:|:---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(
            f"| {float(row['energy_influx_rate']):g} | {int(row['feasible'])}/{int(row['runs'])} | "
            f"{float(row['max_energy_error']):.3e} | {float(row['median_active']):.3f} | "
            f"{float(row['median_writes']):.0f} | {float(row['median_occupancy']):.3f} | "
            f"{float(row['median_mean_energy']):.3f} | {float(row['median_dissipated_fraction']):.3f} | "
            f"{int(row['starvation_deaths'])} | {bool(row['conserved'])} | "
            f"{int(row['invariant_failures'])} | {bool(row['eligible'])} |"
        )
    lines += [
        "",
        "This is an energy-accounting and liveness gate, not evidence of trophic structure.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage3_energy_liveness_runs.csv"))
    parser.add_argument("--groups-output", type=Path, default=Path("reports/stage3_energy_liveness_groups.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage3_energy_liveness_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", INFLUX}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"energy index missing columns: {sorted(missing)}")
    runs = pd.DataFrame(
        [
            summarize(Path(str(row["run_dir"])))
            for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))
        ]
    ).sort_values(["energy_influx_rate", "seed"], ignore_index=True)
    if len(runs) != 9 or runs.groupby("energy_influx_rate")["seed"].nunique().min() != 3:
        raise ValueError("energy pilot requires three complete three-seed cells")
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
