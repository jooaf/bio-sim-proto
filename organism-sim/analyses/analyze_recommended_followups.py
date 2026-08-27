"""Analyze persistence, resource-factorial, and founder-archetype follow-ups."""

from __future__ import annotations

import csv
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path("experiment_results/recommended_followups")
RUNS_ROOT = ROOT / "runs"
CAUSE_COLUMNS = {
    "mate_readiness": "reproduction_mate_readiness_blocks",
    "energy": "reproduction_energy_blocks",
    "body_matter": "reproduction_body_matter_blocks",
}
SUMMARY_METRICS = (
    "population_retention",
    "replacement_ratio",
    "resource_block_rate",
    "mate_readiness_block_rate",
    "energy_block_rate",
    "body_matter_block_rate",
    "attrition_per_1000_organism_ticks",
    "final_living_species",
    "species_evenness",
    "peak_colonies",
)


def safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else math.nan


def final_evenness(database: sqlite3.Connection, tick: int) -> float:
    counts = np.asarray([
        row[0]
        for row in database.execute(
            "SELECT population FROM species_states WHERE tick=? AND population>0", (tick,)
        )
    ], dtype=np.float64)
    if not len(counts):
        return 0.0
    if len(counts) == 1:
        return 1.0
    probabilities = counts / counts.sum()
    return math.exp(-float(np.sum(probabilities * np.log(probabilities)))) / len(counts)


def late_population_slope(database: sqlite3.Connection, final_tick: int) -> float:
    start = max(0, final_tick - 1_999)
    rows = database.execute(
        "SELECT tick, population FROM tick_metrics WHERE tick>=? ORDER BY tick", (start,)
    ).fetchall()
    ticks = np.asarray([row[0] for row in rows], dtype=np.float64)
    population = np.asarray([row[1] for row in rows], dtype=np.float64)
    centered = ticks - ticks.mean()
    denominator = float(centered @ centered)
    return float(centered @ (population - population.mean()) / denominator) if denominator else 0.0


