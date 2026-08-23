"""Batch-2 analysis: shadowing onset (D2) and role-persistence decay (D3).

Preregistration: ``reports/phase1_batch2_preregistration.md``. D1
(population-scale runs) is summarized by
``experiments.analyze_phase1_newexperiments`` once those runs finish; this
module covers the analysis-only hypotheses on existing batch-1 data and the
D1 summaries when available.

Usage: ``uv run python -m experiments.analyze_phase1_batch2``
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.analyze_phase1_newexperiments import (
    LONGWINDOW,
    ROOT,
    TRACE_WINDOWS,
    CONTROL_DIR,
    entropy_transition,
    fisher_exact_2x2,
    format_p_value,
    mannwhitney_u,
    spearman,
)

REPORTS = ROOT / "reports"
BATCH2 = ROOT / "experiments/phase1_runs/batch2_scale"
BATCH3 = ROOT / "experiments/phase1_runs/batch3_scale"


def first_blocked_epoch(writes: pd.DataFrame) -> int:
    blocked = writes["execution_writes_blocked"] + writes["mutation_writes_blocked"]
    nonzero = writes["epoch"][blocked > 0]
    return int(nonzero.iloc[0]) if len(nonzero) else -1


def _scale_rows(
    run_root: Path,
    control_glob: str,
    population: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for run_dir in sorted(run_root.glob(f"p1_m*_n{population}_s*")):
        manifest = json.loads((run_dir / "manifest.json").read_text())
        if manifest.get("exit_status") != "success":
            continue
        aggregate = pd.read_csv(run_dir / "aggregate.csv")
        writes = pd.read_csv(run_dir / "writes.csv")
        transition, first_epoch, _ = entropy_transition(aggregate)
        entropy = aggregate["high_order_entropy"].to_numpy()
        distinct = aggregate["distinct_tapes"].to_numpy()
        max_collapse = float((distinct[0] - distinct.min()) / max(1, distinct[0]))
        rows.append(
            {
                "arm": f"m{manifest['config']['pool_multiplier']:g}",
                "seed": manifest["config"]["seed"],
                "entropy_transition": transition,
                "first_transition_epoch": first_epoch,
                "final_entropy": float(entropy[-1]),
                "held_to_end": bool(entropy[-1] > 1.0),
                "max_diversity_collapse": max_collapse,
                "structural_takeover": bool(transition and max_collapse >= 0.05),
                "first_blocked_epoch": first_blocked_epoch(writes),
            }
        )
    for csv in sorted((REPORTS / "phase1_newexperiments").glob(control_glob)):
        aggregate = pd.read_csv(csv)
        transition, first_epoch, _ = entropy_transition(aggregate)
        entropy = aggregate["high_order_entropy"].to_numpy()
        distinct = aggregate["distinct_tapes"].to_numpy()
        max_collapse = float((distinct[0] - distinct.min()) / max(1, distinct[0]))
        rows.append(
            {
                "arm": "control",
                "seed": int(csv.stem.split("_s")[-1]),
                "entropy_transition": transition,
                "first_transition_epoch": first_epoch,
                "final_entropy": float(entropy[-1]),
                "held_to_end": bool(entropy[-1] > 1.0),
                "max_diversity_collapse": max_collapse,
                "structural_takeover": bool(transition and max_collapse >= 0.05),
                "first_blocked_epoch": -1,
            }
        )
    return pd.DataFrame(rows)


def analyze_d1() -> pd.DataFrame:
    return _scale_rows(BATCH2, "D1_control_n16384_s*.csv", 16384)


def analyze_e1() -> pd.DataFrame:
    return _scale_rows(BATCH3, "E1_control_n32768_s*.csv", 32768)


def analyze_d2() -> tuple[pd.DataFrame, dict[str, float]]:
    rows = []
    for run_dir in sorted(LONGWINDOW.glob("p1_m*_n4096_s*")):
        manifest = json.loads((run_dir / "manifest.json").read_text())
        if manifest.get("exit_status") != "success":
            continue
        writes = pd.read_csv(run_dir / "writes.csv")
        rows.append(
            {
                "multiplier": manifest["config"]["pool_multiplier"],
                "seed": manifest["config"]["seed"],
                "first_blocked_epoch": first_blocked_epoch(writes),
            }
        )
    frame = pd.DataFrame(rows)
    rho, p = spearman(frame["multiplier"].to_numpy(), frame["first_blocked_epoch"].to_numpy())
    stats = {"spearman_rho": rho, "p_value": p, "n": len(frame)}
    return frame, stats


def window_matrix(edges: pd.DataFrame, window: int, size: int) -> np.ndarray:
    sub = edges[edges["window"] == window]
    matrix = np.zeros((size, size))
    matrix[sub["donor_tape"].to_numpy(), sub["receiver_tape"].to_numpy()] = sub["token_transfers"]
    return matrix


def analyze_d3(max_lag: int = 4) -> tuple[pd.DataFrame, dict[str, float], dict[str, float]]:
    lag_rows: list[dict[str, object]] = []
    diag_rows: list[dict[str, object]] = []
    for run_dir in sorted(TRACE_WINDOWS.glob("trace_m*_n256_s*")):
        manifest = json.loads((run_dir / "manifest.json").read_text())
        if manifest.get("exit_status") != "success":
            continue
        config = manifest["config"]
        edges = pd.read_csv(run_dir / "flow_edges_windows.csv")
        n_windows = int(edges["window"].max()) + 1
        size = int(config["population_size"])
        matrices = [window_matrix(edges, w, size) for w in range(n_windows)]
        for lag in range(1, max_lag + 1):
            correlations = [
                spearman(matrices[w].ravel(), matrices[w + lag].ravel())[0]
                for w in range(n_windows - lag)
            ]
            lag_rows.append(
                {
                    "pool_multiplier": config["pool_multiplier"],
                    "seed": config["seed"],
                    "lag": lag,
                    "mean_corr": float(np.nanmean(correlations)),
                }
            )
        diagonal_shares = [float(np.trace(m) / max(1.0, m.sum())) for m in matrices]
        diag_rows.append(
            {
                "pool_multiplier": config["pool_multiplier"],
                "seed": config["seed"],
                "mean_self_flow_share": float(np.mean(diagonal_shares)),
                "self_flow_share_cv": float(np.std(diagonal_shares) / max(1e-12, np.mean(diagonal_shares))),
            }
        )
    lags = pd.DataFrame(lag_rows)
    summary = lags.groupby("lag")["mean_corr"].mean().reset_index()
    rho_decay, p_decay = spearman(summary["lag"].to_numpy(), summary["mean_corr"].to_numpy())
    diag = pd.DataFrame(diag_rows)
    return (
        lags,
        {"spearman_rho": rho_decay, "p_value": p_decay, "n_lags": len(summary)},
        {"mean_cv": float(diag["self_flow_share_cv"].mean()), "mean_share": float(diag["mean_self_flow_share"].mean())},
    )


def main() -> None:
    lines: list[str] = ["# Phase 1 batch-2 analysis", ""]

    d1 = analyze_d1()
    if len(d1):
        lines += ["## D1 — 16,384-tape runs", "", d1.to_markdown(index=False), ""]
        control = d1[d1["arm"] == "control"]
        emergent = control[control["entropy_transition"]]
        lines += [
            f"- D1a: control emergences {int(control['entropy_transition'].sum())}/{len(control)} "
            f"(criterion >= 2/5: {'SUPPORTED' if control['entropy_transition'].sum() >= 2 else 'NOT SUPPORTED'})",
            f"- D1b: held-to-end among emergent controls: {int(emergent['held_to_end'].sum())}/{len(emergent)}",
            f"- Structural takeovers (entropy crossing + >=5% diversity collapse): "
            f"m16 {int(d1[d1['arm'] != 'control']['structural_takeover'].sum())}/5, "
            f"control {int(control['structural_takeover'].sum())}/5",
            "",
        ]
        m16 = d1[d1["arm"] != "control"]
        if len(m16) and (m16["first_blocked_epoch"] >= 0).any():
            batch1_first_blocks = []
            for run_dir in sorted(LONGWINDOW.glob("p1_m16_n4096_s*")):
                manifest = json.loads((run_dir / "manifest.json").read_text())
                if manifest.get("exit_status") == "success":
                    batch1_first_blocks.append(first_blocked_epoch(pd.read_csv(run_dir / "writes.csv")))
            stat, p = mannwhitney_u(
                m16.loc[m16["first_blocked_epoch"] >= 0, "first_blocked_epoch"].to_numpy(dtype=float),
                np.asarray(batch1_first_blocks, dtype=float),
                alternative="greater",
            )
            lines += [
                f"- D1c: first-block epoch median 16,384 = {m16.loc[m16['first_blocked_epoch'] >= 0, 'first_blocked_epoch'].median():.0f} "
                f"vs 4,096 batch-1 median = {np.median(batch1_first_blocks):.0f}; MW-U one-sided p = {p:.4f}",
                "",
            ]

    e1 = analyze_e1()
    if len(e1):
        lines += ["## E1 — 32,768-tape runs", "", e1.to_markdown(index=False), ""]
        control = e1[e1["arm"] == "control"]
        m16 = e1[e1["arm"] != "control"]
        control_crossings = int(control["entropy_transition"].sum())
        m16_crossings = int(m16["entropy_transition"].sum())
        control_held = int(control[control["entropy_transition"]]["held_to_end"].sum())
        m16_held = int(m16[m16["entropy_transition"]]["held_to_end"].sum())
        # E1b: pooled crossing x held contingency, m16 vs control.
        _, p_e1b = fisher_exact_2x2(
            m16_held, m16_crossings - m16_held,
            control_held, control_crossings - control_held,
            one_sided=False,
        )
        d2_m16 = analyze_d1()
        d2_m16_blocks = d2_m16.loc[(d2_m16["arm"] != "control") & (d2_m16["first_blocked_epoch"] >= 0), "first_blocked_epoch"].to_numpy(dtype=float)
        e1_m16_blocks = m16.loc[m16["first_blocked_epoch"] >= 0, "first_blocked_epoch"].to_numpy(dtype=float)
        _, p_e1c = mannwhitney_u(e1_m16_blocks, d2_m16_blocks, alternative="two-sided")
        lines += [
            f"- E1a: control emergences {control_crossings}/{len(control)} "
            f"(criterion >= 2/5: {'SUPPORTED' if control_crossings >= 2 else 'NOT SUPPORTED'})",
            f"- E1b: held-to-end among crossings — m16 {m16_held}/{m16_crossings}, control {control_held}/{control_crossings}; "
            f"Fisher exact two-sided p = {p_e1b:.4f}",
            f"- Structural takeovers: m16 {int(m16['structural_takeover'].sum())}/5, control {int(control['structural_takeover'].sum())}/5",
            f"- E1c: first-block epoch median 32,768 = {np.median(e1_m16_blocks):.0f} vs 16,384 = {np.median(d2_m16_blocks):.0f}; "
            f"MW-U two-sided p = {p_e1c:.4f} (scale-invariance confirmed if p > 0.05)",
            "",
        ]

    d2_frame, d2_stats = analyze_d2()
    lines += [
        "## D2 — shadowing onset (batch-1 A runs)",
        "",
        d2_frame.pivot_table(index="seed", columns="multiplier", values="first_blocked_epoch").to_markdown(),
        "",
        f"Spearman rho = {d2_stats['spearman_rho']:.3f}, p = {format_p_value(d2_stats['p_value'])} (n = {int(d2_stats['n'])}).",
        "",
    ]

    d3_lags, d3_stats, d3_diag = analyze_d3()
    lines += [
        "## D3 — role-persistence decay and self-flow share",
        "",
        d3_lags.groupby("lag")["mean_corr"].agg(["mean", "std"]).to_markdown(),
        "",
        f"D3a decay Spearman rho = {d3_stats['spearman_rho']:.3f}, p = {format_p_value(d3_stats['p_value'])}: "
        f"{'monotone decay (drifting roles)' if d3_stats['spearman_rho'] < 0 and d3_stats['p_value'] < 0.05 else 'no significant monotone decay'}",
        "",
        f"D3b self-flow share mean = {d3_diag['mean_share']:.4f}, CV across windows mean = {d3_diag['mean_cv']:.3f} "
        f"({'stationary' if d3_diag['mean_cv'] < 0.2 else 'non-stationary'})",
        "",
    ]

    (REPORTS / "phase1_batch2_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    d1.to_csv(REPORTS / "phase1_batch2_d1_runs.csv", index=False)
    e1.to_csv(REPORTS / "phase1_batch3_e1_runs.csv", index=False)
    print(f"wrote reports/phase1_batch2_report.md (D1 rows: {len(d1)}, E1 rows: {len(e1)})")


if __name__ == "__main__":
    main()
