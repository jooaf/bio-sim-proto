"""Statistical analysis for the Phase 1 new-experiment batch.

Implements every preregistered test in
``reports/phase1_newexperiments_preregistration.md`` with numpy/pandas only
(no scipy dependency). Produces:

- ``reports/phase1_newexperiments_runs.csv``  (Experiment A + B rows)
- ``reports/phase1_newexperiments_C_runs.csv`` (Experiment C rows)
- ``reports/phase1_newexperiments_report.md``  (hypothesis decisions)

Usage: ``uv run python -m experiments.analyze_phase1_newexperiments``
"""

from __future__ import annotations

import math
from itertools import combinations, permutations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LONGWINDOW = ROOT / "experiments/phase1_runs/longwindow"
CONTINUATION = ROOT / "experiments/phase1_runs/continuation"
TRACE_WINDOWS = ROOT / "experiments/phase1_runs/metabolic_trace_windows"
CONTROL_DIR = ROOT / "reports/phase1_newexperiments"
REPORTS = ROOT / "reports"

RNG = np.random.default_rng(20260815)
BOOTSTRAP_SAMPLES = 10_000
PERMUTATION_SAMPLES = 2_000


# ---------------------------------------------------------------------------
# Statistics helpers (numpy-only implementations)
# ---------------------------------------------------------------------------


