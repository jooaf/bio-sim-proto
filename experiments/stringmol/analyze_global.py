"""Analyze the preregistered Stringmol global parasite positive control."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import pandas as pd

from experiments.stringmol.ancestry import ancestry_trajectory


def latest_species_path(run_dir: Path) -> Path:
    """Return the numerically latest upstream species-parentage snapshot."""

    paths = list(run_dir.glob("splist*.dat"))
    if not paths:
        raise FileNotFoundError(f"no Stringmol species logs in {run_dir}")
    return max(paths, key=lambda path: int(path.stem.removeprefix("splist")))


def summarize_run(run_dir: Path) -> tuple[dict[str, Any], pd.DataFrame]:
    """Return exact-R and passive-ancestry outcomes for one global run."""

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    control = cast(dict[str, Any], manifest["control"])
    summary = cast(dict[str, Any], manifest["summary"])
    trajectory = ancestry_trajectory(
        run_dir / "popdy001.dat",
        latest_species_path(run_dir),
        founder_species=2,
        parent_role="passive",
    )
    final = trajectory.iloc[-1]
    row = {
        "run_dir": str(run_dir),
        "seed": int(control["seed"]),
        "exit_status": str(manifest["exit_status"]),
        "source_commit": str(manifest["source_lock"]["commit"]),
        "reproducible_loader_warning": bool(summary["reproducible_loader_warning"]),
        "initial_total": int(summary["initial_total"]),
        "final_total": int(summary["final_total"]),
        "initial_exact_r": int(summary["initial_parasite_count"]),
        "max_exact_r": int(summary["maximum_parasite_count"]),
        "final_exact_r": int(summary["final_parasite_count"]),
        "max_exact_r_fraction": float(summary["maximum_parasite_fraction"]),
        "final_exact_r_fraction": float(summary["final_parasite_fraction"]),
        "max_ancestry_fraction": float(trajectory["ancestry_fraction"].max()),
        "final_ancestry_fraction": float(final["ancestry_fraction"]),
        "final_ancestry_count": int(final["ancestry_count"]),
        "family_species_count": int(final["family_species_count"]),
        "reached_90pct": bool((trajectory["ancestry_fraction"] >= 0.9).any()),
        "exact_r_increased": int(summary["maximum_parasite_count"]) > 10,
        "population_persisted": int(summary["final_total"]) > 0,
    }
    tagged = trajectory.copy()
    tagged.insert(0, "seed", int(control["seed"]))
    tagged.insert(1, "run_dir", str(run_dir))
    return row, tagged


def write_report(runs: pd.DataFrame, target: Path) -> None:
    """Apply the frozen 8/10 positive-control rule."""

    reached = int(runs["reached_90pct"].sum())
    exact_increased = int(runs["exact_r_increased"].sum())
    persisted = int(runs["population_persisted"].sum())
    provenance_ok = bool(
        (runs["exit_status"] == "success").all()
        and not runs["reproducible_loader_warning"].any()
        and runs["source_commit"].nunique() == 1
    )
    passed = bool(
        reached >= 8
        and exact_increased >= 8
        and persisted >= 8
        and provenance_ok
    )
    lines = [
        "# Phase 2 Stringmol global parasite positive control",
        "",
        "## Decision",
        "",
        f"Global positive control pass: **{passed}**.",
        "",
        f"- Passive-parent ancestry reached 90%: {reached}/{len(runs)} seeds",
        f"- Exact R exceeded inoculum: {exact_increased}/{len(runs)} seeds",
        f"- Population persisted: {persisted}/{len(runs)} seeds",
        f"- Pinned provenance and loader checks passed: **{provenance_ok}**",
        "",
        (
            "The matched local treatment may now be preregistered and launched."
            if passed
            else "The local treatment remains blocked; failed global runs cannot be called containment."
        ),
        "",
        "## Seed results",
        "",
        "| seed | max exact R | final exact R | max ancestry fraction | final ancestry fraction | family species | reached 90% |",
        "|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    records = cast(list[dict[str, Any]], runs.to_dict(orient="records"))
    for row in records:
        lines.append(
            f"| {int(row['seed'])} | {int(row['max_exact_r'])} | "
            f"{int(row['final_exact_r'])} | {float(row['max_ancestry_fraction']):.3f} | "
            f"{float(row['final_ancestry_fraction']):.3f} | "
            f"{int(row['family_species_count'])} | {bool(row['reached_90pct'])} |"
        )
    lines += [
        "",
        "Passive-parent ancestry follows Stringmol's inherited passive label. Exact R remains separately reported. This external control does not establish BFF parasite viability.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, required=True)
    parser.add_argument("--trajectory-output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    outputs = [summarize_run(Path(path)) for path in index["run_dirs"]]
    runs = pd.DataFrame([row for row, _ in outputs]).sort_values("seed", ignore_index=True)
    trajectories = pd.concat([trajectory for _, trajectory in outputs], ignore_index=True)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    runs.to_csv(args.runs_output, index=False)
    trajectories.to_csv(args.trajectory_output, index=False)
    write_report(runs, args.report)
    print(args.runs_output)
    print(args.trajectory_output)
    print(args.report)


if __name__ == "__main__":
    main()
