"""Analyze the preregistered Stage 4 local signal-write mechanics assay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import pandas as pd

from analysis.load import load_run

SEEDS = set(range(202609270, 202609275))
ARMS = {"write_enabled", "write_disabled", "mismatched"}


def summarize(run_dir: Path) -> dict[str, Any]:
    data = load_run(run_dir)
    ticks = data.table("ticks").sort_values("tick", ignore_index=True)
    tapes = data.table("tapes")
    events = data.table("events")
    protocol = json.loads((run_dir / "signal_write_protocol.json").read_text(encoding="utf-8"))
    signal_events = events[events["event_type"] == "signal_dispatch"]
    details = [json.loads(str(value)) for value in signal_events["details_json"]]
    reads = sum(int(item["reads"]) for item in details)
    dispatches = sum(int(item["dispatches"]) for item in details)
    writes = sum(int(item["writes"]) for item in details)
    occupied = {int(index) for index in protocol["occupied_indices"]}
    changed_targets_valid = all(
        tuple(int(value) for value in item["partner_cell"])
        in {
            (index % data.config.world.width, index // data.config.world.width)
            for index in occupied
        }
        for item in details
        if int(item["writes"]) > 0
    )
    initial = pd.read_parquet(run_dir / "signal_profile_initial.parquet")
    final = pd.read_parquet(run_dir / "signal_profile_final.parquet")
    occupied_final = final[final["occupied"]]
    empty_initial = initial[~initial["occupied"]].sort_values("flat_index")
    empty_final = final[~final["occupied"]].sort_values("flat_index")
    invariant_path = run_dir / "invariant_log.jsonl"
    return {
        "run_dir": str(run_dir),
        "seed": data.config.run.seed,
        "arm": protocol["arm"],
        "interactions": int(ticks["n_interactions"].sum()),
        "signal_reads": reads,
        "signal_dispatches": dispatches,
        "signal_writes": writes,
        "all_reads_one": bool(len(details) == int(ticks["n_interactions"].sum()) and all(int(item["reads"]) == 1 for item in details)),
        "all_dispatches_one": bool(all(int(item["dispatches"]) == 1 for item in details)),
        "all_dispatches_zero": bool(dispatches == 0),
        "occupied_final_written": bool((occupied_final["tag_hex"] == "11223344").all()),
        "field_unchanged": bool(initial["tag_hex"].tolist() == final["tag_hex"].tolist()),
        "empty_cells_unchanged": bool(empty_initial["tag_hex"].tolist() == empty_final["tag_hex"].tolist()),
        "changed_targets_valid": changed_targets_valid,
        "final_tapes": int(cast(Any, tapes[tapes["tick"] == tapes["tick"].max()]["tape_id"].nunique())),
        "unchanged_tapes": bool(tapes["content_hash"].nunique() == 1),
        "matter_total_constant": bool(ticks["pool_total"].nunique() == 1 and ticks["n_tapes"].nunique() == 1),
        "successful_exit": data.manifest.get("exit_status") == "success",
        "invariant_failures": sum(bool(line) for line in invariant_path.read_text(encoding="utf-8").splitlines()),
    }


def passes_gate(runs: pd.DataFrame) -> bool:
    enabled = runs[runs["arm"] == "write_enabled"]
    disabled = runs[runs["arm"] == "write_disabled"]
    mismatched = runs[runs["arm"] == "mismatched"]
    return bool(
        len(runs) == 15
        and (enabled["signal_writes"] == 8).all()
        and enabled["occupied_final_written"].all()
        and disabled["all_reads_one"].all()
        and disabled["all_dispatches_one"].all()
        and (disabled["signal_writes"] == 0).all()
        and disabled["field_unchanged"].all()
        and mismatched["all_reads_one"].all()
        and mismatched["all_dispatches_zero"].all()
        and (mismatched["signal_writes"] == 0).all()
        and mismatched["field_unchanged"].all()
        and runs["empty_cells_unchanged"].all()
        and runs["changed_targets_valid"].all()
        and (runs["final_tapes"] == 8).all()
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
    lines = ["# Stage 4 local signal-write mechanics", "", "## Decision", "", f"Local partner-cell signal writing supported: **{passes_gate(runs)}**.", "", "| arm | runs | interactions | reads | dispatches | changed writes | runs with written occupied field |", "|---|---:|---:|---:|---:|---:|---:|"]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(f"| {row['arm']} | {int(row['runs'])} | {int(row['interactions'])} | {int(row['reads'])} | {int(row['dispatches'])} | {int(row['writes'])} | {int(row['final_written'])} |")
    lines += ["", "This is an atomic signal-write mechanics result only. Inter-tape response, coordination, niche construction, fitness, and adaptation were not tested.", ""]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage4_signal_write_runs.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage4_signal_write_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    if len(index) != 15 or set(index["seed"].astype(int)) != SEEDS or set(index["arm"].astype(str)) != ARMS:
        raise ValueError("signal-write campaign requires three complete five-seed arms")
    runs = pd.DataFrame([summarize(Path(str(row["run_dir"]))) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))]).sort_values(["arm", "seed"], ignore_index=True)
    runs.to_csv(args.runs_output, index=False)
    write_report(runs, args.report)
    print(args.runs_output); print(args.report)


if __name__ == "__main__":
    main()
