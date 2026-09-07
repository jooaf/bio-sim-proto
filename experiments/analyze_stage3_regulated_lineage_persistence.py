"""Analyze the preregistered regulated lineage switch-off campaign."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater
from experiments.analyze_stage3_lineage_persistence import (
    CHECKPOINTS,
    group_summary,
    summarize as lineage_summary,
)
from experiments.analyze_stage3_population_regulation import mechanics
from experiments.stringmol.analyze_locality import paired_bootstrap_interval


STOP_TICK = "reproduction.stop_tick"
SEEDS = set(range(202609193, 202609203))
ANALYSIS_SEED = 20260919


def summarize(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Combine frozen S3-E007 mechanics with unchanged lineage measurements."""

    lineage, curves = lineage_summary(
        run_dir, permutations=499, analysis_seed=ANALYSIS_SEED
    )
    regulated = mechanics(run_dir)
    lineage.update(regulated)
    lineage["stopped_persistence_feasible"] = bool(
        lineage["successful_exit"]
        and lineage["conserved"]
        and int(lineage["invariant_failures"]) == 0
        and 0.40 <= float(lineage["occupancy_19900"]) <= 0.90
        and int(lineage["reproductive_births"]) >= 100
        and int(lineage["dissolutions"]) >= 100
        and int(lineage["placements"]) > 0
        and float(lineage["late_active_interaction_fraction"]) > 0.0
        and int(lineage["late_successful_writes"]) > 0
        and int(lineage["late_pool_changes"]) > 0
        and int(lineage["reproduction_blocked_pool"])
        <= int(lineage["reproductive_births"])
        and int(lineage["max_lineage_depth"]) >= 3
    )
    return lineage, curves


def holm_adjust(p_values: tuple[float, float]) -> tuple[float, float]:
    """Return Holm-adjusted p-values in original endpoint order."""

    order = np.argsort(np.asarray(p_values, dtype=np.float64))
    adjusted = [0.0, 0.0]
    running = 0.0
    for rank, index_value in enumerate(order):
        index = int(index_value)
        value = min(1.0, (len(p_values) - rank) * p_values[index])
        running = max(running, value)
        adjusted[index] = running
    return adjusted[0], adjusted[1]


def inference(
    runs: pd.DataFrame,
) -> tuple[pd.DataFrame, np.ndarray[Any, np.dtype[np.float64]], np.ndarray[Any, np.dtype[np.float64]]]:
    """Return frozen co-primary summaries and their paired vectors."""

    pivot = runs.pivot(index="seed", columns="stop_tick", values="final_family_excess")
    if len(pivot) != 10 or set(pivot.columns) != {0, 10_000}:
        raise ValueError("regulated persistence requires ten complete matched pairs")
    stopped = pivot[10_000].to_numpy(dtype=np.float64)
    contrast = (pivot[0] - pivot[10_000]).to_numpy(dtype=np.float64)
    rows: list[dict[str, float | str]] = []
    raw_ps: list[float] = []
    for name, values in (("stopped_final", stopped), ("continued_minus_stopped", contrast)):
        lower, upper = paired_bootstrap_interval(
            values, resamples=10_000, seed=ANALYSIS_SEED
        )
        raw_p = exact_paired_sign_flip_greater(values)
        raw_ps.append(raw_p)
        rows.append(
            {
                "endpoint": name,
                "mean": float(values.mean()),
                "median": float(np.median(values)),
                "bootstrap_lower": lower,
                "bootstrap_upper": upper,
                "raw_p": raw_p,
            }
        )
    adjusted = holm_adjust((raw_ps[0], raw_ps[1]))
    for row, p_value in zip(rows, adjusted, strict=True):
        row["holm_p"] = p_value
    return pd.DataFrame(rows), stopped, contrast


def passes_gate(runs: pd.DataFrame, endpoints: pd.DataFrame) -> bool:
    """Apply every preregistered integrated criterion."""

    stopped_runs = runs[runs["stop_tick"] == 10_000]
    continued_runs = runs[runs["stop_tick"] == 0]
    stopped = stopped_runs["final_family_excess"].to_numpy(dtype=np.float64)
    retention = stopped_runs["retention_ratio"].dropna().to_numpy(dtype=np.float64)
    return bool(
        len(runs) == 20
        and len(stopped_runs) == 10
        and len(continued_runs) == 10
        and (endpoints["mean"] > 0.0).all()
        and (endpoints["bootstrap_lower"] > 0.0).all()
        and (endpoints["holm_p"] <= 0.05).all()
        and int(np.count_nonzero(stopped > 0.0)) >= 8
        and int((stopped_runs["final_family_p"] <= 0.05).sum()) >= 8
        and len(retention) >= 8
        and float(np.median(retention)) >= 0.25
        and int((continued_runs["final_family_excess"] > 0.0).sum()) >= 8
        and int((continued_runs["final_family_p"] <= 0.05).sum()) >= 8
        and int(stopped_runs["stopped_persistence_feasible"].sum()) >= 8
        and int(continued_runs["regulation_feasible"].sum()) >= 8
        and runs["successful_exit"].all()
        and runs["conserved"].all()
        and int(runs["invariant_failures"].sum()) == 0
    )


