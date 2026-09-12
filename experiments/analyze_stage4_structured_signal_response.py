"""Analyze structured read-only environmental signal response."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run

SEEDS = set(range(202609290, 202609295))
ARMS = {"split", "uniform", "disabled"}


def summarize(run_dir: Path) -> dict[str, Any]:
    data = load_run(run_dir)
    ticks = data.table("ticks").sort_values("tick", ignore_index=True)
    tapes = data.table("tapes")
    events = data.table("events")
    protocol = json.loads((run_dir / "structured_signal_response_protocol.json").read_text(encoding="utf-8"))
    signal_rows = events[events["event_type"] == "signal_dispatch"]
    details = [json.loads(str(value)) for value in signal_rows["details_json"]]
    cell_uptake = np.zeros(16, dtype=np.int64)
    spatial_rule_exact = True
    for item in details:
        x, y = (int(value) for value in item["cell"])
        uptake = int(item["uptake_executions"])
        cell_uptake[y * 4 + x] += uptake
        if protocol["arm"] == "split":
            spatial_rule_exact &= uptake == int(x < 2)
    final_tick = int(cast(Any, tapes["tick"].max()))
    final_tapes = tapes[tapes["tick"] == final_tick]
    left_energy = final_tapes[final_tapes["cell_x"] < 2]["energy"]
    right_energy = final_tapes[final_tapes["cell_x"] >= 2]["energy"]
    expected = ticks["energy_influx_cum"].to_numpy(dtype=np.float64)
    accounted = ticks["energy_field_total"].to_numpy(dtype=np.float64) + ticks["energy_tape_total"].to_numpy(dtype=np.float64) + ticks["energy_dissipated_cum"].to_numpy(dtype=np.float64)
    errors = np.abs(accounted - expected) / np.maximum(1.0, np.abs(expected))
    invariant_path = run_dir / "invariant_log.jsonl"
    return {
        "run_dir": str(run_dir), "seed": data.config.run.seed, "arm": protocol["arm"],
        "interactions": int(ticks["n_interactions"].sum()),
        "signal_reads": sum(int(item["reads"]) for item in details),
        "signal_dispatches": sum(int(item["dispatches"]) for item in details),
        "uptake_executions": int(cell_uptake.sum()),
        "all_reads_dispatch": bool(len(details) == int(ticks["n_interactions"].sum()) and all(int(item["reads"]) == 1 and int(item["dispatches"]) == 1 for item in details)),
        "spatial_rule_exact": spatial_rule_exact,
        "left_all_uptake": bool((cell_uptake.reshape(4, 4)[:, :2] > 0).all()),
        "right_zero_uptake": bool((cell_uptake.reshape(4, 4)[:, 2:] == 0).all()),
        "all_cells_uptake": bool((cell_uptake > 0).all()),
        "all_cells_zero_uptake": bool((cell_uptake == 0).all()),
        "left_mean_energy": float(left_energy.mean()),
        "right_mean_energy": float(right_energy.mean()),
        "final_tapes": len(final_tapes),
        "unchanged_tapes": bool(tapes["content_hash"].nunique() == 1),
        "successful_exit": data.manifest.get("exit_status") == "success",
        "invariant_failures": sum(bool(line) for line in invariant_path.read_text(encoding="utf-8").splitlines()),
        "max_relative_energy_error": float(errors.max()),
    }


def passes_gate(runs: pd.DataFrame) -> bool:
    split = runs[runs["arm"] == "split"]
    uniform = runs[runs["arm"] == "uniform"]
    disabled = runs[runs["arm"] == "disabled"]
    return bool(
        len(runs) == 15
        and split["all_reads_dispatch"].all() and split["spatial_rule_exact"].all()
        and split["left_all_uptake"].all() and split["right_zero_uptake"].all()
        and (split["left_mean_energy"] > 0.0).all() and (split["right_mean_energy"] == 0.0).all()
        and uniform["all_reads_dispatch"].all() and uniform["all_cells_uptake"].all()
        and (uniform["left_mean_energy"] > 0.0).all() and (uniform["right_mean_energy"] > 0.0).all()
        and (disabled["signal_reads"] == 0).all() and (disabled["signal_dispatches"] == 0).all()
        and disabled["all_cells_zero_uptake"].all()
        and (disabled["left_mean_energy"] == 0.0).all() and (disabled["right_mean_energy"] == 0.0).all()
        and (runs["final_tapes"] == 16).all() and runs["unchanged_tapes"].all()
        and runs["successful_exit"].all() and int(runs["invariant_failures"].sum()) == 0
        and (runs["max_relative_energy_error"] <= 1e-9).all()
    )


def write_report(runs: pd.DataFrame, target: Path) -> None:
    groups = runs.groupby("arm").agg(runs=("seed", "size"), interactions=("interactions", "sum"), reads=("signal_reads", "sum"), dispatches=("signal_dispatches", "sum"), uptake=("uptake_executions", "sum"), left_energy=("left_mean_energy", "mean"), right_energy=("right_mean_energy", "mean"), max_error=("max_relative_energy_error", "max")).reset_index()
    lines = ["# Stage 4 structured read-only signal response", "", "## Decision", "", f"Spatially conditional behavior supported: **{passes_gate(runs)}**.", "", "| arm | runs | interactions | reads | dispatches | uptake | left energy | right energy | max error |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(f"| {row['arm']} | {int(row['runs'])} | {int(row['interactions'])} | {int(row['reads'])} | {int(row['dispatches'])} | {int(row['uptake'])} | {float(row['left_energy']):.6f} | {float(row['right_energy']):.6f} | {float(row['max_error']):.3e} |")
    lines += ["", "This supports spatially conditional behavior by one immutable tape under read-only environmental signals. It does not establish communication, coordination, fitness, adaptation, or organization.", ""]
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage4_structured_signal_response_runs.csv")); parser.add_argument("--report", type=Path, default=Path("reports/stage4_structured_signal_response_report.md")); args = parser.parse_args()
    index = pd.read_parquet(args.index)
    if len(index) != 15 or set(index["seed"].astype(int)) != SEEDS or set(index["arm"].astype(str)) != ARMS: raise ValueError("structured response requires three complete five-seed arms")
    runs = pd.DataFrame([summarize(Path(str(row["run_dir"]))) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))]).sort_values(["arm", "seed"], ignore_index=True)
    runs.to_csv(args.runs_output, index=False); write_report(runs, args.report); print(args.runs_output); print(args.report)


if __name__ == "__main__": main()