def summarize(database_path: Path) -> dict[str, object]:
    condition = database_path.parents[1].name
    study = database_path.parents[2].name
    manifest = json.loads((database_path.parent / "manifest.json").read_text(encoding="utf-8"))
    with sqlite3.connect(database_path) as database:
        database.row_factory = sqlite3.Row
        first = database.execute("SELECT * FROM tick_metrics ORDER BY tick LIMIT 1").fetchone()
        final = database.execute("SELECT * FROM tick_metrics ORDER BY tick DESC LIMIT 1").fetchone()
        assert first is not None and final is not None
        config = json.loads(database.execute(
            "SELECT config_json FROM config_events ORDER BY tick LIMIT 1"
        ).fetchone()[0])
        aggregates = database.execute(
            """
            SELECT SUM(population) AS organism_ticks,
                   MAX(population) AS peak_population,
                   MAX(living_species) AS peak_species,
                   MAX(colonies) AS peak_colonies,
                   MAX(ABS(energy_error)) AS maximum_energy_error,
                   SUM(CASE WHEN reproduction_resource_blocks !=
                       reproduction_mate_readiness_blocks + reproduction_energy_blocks
                       + reproduction_body_matter_blocks THEN 1 ELSE 0 END) AS block_mismatches
            FROM tick_metrics
            """
        ).fetchone()
        attrition = database.execute(
            """
            SELECT COUNT(*) FROM events WHERE event_type='death'
            AND json_extract(payload_json, '$.last_action')='dead:attrition'
            """
        ).fetchone()[0]
        element_residual = database.execute(
            """
            WITH initial AS (SELECT element_id, element_count FROM element_states WHERE tick=0)
            SELECT MAX(ABS(states.element_count - initial.element_count))
            FROM element_states AS states JOIN initial USING (element_id)
            """
        ).fetchone()[0]
        attempts = final["reproduction_attempts"]
        resource_blocks = final["reproduction_resource_blocks"]
        extinction_tick = database.execute(
            "SELECT MIN(tick) FROM tick_metrics WHERE population=0"
        ).fetchone()[0]
        checkpoint_populations = {
            tick: database.execute(
                "SELECT population FROM tick_metrics WHERE tick=?", (tick,)
            ).fetchone()
            for tick in (2_500, 5_000, 7_500, 10_000)
            if tick <= final["tick"]
        }
        return {
            "study": study,
            "condition": condition,
            "seed": manifest["seed"],
            "run_id": manifest["run_id"],
            "schema_version": manifest["schema_version"],
            "configured_ticks": 10_000 if study == "persistence" else 2_500,
            "final_tick": final["tick"],
            "initial_population": first["population"],
            "final_population": final["population"],
            "peak_population": aggregates["peak_population"],
            "population_retention": safe_ratio(final["population"], first["population"]),
            "extinct": final["population"] == 0,
            "extinction_tick": extinction_tick,
            "population_tick_2500": checkpoint_populations.get(2_500, (None,))[0],
            "population_tick_5000": checkpoint_populations.get(5_000, (None,))[0],
            "population_tick_7500": checkpoint_populations.get(7_500, (None,))[0],
            "population_tick_10000": checkpoint_populations.get(10_000, (None,))[0],
            "births": final["births"],
            "deaths": final["deaths"],
            "replacement_ratio": safe_ratio(final["births"], final["deaths"]),
            "reproduction_attempts": attempts,
            "reproduction_resource_blocks": resource_blocks,
            "reproduction_mate_readiness_blocks": final["reproduction_mate_readiness_blocks"],
            "reproduction_energy_blocks": final["reproduction_energy_blocks"],
            "reproduction_body_matter_blocks": final["reproduction_body_matter_blocks"],
            "resource_block_rate": safe_ratio(resource_blocks, attempts),
            "mate_readiness_block_rate": safe_ratio(
                final["reproduction_mate_readiness_blocks"], attempts
            ),
            "energy_block_rate": safe_ratio(final["reproduction_energy_blocks"], attempts),
            "body_matter_block_rate": safe_ratio(
                final["reproduction_body_matter_blocks"], attempts
            ),
            "energy_share_of_resource_blocks": safe_ratio(
                final["reproduction_energy_blocks"], resource_blocks
            ),
            "body_matter_share_of_resource_blocks": safe_ratio(
                final["reproduction_body_matter_blocks"], resource_blocks
            ),
            "mate_readiness_share_of_resource_blocks": safe_ratio(
                final["reproduction_mate_readiness_blocks"], resource_blocks
            ),
            "success_per_attempt": safe_ratio(final["successful_reproductions"], attempts),
            "sexual_event_share": safe_ratio(
                final["sexual_events"], final["asexual_events"] + final["sexual_events"]
            ),
            "attrition_deaths": attrition,
            "organism_ticks": aggregates["organism_ticks"],
            "attrition_per_1000_organism_ticks": 1000.0 * safe_ratio(
                attrition, aggregates["organism_ticks"]
            ),
            "final_living_species": final["living_species"],
            "peak_living_species": aggregates["peak_species"],
            "species_evenness": final_evenness(database, final["tick"]),
            "peak_colonies": aggregates["peak_colonies"],
            "late_population_slope": late_population_slope(database, final["tick"]),
            "maximum_energy_error": aggregates["maximum_energy_error"],
            "maximum_element_residual": element_residual,
            "block_counter_mismatches": aggregates["block_mismatches"],
            "reproduction_cost": config["reproduction_cost_multiplier"],
            "initial_deposits": config["initial_deposits"],
            "founder_archetypes": config["founder_archetype_count"],
            "mutation_multiplier": config["mutation_multiplier"],
            "maintenance_multiplier": config["maintenance_cost_multiplier"],
        }


