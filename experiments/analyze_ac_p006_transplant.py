"""Analyze the frozen AC-P006 composition-preserving transplantation campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PAIRS = 10


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def exact_sign_probability(favored: int, opposite: int) -> float:
    discordant = favored + opposite
    if discordant == 0:
        return 1.0
    return float(sum(math.comb(discordant, k) for k in range(favored, discordant + 1)) / 2**discordant)


def analyze(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    preparation = json.loads((root / "preparation.json").read_text())
    if preparation.get("campaign") != "AC-P006" or len(preparation.get("pairs", [])) != PAIRS:
        raise ValueError("invalid preparation manifest")
    rows: list[dict[str, Any]] = []
    for manifest_path in sorted((root / "runs").glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        config = manifest["config"]
        initial_name = Path(config["initial_soup"]).name
        parsed = initial_name.removeprefix("pair_").removesuffix(".npy").split("_")
        if len(parsed) != 2:
            raise ValueError(f"invalid initial soup name: {initial_name}")
        pair, arm = int(parsed[0]), parsed[1]
        if pair not in range(PAIRS) or arm not in {"witness", "shuffle"}:
            raise ValueError("unexpected pair/arm")
        run_dir = manifest_path.parent
        checksums = manifest.get("artifact_checksums", {})
        if manifest.get("exit_status") != "success" or manifest.get("max_conservation_residual") != 0:
            raise ValueError(f"failed run: {run_dir}")
        for relative, expected in checksums.items():
            if sha256(run_dir / relative) != expected:
                raise ValueError(f"checksum mismatch: {run_dir}/{relative}")
        pair_info = preparation["pairs"][pair]
        arm_info = pair_info["arms"][arm]
        initial_path = Path(config["initial_soup"])
        if sha256(initial_path) != arm_info["sha256"] or config["initial_soup_sha256"] != arm_info["sha256"]:
            raise ValueError("initial soup checksum mismatch")
        tracker = pd.read_csv(run_dir / "tracked_tape.csv")
        aggregate = pd.read_csv(run_dir / "aggregate.csv")
        expected_epochs = [0] + sorted(set(range(1, 10_001, 100)) | {10_000})
        if tracker["epoch"].tolist() != expected_epochs:
            raise ValueError("tracker callback schedule mismatch")
        if not np.array_equal(tracker.iloc[1:]["exact_target_count"], aggregate["exact_target_count"]):
            raise ValueError("tracker/aggregate mismatch")
        initial = int(tracker.iloc[0]["exact_target_count"])
        if initial != arm_info["initial_exact_target_count"] or initial < 32:
            raise ValueError("initial target count mismatch")
        post = tracker[tracker["epoch"] >= 1001]["exact_target_count"].to_numpy(dtype=float)
        mean_fold = float(post.mean() / initial)
        maximum = int(tracker["exact_target_count"].max())
        final = int(tracker.iloc[-1]["exact_target_count"])
        established = maximum >= 64 and final >= 16
        above = tracker.loc[tracker["exact_target_count"] > initial, "epoch"]
        rows.append({
            "pair": pair, "arm": arm, "source_seed": pair_info["source_seed"],
            "recipient_seed": pair_info["recipient_seed"], "initial_count": initial,
            "max_count": maximum, "final_count": final, "mean_fold_abundance": mean_fold,
            "established": established, "first_above_initial_epoch": int(above.iloc[0]) if len(above) else None,
            "max_conservation_residual": 0, "run_dir": str(run_dir),
        })
    runs = pd.DataFrame(rows).sort_values(["pair", "arm"], ignore_index=True)
    if len(runs) != 20 or runs.groupby(["pair", "arm"]).size().ne(1).any():
        raise ValueError("incomplete treatment matrix")
    witness = runs[runs.arm == "witness"].set_index("pair")
    shuffle = runs[runs.arm == "shuffle"].set_index("pair")
    pairs = pd.DataFrame({
        "pair": range(PAIRS),
        "witness_mean_fold": witness["mean_fold_abundance"],
        "shuffle_mean_fold": shuffle["mean_fold_abundance"],
        "witness_max": witness["max_count"], "shuffle_max": shuffle["max_count"],
        "witness_final": witness["final_count"], "shuffle_final": shuffle["final_count"],
        "witness_established": witness["established"], "shuffle_established": shuffle["established"],
    }).reset_index(drop=True)
    pairs["favored"] = pairs.witness_mean_fold > pairs.shuffle_mean_fold
    pairs["opposite"] = pairs.witness_mean_fold < pairs.shuffle_mean_fold
    pairs["fold_ratio"] = (pairs.witness_mean_fold + 1e-12) / (pairs.shuffle_mean_fold + 1e-12)
    favored, opposite = int(pairs.favored.sum()), int(pairs.opposite.sum())
    probability = exact_sign_probability(favored, opposite)
    witness_established = int(pairs.witness_established.sum())
    shuffle_established = int(pairs.shuffle_established.sum())
    median_ratio = float(pairs.fold_ratio.median())
    gates = {
        "integrity": True,
        "witness_positive_control": witness_established >= 5,
        "shuffle_control": shuffle_established <= 2,
        "paired_direction": favored >= 9 and probability <= 0.05,
        "median_fold_ratio": median_ratio >= 2,
    }
    result = {
        "decision": "PASS" if all(gates.values()) else "VALID NON-PASS",
        "gates": gates, "witness_established": witness_established,
        "shuffle_established": shuffle_established, "favored_pairs": favored,
        "opposite_pairs": opposite, "tied_pairs": PAIRS - favored - opposite,
        "exact_sign_probability": probability, "median_fold_ratio": median_ratio,
    }
    return runs, pairs, result


def write_outputs(runs: pd.DataFrame, pairs: pd.DataFrame, result: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    runs.to_csv(output / "runs.csv", index=False)
    pairs.to_csv(output / "pairs.csv", index=False)
    (output / "decision.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    lines = ["# AC-P006 composition-preserving transplantation", "", f"**{result['decision']}**", "",
             f"- Witness established: {result['witness_established']}/10",
             f"- Shuffle established: {result['shuffle_established']}/10",
             f"- Post-transient favored/opposite/tied: {result['favored_pairs']}/{result['opposite_pairs']}/{result['tied_pairs']}",
             f"- Exact one-sided sign probability: {result['exact_sign_probability']:.8g}",
             f"- Median post-transient fold ratio: {result['median_fold_ratio']:.8g}", ""]
    lines += [f"- {gate}: {'PASS' if passed else 'FAIL'}" for gate, passed in result["gates"].items()]
    lines += ["", "Secondary transient maximum abundance cannot rescue failed persistence and post-transient gates.",
              "No organism, adaptation, ecology, organization, or open-ended heredity claim follows.", ""]
    (output / "report.md").write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs_root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    runs, pairs, result = analyze(args.runs_root)
    write_outputs(runs, pairs, result, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
