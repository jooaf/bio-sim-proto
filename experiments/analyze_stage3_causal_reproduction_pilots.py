"""Analyze the frozen vacancy-first and exact-copy Stage 3 mechanics pilots."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import pandas as pd

from analysis.load import load_run
from experiments.analyze_phase2_liveness_pilot import summarize_run
from experiments.analyze_stage3r_reproduction_liveness import event_count
from soup.config import Config


PLACEMENT_RADIUS = "reproduction.placement_radius"


def summarize(run_dir: Path) -> dict[str, Any]:
    """Return only preregistered mechanical outcomes for one pilot run."""

    config = Config.load(run_dir / "config.toml")
    summary = summarize_run(
        run_dir,
        dissolution_rate=config.dissolution.spontaneous_rate,
        reseed_rate=config.world.reseed_rate,
        permutations=19,
        analysis_seed=20260910,
    )
    events = load_run(run_dir).table("events")
    births = event_count(events, "offspring_born")
    blocked_space = event_count(events, "reproduction_blocked_no_space")
    blocked_pool = event_count(events, "reproduction_blocked_pool")
    blocked_parent = event_count(events, "reproduction_blocked_no_parent")
    invalidated = event_count(events, "reproduction_trigger_invalidated")
    triggers = event_count(events, "exact_copy_trigger")
    observed_attempts = births + blocked_space + blocked_pool + blocked_parent + invalidated
    summary.update(
        {
            "reproduction_trigger": config.reproduction.trigger,
            "placement_protocol": config.reproduction.placement_protocol,
            "placement_radius": config.reproduction.placement_radius,
            "births": births,
            "exact_copy_triggers": triggers,
            "blocked_no_space": blocked_space,
            "blocked_pool": blocked_pool,
            "blocked_no_parent": blocked_parent,
            "invalidated_triggers": invalidated,
            "observed_attempts": observed_attempts,
            "no_parent_fraction": blocked_parent / observed_attempts if observed_attempts else 0.0,
            "base_mechanical_feasible": bool(
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
    return summary


def load_campaign(index_path: Path) -> pd.DataFrame:
    """Summarize every indexed run without dropping failures."""

    index = pd.read_parquet(index_path)
    required = {"run_dir", "seed"}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"pilot index missing columns: {sorted(missing)}")
    return pd.DataFrame(
        [
            summarize(Path(str(row["run_dir"])))
            for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))
        ]
    )


def vacancy_groups(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the frozen vacancy-first mechanical endpoints."""

    return (
        runs.groupby("placement_radius", sort=True)
        .agg(
            runs=("seed", "size"),
            mechanically_feasible=("base_mechanical_feasible", "sum"),
            median_births=("births", "median"),
            attempts=("observed_attempts", "sum"),
            no_parent_blocks=("blocked_no_parent", "sum"),
            pool_blocks=("blocked_pool", "sum"),
            median_occupancy=("late_mean_occupied_fraction", "median"),
            conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
        )
        .reset_index()
        .assign(
            no_parent_fraction=lambda frame: frame["no_parent_blocks"]
            / frame["attempts"].clip(lower=1)
        )
    )


def decisions(vacancy: pd.DataFrame, exact: pd.DataFrame) -> tuple[bool, bool]:
    """Apply both frozen pilot gates."""

    births = vacancy.set_index("placement_radius")["median_births"]
    comparable_birth_ratio = float(births.min() / births.max()) if births.max() else 0.0
    vacancy_pass = bool(
        len(vacancy) == 2
        and int(vacancy["runs"].sum()) == 6
        and vacancy["conserved"].all()
        and int(vacancy["invariant_failures"].sum()) == 0
        and (vacancy["mechanically_feasible"] == vacancy["runs"]).all()
        and int(vacancy["pool_blocks"].sum()) == 0
        and (vacancy["no_parent_fraction"] <= 0.02).all()
        and (vacancy["median_births"] >= 50).all()
        and comparable_birth_ratio >= 0.90
    )
    exact_pass = bool(
        len(exact) == 3
        and exact["base_mechanical_feasible"].all()
        and exact["conserved"].all()
        and int(exact["invariant_failures"].sum()) == 0
        and int((exact["exact_copy_triggers"] > 0).sum()) >= 2
        and int((exact["births"] > 0).sum()) >= 2
        and int(exact["births"].sum()) >= 3
        and int(exact["blocked_pool"].sum()) <= int(exact["births"].sum())
    )
    return vacancy_pass, exact_pass