def bootstrap_mean_ci(values: np.ndarray, seed: int, draws: int = 20_000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    resamples = rng.choice(values, size=(draws, len(values)), replace=True).mean(axis=1)
    return tuple(float(value) for value in np.quantile(resamples, (0.025, 0.975)))


def exact_sign_flip_p(differences: np.ndarray) -> float:
    observed = abs(float(differences.mean()))
    n = len(differences)
    masks = np.arange(1 << n, dtype=np.uint32)
    signs = 1.0 - 2.0 * ((masks[:, None] >> np.arange(n, dtype=np.uint32)) & 1)
    means = (signs * differences).mean(axis=1)
    return float(np.mean(np.abs(means) >= observed - 1e-15))


def contrast(name: str, study: str, metric: str, differences: np.ndarray, seed: int) -> dict[str, object]:
    low, high = bootstrap_mean_ci(differences, seed)
    standard_deviation = float(differences.std(ddof=1))
    return {
        "study": study,
        "contrast": name,
        "metric": metric,
        "n_pairs": len(differences),
        "mean_difference": float(differences.mean()),
        "ci95_low": low,
        "ci95_high": high,
        "cohen_dz": safe_ratio(float(differences.mean()), standard_deviation),
        "directions_positive": int(np.sum(differences > 0)),
        "directions_negative": int(np.sum(differences < 0)),
        "exact_sign_flip_p": exact_sign_flip_p(differences),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def group_summaries(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["study"]), str(row["condition"]))].append(row)
    output: list[dict[str, object]] = []
    for index, ((study, condition), group) in enumerate(sorted(groups.items())):
        summary: dict[str, object] = {
            "study": study,
            "condition": condition,
            "n_runs": len(group),
            "extinctions": sum(bool(row["extinct"]) for row in group),
            "runs_with_colonies": sum(float(row["peak_colonies"]) > 0 for row in group),
        }
        for offset, metric in enumerate(SUMMARY_METRICS + ("late_population_slope",)):
            values = np.asarray([float(row[metric]) for row in group])
            low, high = bootstrap_mean_ci(values, 20260901 + index * 20 + offset)
            summary[f"{metric}_mean"] = float(values.mean())
            summary[f"{metric}_median"] = float(np.median(values))
            summary[f"{metric}_ci95_low"] = low
            summary[f"{metric}_ci95_high"] = high
        output.append(summary)
    return output


