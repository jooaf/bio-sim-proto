"""Measure whether exact Rust states admit event/cohort compression.

This benchmark does not simulate cohorts. It samples the unchanged exact kernel
and estimates represented work under three preregistered grouping policies.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from organism_sim.config import SimulationConfig
from organism_sim.rust_kernel import RustKernelSimulation

RESULTS_ROOT = Path(__file__).resolve().parent / "results"
PRESETS = ("lineage_safe", "species_safe", "trait_only")
POLICY_DEFINITIONS = {
    "lineage_safe": {
        "tile_size": 8,
        "colony_bonus_bins": 32,
        "representatives_per_class": 8,
        "taxon_key": "lineage",
        "state_representation": "8 particles retain phenotype/reserve/age/toxin/inventory distributions",
        "protect": "physiology-critical, age<=64, or global lineage population<=32",
    },
    "species_safe": {
        "tile_size": 16,
        "colony_bonus_bins": 16,
        "representatives_per_class": 8,
        "taxon_key": "species",
        "state_representation": "8 particles retain phenotype/reserve/age/toxin/inventory distributions",
        "protect": "physiology-critical, age<=64, or global species population<=32",
    },
    "trait_only": {
        "tile_size": 32,
        "colony_bonus_bins": 8,
        "representatives_per_class": 4,
        "taxon_key": "guild only",
        "state_representation": "4 particles retain phenotype/reserve/age/toxin/inventory distributions",
        "protect": "physiology-critical or age<=64; exploratory and not rare-lineage safe",
    },
}
PROTECTION_DEFINITIONS = {
    "physiology_critical": (
        "reserve<=2 maintenance ticks, integrity<=10%, debt>=87.5% of death threshold, "
        "or active magic status"
    ),
    "cohort_sensitive": (
        "toxin>=90% tolerance and post-lifespan are measured but remain cohort-eligible via "
        "representative distributions and bounded event counts"
    ),
    "low_reserve_diagnostic": "reserve<=8 maintenance ticks",
    "novel": "age<=64 ticks",
    "rare": "global living taxon population<=32",
}


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def build_config(founders: int, seed: int) -> SimulationConfig:
    return SimulationConfig(
        founder_count=founders,
        founder_archetype_count=min(20, max(8, founders // 40)),
        seed=seed,
        audit_every=0,
    )


def fraction(row: dict[str, Any], field: str) -> float:
    population = max(1, int(row["population"]))
    return int(row[field]) / population


def summarize(
    rows: list[dict[str, Any]],
    *,
    burn_in: int,
    simulation_seconds: float,
    observation_seconds: float,
) -> dict[str, Any]:
    eligible = [row for row in rows if int(row["tick"]) >= burn_in] or rows
    preset_summary: dict[str, Any] = {}
    for preset in PRESETS:
        values = [float(row[preset]["represented_fraction"]) for row in eligible]
        preset_summary[preset] = {
            "mean_represented_fraction": statistics.fmean(values),
            "median_represented_fraction": statistics.median(values),
            "min_represented_fraction": min(values),
            "max_represented_fraction": max(values),
            "final_represented_fraction": float(
                rows[-1][preset]["represented_fraction"]
            ),
            "final_protected": int(rows[-1][preset]["protected"]),
            "final_classes": int(rows[-1][preset]["classes"]),
            "final_representatives": int(rows[-1][preset]["representatives"]),
            "final_represented_work": int(rows[-1][preset]["represented_work"]),
        }

    diagnostic_fields = (
        "exact_policy_keys",
        "rare_lineage_organisms",
        "rare_species_organisms",
        "novel_organisms",
        "physiology_critical",
        "low_reserve",
        "critical_reserve",
        "near_integrity_death",
        "near_debt_death",
        "near_toxin_threshold",
        "post_lifespan",
        "active_status",
        "action_due_now",
        "action_due_within_8",
        "nonempty_gut",
    )
    diagnostics = {
        field: {
            "mean_fraction": statistics.fmean(fraction(row, field) for row in eligible),
            "final_fraction": fraction(rows[-1], field),
        }
        for field in diagnostic_fields
    }
    return {
        "sample_count": len(rows),
        "burn_in": burn_in,
        "first_tick": int(rows[0]["tick"]),
        "final_tick": int(rows[-1]["tick"]),
        "initial_population": int(rows[0]["population"]),
        "final_population": int(rows[-1]["population"]),
        "simulation_seconds": simulation_seconds,
        "observation_seconds": observation_seconds,
        "observation_overhead_fraction": observation_seconds
        / max(simulation_seconds + observation_seconds, 1e-12),
        "presets": preset_summary,
        "diagnostics": diagnostics,
        "final_spatial": {
            key: int(rows[-1][key])
            for key in (
                "organism_tiles_8",
                "organism_tiles_16",
                "organism_tiles_32",
                "generated_chunks",
                "active_heat_chunks",
                "active_heat_cells",
                "active_deposit_positions",
                "active_deposit_batches",
                "occupied_cells",
            )
        },
    }


def verdict(median_fraction: float) -> str:
    if median_fraction <= 0.35:
        return "strong compression signal"
    if median_fraction <= 0.65:
        return "moderate compression signal"
    if median_fraction <= 0.85:
        return "weak compression signal"
    return "little or no compression signal"


def write_summary_markdown(
    path: Path,
    *,
    label: str,
    config: SimulationConfig,
    summary: dict[str, Any],
    digest: int,
    audit: dict[str, Any],
) -> None:
    lines = [
        f"# Compressibility benchmark: {label}",
        "",
        (
            f"Exact Rust run: seed `{config.seed}`, founders `{config.founder_count}`, "
            f"ticks `{summary['final_tick']}`, final population `{summary['final_population']}`."
        ),
        "",
        "## Cohort representation estimates",
        "",
        "| policy | median represented | mean represented | final represented | final protected | final classes | signal |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for preset in PRESETS:
        item = summary["presets"][preset]
        median = item["median_represented_fraction"]
        lines.append(
            f"| {preset} | {median:.1%} | {item['mean_represented_fraction']:.1%} | "
            f"{item['final_represented_fraction']:.1%} | {item['final_protected']} | "
            f"{item['final_classes']} | {verdict(median)} |"
        )

    lines.extend(
        [
            "",
            (
                "`represented` is protected individuals plus up to the configured number of "
                "representative particles in every non-protected class. It excludes implementation "
                "overheads and therefore measures opportunity, not predicted wall-clock speedup."
            ),
            "",
            "## Event and protection lower bounds",
            "",
            "| diagnostic | mean population fraction | final population fraction |",
            "|---|---:|---:|",
        ]
    )
    for field, item in summary["diagnostics"].items():
        lines.append(
            f"| {field} | {item['mean_fraction']:.1%} | {item['final_fraction']:.1%} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- `exact_policy_keys` estimates exact-state batching; a value near 100% means lazy events alone cannot merge current states.",
            "- Cohort representative particles carry phenotype, reserve, age, toxin, and inventory distributions rather than making those dimensions separate class keys.",
            "- Toxin-threshold and post-lifespan organisms remain cohort-eligible only because the proposed engine uses representative toxin/age distributions and bounded event counts; both require convergence tests.",
            "- `lineage_safe` is the strongest evolutionary-conservation diagnostic.",
            "- `species_safe` permits merging common lineages within a species and therefore needs drift validation.",
            "- `trait_only` is an exploratory upper bound and is not safe for rare lineages.",
            "- Frequent independent actions, digestion, spatial conflicts, output, or cohort churn can keep total work linear even when upkeep compresses.",
            "- A fragmented ecology must fall back to finer classes; no preset guarantees sublinear scaling.",
            "",
            "## Run integrity",
            "",
            f"- Final digest: `{digest}`",
            f"- Elements conserved: `{audit['elements_ok']}`",
            f"- Energy conserved: `{audit['energy_ok']}`",
            f"- Simulation time: `{summary['simulation_seconds']:.3f}s`",
            (
                f"- Metric observation time: `{summary['observation_seconds']:.3f}s` "
                f"({summary['observation_overhead_fraction']:.2%} of measured total)"
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    config = build_config(args.founders, args.seed)
    simulation = RustKernelSimulation(config)
    label = args.label or f"compress-f{args.founders}-t{args.ticks}-s{args.seed}"
    out_dir = RESULTS_ROOT / label
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    simulation_seconds = 0.0
    observation_seconds = 0.0
    next_progress = args.progress_every

    with (out_dir / "samples.jsonl").open("w", encoding="utf-8") as output:
        while True:
            observed_at = time.perf_counter()
            row = simulation.compressibility_metrics()
            observation_seconds += time.perf_counter() - observed_at
            rows.append(row)
            output.write(_json(row) + "\n")
            output.flush()

            if simulation.tick >= args.ticks:
                break
            step_count = min(args.interval, args.ticks - simulation.tick)
            started = time.perf_counter()
            simulation.step(step_count)
            simulation_seconds += time.perf_counter() - started
            if args.progress_every and simulation.tick >= next_progress:
                latest = rows[-1]["species_safe"]["represented_fraction"]
                print(
                    f"tick={simulation.tick} pop={simulation.population} "
                    f"last_species_safe={latest:.1%}"
                )
                next_progress = simulation.tick + args.progress_every

    audit = simulation.audit()
    digest = simulation.digest()
    summary = summarize(
        rows,
        burn_in=args.burn_in,
        simulation_seconds=simulation_seconds,
        observation_seconds=observation_seconds,
    )
    result = {
        "schema_version": 1,
        "label": label,
        "config": asdict(config),
        "sampling_interval": args.interval,
        "policy_definitions": POLICY_DEFINITIONS,
        "protection_definitions": PROTECTION_DEFINITIONS,
        "summary": summary,
        "digest": digest,
        "audit": audit,
    }
    (out_dir / "metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    write_summary_markdown(
        out_dir / "summary.md",
        label=label,
        config=config,
        summary=summary,
        digest=digest,
        audit=audit,
    )
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--founders", type=int, default=1200)
    parser.add_argument("--ticks", type=int, default=10000)
    parser.add_argument("--interval", type=int, default=500)
    parser.add_argument("--burn-in", type=int, default=500)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--label")
    parser.add_argument("--progress-every", type=int, default=1000)
    args = parser.parse_args()
    if args.ticks < 0 or args.interval < 1 or args.burn_in < 0:
        parser.error("ticks and burn-in must be nonnegative; interval must be positive")

    out_dir = run(args)
    result = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
    summary = result["summary"]
    for preset in PRESETS:
        item = summary["presets"][preset]
        print(
            f"{preset}: median={item['median_represented_fraction']:.1%} "
            f"final={item['final_represented_fraction']:.1%}"
        )
    print(f"results: {out_dir}")


if __name__ == "__main__":
    main()
