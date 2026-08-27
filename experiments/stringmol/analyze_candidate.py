"""Analyze the preregistered unseen-seed Stringmol R host-dependence matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

import pandas as pd


def load_rows(index_path: Path) -> pd.DataFrame:
    """Load compact successful-run manifests without parsing legacy bulk output."""

    index = json.loads(index_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for run_dir_text in index["run_dirs"]:
        run_dir = Path(run_dir_text)
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        control = cast(dict[str, Any], manifest["control"])
        summary = cast(dict[str, Any], manifest["summary"])
        rows.append(
            {
                "run_dir": str(run_dir),
                "seed": int(control["seed"]),
                "condition": str(control["condition"]),
                "exit_status": str(manifest["exit_status"]),
                "source_commit": str(manifest["source_lock"]["commit"]),
                "reproducible_loader_warning": bool(summary["reproducible_loader_warning"]),
                **summary,
            }
        )
    return pd.DataFrame(rows).sort_values(["seed", "condition"], ignore_index=True)


def paired_results(rows: pd.DataFrame) -> pd.DataFrame:
    """Create one row per seed with the frozen host-dependence decisions."""

    records: list[dict[str, Any]] = []
    for seed, group in rows.groupby("seed", sort=True):
        group_records = cast(list[dict[str, Any]], group.to_dict(orient="records"))
        by_condition = {str(row["condition"]): row for row in group_records}
        if set(by_condition) != {"host-only", "parasite-only", "mixed"}:
            raise ValueError(f"seed {seed} lacks one or more candidate conditions")
        host = by_condition["host-only"]
        alone = by_condition["parasite-only"]
        mixed = by_condition["mixed"]
        difference = int(mixed["maximum_parasite_count"]) - int(
            alone["maximum_parasite_count"]
        )
        records.append(
            {
                "seed": int(cast(Any, seed)),
                "host_final": int(host["final_host_count"]),
                "alone_initial_r": int(alone["initial_parasite_count"]),
                "alone_max_r": int(alone["maximum_parasite_count"]),
                "alone_final_r": int(alone["final_parasite_count"]),
                "mixed_initial_r": int(mixed["initial_parasite_count"]),
                "mixed_max_r": int(mixed["maximum_parasite_count"]),
                "mixed_final_r": int(mixed["final_parasite_count"]),
                "mixed_max_r_fraction": float(mixed["maximum_parasite_fraction"]),
                "mixed_minus_alone_max": difference,
                "mixed_increased": int(mixed["maximum_parasite_count"]) > 10,
                "alone_did_not_increase": int(alone["maximum_parasite_count"]) <= 10,
                "paired_advantage_positive": difference > 0,
                "host_persisted": int(host["final_host_count"]) > 0,
            }
        )
    return pd.DataFrame(records)


def write_report(rows: pd.DataFrame, paired: pd.DataFrame, target: Path) -> None:
    """Apply all frozen 8/10 host-dependence criteria."""

    mixed_increased = int(paired["mixed_increased"].sum())
    alone_control = int(paired["alone_did_not_increase"].sum())
    paired_positive = int(paired["paired_advantage_positive"].sum())
    host_persisted = int(paired["host_persisted"].sum())
    provenance_ok = bool(
        (rows["exit_status"] == "success").all()
        and not rows["reproducible_loader_warning"].any()
        and rows["source_commit"].nunique() == 1
    )
    passed = bool(
        mixed_increased >= 8
        and alone_control >= 8
        and paired_positive >= 8
        and host_persisted >= 8
        and provenance_ok
    )
    lines = [
        "# Phase 2 Stringmol R host-dependence validation",
        "",
        "## Decision",
        "",
        f"Candidate R host-dependence validation pass: **{passed}**.",
        "",
        f"- Mixed R increased: {mixed_increased}/{len(paired)} seeds",
        f"- R-alone did not increase: {alone_control}/{len(paired)} seeds",
        f"- Mixed-minus-alone maximum was positive: {paired_positive}/{len(paired)} seeds",
        f"- Host-only population persisted: {host_persisted}/{len(paired)} seeds",
        f"- Pinned provenance and explicit loader checks passed: **{provenance_ok}**",
        "",
        "Passing this screen permits a separate ten-seed global positive-control preregistration. It is not a locality/containment result.",
        "",
        "## Seed results",
        "",
        "| seed | host final | R-alone max | mixed R max | mixed R final | mixed max fraction | mixed−alone max |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    records = cast(list[dict[str, Any]], paired.to_dict(orient="records"))
    for row in records:
        lines.append(
            f"| {int(row['seed'])} | {int(row['host_final'])} | "
            f"{int(row['alone_max_r'])} | {int(row['mixed_max_r'])} | "
            f"{int(row['mixed_final_r'])} | {float(row['mixed_max_r_fraction']):.3f} | "
            f"{int(row['mixed_minus_alone_max'])} |"
        )
    lines += [
        "",
        "## Scope",
        "",
        "R was selected from one disclosed exploratory seed before this unseen-seed matrix. B and S were not reconsidered. Exact sequence abundance is the primary outcome; mutated descendants are not folded into R.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--runs-output", type=Path, required=True)
    parser.add_argument("--paired-output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    rows = load_rows(args.index)
    paired = paired_results(rows)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(args.runs_output, index=False)
    paired.to_csv(args.paired_output, index=False)
    write_report(rows, paired, args.report)
    print(args.runs_output)
    print(args.paired_output)
    print(args.report)


if __name__ == "__main__":
    main()
