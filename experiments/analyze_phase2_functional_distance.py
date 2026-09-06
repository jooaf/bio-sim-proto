"""Analyze preregistered BFF functional prediction and spatial distance decay."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.distance_decay import opcode_js_distance_decay_test
from analysis.functional import (
    behavior_fingerprints,
    mantel_spearman_test,
    pairwise_gower_similarity,
    pairwise_js_similarity,
    standard_behavior_probes,
)
from analysis.load import load_run
from analysis.spatial import (
    bff_opcode_composition_matrix,
    neighbor_bff_opcode_js_test,
)
from experiments.analyze_phase2_liveness_pilot import summarize_run
from experiments.analyze_phase2_opcode_beta_followup import holm_two
from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater
from experiments.stringmol.analyze_locality import paired_bootstrap_interval
from soup.config import Config
from soup.substrate.bff import BFFSubstrate


RADIUS = "world.interaction_radius"


def summarize_run_metrics(
    run_dir: Path,
    *,
    mantel_permutations: int,
    decay_permutations: int,
    sample_size: int,
    analysis_seed: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Return functional, distance, neighbor, and mechanical results for one run."""

    config = Config.load(run_dir / "config.toml")
    summary = summarize_run(
        run_dir,
        dissolution_rate=config.dissolution.spontaneous_rate,
        reseed_rate=config.world.reseed_rate,
        permutations=19,
        analysis_seed=analysis_seed + 40_000,
    )
    data = load_run(run_dir)
    tapes_table = data.table("tapes")
    complete = tapes_table[tapes_table["full_bytes"].notna()]
    tick = int(cast(Any, complete["tick"].max()))
    snapshot = complete[complete["tick"] == tick].reset_index(drop=True)
    if len(snapshot) < sample_size:
        raise ValueError(f"run {run_dir} has fewer than {sample_size} occupied tapes")

    sample_rng = np.random.default_rng(analysis_seed + config.run.seed)
    sample_indices = np.sort(sample_rng.choice(len(snapshot), size=sample_size, replace=False))
    sample = snapshot.iloc[sample_indices].reset_index(drop=True)
    sampled_tapes = np.stack(
        [np.frombuffer(bytes(value), dtype=np.uint8) for value in sample["full_bytes"]]
    )
    substrate = BFFSubstrate(
        tape_length=config.substrate.tape_length,
        head_wrap=config.substrate.head_wrap,
        pc_wrap=config.substrate.pc_wrap,
        noop_density=config.substrate.noop_density,
    )
    fingerprints = behavior_fingerprints(
        sampled_tapes,
        substrate=substrate,
        max_steps=config.substrate.max_steps,
    )
    compositions = bff_opcode_composition_matrix(sample)
    mantel = mantel_spearman_test(
        pairwise_js_similarity(compositions),
        pairwise_gower_similarity(fingerprints),
        probes=len(standard_behavior_probes(config.substrate.tape_length)),
        permutations=mantel_permutations,
        rng=np.random.default_rng(analysis_seed + 10_000 + config.run.seed),
    )
    decay, curve = opcode_js_distance_decay_test(
        snapshot,
        width=config.world.width,
        height=config.world.height,
        permutations=decay_permutations,
        rng=np.random.default_rng(analysis_seed + 20_000 + config.run.seed),
    )
    neighbor = neighbor_bff_opcode_js_test(
        snapshot,
        width=config.world.width,
        height=config.world.height,
        permutations=199,
        rng=np.random.default_rng(analysis_seed + 30_000 + config.run.seed),
    )
    summary.update(
        {
            "radius": config.world.interaction_radius,
            "analysis_tick": tick,
            "sampled_tapes": sample_size,
            "mantel_rho": mantel.correlation,
            "mantel_null_mean": mantel.null_mean,
            "mantel_p": mantel.p_value,
            "behavior_features": fingerprints.shape[1],
            "distance_decay_strength": decay.decay_strength,
            "distance_decay_null_mean": decay.null_mean,
            "distance_decay_excess": decay.excess,
            "distance_decay_p": decay.p_value,
            "neighbor_js_excess": neighbor.excess,
            "neighbor_js_p": neighbor.p_value,
            "functional_distance_feasible": bool(
                summary["mechanically_feasible"]
                and float(summary["late_mean_occupied_fraction"]) >= 0.25
            ),
        }
    )
    curve.insert(0, "run_dir", str(run_dir))
    curve.insert(1, "seed", config.run.seed)
    curve.insert(2, "radius", config.world.interaction_radius)
    return summary, curve


