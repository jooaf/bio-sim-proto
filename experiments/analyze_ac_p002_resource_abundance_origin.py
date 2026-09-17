"""Analyze the preregistered AC-P002 paired resource-abundance confirmation."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from experiments.analyze_ac_p001_high_resource_origin_viability import summarize

SEEDS = set(range(202613000, 202613020))
ARMS = {"m2": 2, "m16": 16}


def exact_one_sided(favored_only: int, opposite_only: int) -> float:
    discordant = favored_only + opposite_only
    if discordant == 0:
        return 1.0
    return float(
        sum(math.comb(discordant, value) for value in range(favored_only, discordant + 1))
        / 2**discordant
    )


def analyze(runs_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for arm, multiplier in ARMS.items():
        for seed in sorted(SEEDS):
            matches = list(runs_root.glob(f"p1_m{multiplier}_n32768_s{seed}_funcv1"))
            if len(matches) != 1:
                summaries.append({"arm": arm, "seed": seed, "integrity": False, "origin": None,
                                  "error": f"expected one run, found {len(matches)}"})
                continue
            result, _, _ = summarize(matches[0], pool_multiplier=multiplier, allowed_seeds=SEEDS)
            result.update(arm=arm)
            summaries.append(result)
    runs = pd.DataFrame(summaries).sort_values(["seed", "arm"], ignore_index=True)
    valid = runs[runs["integrity"] == True]  # noqa: E712
    pivot = valid.pivot(index="seed", columns="arm", values="origin")
    complete = pivot.dropna().astype(bool)
    favored_only = int((complete["m16"] & ~complete["m2"]).sum())
    opposite_only = int((complete["m2"] & ~complete["m16"]).sum())
    both = int((complete["m2"] & complete["m16"]).sum())
    neither = int((~complete["m2"] & ~complete["m16"]).sum())
    pairs = pd.DataFrame({
        "seed": complete.index.astype(int), "m2_origin": complete["m2"].to_numpy(),
        "m16_origin": complete["m16"].to_numpy(),
    })
    m2_origins = int(complete["m2"].sum())
    m16_origins = int(complete["m16"].sum())
    difference = (m16_origins - m2_origins) / 20
    p_value = exact_one_sided(favored_only, opposite_only)
    gates = {
        "integrity": len(valid) == 40 and len(complete) == 20,
        "m16_positive_control": m16_origins >= 5,
        "paired_difference": difference >= 0.20,
        "exact_test": p_value <= 0.05,
    }
    decision = bool(all(gates.values()))
    result = {
        "decision": "PASS" if decision else "FAIL — stop resource-abundance comparison",
        "resource_abundance_support": decision,
        "gates": gates,
        "m2_origins": m2_origins,
        "m16_origins": m16_origins,
        "incidence_difference": difference,
        "favored_only": favored_only,
        "opposite_only": opposite_only,
        "both": both,
        "neither": neither,
        "p_one_sided": p_value,
    }
    return runs, pairs, result


def write_outputs(runs: pd.DataFrame, pairs: pd.DataFrame, result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    runs.to_csv(output_dir / "runs.csv", index=False)
    pairs.to_csv(output_dir / "pairs.csv", index=False)
    pd.DataFrame([{"gate": key, "pass": value} for key, value in result["gates"].items()]).to_csv(
        output_dir / "gates.csv", index=False
    )
    (output_dir / "decision.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# AC-P002 conserved-resource abundance and functional origin", "",
        f"**{result['decision']}**", "",
        f"- m16 origins: {result['m16_origins']}/20",
        f"- m2 origins: {result['m2_origins']}/20",
        f"- Paired incidence difference: {result['incidence_difference']:.3f}",
        f"- Discordant pairs (m16-only / m2-only): {result['favored_only']} / {result['opposite_only']}",
        f"- Exact one-sided p: {result['p_one_sided']:.8g}", "",
    ]
    lines += [f"- {gate}: {'PASS' if passed else 'FAIL'}" for gate, passed in result["gates"].items()]
    lines += ["", "A failed paired gate cannot be rescued by the positive-control result. Nonsignificance is not equivalence.",
              "This analysis supports no adaptation, organization, ecology, self-maintenance, or organism claim.", ""]
    (output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


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
