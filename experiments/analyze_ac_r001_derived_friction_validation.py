"""Analyze the AC-R001 mechanics-derived friction validation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from experiments.analyze_ac_i001_friction_calibration import summarize

SEEDS = set(range(202610010, 202610015))
RATE = 0.27555027572734614


def paired_results(runs: pd.DataFrame) -> pd.DataFrame:
    natural = runs[runs["treatment"] == "natural_six"].set_index("seed")
    friction = runs[runs["treatment"] == "friction"].set_index("seed")
    paired = natural[["matched_blocks", "changing_write_attempts"]].add_prefix("natural_").join(
        friction[["matched_blocks", "changing_write_attempts"]].add_prefix("friction_")
    )
    paired["block_ratio"] = paired["friction_matched_blocks"] / paired["natural_matched_blocks"]
    return paired.reset_index()


def passes_gate(runs: pd.DataFrame, paired: pd.DataFrame) -> tuple[bool, float]:
    natural_median = float(runs.loc[runs["treatment"] == "natural_six", "matched_blocks"].median())
    friction_median = float(runs.loc[runs["treatment"] == "friction", "matched_blocks"].median())
    ratio = friction_median / natural_median
    passed = bool(
        len(runs) == 10 and runs["successful_exit"].all()
        and (runs["max_conservation_residual"] == 0).all()
        and (runs["changing_write_attempts"] > 0).all()
        and 0.8 <= ratio <= 1.25
        and int(paired["block_ratio"].between(0.67, 1.5).sum()) >= 4
    )
    return passed, ratio


def write_report(runs: pd.DataFrame, paired: pd.DataFrame, target: Path) -> None:
    passed, ratio = passes_gate(runs, paired)
    natural_median = float(runs.loc[runs["treatment"] == "natural_six", "matched_blocks"].median())
    friction_median = float(runs.loc[runs["treatment"] == "friction", "matched_blocks"].median())
    lines = [
        "# AC-R001 mechanics-derived friction validation", "", "## Decision", "",
        f"Derived friction control validated: **{passed}**.", "",
        f"- Frozen rejection rate: `{RATE:.17g}`",
        f"- Natural-six median blocks: {natural_median:.0f}",
        f"- Friction median blocks: {friction_median:.0f}",
        f"- Median count ratio: {ratio:.6f}",
        f"- Paired ratios in `[0.67, 1.5]`: {int(paired['block_ratio'].between(0.67, 1.5).sum())}/5", "",
        "| seed | natural blocks | friction blocks | ratio |", "|---:|---:|---:|---:|",
    ]
    for row in paired.to_dict(orient="records"):
        lines.append(f"| {int(row['seed'])} | {int(row['natural_matched_blocks'])} | {int(row['friction_matched_blocks'])} | {float(row['block_ratio']):.6f} |")
    lines += ["", "No emergence-related calibration artifact was inspected. A pass permits a new held-out origin-filter preregistration; it is not evidence for that filter.", ""]
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("runs_root", type=Path); parser.add_argument("--runs-output", type=Path, default=Path("reports/ac_r001_derived_friction_validation_runs.csv")); parser.add_argument("--paired-output", type=Path, default=Path("reports/ac_r001_derived_friction_validation_pairs.csv")); parser.add_argument("--report", type=Path, default=Path("reports/ac_r001_derived_friction_validation_report.md")); args = parser.parse_args()
    run_dirs = sorted(path.parent for path in args.runs_root.glob("*/manifest.json")); runs = pd.DataFrame([summarize(path) for path in run_dirs]).sort_values(["treatment", "seed"], ignore_index=True)
    if len(runs) != 10 or set(runs["seed"]) != SEEDS or set(runs["treatment"]) != {"natural_six", "friction"}: raise ValueError("AC-R001 treatment matrix incomplete")
    friction_rates = set(runs.loc[runs["treatment"] == "friction", "friction_rate"])
    if friction_rates != {RATE}: raise ValueError(f"unexpected friction rates: {friction_rates}")
    paired = paired_results(runs); runs.to_csv(args.runs_output, index=False); paired.to_csv(args.paired_output, index=False); write_report(runs, paired, args.report); print(args.report)


if __name__ == "__main__": main()
