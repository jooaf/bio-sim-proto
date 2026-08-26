"""Analyze seeded BFF parasite positive-control mechanics and viability runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.conservation import conservation_residuals
from analysis.load import load_run
from experiments.run_phase2_parasite_control import DEFAULT_INSERTED_COUNT, parasite_tape
from soup.substrate.bff import INSTRUCTION_SET


def opcode_signature(tape: np.ndarray[Any, np.dtype[np.uint8]]) -> bytes:
    """Return the ordered BFF instruction sequence for one tape."""

    return bytes(int(value) for value in tape if int(value) in INSTRUCTION_SET)


def snapshot_family_counts(tapes: pd.DataFrame) -> pd.DataFrame:
    """Count exact, near-seed, and opcode-family tapes at complete snapshots."""

    candidate = parasite_tape()
    candidate_signature = opcode_signature(candidate)
    rows: list[dict[str, int | float]] = []
    complete = tapes[tapes["full_bytes"].notna()]
    for tick, snapshot in complete.groupby("tick", sort=True):
        matrix = np.stack(
            [np.frombuffer(bytes(value), dtype=np.uint8) for value in snapshot["full_bytes"]]
        )
        distances = np.count_nonzero(matrix != candidate, axis=1)
        exact = int(np.count_nonzero(distances == 0))
        near = int(np.count_nonzero(distances <= 8))
        opcode = int(
            sum(opcode_signature(tape) == candidate_signature for tape in matrix)
        )
        occupied = len(matrix)
        rows.append(
            {
                "tick": int(cast(Any, tick)),
                "occupied": occupied,
                "exact_count": exact,
                "near_count": near,
                "opcode_count": opcode,
                "exact_fraction": exact / occupied,
                "near_fraction": near / occupied,
                "opcode_fraction": opcode / occupied,
            }
        )
    return pd.DataFrame(rows)


def summarize_run(run_dir: Path, inserted_count: int) -> tuple[dict[str, Any], pd.DataFrame]:
    """Return one run summary and its complete family trajectory."""

    data = load_run(run_dir)
    ticks = data.table("ticks")
    tapes = data.table("tapes")
    trajectory = snapshot_family_counts(tapes)
    if trajectory.empty:
        raise ValueError(f"parasite run has no complete full-byte snapshots: {run_dir}")
    residuals = conservation_residuals(ticks, tapes)
    invariant_failures = len(
        [
            line
            for line in (run_dir / "invariant_log.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        ]
    )
    final = trajectory.iloc[-1]
    protocol = json.loads((run_dir / "parasite_protocol.json").read_text(encoding="utf-8"))
    initialization = data.manifest.get("initialization", {})
    summary = {
        "run_dir": str(run_dir),
        "seed": data.config.run.seed,
        "width": data.config.world.width,
        "radius": data.config.world.interaction_radius,
        "ticks": data.config.run.n_ticks,
        "mutation_rate": data.config.world.mutation_rate,
        "inserted_count": inserted_count,
        "successful_exit": data.manifest.get("exit_status") == "success",
        "invariant_failures": invariant_failures,
        "conserved": bool(len(residuals) and residuals["conserved"].all()),
        "max_conservation_residual": (
            int(residuals["max_abs_residual"].max()) if not residuals.empty else -1
        ),
        "manifest_override_count": (
            int(initialization.get("count", -1)) if isinstance(initialization, dict) else -1
        ),
        "protocol_matches_candidate": protocol.get("candidate_hex") == parasite_tape().tobytes().hex(),
        "max_exact_count": int(trajectory["exact_count"].max()),
        "max_near_count": int(trajectory["near_count"].max()),
        "max_opcode_count": int(trajectory["opcode_count"].max()),
        "max_exact_fraction": float(trajectory["exact_fraction"].max()),
        "max_near_fraction": float(trajectory["near_fraction"].max()),
        "max_opcode_fraction": float(trajectory["opcode_fraction"].max()),
        "final_snapshot_tick": int(final["tick"]),
        "final_exact_count": int(final["exact_count"]),
        "final_near_count": int(final["near_count"]),
        "final_opcode_count": int(final["opcode_count"]),
        "final_exact_fraction": float(final["exact_fraction"]),
        "final_near_fraction": float(final["near_fraction"]),
        "final_opcode_fraction": float(final["opcode_fraction"]),
        "family_increased": int(trajectory["near_count"].max()) > inserted_count,
        "family_reached_50pct": bool((trajectory["near_fraction"] >= 0.5).any()),
        "family_reached_90pct": bool((trajectory["near_fraction"] >= 0.9).any()),
    }
    tagged = trajectory.copy()
    tagged.insert(0, "seed", data.config.run.seed)
    tagged.insert(1, "run_dir", str(run_dir))
    return summary, tagged


def write_report(summaries: pd.DataFrame, target: Path) -> None:
    """Apply frozen development-step decisions and write all seed outcomes."""

    mechanics = len(summaries) == 1 and float(summaries.iloc[0]["mutation_rate"]) == 0.0
    if mechanics:
        passed = bool(int(summaries.iloc[0]["max_exact_count"]) > DEFAULT_INSERTED_COUNT)
        decision = f"Strict exact-copy mechanics pass: **{passed}**."
        title = "# Phase 2 parasite strict-mechanics control"
    else:
        increases = int(summaries["family_increased"].sum())
        reaches_half = int(summaries["family_reached_50pct"].sum())
        passed = increases >= 4 and reaches_half >= 1
        decision = (
            f"Bounded viability pilot pass: **{passed}** "
            f"({increases}/{len(summaries)} increased; {reaches_half}/{len(summaries)} reached 50%)."
        )
        title = "# Phase 2 parasite bounded viability pilot"
    lines = [
        title,
        "",
        "## Decision",
        "",
        decision,
        "",
        "This is positive-control development, not a parasite-containment result.",
        "",
        "## Runs",
        "",
        "| seed | max exact | max near | max near fraction | final exact | final near | final near fraction | increased | reached 50% |",
        "|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|",
    ]
    records = cast(list[dict[str, Any]], summaries.to_dict(orient="records"))
    for row in records:
        lines.append(
            f"| {int(row['seed'])} | {int(row['max_exact_count'])} | "
            f"{int(row['max_near_count'])} | {float(row['max_near_fraction']):.3f} | "
            f"{int(row['final_exact_count'])} | {int(row['final_near_count'])} | "
            f"{float(row['final_near_fraction']):.3f} | {bool(row['family_increased'])} | "
            f"{bool(row['family_reached_50pct'])} |"
        )
    lines += [
        "",
        "## Integrity",
        "",
        f"- Successful exits: {int(summaries['successful_exit'].sum())}/{len(summaries)}",
        f"- Exactly conserved: {int(summaries['conserved'].sum())}/{len(summaries)}",
        f"- Total invariant failures: {int(summaries['invariant_failures'].sum())}",
        f"- Correct manifest override count: {int((summaries['manifest_override_count'] == DEFAULT_INSERTED_COUNT).sum())}/{len(summaries)}",
        f"- Protocol candidate matched: {int(summaries['protocol_matches_candidate'].sum())}/{len(summaries)}",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    inserted_count = int(index["inserted_count"])
    outputs = [summarize_run(Path(path), inserted_count) for path in index["run_dirs"]]
    summaries = pd.DataFrame([summary for summary, _ in outputs]).sort_values(
        "seed", ignore_index=True
    )
    trajectories = pd.concat([trajectory for _, trajectory in outputs], ignore_index=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    summaries.to_csv(args.summary, index=False)
    trajectories.to_csv(args.trajectory, index=False)
    write_report(summaries, args.report)
    print(args.summary)
    print(args.trajectory)
    print(args.report)


if __name__ == "__main__":
    main()
