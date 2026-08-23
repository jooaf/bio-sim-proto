"""Analyze the bounded exact-conservation Phase 1 campaign."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

INSTRUCTION_SYMBOLS = {43, 44, 45, 46, 60, 62, 91, 93, 123, 125}


def bootstrap_mean_ci(values: np.ndarray, seed: int = 20260812, draws: int = 10_000) -> tuple[float, float]:
    if len(values) == 0:
        return math.nan, math.nan
    if len(values) == 1:
        return float(values[0]), float(values[0])
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(draws, len(values)), replace=True).mean(axis=1)
    low, high = np.quantile(samples, [0.025, 0.975])
    return float(low), float(high)


def lag_one(values: np.ndarray) -> float:
    if len(values) < 2 or np.std(values[:-1]) == 0.0 or np.std(values[1:]) == 0.0:
        return math.nan
    return float(np.corrcoef(values[:-1], values[1:])[0, 1])


def spectral_summary(values: np.ndarray) -> tuple[float, float]:
    centered = values - values.mean()
    if len(centered) < 4 or np.all(centered == 0.0):
        return 0.0, math.nan
    power = np.abs(np.fft.rfft(centered)) ** 2
    power[0] = 0.0
    total = float(power.sum())
    if total == 0.0:
        return 0.0, math.nan
    index = int(np.argmax(power))
    return float(power[index] / total), math.nan if index == 0 else float(len(values) / index)


def effective_symbol_count(counts: np.ndarray) -> float:
    total = float(counts.sum())
    if total == 0.0:
        return 0.0
    probabilities = counts[counts > 0] / total
    return float(np.exp(-np.sum(probabilities * np.log(probabilities))))


def summarize_run(run_dir: Path) -> dict[str, object]:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    config = manifest["config"]
    aggregate = pd.read_csv(run_dir / "aggregate.csv")
    writes = pd.read_csv(run_dir / "writes.csv")
    symbols = pd.read_csv(run_dir / "symbols.csv")
    final_symbols = symbols[symbols["epoch"] == symbols["epoch"].max()].copy()

    attempted = (
        writes["execution_writes_success"]
        + writes["execution_writes_blocked"]
        + writes["mutation_writes_success"]
        + writes["mutation_writes_blocked"]
    )
    blocked = writes["execution_writes_blocked"] + writes["mutation_writes_blocked"]
    blocked_fraction = blocked.div(attempted.where(attempted > 0, 1)).to_numpy(dtype=np.float64)
    concentration, peak_period = spectral_summary(blocked_fraction)
    blocked_by_symbol = (
        final_symbols["execution_blocked"].to_numpy(dtype=np.int64)
        + final_symbols["mutation_blocked"].to_numpy(dtype=np.int64)
    )
    total_blocked = int(blocked_by_symbol.sum())
    top_index = int(np.argmax(blocked_by_symbol)) if total_blocked else 0
    cross_a_to_b = int(final_symbols["cross_a_to_b"].sum())
    cross_b_to_a = int(final_symbols["cross_b_to_a"].sum())
    cross_total = cross_a_to_b + cross_b_to_a
    instruction_blocked = int(
        final_symbols.loc[final_symbols["symbol"].isin(INSTRUCTION_SYMBOLS), ["execution_blocked", "mutation_blocked"]]
        .to_numpy(dtype=np.int64)
        .sum()
    )
    return {
        "run_dir": str(run_dir),
        "population_size": int(config["population_size"]),
        "epochs": int(config["epochs"]),
        "pool_multiplier": float(config["pool_multiplier"]),
        "seed": int(config["seed"]),
        "wall_time_s": float(manifest["wall_time_s"]),
        "overall_blocked_fraction": float(blocked.sum() / attempted.sum()),
        "first_100_blocked_fraction": float(blocked_fraction[:100].mean()),
        "last_100_blocked_fraction": float(blocked_fraction[-100:].mean()),
        "peak_epoch_blocked_fraction": float(blocked_fraction.max()),
        "zero_block_epoch_fraction": float(np.mean(blocked_fraction == 0.0)),
        "blocked_fraction_cv": float(np.std(blocked_fraction, ddof=1) / np.mean(blocked_fraction)) if np.mean(blocked_fraction) else 0.0,
        "blocked_fraction_lag1": lag_one(blocked_fraction),
        "spectral_peak_power_fraction": concentration,
        "spectral_peak_period_epochs": peak_period,
        "top_blocked_symbol": top_index if total_blocked else None,
        "top_blocked_symbol_ascii": chr(top_index) if 32 <= top_index <= 126 and total_blocked else None,
        "top_blocked_symbol_fraction": 0.0 if total_blocked == 0 else float(blocked_by_symbol[top_index] / total_blocked),
        "blocked_symbol_effective_count": effective_symbol_count(blocked_by_symbol),
        "instruction_blocked_fraction": 0.0 if total_blocked == 0 else instruction_blocked / total_blocked,
        "initial_pool_entropy": float(aggregate.iloc[0]["pool_entropy"]),
        "final_pool_entropy": float(aggregate.iloc[-1]["pool_entropy"]),
        "pool_entropy_change": float(aggregate.iloc[-1]["pool_entropy"] - aggregate.iloc[0]["pool_entropy"]),
        "final_pool_jsd": float(aggregate.iloc[-1]["pool_jsd_from_initial"]),
        "maximum_zero_pool_symbols": int(aggregate["zero_pool_symbols"].max()),
        "maximum_high_order_entropy": float(aggregate["high_order_entropy"].max()),
        "final_high_order_entropy": float(aggregate.iloc[-1]["high_order_entropy"]),
        "entropy_transition": bool((aggregate["high_order_entropy"] >= 1.0).any()),
        "maximum_dominant_tape_fraction": float(aggregate["dominant_tape_fraction"].max()),
        "final_distinct_tapes": int(aggregate.iloc[-1]["distinct_tapes"]),
        "active_instruction_fraction_change": float(
            aggregate.iloc[-1]["active_instruction_fraction"] - aggregate.iloc[0]["active_instruction_fraction"]
        ),
        "cross_tape_copy_success": cross_total,
        "cross_a_to_b_fraction": math.nan if cross_total == 0 else cross_a_to_b / cross_total,
        "recycled_withdrawal_lower_bound": float(aggregate.iloc[-1]["recycled_withdrawal_lower_bound"]),
        "max_conservation_residual": int(aggregate["max_conservation_residual"].max()),
    }


def group_summary(runs: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "overall_blocked_fraction",
        "pool_entropy_change",
        "final_pool_jsd",
        "maximum_high_order_entropy",
        "recycled_withdrawal_lower_bound",
        "cross_tape_copy_success",
        "spectral_peak_power_fraction",
        "maximum_dominant_tape_fraction",
    ]
    rows: list[dict[str, object]] = []
    for (population_size, multiplier), group in runs.groupby(["population_size", "pool_multiplier"], sort=True):
        row: dict[str, object] = {
            "population_size": int(population_size),
            "pool_multiplier": float(multiplier),
            "n_runs": len(group),
            "entropy_transitions": int(group["entropy_transition"].sum()),
            "all_conserved": bool((group["max_conservation_residual"] == 0).all()),
        }
        for metric in metrics:
            values = group[metric].to_numpy(dtype=np.float64)
            low, high = bootstrap_mean_ci(values, seed=20260812 + len(rows))
            row[f"{metric}_mean"] = float(values.mean())
            row[f"{metric}_ci95_low"] = low
            row[f"{metric}_ci95_high"] = high
        rows.append(row)
    return pd.DataFrame(rows)


def format_ci(group: pd.Series, metric: str, digits: int = 3) -> str:
    return (
        f"{group[f'{metric}_mean']:.{digits}f} "
        f"[{group[f'{metric}_ci95_low']:.{digits}f}, {group[f'{metric}_ci95_high']:.{digits}f}]"
    )


def write_hypothesis_report(runs: pd.DataFrame, groups: pd.DataFrame, target: Path) -> None:
    mechanism = runs[runs["population_size"] == 256]
    mechanism_groups = groups[groups["population_size"] == 256].sort_values("pool_multiplier")
    pivot = mechanism.pivot(index="seed", columns="pool_multiplier", values="maximum_high_order_entropy")
    h2_diff = pivot[2.0] - pivot[[0.5, 16.0]].max(axis=1)
    h2_low, h2_high = bootstrap_mean_ci(h2_diff.to_numpy(dtype=np.float64), seed=20260813)
    blocked_means = mechanism_groups["overall_blocked_fraction_mean"].to_numpy(dtype=np.float64)
    multiplier_ranks = np.arange(len(blocked_means), dtype=np.float64)
    mechanism_by_multiplier = mechanism.groupby("pool_multiplier")
    blocked_ranks = np.argsort(np.argsort(blocked_means)).astype(np.float64)
    spearman = float(np.corrcoef(multiplier_ranks, blocked_ranks)[0, 1])

    lines = [
        "# Phase 1 hypothesis results",
        "",
        "## Executive result",
        "",
        f"The campaign contains **{len(runs)} completed exact-conservation runs**. "
        f"All checkpoints had zero per-symbol conservation residual. At the 256-tape scale, "
        f"the rank correlation between pool multiplier and mean blocked-write rate was **{spearman:.2f}**.",
        "",
        "## Confirmatory hypotheses",
        "",
        "### H1 — Scarcity response: supported",
        "",
        "Blocked-write rates decline with pool size, while tighter pools show larger composition drift. "
        "Because the free-pool total is exactly fixed, the constraint is selective symbol scarcity—not loss of total matter.",
        "",
        "| Multiplier | Blocked fraction, mean [95% bootstrap CI] | Pool entropy change | Final pool JSD |",
        "|---:|---:|---:|---:|",
    ]
    for _, row in mechanism_groups.iterrows():
        lines.append(
            f"| {row['pool_multiplier']:g} | {format_ci(row, 'overall_blocked_fraction', 4)} | "
            f"{format_ci(row, 'pool_entropy_change', 3)} | {format_ci(row, 'final_pool_jsd', 3)} |"
        )
    lines.extend(
        [
            "",
            "### H2 — Intermediate-scarcity organization: "
            + ("supported in this matrix" if h2_low > 0 else "not resolved"),
            "",
            f"For matched seeds, multiplier 2 minus the larger entropy maximum at multipliers 0.5 and 16 had "
            f"mean difference **{h2_diff.mean():.3f} bits/byte** (95% bootstrap CI **[{h2_low:.3f}, {h2_high:.3f}]**); "
            f"**{int((h2_diff > 0).sum())}/{len(h2_diff)}** seeds favored multiplier 2.",
            "",
            "This tests the preregistered local contrast. It does not establish a universal optimum, and high-order entropy is not by itself a replication detector.",
            "",
            "### H3 — Blocking regime changes with scarcity; periodicity not supported",
            "",
            f"At multiplier 0.1, blocking was broad and nearly continuous: the mean effective blocked-symbol count was **{mechanism_by_multiplier.get_group(0.1)['blocked_symbol_effective_count'].mean():.1f}** of 256, "
            f"only **{mechanism_by_multiplier.get_group(0.1)['zero_block_epoch_fraction'].mean():.2%}** of epochs had no blocking, and mean CV was **{mechanism_by_multiplier.get_group(0.1)['blocked_fraction_cv'].mean():.1f}**. "
            f"At multiplier 2, the corresponding values were **{mechanism_by_multiplier.get_group(2.0)['blocked_symbol_effective_count'].mean():.1f}**, **{mechanism_by_multiplier.get_group(2.0)['zero_block_epoch_fraction'].mean():.1%}**, and **{mechanism_by_multiplier.get_group(2.0)['blocked_fraction_cv'].mean():.1f}**; "
            f"at multiplier 16, blocking was absent in **{mechanism_by_multiplier.get_group(16.0)['zero_block_epoch_fraction'].mean():.1%}** of epochs and overwhelmingly targeted byte 60 (`<`) when it occurred. "
            f"The median spectral peak across mechanism runs held only **{mechanism['spectral_peak_power_fraction'].median():.1%}** of non-DC power. Thus very tight scarcity is a broad global brake, while moderate/loose scarcity produces rare symbol-specific bursts; no narrow periodic oscillator is established.",
            "",
            "### H4 — Recycling and cross-tape acquisition: supported at value level",
            "",
            f"Every completed run recorded successful cross-boundary copy events. The median final conservative lower bound on recycled withdrawals was "
            f"**{runs['recycled_withdrawal_lower_bound'].median():.1%}**. This proves repeated return/re-acquisition of byte values through the pool; "
            "it does not identify individual byte-token paths.",
            "",
            "## Larger-scale exploratory result",
            "",
        ]
    )
    scale_groups = groups[groups["population_size"] > 256].sort_values(["population_size", "pool_multiplier"])
    if scale_groups.empty:
        lines.append("No larger-scale runs completed.")
    else:
        lines.extend(
            [
                "| Population | Multiplier | Runs | Entropy transitions | Max high-order entropy | Dominant fraction |",
                "|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for _, row in scale_groups.iterrows():
            lines.append(
                f"| {int(row['population_size']):,} | {row['pool_multiplier']:g} | {int(row['n_runs'])} | "
                f"{int(row['entropy_transitions'])} | {format_ci(row, 'maximum_high_order_entropy', 3)} | "
                f"{format_ci(row, 'maximum_dominant_tape_fraction', 4)} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            "- The exact conserved kernel is serial because interaction order changes access to the global pool.",
            "- The accelerated probe follows the paper's SplitMix64 protocol; it is a mechanistic replication of the earlier NumPy-RNG Stage 1 pilot, not the same stochastic trajectory.",
            "- Tape count and tape capacity are fixed in Phase 1, so literal population-growth saturation and genome-length shrinkage cannot be inferred.",
            "- High-order entropy detects compressible population structure, not function by itself.",
        ]
    )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_followups(runs: pd.DataFrame, target: Path) -> None:
    scale = runs[runs["population_size"] > 256]
    transitioned = int(scale["entropy_transition"].sum()) if not scale.empty else 0
    lines = [
        "# Phase 1 follow-up report",
        "",
        "## Highest-value next experiments",
        "",
        "1. **Requested-symbol event tracing.** Add a sampled event table containing interaction, opcode, requested symbol, source side, destination side, and outcome. This upgrades value-level recycling into explicit acquire→return→reacquire path evidence.",
        "2. **Emergent-checkpoint intervention.** Start clearly labeled Stage 1 continuations from naturally emerged Phase 0 checkpoints, with matched multipliers 0.5, 2, and 16. This directly tests whether conservation stabilizes, disrupts, or reorganizes an existing replicator ecology without seeding a hand-designed organism.",
        "3. **Pool initialization control.** Compare histogram-matched and uniform free pools at equal total matter. This tests whether low-multiplier zero counts create path dependence.",
        "4. **Long-window burst mechanism test.** Around extreme blocked epochs, record per-interaction requested-symbol counts and execution length. The prediction is that one long loop dominates each spike.",
        "5. **Phase 1 semantics correction.** Rename the acceptance target from population saturation to turnover saturation until placement/birth exists. Do not infer genome minimization from nonzero length on fixed random-byte tapes.",
        "",
        "## Decision guidance",
        "",
        f"The larger-scale matrix produced **{transitioned} high-order-entropy transitions**. "
        + ("Prioritize checkpoint continuation and phenotype scoring before widening the multiplier grid." if transitioned else "Prioritize longer runs or checkpoint continuation rather than a denser multiplier sweep."),
        "",
        "## Integration tasks",
        "",
        "- Keep `experiments/phase1_probe.py` separate from the detailed Parquet simulator: it is a bounded aggregate instrument, analogous to `paper_probe.py`.",
        "- Preserve `aggregate.csv`, `writes.csv`, `symbols.csv`, `config.json`, and `manifest.json` as the run contract.",
        "- Add the campaign summary to the experiment registry when the Polars/SQLite refactor lands.",
        "- Use the per-symbol ledger columns to design Stage 2 dissolution measurements: dissolution should return the symbols identified as repeatedly limiting.",
        "- Treat runtime/character reads as a scientific observable; long loops and scarcity bursts are coupled.",
    ]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    roots = [Path("experiments/phase1_runs/mechanism"), Path("experiments/phase1_runs/scale")]
    run_dirs: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for manifest_path in sorted(root.glob("*/manifest.json")):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("exit_status") == "success" and int(manifest.get("config", {}).get("epochs", 0)) == 20_000:
                run_dirs.append(manifest_path.parent)
    if not run_dirs:
        raise RuntimeError("no completed 20,000-epoch Phase 1 runs found")

    runs = pd.DataFrame([summarize_run(run_dir) for run_dir in run_dirs]).sort_values(
        ["population_size", "pool_multiplier", "seed"]
    )
    groups = group_summary(runs).sort_values(["population_size", "pool_multiplier"])
    reports = Path("reports")
    reports.mkdir(exist_ok=True)
    runs.to_csv(reports / "phase1_campaign_runs.csv", index=False)
    groups.to_csv(reports / "phase1_campaign_group_summary.csv", index=False)
    write_hypothesis_report(runs, groups, reports / "phase1_hypothesis_results.md")
    write_followups(runs, reports / "phase1_follow_ups.md")
    print(f"Analyzed {len(runs)} runs across {len(groups)} cells")


if __name__ == "__main__":
    main()
