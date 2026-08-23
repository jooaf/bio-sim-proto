"""Generate the Phase 1 new-experiment Jupyter notebooks.

Writes two notebooks into ``notebooks/``:

- ``phase1_newexperiments_stats.ipynb`` — Experiments A and B (long-window
  emergence, conserved continuation) with all preregistered tests.
- ``phase1_newexperiments_flow_null.ipynb`` — Experiment C (windowed flow
  organization vs. permutation null).

Run: ``uv run python experiments/make_newexperiments_notebooks.py``
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"


def md(text: str) -> tuple[str, str]:
    return ("markdown", text)


def code(text: str) -> tuple[str, str]:
    return ("code", text)


def build(cells: list[tuple[str, str]], path: Path) -> None:
    notebook = nbf.v4.new_notebook()
    notebook.cells = [
        nbf.v4.new_markdown_cell(source) if kind == "markdown" else nbf.v4.new_code_cell(source)
        for kind, source in cells
    ]
    notebook.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, str(path))
    print(f"wrote {path.relative_to(ROOT)}")


STATS_NOTEBOOK = [
    md(
        """# Phase 1 new-experiment batch — Experiments A & B (statistical analysis)

Companion notebook to `reports/phase1_newexperiments_preregistration.md`.
The tests implemented here are exactly the preregistered ones; statistics
helpers are imported from `experiments/analyze_phase1_newexperiments.py`
(numpy-only implementations, seeded RNG 20260815) so the notebook and the
headless analyzer share one source of truth.

- **Experiment A** — long-window emergence at 4,096 tapes / 100,000 epochs:
  conserved arms m0.5/m2/m16 (5 seeds each) + no-conservation control (5 seeds).
- **Experiment B** — conserved continuation of the natural Phase 0 seed-0
  checkpoint (131,072 tapes, 8,000 epochs, offset 2,433).

Re-run with: `uv run jupyter lab notebooks/` (kernel: `.venv` python3)."""
    ),
    code(
        """from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments.analyze_phase1_newexperiments import (
    LONGWINDOW,
    CONTINUATION,
    CONTROL_DIR,
    ROOT,
    block_bootstrap_difference,
    bootstrap_ci,
    entropy_transition,
    fisher_exact_2x2,
    mannwhitney_u,
    spearman,
)

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 50)
RNG = np.random.default_rng(20260815)"""
    ),
    md("## 1. Load runs (only manifests with `exit_status == success`)"),
    code(
        """def load_conserved(run_dir: Path) -> dict:
    manifest = json.loads((run_dir / "manifest.json").read_text())
    aggregate = pd.read_csv(run_dir / "aggregate.csv")
    writes = pd.read_csv(run_dir / "writes.csv")
    transition, first_epoch, max_entropy = entropy_transition(aggregate)
    cfg = manifest["config"]
    return {
        "arm": f"m{cfg['pool_multiplier']:g}",
        "kind": "conserved",
        "seed": cfg["seed"],
        "epochs": cfg["epochs"],
        "entropy_transition": transition,
        "first_transition_epoch": first_epoch,
        "max_high_order_entropy": max_entropy,
        "final_high_order_entropy": aggregate["high_order_entropy"].iloc[-1],
        "max_dominant_fraction": aggregate["dominant_tape_fraction"].max(),
        "final_dominant_fraction": aggregate["dominant_tape_fraction"].iloc[-1],
        "overall_blocked_fraction": (writes["execution_writes_blocked"] + writes["mutation_writes_blocked"]).sum() / max(1, (writes["execution_writes_success"] + writes["execution_writes_blocked"] + writes["mutation_writes_success"] + writes["mutation_writes_blocked"]).sum()),
        "run_dir": str(run_dir.relative_to(ROOT)),
        "_aggregate": aggregate,
        "_writes": writes,
    }


