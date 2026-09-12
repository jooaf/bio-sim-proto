"""Analyze the fully connected signal-write reachability positive control."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import pandas as pd

from experiments.analyze_stage4_signal_write import summarize

SEEDS = set(range(202609280, 202609285))
ARMS = {"write_enabled", "write_disabled", "mismatched"}


def passes_gate(runs: pd.DataFrame) -> bool:
    enabled = runs[runs["arm"] == "write_enabled"]
    disabled = runs[runs["arm"] == "write_disabled"]
    mismatched = runs[runs["arm"] == "mismatched"]
    return bool(
        len(runs) == 15
        and (enabled["signal_writes"] == 16).all()
        and enabled["occupied_final_written"].all()
        and disabled["all_reads_one"].all()
        and disabled["all_dispatches_one"].all()
        and (disabled["signal_writes"] == 0).all()
        and disabled["field_unchanged"].all()
        and mismatched["all_reads_one"].all()
        and mismatched["all_dispatches_zero"].all()
        and (mismatched["signal_writes"] == 0).all()
        and mismatched["field_unchanged"].all()
        and runs["changed_targets_valid"].all()
        and (runs["final_tapes"] == 16).all()
        and (runs["interactions"] > 0).all()
        and runs["unchanged_tapes"].all()
        and runs["matter_total_constant"].all()
        and runs["successful_exit"].all()
        and int(runs["invariant_failures"].sum()) == 0
    )


def write_report(runs: pd.DataFrame, target: Path) -> None:
    groups = runs.groupby("arm").agg(
        runs=("seed", "size"), interactions=("interactions", "sum"),
        reads=("signal_reads", "sum"), dispatches=("signal_dispatches", "sum"),
        writes=("signal_writes", "sum"), final_written=("occupied_final_written", "sum"),
    ).reset_index()
    lines = [
        "# Stage 4 signal-write reachability positive control", "", "## Decision", "",
        f"Fully connected partner-cell signal writing supported: **{passes_gate(runs)}**.", "",
        "| arm | runs | interactions | reads | dispatches | changed writes | complete fields |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(f"| {row['arm']} | {int(row['runs'])} | {int(row['interactions'])} | {int(row['reads'])} | {int(row['dispatches'])} | {int(row['writes'])} | {int(row['final_written'])} |")
    lines += ["", "This positive control does not overturn S4S-I002 and establishes mechanics only under a fully connected interaction graph.", ""]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage4_signal_write_reachability_runs.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage4_signal_write_reachability_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    if len(index) != 15 or set(index["seed"].astype(int)) != SEEDS or set(index["arm"].astype(str)) != ARMS:
        raise ValueError("reachability campaign requires three complete five-seed arms")
    runs = pd.DataFrame([summarize(Path(str(row["run_dir"]))) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))]).sort_values(["arm", "seed"], ignore_index=True)
    runs.to_csv(args.runs_output, index=False)
    write_report(runs, args.report)
    print(args.runs_output); print(args.report)


if __name__ == "__main__":
    main()
