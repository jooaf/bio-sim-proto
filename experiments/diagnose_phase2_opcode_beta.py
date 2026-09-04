"""Exploratory diagnosis of opcode-beta identifiability and spatial scale."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from analysis.load import load_run
from analysis.spatial import pooled_categorical_beta_test
from soup.substrate.bff import INSTRUCTION_SET


Labeler = Callable[[bytes], str]
OPCODES = tuple(sorted(INSTRUCTION_SET))


def opcode_values(value: bytes) -> tuple[int, ...]:
    """Return the ordered BFF instructions in one tape."""

    return tuple(byte for byte in value if byte in INSTRUCTION_SET)


def labelers() -> dict[str, Labeler]:
    """Return exact and increasingly coarse exploratory opcode labels."""

    return {
        "ordered_full": lambda value: bytes(opcode_values(value)).hex(),
        "ordered_prefix8": lambda value: bytes(opcode_values(value)[:8]).hex(),
        "opcode_histogram": lambda value: ",".join(
            str(opcode_values(value).count(opcode)) for opcode in OPCODES
        ),
        "opcode_presence": lambda value: "".join(
            "1" if opcode in opcode_values(value) else "0" for opcode in OPCODES
        ),
    }


def analyze(
    run_dir: Path,
    *,
    permutations: int,
    analysis_seed: int,
) -> pd.DataFrame:
    """Return exploratory uniqueness and beta results for the final 10% window."""

    data = load_run(run_dir)
    tapes = data.table("tapes")
    start = int(np.floor(data.config.run.n_ticks * 0.9))
    complete = tapes[tapes["full_bytes"].notna() & (tapes["tick"] >= start)]
    raw_snapshots = [
        snapshot.reset_index(drop=True)
        for _, snapshot in complete.groupby("tick", sort=True)
    ]
    if not raw_snapshots:
        raise ValueError("no complete final-window snapshots")
    rows: list[dict[str, Any]] = []
    for label_index, (label_name, labeler) in enumerate(labelers().items()):
        prepared: list[pd.DataFrame] = []
        uniqueness: list[float] = []
        singleton_fractions: list[float] = []
        for snapshot in raw_snapshots:
            frame = snapshot.copy()
            labels = frame["full_bytes"].map(lambda value: labeler(bytes(value)))
            frame["content_hash"] = labels
            counts = labels.value_counts()
            uniqueness.append(float(len(counts) / len(labels)))
            singleton_fractions.append(
                float(labels.map(counts).eq(1).sum() / len(labels))
            )
            prepared.append(frame)
        for block_index, block_size in enumerate((2, 4, 8, 16)):
            result = pooled_categorical_beta_test(
                prepared,
                width=data.config.world.width,
                height=data.config.world.height,
                block_size=block_size,
                permutations=permutations,
                rng=np.random.default_rng(
                    analysis_seed + 100 * label_index + block_index
                ),
            )
            rows.append(
                {
                    "label": label_name,
                    "block_size": block_size,
                    "mean_unique_fraction": float(np.mean(uniqueness)),
                    "mean_singleton_tape_fraction": float(
                        np.mean(singleton_fractions)
                    ),
                    "observed_beta": result.observed,
                    "null_mean_beta": result.null_mean,
                    "beta_excess": result.excess,
                    "p_value": result.p_value,
                    "snapshots": result.snapshots,
                    "permutations": result.permutations,
                }
            )
    return pd.DataFrame(rows)


def write_report(results: pd.DataFrame, target: Path) -> None:
    """Write an explicitly exploratory diagnostic report."""

    lines = [
        "# Exploratory diagnosis of the Phase 2 opcode-beta failure",
        "",
        "These analyses inspect the completed acceptance run after its frozen NO-GO decision. They cannot rescue or replace that decision.",
        "",
        "| label | block | unique fraction | singleton-tape fraction | beta excess | p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in results.to_dict(orient="records"):
        lines.append(
            f"| {row['label']} | {int(row['block_size'])} | "
            f"{float(row['mean_unique_fraction']):.3f} | "
            f"{float(row['mean_singleton_tape_fraction']):.3f} | "
            f"{float(row['beta_excess']):.6f} | {float(row['p_value']):.3f} |"
        )
    ordered = results[results["label"] == "ordered_full"]
    lines += [
        "",
        "## Diagnostic interpretation",
        "",
        f"The frozen ordered-full opcode label had mean unique fraction {float(ordered['mean_unique_fraction'].iloc[0]):.3f} and mean singleton-tape fraction {float(ordered['mean_singleton_tape_fraction'].iloc[0]):.3f}.",
        "High singleton prevalence makes categorical beta behave similarly to the previously rejected exact-hash statistic: local byte similarity can be real while exact ordered opcode sequences rarely repeat.",
        "",
        "Block-size and coarse-label results are hypothesis-generating only. Any new metric or treatment must be frozen on unseen seeds before confirmatory use.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--permutations", type=int, default=199)
    parser.add_argument("--analysis-seed", type=int, default=20260904)
    parser.add_argument(
        "--output", type=Path, default=Path("reports/phase2_opcode_beta_diagnostics.csv")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("reports/phase2_opcode_beta_diagnostics.md")
    )
    args = parser.parse_args()
    results = analyze(
        args.run_dir,
        permutations=args.permutations,
        analysis_seed=args.analysis_seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output, index=False)
    write_report(results, args.report)
    print(args.output)
    print(args.report)


if __name__ == "__main__":
    main()