def write_report(
    vacancy: pd.DataFrame, exact: pd.DataFrame, target: Path
) -> None:
    """Write pilot decisions without forbidden family or composition outcomes."""

    vacancy_pass, exact_pass = decisions(vacancy, exact)
    births = vacancy.set_index("placement_radius")["median_births"]
    birth_ratio = float(births.min() / births.max()) if births.max() else 0.0
    lines = [
        "# Stage 3 causal reproduction mechanics pilots",
        "",
        "## Decisions",
        "",
        f"- Vacancy-first opportunity control feasible: **{vacancy_pass}**",
        f"- Interaction-gated exact-copy birth viable: **{exact_pass}**",
        "",
        "No lineage-family or spatial-composition endpoint was computed.",
        "",
        "## Vacancy-first pilot",
        "",
        "| radius | feasible | births | attempts | no-parent | fraction | pool blocks | occupancy | conserved | invariants |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], vacancy.to_dict(orient="records")):
        lines.append(
            f"| {int(row['placement_radius'])} | {int(row['mechanically_feasible'])}/{int(row['runs'])} | "
            f"{float(row['median_births']):.0f} | {int(row['attempts'])} | {int(row['no_parent_blocks'])} | "
            f"{float(row['no_parent_fraction']):.4f} | {int(row['pool_blocks'])} | "
            f"{float(row['median_occupancy']):.3f} | {bool(row['conserved'])} | {int(row['invariant_failures'])} |"
        )
    lines += [
        "",
        f"Matched-treatment median birth ratio: **{birth_ratio:.3f}**.",
        "",
        "## Exact-copy pilot",
        "",
        "| seed | feasible | triggers | births | invalidated | no-space | pool blocks | occupancy | conserved | invariants |",
        "|---:|:---:|---:|---:|---:|---:|---:|---:|:---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], exact.sort_values("seed").to_dict(orient="records")):
        lines.append(
            f"| {int(row['seed'])} | {bool(row['base_mechanical_feasible'])} | "
            f"{int(row['exact_copy_triggers'])} | {int(row['births'])} | "
            f"{int(row['invalidated_triggers'])} | {int(row['blocked_no_space'])} | "
            f"{int(row['blocked_pool'])} | {float(row['late_mean_occupied_fraction']):.3f} | "
            f"{bool(row['conserved'])} | {int(row['invariant_failures'])} |"
        )
    lines += [
        "",
        "A failed exact-copy pilot is a frozen negative result and does not permit weakening the byte-exact trigger.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vacancy_index", type=Path)
    parser.add_argument("exact_index", type=Path)
    parser.add_argument(
        "--runs-output",
        type=Path,
        default=Path("reports/stage3_causal_reproduction_pilot_runs.csv"),
    )
    parser.add_argument(
        "--groups-output",
        type=Path,
        default=Path("reports/stage3_vacancy_pilot_groups.csv"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/stage3_causal_reproduction_pilots_report.md"),
    )
    args = parser.parse_args()
    vacancy_runs = load_campaign(args.vacancy_index).sort_values(
        ["placement_radius", "seed"], ignore_index=True
    )
    exact_runs = load_campaign(args.exact_index).sort_values("seed", ignore_index=True)
    if (
        len(vacancy_runs) != 6
        or vacancy_runs.groupby("placement_radius")["seed"].nunique().min() != 3
    ):
        raise ValueError("vacancy pilot requires two complete three-seed cells")
    if len(exact_runs) != 3 or exact_runs["seed"].nunique() != 3:
        raise ValueError("exact-copy pilot requires three complete seeds")
    combined = pd.concat([vacancy_runs, exact_runs], ignore_index=True)
    groups = vacancy_groups(vacancy_runs)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(args.runs_output, index=False)
    groups.to_csv(args.groups_output, index=False)
    write_report(groups, exact_runs, args.report)
    print(args.runs_output)
    print(args.groups_output)
    print(args.report)


if __name__ == "__main__":
    main()