def primary_results(
    runs: pd.DataFrame,
) -> tuple[
    np.ndarray[Any, np.dtype[np.float64]],
    float,
    tuple[float, float],
    np.ndarray[Any, np.dtype[np.float64]],
    float,
    tuple[float, float],
]:
    """Return H1 seed-average correlations and H2 matched decay effects."""

    rho_pivot = runs.pivot(index="seed", columns="radius", values="mantel_rho")
    decay_pivot = runs.pivot(index="seed", columns="radius", values="distance_decay_excess")
    for pivot in (rho_pivot, decay_pivot):
        if 1 not in pivot.columns or 8 not in pivot.columns or len(pivot) != 10 or pivot.isna().any().any():
            raise ValueError("campaign requires ten complete radius pairs")
    h1 = rho_pivot[[1, 8]].mean(axis=1).to_numpy(dtype=np.float64)
    h2 = (decay_pivot[1] - decay_pivot[8]).to_numpy(dtype=np.float64)
    h1_p = exact_paired_sign_flip_greater(h1)
    h2_p = exact_paired_sign_flip_greater(h2)
    h1_ci = paired_bootstrap_interval(h1, resamples=10_000, seed=20260907)
    h2_ci = paired_bootstrap_interval(h2, resamples=10_000, seed=20260908)
    return h1, h1_p, h1_ci, h2, h2_p, h2_ci


