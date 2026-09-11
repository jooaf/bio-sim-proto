"""Analyze the preregistered Stage 4 exact-tag signal-dispatch assay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run

SEEDS = set(range(202609260, 202609265))
ARMS = {"matched", "mismatched", "disabled"}


def summarize(run_dir: Path) -> dict[str, Any]:
    data = load_run(run_dir)
    ticks = data.table("ticks").sort_values("tick", ignore_index=True)
    interactions = data.table("interactions")
    tapes = data.table("tapes")
    events = data.table("events")
    protocol = json.loads((run_dir / "signal_dispatch_protocol.json").read_text(encoding="utf-8"))
    uptake_events = events[events["event_type"] == "energy_uptake"]
    uptake_executions = sum(int(json.loads(str(value))["executions"]) for value in uptake_events["details_json"])
    gross_uptake = sum(float(json.loads(str(value))["energy_absorbed"]) for value in uptake_events["details_json"])
    signal_events = events[events["event_type"] == "signal_dispatch"]
    signal_details = [json.loads(str(value)) for value in signal_events["details_json"]]
    signal_reads = sum(int(details["reads"]) for details in signal_details)
    signal_dispatches = sum(int(details["dispatches"]) for details in signal_details)
    final_tick = int(cast(Any, tapes["tick"].max()))
    final_tapes = tapes[tapes["tick"] == final_tick]
    expected = ticks["energy_influx_cum"].to_numpy(dtype=np.float64)
    accounted = (
        ticks["energy_field_total"].to_numpy(dtype=np.float64)
        + ticks["energy_tape_total"].to_numpy(dtype=np.float64)
        + ticks["energy_dissipated_cum"].to_numpy(dtype=np.float64)
    )
    errors = np.abs(accounted - expected) / np.maximum(1.0, np.abs(expected))
    invariant_path = run_dir / "invariant_log.jsonl"
    return {
        "run_dir": str(run_dir),
        "seed": data.config.run.seed,
        "arm": protocol["arm"],
        "interactions": len(interactions),
        "signal_reads": signal_reads,
        "signal_dispatches": signal_dispatches,
        "all_reads_one": bool(len(signal_details) == len(interactions) and all(int(details["reads"]) == 1 for details in signal_details)),
        "all_reads_zero": bool(signal_reads == 0),
        "all_dispatches_one": bool(len(signal_details) == len(interactions) and all(int(details["dispatches"]) == 1 for details in signal_details)),
        "all_dispatches_zero": bool(signal_dispatches == 0),
        "uptake_executions": uptake_executions,
        "gross_uptake": gross_uptake,
        "final_tapes": len(final_tapes),
        "final_mean_energy": float(final_tapes["energy"].mean()),
        "unchanged_tapes": bool(tapes["content_hash"].nunique() == 1),
        "successful_exit": data.manifest.get("exit_status") == "success",
        "invariant_failures": sum(bool(line) for line in invariant_path.read_text(encoding="utf-8").splitlines()),
        "max_relative_energy_error": float(errors.max()),
    }


def passes_gate(runs: pd.DataFrame) -> bool:
    matched = runs[runs["arm"] == "matched"]
    mismatched = runs[runs["arm"] == "mismatched"]
    disabled = runs[runs["arm"] == "disabled"]
    controls = runs[runs["arm"].isin(["mismatched", "disabled"])]
    return bool(
        len(runs) == 15
        and matched["all_reads_one"].all()
        and matched["all_dispatches_one"].all()
        and mismatched["all_reads_one"].all()
        and mismatched["all_dispatches_zero"].all()
        and disabled["all_reads_zero"].all()
        and disabled["all_dispatches_zero"].all()
        and (matched["uptake_executions"] > 0).all()
        and (matched["final_mean_energy"] > 0.0).all()
        and (controls["uptake_executions"] == 0).all()
        and (controls["final_mean_energy"] == 0.0).all()
        and (runs["final_tapes"] == 8).all()
        and (runs["interactions"] > 0).all()
        and runs["unchanged_tapes"].all()
        and runs["successful_exit"].all()
        and int(runs["invariant_failures"].sum()) == 0
        and (runs["max_relative_energy_error"] <= 1e-9).all()
    )


def write_report(runs: pd.DataFrame, target: Path) -> None:
    groups = runs.groupby("arm").agg(
        runs=("seed", "size"),
        interactions=("interactions", "sum"),
        reads=("signal_reads", "sum"),
        dispatches=("signal_dispatches", "sum"),
        uptake=("uptake_executions", "sum"),
        final_energy=("final_mean_energy", "mean"),
        max_error=("max_relative_energy_error", "max"),
    ).reset_index()
    lines = [
        "# Stage 4 exact-tag signal dispatch mechanics", "", "## Decision", "",
        f"Exact local signal dispatch supported: **{passes_gate(runs)}**.", "",
        "| arm | runs | interactions | reads | dispatches | uptake executions | mean final energy | max error |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(f"| {row['arm']} | {int(row['runs'])} | {int(row['interactions'])} | {int(row['reads'])} | {int(row['dispatches'])} | {int(row['uptake'])} | {float(row['final_energy']):.6f} | {float(row['max_error']):.3e} |")
    lines += ["", "This is an exact-tag dispatch mechanics result only. Signal writing, coordination, fitness, adaptation, and organization were not tested.", ""]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage4_signal_dispatch_runs.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage4_signal_dispatch_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    if len(index) != 15 or set(index["seed"].astype(int)) != SEEDS or set(index["arm"].astype(str)) != ARMS:
        raise ValueError("signal dispatch campaign requires three complete five-seed arms")
    runs = pd.DataFrame([summarize(Path(str(row["run_dir"]))) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))]).sort_values(["arm", "seed"], ignore_index=True)
    runs.to_csv(args.runs_output, index=False)
    write_report(runs, args.report)
    print(args.runs_output); print(args.report)


if __name__ == "__main__":
    main()
