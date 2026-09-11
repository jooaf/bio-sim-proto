"""Analyze the preregistered Stage 4 structured-influx mechanics campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from analysis.load import load_run
from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater


SEEDS = set(range(202609230, 202609235))
PATCH_LENGTHS = {0.5, 2.0, 8.0}
WIDTH = 16
HEIGHT = 16


def coefficient_of_variation(values: np.ndarray[Any, np.dtype[np.float64]]) -> float:
    mean = float(values.mean())
    return 0.0 if mean == 0.0 else float(values.std() / mean)


def moran_i(
    values: np.ndarray[Any, np.dtype[np.float64]],
    mask: np.ndarray[Any, np.dtype[np.bool_]] | None = None,
) -> float:
    """Calculate toroidal four-neighbor Moran's I over selected cells."""

    grid = np.asarray(values, dtype=np.float64).reshape(HEIGHT, WIDTH)
    selected = np.ones((HEIGHT, WIDTH), dtype=bool) if mask is None else mask.reshape(HEIGHT, WIDTH)
    node_values = grid[selected]
    centered = grid - float(node_values.mean())
    denominator = float(np.square(centered[selected]).sum())
    if denominator == 0.0:
        return 0.0
    numerator = 0.0
    edges = 0
    for y, x in np.argwhere(selected):
        for neighbor_y, neighbor_x in (
            ((y - 1) % HEIGHT, x),
            ((y + 1) % HEIGHT, x),
            (y, (x - 1) % WIDTH),
            (y, (x + 1) % WIDTH),
        ):
            if selected[neighbor_y, neighbor_x]:
                numerator += centered[y, x] * centered[neighbor_y, neighbor_x]
                edges += 1
    if edges == 0:
        return 0.0
    return float(len(node_values) * numerator / (edges * denominator))


def summarize(run_dir: Path) -> dict[str, Any]:
    data = load_run(run_dir)
    ticks = data.table("ticks").sort_values("tick", ignore_index=True)
    tapes = data.table("tapes")
    events = data.table("events")
    profile_frame = pd.read_parquet(run_dir / "influx_profile.parquet").sort_values("flat_index")
    profile = profile_frame["weight"].to_numpy(dtype=np.float64)
    cumulative_uptake = np.zeros(WIDTH * HEIGHT, dtype=np.float64)
    uptake_executions = 0
    gross_uptake = 0.0
    for value in events.loc[events["event_type"] == "energy_uptake", "details_json"]:
        details = json.loads(str(value))
        uptake_executions += int(details["executions"])
        gross_uptake += float(details["energy_absorbed"])
        for cell in details["by_cell"]:
            x, y = (int(coordinate) for coordinate in cell["cell"])
            cumulative_uptake[y * WIDTH + x] += float(cell["energy_absorbed"])
    final_snapshot_tick = int(cast(Any, tapes["tick"].max()))
    final_tapes = tapes[tapes["tick"] == final_snapshot_tick]
    occupied = np.zeros(WIDTH * HEIGHT, dtype=bool)
    tape_energy = np.zeros(WIDTH * HEIGHT, dtype=np.float64)
    for row in final_tapes.itertuples(index=False):
        index = int(cast(Any, row.cell_y)) * WIDTH + int(cast(Any, row.cell_x))
        occupied[index] = True
        tape_energy[index] = float(cast(Any, row.energy))
    expected = ticks["energy_influx_cum"].to_numpy(dtype=np.float64)
    accounted = (
        ticks["energy_field_total"].to_numpy(dtype=np.float64)
        + ticks["energy_tape_total"].to_numpy(dtype=np.float64)
        + ticks["energy_dissipated_cum"].to_numpy(dtype=np.float64)
    )
    relative_error = np.abs(accounted - expected) / np.maximum(1.0, np.abs(expected))
    invariant_path = run_dir / "invariant_log.jsonl"
    protocol = json.loads((run_dir / "structured_field_protocol.json").read_text(encoding="utf-8"))
    return {
        "run_dir": str(run_dir),
        "seed": data.config.run.seed,
        "field_spec": protocol["field_spec"],
        "correlation_length": protocol["correlation_length"],
        "successful_exit": data.manifest.get("exit_status") == "success",
        "invariant_failures": sum(bool(line) for line in invariant_path.read_text(encoding="utf-8").splitlines()),
        "final_tapes": len(final_tapes),
        "unchanged_tape_type": bool(tapes["content_hash"].nunique() == 1),
        "active_ticks": int((ticks["n_interactions"] > 0).sum()),
        "uptake_executions": uptake_executions,
        "gross_uptake": gross_uptake,
        "uptake_moran": moran_i(cumulative_uptake, occupied),
        "uptake_cv": coefficient_of_variation(cumulative_uptake[occupied]),
        "tape_energy_moran": moran_i(tape_energy, occupied),
        "profile_moran": moran_i(profile),
        "profile_cv": coefficient_of_variation(profile),
        "profile_min": float(profile.min()),
        "profile_sum": float(profile.sum()),
        "max_relative_energy_error": float(relative_error.max()),
    }