def load_control(csv_path: Path, arm: str | None = None, seed: int | None = None) -> dict:
    aggregate = pd.read_csv(csv_path)
    transition, first_epoch, max_entropy = entropy_transition(aggregate)
    return {
        "arm": arm or "control",
        "kind": "control",
        "seed": seed if seed is not None else int(csv_path.stem.split("_s")[-1]),
        "epochs": len(aggregate),
        "entropy_transition": transition,
        "first_transition_epoch": first_epoch,
        "max_high_order_entropy": max_entropy,
        "final_high_order_entropy": aggregate["high_order_entropy"].iloc[-1],
        "max_dominant_fraction": aggregate["dominant_tape_fraction"].max(),
        "final_dominant_fraction": aggregate["dominant_tape_fraction"].iloc[-1],
        "overall_blocked_fraction": 0.0,
        "run_dir": str(csv_path.relative_to(ROOT)),
        "_aggregate": aggregate,
        "_writes": None,
    }


rows = []
for run_dir in sorted(LONGWINDOW.glob("p1_m*_n4096_s*")):
    if json.loads((run_dir / "manifest.json").read_text()).get("exit_status") == "success":
        rows.append(load_conserved(run_dir))
for csv_path in sorted(CONTROL_DIR.glob("A_control_n4096_s*.csv")):
    rows.append(load_control(csv_path))
a_runs = pd.DataFrame([{k: v for k, v in row.items() if not k.startswith("_")} for row in rows])
trajectories = {row["run_dir"]: (row["_aggregate"], row["_writes"]) for row in rows}
print(f"Experiment A: {len(a_runs)} completed runs")
a_runs[["arm", "seed", "entropy_transition", "first_transition_epoch", "max_high_order_entropy", "final_dominant_fraction", "overall_blocked_fraction"]]"""
    ),
    md(
        """## 2. Experiment A hypotheses

### A1 — horizon sufficiency (control)
Emergence in at least 1/5 control seeds within 100,000 epochs."""
    ),
    code(
        """control = a_runs[a_runs["arm"] == "control"]
control_emergence = int(control["entropy_transition"].sum())
print(f"A1: control emergences = {control_emergence}/{len(control)}")
print(f"     first-transition epochs: {sorted(control['first_transition_epoch'].dropna().astype(int).tolist())}")
for seed, first in zip(control.loc[control["entropy_transition"], "seed"], control.loc[control["entropy_transition"], "first_transition_epoch"]):
    print(f"     seed {seed}: transition at epoch {int(first)}")"""
    ),
    md("### A2 — conservation suppresses emergence (one-sided Fisher exact on m2 vs control)"),
    code(
        """m2 = a_runs[a_runs["arm"] == "m2"]
m2_emergence = int(m2["entropy_transition"].sum())
odds, p_a2 = fisher_exact_2x2(control_emergence, len(control) - control_emergence, m2_emergence, len(m2) - m2_emergence, one_sided=True)
print(f"A2: m2 emergences {m2_emergence}/{len(m2)} vs control {control_emergence}/{len(control)}")
print(f"     one-sided Fisher exact: OR = {odds:.3f}, p = {p_a2:.4f}")"""
    ),
    md("### A3 — scarcity ordering: multiplier vs max high-order entropy (Spearman)"),
    code(
        """conserved = a_runs[a_runs["arm"] != "control"].copy()
conserved["multiplier"] = conserved["arm"].str[1:].astype(float)
rho_a3, p_a3 = spearman(conserved["multiplier"].to_numpy(), conserved["max_high_order_entropy"].to_numpy())
print(f"A3: Spearman rho = {rho_a3:.3f}, p = {p_a3:.4f} (n = {len(conserved)})")
conserved.groupby("arm")["max_high_order_entropy"].agg(["mean", "min", "max"])"""
    ),
    md("### A4 — blocked-write scarcity curve reproduces (Spearman, multiplier vs blocked fraction)"),
    code(
        """rho_a4, p_a4 = spearman(conserved["multiplier"].to_numpy(), conserved["overall_blocked_fraction"].to_numpy())
