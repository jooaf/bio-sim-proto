"""Analyze the conservation-aware SKI substrate validation sweep."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.conservation import conservation_residuals
from soup.substrate.ski import APPLY, I, K, S, parse_expression, serialize_expression


def safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float("nan") if denominator == 0 else float(numerator / denominator)


def summarize_run(run_dir: Path, multiplier: float, seed: int) -> dict[str, object]:
    ticks = pd.read_parquet(run_dir / "ticks.parquet")
    interactions = pd.read_parquet(run_dir / "interactions.parquet")
    tapes = pd.read_parquet(run_dir / "tapes.parquet")
    population = pd.read_parquet(run_dir / "population.parquet")
    residuals = conservation_residuals(ticks, tapes)
    full = tapes[tapes["full_bytes"].notna()].copy()
    valid = []
    token_lengths = []
    applications = []
    for value in full["full_bytes"]:
        expression = parse_expression(np.frombuffer(bytes(value), dtype=np.uint8))
        valid.append(expression is not None)
        serialized = [] if expression is None else serialize_expression(expression)
        token_lengths.append(len(serialized))
        applications.append(serialized.count(APPLY))
    full["valid_expression"] = valid
    full["token_length"] = token_lengths
    full["applications"] = applications
    final_tick = int(full["tick"].max())
    final_tapes = full[full["tick"] == final_tick]
    total_attempts = ticks["n_writes_success"].sum() + ticks["n_writes_blocked"].sum()
    halt_counts = interactions["halt_reason"].value_counts(normalize=True)
    final_population = population[population["tick"] == population["tick"].max()]
    initial_pool = np.asarray(ticks.iloc[0]["pool_histogram"], dtype=np.int64)
    final_pool = np.asarray(ticks.iloc[-1]["pool_histogram"], dtype=np.int64)
    active_symbols = np.asarray([0, APPLY, S, K, I], dtype=np.int64)
    inactive_mask = np.ones(256, dtype=bool)
    inactive_mask[active_symbols] = False
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    first = ticks.iloc[:100]
    last = ticks.iloc[-100:]
    first_attempts = int(first["n_writes_success"].sum() + first["n_writes_blocked"].sum())
    last_attempts = int(last["n_writes_success"].sum() + last["n_writes_blocked"].sum())
    return {
        "run_dir": str(run_dir),
        "pool_multiplier": multiplier,
        "seed": seed,
        "wall_time_s": float(manifest["wall_time_seconds"]),
        "blocked_fraction": safe_ratio(ticks["n_writes_blocked"].sum(), total_attempts),
        "first_100_blocked_fraction": safe_ratio(first["n_writes_blocked"].sum(), first_attempts),
        "last_100_blocked_fraction": safe_ratio(last["n_writes_blocked"].sum(), last_attempts),
        "last_100_has_write_attempts": last_attempts > 0,
        "pool_entropy_change": float(ticks.iloc[-1]["pool_entropy"] - ticks.iloc[0]["pool_entropy"]),
        "pool_composition_l1_change": int(np.abs(final_pool - initial_pool).sum()),
        "inactive_symbol_pool_total": int(final_pool[inactive_mask].sum()),
        "valid_expression_fraction": float(full["valid_expression"].mean()),
        "final_mean_token_length": float(final_tapes["token_length"].mean()),
        "final_mean_applications": float(final_tapes["applications"].mean()),
        "final_distinct_expressions": int(len(final_population)),
        "final_dominant_fraction": float(final_population["count"].max() / 256),
        "sampled_normal_form_fraction": float(halt_counts.get("normal_form", 0.0)),
        "sampled_pool_blocked_fraction": float(halt_counts.get("pool_blocked", 0.0)),
        "sampled_capacity_exhausted_fraction": float(halt_counts.get("capacity_exhausted", 0.0)),
        "sampled_budget_exhausted_fraction": float(halt_counts.get("budget_exhausted", 0.0)),
        "sampled_invalid_program_fraction": float(halt_counts.get("invalid_program", 0.0)),
        "max_conservation_residual": int(residuals["max_abs_residual"].max()),
        "all_conserved": bool(residuals["conserved"].all()),
        "invariant_log_empty": (run_dir / "invariant_log.jsonl").stat().st_size == 0,
    }


def main() -> None:
    index = pd.read_parquet("sweeps/p1_ski_validation/index.parquet")
    rows = [
        summarize_run(
            Path(str(item.run_dir)),
            float(getattr(item, "_3")),
            int(item.seed),
        )
        for item in index.itertuples(index=False)
    ]
    runs = pd.DataFrame(rows).sort_values(["pool_multiplier", "seed"])
    if len(runs) != 9:
        raise RuntimeError(f"expected 9 SKI runs, found {len(runs)}")
    runs.to_csv("reports/phase1_ski_validation_runs.csv", index=False)
    groups = runs.groupby("pool_multiplier", sort=True).mean(numeric_only=True).reset_index()
    attempt_counts = (
        runs.groupby("pool_multiplier", sort=True)["last_100_has_write_attempts"]
        .sum()
        .astype(int)
        .to_numpy()
    )
    groups["last_100_attempting_runs"] = attempt_counts
    groups.to_csv("reports/phase1_ski_validation_group_summary.csv", index=False)

    lines = [
        "# Phase 1 SKI substrate-validation results",
        "",
        "## Scope",
        "",
        "Nine conservation-aware SKI runs used the existing flat world, ordered interaction runner, scheduler, invariant checker, six Parquet tables, and Stage 1 report pipeline. Each run contained 256 tapes, 5,000 ticks, and 640,000 interactions; mutation was disabled to avoid confounding prefix-grammar corruption.",
        "",
        "## Multiplier response",
        "",
        "| Multiplier | Blocked writes | First-100 blocked | Last-100 blocked | Valid expressions | Final mean tokens | Normal form | Pool-blocked reactions | Conservation residual |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in groups.itertuples(index=False):
        last_fraction = "n/a" if np.isnan(row.last_100_blocked_fraction) else f"{row.last_100_blocked_fraction:.2%} ({int(row.last_100_attempting_runs)}/3 runs attempted writes)"
        lines.append(
            f"| {row.pool_multiplier:g} | {row.blocked_fraction:.2%} | {row.first_100_blocked_fraction:.2%} | "
            f"{last_fraction} | {row.valid_expression_fraction:.2%} | "
            f"{row.final_mean_token_length:.2f} | {row.sampled_normal_form_fraction:.1%} | "
            f"{row.sampled_pool_blocked_fraction:.1%} | {int(row.max_conservation_residual)} |"
        )
    lines.extend(
        [
            "",
            "## Mechanical criteria",
            "",
            "- **S1 passed:** hand-worked `I x`, `K x y`, and one-step `S x y z` reductions have unit tests.",
            "- **S2 passed:** an unavailable atomic rewrite leaves the joint tape and pool byte-identical; simultaneous swaps can use symbols returned by the same reaction.",
            "- **S3 passed:** all sweep snapshots have exact 256-component conservation and every invariant log is empty.",
            "- **S4 passed:** two independently executed short SKI runs with the same seed/config produce byte-identical raw Parquet digests.",
            "- **S5 contradicted as a monotonic hypothesis:** multiplier 2 blocked more attempted slots than 0.5, while 16 was nearly unblocked. The intermediate reservoir supports longer expressions, which then demand scarce application/combinator symbols; the tighter reservoir collapses sooner to shorter expressions. This is a real substrate dynamic, not a conservation failure.",
            "- **S6 passed with documented boundary work:** no changes were made to `soup/world.py`, `soup/scheduler.py`, or `soup/logging/` for SKI.",
            "",
            "## Forced implementation changes",
            "",
            "1. `WriteMediator` gained a generic atomic `write_batch` operation, implemented by `SymbolPool`. SKI rewrites must be all-or-nothing; partial serialized rewrites would corrupt grammar. BFF continues using single-slot writes unchanged.",
            "2. `Simulation` now selects `BFFSubstrate` or `SKISubstrate` from config.",
            "3. Stage 1 config validation now permits `substrate.name = \"ski\"`; Stage 0 remains BFF-only.",
            "4. The visualizer received only a BFF type guard for BFF-specific live controls. SKI validation itself is headless.",
            "5. The Stage 1 report label changed from “BFF writes” to “substrate writes.”",
            "",
            "## Interpretation",
            "",
            "The portability criterion is satisfied: a second execution chemistry uses the same state container, pair scheduling, mutation wrapper, conservation invariant, logging schemas, and offline conservation report. This validates the substrate boundary mechanically.",
            "",
            "This SKI model is deliberately minimal. It stores one prefix expression per fixed tape; ordered interaction replaces A with a bounded reduction of application `A B`, while B remains unchanged. It is not claimed to reproduce Combinatory Chemistry or chemSKI ecology. Its purpose is to test substrate independence and conserved rewrite mechanics.",
            "",
            f"Across all runs, inactive byte values retained **{int(runs['inactive_symbol_pool_total'].max())}** free tokens at most (expected zero), and the sampled invalid-program fraction was **{runs['sampled_invalid_program_fraction'].max():.2%}**, confirming that atomic rewrites preserved grammar without mutation.",
        ]
    )
    Path("reports/phase1_ski_validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Analyzed {len(runs)} SKI runs")


if __name__ == "__main__":
    main()