def write_report(
    runs: pd.DataFrame,
    groups: pd.DataFrame,
    endpoints: pd.DataFrame,
    target: Path,
) -> None:
    stopped_runs = runs[runs["stop_tick"] == 10_000]
    continued_runs = runs[runs["stop_tick"] == 0]
    stopped_row = cast(dict[str, Any], endpoints.iloc[0].to_dict())
    contrast_row = cast(dict[str, Any], endpoints.iloc[1].to_dict())
    lines = [
        "# Stage 3 regulated lineage switch-off persistence",
        "",
        "## Decision",
        "",
        f"Integrated regulated persistence supported: **{passes_gate(runs, endpoints)}**.",
        "",
        "## Co-primary endpoints",
        "",
        "| endpoint | mean | median | bootstrap interval | raw p | Holm p |",
        "|---|---:|---:|---:|---:|---:|",
        f"| stopped final excess | {float(stopped_row['mean']):.6f} | {float(stopped_row['median']):.6f} | [{float(stopped_row['bootstrap_lower']):.6f}, {float(stopped_row['bootstrap_upper']):.6f}] | {float(stopped_row['raw_p']):.6f} | {float(stopped_row['holm_p']):.6f} |",
        f"| continued minus stopped | {float(contrast_row['mean']):.6f} | {float(contrast_row['median']):.6f} | [{float(contrast_row['bootstrap_lower']):.6f}, {float(contrast_row['bootstrap_upper']):.6f}] | {float(contrast_row['raw_p']):.6f} | {float(contrast_row['holm_p']):.6f} |",
        "",
        "## Integrated criteria",
        "",
        f"- Stopped final excess positive: {int((stopped_runs['final_family_excess'] > 0).sum())}/10",
        f"- Stopped final within-run p <= 0.05: {int((stopped_runs['final_family_p'] <= 0.05).sum())}/10",
        f"- Median stopped retention: {float(stopped_runs['retention_ratio'].median()):.6f}",
        f"- Continued final excess positive: {int((continued_runs['final_family_excess'] > 0).sum())}/10",
        f"- Continued final within-run p <= 0.05: {int((continued_runs['final_family_p'] <= 0.05).sum())}/10",
        f"- Mechanically feasible stopped/continued: {int(stopped_runs['stopped_persistence_feasible'].sum())}/10, {int(continued_runs['regulation_feasible'].sum())}/10",
        f"- Successful and conserved runs: {int((runs['successful_exit'] & runs['conserved']).sum())}/20",
        f"- Invariant failures: {int(runs['invariant_failures'].sum())}",
        "",
        "## Arm summaries",
        "",
        "| stop tick | feasible | births | occupancy | switch excess | final excess | retention |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    indexed_groups = groups.set_index("stop_tick")
    for stop_tick in (0, 10_000):
        group = indexed_groups.loc[stop_tick]
        regulated_group = runs[runs["stop_tick"] == stop_tick]
        feasibility_column = (
            "regulation_feasible"
            if stop_tick == 0
            else "stopped_persistence_feasible"
        )
        lines.append(
            f"| {stop_tick} | {int(regulated_group[feasibility_column].sum())}/10 | "
            f"{float(group['median_births']):.0f} | {float(group['median_occupancy']):.3f} | "
            f"{float(group['mean_switch_excess']):.6f} | {float(group['mean_final_excess']):.6f} | "
            f"{float(group['median_retention']):.3f} |"
        )
    lines += [
        "",
        "This result concerns a neutral lineage label pattern under exogenous mortality and scheduled cloning. It is not endogenous reproduction or organismal self-maintenance.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage3_regulated_lineage_persistence_runs.csv"))
    parser.add_argument("--groups-output", type=Path, default=Path("reports/stage3_regulated_lineage_persistence_groups.csv"))
    parser.add_argument("--curves-output", type=Path, default=Path("reports/stage3_regulated_lineage_persistence_curves.csv"))
    parser.add_argument("--endpoints-output", type=Path, default=Path("reports/stage3_regulated_lineage_persistence_endpoints.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage3_regulated_lineage_persistence_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", STOP_TICK}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"regulated persistence index missing columns: {sorted(missing)}")
    complete_cells = index.groupby(STOP_TICK)["seed"].nunique()
    if (
        len(index) != 20
        or set(index["seed"].astype(int)) != SEEDS
        or set(index[STOP_TICK].astype(int)) != {0, 10_000}
        or not (complete_cells == 10).all()
    ):
        raise ValueError("regulated persistence requires two complete ten-seed arms")
    summaries: list[dict[str, Any]] = []
    curves: list[dict[str, Any]] = []
    for row in cast(list[dict[str, Any]], index.to_dict(orient="records")):
        summary, run_curves = summarize(Path(str(row["run_dir"])))
        summaries.append(summary)
        curves.extend(run_curves)
    runs = pd.DataFrame(summaries).sort_values(["stop_tick", "seed"], ignore_index=True)
    curves_frame = pd.DataFrame(curves).sort_values(["stop_tick", "seed", "tick"], ignore_index=True)
    if set(curves_frame["tick"].astype(int)) != set(CHECKPOINTS):
        raise ValueError("regulated persistence is missing frozen checkpoints")
    groups = group_summary(runs)
    endpoints, _, _ = inference(runs)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    groups.to_csv(args.groups_output, index=False)
    curves_frame.to_csv(args.curves_output, index=False)
    endpoints.to_csv(args.endpoints_output, index=False)
    write_report(runs, groups, endpoints, args.report)
    for path in (args.runs_output, args.groups_output, args.curves_output, args.endpoints_output, args.report):
        print(path)


if __name__ == "__main__":
    main()