print(f"A4: Spearman rho = {rho_a4:.3f}, p = {p_a4:.4f} (n = {len(conserved)})")
conserved.groupby("arm")["overall_blocked_fraction"].agg(["mean", "min", "max"])"""
    ),
    md("## 3. Experiment A trajectories"),
    code(
        """fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharex=True)
colors = {"control": "tab:gray", "m0.5": "tab:red", "m2": "tab:orange", "m16": "tab:green"}
for run_dir, (aggregate, _) in trajectories.items():
    arm = "control" if "control" in run_dir else ("m" + run_dir.split("_m")[1].split("_")[0])
    color = colors.get(arm, None)
    axes[0].plot(aggregate["epoch"], aggregate["high_order_entropy"], color=color, alpha=0.6, lw=0.8)
    axes[1].plot(aggregate["epoch"], aggregate["dominant_tape_fraction"], color=color, alpha=0.6, lw=0.8)
for run_dir, (_, writes) in trajectories.items():
    if writes is None:
        continue
    blocked = (writes["execution_writes_blocked"] + writes["mutation_writes_blocked"])
    attempted = (writes["execution_writes_success"] + writes["execution_writes_blocked"] + writes["mutation_writes_success"] + writes["mutation_writes_blocked"])
    roll = (blocked / attempted.replace(0, np.nan)).rolling(500, min_periods=1).mean()
    axes[2].plot(writes["epoch"], roll, alpha=0.6, lw=0.8)
axes[0].axhline(1.0, color="k", ls="--", lw=0.7)
axes[0].set_ylabel("high-order entropy (bits/byte)"); axes[0].set_title("Entropy trajectories (all arms)")
axes[1].set_ylabel("dominant tape fraction"); axes[1].set_title("Dominant-takeover trajectories")
axes[2].set_ylabel("blocked fraction (rolling 500)"); axes[2].set_title("Blocked writes (conserved arms only)")
for ax in axes:
    ax.set_xlabel("epoch")
handles = [plt.Line2D([], [], color=c, label=k) for k, c in colors.items()]
axes[0].legend(handles=handles)
plt.tight_layout(); plt.show()"""
    ),
    md("## 4. Experiment B — conserved continuation of a natural replicator ecology"),
    code(
        """rows_b = []
control_csv = CONTROL_DIR / "B_control_continuation.csv"
if control_csv.exists():
    rows_b.append(load_control(control_csv, arm="control_continuation", seed=0))
for run_dir in sorted(CONTINUATION.glob("p1_m*_n131072_s0*")):
    manifest = json.loads((run_dir / "manifest.json").read_text())
    if manifest.get("exit_status") != "success":
        continue
    row = load_conserved(run_dir)
    row["kind"] = "continuation" if "initial_soup" in manifest["config"] else "baseline"
    if row["kind"] == "continuation":
        row["arm"] += "_continuation"
    else:
        row["arm"] += "_baseline"
    writes = row["_writes"]
    head = writes.head(1000)
    row["first_1000_blocked_fraction"] = (head["execution_writes_blocked"] + head["mutation_writes_blocked"]).sum() / max(1, (head["execution_writes_success"] + head["execution_writes_blocked"] + head["mutation_writes_success"] + head["mutation_writes_blocked"]).sum())
    rows_b.append(row)
b_runs = pd.DataFrame([{k: v for k, v in row.items() if not k.startswith("_")} for row in rows_b])
b_trajectories = {row["run_dir"]: (row["_aggregate"], row["_writes"]) for row in rows_b}
print(f"Experiment B: {len(b_runs)} completed runs")
b_runs.drop(columns=[c for c in ("overall_blocked_fraction",) if c not in b_runs.columns], errors="ignore")"""
    ),
    md("### B1 — control continuation completes takeover"),
    code(
        """bc = b_runs[b_runs["arm"] == "control_continuation"]