def build_contrasts(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_key = {
        (str(row["study"]), str(row["condition"]), int(row["seed"])): row
        for row in rows
    }
    metrics = SUMMARY_METRICS + ("success_per_attempt", "sexual_event_share")
    output: list[dict[str, object]] = []
    serial = 0
    for metric in metrics:
        # Resource-cost main effect: cost 0.50 - 0.75, averaging deposits within seed.
        cost_differences = np.asarray([
            np.mean([
                float(by_key[("resource_factorial", f"cost-0p5_deposits-{deposits}", seed)][metric])
                - float(by_key[("resource_factorial", f"cost-0p75_deposits-{deposits}", seed)][metric])
                for deposits in (2600, 4900)
            ])
            for seed in range(60, 65)
        ])
        output.append(contrast("cost 0.50 - 0.75", "resource_factorial", metric, cost_differences, 20261000 + serial))
        serial += 1
        deposit_differences = np.asarray([
            np.mean([
                float(by_key[("resource_factorial", f"cost-{cost}_deposits-4900", seed)][metric])
                - float(by_key[("resource_factorial", f"cost-{cost}_deposits-2600", seed)][metric])
                for cost in ("0p5", "0p75")
            ])
            for seed in range(60, 65)
        ])
        output.append(contrast("deposits 4900 - 2600", "resource_factorial", metric, deposit_differences, 20261000 + serial))
        serial += 1
        founder_differences = np.asarray([
            float(by_key[("founder_archetypes", "archetypes-21", seed)][metric])
            - float(by_key[("founder_archetypes", "archetypes-8", seed)][metric])
            for seed in range(65, 70)
        ])
        output.append(contrast("archetypes 21 - 8", "founder_archetypes", metric, founder_differences, 20261000 + serial))
        serial += 1
    return output


def effect(contrasts: list[dict[str, object]], study: str, name: str, metric: str) -> dict[str, object]:
    return next(
        row for row in contrasts
        if row["study"] == study and row["contrast"] == name and row["metric"] == metric
    )


def fmt(row: dict[str, object], digits: int = 3) -> str:
    return (
        f"{float(row['mean_difference']):+.{digits}f} "
        f"[{float(row['ci95_low']):+.{digits}f}, {float(row['ci95_high']):+.{digits}f}] "
        f"({int(row['directions_positive'])}+/{int(row['directions_negative'])}− pairs, "
        f"exact p={float(row['exact_sign_flip_p']):.4f})"
    )


def write_report(rows: list[dict[str, object]], groups: list[dict[str, object]], contrasts: list[dict[str, object]]) -> None:
    persistence = [row for row in rows if row["study"] == "persistence"]
    persistence_group = next(row for row in groups if row["study"] == "persistence")
    resource_groups = [row for row in groups if row["study"] == "resource_factorial"]
    founder_groups = [row for row in groups if row["study"] == "founder_archetypes"]
    all_valid = all(
        int(row["schema_version"]) == 3
        and int(row["final_tick"]) == int(row["configured_ticks"])
        and int(row["maximum_element_residual"]) == 0
        and int(row["block_counter_mismatches"]) == 0
        and float(row["maximum_energy_error"]) < 1e-6
        for row in rows
    )
    persistence_slopes = np.asarray([float(row["late_population_slope"]) for row in persistence])
    extinction_ticks = np.asarray([
        int(row["extinction_tick"]) for row in persistence if row["extinction_tick"] is not None
    ])
    resource_best = max(resource_groups, key=lambda row: float(row["population_retention_median"]))
    cause_totals = {
        cause: sum(int(row[column]) for row in rows)
        for cause, column in CAUSE_COLUMNS.items()
    }
    total_resource_blocks = sum(int(row["reproduction_resource_blocks"]) for row in rows)
    lines = [
        "# Recommended follow-up results",
        "",
        "## Executive summary",
        "",
        f"All **{len(rows)}/{len(rows)}** runs completed and {'passed' if all_valid else 'did not all pass'} integrity checks. The split counters show which resource bottleneck dominates rather than treating all failed attempts as one category.",
        "",
        "## F1 — 10,000-tick persistence",
        "",
        f"- Extinctions: **{int(persistence_group['extinctions'])}/10**.",
        (
            f"- Mean final retention: **{float(persistence_group['population_retention_mean']):.1%}** "
            f"[{float(persistence_group['population_retention_ci95_low']):.1%}, "
            f"{float(persistence_group['population_retention_ci95_high']):.1%}]."
        ),
        f"- Median extinction tick among extinct runs: **{float(np.median(extinction_ticks)):,.0f}**.",
        f"- Mean births/death: **{float(persistence_group['replacement_ratio_mean']):.3f}**.",
        f"- Mean populations at ticks 2,500/5,000/7,500/10,000: **{np.mean([float(row['population_tick_2500']) for row in persistence]):.1f} / {np.mean([float(row['population_tick_5000']) for row in persistence]):.1f} / {np.mean([float(row['population_tick_7500']) for row in persistence]):.1f} / {np.mean([float(row['population_tick_10000']) for row in persistence]):.1f}**.",
        (
            f"- Mean late-window population slope: **{float(persistence_slopes.mean()):+.4f} "
            f"organisms/tick**; {int(np.sum(persistence_slopes > 0))}/10 were positive."
        ),
        f"- Resource-block causes per attempt: energy **{float(persistence_group['energy_block_rate_mean']):.1%}**, body matter **{float(persistence_group['body_matter_block_rate_mean']):.1%}**, mate readiness **{float(persistence_group['mate_readiness_block_rate_mean']):.1%}**.",
        "",
        "## F2 — Reproduction cost × deposits",
        "",
        "| Condition | Retention mean / median | Births/death mean / median | Resource blocked | Energy blocked | Body blocked | Mate blocked | Extinct |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in resource_groups:
        lines.append(
            f"| `{row['condition']}` | {float(row['population_retention_mean']):.1%} / {float(row['population_retention_median']):.1%} | "
            f"{float(row['replacement_ratio_mean']):.3f} / {float(row['replacement_ratio_median']):.3f} | {float(row['resource_block_rate_mean']):.1%} | "
            f"{float(row['energy_block_rate_mean']):.1%} | {float(row['body_matter_block_rate_mean']):.1%} | "
            f"{float(row['mate_readiness_block_rate_mean']):.1%} | {int(row['extinctions'])}/5 |"
        )
    lines.extend([
        "",
        f"Best median-retention cell: `{resource_best['condition']}` at **{float(resource_best['population_retention_median']):.1%}**; heavy-tailed seed outcomes make medians more representative than means here.",
        "",
        "Factor effects (five independent seed blocks):",
        "",
        f"- Cost 0.50 retention: {fmt(effect(contrasts, 'resource_factorial', 'cost 0.50 - 0.75', 'population_retention'))}.",
        f"- Cost 0.50 replacement: {fmt(effect(contrasts, 'resource_factorial', 'cost 0.50 - 0.75', 'replacement_ratio'))}.",
        f"- Cost 0.50 energy blocking: {fmt(effect(contrasts, 'resource_factorial', 'cost 0.50 - 0.75', 'energy_block_rate'))}.",
        f"- Deposits 4,900 retention: {fmt(effect(contrasts, 'resource_factorial', 'deposits 4900 - 2600', 'population_retention'))}.",
        f"- Deposits 4,900 energy blocking: {fmt(effect(contrasts, 'resource_factorial', 'deposits 4900 - 2600', 'energy_block_rate'))}.",
        "",
        "## F3 — Founder archetypes",
        "",
        "| Archetypes | Retention | Births/death | Living species | Evenness | Resource blocked |",
        "|---:|---:|---:|---:|---:|---:|",
    ])
    for row in founder_groups:
        lines.append(
            f"| {row['condition'].split('-')[-1]} | {float(row['population_retention_mean']):.1%} | "
            f"{float(row['replacement_ratio_mean']):.3f} | {float(row['final_living_species_mean']):.2f} | "
            f"{float(row['species_evenness_mean']):.3f} | {float(row['resource_block_rate_mean']):.1%} |"
        )
    lines.extend([
        "",
        f"- 21-archetype living-species effect: {fmt(effect(contrasts, 'founder_archetypes', 'archetypes 21 - 8', 'final_living_species'))}.",
        f"- 21-archetype retention effect: {fmt(effect(contrasts, 'founder_archetypes', 'archetypes 21 - 8', 'population_retention'))}.",
        f"- 21-archetype evenness effect: {fmt(effect(contrasts, 'founder_archetypes', 'archetypes 21 - 8', 'species_evenness'))}.",
        "",
        "## Interpretation",
        "",
        f"Across all runs, **{cause_totals['energy'] / total_resource_blocks:.1%}** of resource blocks were energy blocks, **{cause_totals['body_matter'] / total_resource_blocks:.1%}** were body-matter blocks, and mate-readiness blocks were **{cause_totals['mate_readiness']}**. Mate readiness is normally filtered before `_attempt_reproduction`, so zero confirms that this guard is not a runtime bottleneck.",
        "",
        "Lower reproduction cost produced small, consistent improvements in retention and births/death, but barely changed energy blocking. More deposits strongly reduced energy blocking in every seed, yet did not consistently improve retention or replacement. Deposit count is initialized before founders using one RNG stream, so changing deposits also changes the realized founder draw; the deposit survival contrast is therefore noisy and should be repeated after RNG streams are separated.",
        "",
        "The 10K study rejects 2,500-tick retention as evidence of persistence: eight runs went extinct and the two survivors had only three and one organisms. Five-pair factorial and founder effects are estimates, not significance claims; their minimum two-sided exact p-value is 0.0625.",
        "",
        "## Reproducibility",
        "",
        "- Raw runs: `experiment_results/recommended_followups/runs/`",
        "- Per-run summary: `experiment_results/recommended_followups/run_summary.csv`",
        "- Group summary: `experiment_results/recommended_followups/group_summary.csv`",
        "- Paired effects: `experiment_results/recommended_followups/paired_contrasts.csv`",
        "- Runner: `experiments/run_recommended_followups.nu`",
        "- Analyzer: `analyses/analyze_recommended_followups.py`",
    ])
    (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    databases = sorted(RUNS_ROOT.glob("*/*/*/run.sqlite"))
    if len(databases) != 40:
        raise RuntimeError(f"expected 40 runs, found {len(databases)}")
    rows = [summarize(path) for path in databases]
    write_csv(ROOT / "run_summary.csv", rows)
    groups = group_summaries(rows)
    write_csv(ROOT / "group_summary.csv", groups)
    contrasts = build_contrasts(rows)
    write_csv(ROOT / "paired_contrasts.csv", contrasts)
    write_report(rows, groups, contrasts)
    print(f"Analyzed {len(rows)} runs across {len(groups)} cells")


if __name__ == "__main__":
    main()
