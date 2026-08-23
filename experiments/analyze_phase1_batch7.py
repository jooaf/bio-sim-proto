"""Statistical analysis for the Phase 1 batch-7 specificity-control campaign.

Implements every preregistered test in
``reports/phase1_batch7_preregistration.md``. Produces:

- ``reports/phase1_batch7_runs.csv``   (I1/I2 emergence rows)
- ``reports/phase1_batch7_report.md``  (hypothesis decisions + I3 mechanism)

Usage: ``uv run python -m experiments.analyze_phase1_batch7``
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from experiments.analyze_phase1_batch4 import load_run
from experiments.analyze_phase1_newexperiments import (
    entropy_transition,
    fisher_exact_2x2,
)

ROOT = Path(__file__).resolve().parents[1]
BATCH7 = ROOT / "experiments/phase1_runs/batch7_specificity"
BATCH6 = ROOT / "experiments/phase1_runs/batch6_origin"
BATCH3 = ROOT / "experiments/phase1_runs/batch3_scale"
CONTROL_CSV = ROOT / "reports/phase1_newexperiments"
REPORTS = ROOT / "reports"

I1_DIGEST = "exlist6_aeece65c"
I2_DIGEST = "exlist1_09b9265b"
I1_SYMBOLS = [200, 201, 202, 203, 204, 205]
I2_SYMBOLS = [42]
H1_DIGEST = "exlist6_4e46cb76"
H2_DIGEST = "exlist1_d202ef8d"
NATURAL_SIX = [0, 60, 91, 44, 125, 93]
STRUCTURAL = [91, 93, 60, 44, 125, 0]  # [ ] < , } and null


def emergence_row(run_dir: Path, arm: str, seed: int) -> dict[str, object] | None:
    loaded = load_run(run_dir)
    if loaded is None:
        return None
    manifest, aggregate, writes = loaded
    transition, first_epoch, max_entropy = entropy_transition(aggregate)
    entropy = aggregate["high_order_entropy"].to_numpy(dtype=float)
    blocked_total = int(
        (writes["execution_writes_blocked"] + writes["mutation_writes_blocked"]).sum()
    )
    return {
        "arm": arm,
        "seed": seed,
        "entropy_transition": transition,
        "first_transition_epoch": first_epoch,
        "max_high_order_entropy": max_entropy,
        "final_high_order_entropy": float(entropy[-1]),
        "held_to_end": bool(entropy[-1] >= 1.0),
        "median_entropy": float(np.median(entropy)),
        "blocked_writes_total": blocked_total,
        "max_conservation_residual": manifest.get("max_conservation_residual", -1),
        "run_dir": str(run_dir.relative_to(ROOT)),
    }


def control_emergence_counts() -> tuple[int, int]:
    crossings = 0
    total = 0
    for path in sorted(CONTROL_CSV.glob("E1_control_n32768_s*.csv")):
        aggregate = pd.read_csv(path)
        transition, _, _ = entropy_transition(aggregate)
        crossings += int(transition)
        total += 1
    return crossings, total


def structural_growth(run_dir: Path, seed: int) -> dict[str, float]:
    """Initial -> final soup share of the six structural symbols."""

    from experiments.paper_probe import initialize_soup

    initial_soup = initialize_soup(32768, seed)
    counts = np.bincount(initial_soup.ravel(), minlength=256).astype(np.int64)
    sym = pd.read_csv(run_dir / "symbols.csv")
    first_epoch = int(sym["epoch"].min())
    last_epoch = int(sym["epoch"].max())
    first = sym[sym["epoch"] == first_epoch]
    last = sym[sym["epoch"] == last_epoch]
    conserved = (
        first["initial_pool_count"].to_numpy(dtype=np.int64)
        + counts[first["symbol"].to_numpy()]
    )
    last_counts = conserved[last["symbol"].to_numpy()] - last["pool_count"].to_numpy(
        dtype=np.int64
    )
    tape_matter = 32768 * 64
    idx = last["symbol"].to_numpy()
    return {
        "initial_structural_share": float(counts[STRUCTURAL].sum() / tape_matter),
        "final_structural_share": float(last_counts[np.isin(idx, STRUCTURAL)].sum() / tape_matter),
    }


def analyze() -> pd.DataFrame:
    rows = []
    for seed in range(5):
        row = emergence_row(BATCH7 / f"p1_m2_n32768_s{seed}_{I1_DIGEST}", "I1-ctrl6", seed)
        if row is not None:
            rows.append(row)
    for seed in range(3):
        row = emergence_row(BATCH7 / f"p1_m2_n32768_s{seed}_{I2_DIGEST}", "I2-ctrl1", seed)
        if row is not None:
            rows.append(row)
    return pd.DataFrame(rows)


def i3_mechanism() -> str:
    parts = ["### I3 — mechanism in suppressed runs (analysis-only)"]
    for label, digest, seeds in (("H1", H1_DIGEST, range(5)), ("H2", H2_DIGEST, range(3))):
        for seed in seeds:
            run_dir = BATCH6 / f"p1_m2_n32768_s{seed}_{digest}"
            if not (run_dir / "symbols.csv").exists():
                continue
            growth = structural_growth(run_dir, seed)
            parts.append(
                f"- {label} seed {seed}: structural-six share "
                f"{growth['initial_structural_share']:.4f} -> "
                f"{growth['final_structural_share']:.4f}."
            )
    for seed in range(5):
        run_dir = BATCH3 / f"p1_m16_n32768_s{seed}"
        if not (run_dir / "symbols.csv").exists():
            continue
        aggregate = pd.read_csv(run_dir / "aggregate.csv")
        transition, _, _ = entropy_transition(aggregate)
        growth = structural_growth(run_dir, seed)
        parts.append(
            f"- matched m16 seed {seed} (emergent={bool(transition)}): structural-six share "
            f"{growth['initial_structural_share']:.4f} -> {growth['final_structural_share']:.4f}."
        )
    return "\n".join(parts)


def decide(runs: pd.DataFrame) -> str:
    parts = []
    control_cross, control_total = control_emergence_counts()
    i1 = runs[runs["arm"] == "I1-ctrl6"]
    i2 = runs[runs["arm"] == "I2-ctrl1"]
    i1_cross = int(i1["entropy_transition"].sum())
    i2_cross = int(i2["entropy_transition"].sum())
    h1_blocked = (2_500_000_000, 3_400_000_000)  # batch-6 reference range

    for arm, frame, cross in (("I1", i1, i1_cross), ("I2", i2, i2_cross)):
        if not len(frame):
            continue
        parts.append(
            f"- **{arm}:** emergence {cross}/{len(frame)}, held "
            f"{int(frame['held_to_end'].sum())}/{len(frame)}; median entropy "
            f"{frame['median_entropy'].median():.3f}; blocked-write totals "
            f"{frame['blocked_writes_total'].min():.3e}–{frame['blocked_writes_total'].max():.3e} "
            f"(batch-6 H1 reference ~{h1_blocked[0]:.1e}–{h1_blocked[1]:.1e})."
        )
        for _, row in frame.iterrows():
            parts.append(
                f"  - seed {row['seed']}: emergent={row['entropy_transition']}, "
                f"held={row['held_to_end']}, Hmax {row['max_high_order_entropy']:.3f}, "
                f"final H {row['final_high_order_entropy']:.3f}, "
                f"blocked {row['blocked_writes_total']:.3e}."
            )

    if len(i1):
        _, p_two = fisher_exact_2x2(i1_cross, len(i1) - i1_cross, control_cross, control_total - control_cross)
        i1_supported = i1_cross >= 2
        parts.append(
            f"\n**I1 (specificity):** I1 {i1_cross}/{len(i1)} vs control "
            f"{control_cross}/{control_total} (Fisher two-sided p = {p_two:.3f}). "
            f"{'SUPPORTED (>= 2/5): suppression is class-specific' if i1_supported else 'NOT MET (<= 1/5): suppression is generic friction'}."
        )
    if len(i2):
        parts.append(
            f"\n**I2:** I2 {i2_cross}/{len(i2)} vs control {control_cross}/{control_total}; "
            f"H2 (symbol-0 exclusion) was 0/3. "
            f"{'Consistent with null-byte specificity' if i2_cross >= 1 else 'Suppression also generic at single-symbol level'}."
        )
    return "\n".join(parts)


def main() -> None:
    runs = analyze()
    runs.to_csv(REPORTS / "phase1_batch7_runs.csv", index=False)
    parts = [
        "# Phase 1 batch-7 report — specificity control",
        "",
        f"Generated {pd.Timestamp.now(tz='UTC').isoformat()}. Preregistration: "
        "`reports/phase1_batch7_preregistration.md`.",
        "",
        decide(runs),
        "",
        i3_mechanism(),
        "",
        f"Conservation residuals nonzero in {int((runs['max_conservation_residual'] != 0).sum())} runs (expected 0).",
    ]
    (REPORTS / "phase1_batch7_report.md").write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {REPORTS / 'phase1_batch7_report.md'}")


if __name__ == "__main__":
    main()