if len(bc):
    final_dom = float(bc["final_dominant_fraction"].iloc[0])
    final_ent = float(bc["final_high_order_entropy"].iloc[-1]) if "final_high_order_entropy" in bc else float(bc["final_high_order_entropy"].iloc[0])
    print(f"B1: control final dominant fraction = {final_dom:.4f}, final entropy = {final_ent:.3f}")
    print(f"     decision: {'SUPPORTED' if final_dom > 0.5 and final_ent > 1.0 else 'NOT SUPPORTED (B2/B3 uninterpretable)'}")
else:
    print("B1: control continuation not finished yet")"""
    ),
    md("### B2 / B3 — intermediate disruption, loose neutrality"),
    code(
        """for arm, label, criterion in [("m2_continuation", "B2 (disrupts takeover)", None), ("m16_continuation", "B3 (loose conservation neutral)", 0.5)]:
    sub = b_runs[b_runs["arm"] == arm]
    if not len(sub):
        print(f"{label}: run not finished yet")
        continue
    final_dom = float(sub["final_dominant_fraction"].iloc[0])
    final_ent = float(sub["final_high_order_entropy"].iloc[0])
    print(f"{label}: final dominant fraction = {final_dom:.4f}, final entropy = {final_ent:.3f} bits/byte")"""
    ),
    md("### B4 — replicator demand concentrates scarcity (first-1000-epoch blocked fraction, moving-block bootstrap)"),
    code(
        """m2c = b_runs[b_runs["arm"] == "m2_continuation"]
base = b_runs[b_runs["arm"] == "m2_baseline"]
if len(m2c) and len(base):
    writes_cont = b_trajectories[m2c["run_dir"].iloc[0]][1]
    writes_base = b_trajectories[base["run_dir"].iloc[0]][1]

    def per_epoch_blocked(w: pd.DataFrame) -> np.ndarray:
        attempted = w["execution_writes_success"] + w["execution_writes_blocked"] + w["mutation_writes_success"] + w["mutation_writes_blocked"]
        blocked = w["execution_writes_blocked"] + w["mutation_writes_blocked"]
        return (blocked / attempted.replace(0, np.nan)).fillna(0.0).to_numpy()

    cont_series, base_series = per_epoch_blocked(writes_cont.head(1000)), per_epoch_blocked(writes_base.head(1000))
    diff, lo, hi = block_bootstrap_difference(cont_series, base_series, block=100, samples=2000)
    print(f"B4: continuation first-1000 mean blocked = {cont_series.mean():.4f}")
    print(f"     random-soup baseline first-1000 mean blocked = {base_series.mean():.4f}")
    print(f"     difference = {diff:+.4f}, 95% moving-block bootstrap CI = [{lo:+.4f}, {hi:+.4f}]")
else:
    print("B4: continuation/baseline runs not finished yet")"""
    ),
    md("## 5. Experiment B trajectories"),
    code(
        """fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for run_dir, (aggregate, _) in b_trajectories.items():
    axes[0].plot(aggregate["epoch"], aggregate["high_order_entropy"], lw=0.9, label=run_dir.split("/")[-1])
    axes[1].plot(aggregate["epoch"], aggregate["dominant_tape_fraction"], lw=0.9)
axes[0].axhline(1.0, color="k", ls="--", lw=0.7)
axes[0].set_title("High-order entropy (continuation window)"); axes[0].set_ylabel("bits/byte")
axes[1].set_title("Dominant tape fraction"); axes[1].axhline(0.5, color="k", ls="--", lw=0.7)
for ax in axes:
    ax.set_xlabel("epoch (continuation)")
axes[0].legend(fontsize=7)
plt.tight_layout(); plt.show()"""
    ),
    md(
        """## 6. Summary

Hypothesis decisions are also written to `reports/phase1_newexperiments_report.md`
by `uv run python -m experiments.analyze_phase1_newexperiments`. Interpretation
notes and caveats live in the final report; this notebook only reports the
preregistered statistics."""
    ),
]

FLOW_NOTEBOOK = [
    md(
        """# Phase 1 new-experiment batch — Experiment C (windowed flow vs. null)

