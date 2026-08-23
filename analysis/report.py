"""Stage-gate acceptance reports computed only from raw run logs."""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.complexity import soup_high_order_entropy
from analysis.conservation import conservation_residuals
from analysis.diversity import epoch_hill_numbers
from analysis.load import TABLE_NAMES, RunData, load_run


@dataclass(frozen=True, slots=True)
class Stage0Summary:
    run_dir: Path
    seed: int
    replication_events: int
    first_replication_tick: int | None
    replicator_max_abundance: int
    initial_distinct: int
    peak_distinct: int
    final_distinct: int
    post_replication_min_distinct: int
    collapse_fraction_from_peak: float

    @property
    def replicator_emerged(self) -> bool:
        return self.replication_events > 0


def detect_replications(interactions: pd.DataFrame) -> pd.DataFrame:
    """Infer exact cross-tape copies from hashes; the simulator does not label them."""

    columns = ["tick", "round_index", "direction", "source_id", "target_id", "source_hash"]
    if interactions.empty:
        return pd.DataFrame(columns=columns)
    a_into_b = (
        (interactions["a_hash_after"] == interactions["a_hash_before"])
        & (interactions["b_hash_after"] == interactions["a_hash_before"])
        & (interactions["b_hash_before"] != interactions["a_hash_before"])
        & (interactions["b_bytes_changed"] > 0)
    )
    b_into_a = (
        (interactions["b_hash_after"] == interactions["b_hash_before"])
        & (interactions["a_hash_after"] == interactions["b_hash_before"])
        & (interactions["a_hash_before"] != interactions["b_hash_before"])
        & (interactions["a_bytes_changed"] > 0)
    )
    rows: list[dict[str, object]] = []
    for row in interactions.loc[a_into_b].itertuples(index=False):
        rows.append(
            {
                "tick": int(cast(Any, row.tick)),
                "round_index": int(cast(Any, row.round_index)),
                "direction": "a_into_b",
                "source_id": int(cast(Any, row.a_id)),
                "target_id": int(cast(Any, row.b_id)),
                "source_hash": str(row.a_hash_before),
            }
        )
    for row in interactions.loc[b_into_a].itertuples(index=False):
        rows.append(
            {
                "tick": int(cast(Any, row.tick)),
                "round_index": int(cast(Any, row.round_index)),
                "direction": "b_into_a",
                "source_id": int(cast(Any, row.b_id)),
                "target_id": int(cast(Any, row.a_id)),
                "source_hash": str(row.b_hash_before),
            }
        )
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values(["tick", "round_index", "direction"], ignore_index=True)


def summarize_stage0(data: RunData) -> Stage0Summary:
    """Compute Stage 0 observations from interaction and population tables."""

    interactions = data.table("interactions")
    population = data.table("population")
    replications = detect_replications(interactions)
    distinct = population.groupby("epoch", sort=True)["content_hash"].nunique()
    if distinct.empty:
        raise ValueError("population table contains no epochs")
    first_tick: int | None = None
    post_min = int(distinct.min())
    max_abundance = 0
    if not replications.empty:
        first_tick = int(cast(Any, replications.iloc[0]["tick"]))
        first_epoch = first_tick // data.config.run.epoch_length
        post = distinct.loc[distinct.index >= first_epoch]
        if not post.empty:
            post_min = int(post.min())
        replicator_hashes = set(replications["source_hash"].astype(str))
        matching = population[population["content_hash"].isin(replicator_hashes)]
        if not matching.empty:
            max_abundance = int(matching["count"].max())
    peak = int(distinct.max())
    collapse = 0.0 if peak == 0 else (peak - post_min) / peak
    return Stage0Summary(
        run_dir=data.run_dir,
        seed=data.config.run.seed,
        replication_events=len(replications),
        first_replication_tick=first_tick,
        replicator_max_abundance=max_abundance,
        initial_distinct=int(distinct.iloc[0]),
        peak_distinct=peak,
        final_distinct=int(distinct.iloc[-1]),
        post_replication_min_distinct=post_min,
        collapse_fraction_from_peak=collapse,
    )


