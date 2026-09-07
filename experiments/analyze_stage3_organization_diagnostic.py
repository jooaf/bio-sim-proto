"""Analyze the preregistered Stage 3 empirical organization diagnostic."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run
from analysis.organizations import (
    CompositionReaction,
    Species,
    detect_organizations,
    permute_products,
    recurrence_diagnostics,
)
from experiments.analyze_stage3_energy_liveness import summarize as summarize_energy


WINDOW_SIZE = 1_000
N_WINDOWS = 5
PERMUTATIONS = 199


@dataclass(slots=True)
class WindowData:
    seed: int
    window: int
    reactions: list[CompositionReaction]
    diagnostics: dict[str, float | int]
    identifiable: bool


def _species(value: object) -> Species:
    items = cast(list[object], value)
    result = tuple(int(cast(Any, item)) for item in items)
    if len(result) != 11 or sum(result) != 64:
        raise ValueError("invalid logged BFF composition species")
    return result


def load_windows(run_dir: Path) -> tuple[dict[str, Any], list[WindowData]]:
    """Load deterministic composition-reaction samples and mechanics."""

    mechanics = summarize_energy(run_dir)
    data = load_run(run_dir)
    events = data.table("events")
    selected = events[events["event_type"] == "composition_reaction"]
    by_window: list[list[CompositionReaction]] = [[] for _ in range(N_WINDOWS)]
    for row in selected.itertuples(index=False):
        tick = int(cast(Any, row.tick))
        window = tick // WINDOW_SIZE
        if not 0 <= window < N_WINDOWS:
            continue
        details = json.loads(str(cast(Any, row.details_json)))
        by_window[window].append(
            CompositionReaction(
                reactants=(
                    _species(details["a_before"]),
                    _species(details["b_before"]),
                ),
                products=(
                    _species(details["a_after"]),
                    _species(details["b_after"]),
                ),
            )
        )
    windows: list[WindowData] = []
    for window, reactions in enumerate(by_window):
        diagnostics = recurrence_diagnostics(reactions)
        identifiable = bool(
            int(diagnostics["sampled_reactions"]) >= 100
            and int(diagnostics["changed_reactions"]) >= 10
            and float(diagnostics["recurrent_observation_fraction"]) >= 0.50
            and float(diagnostics["singleton_species_fraction"]) <= 0.80
        )
        windows.append(
            WindowData(
                seed=data.config.run.seed,
                window=window,
                reactions=reactions,
                diagnostics=diagnostics,
                identifiable=identifiable,
            )
        )
    return mechanics, windows


def identifiability_pass(windows: list[WindowData]) -> bool:
    """Apply the frozen campaign-level representation gate."""

    frame = pd.DataFrame(
        [
            {"seed": window.seed, "identifiable": window.identifiable}
            for window in windows
        ]
    )
    by_seed = frame.groupby("seed")["identifiable"].sum()
    return bool(len(windows) == 15 and int(frame["identifiable"].sum()) >= 12 and (by_seed >= 4).all())


def evaluate_windows(
    windows: list[WindowData], *, analysis_seed: int
) -> tuple[pd.DataFrame, np.ndarray[Any, np.dtype[np.float64]] | None]:
    """Evaluate observed and null organizations only after identifiability passes."""

    gate = identifiability_pass(windows)
    rows: list[dict[str, Any]] = []
    null_rows: list[np.ndarray[Any, np.dtype[np.float64]]] = []
    for window in windows:
        row: dict[str, Any] = {
            "seed": window.seed,
            "window": window.window,
            "start_tick": window.window * WINDOW_SIZE,
            "end_tick": (window.window + 1) * WINDOW_SIZE - 1,
            **window.diagnostics,
            "identifiable": window.identifiable,
            "candidate_components": np.nan,
            "accepted_organizations": np.nan,
            "null_mean": np.nan,
            "null_p95": np.nan,
            "window_p": np.nan,
        }
        if gate and window.identifiable:
            candidates = detect_organizations(window.reactions)
            accepted = sum(candidate.self_maintaining for candidate in candidates)
            rng = np.random.default_rng(
                analysis_seed + window.seed + window.window
            )
            null = np.asarray(
                [
                    sum(
                        candidate.self_maintaining
                        for candidate in detect_organizations(
                            permute_products(window.reactions, rng)
                        )
                    )
                    for _ in range(PERMUTATIONS)
                ],
                dtype=np.float64,
            )
            row.update(
                {
                    "candidate_components": len(candidates),
                    "accepted_organizations": accepted,
                    "null_mean": float(null.mean()),
                    "null_p95": float(np.quantile(null, 0.95)),
                    "window_p": float(
                        (1 + np.count_nonzero(null >= accepted))
                        / (PERMUTATIONS + 1)
                    ),
                }
            )
            null_rows.append(null)
        rows.append(row)
    campaign_null = (
        np.mean(np.stack(null_rows), axis=0) if gate and null_rows else None
    )
    return pd.DataFrame(rows), campaign_null


def campaign_decision(
    mechanics: pd.DataFrame,
    windows: pd.DataFrame,
    campaign_null: np.ndarray[Any, np.dtype[np.float64]] | None,
) -> tuple[bool, bool, float, float, float]:
    """Return identifiability, organization support, observed mean, p95, and p."""

    identifiable = bool(
        int(windows["identifiable"].sum()) >= 12
        and (windows.groupby("seed")["identifiable"].sum() >= 4).all()
    )
    if not identifiable or campaign_null is None:
        return identifiable, False, float("nan"), float("nan"), float("nan")
    eligible = windows[windows["identifiable"]]
    observed = float(eligible["accepted_organizations"].mean())
    p95 = float(np.quantile(campaign_null, 0.95))
    p_value = float(
        (1 + np.count_nonzero(campaign_null >= observed))
        / (len(campaign_null) + 1)
    )
    mechanics_clean = bool(
        len(mechanics) == 3
        and mechanics["successful_exit"].all()
        and mechanics["conserved"].all()
        and int(mechanics["invariant_failures"].sum()) == 0
        and (mechanics["max_relative_energy_error"] <= 1e-9).all()
    )
    supported = bool(
        mechanics_clean
        and int((eligible["accepted_organizations"] > 0).sum()) >= 8
        and observed > p95
        and p_value <= 0.05
    )
    return identifiable, supported, observed, p95, p_value


def write_report(
    mechanics: pd.DataFrame,
    windows: pd.DataFrame,
    campaign_null: np.ndarray[Any, np.dtype[np.float64]] | None,
    target: Path,
) -> None:
    """Write the frozen identifiability-first decision."""

    identifiable, supported, observed, p95, p_value = campaign_decision(
        mechanics, windows, campaign_null
    )
    lines = [
        "# Stage 3 empirical organization diagnostic",
        "",
        "## Decisions",
        "",
        f"- Composition-reaction representation identifiable: **{identifiable}**",
        f"- Empirical organization excess supported: **{supported}**",
        "",
        f"- Identifiable windows: {int(windows['identifiable'].sum())}/{len(windows)}",
    ]
    if identifiable:
        eligible = windows[windows["identifiable"]]
        lines += [
            f"- Mean accepted candidates: {observed:.6f}",
            f"- Null 95th percentile: {p95:.6f}",
            f"- Campaign Monte Carlo p: {p_value:.6f}",
            f"- Windows with accepted candidates: {int((eligible['accepted_organizations'] > 0).sum())}/{len(eligible)}",
        ]
    else:
        lines.append("- Organization inference skipped by the frozen stopping rule.")
    lines += [
        "",
        "| seed | window | samples | changed | species | unique fraction | singleton fraction | recurrent observations | identifiable | candidates | accepted | null mean | window p |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---:|---:|---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], windows.to_dict(orient="records")):
        lines.append(
            f"| {int(row['seed'])} | {int(row['window'])} | {int(row['sampled_reactions'])} | "
            f"{int(row['changed_reactions'])} | {int(row['species'])} | "
            f"{float(row['unique_species_fraction']):.3f} | {float(row['singleton_species_fraction']):.3f} | "
            f"{float(row['recurrent_observation_fraction']):.3f} | {bool(row['identifiable'])} | "
            f"{row['candidate_components']} | {row['accepted_organizations']} | {row['null_mean']} | {row['window_p']} |"
        )
    lines += [
        "",
        "Empirical composition organizations are representation- and window-dependent. Even a positive result would require intervention before a self-maintenance or organism claim.",
        "",
        "## Integrity",
        "",
        f"- Successful runs: {int(mechanics['successful_exit'].sum())}/{len(mechanics)}",
        f"- Matter-conserved runs: {int(mechanics['conserved'].sum())}/{len(mechanics)}",
        f"- Invariant failures: {int(mechanics['invariant_failures'].sum())}",
        f"- Maximum relative energy error: {float(mechanics['max_relative_energy_error'].max()):.3e}",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--analysis-seed", type=int, default=20260917)
    parser.add_argument("--windows-output", type=Path, default=Path("reports/stage3_organization_windows.csv"))
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage3_organization_runs.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage3_organization_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    if len(index) != 3 or index["seed"].nunique() != 3:
        raise ValueError("organization diagnostic requires three complete seeds")
    mechanics_rows: list[dict[str, Any]] = []
    all_windows: list[WindowData] = []
    for row in cast(list[dict[str, Any]], index.to_dict(orient="records")):
        mechanics, windows = load_windows(Path(str(row["run_dir"])))
        mechanics_rows.append(mechanics)
        all_windows.extend(windows)
    mechanics_frame = pd.DataFrame(mechanics_rows).sort_values("seed", ignore_index=True)
    windows_frame, campaign_null = evaluate_windows(
        all_windows, analysis_seed=args.analysis_seed
    )
    windows_frame = windows_frame.sort_values(["seed", "window"], ignore_index=True)
    args.windows_output.parent.mkdir(parents=True, exist_ok=True)
    windows_frame.to_csv(args.windows_output, index=False)
    mechanics_frame.to_csv(args.runs_output, index=False)
    write_report(mechanics_frame, windows_frame, campaign_null, args.report)
    print(args.windows_output)
    print(args.runs_output)
    print(args.report)


if __name__ == "__main__":
    main()