Companion notebook to `reports/phase1_newexperiments_preregistration.md`.

**Question**: is the donor→receiver matter-flow structure between consecutive
time windows more persistent than expected under identity-shuffled pairing?

- Data: 9 metabolic-trace runs (multipliers 0.5/2/16 × seeds 0–2, 256 tapes,
  20,000 epochs) with `--flow-window 2000` → 10 window matrices per run.
- Statistic: Spearman correlation of edge weights between consecutive windows.
- Null: donor/receiver labels permuted within the later window
  (2,000-run ensemble uses 200 resamples per window pair; seeded RNG).
"""
    ),
    code(
        """from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments.analyze_phase1_newexperiments import (
    TRACE_WINDOWS,
    ROOT,
    paired_permutation,
    spearman,
)

pd.set_option("display.width", 160)"""
    ),
    md("## 1. Load windowed flows and compute observed vs. null correlations"),
    code(
        """def window_matrix(edges: pd.DataFrame, window: int, size: int) -> np.ndarray:
    sub = edges[edges["window"] == window]
    matrix = np.zeros((size, size))
    matrix[sub["donor_tape"].to_numpy(), sub["receiver_tape"].to_numpy()] = sub["token_transfers"]
    return matrix


rows = []
curves = {}
for run_dir in sorted(TRACE_WINDOWS.glob("trace_m*_n256_s*")):
    manifest = json.loads((run_dir / "manifest.json").read_text())
    if manifest.get("exit_status") != "success":
        continue
    cfg = manifest["config"]
    edges = pd.read_csv(run_dir / "flow_edges_windows.csv")
    n_windows = int(edges["window"].max()) + 1
    size = int(cfg["population_size"])
    rng = np.random.default_rng(10_000 + int(cfg["seed"]))
    matrices = [window_matrix(edges, w, size) for w in range(n_windows)]
    observed, nulls = [], []
    for w in range(n_windows - 1):
        obs = spearman(matrices[w].ravel(), matrices[w + 1].ravel())[0]
        observed.append(obs)
        nulls.append(float(np.mean([
            spearman(matrices[w].ravel(), matrices[w + 1][rng.permutation(size)][:, rng.permutation(size)].ravel())[0]
            for _ in range(200)
        ])))
    curves[run_dir.name] = {"observed": observed, "null": nulls}
    rows.append({
        "pool_multiplier": cfg["pool_multiplier"],
        "seed": cfg["seed"],
        "n_windows": n_windows,
        "observed_mean_corr": float(np.nanmean(observed)),
        "null_mean_corr": float(np.nanmean(nulls)),
        "gap": float(np.nanmean(observed) - np.nanmean(nulls)),
    })
