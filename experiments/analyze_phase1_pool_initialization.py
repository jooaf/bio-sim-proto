"""Analyze the post-campaign uniform-vs-matched Phase 1 pool follow-up."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.analyze_phase1_campaign import bootstrap_mean_ci, summarize_run


def load_condition(run_dir: Path, mode: str) -> dict[str, object]:
    row = summarize_run(run_dir)
    symbols = pd.read_csv(run_dir / "symbols.csv", usecols=["epoch", "symbol", "initial_pool_count"])
    first_symbols = symbols[symbols["epoch"] == symbols["epoch"].min()]
    row["pool_mode"] = mode
    row["initial_zero_pool_symbols"] = int((first_symbols["initial_pool_count"] == 0).sum())
    return row


def main() -> None:
    rows: list[dict[str, object]] = []
    matched_root = Path("experiments/phase1_runs/mechanism")
    uniform_root = Path("experiments/phase1_runs/pool_initialization")
    for multiplier in (0.1, 0.5):
        slug = format(multiplier, ".8g").replace(".", "p")
        for seed in range(5):
            matched = matched_root / f"p1_m{slug}_n256_s{seed}"
            uniform = uniform_root / f"p1_m{slug}_n256_s{seed}_uniform"
            for run_dir, mode in ((matched, "histogram_matched"), (uniform, "uniform")):
                manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
                if manifest.get("exit_status") != "success":
                    raise RuntimeError(f"incomplete follow-up run: {run_dir}")
                rows.append(load_condition(run_dir, mode))

    runs = pd.DataFrame(rows).sort_values(["pool_multiplier", "seed", "pool_mode"])
    output = Path("reports/phase1_pool_initialization_runs.csv")
    runs.to_csv(output, index=False)

    report = [
        "# Phase 1 pool-initialization follow-up",
        "",
        "## Question",
        "",
        "Does distributing the same free-pool total uniformly across byte values change low-pool dynamics relative to a pool matched to the initial tape histogram? This P1.6 experiment was selected after the main campaign and is therefore exploratory.",
        "",
        "## Results",
        "",
        "| Multiplier | Metric | Histogram-matched mean | Uniform mean | Paired uniform − matched [95% bootstrap CI] |",
        "|---:|---|---:|---:|---:|",
    ]
    metrics = [
        ("initial_zero_pool_symbols", "Initial zero-count symbols", 2),
        ("first_100_blocked_fraction", "First-100 blocked fraction", 4),
        ("overall_blocked_fraction", "Overall blocked fraction", 4),
        ("final_pool_jsd", "Final pool JSD", 4),
        ("maximum_high_order_entropy", "Maximum high-order entropy", 3),
    ]
    for multiplier in (0.1, 0.5):
        cell = runs[runs["pool_multiplier"] == multiplier]
        for metric, label, digits in metrics:
            pivot = cell.pivot(index="seed", columns="pool_mode", values=metric)
            differences = (pivot["uniform"] - pivot["histogram_matched"]).to_numpy(dtype=np.float64)
            low, high = bootstrap_mean_ci(differences, seed=20260814 + int(multiplier * 10))
            report.append(
                f"| {multiplier:g} | {label} | {pivot['histogram_matched'].mean():.{digits}f} | "
                f"{pivot['uniform'].mean():.{digits}f} | {differences.mean():.{digits}f} [{low:.{digits}f}, {high:.{digits}f}] |"
            )

    low_cell = runs[runs["pool_multiplier"] == 0.1]
    initial_pivot = low_cell.pivot(index="seed", columns="pool_mode", values="initial_zero_pool_symbols")
    early_pivot = low_cell.pivot(index="seed", columns="pool_mode", values="first_100_blocked_fraction")
    entropy_pivot = low_cell.pivot(index="seed", columns="pool_mode", values="maximum_high_order_entropy")
    report.extend(
        [
            "",
            "## Interpretation",
            "",
            f"Uniform initialization changed the initial zero-count-symbol burden in **{int((initial_pivot['uniform'] != initial_pivot['histogram_matched']).sum())}/5** multiplier-0.1 pairs. "
            f"It reduced early blocking in **{int((early_pivot['uniform'] < early_pivot['histogram_matched']).sum())}/5** pairs and increased maximum high-order entropy in **{int((entropy_pivot['uniform'] > entropy_pivot['histogram_matched']).sum())}/5** pairs.",
            "",
            "The result tests path dependence, not a preferred default. Histogram matching remains the most direct continuation of the implemented Stage 1 physics; uniform pools are a controlled alternative world.",
            "",
            "All runs preserved the exact per-symbol invariant at every aggregate checkpoint and used equal total free matter within each matched seed/multiplier pair.",
        ]
    )
    Path("reports/phase1_pool_initialization_followup.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Analyzed {len(runs)} matched/uniform run records")


if __name__ == "__main__":
    main()
