"""Analyze the preregistered matched global-versus-local Stringmol control."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from experiments.stringmol.analyze_global import summarize_run


def paired_bootstrap_interval(
    differences: NDArray[np.float64],
    *,
    resamples: int = 10_000,
    seed: int = 20260826,
) -> tuple[float, float]:
    """Return a deterministic percentile interval over matched seed effects."""

    values = np.asarray(differences, dtype=np.float64)
    if values.ndim != 1 or len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("differences must be a nonempty finite vector")
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(resamples, len(values)), replace=True).mean(axis=1)
    lower, upper = np.quantile(samples, [0.025, 0.975])
    return float(lower), float(upper)


def exact_sign_flip_greater(differences: NDArray[np.float64]) -> float:
    """Return exact one-sided paired sign-flip p for a positive mean."""

    values = np.asarray(differences, dtype=np.float64)
    if values.ndim != 1 or len(values) == 0 or not np.isfinite(values).all():
        raise ValueError("differences must be a nonempty finite vector")
    observed = float(values.mean())
    null = [
        float(np.mean(values * np.asarray(signs, dtype=np.float64)))
        for signs in itertools.product((-1.0, 1.0), repeat=len(values))
    ]
    return sum(value >= observed - 1e-15 for value in null) / len(null)


def paired_table(global_runs: pd.DataFrame, local_runs: pd.DataFrame) -> pd.DataFrame:
    """Join matched seeds and derive frozen global-minus-local effects."""

    selected = [
        "seed",
        "max_ancestry_fraction",
        "final_ancestry_fraction",
        "max_exact_r_fraction",
        "final_exact_r_fraction",
        "reached_90pct",
        "population_persisted",
    ]
    paired = global_runs[selected].merge(
        local_runs[selected],
        on="seed",
        suffixes=("_global", "_local"),
        validate="one_to_one",
    )
    paired["final_ancestry_difference"] = (
        paired["final_ancestry_fraction_global"]
        - paired["final_ancestry_fraction_local"]
    )
    paired["max_ancestry_difference"] = (
        paired["max_ancestry_fraction_global"]
        - paired["max_ancestry_fraction_local"]
    )
    paired["final_exact_r_difference"] = (
        paired["final_exact_r_fraction_global"]
        - paired["final_exact_r_fraction_local"]
    )
    return paired.sort_values("seed", ignore_index=True)


def write_report(
    global_runs: pd.DataFrame,
    local_runs: pd.DataFrame,
    paired: pd.DataFrame,
    target: Path,
) -> None:
    """Apply the frozen external-containment criteria."""

    differences = paired["final_ancestry_difference"].to_numpy(dtype=np.float64)
    lower, upper = paired_bootstrap_interval(differences)
    p_value = exact_sign_flip_greater(differences)
    local_not_reached = int((~local_runs["reached_90pct"]).sum())
    global_reached = int(global_runs["reached_90pct"].sum())
    local_persisted = int(local_runs["population_persisted"].sum())
    provenance_ok = bool(
        (local_runs["exit_status"] == "success").all()
        and not local_runs["reproducible_loader_warning"].any()
        and local_runs["source_commit"].nunique() == 1
    )
    passed = bool(
        lower > 0.0
        and local_not_reached >= 8
        and global_reached >= 8
        and local_persisted >= 8
        and provenance_ok
    )
    lines = [
        "# Phase 2 matched Stringmol locality control",
        "",
        "## Decision",
        "",
        f"External Stringmol containment control pass: **{passed}**.",
        "",
        f"- Mean global−local final ancestry effect: {float(differences.mean()):.6f}",
        f"- Median paired effect: {float(np.median(differences)):.6f}",
        f"- 95% paired bootstrap interval: [{lower:.6f}, {upper:.6f}]",
        f"- Exact one-sided sign-flip p-value: {p_value:.6f}",
        f"- Local did not reach 90%: {local_not_reached}/{len(local_runs)} seeds",
        f"- Global reached 90%: {global_reached}/{len(global_runs)} seeds",
        f"- Local population persisted: {local_persisted}/{len(local_runs)} seeds",
        f"- Pinned provenance and loader checks passed: **{provenance_ok}**",
        "",
        "## Matched seeds",
        "",
        "| seed | global final ancestry | local final ancestry | global−local | global max | local max | local reached 90% |",
        "|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    records = cast(list[dict[str, Any]], paired.to_dict(orient="records"))
    for row in records:
        lines.append(
            f"| {int(row['seed'])} | {float(row['final_ancestry_fraction_global']):.3f} | "
            f"{float(row['final_ancestry_fraction_local']):.3f} | "
            f"{float(row['final_ancestry_difference']):.3f} | "
            f"{float(row['max_ancestry_fraction_global']):.3f} | "
            f"{float(row['max_ancestry_fraction_local']):.3f} | "
            f"{bool(row['reached_90pct_local'])} |"
        )
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "This result concerns pinned Spatial Stringmol. It is an external mechanism control and cannot be restated as parasite containment in the conserved BFF soup.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("local_index", type=Path)
    parser.add_argument("global_runs", type=Path)
    parser.add_argument("--local-runs-output", type=Path, required=True)
    parser.add_argument("--local-trajectory-output", type=Path, required=True)
    parser.add_argument("--paired-output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    index = json.loads(args.local_index.read_text(encoding="utf-8"))
    outputs = [summarize_run(Path(path)) for path in index["run_dirs"]]
    local_runs = pd.DataFrame([row for row, _ in outputs]).sort_values("seed", ignore_index=True)
    local_trajectories = pd.concat([trajectory for _, trajectory in outputs], ignore_index=True)
    global_runs = pd.read_csv(args.global_runs)
    paired = paired_table(global_runs, local_runs)
    args.local_runs_output.parent.mkdir(parents=True, exist_ok=True)
    local_runs.to_csv(args.local_runs_output, index=False)
    local_trajectories.to_csv(args.local_trajectory_output, index=False)
    paired.to_csv(args.paired_output, index=False)
    write_report(global_runs, local_runs, paired, args.report)
    print(args.local_runs_output)
    print(args.local_trajectory_output)
    print(args.paired_output)
    print(args.report)


if __name__ == "__main__":
    main()
