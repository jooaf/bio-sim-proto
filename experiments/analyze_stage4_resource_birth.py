"""Analyze the preregistered Stage 4 resource-coupled birth campaign."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run

SEEDS = set(range(202609250, 202609260))
UPTAKE_COUNTS = {8, 32, 56}


def exact_sign_test_greater(values: np.ndarray[Any, np.dtype[np.float64]]) -> float:
    nonzero = values[values != 0.0]
    positives = int((nonzero > 0.0).sum())
    n = len(nonzero)
    if n == 0:
        return 1.0
    return float(sum(math.comb(n, k) for k in range(positives, n + 1)) / 2**n)


def event_count(events: pd.DataFrame, event_type: str) -> int:
    selected = events[events["event_type"] == event_type]
    return sum(int(json.loads(str(value)).get("count", 1)) for value in selected["details_json"])


def summarize(run_dir: Path) -> dict[str, Any]:
    data = load_run(run_dir)
    ticks = data.table("ticks").sort_values("tick", ignore_index=True)
    tapes = data.table("tapes")
    events = data.table("events")
    protocol = json.loads((run_dir / "resource_birth_protocol.json").read_text(encoding="utf-8"))
    type_by_id = {int(record["tape_id"]): str(record["type"]) for record in protocol["records"]}
    births = events[events["event_type"] == "offspring_born"].sort_values(["tick", "tape_id"])
    uptake_parent_births = 0
    control_parent_births = 0
    for row in births.itertuples(index=False):
        details = json.loads(str(row.details_json))
        parent_id = int(details["parent_id"])
        child_id = int(cast(Any, row.tape_id))
        parent_type = type_by_id[parent_id]
        type_by_id[child_id] = parent_type
        if parent_type == "uptake":
            uptake_parent_births += 1
        else:
            control_parent_births += 1
    uptake_final = sum(value == "uptake" for value in type_by_id.values())
    control_final = sum(value == "control" for value in type_by_id.values())
    initial_uptake = int(protocol["initial_uptake_count"])
    initial_total = initial_uptake + int(protocol["initial_control_count"])
    final_total = uptake_final + control_final
    uptake_events = events[events["event_type"] == "energy_uptake"]
    uptake_executions = sum(int(json.loads(str(value))["executions"]) for value in uptake_events["details_json"])
    expected = ticks["energy_influx_cum"].to_numpy(dtype=np.float64)
    accounted = (
        ticks["energy_field_total"].to_numpy(dtype=np.float64)
        + ticks["energy_tape_total"].to_numpy(dtype=np.float64)
        + ticks["energy_dissipated_cum"].to_numpy(dtype=np.float64)
    )
    errors = np.abs(accounted - expected) / np.maximum(1.0, np.abs(expected))
    type_hashes: dict[str, set[str]] = {"uptake": set(), "control": set()}
    ids_consistent = True
    for tape_id, type_name in type_by_id.items():
        hashes = set(tapes.loc[tapes["tape_id"] == tape_id, "content_hash"].astype(str))
        ids_consistent &= len(hashes) == 1
        type_hashes[type_name].update(hashes)
    population_events = events[events["event_type"].isin(["tape_dissolved", "random_tape_placed"])]
    invariant_path = run_dir / "invariant_log.jsonl"
    return {
        "run_dir": str(run_dir),
        "seed": data.config.run.seed,
        "active_uptake_enabled": bool(protocol["active_uptake_enabled"]),
        "initial_uptake_count": initial_uptake,
        "initial_frequency": initial_uptake / initial_total,
        "final_uptake_count": uptake_final,
        "final_control_count": control_final,
        "final_frequency": uptake_final / final_total,
        "frequency_change": uptake_final / final_total - initial_uptake / initial_total,
        "final_occupancy": final_total,
        "births": len(births),
        "uptake_parent_births": uptake_parent_births,
        "control_parent_births": control_parent_births,
        "uptake_birth_fraction": 0.0 if len(births) == 0 else uptake_parent_births / len(births),
        "energy_blocked_births": event_count(events, "reproduction_blocked_energy"),
        "uptake_executions": uptake_executions,
        "unexpected_population_events": len(population_events),
        "type_consistent": bool(ids_consistent and all(len(values) <= 1 for values in type_hashes.values()) and type_hashes["uptake"].isdisjoint(type_hashes["control"])),
        "successful_exit": data.manifest.get("exit_status") == "success",
        "invariant_failures": sum(bool(line) for line in invariant_path.read_text(encoding="utf-8").splitlines()),
        "max_relative_energy_error": float(errors.max()),
    }


def paired_effects(runs: pd.DataFrame) -> pd.DataFrame:
    keys = ["seed", "initial_uptake_count"]
    enabled = runs[runs["active_uptake_enabled"]].set_index(keys)
    disabled = runs[~runs["active_uptake_enabled"]].set_index(keys)
    paired = enabled[["initial_frequency", "final_frequency", "frequency_change"]].join(
        disabled[["final_frequency", "frequency_change"]].add_prefix("disabled_")
    )
    paired["enabled_minus_disabled"] = paired["final_frequency"] - paired["disabled_final_frequency"]
    return paired.reset_index()


def passes_gate(runs: pd.DataFrame, paired: pd.DataFrame) -> bool:
    enabled = runs[runs["active_uptake_enabled"]]
    disabled = runs[~runs["active_uptake_enabled"]]
    treatment_medians = enabled.groupby("initial_uptake_count")["frequency_change"].median()
    return bool(
        len(runs) == 60
        and (paired["frequency_change"] > 0.0).all()
        and exact_sign_test_greater(paired["frequency_change"].to_numpy(dtype=np.float64)) == 2.0**-30
        and (paired["enabled_minus_disabled"] > 0.0).all()
        and (treatment_medians >= 0.05).all()
        and (enabled["births"] >= 16).all()
        and (enabled["uptake_executions"] > 0).all()
        and (enabled["uptake_birth_fraction"] >= 0.95).all()
        and (disabled["births"] == 0).all()
        and (disabled["frequency_change"] == 0.0).all()
        and (disabled["energy_blocked_births"] > 0).all()
        and (runs["unexpected_population_events"] == 0).all()
        and runs["type_consistent"].all()
        and runs["successful_exit"].all()
        and int(runs["invariant_failures"].sum()) == 0
        and (runs["max_relative_energy_error"] <= 1e-9).all()
    )


def write_report(runs: pd.DataFrame, paired: pd.DataFrame, target: Path) -> None:
    enabled = runs[runs["active_uptake_enabled"]]
    groups = enabled.groupby("initial_uptake_count").agg(
        median_initial=("initial_frequency", "median"),
        median_final=("final_frequency", "median"),
        median_change=("frequency_change", "median"),
        min_births=("births", "min"),
        uptake_birth_fraction=("uptake_birth_fraction", "min"),
    ).reset_index()
    lines = [
        "# Stage 4 resource-coupled birth and frequency change", "", "## Decision", "",
        f"Resource-coupled frequency change supported: **{passes_gate(runs, paired)}**.", "",
        f"- Primary frequency changes positive: {int((paired['frequency_change'] > 0).sum())}/30",
        f"- Exact one-sided sign p: {exact_sign_test_greater(paired['frequency_change'].to_numpy(dtype=np.float64)):.10g}",
        f"- Enabled-minus-disabled differences positive: {int((paired['enabled_minus_disabled'] > 0).sum())}/30",
        f"- Disabled successful births: {int(runs.loc[~runs['active_uptake_enabled'], 'births'].sum())}",
        f"- Enabled runs below the 16-birth gate: {int((enabled['births'] < 16).sum())}/30",
        f"- Maximum relative energy error: {runs['max_relative_energy_error'].max():.3e}", "",
        "| initial uptake | median initial frequency | median final frequency | median change | minimum births | minimum uptake-parent fraction |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        lines.append(f"| {int(row['initial_uptake_count'])} | {row['median_initial']:.3f} | {row['median_final']:.3f} | {row['median_change']:.3f} | {int(row['min_births'])} | {row['uptake_birth_fraction']:.3f} |")
    conclusion = (
        "The frozen gate passed for scheduled resource-coupled cloning and frequency change only. "
        "This is not endogenous reproduction, adaptation, competition, organization, self-maintenance, or organism identity."
        if passes_gate(runs, paired)
        else "The frozen confirmatory gate failed. Directional frequency changes are retained as descriptive evidence only; no resource-coupled reproduction claim is accepted and no parameter tuning is licensed."
    )
    lines += ["", conclusion, ""]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage4_resource_birth_runs.csv"))
    parser.add_argument("--effects-output", type=Path, default=Path("reports/stage4_resource_birth_effects.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage4_resource_birth_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    if len(index) != 60 or set(index["seed"].astype(int)) != SEEDS or set(index["initial_uptake_count"].astype(int)) != UPTAKE_COUNTS:
        raise ValueError("resource-birth campaign requires six complete ten-seed cells")
    runs = pd.DataFrame([summarize(Path(str(row["run_dir"]))) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))])
    paired = paired_effects(runs)
    runs.to_csv(args.runs_output, index=False)
    paired.to_csv(args.effects_output, index=False)
    write_report(runs, paired, args.report)
    print(args.runs_output); print(args.effects_output); print(args.report)


if __name__ == "__main__":
    main()
