"""Analyze the task-relevant signal-modulation campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run
from experiments.analyze_stage4_resource_birth import exact_sign_test_greater

SEEDS = set(range(202609300, 202609310))


def summarize(run_dir: Path) -> dict[str, Any]:
    data = load_run(run_dir); ticks = data.table("ticks").sort_values("tick", ignore_index=True); tapes = data.table("tapes"); events = data.table("events")
    protocol = json.loads((run_dir / "task_modulation_protocol.json").read_text(encoding="utf-8"))
    type_by_id = {int(record["tape_id"]): str(record["type"]) for record in protocol["records"]}
    signal_events = events[events["event_type"] == "signal_dispatch"]
    correct_selections = 0; total_selections = 0; behavior_exact = True
    for row in signal_events.itertuples(index=False):
        item = json.loads(str(row.details_json)); type_name = type_by_id[int(cast(Any, row.tape_id))]
        tag = str(item["tag_hex"]); uptake = int(item["uptake_executions"]) > 0
        expected = (tag == "aabbccdd") if type_name == "correct" else (tag == "11223344")
        behavior_exact &= int(item["dispatches"]) == 1 and uptake == expected
        if int(cast(Any, row.tick)) >= 1:
            total_selections += 1; correct_selections += int(type_name == "correct")
    scores = pd.read_parquet(run_dir / "task_scores_final.parquet")
    expected_energy = ticks["energy_influx_cum"].to_numpy(dtype=np.float64)
    accounted = ticks["energy_field_total"].to_numpy(dtype=np.float64) + ticks["energy_tape_total"].to_numpy(dtype=np.float64) + ticks["energy_dissipated_cum"].to_numpy(dtype=np.float64)
    errors = np.abs(accounted - expected_energy) / np.maximum(1.0, np.abs(expected_energy)); invariant_path = run_dir / "invariant_log.jsonl"
    return {
        "run_dir": str(run_dir), "seed": data.config.run.seed, "task_enabled": bool(protocol["task_enabled"]),
        "correct_selections": correct_selections, "total_selections": total_selections,
        "correct_selection_fraction": correct_selections / total_selections,
        "behavior_exact": behavior_exact,
        "correct_scores_one": bool((scores.loc[scores["type"] == "correct", "score"] == 1.0).all()),
        "incorrect_scores_zero": bool((scores.loc[scores["type"] == "incorrect", "score"] == 0.0).all()),
        "all_scores_zero": bool((scores["score"] == 0.0).all()),
        "final_tapes": int(cast(Any, tapes[tapes["tick"] == tapes["tick"].max()]["tape_id"].nunique())),
        "two_immutable_types": bool(tapes["content_hash"].nunique() == 2 and (tapes.groupby("tape_id")["content_hash"].nunique() == 1).all()),
        "successful_exit": data.manifest.get("exit_status") == "success",
        "invariant_failures": sum(bool(line) for line in invariant_path.read_text(encoding="utf-8").splitlines()),
        "max_relative_energy_error": float(errors.max()),
    }


def paired_effects(runs: pd.DataFrame) -> pd.DataFrame:
    enabled = runs[runs["task_enabled"]].set_index("seed"); disabled = runs[~runs["task_enabled"]].set_index("seed")
    paired = enabled[["correct_selection_fraction"]].join(disabled[["correct_selection_fraction"]].add_prefix("disabled_")); paired["selection_effect"] = paired["correct_selection_fraction"] - paired["disabled_correct_selection_fraction"]; return paired.reset_index()


def passes_gate(runs: pd.DataFrame, paired: pd.DataFrame) -> bool:
    enabled = runs[runs["task_enabled"]]; disabled = runs[~runs["task_enabled"]]
    return bool(len(runs) == 20 and (paired["selection_effect"] > 0).all() and exact_sign_test_greater(paired["selection_effect"].to_numpy(dtype=np.float64)) == 1/1024 and (enabled["correct_selection_fraction"] >= 0.70).all() and disabled["correct_selection_fraction"].between(0.45, 0.55).all() and enabled["correct_scores_one"].all() and enabled["incorrect_scores_zero"].all() and disabled["all_scores_zero"].all() and runs["behavior_exact"].all() and (runs["final_tapes"] == 16).all() and runs["two_immutable_types"].all() and runs["successful_exit"].all() and int(runs["invariant_failures"].sum()) == 0 and (runs["max_relative_energy_error"] <= 1e-9).all())


def write_report(runs: pd.DataFrame, paired: pd.DataFrame, target: Path) -> None:
    groups = runs.groupby("task_enabled").agg(runs=("seed", "size"), mean_fraction=("correct_selection_fraction", "mean"), min_fraction=("correct_selection_fraction", "min"), max_fraction=("correct_selection_fraction", "max"), max_error=("max_relative_energy_error", "max")).reset_index()
    lines = ["# Stage 4 task-relevant signal modulation", "", "## Decision", "", f"Task-relevant interaction modulation supported: **{passes_gate(runs, paired)}**.", "", f"- Paired effects positive: {int((paired['selection_effect'] > 0).sum())}/10", f"- Exact one-sided sign p: {exact_sign_test_greater(paired['selection_effect'].to_numpy(dtype=np.float64)):.8f}", "", "| task enabled | runs | mean correct-selection fraction | range | max error |", "|---|---:|---:|---:|---:|"]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")): lines.append(f"| {bool(row['task_enabled'])} | {int(row['runs'])} | {float(row['mean_fraction']):.6f} | {float(row['min_fraction']):.6f}–{float(row['max_fraction']):.6f} | {float(row['max_error']):.3e} |")
    lines += ["", "This supports task-relevant modulation of interaction opportunity only, not demographic fitness, adaptation, communication, coordination, or organization.", ""]; target.parent.mkdir(parents=True, exist_ok=True); target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("index", type=Path); parser.add_argument("--runs-output", type=Path, default=Path("reports/stage4_task_modulation_runs.csv")); parser.add_argument("--effects-output", type=Path, default=Path("reports/stage4_task_modulation_effects.csv")); parser.add_argument("--report", type=Path, default=Path("reports/stage4_task_modulation_report.md")); args = parser.parse_args()
    index = pd.read_parquet(args.index)
    if len(index) != 20 or set(index["seed"].astype(int)) != SEEDS: raise ValueError("task modulation requires two complete ten-seed arms")
    runs = pd.DataFrame([summarize(Path(str(row["run_dir"]))) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))]).sort_values(["task_enabled", "seed"], ignore_index=True); paired = paired_effects(runs); runs.to_csv(args.runs_output, index=False); paired.to_csv(args.effects_output, index=False); write_report(runs, paired, args.report); print(args.runs_output); print(args.effects_output); print(args.report)


if __name__ == "__main__": main()