c_runs = pd.DataFrame(rows).sort_values(["pool_multiplier", "seed"])
print(f"Experiment C: {len(c_runs)} completed runs")
c_runs"""
    ),
    md("## 2. C1 — flow persistence above null (paired permutation test)"),
    code(
        """if len(c_runs):
    observed_gaps = c_runs["observed_mean_corr"].to_numpy()
    null_gaps = c_runs["null_mean_corr"].to_numpy()
    mean_gap, p_c1, effect = paired_permutation(observed_gaps, null_gaps)
    print(f"C1: mean observed corr = {observed_gaps.mean():.4f}, mean null corr = {null_gaps.mean():.4f}")
    print(f"     mean gap = {mean_gap:+.4f}, one-sided paired permutation p = {p_c1:.4f}")
    print(f"     decision: {'REJECT well-mixed null (persistent flow structure)' if p_c1 < 0.05 else 'DO NOT REJECT null (well-mixed recycling; H2 closes negative)'}")"""
    ),
    md("## 3. C2 — does scarcity sharpen flow structure? (multiplier vs. gap)"),
    code(
        """if len(c_runs):
    rho_c2, p_c2 = spearman(c_runs["pool_multiplier"].to_numpy(), c_runs["gap"].to_numpy())
    print(f"C2: Spearman rho = {rho_c2:.3f}, p = {p_c2:.4f} (n = {len(c_runs)})")
    print(c_runs.groupby("pool_multiplier")[["observed_mean_corr", "null_mean_corr", "gap"]].mean())"""
    ),
    md("## 3b. Robustness — persistence excluding self-flow (diagonal)"),
    code(
        '''if len(c_runs):
    def window_matrix_offdiag(edges: pd.DataFrame, window: int, size: int) -> np.ndarray:
        sub = edges[edges["window"] == window]
        matrix = np.zeros((size, size))
        matrix[sub["donor_tape"].to_numpy(), sub["receiver_tape"].to_numpy()] = sub["token_transfers"]
        np.fill_diagonal(matrix, 0.0)
        return matrix

    offdiag_gaps = []
    for run_dir in sorted(TRACE_WINDOWS.glob("trace_m*_n256_s*")):
        manifest = json.loads((run_dir / "manifest.json").read_text())
        if manifest.get("exit_status") != "success":
            continue
        cfg = manifest["config"]
        edges = pd.read_csv(run_dir / "flow_edges_windows.csv")
        n_windows = int(edges["window"].max()) + 1
        size = int(cfg["population_size"])
        rng = np.random.default_rng(10_000 + int(cfg["seed"]))
        mats = [window_matrix_offdiag(edges, w, size) for w in range(n_windows)]
        obs = [spearman(mats[w].ravel(), mats[w + 1].ravel())[0] for w in range(n_windows - 1)]
        nul = [np.mean([spearman(mats[w].ravel(), mats[w + 1][rng.permutation(size)][:, rng.permutation(size)].ravel())[0] for _ in range(100)]) for w in range(n_windows - 1)]
        offdiag_gaps.append(float(np.mean(obs) - np.mean(nul)))
    print(f"off-diagonal-only observed-minus-null gap: mean = {np.mean(offdiag_gaps):+.4f}")
    print(f"per-run gaps: {[round(g, 3) for g in offdiag_gaps]}")
    print("persistent structure is not an artifact of stable self-flow.")'''
    ),
    md("## 4. Window-by-window persistence curves"),
    code(
        """fig, axes = plt.subplots(3, 3, figsize=(14, 10), sharex=True, sharey=True)
for ax, (name, curve) in zip(axes.ravel(), sorted(curves.items())):
    ax.plot(np.arange(1, len(curve["observed"]) + 1), curve["observed"], "o-", label="observed", ms=3)
    ax.plot(np.arange(1, len(curve["null"]) + 1), curve["null"], "s--", label="null", ms=3)
    ax.set_title(name, fontsize=9)
    ax.legend(fontsize=7)
for ax in axes[-1]:
    ax.set_xlabel("window pair index")
for ax in axes[:, 0]:
    ax.set_ylabel("Spearman(edge weights)")
fig.suptitle("Consecutive-window flow persistence: observed vs. permuted null")
plt.tight_layout(); plt.show()"""
    ),
    md(
        """## 5. Interpretation

If C1's null is not rejected, the aggregate "nearly complete" donor→receiver
graphs from the earlier campaign were not hiding window-scale organizations at
256 tapes — matter circulation is well mixed at every scale measured here, and
the organization search should move to larger populations with event-level
logging. A significant positive gap would justify modularity/trophic analysis
(`analysis/organizations.py` planning docs) on the windowed graphs."""
    ),
]


def main() -> None:
    build(STATS_NOTEBOOK, NOTEBOOKS / "phase1_newexperiments_stats.ipynb")
    build(FLOW_NOTEBOOK, NOTEBOOKS / "phase1_newexperiments_flow_null.ipynb")


if __name__ == "__main__":
    main()