def rankdata(values: np.ndarray) -> np.ndarray:
    """Average ranks with tie correction."""

    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    ranks = np.empty(len(values), dtype=np.float64)
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and sorted_values[j + 1] == sorted_values[i]:
            j += 1
        ranks[order[i : j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return ranks


def spearman(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Spearman rho with a two-sided exact or asymptotic p-value.

    For at most nine observations, enumerate all label permutations. This
    avoids the invalid zero p-value produced by the t approximation for a
    perfect correlation in a tiny sample (for example, |rho|=1 with n=4 has
    exact two-sided p=1/12). Larger samples use the standard t approximation.
    """

    rx, ry = rankdata(x), rankdata(y)
    n = len(x)
    if n < 3:
        return float("nan"), float("nan")
    rx_centered = rx - rx.mean()
    ry_centered = ry - ry.mean()
    denominator = float(np.linalg.norm(rx_centered) * np.linalg.norm(ry_centered))
    if denominator == 0.0:
        return float("nan"), float("nan")
    rho = float(np.dot(rx_centered, ry_centered) / denominator)
    if n <= 9:
        return rho, _exact_spearman_p(rx_centered, ry_centered, denominator, rho)
    if abs(rho) >= 1.0:
        return rho, 0.0
    t = rho * math.sqrt((n - 2) / (1.0 - rho * rho))
    # Two-sided p from the t survival function via the regularized incomplete
    # beta function I_x(a, b) with x = df/(df + t^2).
    df = n - 2
    x_beta = df / (df + t * t)
    p = _betainc_regularized(0.5 * df, 0.5, x_beta)
    return rho, float(p)


def _exact_spearman_p(
    rx_centered: np.ndarray,
    ry_centered: np.ndarray,
    denominator: float,
    observed_rho: float,
) -> float:
    """Return the exact two-sided label-permutation p-value for small samples."""

    threshold = abs(observed_rho) - 1e-12
    extreme = 0
    total = 0
    for permuted in permutations(ry_centered.tolist()):
        permuted_rho = float(np.dot(rx_centered, permuted) / denominator)
        extreme += int(abs(permuted_rho) >= threshold)
        total += 1
    return extreme / total


def format_p_value(p_value: float) -> str:
    """Format a p-value without rounding a nonzero value to ``0.0000``."""

    return f"{p_value:.2e}" if 0.0 < p_value < 0.0001 else f"{p_value:.4f}"


def _log_gamma(z: float) -> float:
    return math.lgamma(z)


def _betainc_regularized(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta via the continued-fraction expansion."""

    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = _log_gamma(a + b) - _log_gamma(a) - _log_gamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    front = math.exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - math.exp(
        _log_gamma(a + b) - _log_gamma(a) - _log_gamma(b) + b * math.log(1.0 - x) + a * math.log(x)
    ) * _betacf(b, a, 1.0 - x) / b


def _betacf(a: float, b: float, x: float, iterations: int = 200, eps: float = 3e-12) -> float:
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1.0 / d
    result = d
    for m in range(1, iterations + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        result *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) < eps:
            break
    return result


def _log_choose(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_exact_2x2(a: int, b: int, c: int, d: int, one_sided: bool = False) -> tuple[float, float]:
    """Exact Fisher test. Returns (odds_ratio, p).

    one_sided=False gives the two-sided p (sum of table probabilities no
    greater than the observed). one_sided=True gives p for OR >= observed.
    """

    row1, row2 = a + b, c + d
    col1, col2 = a + c, b + d
    total = row1 + row2
    observed_p = math.exp(
        _log_choose(col1, a) + _log_choose(col2, b) - _log_choose(total, row1)
    )
    lo = max(0, row1 - col2)
    hi = min(row1, col1)
    if one_sided:
        p_value = 0.0
        for x in range(a, hi + 1):
            p_value += math.exp(
                _log_choose(col1, x) + _log_choose(col2, row1 - x) - _log_choose(total, row1)
            )
    else:
        p_value = 0.0
        for x in range(lo, hi + 1):
            px = math.exp(
                _log_choose(col1, x) + _log_choose(col2, row1 - x) - _log_choose(total, row1)
            )
            if px <= observed_p * (1.0 + 1e-9):
                p_value += px
    if b == 0 or c == 0 or d == 0:
        odds_ratio = float("inf") if a > 0 and d > 0 else (0.0 if a == 0 else float("inf"))
    else:
        odds_ratio = (a * d) / (b * c)
    return odds_ratio, float(min(1.0, p_value))


def mannwhitney_u(x: np.ndarray, y: np.ndarray, alternative: str = "two-sided") -> tuple[float, float]:
    """Exact Mann-Whitney U for small samples, tie-corrected normal otherwise."""

    nx, ny = len(x), len(y)
    all_values = np.concatenate([x, y])
    ranks = rankdata(all_values)
    ranks_x = ranks[:nx]
    ties = pd.Series(all_values).value_counts()
    u1 = float(ranks_x.sum() - nx * (nx + 1) / 2.0)
    u2 = nx * ny - u1
    u_stat = max(u1, u2)
    if (ties > 1).sum() == 0 and nx * ny <= 2_000:
        # Exact enumeration over which ranks are assigned to x.
        count_ge = 0
        total = 0
        for combo in combinations(range(nx + ny), nx):
            su = sum(ranks[i] for i in combo)  # noqa: PERF402
            total += 1
            uc = su - nx * (nx + 1) / 2.0
            if alternative == "greater":
                count_ge += int(uc >= u1 - 1e-9)
            elif alternative == "less":
                count_ge += int(uc <= u1 + 1e-9)
            else:
                count_ge += int(max(uc, nx * ny - uc) >= u_stat - 1e-9)
        p_value = count_ge / total
    else:
        mu = nx * ny / 2.0
        n_total = nx + ny
        sigma_sq = (nx * ny / 12.0) * (
            n_total + 1 - ((ties.to_numpy() ** 3 - ties.to_numpy()).sum() / (n_total * (n_total - 1)))
        )
        sigma = math.sqrt(max(sigma_sq, 1e-12))
        if alternative == "greater":
            z = (u1 - mu) / sigma
        elif alternative == "less":
            z = (u2 - mu) / sigma
        else:
            z = (u_stat - 0.5 - mu) / sigma
        p_value = float(0.5 * math.erfc(z / math.sqrt(2.0)))
    return u_stat, p_value


def bootstrap_ci(values: np.ndarray, statistic=np.mean, samples: int = BOOTSTRAP_SAMPLES) -> tuple[float, float]:
    """Percentile bootstrap CI for a statistic of a 1-D sample."""

    values = np.asarray(values, dtype=np.float64)
    if len(values) == 0:
        return float("nan"), float("nan")
    indices = RNG.integers(0, len(values), size=(samples, len(values)))
    stats = np.sort(np.apply_along_axis(lambda row: statistic(row), 1, values[indices]))
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def block_bootstrap_difference(
    series_a: np.ndarray, series_b: np.ndarray, block: int = 100, samples: int = 2_000
) -> tuple[float, float, float]:
    """Moving-block bootstrap CI for mean(a) - mean(b)."""

    def block_mean(series: np.ndarray) -> np.ndarray:
        n_blocks = len(series) // block
        trimmed = series[: n_blocks * block]
        return trimmed.reshape(n_blocks, block).mean(axis=1)

    a_blocks, b_blocks = block_mean(series_a), block_mean(series_b)
    differences = np.empty(samples)
    for i in range(samples):
        a_resample = a_blocks[RNG.integers(0, len(a_blocks), len(a_blocks))]
        b_resample = b_blocks[RNG.integers(0, len(b_blocks), len(b_blocks))]
        differences[i] = a_resample.mean() - b_resample.mean()
    return float(series_a.mean() - series_b.mean()), float(np.percentile(differences, 2.5)), float(np.percentile(differences, 97.5))


def paired_permutation(observed: np.ndarray, null: np.ndarray, samples: int = PERMUTATION_SAMPLES) -> tuple[float, float, float]:
    """Paired permutation test of mean(observed - null) > 0. Returns (mean_gap, p_one_sided, effect)."""

    gaps = observed - null
    mean_gap = float(gaps.mean())
    count = 0
    for _ in range(samples):
        signs = RNG.choice([-1.0, 1.0], size=len(gaps))
        if (gaps * signs).mean() >= mean_gap - 1e-12:
            count += 1
    return mean_gap, (count + 1) / (samples + 1), float(np.std(gaps, ddof=1))


# ---------------------------------------------------------------------------
# Run-level metric extraction
# ---------------------------------------------------------------------------


def entropy_transition(aggregate: pd.DataFrame, threshold: float = 1.0, sustained: int = 3) -> tuple[bool, int | None, float]:
    """Sustained high-order entropy transition (paper-style criterion)."""

    entropy = aggregate["high_order_entropy"].to_numpy(dtype=float)
    above = entropy >= threshold
    for i in range(len(entropy) - sustained + 1):
        if above[i : i + sustained].all():
            first_epoch = int(aggregate["epoch"].iloc[i])
            return True, first_epoch, float(entropy.max())
    return False, None, float(entropy.max())


def blocked_fraction(writes: pd.DataFrame) -> float:
    attempted = (
        writes["execution_writes_success"]
        + writes["execution_writes_blocked"]
        + writes["mutation_writes_success"]
        + writes["mutation_writes_blocked"]
    ).sum()
    if attempted == 0:
        return 0.0
    blocked = (writes["execution_writes_blocked"] + writes["mutation_writes_blocked"]).sum()
    return float(blocked / attempted)


# ---------------------------------------------------------------------------
# Experiment A + B
# ---------------------------------------------------------------------------


def analyze_a_and_b() -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    # Conserved long-window runs (Experiment A).
    for run_dir in sorted(LONGWINDOW.glob("p1_m*_n4096_s*")):
        manifest = __import__("json").loads((run_dir / "manifest.json").read_text())
        if manifest.get("exit_status") != "success":
            continue
        aggregate = pd.read_csv(run_dir / "aggregate.csv")
        writes = pd.read_csv(run_dir / "writes.csv")
        transition, first_epoch, max_entropy = entropy_transition(aggregate)
        rows.append(
            {
                "experiment": "A",
                "arm": f"m{manifest['config']['pool_multiplier']:g}",
                "seed": manifest["config"]["seed"],
                "epochs": manifest["config"]["epochs"],
                "entropy_transition": transition,
                "first_transition_epoch": first_epoch,
                "max_high_order_entropy": max_entropy,
                "final_high_order_entropy": float(aggregate["high_order_entropy"].iloc[-1]),
                "max_dominant_fraction": float(aggregate["dominant_tape_fraction"].max()),
                "final_dominant_fraction": float(aggregate["dominant_tape_fraction"].iloc[-1]),
                "overall_blocked_fraction": blocked_fraction(writes),
                "wall_time_s": manifest.get("wall_time_s", float("nan")),
                "max_conservation_residual": manifest.get("max_conservation_residual", -1),
                "run_dir": str(run_dir.relative_to(ROOT)),
            }
        )

    # No-conservation control runs (Experiment A).
    for control_csv in sorted(CONTROL_DIR.glob("A_control_n4096_s*.csv")):
        aggregate = pd.read_csv(control_csv)
        transition, first_epoch, max_entropy = entropy_transition(aggregate)
        rows.append(
            {
                "experiment": "A",
                "arm": "control",
                "seed": int(control_csv.stem.split("_s")[-1]),
                "epochs": len(aggregate),
                "entropy_transition": transition,
                "first_transition_epoch": first_epoch,
                "max_high_order_entropy": max_entropy,
                "final_high_order_entropy": float(aggregate["high_order_entropy"].iloc[-1]),
                "max_dominant_fraction": float(aggregate["dominant_tape_fraction"].max()),
                "final_dominant_fraction": float(aggregate["dominant_tape_fraction"].iloc[-1]),
                "overall_blocked_fraction": 0.0,
                "wall_time_s": float("nan"),
                "max_conservation_residual": 0,
                "run_dir": str(control_csv.relative_to(ROOT)),
            }
        )

    # Continuation runs (Experiment B).
    control_csv = CONTROL_DIR / "B_control_continuation.csv"
    if control_csv.exists():
        aggregate = pd.read_csv(control_csv)
        transition, first_epoch, max_entropy = entropy_transition(aggregate)
        rows.append(
            {
                "experiment": "B",
                "arm": "control_continuation",
                "seed": 0,
                "epochs": len(aggregate),
                "entropy_transition": transition,
                "first_transition_epoch": first_epoch,
                "max_high_order_entropy": max_entropy,
                "final_high_order_entropy": float(aggregate["high_order_entropy"].iloc[-1]),
                "max_dominant_fraction": float(aggregate["dominant_tape_fraction"].max()),
                "final_dominant_fraction": float(aggregate["dominant_tape_fraction"].iloc[-1]),
                "overall_blocked_fraction": 0.0,
                "wall_time_s": float("nan"),
                "max_conservation_residual": 0,
                "run_dir": str(control_csv.relative_to(ROOT)),
            }
        )
    for run_dir in sorted(CONTINUATION.glob("p1_m*_n131072_s0*")):
        manifest = __import__("json").loads((run_dir / "manifest.json").read_text())
        if manifest.get("exit_status") != "success":
            continue
        aggregate = pd.read_csv(run_dir / "aggregate.csv")
        writes = pd.read_csv(run_dir / "writes.csv")
        is_continuation = "initial_soup" in manifest["config"]
        transition, first_epoch, max_entropy = entropy_transition(aggregate)
        first_window = writes.head(1000)
        rows.append(
            {
                "experiment": "B",
                "arm": f"m{manifest['config']['pool_multiplier']:g}" + ("_continuation" if is_continuation else "_baseline"),
                "seed": 0,
                "epochs": manifest["config"]["epochs"],
                "entropy_transition": transition,
                "first_transition_epoch": first_epoch,
                "max_high_order_entropy": max_entropy,
                "final_high_order_entropy": float(aggregate["high_order_entropy"].iloc[-1]),
                "max_dominant_fraction": float(aggregate["dominant_tape_fraction"].max()),
                "final_dominant_fraction": float(aggregate["dominant_tape_fraction"].iloc[-1]),
                "overall_blocked_fraction": blocked_fraction(writes),
                "first_1000_blocked_fraction": blocked_fraction(first_window),
                "wall_time_s": manifest.get("wall_time_s", float("nan")),
                "max_conservation_residual": manifest.get("max_conservation_residual", -1),
                "run_dir": str(run_dir.relative_to(ROOT)),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Experiment C
# ---------------------------------------------------------------------------


def window_flow_matrix(edges: pd.DataFrame, window: int, size: int) -> np.ndarray:
    sub = edges[edges["window"] == window]
    matrix = np.zeros((size, size), dtype=np.float64)
    matrix[sub["donor_tape"].to_numpy(), sub["receiver_tape"].to_numpy()] = sub["token_transfers"]
    return matrix


def spearman_matrix_correlation(a: np.ndarray, b: np.ndarray) -> float:
    flat_a, flat_b = a.ravel(), b.ravel()
    if flat_a.std() == 0 or flat_b.std() == 0:
        return float("nan")
    rho, _ = spearman(flat_a, flat_b)
    return rho


def analyze_c() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for run_dir in sorted(TRACE_WINDOWS.glob("trace_m*_n256_s*")):
        config = __import__("json").loads((run_dir / "config.json").read_text())
        manifest = __import__("json").loads((run_dir / "manifest.json").read_text())
        if manifest.get("exit_status") != "success":
            continue
        edges = pd.read_csv(run_dir / "flow_edges_windows.csv")
        n_windows = int(edges["window"].max()) + 1
        size = int(config["population_size"])
        matrices = [window_flow_matrix(edges, w, size) for w in range(n_windows)]
        observed, nulls = [], []
        rng = np.random.default_rng(10_000 + int(config["seed"]))
        for w in range(n_windows - 1):
            observed.append(spearman_matrix_correlation(matrices[w], matrices[w + 1]))
            window_nulls = []
            for _ in range(200):
                permutation = rng.permutation(size)
                permuted = matrices[w + 1][permutation][:, permutation]
                window_nulls.append(spearman_matrix_correlation(matrices[w], permuted))
            nulls.append(float(np.nanmean(window_nulls)))
        observed_mean = float(np.nanmean(observed))
        null_mean = float(np.nanmean(nulls))
        rows.append(
            {
                "pool_multiplier": config["pool_multiplier"],
                "seed": config["seed"],
                "n_windows": n_windows,
                "observed_mean_corr": observed_mean,
                "null_mean_corr": null_mean,
                "gap": observed_mean - null_mean,
                "run_dir": str(run_dir.relative_to(ROOT)),
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Hypothesis decisions
# ---------------------------------------------------------------------------


def decide_hypotheses(runs: pd.DataFrame, c_runs: pd.DataFrame) -> str:
    lines: list[str] = []

    a = runs[runs["experiment"] == "A"]
    if len(a):
        control = a[a["arm"] == "control"]
        m2 = a[a["arm"] == "m2"]
        conserved = a[a["arm"] != "control"]

        control_emergence = int(control["entropy_transition"].sum())
        m2_emergence = int(m2["entropy_transition"].sum())
        lines.append(f"### A1 — control emergence at 4,096 tapes / 100K epochs")
        lines.append(f"Control emergences: **{control_emergence}/{len(control)}**.")
        lines.append(f"Per-seed first-transition epochs: {sorted(x for x in control['first_transition_epoch'].dropna().tolist())}.")
        lines.append("")
        lines.append(f"### A2 — conservation suppresses emergence (Fisher exact, one-sided)")
        _, p_a2 = fisher_exact_2x2(
            control_emergence, len(control) - control_emergence,
            m2_emergence, len(m2) - m2_emergence,
            one_sided=True,
        )
        lines.append(f"m2 emergences: {m2_emergence}/{len(m2)}; control {control_emergence}/{len(control)}; one-sided p = **{p_a2:.4f}**.")
        lines.append("")
        rho_a3, p_a3 = spearman(
            np.array([float(arm[1:]) for arm in conserved["arm"]]),
            conserved["max_high_order_entropy"].to_numpy(),
        )
        lines.append(f"### A3 — scarcity ordering (Spearman, multiplier vs max entropy)")
        lines.append(f"rho = **{rho_a3:.3f}**, p = {format_p_value(p_a3)} (two-sided, n = {len(conserved)}).")
        lines.append("")
        rho_a4, p_a4 = spearman(
            np.array([float(arm[1:]) for arm in conserved["arm"]]),
            conserved["overall_blocked_fraction"].to_numpy(),
        )
        lines.append(f"### A4 — blocked-rate scarcity curve (Spearman)")
        lines.append(f"rho = **{rho_a4:.3f}**, p = {format_p_value(p_a4)} (two-sided, n = {len(conserved)}).")
        lines.append("")

    b = runs[runs["experiment"] == "B"]
    control_row = b[b["arm"] == "control_continuation"]
    m2_cont = b[b["arm"] == "m2_continuation"]
    m16_cont = b[b["arm"] == "m16_continuation"]
    baseline = b[b["arm"] == "m2_baseline"]
    if len(control_row) and len(m2_cont):
        control_final = float(control_row["final_dominant_fraction"].iloc[0])
        control_entropy = float(control_row["final_high_order_entropy"].iloc[0])
        lines.append(f"### B1 — control continuation completes takeover")
        lines.append(f"Control final dominant fraction = **{control_final:.4f}**; final entropy = {control_entropy:.3f} bits/byte.")
        lines.append(f"Decision: {'**supported**' if control_final > 0.5 and control_entropy > 1.0 else '**not supported** (checkpoint not a viable takeover precursor)'}")
        lines.append("")
    if len(m2_cont):
        m2_final = float(m2_cont["final_dominant_fraction"].iloc[0])
        m2_entropy = float(m2_cont["final_high_order_entropy"].iloc[0])
        lines.append(f"### B2 — intermediate conservation disrupts takeover")
        lines.append(f"m2 continuation final dominant fraction = **{m2_final:.4f}**; final entropy = {m2_entropy:.3f} bits/byte (control: {control_entropy:.3f}).")
        disrupted = m2_final < 0.5 and (control_entropy - m2_entropy) >= 0.5
        lines.append(f"Decision: {'**supported**' if disrupted else '**not supported**'}")
        lines.append("")
    if len(m16_cont):
        m16_final = float(m16_cont["final_dominant_fraction"].iloc[0])
        lines.append(f"### B3 — loose conservation is neutral")
        lines.append(f"m16 continuation final dominant fraction = **{m16_final:.4f}** (criterion > 0.5).")
        lines.append(f"Decision: {'**supported**' if m16_final > 0.5 else '**not supported**'}")
        lines.append("")
    if len(m2_cont) and len(baseline):
        continuation_blocked = m2_cont["first_1000_blocked_fraction"]
        baseline_blocked = baseline["first_1000_blocked_fraction"]
        lines.append(f"### B4 — replicator demand concentrates scarcity")
        lines.append(f"Continuation first-1000-epoch blocked fraction = **{float(continuation_blocked.iloc[0]):.4f}**; random-soup baseline = {float(baseline_blocked.iloc[0]):.4f}.")

    if len(c_runs):
        observed_gaps = c_runs["observed_mean_corr"].to_numpy()
        null_gaps = c_runs["null_mean_corr"].to_numpy()
        mean_gap, p_c1, effect = paired_permutation(observed_gaps, null_gaps)
        lines.append(f"### C1 — windowed flow organization vs null")
        lines.append(f"Mean observed corr = {observed_gaps.mean():.4f}; mean null = {null_gaps.mean():.4f}; mean gap = **{mean_gap:.4f}**; one-sided paired permutation p = **{p_c1:.4f}** (n = {len(c_runs)} runs, effect SD = {effect:.4f}).")
        lines.append(f"Decision: {'**flow structure exceeds null** (persistent organization evidence)' if p_c1 < 0.05 else '**not significantly above null** (well-mixed recycling; closes campaign H2 as negative)'}")
        lines.append("")
        rho_c2, p_c2 = spearman(c_runs["pool_multiplier"].to_numpy(), c_runs["gap"].to_numpy())
        lines.append(f"### C2 — scarcity sharpens structure (Spearman, multiplier vs gap)")
        lines.append(f"rho = **{rho_c2:.3f}**, p = {format_p_value(p_c2)} (two-sided, n = {len(c_runs)}).")
    return "\n".join(lines)


def main() -> None:
    runs = analyze_a_and_b()
    runs.to_csv(REPORTS / "phase1_newexperiments_runs.csv", index=False)
    c_runs = analyze_c()
    c_runs.to_csv(REPORTS / "phase1_newexperiments_C_runs.csv", index=False)

    summary = [
        "# Phase 1 new-experiment batch: results",
        "",
        f"Preregistration: `reports/phase1_newexperiments_preregistration.md`.",
        f"Analyzer: `experiments/analyze_phase1_newexperiments.py` (numpy-only stats, seeded RNG 20260815).",
        "",
        "## Verification",
        "",
        f"- Conserved runs with nonzero conservation residual: **{int((runs['max_conservation_residual'] > 0).sum()) if len(runs) else 0}**",
        f"- Conserved runs in A+B: {int(((runs['experiment'].isin(['A', 'B'])) & (runs['arm'] != 'control')).sum()) if len(runs) else 0}",
        "",
        "## Run inventory",
        "",
        runs.to_markdown(index=False) if len(runs) else "(no runs yet)",
        "",
        "## Experiment C inventory",
        "",
        c_runs.to_markdown(index=False) if len(c_runs) else "(no trace runs yet)",
        "",
        "## Hypothesis decisions",
        "",
        decide_hypotheses(runs, c_runs),
    ]
    (REPORTS / "phase1_newexperiments_report.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"wrote reports/phase1_newexperiments_runs.csv ({len(runs)} rows)")
    print(f"wrote reports/phase1_newexperiments_C_runs.csv ({len(c_runs)} rows)")
    print("wrote reports/phase1_newexperiments_report.md")


if __name__ == "__main__":
    main()