def paired_effects(runs: pd.DataFrame) -> pd.DataFrame:
    uniform = runs[runs["field_spec"] == "uniform"].set_index("seed")
    patches = runs[runs["field_spec"] == "patches"]
    patch_means = patches.groupby("seed").agg(
        patch_uptake_moran=("uptake_moran", "mean"),
        patch_uptake_cv=("uptake_cv", "mean"),
        patch_tape_energy_moran=("tape_energy_moran", "mean"),
    )
    effects = patch_means.join(
        uniform[["uptake_moran", "uptake_cv", "tape_energy_moran"]].add_prefix("uniform_")
    )
    effects["uptake_moran_effect"] = effects["patch_uptake_moran"] - effects["uniform_uptake_moran"]
    effects["uptake_cv_effect"] = effects["patch_uptake_cv"] - effects["uniform_uptake_cv"]
    effects["tape_energy_moran_effect"] = effects["patch_tape_energy_moran"] - effects["uniform_tape_energy_moran"]
    return effects.reset_index()


def primary_p(effects: pd.DataFrame) -> float:
    return exact_paired_sign_flip_greater(effects["uptake_moran_effect"].to_numpy(dtype=np.float64))


def passes_gate(runs: pd.DataFrame, effects: pd.DataFrame) -> bool:
    patches = runs[runs["field_spec"] == "patches"]
    uniform_median = float(runs.loc[runs["field_spec"] == "uniform", "uptake_moran"].median())
    length_medians = patches.groupby("correlation_length")["uptake_moran"].median()
    profiles_valid = bool(
        np.isfinite(patches[["profile_moran", "profile_cv", "profile_min", "profile_sum"]].to_numpy()).all()
        and (patches["profile_min"] > 0.0).all()
        and ((patches["profile_sum"] - WIDTH * HEIGHT).abs() <= 1e-12).all()
        and (patches["profile_moran"] > 0.0).all()
        and (patches["profile_cv"] > 0.0).all()
    )
    return bool(
        (effects["uptake_moran_effect"] > 0.0).all()
        and primary_p(effects) <= 0.05
        and int((length_medians > uniform_median).sum()) >= 2
        and (effects["uptake_cv_effect"] > 0.0).all()
        and int((effects["tape_energy_moran_effect"] > 0.0).sum()) >= 4
        and profiles_valid
        and len(runs) == 20
        and runs["successful_exit"].all()
        and (runs["final_tapes"] == 128).all()
        and (runs["active_ticks"] == 1000).all()
        and (runs["gross_uptake"] > 0.0).all()
        and runs["unchanged_tape_type"].all()
        and int(runs["invariant_failures"].sum()) == 0
        and (runs["max_relative_energy_error"] <= 1e-9).all()
    )


def write_report(runs: pd.DataFrame, effects: pd.DataFrame, target: Path) -> None:
    groups = (
        runs.groupby(["field_spec", "correlation_length"], dropna=False, sort=True)
        .agg(
            runs=("seed", "size"),
            uptake_moran=("uptake_moran", "median"),
            uptake_cv=("uptake_cv", "median"),
            tape_energy_moran=("tape_energy_moran", "median"),
            profile_moran=("profile_moran", "median"),
            gross_uptake=("gross_uptake", "median"),
            max_error=("max_relative_energy_error", "max"),
        )
        .reset_index()
    )
    lines = [
        "# Stage 4 structured energy-field scale",
        "",
        "## Decision",
        "",
        f"Structured local energy niches supported: **{passes_gate(runs, effects)}**.",
        "",
        f"- Mean-patch uptake Moran effect positive: {int((effects['uptake_moran_effect'] > 0).sum())}/5",
        f"- Exact one-sided sign p: {primary_p(effects):.6f}",
        f"- Mean-patch uptake-CV effect positive: {int((effects['uptake_cv_effect'] > 0).sum())}/5",
        f"- Mean-patch tape-energy Moran effect positive: {int((effects['tape_energy_moran_effect'] > 0).sum())}/5",
        "",
        "| field | length | runs | uptake Moran | uptake CV | tape-energy Moran | profile Moran | gross uptake | max error |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cast(list[dict[str, Any]], groups.to_dict(orient="records")):
        length = "—" if pd.isna(row["correlation_length"]) else f"{float(row['correlation_length']):g}"
        lines.append(
            f"| {row['field_spec']} | {length} | {int(row['runs'])} | {float(row['uptake_moran']):.6f} | "
            f"{float(row['uptake_cv']):.6f} | {float(row['tape_energy_moran']):.6f} | "
            f"{float(row['profile_moran']):.6f} | {float(row['gross_uptake']):.3f} | {float(row['max_error']):.3e} |"
        )
    lines += [
        "",
        "No correlation length was selected by this campaign. Lineage, reproduction, mortality, organization, and fitness were not analyzed.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, default=Path("reports/stage4_structured_field_runs.csv"))
    parser.add_argument("--effects-output", type=Path, default=Path("reports/stage4_structured_field_effects.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage4_structured_field_report.md"))
    args = parser.parse_args()
    index = pd.read_parquet(args.index)
    if len(index) != 20 or set(index["seed"].astype(int)) != SEEDS:
        raise ValueError("structured field campaign requires four complete five-seed cells")
    runs = pd.DataFrame(
        [summarize(Path(str(row["run_dir"]))) for row in cast(list[dict[str, Any]], index.to_dict(orient="records"))]
    ).sort_values(["field_spec", "correlation_length", "seed"], ignore_index=True)
    if len(runs[runs["field_spec"] == "uniform"]) != 5 or set(runs.loc[runs["field_spec"] == "patches", "correlation_length"].astype(float)) != PATCH_LENGTHS:
        raise ValueError("structured field campaign has an unexpected treatment matrix")
    effects = paired_effects(runs)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    effects.to_csv(args.effects_output, index=False)
    write_report(runs, effects, args.report)
    print(args.runs_output)
    print(args.effects_output)
    print(args.report)


if __name__ == "__main__":
    main()