def treatment_summary(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate outcomes by radius."""

    return (
        runs.groupby("radius", sort=True)
        .agg(
            runs=("seed", "size"),
            feasible=("functional_distance_feasible", "sum"),
            conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
            median_occupancy=("late_mean_occupied_fraction", "median"),
            mean_mantel_rho=("mantel_rho", "mean"),
            significant_mantel=("mantel_p", lambda values: int((values <= 0.05).sum())),
            mean_decay_strength=("distance_decay_strength", "mean"),
            mean_decay_excess=("distance_decay_excess", "mean"),
            significant_decay=("distance_decay_p", lambda values: int((values <= 0.05).sum())),
            mean_neighbor_js_excess=("neighbor_js_excess", "mean"),
        )
        .reset_index()
    )


def write_report(runs: pd.DataFrame, groups: pd.DataFrame, target: Path) -> None:
    """Apply Holm and frozen auxiliary decision criteria."""

    h1, h1_p, h1_ci, h2, h2_p, h2_ci = primary_results(runs)
    decisions = holm_two({"H1": h1_p, "H2": h2_p})
    feasible = runs.groupby("radius")["functional_distance_feasible"].sum()
    h1_pass = bool(
        decisions["H1"]
        and float(h1.mean()) > 0.0
        and h1_ci[0] > 0.0
        and np.count_nonzero(h1 > 0.0) >= 8
        and np.isfinite(runs["mantel_rho"]).all()
    )
    h2_pass = bool(
        decisions["H2"]
        and float(h2.mean()) > 0.0
        and h2_ci[0] > 0.0
        and np.count_nonzero(h2 > 0.0) >= 8
    )
    joint = h1_pass and h2_pass and int(feasible.loc[1]) >= 8 and int(feasible.loc[8]) >= 8
    lines = [
        "# Functional-prediction and distance-decay results",
        "",
        "## Decision",
        "",
        f"Joint preregistered result supported: **{joint}**.",
        "",
        f"- H1 mean seed-average Mantel rho: {float(h1.mean()):.6f}",
        f"- H1 95% bootstrap interval: [{h1_ci[0]:.6f}, {h1_ci[1]:.6f}]",
        f"- H1 exact p: {h1_p:.6f}; Holm pass: **{decisions['H1']}**; full H1 pass: **{h1_pass}**",
        f"- H1 positive seed averages: {int(np.count_nonzero(h1 > 0.0))}/10",
        f"- H2 mean radius-1-minus-radius-8 decay-excess effect: {float(h2.mean()):.8f}",
        f"- H2 95% bootstrap interval: [{h2_ci[0]:.8f}, {h2_ci[1]:.8f}]",
        f"- H2 exact p: {h2_p:.6f}; Holm pass: **{decisions['H2']}**; full H2 pass: **{h2_pass}**",
        f"- H2 positive pairs: {int(np.count_nonzero(h2 > 0.0))}/10",
        "",
        "## Radius summary",
        "",
        "| radius | feasible | Mantel rho | significant Mantel | decay strength | decay excess | significant decay | neighbor JS excess | occupancy |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    records = cast(list[dict[str, Any]], groups.to_dict(orient="records"))
    for row in records:
        lines.append(
            f"| {int(row['radius'])} | {int(row['feasible'])}/{int(row['runs'])} | "
            f"{float(row['mean_mantel_rho']):.6f} | {int(row['significant_mantel'])}/{int(row['runs'])} | "
            f"{float(row['mean_decay_strength']):.8f} | {float(row['mean_decay_excess']):.8f} | "
            f"{int(row['significant_decay'])}/{int(row['runs'])} | "
            f"{float(row['mean_neighbor_js_excess']):.6f} | {float(row['median_occupancy']):.3f} |"
        )
    lines += [
        "",
        "## Primary seed values",
        "",
        f"- H1: {', '.join(f'{value:.6f}' for value in h1)}",
        f"- H2: {', '.join(f'{value:.8f}' for value in h2)}",
        "",
        "## Integrity",
        "",
        f"- Runs: {len(runs)}",
        f"- Successful exits: {int(runs['successful_exit'].sum())}/{len(runs)}",
        f"- Exactly conserved: {int(runs['conserved'].sum())}/{len(runs)}",
        f"- Invariant failures: {int(runs['invariant_failures'].sum())}",
        f"- Mechanically feasible: {int(runs['functional_distance_feasible'].sum())}/{len(runs)}",
        "",
        "The offline assay measures standardized unconstrained execution, not in-soup fitness. Distance decay concerns syntax composition, not organism boundaries.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--mantel-permutations", type=int, default=999)
    parser.add_argument("--decay-permutations", type=int, default=499)
    parser.add_argument("--sample-size", type=int, default=128)
    parser.add_argument("--analysis-seed", type=int, default=20260907)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/phase2_functional_distance_runs.csv"))
    parser.add_argument("--groups-output", type=Path, default=Path("reports/phase2_functional_distance_groups.csv"))
    parser.add_argument("--curves-output", type=Path, default=Path("reports/phase2_functional_distance_curves.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/phase2_functional_distance_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", RADIUS}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"campaign index missing columns: {sorted(missing)}")
    outputs = [
        summarize_run_metrics(
            Path(str(row["run_dir"])),
            mantel_permutations=args.mantel_permutations,
            decay_permutations=args.decay_permutations,
            sample_size=args.sample_size,
            analysis_seed=args.analysis_seed,
        )
        for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))
    ]
    runs = pd.DataFrame([row for row, _ in outputs]).sort_values(["radius", "seed"], ignore_index=True)
    curves = pd.concat([curve for _, curve in outputs], ignore_index=True)
    if len(runs) != 20 or runs.groupby("radius")["seed"].nunique().min() != 10:
        raise ValueError("campaign requires two complete ten-seed cells")
    groups = treatment_summary(runs)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    groups.to_csv(args.groups_output, index=False)
    curves.to_csv(args.curves_output, index=False)
    write_report(runs, groups, args.report)
    for path in (args.runs_output, args.groups_output, args.curves_output, args.report):
        print(path)


if __name__ == "__main__":
    main()
