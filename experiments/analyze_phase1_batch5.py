"""Statistical analysis for the Phase 1 batch-5 exclusion-pool campaign.

Implements every preregistered test in
``reports/phase1_batch5_preregistration.md`` with numpy/pandas only.
Produces:

- ``reports/phase1_batch5_continuation.csv`` (G1/G2/G3 rows)
- ``reports/phase1_batch5_runs.csv``            (G4 emergence rows)
- ``reports/phase1_batch5_report.md``           (hypothesis decisions)

Usage: ``uv run python -m experiments.analyze_phase1_batch5``
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from experiments.analyze_phase1_batch4 import (
    load_run,
    longest_run_below,
)
from experiments.analyze_phase1_newexperiments import (
    blocked_fraction,
    entropy_transition,
    fisher_exact_2x2,
)

ROOT = Path(__file__).resolve().parents[1]
BATCH5 = ROOT / "experiments/phase1_runs/batch5_exclusion"
BATCH4 = ROOT / "experiments/phase1_runs/batch4_mismatch"
BATCH3 = ROOT / "experiments/phase1_runs/batch3_scale"
CHECKPOINT = ROOT / "runs/paper_probe_seed0_transition.npy"
REPORTS = ROOT / "reports"

TAPE_MATTER = 131072 * 64
EXCLUDED_TOP6 = [0, 60, 91, 44, 125, 93]
EXCLUDED_TOP1 = [0]


def checkpoint_counts() -> np.ndarray:
    soup = np.load(CHECKPOINT)
    return np.bincount(soup.ravel(), minlength=256).astype(np.int64)


def excluded_share_trajectory(run_dir: Path, excluded: list[int]) -> pd.DataFrame:
    """Excluded-symbol soup share per callback (conservation reconstruction)."""

    counts = checkpoint_counts()
    symbols = pd.read_csv(run_dir / "symbols.csv")
    first_epoch = int(symbols["epoch"].min())
    initial = symbols[symbols["epoch"] == first_epoch]
    conserved = (
        initial["initial_pool_count"].to_numpy(dtype=np.int64)
        + counts[initial["symbol"].to_numpy()]
    )
    rows = []
    for epoch, group in symbols.groupby("epoch", sort=True):
        symbols_idx = group["symbol"].to_numpy()
        soup = conserved[symbols_idx] - group["pool_count"].to_numpy(dtype=np.int64)
        share = float(soup[np.isin(symbols_idx, excluded)].sum() / TAPE_MATTER)
        rows.append({"epoch": int(epoch), "excluded_share": share})
    return pd.DataFrame(rows)


def blocked_concentration(run_dir: Path, excluded: list[int]) -> float:
    """Fraction of all blocked writes that target excluded symbols."""

    symbols = pd.read_csv(run_dir / "symbols.csv")
    last_epoch = int(symbols["epoch"].max())
    final = symbols[symbols["epoch"] == last_epoch]
    blocked = final["execution_blocked"].to_numpy(dtype=np.int64) + final[
        "mutation_blocked"
    ].to_numpy(dtype=np.int64)
    total = int(blocked.sum())
    if total == 0:
        return float("nan")
    mask = np.isin(final["symbol"].to_numpy(), excluded)
    return float(blocked[mask].sum() / total)


def continuation_row(run_dir: Path, arm: str, excluded: list[int]) -> dict[str, object] | None:
    loaded = load_run(run_dir)
    if loaded is None:
        return None
    manifest, aggregate, writes = loaded
    entropy = aggregate["high_order_entropy"].to_numpy(dtype=float)
    trajectory = excluded_share_trajectory(run_dir, excluded)
    shares = trajectory["excluded_share"].to_numpy(dtype=float)
    initial_share = float(checkpoint_counts()[excluded].sum() / TAPE_MATTER)
    jsd_pool = aggregate["soup_jsd_from_pool"].to_numpy(dtype=float)
    non_increasing = int(np.sum(np.diff(shares) <= 0)) / max(len(shares) - 1, 1)
    return {
        "arm": arm,
        "run_id": manifest["run_id"],
        "min_high_order_entropy": float(entropy.min()),
        "final_high_order_entropy": float(entropy[-1]),
        "viable_every_callback": bool((entropy > 1.0).all()),
        "longest_below_1_run_epochs": longest_run_below(entropy, 1.0) * 100,
        "initial_excluded_share": initial_share,
        "final_excluded_share": float(shares[-1]),
        "excluded_share_ratio": float(shares[-1] / initial_share),
        "excluded_share_non_increasing_fraction": non_increasing,
        "first_soup_jsd_from_pool": float(jsd_pool[0]),
        "final_soup_jsd_from_pool": float(jsd_pool[-1]),
        "jsd_pool_ratio": float(jsd_pool[-1] / jsd_pool[0]) if jsd_pool[0] > 0 else float("nan"),
        "blocked_fraction_on_excluded": blocked_concentration(run_dir, excluded),
        "overall_blocked_fraction": blocked_fraction(writes),
        "final_distinct_tapes": int(aggregate["distinct_tapes"].iloc[-1]),
        "final_dominant_fraction": float(aggregate["dominant_tape_fraction"].iloc[-1]),
        "final_active_instruction_fraction": float(aggregate["active_instruction_fraction"].iloc[-1]),
        "max_conservation_residual": manifest.get("max_conservation_residual", -1),
    }


def emergence_row(run_dir: Path, arm: str, seed: int) -> dict[str, object] | None:
    loaded = load_run(run_dir)
    if loaded is None:
        return None
    manifest, aggregate, writes = loaded
    transition, first_epoch, max_entropy = entropy_transition(aggregate)
    entropy = aggregate["high_order_entropy"].to_numpy(dtype=float)
    return {
        "arm": arm,
        "seed": seed,
        "entropy_transition": transition,
        "first_transition_epoch": first_epoch,
        "max_high_order_entropy": max_entropy,
        "final_high_order_entropy": float(entropy[-1]),
        "held_to_end": bool(entropy[-1] >= 1.0),
        "overall_blocked_fraction": blocked_fraction(writes),
        "max_conservation_residual": manifest.get("max_conservation_residual", -1),
        "run_dir": str(run_dir.relative_to(ROOT)),
    }


def analyze_continuations() -> pd.DataFrame:
    rows = []
    for run_dir, arm, excluded in (
        (BATCH5 / "p1_m2_n131072_s0_excl6_cont", "G1-excl6", EXCLUDED_TOP6),
        (BATCH5 / "p1_m2_n131072_s0_excl1_cont", "G2-excl1", EXCLUDED_TOP1),
        (BATCH5 / "p1_m0p05_n131072_s0_uniform_cont", "G3-U0.05", []),
        (BATCH5 / "p1_m0p1_n131072_s0_uniform_cont", "G3-U0.1", []),
    ):
        row = continuation_row(run_dir, arm, excluded)
        if row is not None:
            rows.append(row)
    return pd.DataFrame(rows)


def analyze_emergence() -> pd.DataFrame:
    rows = []
    # Uniform m16: batch-4 seeds 0-2, batch-5 seeds 3-4.
    for seed in (0, 1, 2):
        row = emergence_row(BATCH4 / f"p1_m16_n32768_s{seed}_uniform", "U16", seed)
        if row is not None:
            rows.append(row)
    for seed in (3, 4):
        row = emergence_row(BATCH5 / f"p1_m16_n32768_s{seed}_uniform", "U16", seed)
        if row is not None:
            rows.append(row)
    for seed in (0, 1, 2, 3, 4):
        row = emergence_row(BATCH3 / f"p1_m16_n32768_s{seed}", "M16", seed)
        if row is not None:
            rows.append(row)
    return pd.DataFrame(rows)


def decide(continuations: pd.DataFrame, emergence: pd.DataFrame) -> str:
    parts = []
    excl = continuations[continuations["arm"].str.startswith(("G1", "G2"))]
    tiny = continuations[continuations["arm"].str.startswith("G3")]

    for _, row in excl.iterrows():
        viable = bool(row["viable_every_callback"])
        disrupted = int(row["longest_below_1_run_epochs"]) >= 2000
        restructured = (
            viable
            and float(row["excluded_share_ratio"]) <= 0.5
            and float(row["jsd_pool_ratio"]) <= 0.5
        )
        parts.append(
            f"- **{row['arm']}:** viable={viable} (min entropy "
            f"{row['min_high_order_entropy']:.3f}), longest sub-1.0 run "
            f"{int(row['longest_below_1_run_epochs'])} epochs, excluded-symbol share "
            f"{row['initial_excluded_share']:.4f} -> {row['final_excluded_share']:.4f} "
            f"(ratio {row['excluded_share_ratio']:.3f}), JSD(soup,pool) "
            f"{row['first_soup_jsd_from_pool']:.4f} -> {row['final_soup_jsd_from_pool']:.4f} "
            f"(ratio {row['jsd_pool_ratio']:.3f}), blocked writes on excluded symbols "
            f"{row['blocked_fraction_on_excluded']:.3f}, share non-increasing at "
            f"{100 * float(row['excluded_share_non_increasing_fraction']):.1f}% of callbacks."
        )
        if disrupted:
            parts.append(f"  - **{row['arm']}a (disruption): SUPPORTED.**")
        elif restructured:
            parts.append(f"  - **{row['arm']}b (restructuring rescue / breakthrough): SUPPORTED.**")
        else:
            parts.append(f"  - **{row['arm']}a/{row['arm']}b: not met.**")
        ratchet = float(row["excluded_share_non_increasing_fraction"]) >= 0.95 and (
            not np.isnan(row["blocked_fraction_on_excluded"])
            and float(row["blocked_fraction_on_excluded"]) >= 0.80
        )
        parts.append(
            f"  - {row['arm']}c (ratchet + blocked concentration): "
            f"{'SUPPORTED' if ratchet else 'not met'}."
        )

    for _, row in tiny.iterrows():
        robust = bool(row["viable_every_callback"]) and float(row["overall_blocked_fraction"]) < 1e-3
        parts.append(
            f"- **{row['arm']}:** viable={row['viable_every_callback']} (min entropy "
            f"{row['min_high_order_entropy']:.3f}), blocked fraction "
            f"{row['overall_blocked_fraction']:.3e} -> G3 robustness "
            f"{'SUPPORTED' if robust else 'VIOLATED (absolute scarcity binds)'}."
        )

    if len(emergence):
        u16 = emergence[emergence["arm"] == "U16"]
        m16 = emergence[emergence["arm"] == "M16"]
        u_cross = int(u16["entropy_transition"].sum())
        m_cross = int(m16["entropy_transition"].sum())
        n = min(len(u16), len(m16))
        _, p_two = fisher_exact_2x2(u_cross, len(u16) - u_cross, m_cross, len(m16) - m_cross)
        _, p_one = fisher_exact_2x2(u_cross, len(u16) - u_cross, m_cross, len(m16) - m_cross, one_sided=True)
        parts.append(
            f"\n**G4:** uniform m16 emergence {u_cross}/{len(u16)} vs matched m16 "
            f"{m_cross}/{len(m16)}; Fisher exact two-sided p = {p_two:.3f} "
            f"(one-sided p = {p_one:.3f}). Held-to-end: U16 "
            f"{int(u16['held_to_end'].sum())}/{len(u16)}, M16 "
            f"{int(m16['held_to_end'].sum())}/{len(m16)}. "
            f"{'Supported (>= 4/5 uniform)' if u_cross >= 4 else 'Not supported at the 4/5 criterion'}."
        )
    return "\n".join(parts)


def main() -> None:
    continuations = analyze_continuations()
    emergence = analyze_emergence()
    continuations.to_csv(REPORTS / "phase1_batch5_continuation.csv", index=False)
    emergence.to_csv(REPORTS / "phase1_batch5_runs.csv", index=False)

    parts = [
        "# Phase 1 batch-5 report — exclusion pools",
        "",
        f"Generated {pd.Timestamp.now(tz='UTC').isoformat()}. Preregistration: "
        "`reports/phase1_batch5_preregistration.md`.",
        "",
        "## Continuations (G1/G2/G3)",
        decide(continuations, emergence),
        "",
    ]
    residual_bad = int(
        (continuations["max_conservation_residual"] != 0).sum()
        + (emergence["max_conservation_residual"] != 0).sum()
    )
    parts.append(f"Conservation residuals nonzero in {residual_bad} runs (expected 0).")
    (REPORTS / "phase1_batch5_report.md").write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {REPORTS / 'phase1_batch5_report.md'}")


if __name__ == "__main__":
    main()
