"""Statistical analysis for the Phase 1 batch-4 mismatched-pool campaign.

Implements every preregistered test in
``reports/phase1_batch4_preregistration.md`` with numpy/pandas only.
Produces:

- ``reports/phase1_batch4_f1_continuation.csv`` (F1 uniform + F3 control rows)
- ``reports/phase1_batch4_runs.csv``            (F2 emergence rows)
- ``reports/phase1_batch4_report.md``           (hypothesis decisions)

Usage: ``uv run python -m experiments.analyze_phase1_batch4``
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.analyze_phase1_newexperiments import (
    blocked_fraction,
    entropy_transition,
    fisher_exact_2x2,
)
from experiments.paper_probe import initialize_soup

ROOT = Path(__file__).resolve().parents[1]
BATCH4 = ROOT / "experiments/phase1_runs/batch4_mismatch"
BATCH3 = ROOT / "experiments/phase1_runs/batch3_scale"
CONTINUATION = ROOT / "experiments/phase1_runs/continuation"
CHECKPOINT = ROOT / "runs/paper_probe_seed0_transition.npy"
REPORTS = ROOT / "reports"

UNIFORM_MULTIPLIERS = (0.5, 2.0, 16.0)
F2_SEEDS = (0, 1, 2)


# ---------------------------------------------------------------------------
# Histogram / JSD helpers
# ---------------------------------------------------------------------------


def jsd_bits(a: np.ndarray, b: np.ndarray) -> float:
    """Base-2 Jensen-Shannon divergence between count vectors."""

    p = a.astype(np.float64) / float(a.sum())
    q = b.astype(np.float64) / float(b.sum())
    m = 0.5 * (p + q)

    def kl(x: np.ndarray) -> float:
        mask = x > 0
        return float(np.sum(x[mask] * np.log2(x[mask] / m[mask])))

    return 0.5 * (kl(p) + kl(q))


def initial_tape_counts(run_config: dict) -> np.ndarray:
    """Reconstruct the initial soup histogram from run config."""

    population = int(run_config["population_size"])
    seed = int(run_config["seed"])
    soup_path = run_config.get("initial_soup")
    if soup_path:
        soup = np.load(ROOT / soup_path if not Path(soup_path).is_absolute() else soup_path)
    else:
        soup = initialize_soup(population, seed)
    return np.bincount(soup.ravel(), minlength=256).astype(np.int64)


def initial_pool_counts(run_config: dict, tape_counts: np.ndarray) -> np.ndarray:
    """Reconstruct the initial pool histogram (matched or uniform mode)."""

    multiplier = float(run_config["pool_multiplier"])
    matched = np.rint(tape_counts.astype(np.float64) * multiplier).astype(np.int64)
    if run_config.get("pool_mode", "histogram_matched") == "uniform":
        total = int(matched.sum())
        pool = np.full(256, total // 256, dtype=np.int64)
        pool[: total % 256] += 1
        return pool
    return matched


def soup_histograms_from_symbols(run_dir: Path, run_config: dict) -> pd.DataFrame:
    """Reconstruct per-callback soup histograms from symbols.csv.

    Conservation gives soup_count[s] = conserved_total[s] - pool_count[s].
    """

    tape_counts = initial_tape_counts(run_config)
    pool0 = initial_pool_counts(run_config, tape_counts)
    conserved = tape_counts + pool0
    symbols = pd.read_csv(run_dir / "symbols.csv")
    symbols["soup_count"] = conserved[symbols["symbol"].to_numpy()] - symbols["pool_count"]
    return symbols


def jsd_trajectory(run_dir: Path, run_config: dict) -> pd.DataFrame:
    """JSD(soup, pool) and JSD(soup, uniform) per callback epoch."""

    pool0 = initial_pool_counts(run_config, initial_tape_counts(run_config))
    symbols = soup_histograms_from_symbols(run_dir, run_config)
    uniform = np.ones(256, dtype=np.int64)
    rows = []
    for epoch, group in symbols.groupby("epoch", sort=True):
        soup = np.zeros(256, dtype=np.int64)
        pool = np.zeros(256, dtype=np.int64)
        soup[group["symbol"].to_numpy()] = group["soup_count"].to_numpy()
        pool[group["symbol"].to_numpy()] = group["pool_count"].to_numpy()
        rows.append(
            {
                "epoch": int(epoch),
                "soup_jsd_from_pool": jsd_bits(soup, pool),
                "soup_jsd_from_uniform": jsd_bits(soup, uniform),
                "pool_jsd_from_initial": jsd_bits(pool, pool0),
            }
        )
    return pd.DataFrame(rows)


def longest_run_below(values: np.ndarray, threshold: float) -> int:
    """Longest run of consecutive values strictly below threshold."""

    best = current = 0
    for value in values:
        if value < threshold:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def load_run(run_dir: Path) -> tuple[dict, pd.DataFrame, pd.DataFrame] | None:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("exit_status") != "success":
        return None
    aggregate = pd.read_csv(run_dir / "aggregate.csv")
    writes = pd.read_csv(run_dir / "writes.csv")
    return manifest, aggregate, writes


# ---------------------------------------------------------------------------
# F1 + F3: continuations
# ---------------------------------------------------------------------------


def analyze_f1() -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    # Uniform arms (new metrics in aggregate.csv).
    for multiplier in UNIFORM_MULTIPLIERS:
        slug = format(multiplier, ".8g").replace(".", "p")
        run_dir = BATCH4 / f"p1_m{slug}_n131072_s0_uniform_cont"
        loaded = load_run(run_dir)
        if loaded is None:
            continue
        manifest, aggregate, writes = loaded
        entropy = aggregate["high_order_entropy"].to_numpy(dtype=float)
        jsd_pool = aggregate["soup_jsd_from_pool"].to_numpy(dtype=float)
        jsd_uniform = aggregate["soup_jsd_from_uniform"].to_numpy(dtype=float)
        rows.append(
            {
                "experiment": "F1",
                "arm": f"U{multiplier:g}",
                "run_id": manifest["run_id"],
                "epochs": manifest["config"]["epochs"],
                "min_high_order_entropy": float(entropy.min()),
                "final_high_order_entropy": float(entropy[-1]),
                "viable_every_callback": bool((entropy > 1.0).all()),
                "longest_below_1_run_epochs": longest_run_below(entropy, 1.0) * 100,
                "first_soup_jsd_from_pool": float(jsd_pool[0]),
                "final_soup_jsd_from_pool": float(jsd_pool[-1]),
                "jsd_pool_ratio": float(jsd_pool[-1] / jsd_pool[0]) if jsd_pool[0] > 0 else float("nan"),
                "first_soup_jsd_from_uniform": float(jsd_uniform[0]),
                "final_soup_jsd_from_uniform": float(jsd_uniform[-1]),
                "overall_blocked_fraction": blocked_fraction(writes),
                "final_zero_pool_symbols": int(aggregate["zero_pool_symbols"].iloc[-1]),
                "final_distinct_tapes": int(aggregate["distinct_tapes"].iloc[-1]),
                "final_dominant_fraction": float(aggregate["dominant_tape_fraction"].iloc[-1]),
                "max_conservation_residual": manifest.get("max_conservation_residual", -1),
            }
        )

    # Matched controls (F3): JSD trajectories reconstructed from symbols.csv.
    for multiplier in UNIFORM_MULTIPLIERS:
        slug = format(multiplier, ".8g").replace(".", "p")
        run_dir = CONTINUATION / f"p1_m{slug}_n131072_s0_cont"
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("exit_status") != "success":
            continue
        aggregate = pd.read_csv(run_dir / "aggregate.csv")
        writes = pd.read_csv(run_dir / "writes.csv")
        trajectory = jsd_trajectory(run_dir, manifest["config"])
        entropy = aggregate["high_order_entropy"].to_numpy(dtype=float)
        jsd_pool = trajectory["soup_jsd_from_pool"].to_numpy(dtype=float)
        jsd_uniform = trajectory["soup_jsd_from_uniform"].to_numpy(dtype=float)
        rows.append(
            {
                "experiment": "F3-control",
                "arm": f"M{multiplier:g}",
                "run_id": manifest["run_id"],
                "epochs": manifest["config"]["epochs"],
                "min_high_order_entropy": float(entropy.min()),
                "final_high_order_entropy": float(entropy[-1]),
                "viable_every_callback": bool((entropy > 1.0).all()),
                "longest_below_1_run_epochs": longest_run_below(entropy, 1.0) * 100,
                "first_soup_jsd_from_pool": float(jsd_pool[0]),
                "final_soup_jsd_from_pool": float(jsd_pool[-1]),
                "jsd_pool_ratio": float(jsd_pool[-1] / jsd_pool[0]) if jsd_pool[0] > 0 else float("nan"),
                "first_soup_jsd_from_uniform": float(jsd_uniform[0]),
                "final_soup_jsd_from_uniform": float(jsd_uniform[-1]),
                "overall_blocked_fraction": blocked_fraction(writes),
                "final_zero_pool_symbols": int(aggregate["zero_pool_symbols"].iloc[-1]),
                "final_distinct_tapes": int(aggregate["distinct_tapes"].iloc[-1]),
                "final_dominant_fraction": float(aggregate["dominant_tape_fraction"].iloc[-1]),
                "max_conservation_residual": manifest.get("max_conservation_residual", -1),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# F2: emergence at 32,768 tapes
# ---------------------------------------------------------------------------


def f2_row(run_dir: Path, arm: str, seed: int) -> dict[str, object] | None:
    loaded = load_run(run_dir)
    if loaded is None:
        return None
    manifest, aggregate, writes = loaded
    transition, first_epoch, max_entropy = entropy_transition(aggregate)
    entropy = aggregate["high_order_entropy"].to_numpy(dtype=float)
    # Final soup-vs-uniform JSD from symbols.csv reconstruction (works for
    # both new runs and pre-batch-4 runs without the new aggregate columns).
    trajectory = jsd_trajectory(run_dir, manifest["config"])
    blocked = writes["execution_writes_blocked"] + writes["mutation_writes_blocked"]
    first_block_epoch = None
    nonzero = writes.index[blocked > 0]
    if len(nonzero):
        first_block_epoch = int(writes["epoch"].iloc[nonzero[0]])
    return {
        "experiment": "F2",
        "arm": arm,
        "seed": seed,
        "entropy_transition": transition,
        "first_transition_epoch": first_epoch,
        "max_high_order_entropy": max_entropy,
        "final_high_order_entropy": float(entropy[-1]),
        "held_to_end": bool(entropy[-1] >= 1.0),
        "overall_blocked_fraction": blocked_fraction(writes),
        "first_block_epoch": first_block_epoch,
        "final_soup_jsd_from_uniform": float(trajectory["soup_jsd_from_uniform"].iloc[-1]),
        "final_soup_jsd_from_pool": float(trajectory["soup_jsd_from_pool"].iloc[-1]),
        "max_conservation_residual": manifest.get("max_conservation_residual", -1),
        "run_dir": str(run_dir.relative_to(ROOT)),
    }


def analyze_f2() -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    # New batch-4 runs: uniform m16/m2 seeds 0-2 and matched m2 pairs.
    for seed in F2_SEEDS:
        for arm, slug in (
            ("U16", "p1_m16_n32768_s%d_uniform"),
            ("U2", "p1_m2_n32768_s%d_uniform"),
            ("M2", "p1_m2_n32768_s%d"),
        ):
            row = f2_row(BATCH4 / (slug % seed), arm, seed)
            if row is not None:
                rows.append(row)

    # Matched m16 controls from batch 3 (seeds 0-4).
    for seed in (0, 1, 2, 3, 4):
        row = f2_row(BATCH3 / f"p1_m16_n32768_s{seed}", "M16", seed)
        if row is not None:
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Hypothesis decisions
# ---------------------------------------------------------------------------


def decide_f1(f1: pd.DataFrame) -> str:
    lines = ["## F1/F3 — mismatched-pool continuation (headline)"]
    uniform = f1[f1["experiment"] == "F1"].set_index("arm")
    matched = f1[f1["experiment"] == "F3-control"].set_index("arm")

    adapted = []
    for arm, row in uniform.iterrows():
        viable = bool(row["viable_every_callback"])
        adapted_jsd = float(row["jsd_pool_ratio"]) <= 0.5
        if viable and adapted_jsd:
            adapted.append(arm)
        lines.append(
            f"- **{arm}:** viability every callback = {viable} "
            f"(min entropy {row['min_high_order_entropy']:.3f}), "
            f"JSD(soup,pool) {row['first_soup_jsd_from_pool']:.4f} -> "
            f"{row['final_soup_jsd_from_pool']:.4f} "
            f"(ratio {row['jsd_pool_ratio']:.3f}), blocked fraction "
            f"{row['overall_blocked_fraction']:.3e}, longest sub-1.0 run "
            f"{int(row['longest_below_1_run_epochs'])} epochs."
        )

    control_ok = None
    if len(matched):
        thresholds = uniform["first_soup_jsd_from_pool"].astype(float)
        control_ok = all(
            float(row["final_soup_jsd_from_pool"]) < 0.10 * float(thresholds.max())
            for _, row in matched.iterrows()
        )
        for arm, row in matched.iterrows():
            lines.append(
                f"- Control {arm}: JSD(soup,pool) {row['first_soup_jsd_from_pool']:.4f} -> "
                f"{row['final_soup_jsd_from_pool']:.4f}, viable = {row['viable_every_callback']}, "
                f"blocked {row['overall_blocked_fraction']:.3e}."
            )

    if len(adapted) >= 2 and control_ok:
        lines.append(
            f"\n**F1-B: SUPPORTED (breakthrough).** Arms {adapted} remain viable while their "
            "content adapts to the pool (JSD(soup,pool) halves or better), and matched-pool "
            "controls stay matter-closed. The conserved economy exerts sustained directional "
            "selection on replicator content."
        )
    else:
        lines.append(
            f"\n**F1-B: not met** (adapted+viable arms: {adapted}; control discrimination = {control_ok})."
        )

    disrupted = [
        arm
        for arm, row in uniform.iterrows()
        if int(row["longest_below_1_run_epochs"]) >= 2000
    ]
    if disrupted:
        lines.append(
            f"**F1-D: SUPPORTED (disruption).** Arms {disrupted} sustain entropy < 1.0 for >= 2,000 "
            "epochs — matter-economy mismatch is lethal to an established ecology."
        )
    else:
        lines.append("**F1-D: not observed** (no uniform arm sustains entropy < 1.0 for 2,000 epochs).")
    return "\n".join(lines)


def decide_f2(f2: pd.DataFrame) -> str:
    lines = ["## F2 — mismatched-pool emergence at 32,768 tapes (paired seeds 0-2)"]

    def count(arm: str, column: str) -> pd.DataFrame:
        return f2[f2["arm"] == arm].set_index("seed")[[column]]

    for arm in ("U16", "U2", "M2", "M16"):
        sub = f2[f2["arm"] == arm]
        if len(sub):
            lines.append(
                f"- {arm}: emergence {int(sub['entropy_transition'].sum())}/{len(sub)}, "
                f"held {int(sub['held_to_end'].sum())}/{len(sub)}, "
                f"max entropy {sub['max_high_order_entropy'].max():.3f}, "
                f"final JSD(soup,uniform) median {sub['final_soup_jsd_from_uniform'].median():.4f}."
            )

    u16 = f2[f2["arm"] == "U16"].set_index("seed")
    m16 = f2[f2["arm"] == "M16"].set_index("seed")
    paired_seeds = sorted(set(u16.index) & set(m16.index))
    if paired_seeds:
        u_emergence = int(u16.loc[paired_seeds, "entropy_transition"].sum())
        m_emergence = int(m16.loc[paired_seeds, "entropy_transition"].sum())
        _, p = fisher_exact_2x2(u_emergence, len(paired_seeds) - u_emergence, m_emergence, len(paired_seeds) - m_emergence)
        lines.append(
            f"\n**F2a:** paired emergence U16 {u_emergence}/{len(paired_seeds)} vs M16 "
            f"{m_emergence}/{len(paired_seeds)} (seeds {paired_seeds}); Fisher exact two-sided "
            f"p = {p:.3f}. Directional note: uniform pool "
            f"{'raises' if u_emergence > m_emergence else 'lowers' if u_emergence < m_emergence else 'does not change'} "
            "emergence at this scale."
        )

    # F2b: content selection among emergent pairs.
    f2b_hits = 0
    f2b_total = 0
    for seed in paired_seeds:
        u_row = u16.loc[seed]
        m_row = m16.loc[seed]
        if bool(u_row["entropy_transition"]) and bool(m_row["entropy_transition"]):
            f2b_total += 1
            u_more_uniform = float(u_row["final_soup_jsd_from_uniform"]) < float(m_row["final_soup_jsd_from_uniform"])
            f2b_hits += int(u_more_uniform)
            lines.append(
                f"- seed {seed} emergent pair: final JSD(soup,uniform) U16 "
                f"{u_row['final_soup_jsd_from_uniform']:.4f} vs M16 {m_row['final_soup_jsd_from_uniform']:.4f} "
                f"({'U more uniform' if u_more_uniform else 'M more uniform'})."
            )
    lines.append(
        f"\n**F2b:** among {f2b_total} emergent m16 seed pairs, uniform pool produced more-uniform "
        f"content in {f2b_hits}/{f2b_total}."
    )

    # F2c: early scarcity binding.
    f2c_hits = 0
    for seed in paired_seeds:
        u_row = u16.loc[seed]
        m_row = m16.loc[seed]
        u_early = float(u_row["overall_blocked_fraction"])
        m_early = float(m_row["overall_blocked_fraction"])
        f2c_hits += int(u_early > m_early)
        lines.append(
            f"- seed {seed}: overall blocked fraction U16 {u_early:.3e} vs M16 {m_early:.3e} "
            f"(first block epoch U16 {u_row['first_block_epoch']}, M16 {m_row['first_block_epoch']})."
        )
    lines.append(
        f"\n**F2c:** uniform pool blocked fraction exceeds matched pair in {f2c_hits}/{len(paired_seeds)} m16 seed pairs."
    )
    return "\n".join(lines)


def main() -> None:
    f1 = analyze_f1()
    f2 = analyze_f2()
    f1.to_csv(REPORTS / "phase1_batch4_f1_continuation.csv", index=False)
    f2.to_csv(REPORTS / "phase1_batch4_runs.csv", index=False)

    parts = [
        "# Phase 1 batch-4 report — mismatched-pool economies",
        "",
        f"Generated {pd.Timestamp.now(tz='UTC').isoformat()}. Preregistration: "
        "`reports/phase1_batch4_preregistration.md`.",
        "",
    ]
    if len(f1):
        parts += [decide_f1(f1), ""]
    else:
        parts += ["## F1 — no completed uniform continuations found", ""]
    if len(f2):
        parts += [decide_f2(f2), ""]
    else:
        parts += ["## F2 — no completed emergence runs found", ""]

    residual_bad = int(
        (f1["max_conservation_residual"] != 0).sum() + (f2["max_conservation_residual"] != 0).sum()
    )
    parts.append(f"Conservation residuals nonzero in {residual_bad} runs (expected 0).")
    (REPORTS / "phase1_batch4_report.md").write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {REPORTS / 'phase1_batch4_report.md'}")


if __name__ == "__main__":
    main()
