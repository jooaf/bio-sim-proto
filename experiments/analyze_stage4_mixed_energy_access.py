"""Analyze the preregistered Stage 4 mixed-population energy-access assay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run
from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater


SEEDS = set(range(202609220, 202609225))


def summarize(run_dir: Path) -> dict[str, Any]:
    data = load_run(run_dir)
    ticks = data.table("ticks").sort_values("tick", ignore_index=True)
    tapes = data.table("tapes")
    interactions = data.table("interactions")
    events = data.table("events")
    protocol = json.loads(
        (run_dir / "mixed_access_protocol.json").read_text(encoding="utf-8")
    )
    type_by_id = {
        int(record["tape_id"]): str(record["type"])
        for record in protocol["records"]
    }
    typed_tapes = tapes.copy()
    typed_tapes["type"] = typed_tapes["tape_id"].map(type_by_id)
    if typed_tapes["type"].isna().any():
        raise ValueError(f"unlabelled tape in immutable mixed assay: {run_dir}")
    counts = typed_tapes.groupby(["tick", "type"]).size().unstack(fill_value=0)
    if len(counts) != 200 or not (counts[["uptake", "control"]] == 4).all().all():
        raise ValueError(f"mixed assay type counts changed: {run_dir}")
    energy_by_tick = typed_tapes.groupby(["tick", "type"])["energy"].mean().unstack()
    final = energy_by_tick.loc[199]
    active_types = interactions["a_id"].map(type_by_id)
    steps_by_type = interactions.assign(type=active_types).groupby("type")["steps"].sum()
    interactions_by_type = active_types.value_counts()
    uptake_executions = 0
    gross_uptake = 0.0
    for value in events.loc[events["event_type"] == "energy_uptake", "details_json"]:
        details = json.loads(str(value))
        uptake_executions += int(details["executions"])
        gross_uptake += float(details["energy_absorbed"])
    expected = ticks["energy_influx_cum"].to_numpy(dtype=np.float64)
    accounted = (
        ticks["energy_field_total"].to_numpy(dtype=np.float64)
        + ticks["energy_tape_total"].to_numpy(dtype=np.float64)
        + ticks["energy_dissipated_cum"].to_numpy(dtype=np.float64)
    )
    relative_error = np.abs(accounted - expected) / np.maximum(1.0, np.abs(expected))
    invariant_path = run_dir / "invariant_log.jsonl"
    final_tick = ticks.iloc[-1]
    uptake_final = float(cast(Any, final["uptake"]))
    control_final = float(cast(Any, final["control"]))
    return {
        "run_dir": str(run_dir),
        "seed": data.config.run.seed,
        "active_uptake_enabled": data.config.energy.active_uptake_enabled,
        "successful_exit": data.manifest.get("exit_status") == "success",
        "invariant_failures": sum(
            bool(line)
            for line in invariant_path.read_text(encoding="utf-8").splitlines()
        ),
        "final_tapes": int(final_tick["n_tapes"]),
        "uptake_type_final_energy": uptake_final,
        "control_type_final_energy": control_final,
        "final_energy_difference": uptake_final - control_final,
        "uptake_type_energy_area": float(energy_by_tick["uptake"].sum()),
        "control_type_energy_area": float(energy_by_tick["control"].sum()),
        "energy_area_difference": float(
            energy_by_tick["uptake"].sum() - energy_by_tick["control"].sum()
        ),
        "uptake_type_active_interactions": int(interactions_by_type.get("uptake", 0)),
        "control_type_active_interactions": int(interactions_by_type.get("control", 0)),
        "uptake_type_steps": int(steps_by_type.get("uptake", 0)),
        "control_type_steps": int(steps_by_type.get("control", 0)),
        "uptake_executions": uptake_executions,
        "gross_uptake": gross_uptake,
        "final_field_energy": float(final_tick["energy_field_total"]),
        "final_tape_energy": float(final_tick["energy_tape_total"]),
        "final_dissipated_energy": float(final_tick["energy_dissipated_cum"]),
        "max_relative_energy_error": float(relative_error.max()),
    }


def primary_p(runs: pd.DataFrame) -> float:
    enabled = runs[runs["active_uptake_enabled"]]
    return exact_paired_sign_flip_greater(
        enabled["final_energy_difference"].to_numpy(dtype=np.float64)
    )


def passes_gate(runs: pd.DataFrame) -> bool:
    disabled = runs[~runs["active_uptake_enabled"]]
    enabled = runs[runs["active_uptake_enabled"]]
    if len(disabled) != 5 or len(enabled) != 5:
        return False
    return bool(
        (enabled["final_energy_difference"] > 0.0).all()
        and primary_p(runs) <= 0.05
        and (enabled["energy_area_difference"] > 0.0).all()
        and (enabled["uptake_type_final_energy"] > 0.0).all()
        and (enabled["uptake_type_steps"] > 0).all()
        and (enabled["control_type_final_energy"] == 0.0).all()
        and (enabled["control_type_steps"] == 0).all()
        and (enabled["gross_uptake"] > 0.0).all()
        and (disabled["gross_uptake"] == 0.0).all()
        and (disabled["final_tape_energy"] == 0.0).all()
        and (disabled["uptake_type_steps"] == 0).all()
        and (disabled["control_type_steps"] == 0).all()
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
            uptake_final_energy=("uptake_type_final_energy", "median"),
            control_final_energy=("control_type_final_energy", "median"),
            final_difference=("final_energy_difference", "median"),
            area_difference=("energy_area_difference", "median"),
            uptake_steps=("uptake_type_steps", "median"),
            control_steps=("control_type_steps", "median"),
            gross_uptake=("gross_uptake", "median"),
            max_energy_error=("max_relative_energy_error", "max"),
        )
        .reset_index()
    )
    enabled = runs[runs["active_uptake_enabled"]]
    lines = [
        "# Stage 4 mixed-population differentiated energy access",
        "",
        "## Decision",
        "",
        f"Mixed-population differentiated access supported: **{passes_gate(runs)}**.",
        "",
        f"- Enabled final-energy differences positive: {int((enabled['final_energy_difference'] > 0).sum())}/5",
        f"- Exact one-sided sign p: {primary_p(runs):.6f}",
        f"- Enabled energy-area differences positive: {int((enabled['energy_area_difference'] > 0).sum())}/5",
        "",
        "| uptake enabled | runs | uptake energy | control energy | difference | area difference | uptake steps | control steps | gross uptake | max error |",
        "|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(
            f"| {bool(row['active_uptake_enabled'])} | {int(row['runs'])} | "
            f"{float(row['uptake_final_energy']):.6f} | {float(row['control_final_energy']):.6f} | "
            f"{float(row['final_difference']):.6f} | {float(row['area_difference']):.6f} | "
            f"{float(row['uptake_steps']):.0f} | {float(row['control_steps']):.0f} | "
            f"{float(row['gross_uptake']):.6f} | {float(row['max_energy_error']):.3e} |"
        )
    lines += [
        "",
        f"- Successful runs: {int(runs['successful_exit'].sum())}/10",
        f"- Invariant failures: {int(runs['invariant_failures'].sum())}",
        "",
        "This establishes coexisting type-specific access in a uniform field, not fitness or ecology.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage4_mixed_energy_access_runs.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage4_mixed_energy_access_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    if (
        len(index) != 10
        or set(index["seed"].astype(int)) != SEEDS
        or index.groupby("active_uptake_enabled")["seed"].nunique().min() != 5
    ):
        raise ValueError("mixed access assay requires two complete five-seed arms")
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
