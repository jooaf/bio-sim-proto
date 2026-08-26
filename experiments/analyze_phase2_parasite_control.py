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
from analysis.report import detect_replications
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


def ancestry_trajectory(
    interactions: pd.DataFrame,
    events: pd.DataFrame,
    tapes: pd.DataFrame,
    initial_tape_ids: list[int],
) -> pd.DataFrame:
    """Propagate neutral ancestry through strict offline exact-copy witnesses."""

    columns = ["tick", "ancestry_count", "ancestry_fraction"]
    if interactions.empty:
        return pd.DataFrame(columns=columns)
    replications = detect_replications(interactions)
    deaths = events[events["event_type"] == "tape_dissolved"].sort_values("tick")
    replication_records = cast(
        list[dict[str, Any]], replications.to_dict(orient="records")
    )
    death_records = cast(list[dict[str, Any]], deaths.to_dict(orient="records"))
    labels = set(initial_tape_ids)
    replication_index = 0
    death_index = 0
    rows: list[dict[str, int | float]] = []
    for tick, snapshot in tapes.groupby("tick", sort=True):
        tick_value = int(cast(Any, tick))
        while (
            replication_index < len(replication_records)
            and int(replication_records[replication_index]["tick"]) <= tick_value
        ):
            replication = replication_records[replication_index]
            source = int(replication["source_id"])
            target = int(replication["target_id"])
            if source in labels:
                labels.add(target)
            else:
                labels.discard(target)
            replication_index += 1
        while death_index < len(death_records) and int(death_records[death_index]["tick"]) <= tick_value:
            tape_id = death_records[death_index].get("tape_id")
            if tape_id is not None:
                labels.discard(int(tape_id))
            death_index += 1
        occupied_ids = set(int(value) for value in snapshot["tape_id"])
        count = len(labels & occupied_ids)
        rows.append(
            {
                "tick": tick_value,
                "ancestry_count": count,
                "ancestry_fraction": count / len(occupied_ids),
            }
        )
    return pd.DataFrame(rows, columns=columns)


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
    ancestry = ancestry_trajectory(
        data.table("interactions"),
        data.table("events"),
        tapes,
        [int(value) for value in protocol.get("tape_ids", [])],
    )
    if not ancestry.empty:
        trajectory = trajectory.merge(ancestry, on="tick", how="left", validate="one_to_one")
    else:
        trajectory["ancestry_count"] = float("nan")
        trajectory["ancestry_fraction"] = float("nan")
    ancestry_available = bool(trajectory["ancestry_count"].notna().all())
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
        "ancestry_available": ancestry_available,
        "max_ancestry_count": (
            int(trajectory["ancestry_count"].max()) if ancestry_available else -1
        ),
        "max_ancestry_fraction": (
            float(trajectory["ancestry_fraction"].max()) if ancestry_available else float("nan")
        ),
        "final_ancestry_count": (
            int(trajectory.iloc[-1]["ancestry_count"]) if ancestry_available else -1
        ),
        "final_ancestry_fraction": (
            float(trajectory.iloc[-1]["ancestry_fraction"])
            if ancestry_available
            else float("nan")
        ),
        "ancestry_increased": bool(
            ancestry_available and int(trajectory["ancestry_count"].max()) > inserted_count
        ),
        "ancestry_reached_50pct": bool(
            ancestry_available and (trajectory["ancestry_fraction"] >= 0.5).any()
        ),
        "ancestry_reached_90pct": bool(
            ancestry_available and (trajectory["ancestry_fraction"] >= 0.9).any()
        ),
    }
    tagged = trajectory.copy()
    tagged.insert(0, "seed", data.config.run.seed)
    tagged.insert(1, "run_dir", str(run_dir))
    return summary, tagged


def write_report(summaries: pd.DataFrame, target: Path) -> None:
    """Apply frozen development-step decisions and write all seed outcomes."""

    mechanics = len(summaries) == 1 and float(summaries.iloc[0]["mutation_rate"]) == 0.0
    ancestry_mode = bool(summaries["ancestry_available"].all())
    if mechanics:
        passed = bool(int(summaries.iloc[0]["max_exact_count"]) > DEFAULT_INSERTED_COUNT)
        decision = f"Strict exact-copy mechanics pass: **{passed}**."
        title = "# Phase 2 parasite strict-mechanics control"
    elif ancestry_mode:
        increases = int(summaries["ancestry_increased"].sum())
        reaches_half = int(summaries["ancestry_reached_50pct"].sum())
        passed = increases >= 4 and reaches_half >= 1
        decision = (
            f"Neutral-ancestry diagnostic pass: **{passed}** "
            f"({increases}/{len(summaries)} increased; {reaches_half}/{len(summaries)} reached 50%)."
        )
        title = "# Phase 2 parasite neutral-ancestry diagnostic"
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
        "| seed | max exact | max near | max near fraction | max ancestry | max ancestry fraction | final near | final ancestry | content increased | ancestry increased | ancestry reached 50% |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|",
    ]
    records = cast(list[dict[str, Any]], summaries.to_dict(orient="records"))
    for row in records:
        lines.append(
            f"| {int(row['seed'])} | {int(row['max_exact_count'])} | "
            f"{int(row['max_near_count'])} | {float(row['max_near_fraction']):.3f} | "
            f"{int(row['max_ancestry_count'])} | {float(row['max_ancestry_fraction']):.3f} | "
            f"{int(row['final_near_count'])} | {int(row['final_ancestry_count'])} | "
            f"{bool(row['family_increased'])} | {bool(row['ancestry_increased'])} | "
            f"{bool(row['ancestry_reached_50pct'])} |"
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
        f"- Complete ancestry reconstruction available: {int(summaries['ancestry_available'].sum())}/{len(summaries)}",
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