def parquet_digest(run_dir: str | Path) -> str:
    """Hash table names and exact Parquet bytes in stable order."""

    root = Path(run_dir)
    digest = hashlib.sha256()
    for name in sorted(TABLE_NAMES):
        path = root / f"{name}.parquet"
        if not path.exists():
            raise FileNotFoundError(path)
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_stage0_report(run_dir: str | Path, output: str | Path | None = None) -> Path:
    """Load a run and emit its complete Stage 0 markdown report and Hill table."""

    data = load_run(run_dir)
    summary = summarize_stage0(data)
    hill = epoch_hill_numbers(data.table("population"))
    hill_path = data.run_dir / "analysis_hill_numbers.parquet"
    hill.to_parquet(hill_path, index=False, compression="zstd")
    complexity = soup_high_order_entropy(data.table("tapes"))
    complexity_path = data.run_dir / "analysis_high_order_entropy.parquet"
    complexity.to_parquet(complexity_path, index=False, compression="zstd")
    target = Path(output) if output is not None else data.run_dir / "stage0_report.md"
    first = "none" if summary.first_replication_tick is None else str(summary.first_replication_tick)
    clear_collapse = summary.collapse_fraction_from_peak >= 0.5
    transitions = complexity[complexity["high_order_entropy"] >= 1.0]
    first_transition = "none" if transitions.empty else str(int(transitions.iloc[0]["tick"]))
    maximum_complexity = float(complexity["high_order_entropy"].max()) if not complexity.empty else float("nan")
    target.write_text(
        "\n".join(
            [
                "# Stage 0 run report",
                "",
                f"- Run: `{data.run_dir}`",
                f"- Seed: {summary.seed}",
                f"- Exit status: {data.manifest.get('exit_status', 'unknown')}",
                f"- Replicator detected offline: **{summary.replicator_emerged}**",
                f"- Exact replication events: {summary.replication_events}",
                f"- First replication tick: {first}",
                f"- Maximum abundance of a detected replicator hash: {summary.replicator_max_abundance}",
                f"- Distinct hashes (initial / peak / final): {summary.initial_distinct} / {summary.peak_distinct} / {summary.final_distinct}",
                f"- Minimum distinct hashes after first replication: {summary.post_replication_min_distinct}",
                f"- Collapse from peak: {summary.collapse_fraction_from_peak:.3%}",
                f"- Clear collapse (offline threshold >=50%): **{clear_collapse}**",
                f"- Maximum high-order entropy: {maximum_complexity:.6f}",
                f"- First paper-style complexity transition (>=1 bit/byte): {first_transition}",
                f"- Exact Parquet digest: `{parquet_digest(data.run_dir)}`",
                "",
                "Replication is defined here as an unchanged source tape leaving the other, previously different, tape with the source's exact pre-interaction hash.",
                f"Hill effective-number profiles are in `{hill_path.name}`.",
                f"Brotli-based high-order entropy is in `{complexity_path.name}`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return target


def write_stage1_report(run_dir: str | Path, output: str | Path | None = None) -> Path:
    """Validate conserved-symbol snapshots and emit a Stage 1 report."""

    data = load_run(run_dir)
    if data.config.run.stage != 1:
        raise ValueError("Stage 1 report requires run.stage=1")
    residuals = conservation_residuals(data.table("ticks"), data.table("tapes"))
    if residuals.empty:
        raise ValueError("run has no aligned tick and tape snapshots")
    residual_path = data.run_dir / "analysis_conservation.parquet"
    residuals.to_parquet(residual_path, index=False, compression="zstd")
    interactions = data.table("interactions")
    execution_blocked = int(interactions["writes_blocked"].sum())
    mutation_blocked = int(interactions["mutation_writes_blocked"].sum())
    all_conserved = bool(residuals["conserved"].all())
    max_residual = int(residuals["max_abs_residual"].max())
    target = Path(output) if output is not None else data.run_dir / "stage1_report.md"
    target.write_text(
        "\n".join(
            [
                "# Stage 1 conservation report",
                "",
                f"- Run: `{data.run_dir}`",
                f"- Seed: {data.config.run.seed}",
                f"- Exit status: {data.manifest.get('exit_status', 'unknown')}",
                f"- Checked conservation snapshots: {len(residuals)}",
                f"- Exact per-symbol conservation: **{all_conserved}**",
                f"- Maximum absolute per-symbol residual: {max_residual}",
                f"- Substrate writes blocked by symbol scarcity: {execution_blocked}",
                f"- Mutation writes blocked by symbol scarcity: {mutation_blocked}",
                f"- Conservation details: `{residual_path.name}`",
                f"- Exact Parquet digest: `{parquet_digest(data.run_dir)}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return target


def _longest_true_run(values: pd.Series) -> int:
    longest = 0
    current = 0
    for value in values.astype(bool):
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def write_stage2_report(run_dir: str | Path, output: str | Path | None = None) -> Path:
    """Emit clarified anti-clogging and anti-extinction results for Stage 2."""

    data = load_run(run_dir)
    if data.config.run.stage != 2:
        raise ValueError("Stage 2 report requires run.stage=2")
    ticks = data.table("ticks").sort_values("tick", ignore_index=True)
    if ticks.empty:
        raise ValueError("run has no tick facts")
    residuals = conservation_residuals(ticks, data.table("tapes"))
    residual_path = data.run_dir / "analysis_conservation.parquet"
    residuals.to_parquet(residual_path, index=False, compression="zstd")
    capacity = data.config.world.width * data.config.world.height
    final_window_size = max(1, len(ticks) // 10)
    late = ticks.iloc[-final_window_size:]
    occupied_fraction = late["n_tapes"] / capacity
    interaction_active_fraction = float((late["n_interactions"] > 0).mean())
    late_successful_writes = int(late["n_writes_success"].sum())
    longest_clogged = _longest_true_run(ticks["n_free_cells"] == 0)
    events = data.table("events")
    placements = int((events["event_type"] == "random_tape_placed").sum()) if not events.empty else 0
    dissolutions = int(ticks["n_dissolutions"].sum())
    pool_changed = 0
    if len(late) > 1:
        histograms = [np.asarray(value, dtype=np.int64) for value in late["pool_histogram"]]
        pool_changed = sum(not np.array_equal(left, right) for left, right in zip(histograms, histograms[1:]))
    all_conserved = bool(len(residuals) and residuals["conserved"].all())
    anti_clogging = longest_clogged <= 1_000
    liveness = bool(
        int(ticks["n_tapes"].min()) > 0
        and float(occupied_fraction.mean()) >= 0.20
        and interaction_active_fraction >= 0.90
        and late_successful_writes > 0
        and dissolutions > 0
        and placements > 0
        and pool_changed > 0
    )
    target = Path(output) if output is not None else data.run_dir / "stage2_report.md"
    target.write_text(
        "\n".join(
            [
                "# Stage 2 space and dissolution report",
                "",
                f"- Run: `{data.run_dir}`",
                f"- Exit status: {data.manifest.get('exit_status', 'unknown')}",
                f"- Ticks completed: {len(ticks)}",
                f"- Lattice capacity: {capacity}",
                f"- Minimum live tapes: {int(ticks['n_tapes'].min())}",
                f"- Final-window mean occupied fraction: {float(occupied_fraction.mean()):.3f}",
                f"- Longest fully occupied interval: {longest_clogged} ticks",
                f"- Final-window active-interaction fraction: {interaction_active_fraction:.3f}",
                f"- Final-window successful writes: {late_successful_writes}",
                f"- Dissolutions: {dissolutions}",
                f"- Successful random placements: {placements}",
                f"- Final-window pool-composition changes: {pool_changed}",
                f"- Exact per-symbol conservation: **{all_conserved}**",
                f"- Anti-clogging criterion: **{anti_clogging}**",
                f"- Anti-extinction/liveness criterion: **{liveness}**",
                f"- Combined mechanical gate: **{anti_clogging and liveness and all_conserved}**",
                f"- Conservation details: `{residual_path.name}`",
                f"- Exact Parquet digest: `{parquet_digest(data.run_dir)}`",
                "",
                "Spatial autocorrelation and block beta diversity are computed by `analysis/spatial.py` from tape snapshots.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return target


def write_batch_stage0_report(run_dirs: list[Path], output: Path) -> Path:
    """Aggregate the 20-run emergence criterion without ranking or selecting tapes."""

    summaries = [summarize_stage0(load_run(path)) for path in run_dirs]
    emerged = sum(item.replicator_emerged for item in summaries)
    rate = emerged / len(summaries) if summaries else 0.0
    rows = [
        "# Stage 0 batch acceptance report",
        "",
        f"- Runs: {len(summaries)}",
        f"- Runs with offline-detected replication: {emerged}",
        f"- Emergence rate: **{rate:.1%}**",
        f"- Acceptance threshold (>=30%): **{rate >= 0.3}**",
        "",
        "| seed | emerged | first tick | events | max abundance | peak distinct | final distinct | collapse |",
        "|---:|:---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summaries:
        first = "—" if item.first_replication_tick is None else str(item.first_replication_tick)
        rows.append(
            f"| {item.seed} | {item.replicator_emerged} | {first} | {item.replication_events} | "
            f"{item.replicator_max_abundance} | {item.peak_distinct} | {item.final_distinct} | "
            f"{item.collapse_fraction_from_peak:.1%} |"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--stage", type=int, default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.stage == 0:
        print(write_stage0_report(args.run_dir, args.output))
    elif args.stage == 1:
        print(write_stage1_report(args.run_dir, args.output))
    elif args.stage == 2:
        print(write_stage2_report(args.run_dir, args.output))
    else:
        raise SystemExit("only Stages 0, 1, and 2 reports are implemented")


if __name__ == "__main__":
    main()
