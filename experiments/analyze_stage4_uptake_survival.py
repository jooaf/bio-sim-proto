"""Analyze the preregistered Stage 4 active-uptake survival campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run
from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater

SEEDS = set(range(202609240, 202609250))


def summarize(run_dir: Path) -> dict[str, Any]:
    data = load_run(run_dir)
    ticks = data.table("ticks").sort_values("tick", ignore_index=True)
    tapes = data.table("tapes")
    events = data.table("events")
    protocol = json.loads((run_dir / "uptake_survival_protocol.json").read_text(encoding="utf-8"))
    types = {int(record["tape_id"]): str(record["type"]) for record in protocol["records"]}
    deaths = events[events["event_type"] == "tape_dissolved"]
    dead_ids = {int(value) for value in deaths["tape_id"]}
    survivor_counts = {
        name: sum(tape_id not in dead_ids and type_name == name for tape_id, type_name in types.items())
        for name in ("uptake", "control")
    }
    causes = [str(json.loads(str(value)).get("cause", "")) for value in deaths["details_json"]]
    uptake_events = events[events["event_type"] == "energy_uptake"]
    gross_uptake = sum(float(json.loads(str(value))["energy_absorbed"]) for value in uptake_events["details_json"])
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
        "active_uptake_enabled": bool(protocol["active_uptake_enabled"]),
        "uptake_survivors": survivor_counts["uptake"],
        "control_survivors": survivor_counts["control"],
        "uptake_survival": survivor_counts["uptake"] / 64.0,
        "control_survival": survivor_counts["control"] / 64.0,
        "total_survivors": sum(survivor_counts.values()),
        "deaths": len(deaths),
        "all_deaths_starvation": bool(causes) and all(cause == "starved" for cause in causes),
        "gross_uptake": gross_uptake,
        "post_100_active_ticks": int(((ticks["tick"] >= 100) & (ticks["n_interactions"] > 0)).sum()),
        "type_consistent": bool((tapes.groupby("tape_id")["content_hash"].nunique() == 1).all()),
        "successful_exit": data.manifest.get("exit_status") == "success",
        "invariant_failures": sum(bool(line) for line in invariant_path.read_text(encoding="utf-8").splitlines()),
        "max_relative_energy_error": float(errors.max()),
    }


def effects(runs: pd.DataFrame) -> pd.DataFrame:
    enabled = runs[runs["active_uptake_enabled"]].copy()
    enabled["survival_effect"] = enabled["uptake_survival"] - enabled["control_survival"]
    return enabled[["seed", "uptake_survival", "control_survival", "survival_effect"]]


def passes_gate(runs: pd.DataFrame, paired: pd.DataFrame) -> bool:
    enabled = runs[runs["active_uptake_enabled"]]
    disabled = runs[~runs["active_uptake_enabled"]]
    p_value = exact_paired_sign_flip_greater(paired["survival_effect"].to_numpy(dtype=np.float64))
    return bool(
        len(runs) == 20
        and (paired["survival_effect"] > 0.0).all()
        and p_value == 1.0 / 1024.0
        and (enabled["uptake_survival"] >= 0.8).all()
        and (enabled["control_survival"] == 0.0).all()
        and (disabled["total_survivors"] == 0).all()
        and (enabled["total_survivors"] >= 2).all()
        and (enabled["post_100_active_ticks"] > 0).all()
        and (enabled["gross_uptake"] > 0.0).all()
        and runs["all_deaths_starvation"].all()
        and runs["type_consistent"].all()
        and runs["successful_exit"].all()
        and int(runs["invariant_failures"].sum()) == 0
        and (runs["max_relative_energy_error"] <= 1e-9).all()
    )


def write_report(runs: pd.DataFrame, paired: pd.DataFrame, target: Path) -> None:
    enabled = runs[runs["active_uptake_enabled"]]
    disabled = runs[~runs["active_uptake_enabled"]]
    p_value = exact_paired_sign_flip_greater(paired["survival_effect"].to_numpy(dtype=np.float64))
    lines = [
        "# Stage 4 active-uptake survival consequence",
        "", "## Decision", "",
        f"Causal starvation-survival consequence supported: **{passes_gate(runs, paired)}**.", "",
        f"- Enabled uptake survival range: {enabled['uptake_survival'].min():.3f}–{enabled['uptake_survival'].max():.3f}",
        f"- Enabled control survival range: {enabled['control_survival'].min():.3f}–{enabled['control_survival'].max():.3f}",
        f"- Primary survival difference positive: {int((paired['survival_effect'] > 0).sum())}/10",
        f"- Exact one-sided sign p: {p_value:.8f}",
        f"- Disabled final survivors: {int(disabled['total_survivors'].sum())} across 10 runs",
        f"- Maximum relative energy error: {runs['max_relative_energy_error'].max():.3e}",
        "", "The result is limited to differential survival under the frozen starvation regime. It does not establish adaptation, reproduction, competition, organization, self-maintenance, or organism identity.", "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage4_uptake_survival_runs.csv"))
    parser.add_argument("--effects-output", type=Path, default=Path("reports/stage4_uptake_survival_effects.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage4_uptake_survival_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    if len(index) != 20 or set(index["seed"].astype(int)) != SEEDS:
        raise ValueError("uptake survival campaign requires two complete ten-seed arms")
    runs = pd.DataFrame([summarize(Path(str(row["run_dir"]))) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))])
    paired = effects(runs)
    runs.to_csv(args.runs_output, index=False)
    paired.to_csv(args.effects_output, index=False)
    write_report(runs, paired, args.report)
    print(args.runs_output); print(args.effects_output); print(args.report)


if __name__ == "__main__":
    main()
