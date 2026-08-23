"""Summarize the targeted pool-multiplier and mutation-rate pilot campaigns."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from analysis.complexity import soup_high_order_entropy
from analysis.conservation import conservation_residuals
from analysis.report import detect_replications


def summarize_pool_pilot() -> pd.DataFrame:
    index = pd.read_parquet("sweeps/p1_pool_multiplier_pilot/index.parquet")
    rows: list[dict[str, object]] = []
    for _, entry in index.sort_values("symbols.pool_multiplier").iterrows():
        run_dir = Path(str(entry["run_dir"]))
        multiplier = float(entry["symbols.pool_multiplier"])
        ticks = pd.read_parquet(run_dir / "ticks.parquet")
        interactions = pd.read_parquet(
            run_dir / "interactions.parquet",
            columns=[
                "tick",
                "round_index",
                "a_id",
                "b_id",
                "writes_success",
                "writes_blocked",
                "mutation_writes_success",
                "mutation_writes_blocked",
                "a_bytes_changed",
                "b_bytes_changed",
                "a_hash_before",
                "a_hash_after",
                "b_hash_before",
                "b_hash_after",
            ],
        )
        population = pd.read_parquet(run_dir / "population.parquet", columns=["tick", "content_hash", "count"])
        tapes = pd.read_parquet(run_dir / "tapes.parquet", columns=["tick", "tape_id", "byte_histogram", "full_bytes"])
        conservation = conservation_residuals(ticks, tapes)
        complexity = soup_high_order_entropy(tapes)
        replications = detect_replications(interactions)
        total_writes = ticks["n_writes_success"] + ticks["n_writes_blocked"]
        blocked_rate = ticks["n_writes_blocked"].div(total_writes.where(total_writes > 0, 1))
        distinct = population.groupby("tick")["content_hash"].nunique()
        abundance = population.groupby("tick")["count"].max()
        initial_pool = np.asarray(ticks.iloc[0]["pool_histogram"], dtype=np.int64)
        final_pool = np.asarray(ticks.iloc[-1]["pool_histogram"], dtype=np.int64)
        rows.append(
            {
                "pool_multiplier": multiplier,
                "run_dir": str(run_dir),
                "pool_total": int(ticks.iloc[0]["pool_total"]),
                "pool_entropy_initial": float(ticks.iloc[0]["pool_entropy"]),
                "pool_entropy_final": float(ticks.iloc[-1]["pool_entropy"]),
                "pool_entropy_change": float(ticks.iloc[-1]["pool_entropy"] - ticks.iloc[0]["pool_entropy"]),
                "depleted_symbols_initial": int(np.count_nonzero(initial_pool == 0)),
                "depleted_symbols_final": int(np.count_nonzero(final_pool == 0)),
                "blocked_rate_overall": float(ticks["n_writes_blocked"].sum() / total_writes.sum()),
                "blocked_rate_first_100": float(blocked_rate.iloc[:100].mean()),
                "blocked_rate_last_100": float(blocked_rate.iloc[-100:].mean()),
                "blocked_rate_peak": float(blocked_rate.max()),
                "blocked_rate_lag1_autocorrelation": float(blocked_rate.autocorr(lag=1)),
                "blocked_count_cv": float(ticks["n_writes_blocked"].std() / ticks["n_writes_blocked"].mean()),
                "execution_writes_success": int(interactions["writes_success"].sum()),
                "execution_writes_blocked": int(interactions["writes_blocked"].sum()),
                "mutation_writes_success": int(interactions["mutation_writes_success"].sum()),
                "mutation_writes_blocked": int(interactions["mutation_writes_blocked"].sum()),
                "changed_interaction_fraction": float(
                    ((interactions["a_bytes_changed"] + interactions["b_bytes_changed"]) > 0).mean()
                ),
                "exact_replication_events": len(replications),
                "minimum_distinct_hashes": int(distinct.min()),
                "final_distinct_hashes": int(distinct.iloc[-1]),
                "maximum_exact_hash_abundance": int(abundance.max()),
                "maximum_high_order_entropy": float(complexity["high_order_entropy"].max()),
                "all_conservation_snapshots_pass": bool(conservation["conserved"].all()),
                "maximum_conservation_residual": int(conservation["max_abs_residual"].max()),
            }
        )
    summary = pd.DataFrame(rows).sort_values("pool_multiplier")
    target = Path("reports/p1_pool_multiplier_pilot_summary.csv")
    summary.to_csv(target, index=False)
    return summary


def summarize_mutation_pilot() -> pd.DataFrame:
    rates = {"zero": 0.0, "reference": 1.0 / 4096.0, "high": 1.0 / 128.0}
    rows: list[dict[str, object]] = []
    for name, rate in rates.items():
        path = Path(f"reports/paper_mutation_{name}_seed0.csv")
        metrics = pd.read_csv(path)
        transitions = metrics[metrics["high_order_entropy"] >= 1.0]
        rows.append(
            {
                "condition": name,
                "mutation_rate": rate,
                "first_transition_epoch": None if transitions.empty else int(transitions.iloc[0]["epoch"]),
                "maximum_high_order_entropy": float(metrics["high_order_entropy"].max()),
                "final_high_order_entropy": float(metrics.iloc[-1]["high_order_entropy"]),
                "peak_epoch": int(metrics.loc[metrics["high_order_entropy"].idxmax(), "epoch"]),
                "runtime_seconds": float(metrics.iloc[-1]["elapsed_seconds"]),
                "transition_checkpoint": Path(f"runs/paper_mutation_{name}_seed0_transition.npy").exists(),
            }
        )
    summary = pd.DataFrame(rows)
    summary.to_csv("reports/p0_mutation_rate_pilot_summary.csv", index=False)
    return summary


def main() -> None:
    print(summarize_pool_pilot().to_string(index=False))
    print(summarize_mutation_pilot().to_string(index=False))


if __name__ == "__main__":
    main()
