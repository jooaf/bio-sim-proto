"""Analyze the preregistered mutation-by-radius opcode-beta follow-up."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run
from analysis.spatial import (
    bff_opcode_signature_snapshot,
    block_beta_permutation_test,
)
from experiments.analyze_phase2_liveness_pilot import summarize_run
from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater
from experiments.diagnose_phase2_opcode_beta import OPCODES, opcode_values
from soup.config import Config


RADIUS = "world.interaction_radius"
MUTATION = "world.mutation_rate"
LOW_MUTATION = 1 / 16_384
BASELINE_MUTATION = 1 / 4_096


def opcode_presence_label(value: bytes) -> str:
    """Return the frozen ten-bit opcode-presence label."""

    values = opcode_values(value)
    return "".join("1" if opcode in values else "0" for opcode in OPCODES)


def summarize_followup_run(
    run_dir: Path,
    *,
    permutations: int,
    analysis_seed: int,
) -> dict[str, Any]:
    """Compute mechanical and frozen final-snapshot follow-up outcomes."""

    config = Config.load(run_dir / "config.toml")
    summary = summarize_run(
        run_dir,
        dissolution_rate=config.dissolution.spontaneous_rate,
        reseed_rate=config.world.reseed_rate,
        permutations=permutations,
        analysis_seed=analysis_seed + 30_000,
    )
    data = load_run(run_dir)
    tapes = data.table("tapes")
    complete = tapes[tapes["full_bytes"].notna()]
    tick = int(cast(Any, complete["tick"].max()))
    snapshot = complete[complete["tick"] == tick].reset_index(drop=True)
    ordered = bff_opcode_signature_snapshot(snapshot)
    counts = ordered["content_hash"].value_counts()
    unique_fraction = float(len(counts) / len(ordered))
    singleton_fraction = float(
        ordered["content_hash"].map(counts).eq(1).sum() / len(ordered)
    )
    ordered_block2 = block_beta_permutation_test(
        ordered,
        width=config.world.width,
        height=config.world.height,
        block_size=2,
        permutations=permutations,
        q_values=(1.0,),
        rng=np.random.default_rng(analysis_seed + config.run.seed),
    ).iloc[0]
    presence = snapshot.copy()
    presence["content_hash"] = presence["full_bytes"].map(
        lambda value: opcode_presence_label(bytes(value))
    )
    presence_block2 = block_beta_permutation_test(
        presence,
        width=config.world.width,
        height=config.world.height,
        block_size=2,
        permutations=permutations,
        q_values=(1.0,),
        rng=np.random.default_rng(analysis_seed + 10_000 + config.run.seed),
    ).iloc[0]
    summary.update(
        {
            "radius": config.world.interaction_radius,
            "mutation_rate": config.world.mutation_rate,
            "primary_snapshot_tick": tick,
            "ordered_unique_fraction": unique_fraction,
            "ordered_singleton_tape_fraction": singleton_fraction,
            "ordered_block2_beta": float(ordered_block2["observed_beta"]),
            "ordered_block2_beta_null": float(ordered_block2["null_mean_beta"]),
            "ordered_block2_beta_excess": float(ordered_block2["beta_excess"]),
            "ordered_block2_beta_p": float(ordered_block2["p_value"]),
            "presence_block2_beta_excess": float(presence_block2["beta_excess"]),
            "presence_block2_beta_p": float(presence_block2["p_value"]),
            "followup_mechanically_feasible": bool(
                summary["mechanically_feasible"]
                and float(summary["late_mean_occupied_fraction"]) >= 0.25
            ),
        }
    )
    return summary


def paired_effect(
    runs: pd.DataFrame,
    *,
    fixed_column: str,
    fixed_value: float | int,
    compared_column: str,
    high: float | int,
    low: float | int,
    outcome: str,
) -> tuple[np.ndarray[Any, np.dtype[np.float64]], float]:
    """Return high-minus-low matched effects within one factorial slice."""

    selected = runs[np.isclose(runs[fixed_column].astype(float), float(fixed_value))]
    pivot = selected.pivot(index="seed", columns=compared_column, values=outcome)
    high_column = min(pivot.columns, key=lambda value: abs(float(value) - float(high)))
    low_column = min(pivot.columns, key=lambda value: abs(float(value) - float(low)))
    if pivot[[high_column, low_column]].isna().any().any() or len(pivot) != 10:
        raise ValueError(f"incomplete matched pairs for {outcome}")
    differences = (pivot[high_column] - pivot[low_column]).to_numpy(dtype=np.float64)
    return differences, exact_paired_sign_flip_greater(differences)


def holm_two(p_values: dict[str, float]) -> dict[str, bool]:
    """Apply frozen two-test Holm step-down decisions at alpha 0.05."""

    ordered = sorted(p_values, key=p_values.get)  # type: ignore[arg-type]
    first, second = ordered
    first_pass = p_values[first] <= 0.025
    return {first: first_pass, second: first_pass and p_values[second] <= 0.05}


def treatment_summary(runs: pd.DataFrame) -> pd.DataFrame:
    """Aggregate all four factorial cells without selecting a winner."""

    return (
        runs.groupby(["radius", "mutation_rate"], sort=True)
        .agg(
            runs=("seed", "size"),
            feasible=("followup_mechanically_feasible", "sum"),
            conserved=("conserved", "all"),
            invariant_failures=("invariant_failures", "sum"),
            median_occupancy=("late_mean_occupied_fraction", "median"),
            mean_unique_fraction=("ordered_unique_fraction", "mean"),
            mean_singleton_fraction=("ordered_singleton_tape_fraction", "mean"),
            median_ordered_block2_excess=("ordered_block2_beta_excess", "median"),
            median_ordered_block2_p=("ordered_block2_beta_p", "median"),
            median_ordered_block8_excess=("opcode_q1_beta_excess", "median"),
            median_presence_block2_excess=("presence_block2_beta_excess", "median"),
            median_byte_excess=("neighbor_byte_identity_excess", "median"),
        )
        .reset_index()
    )


def write_report(runs: pd.DataFrame, groups: pd.DataFrame, target: Path) -> None:
    """Write primary Holm decisions, secondary outcomes, and integrity."""

    h1, h1_p = paired_effect(
        runs,
        fixed_column="radius",
        fixed_value=1,
        compared_column="mutation_rate",
        high=BASELINE_MUTATION,
        low=LOW_MUTATION,
        outcome="ordered_unique_fraction",
    )
    h2, h2_p = paired_effect(
        runs,
        fixed_column="mutation_rate",
        fixed_value=LOW_MUTATION,
        compared_column="radius",
        high=1,
        low=8,
        outcome="ordered_block2_beta_excess",
    )
    decisions = holm_two({"H1": h1_p, "H2": h2_p})
    viable = int(
        runs[
            np.isclose(runs["mutation_rate"], LOW_MUTATION)
            & (runs["radius"] == 1)
        ]["followup_mechanically_feasible"].sum()
    )
    joint = decisions["H1"] and decisions["H2"] and viable >= 8
    lines = [
        "# Phase 2 opcode-beta mechanistic follow-up",
        "",
        "## Decision",
        "",
        f"Joint preregistered mechanism result supported: **{joint}**.",
        "",
        f"- H1 mean baseline-minus-low-mutation unique-fraction effect: {float(h1.mean()):.6f}",
        f"- H1 exact one-sided p: {h1_p:.6f}; Holm pass: **{decisions['H1']}**",
        f"- H2 mean radius-1-minus-radius-8 block-2 beta-excess effect: {float(h2.mean()):.6f}",
        f"- H2 exact one-sided p: {h2_p:.6f}; Holm pass: **{decisions['H2']}**",
        f"- Low-mutation radius-1 mechanical feasibility: {viable}/10",
        "",
        "These 5,000-tick follow-ups cannot overturn the completed 500,000-tick NO-GO.",
        "",
        "## Factorial cells",
        "",
        "| radius | mutation | feasible | unique fraction | singleton fraction | ordered block-2 excess | median within-run p | old block-8 excess | presence block-2 excess | byte excess |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    records = cast(list[dict[str, Any]], groups.to_dict(orient="records"))
    for row in records:
        lines.append(
            f"| {int(row['radius'])} | {float(row['mutation_rate']):.8f} | "
            f"{int(row['feasible'])}/{int(row['runs'])} | "
            f"{float(row['mean_unique_fraction']):.3f} | "
            f"{float(row['mean_singleton_fraction']):.3f} | "
            f"{float(row['median_ordered_block2_excess']):.6f} | "
            f"{float(row['median_ordered_block2_p']):.3f} | "
            f"{float(row['median_ordered_block8_excess']):.6f} | "
            f"{float(row['median_presence_block2_excess']):.6f} | "
            f"{float(row['median_byte_excess']):.6f} |"
        )
    lines += [
        "",
        "## Matched primary effects",
        "",
        f"- H1 seed effects: {', '.join(f'{value:.6f}' for value in h1)}",
        f"- H2 seed effects: {', '.join(f'{value:.6f}' for value in h2)}",
        "",
        "## Integrity",
        "",
        f"- Runs: {len(runs)}",
        f"- Successful exits: {int(runs['successful_exit'].sum())}/{len(runs)}",
        f"- Exactly conserved: {int(runs['conserved'].sum())}/{len(runs)}",
        f"- Invariant failures: {int(runs['invariant_failures'].sum())}",
        f"- Mechanically feasible: {int(runs['followup_mechanically_feasible'].sum())}/{len(runs)}",
        "",
        "Secondary labels and scales are descriptive. A positive result motivates model/protocol design; it does not rewrite Phase 2 acceptance.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--permutations", type=int, default=999)
    parser.add_argument("--analysis-seed", type=int, default=20260904)
    parser.add_argument(
        "--runs-output", type=Path, default=Path("reports/phase2_opcode_beta_followup_runs.csv")
    )
    parser.add_argument(
        "--groups-output", type=Path, default=Path("reports/phase2_opcode_beta_followup_groups.csv")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("reports/phase2_opcode_beta_followup_report.md")
    )
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    required = {"run_dir", "seed", RADIUS, MUTATION}
    missing = required - set(index.columns)
    if missing:
        raise ValueError(f"follow-up index missing columns: {sorted(missing)}")
    rows = [
        summarize_followup_run(
            Path(str(row["run_dir"])),
            permutations=args.permutations,
            analysis_seed=args.analysis_seed,
        )
        for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))
    ]
    runs = pd.DataFrame(rows).sort_values(
        ["radius", "mutation_rate", "seed"], ignore_index=True
    )
    if len(runs) != 40 or runs.groupby(["radius", "mutation_rate"])["seed"].nunique().min() != 10:
        raise ValueError("follow-up requires four complete ten-seed factorial cells")
    groups = treatment_summary(runs)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    groups.to_csv(args.groups_output, index=False)
    write_report(runs, groups, args.report)
    print(args.runs_output)
    print(args.groups_output)
    print(args.report)


if __name__ == "__main__":
    main()
