"""Analyze AC-I001 mechanics calibration without inspecting emergence metrics."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

SEEDS = set(range(202610000, 202610005))
RATES = {0.01, 0.02, 0.03, 0.05, 0.08}
NATURAL_SIX = [0, 44, 60, 91, 93, 125]


def summarize(run_dir: Path) -> dict[str, Any]:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    config = manifest["config"]
    writes = pd.read_csv(run_dir / "writes.csv")
    friction_rate = float(config.get("friction_rejection_rate", 0.0))
    natural = config.get("pool_mode") == "excluded_list"
    if natural and config.get("pool_exclude_symbols") != NATURAL_SIX:
        raise ValueError(f"unexpected exclusion set in {run_dir}")
    if natural:
        treatment = "natural_six"
        matched_blocks = int((writes["execution_scarcity_blocked"] + writes["mutation_scarcity_blocked"]).sum())
    else:
        treatment = "friction"
        matched_blocks = int((writes["execution_friction_blocked"] + writes["mutation_friction_blocked"]).sum())
    return {
        "run_dir": str(run_dir), "seed": int(config["seed"]), "treatment": treatment,
        "friction_rate": friction_rate, "matched_blocks": matched_blocks,
        "changing_write_attempts": int(writes["changing_write_attempts"].sum()),
        "scarcity_blocks": int((writes["execution_scarcity_blocked"] + writes["mutation_scarcity_blocked"]).sum()),
        "friction_blocks": int((writes["execution_friction_blocked"] + writes["mutation_friction_blocked"]).sum()),
        "successful_exit": manifest.get("exit_status") == "success",
        "max_conservation_residual": int(manifest.get("max_conservation_residual", -1)),
        "wall_time_s": float(manifest["wall_time_s"]),
    }


def select_rate(runs: pd.DataFrame) -> tuple[float | None, pd.DataFrame]:
    natural_median = float(runs.loc[runs["treatment"] == "natural_six", "matched_blocks"].median())
    friction = runs[runs["treatment"] == "friction"]
    groups = friction.groupby("friction_rate").agg(
        runs=("seed", "size"), median_blocks=("matched_blocks", "median"),
        min_blocks=("matched_blocks", "min"), max_blocks=("matched_blocks", "max"),
    ).reset_index().sort_values("friction_rate")
    groups["natural_median_blocks"] = natural_median
    groups["count_ratio"] = groups["median_blocks"] / natural_median
    groups["absolute_log_ratio"] = groups["count_ratio"].map(lambda value: abs(math.log(float(value))))
    best = groups.sort_values(["absolute_log_ratio", "friction_rate"], ignore_index=True).iloc[0]
    acceptable = bool(0.8 <= float(best["count_ratio"]) <= 1.25 and runs["successful_exit"].all() and (runs["max_conservation_residual"] == 0).all())
    return (float(best["friction_rate"]) if acceptable else None), groups


def write_report(runs: pd.DataFrame, groups: pd.DataFrame, selected: float | None, target: Path) -> None:
    lines = [
        "# AC-I001 nonspecific-friction calibration", "", "## Decision", "",
        (f"Selected friction rejection rate: **{selected:g}**." if selected is not None else "**No acceptable friction rate; stop AC-I001 confirmation.**"), "",
        f"Natural-six median scarcity blocks: {float(groups['natural_median_blocks'].iloc[0]):.0f}", "",
        "| friction rate | runs | median blocks | range | ratio to natural-six | absolute log ratio |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in groups.to_dict(orient="records"):
        lines.append(f"| {float(row['friction_rate']):g} | {int(row['runs'])} | {float(row['median_blocks']):.0f} | {int(row['min_blocks'])}–{int(row['max_blocks'])} | {float(row['count_ratio']):.6f} | {float(row['absolute_log_ratio']):.6f} |")
    lines += ["", "Selection used blocked-write mechanics only. Emergence, entropy, abundance, and functional replication were not inspected.", ""]
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("runs_root", type=Path); parser.add_argument("--runs-output", type=Path, default=Path("reports/ac_i001_friction_calibration_runs.csv")); parser.add_argument("--groups-output", type=Path, default=Path("reports/ac_i001_friction_calibration_groups.csv")); parser.add_argument("--selection-output", type=Path, default=Path("reports/ac_i001_friction_calibration_selection.json")); parser.add_argument("--report", type=Path, default=Path("reports/ac_i001_friction_calibration_report.md")); args = parser.parse_args()
    run_dirs = sorted(path.parent for path in args.runs_root.glob("*/manifest.json")); runs = pd.DataFrame([summarize(path) for path in run_dirs]).sort_values(["treatment", "friction_rate", "seed"], ignore_index=True)
    if len(runs) != 30 or set(runs["seed"]) != SEEDS or set(runs.loc[runs["treatment"] == "friction", "friction_rate"]) != RATES: raise ValueError("calibration treatment matrix is incomplete")
    selected, groups = select_rate(runs); args.runs_output.parent.mkdir(parents=True, exist_ok=True); runs.to_csv(args.runs_output, index=False); groups.to_csv(args.groups_output, index=False); args.selection_output.write_text(json.dumps({"selected_friction_rejection_rate": selected}, indent=2, sort_keys=True) + "\n", encoding="utf-8"); write_report(runs, groups, selected, args.report); print(args.report)


if __name__ == "__main__": main()
