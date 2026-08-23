"""Statistical analysis for the Phase 1 batch-6 origin-under-exclusion campaign.

Implements every preregistered test in
``reports/phase1_batch6_preregistration.md`` with numpy/pandas only.
Produces:

- ``reports/phase1_batch6_runs.csv``  (H1/H2 emergence rows)
- ``reports/phase1_batch6_report.md`` (hypothesis decisions)

Usage: ``uv run python -m experiments.analyze_phase1_batch6``
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
from experiments.paper_probe import initialize_soup

ROOT = Path(__file__).resolve().parents[1]
BATCH6 = ROOT / "experiments/phase1_runs/batch6_origin"
BATCH3 = ROOT / "experiments/phase1_runs/batch3_scale"
BATCH4 = ROOT / "experiments/phase1_runs/batch4_mismatch"
CONTROL_CSV = ROOT / "reports/phase1_newexperiments"
CHECKPOINT = ROOT / "runs/paper_probe_seed0_transition.npy"
REPORTS = ROOT / "reports"

TAPE_MATTER = 32768 * 64
NATURAL_SIX = [0, 60, 91, 44, 125, 93]
H1_DIGEST = "exlist6_4e46cb76"
H2_DIGEST = "exlist1_d202ef8d"
RANDOM_SOUP_SHARE_SIX = len(NATURAL_SIX) / 256


def soup_share(run_dir: Path, seed: int, symbols: list[int]) -> tuple[float, float]:
    """Initial and final soup share of `symbols` (conservation reconstruction)."""

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
    initial_share = float(counts[symbols].sum() / TAPE_MATTER)
    last_counts = conserved[last["symbol"].to_numpy()] - last["pool_count"].to_numpy(
        dtype=np.int64
    )
    final_share = float(
        last_counts[np.isin(last["symbol"].to_numpy(), symbols)].sum() / TAPE_MATTER
    )
    return initial_share, final_share


def blocked_concentration(run_dir: Path, symbols: list[int]) -> float:
    sym = pd.read_csv(run_dir / "symbols.csv")
    last = sym[sym["epoch"] == int(sym["epoch"].max())]
    blocked = last["execution_blocked"].to_numpy(dtype=np.int64) + last[
        "mutation_blocked"
    ].to_numpy(dtype=np.int64)
    total = int(blocked.sum())
    if total == 0:
        return float("nan")
    mask = np.isin(last["symbol"].to_numpy(), symbols)
    return float(blocked[mask].sum() / total)


def h_row(run_dir: Path, arm: str, seed: int, symbols: list[int]) -> dict[str, object] | None:
    loaded = load_run(run_dir)
    if loaded is None:
        return None
    manifest, aggregate, writes = loaded
    transition, first_epoch, max_entropy = entropy_transition(aggregate)
    entropy = aggregate["high_order_entropy"].to_numpy(dtype=float)
    initial_share, final_share = soup_share(run_dir, seed, symbols)
    return {
        "arm": arm,
        "seed": seed,
        "entropy_transition": transition,
        "first_transition_epoch": first_epoch,
        "max_high_order_entropy": max_entropy,
        "final_high_order_entropy": float(entropy[-1]),
        "held_to_end": bool(entropy[-1] >= 1.0),
        "initial_excluded_share": initial_share,
        "final_excluded_share": final_share,
        "excluded_share_growth": final_share / initial_share if initial_share else float("nan"),
        "blocked_fraction_on_excluded": blocked_concentration(run_dir, symbols),
        "overall_blocked_fraction": float(
            (
                writes["execution_writes_blocked"] + writes["mutation_writes_blocked"]
            ).sum()
            / max(
                (
                    writes["execution_writes_success"]
                    + writes["execution_writes_blocked"]
                    + writes["mutation_writes_success"]
                    + writes["mutation_writes_blocked"]
                ).sum(),
                1,
            )
        ),
        "max_conservation_residual": manifest.get("max_conservation_residual", -1),
        "run_dir": str(run_dir.relative_to(ROOT)),
    }


def control_emergence_counts() -> tuple[int, int]:
    """No-conservation control emergence at 32,768 (batch-3 E1 CSVs)."""

    crossings = 0
    total = 0
    for path in sorted(CONTROL_CSV.glob("E1_control_n32768_s*.csv")):
        aggregate = pd.read_csv(path)
        transition, _, _ = entropy_transition(aggregate)
        crossings += int(transition)
        total += 1
    return crossings, total


def natural_class_reference() -> float:
    """Excluded-six share of the natural epoch-2,433 checkpoint soup."""

    soup = np.load(CHECKPOINT)
    counts = np.bincount(soup.ravel(), minlength=256)
    return float(counts[NATURAL_SIX].sum() / counts.sum())


def matched_m16_emergent_shares() -> list[dict[str, object]]:
    """Final excluded-six share for emergent matched m16 runs (natural class)."""

    rows = []
    for seed in range(5):
        run_dir = BATCH3 / f"p1_m16_n32768_s{seed}"
        if not (run_dir / "symbols.csv").exists():
            continue
        manifest = __import__("json").loads((run_dir / "manifest.json").read_text())
        if manifest.get("exit_status") != "success":
            continue
        aggregate = pd.read_csv(run_dir / "aggregate.csv")
        transition, _, _ = entropy_transition(aggregate)
        _, final_share = soup_share(run_dir, seed, NATURAL_SIX)
        rows.append(
            {
                "seed": seed,
                "emergent": bool(transition),
                "final_six_share": final_share,
            }
        )
    return rows


def analyze() -> pd.DataFrame:
    rows = []
    for seed in range(5):
        row = h_row(BATCH6 / f"p1_m2_n32768_s{seed}_{H1_DIGEST}", "H1-exsix", seed, NATURAL_SIX)
        if row is not None:
            rows.append(row)
    for seed in range(3):
        row = h_row(BATCH6 / f"p1_m2_n32768_s{seed}_{H2_DIGEST}", "H2-ex0", seed, [0])
        if row is not None:
            rows.append(row)
    return pd.DataFrame(rows)


def decide(runs: pd.DataFrame) -> str:
    parts = []
    control_cross, control_total = control_emergence_counts()
    natural_ref = natural_class_reference()
    m16 = matched_m16_emergent_shares()
    emergent_m16_shares = [r["final_six_share"] for r in m16 if r["emergent"]]

    h1 = runs[runs["arm"] == "H1-exsix"]
    h2 = runs[runs["arm"] == "H2-ex0"]
    h1_cross = int(h1["entropy_transition"].sum())
    h2_cross = int(h2["entropy_transition"].sum())

    parts.append(
        f"Controls: no-conservation emergence {control_cross}/{control_total}; "
        f"natural checkpoint excluded-six share {natural_ref:.4f}; "
        f"random-soup baseline {RANDOM_SOUP_SHARE_SIX:.4f}."
    )
    if emergent_m16_shares:
        parts.append(
            "Matched m16 emergent final six-share: "
            + ", ".join(f"{value:.4f}" for value in emergent_m16_shares)
            + " (natural class grows the six symbols far above the baseline)."
        )

    for arm, frame, cross in (("H1", h1, h1_cross), ("H2", h2, h2_cross)):
        if not len(frame):
            continue
        parts.append(
            f"- **{arm}:** emergence {cross}/{len(frame)}, held "
            f"{int(frame['held_to_end'].sum())}/{len(frame)}; final excluded share "
            f"{frame['initial_excluded_share'].iloc[0]:.4f} -> median "
            f"{frame['final_excluded_share'].median():.4f}; blocked-on-excluded median "
            f"{frame['blocked_fraction_on_excluded'].median():.3f}."
        )
        for _, row in frame.iterrows():
            parts.append(
                f"  - seed {row['seed']}: emergent={row['entropy_transition']}, "
                f"Hmax {row['max_high_order_entropy']:.3f}, final H "
                f"{row['final_high_order_entropy']:.3f}, excluded share "
                f"{row['initial_excluded_share']:.4f} -> {row['final_excluded_share']:.4f} "
                f"(growth x{row['excluded_share_growth']:.2f}), blocked-on-excluded "
                f"{row['blocked_fraction_on_excluded']:.3f}."
            )

    if len(h1):
        _, p_two = fisher_exact_2x2(h1_cross, len(h1) - h1_cross, control_cross, control_total - control_cross)
        # One-sided "control emergence exceeds H1": control as the first group.
        _, p_one = fisher_exact_2x2(control_cross, control_total - control_cross, h1_cross, len(h1) - h1_cross, one_sided=True)
        parts.append(
            f"\n**H1a (suppression):** H1 {h1_cross}/{len(h1)} vs control "
            f"{control_cross}/{control_total}; one-sided Fisher p = {p_one:.3f} "
            f"(two-sided {p_two:.3f}). "
            f"{'SUPPORTED' if h1_cross < control_cross and p_one < 0.1 else 'not supported'}."
        )
        emergent_h1 = h1[h1["entropy_transition"]]
        if len(emergent_h1):
            class_changed = bool((emergent_h1["final_excluded_share"] <= 0.03).all())
            parts.append(
                f"**H1b (class change):** emergent H1 runs' final six-share: "
                + ", ".join(f"{v:.4f}" for v in emergent_h1["final_excluded_share"])
                + f" vs natural reference {natural_ref:.4f}. "
                f"{'SUPPORTED (breakthrough: distinct replicator class under matter constraint)' if class_changed else 'not met (excluded symbols grew toward the natural class)'}."
            )
        else:
            parts.append("**H1b:** no H1 emergent runs — class change untestable.")
        concentration_ok = bool(
            (h1["blocked_fraction_on_excluded"] >= 0.90).all()
        )
        parts.append(
            f"**H1c (mechanism):** blocked-write concentration on excluded symbols "
            f"{'>= 90% in all runs' if concentration_ok else 'below threshold in some runs'}."
        )

    if len(h2):
        _, p_two = fisher_exact_2x2(h2_cross, len(h2) - h2_cross, control_cross, control_total - control_cross)
        _, p_one = fisher_exact_2x2(control_cross, control_total - control_cross, h2_cross, len(h2) - h2_cross, one_sided=True)
        parts.append(
            f"\n**H2a:** H2 {h2_cross}/{len(h2)} vs control {control_cross}/{control_total} "
            f"(Fisher two-sided p = {p_two:.3f}, one-sided control>exclusion p = {p_one:.3f}; descriptive at n=3)."
        )
        emergent_h2 = h2[h2["entropy_transition"]]
        if len(emergent_h2):
            parts.append(
                f"**H2b:** emergent H2 symbol-0 final share: "
                + ", ".join(f"{v:.4f}" for v in emergent_h2["final_excluded_share"])
                + f" vs natural ~0.0458. "
                f"{'SUPPORTED' if bool((emergent_h2['final_excluded_share'] <= 0.006).all()) else 'not met'}."
            )
    return "\n".join(parts)


def main() -> None:
    runs = analyze()
    runs.to_csv(REPORTS / "phase1_batch6_runs.csv", index=False)
    parts = [
        "# Phase 1 batch-6 report — origin under exclusion",
        "",
        f"Generated {pd.Timestamp.now(tz='UTC').isoformat()}. Preregistration: "
        "`reports/phase1_batch6_preregistration.md`.",
        "",
        decide(runs),
        "",
        f"Conservation residuals nonzero in {int((runs['max_conservation_residual'] != 0).sum())} runs (expected 0).",
    ]
    (REPORTS / "phase1_batch6_report.md").write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {REPORTS / 'phase1_batch6_report.md'}")


if __name__ == "__main__":
    main()
