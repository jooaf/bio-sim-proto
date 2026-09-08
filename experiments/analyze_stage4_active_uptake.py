"""Analyze the preregistered Stage 4 active-uptake mechanics assay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run


SEEDS = set(range(202609210, 202609215))


def summarize(run_dir: Path) -> dict[str, Any]:
    data = load_run(run_dir)
    ticks = data.table("ticks").sort_values("tick", ignore_index=True)
    interactions = data.table("interactions")
    events = data.table("events")
    uptake = events[events["event_type"] == "energy_uptake"]
    executions = 0
    absorbed = 0.0
    for value in uptake["details_json"]:
        details = json.loads(str(value))
        executions += int(details["executions"])
        absorbed += float(details["energy_absorbed"])
    expected = ticks["energy_influx_cum"].to_numpy(dtype=np.float64)
    accounted = (
        ticks["energy_field_total"].to_numpy(dtype=np.float64)
        + ticks["energy_tape_total"].to_numpy(dtype=np.float64)
        + ticks["energy_dissipated_cum"].to_numpy(dtype=np.float64)
    )
    relative_error = np.abs(accounted - expected) / np.maximum(1.0, np.abs(expected))
    invariant_path = run_dir / "invariant_log.jsonl"
    final = ticks.iloc[-1]
    return {
        "run_dir": str(run_dir),
        "seed": data.config.run.seed,
        "active_uptake_enabled": data.config.energy.active_uptake_enabled,
        "successful_exit": data.manifest.get("exit_status") == "success",
        "invariant_failures": sum(
            bool(line)
            for line in invariant_path.read_text(encoding="utf-8").splitlines()
        ),
        "uptake_executions": executions,
        "energy_absorbed": absorbed,
        "total_steps": int(interactions["steps"].sum()),
        "final_tapes": int(final["n_tapes"]),
        "final_field_energy": float(final["energy_field_total"]),
        "final_tape_energy": float(final["energy_tape_total"]),
        "final_dissipated_energy": float(final["energy_dissipated_cum"]),
        "final_influx": float(final["energy_influx_cum"]),
        "max_relative_energy_error": float(relative_error.max()),
    }


def passes_gate(runs: pd.DataFrame) -> bool:
    disabled = runs[~runs["active_uptake_enabled"]].set_index("seed")
    enabled = runs[runs["active_uptake_enabled"]].set_index("seed")
    if len(disabled) != 5 or len(enabled) != 5 or set(disabled.index) != SEEDS or set(enabled.index) != SEEDS:
        return False
    return bool(
        (enabled["uptake_executions"] > 0).all()
        and (enabled["energy_absorbed"] > 0.0).all()
        and (disabled["uptake_executions"] == 0).all()
        and (disabled["energy_absorbed"] == 0.0).all()
        and (enabled["energy_absorbed"] > disabled["energy_absorbed"]).all()
        and (enabled["final_tape_energy"] > disabled["final_tape_energy"]).all()
        and (disabled["final_tape_energy"] == 0.0).all()
        and (runs["final_tapes"] == 8).all()
        and runs["successful_exit"].all()
        and int(runs["invariant_failures"].sum()) == 0
        and (runs["max_relative_energy_error"] <= 1e-9).all()
    )


def write_report(runs: pd.DataFrame, target: Path) -> None:
    groups = (
        runs.groupby("active_uptake_enabled", sort=True)
        .agg(
            runs=("seed", "size"),
            uptake_executions=("uptake_executions", "median"),
            energy_absorbed=("energy_absorbed", "median"),
            final_tape_energy=("final_tape_energy", "median"),
            total_steps=("total_steps", "median"),
            max_energy_error=("max_relative_energy_error", "max"),
        )
        .reset_index()
    )
    lines = [
        "# Stage 4 active energy-uptake mechanics assay",
        "",
        "## Decision",
        "",
        f"Execution-mediated energy-uptake positive control supported: **{passes_gate(runs)}**.",
        "",
        "| uptake enabled | runs | uptake executions | gross absorbed | final tape energy | steps | max energy error |",
        "|:---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(
            f"| {bool(row['active_uptake_enabled'])} | {int(row['runs'])} | "
            f"{float(row['uptake_executions']):.0f} | {float(row['energy_absorbed']):.6f} | "
            f"{float(row['final_tape_energy']):.6f} | {float(row['total_steps']):.0f} | "
            f"{float(row['max_energy_error']):.3e} |"
        )
    enabled = runs[runs["active_uptake_enabled"]]
    disabled = runs[~runs["active_uptake_enabled"]]
    lines += [
        "",
        f"- Enabled positive gross uptake: {int((enabled['energy_absorbed'] > 0).sum())}/5",
        f"- Disabled exact-zero uptake: {int((disabled['energy_absorbed'] == 0).sum())}/5",
        f"- Successful runs: {int(runs['successful_exit'].sum())}/10",
        f"- Invariant failures: {int(runs['invariant_failures'].sum())}",
        "",
        "This mechanics result establishes behaviorally accessible energy transfer only; it is not evidence of ecology or fitness.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)

    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage4_active_uptake_runs.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage4_active_uptake_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    if len(index) != 10 or set(index["seed"].astype(int)) != SEEDS or index["active_uptake_enabled"].nunique() != 2:
        raise ValueError("active uptake assay requires two complete five-seed arms")
    runs = pd.DataFrame(
        [summarize(Path(str(row["run_dir"]))) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))]
    ).sort_values(["active_uptake_enabled", "seed"], ignore_index=True)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    write_report(runs, args.report)
    print(args.runs_output)
    print(args.report)


if __name__ == "__main__":
    main()
