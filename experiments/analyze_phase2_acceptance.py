"""Run the frozen final-window spatial analyses for a Stage 2 acceptance run."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run
from analysis.report import write_stage2_report
from analysis.spatial import (
    pooled_bff_opcode_beta_test,
    pooled_neighbor_byte_similarity_test,
)


def analyze_acceptance(
    run_dir: Path,
    *,
    permutations: int,
    analysis_seed: int,
    block_size: int,
    output: Path,
    report: Path,
) -> tuple[Path, Path]:
    """Analyze complete full-byte snapshots in the run's final 10% window."""

    data = load_run(run_dir)
    if data.config.run.stage != 2:
        raise ValueError("acceptance analysis requires a Stage 2 run")
    tapes = data.table("tapes")
    final_window_start = int(np.floor(data.config.run.n_ticks * 0.9))
    complete = tapes[
        tapes["full_bytes"].notna() & (tapes["tick"] >= final_window_start)
    ]
    snapshots = [
        snapshot.reset_index(drop=True)
        for _, snapshot in complete.groupby("tick", sort=True)
    ]
    if not snapshots:
        raise ValueError("no complete full-byte snapshots exist in the final 10% window")
    byte_result = pooled_neighbor_byte_similarity_test(
        snapshots,
        width=data.config.world.width,
        height=data.config.world.height,
        permutations=permutations,
        rng=np.random.default_rng(analysis_seed),
    )
    beta_result = pooled_bff_opcode_beta_test(
        snapshots,
        width=data.config.world.width,
        height=data.config.world.height,
        block_size=block_size,
        permutations=permutations,
        rng=np.random.default_rng(analysis_seed + 1),
    )
    ticks = sorted(int(cast(Any, value)) for value in complete["tick"].unique())
    rows: list[dict[str, Any]] = [
        {
            "metric": "neighbor_byte_identity",
            "observed": byte_result.observed,
            "null_mean": byte_result.null_mean,
            "excess": byte_result.excess,
            "p_value": byte_result.p_value,
            "snapshots": len(snapshots),
            "permutations": permutations,
        },
        {
            "metric": "opcode_q1_block_beta",
            "observed": beta_result.observed,
            "null_mean": beta_result.null_mean,
            "excess": beta_result.excess,
            "p_value": beta_result.p_value,
            "snapshots": beta_result.snapshots,
            "permutations": permutations,
        },
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    mechanical_report = write_stage2_report(run_dir)
    byte_pass = byte_result.excess > 0.0 and byte_result.p_value < 0.05
    beta_pass = beta_result.excess > 0.0 and beta_result.p_value < 0.05
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# Phase 2 acceptance spatial analysis",
                "",
                f"- Run: `{run_dir}`",
                f"- Final-window start: {final_window_start}",
                f"- Full-byte snapshot ticks: {ticks}",
                f"- Permutations: {permutations}",
                f"- Analysis seed: {analysis_seed}",
                f"- Byte-identity excess: {byte_result.excess:.6f}",
                f"- Byte-identity pooled p-value: {byte_result.p_value:.6f}",
                f"- Byte-identity criterion: **{byte_pass}**",
                f"- Opcode q=1 beta excess: {beta_result.excess:.6f}",
                f"- Opcode q=1 beta pooled p-value: {beta_result.p_value:.6f}",
                f"- Opcode beta criterion: **{beta_pass}**",
                f"- Combined spatial criterion: **{byte_pass and beta_pass}**",
                f"- Mechanical report: `{mechanical_report}`",
                f"- Machine-readable results: `{output}`",
                "",
                "This report does not treat a short smoke run as the 500,000-tick acceptance result.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return output, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--permutations", type=int, default=999)
    parser.add_argument("--analysis-seed", type=int, default=20260825)
    parser.add_argument("--block-size", type=int, default=8)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    output = args.output or args.run_dir / "analysis_acceptance_spatial.csv"
    report = args.report or args.run_dir / "stage2_acceptance_spatial_report.md"
    results = analyze_acceptance(
        args.run_dir,
        permutations=args.permutations,
        analysis_seed=args.analysis_seed,
        block_size=args.block_size,
        output=output,
        report=report,
    )
    print(results[0])
    print(results[1])


if __name__ == "__main__":
    main()
