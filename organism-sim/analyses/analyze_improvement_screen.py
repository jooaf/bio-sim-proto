"""Analyze the paired maintenance × sexual-floor improvement screen."""

from __future__ import annotations

import csv
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path("experiment_results/improvement_screen")
RUNS_ROOT = ROOT / "runs"
BASELINE = "maint-1_floor-0p12"
PRIMARY_METRICS = ("population_retention", "replacement_ratio", "attrition_per_1000_organism_ticks")
METRICS = PRIMARY_METRICS + (
    "sexual_event_share",
    "success_per_attempt",
    "resource_block_rate",
    "final_living_species",
    "species_evenness",
    "peak_colonies",
)
LABELS = {
    "population_retention": "final population retention",
    "replacement_ratio": "births per death",
    "attrition_per_1000_organism_ticks": "attrition deaths / 1,000 organism-ticks",
    "sexual_event_share": "sexual share of successful reproduction events",
    "success_per_attempt": "successful births per attempt",
    "resource_block_rate": "resource-blocked attempt fraction",
    "final_living_species": "final living species",
    "species_evenness": "final species evenness",
    "peak_colonies": "peak colonies",
}


def safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else math.nan


def parse_condition(name: str) -> tuple[float, float, bool]:
    maintenance = 0.75 if name.startswith("maint-0p75") else 1.0
    if name.endswith("floor-off"):
        return maintenance, 0.0, False
    floor = float(name.rsplit("floor-", 1)[1].replace("p", "."))
    return maintenance, floor, True


def final_evenness(database: sqlite3.Connection, tick: int) -> float:
    counts = np.asarray(
        [row[0] for row in database.execute(
            "SELECT population FROM species_states WHERE tick=? AND population>0", (tick,)
        )],
        dtype=np.float64,
    )
    if len(counts) <= 1:
        return 1.0 if len(counts) == 1 else 0.0
    probabilities = counts / counts.sum()
    shannon = -float(np.sum(probabilities * np.log(probabilities)))
    return math.exp(shannon) / len(counts)


def summarize_run(database_path: Path) -> dict[str, object]:
    condition = database_path.parents[1].name
    maintenance, sexual_floor, floor_enabled = parse_condition(condition)
    manifest = json.loads((database_path.parent / "manifest.json").read_text(encoding="utf-8"))
    with sqlite3.connect(database_path) as database:
        database.row_factory = sqlite3.Row
        first = database.execute("SELECT * FROM tick_metrics ORDER BY tick LIMIT 1").fetchone()
        final = database.execute("SELECT * FROM tick_metrics ORDER BY tick DESC LIMIT 1").fetchone()
        assert first is not None and final is not None
        aggregates = database.execute(
            """
            SELECT SUM(population) AS organism_ticks,
                   MAX(population) AS peak_population,
                   MAX(living_species) AS peak_species,
                   MAX(colonies) AS peak_colonies,
                   MAX(ABS(energy_error)) AS maximum_energy_error
            FROM tick_metrics
            """
        ).fetchone()
        attrition_deaths = database.execute(
            """
            SELECT COUNT(*) FROM events
            WHERE event_type='death'
              AND json_extract(payload_json, '$.last_action')='dead:attrition'
            """
        ).fetchone()[0]
        predation_deaths = database.execute(
            """
            SELECT COUNT(*) FROM events
            WHERE event_type='death'
              AND json_extract(payload_json, '$.last_action')='dead:predation'
            """
        ).fetchone()[0]
        max_generation = database.execute("SELECT MAX(generation) FROM organisms").fetchone()[0]
        maximum_element_residual = database.execute(
            """
            WITH initial AS (
                SELECT element_id, element_count FROM element_states WHERE tick=0
            )
            SELECT MAX(ABS(states.element_count - initial.element_count))
            FROM element_states AS states
            JOIN initial USING (element_id)
            """
        ).fetchone()[0]
        config = json.loads(database.execute(
            "SELECT config_json FROM config_events ORDER BY tick LIMIT 1"
        ).fetchone()[0])
        successful_events = final["asexual_events"] + final["sexual_events"]
        return {
            "condition": condition,
            "maintenance_multiplier": maintenance,
            "sexual_floor": sexual_floor,
            "sexual_floor_enabled": floor_enabled,
            "seed": manifest["seed"],
            "phase": "screen" if int(manifest["seed"]) <= 44 else "maintenance_confirmation",
            "run_id": manifest["run_id"],
            "final_tick": final["tick"],
            "initial_population": first["population"],
            "final_population": final["population"],
            "peak_population": aggregates["peak_population"],
            "population_retention": safe_ratio(final["population"], first["population"]),
            "births": final["births"],
            "deaths": final["deaths"],
            "replacement_ratio": safe_ratio(final["births"], final["deaths"]),
            "reproduction_attempts": final["reproduction_attempts"],
            "reproduction_resource_blocks": final["reproduction_resource_blocks"],
            "reproduction_probability_failures": final["reproduction_probability_failures"],
            "successful_reproductions": final["successful_reproductions"],
            "resource_block_rate": safe_ratio(
                final["reproduction_resource_blocks"], final["reproduction_attempts"]
            ),
            "probability_failure_rate": safe_ratio(
                final["reproduction_probability_failures"], final["reproduction_attempts"]
            ),
            "success_per_attempt": safe_ratio(
                final["successful_reproductions"], final["reproduction_attempts"]
            ),
            "asexual_events": final["asexual_events"],
            "sexual_events": final["sexual_events"],
            "sexual_event_share": safe_ratio(final["sexual_events"], successful_events),
            "unique_sexual_parents": final["unique_sexual_parents"],
            "final_living_species": final["living_species"],
            "peak_living_species": aggregates["peak_species"],
            "species_evenness": final_evenness(database, final["tick"]),
            "peak_colonies": aggregates["peak_colonies"],
            "attrition_deaths": attrition_deaths,
            "predation_deaths": predation_deaths,
            "attrition_death_share": safe_ratio(attrition_deaths, final["deaths"]),
            "organism_ticks": aggregates["organism_ticks"],
            "attrition_per_1000_organism_ticks": 1000.0 * safe_ratio(
                attrition_deaths, aggregates["organism_ticks"]
            ),
            "max_generation": max_generation,
            "maximum_energy_error": aggregates["maximum_energy_error"],
            "maximum_element_residual": maximum_element_residual,
            "initial_deposits": config["initial_deposits"],
            "mutation_multiplier": config["mutation_multiplier"],
        }


def bootstrap_mean_ci(values: np.ndarray, seed: int, draws: int = 20_000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(draws, len(values)), replace=True).mean(axis=1)
    return tuple(float(value) for value in np.quantile(samples, [0.025, 0.975]))


def exact_sign_flip_p(differences: np.ndarray) -> float:
    observed = abs(float(differences.mean()))
    n = len(differences)
    extreme = 0
    total = 1 << n
    for start in range(0, total, 65_536):
        masks = np.arange(start, min(start + 65_536, total), dtype=np.uint32)
        signs = 1.0 - 2.0 * ((masks[:, None] >> np.arange(n, dtype=np.uint32)) & 1)
        means = (signs * differences).mean(axis=1)
        extreme += int(np.count_nonzero(np.abs(means) >= observed - 1e-15))
    return extreme / total


def holm_adjust(p_values: list[float]) -> list[float]:
    order = np.argsort(p_values)
    adjusted = np.empty(len(p_values), dtype=np.float64)
    running = 0.0
    for rank, index in enumerate(order):
        candidate = (len(p_values) - rank) * p_values[index]
        running = max(running, candidate)
        adjusted[index] = min(1.0, running)
    return adjusted.tolist()


def contrast_row(
    name: str,
    scope: str,
    metric: str,
    differences: np.ndarray,
    seed: int,
) -> dict[str, object]:
    low, high = bootstrap_mean_ci(differences, seed)
    standard_deviation = float(differences.std(ddof=1)) if len(differences) > 1 else 0.0
    return {
        "scope": scope,
        "contrast": name,
        "metric": metric,
        "n_pairs": len(differences),
        "mean_difference": float(differences.mean()),
        "ci95_low": low,
        "ci95_high": high,
        "cohen_dz": safe_ratio(float(differences.mean()), standard_deviation),
        "exact_sign_flip_p": exact_sign_flip_p(differences),
        "holm_p": math.nan,
    }


def build_contrasts(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_key = {(str(row["condition"]), int(row["seed"])): row for row in rows}
    conditions = sorted({str(row["condition"]) for row in rows})
    floors = ("floor-off", "floor-0p12", "floor-0p30", "floor-0p50")
    contrast_rows: list[dict[str, object]] = []
    serial = 0
    for metric in METRICS:
        # Independent paired confirmation at the default floor, seeds 40–49.
        confirmation = np.asarray([
            float(by_key[("maint-0p75_floor-0p12", seed)][metric])
            - float(by_key[("maint-1_floor-0p12", seed)][metric])
            for seed in range(40, 50)
        ])
        row = contrast_row(
            "maintenance 0.75 - 1.00 at floor-0p12",
            "maintenance_confirmation",
            metric,
            confirmation,
            20260820 + serial,
        )
        row["holm_p"] = row["exact_sign_flip_p"]
        contrast_rows.append(row)
        serial += 1

        # Held-out adaptive follow-up only. Five seeds cannot attain p<0.05 in a
        # two-sided exact test, but this shows whether direction replicated.
        heldout = np.asarray([
            float(by_key[("maint-0p75_floor-0p12", seed)][metric])
            - float(by_key[("maint-1_floor-0p12", seed)][metric])
            for seed in range(45, 50)
        ])
        row = contrast_row(
            "maintenance 0.75 - 1.00 at floor-0p12 (new seeds 45-49)",
            "heldout_confirmation",
            metric,
            heldout,
            20260820 + serial,
        )
        row["holm_p"] = row["exact_sign_flip_p"]
        contrast_rows.append(row)
        serial += 1

        # Screening maintenance effect. Average repeated floor cells within each
        # seed so the five independent seeds—not 20 correlated cells—are units.
        maintenance_differences = np.asarray([
            np.mean([
                float(by_key[(f"maint-0p75_{floor}", seed)][metric])
                - float(by_key[(f"maint-1_{floor}", seed)][metric])
                for floor in floors
            ])
            for seed in range(40, 45)
        ])
        contrast_rows.append(contrast_row(
            "maintenance 0.75 - 1.00 (screen average)",
            "screening_factor_effect",
            metric,
            maintenance_differences,
            20260820 + serial,
        ))
        serial += 1

        # Screening floor effects. Average maintenance levels within each seed.
        for floor_label in ("floor-off", "floor-0p30", "floor-0p50"):
            floor_differences = np.asarray([
                np.mean([
                    float(by_key[(f"{maintenance}_{floor_label}", seed)][metric])
                    - float(by_key[(f"{maintenance}_floor-0p12", seed)][metric])
                    for maintenance in ("maint-0p75", "maint-1")
                ])
                for seed in range(40, 45)
            ])
            contrast_rows.append(contrast_row(
                f"{floor_label} - floor-0p12",
                "screening_factor_effect",
                metric,
                floor_differences,
                20260820 + serial,
            ))
            serial += 1

        # Exploratory individual-condition contrasts use the five screen seeds.
        for condition in conditions:
            if condition == BASELINE:
                continue
            differences = np.asarray([
                float(by_key[(condition, seed)][metric]) - float(by_key[(BASELINE, seed)][metric])
                for seed in range(40, 45)
            ])
            contrast_rows.append(contrast_row(
                f"{condition} - {BASELINE}", "condition_vs_default", metric,
                differences, 20260820 + serial,
            ))
            serial += 1

    # Screening factor tests are multiplicity-adjusted within each metric.
    for metric in METRICS:
        family = [
            row for row in contrast_rows
            if row["metric"] == metric and row["scope"] == "screening_factor_effect"
        ]
        adjusted = holm_adjust([float(row["exact_sign_flip_p"]) for row in family])
        for row, value in zip(family, adjusted):
            row["holm_p"] = value
    return contrast_rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def group_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["condition"])].append(row)
    output: list[dict[str, object]] = []
    for index, condition in enumerate(sorted(grouped)):
        group = grouped[condition]
        summary: dict[str, object] = {
            "condition": condition,
            "maintenance_multiplier": group[0]["maintenance_multiplier"],
            "sexual_floor": group[0]["sexual_floor"],
            "sexual_floor_enabled": group[0]["sexual_floor_enabled"],
            "n_runs": len(group),
            "runs_extinct": sum(float(row["final_population"]) == 0 for row in group),
            "runs_with_colonies": sum(float(row["peak_colonies"]) > 0 for row in group),
            "maximum_energy_error": max(float(row["maximum_energy_error"]) for row in group),
            "maximum_element_residual": max(int(row["maximum_element_residual"]) for row in group),
        }
        for offset, metric in enumerate(METRICS):
            values = np.asarray([float(row[metric]) for row in group])
            low, high = bootstrap_mean_ci(values, 20260830 + index * 20 + offset)
            summary[f"{metric}_mean"] = float(values.mean())
            summary[f"{metric}_ci95_low"] = low
            summary[f"{metric}_ci95_high"] = high
        output.append(summary)
    return output


def effect_lookup(contrasts: list[dict[str, object]], metric: str, name: str) -> dict[str, object]:
    return next(row for row in contrasts if row["metric"] == metric and row["contrast"] == name)


def format_effect(row: dict[str, object], digits: int = 3) -> str:
    return (
        f"{float(row['mean_difference']):+.{digits}f} "
        f"[{float(row['ci95_low']):+.{digits}f}, {float(row['ci95_high']):+.{digits}f}], "
        f"exact p={float(row['exact_sign_flip_p']):.4f}, Holm p={float(row['holm_p']):.4f}"
    )


def write_report(groups: list[dict[str, object]], contrasts: list[dict[str, object]]) -> None:
    best_retention = max(groups, key=lambda row: float(row["population_retention_mean"]))
    best_replacement = max(groups, key=lambda row: float(row["replacement_ratio_mean"]))
    best_sexual = max(groups, key=lambda row: float(row["sexual_event_share_mean"]))
    confirmation_name = "maintenance 0.75 - 1.00 at floor-0p12"
    maintenance_retention = effect_lookup(contrasts, "population_retention", confirmation_name)
    maintenance_replacement = effect_lookup(contrasts, "replacement_ratio", confirmation_name)
    maintenance_attrition = effect_lookup(
        contrasts, "attrition_per_1000_organism_ticks", confirmation_name
    )
    maintenance_blocking = effect_lookup(contrasts, "resource_block_rate", confirmation_name)
    maintenance_success = effect_lookup(contrasts, "success_per_attempt", confirmation_name)
    heldout_name = "maintenance 0.75 - 1.00 at floor-0p12 (new seeds 45-49)"
    heldout_retention = effect_lookup(contrasts, "population_retention", heldout_name)
    heldout_replacement = effect_lookup(contrasts, "replacement_ratio", heldout_name)
    heldout_attrition = effect_lookup(
        contrasts, "attrition_per_1000_organism_ticks", heldout_name
    )
    floor_effects = [
        effect_lookup(contrasts, "sexual_event_share", f"{floor} - floor-0p12")
        for floor in ("floor-off", "floor-0p30", "floor-0p50")
    ]
    default = next(row for row in groups if row["condition"] == BASELINE)
    all_conserved = all(int(row["maximum_element_residual"]) == 0 for row in groups)
    lines = [
        "# Improvement-screen results",
        "",
        "## Executive summary",
        "",
        (
            "All **40/40** screening runs and **10/10** adaptive confirmation runs completed "
            "for **50 total 2,500-tick experiments**. At the default 0.12 sexual floor, the "
            f"maintenance-1.0 control retained **{float(default['population_retention_mean']):.1%}** "
            f"of founders on average; the best-retention cell was `{best_retention['condition']}` "
            f"at **{float(best_retention['population_retention_mean']):.1%}**."
        ),
        "",
        f"- Combined 10-seed maintenance-0.75 retention effect: **{format_effect(maintenance_retention)}**.",
        f"- Combined replacement-ratio effect: **{format_effect(maintenance_replacement)}**.",
        f"- Combined attrition-rate effect: **{format_effect(maintenance_attrition)}** deaths/1,000 organism-ticks.",
        (
            f"- The largest sexual-event share was `{best_sexual['condition']}` at "
            f"**{float(best_sexual['sexual_event_share_mean']):.1%}**."
        ),
        "",
        "## Cell means",
        "",
        "The floor-0.12 cells contain 10 seeds after confirmation; all other cells contain five.",
        "",
        "| Condition | n | Retention | Births/death | Attrition/1K org-ticks | Sexual share | Success/attempt | Resource blocked | Extinct | Colonies |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in groups:
        lines.append(
            f"| `{row['condition']}` | {int(row['n_runs'])} | "
            f"{float(row['population_retention_mean']):.1%} | "
            f"{float(row['replacement_ratio_mean']):.3f} | "
            f"{float(row['attrition_per_1000_organism_ticks_mean']):.3f} | "
            f"{float(row['sexual_event_share_mean']):.1%} | "
            f"{float(row['success_per_attempt_mean']):.1%} | "
            f"{float(row['resource_block_rate_mean']):.1%} | "
            f"{int(row['runs_extinct'])}/{int(row['n_runs'])} | "
            f"{int(row['runs_with_colonies'])}/{int(row['n_runs'])} |"
        )
    lines.extend([
        "",
        "## Sexual-floor screening effects relative to 0.12",
        "",
        "Each effect first averages the two maintenance cells within each seed, leaving five independent seed blocks. These are screening estimates; with n=5, the smallest possible two-sided exact p-value is 0.0625.",
        "",
        "| Contrast | Sexual-share difference | Retention difference | Resource-block difference |",
        "|---|---:|---:|---:|",
    ])
    for floor, sexual_effect in zip(("floor-off", "floor-0p30", "floor-0p50"), floor_effects):
        retention = effect_lookup(contrasts, "population_retention", f"{floor} - floor-0p12")
        blocking = effect_lookup(contrasts, "resource_block_rate", f"{floor} - floor-0p12")
        lines.append(
            f"| {floor} − 0.12 | {format_effect(sexual_effect)} | "
            f"{format_effect(retention)} | {format_effect(blocking)} |"
        )
    lines.extend([
        "",
        "## What worked",
        "",
        "- **Maintenance 0.75 is the only strongly supported general improvement.** Across all 10 paired seeds at floor 0.12 it improved retention and births/death while reducing exposure-adjusted attrition.",
        (
            "- **The five new seeds replicated the direction:** retention "
            f"{format_effect(heldout_retention)}, replacement {format_effect(heldout_replacement)}, "
            f"and attrition {format_effect(heldout_attrition)}. Exact significance is unattainable "
            "with only five two-sided pairs, so this is directional held-out support."
        ),
        (
            f"- **Best observed retention:** `{best_retention['condition']}` "
            f"({float(best_retention['population_retention_mean']):.1%}, "
            f"n={int(best_retention['n_runs'])})."
        ),
        "- **Higher sexual floors changed reproductive mode directionally:** floor 0.30 and 0.50 raised mean sexual share, but effects were not positive in every seed and the screening sample cannot provide p<0.05.",
        (
            f"- **Conservation:** {'all runs had zero per-element residual' if all_conserved else 'a nonzero element residual was detected'}; maximum energy error remained below "
            f"{max(float(row['maximum_energy_error']) for row in groups):.2e}."
        ),
        "",
        "## What did not work",
        "",
        "- **Sexual floor did not improve survival.** Relative to 0.12, floors 0.30 and 0.50 changed retention by only about 0–0.2 percentage points, with intervals spanning harm and benefit.",
        f"- **Maintenance relief did not solve reproduction scarcity.** It changed resource blocking by {format_effect(maintenance_blocking)} and success per attempt by {format_effect(maintenance_success)}. More organisms survived long enough to attempt reproduction, but roughly 70% of attempts still lacked energy/body matter.",
        f"- **No condition reached replacement.** Even the best cell averaged only {float(best_replacement['replacement_ratio_mean']):.3f} births per death, and extinctions still occurred.",
        "- **Colonies remained inconsistent.** Incidence varied from 1/5 to 3/5 in screening cells with no reliable floor or maintenance effect.",
        "",
        "## Recommended next experiments",
        "",
        "1. Run maintenance 0.75/floor 0.12 for 10,000 ticks on 10 new seeds to estimate extinction probability and late-window population slope.",
        "2. Cross reproduction cost {0.50, 0.75} with deposits {2,600, 4,900} at maintenance 0.75/floor 0.12. This directly targets the unresolved resource block while separating reproductive cost from food availability.",
        "3. Split `reproduction_resource_blocks` into energy, reproductive-body, and mate-readiness counters before that sweep; the current combined counter limits causal diagnosis.",
        "4. Test founder-archetype counts 8 versus 21 only with mutation and ecology fixed; the historical GUI runs confound these factors.",
        "5. Treat floor 0.30 as the next moderate sexual-diversity candidate; 0.50 produced more sexual events but no survival gain and a directional rise in resource blocking.",
        "",
        "## Statistical notes",
        "",
        "Intervals are paired bootstrap percentile intervals over independent seeds. Exact p-values enumerate paired sign flips. The combined 10-seed maintenance result is nominal because the second five-seed allocation followed inspection of the screen, although H1 was specified before any runs. The separate new-seed contrast is the clean directional replication and has a minimum possible two-sided p-value of 0.0625. Screening factor effects average repeated cells within each seed before testing and receive Holm adjustment within each metric. Individual cell contrasts remain exploratory.",
    ])
    (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    databases = sorted(RUNS_ROOT.glob("*/*/run.sqlite"))
    if len(databases) != 50:
        raise RuntimeError(f"expected 50 databases, found {len(databases)}")
    rows = [summarize_run(path) for path in databases]
    if any(int(row["final_tick"]) != 2500 for row in rows):
        raise RuntimeError("one or more runs did not complete 2,500 ticks")
    write_csv(ROOT / "run_summary.csv", rows)
    groups = group_summary(rows)
    write_csv(ROOT / "group_summary.csv", groups)
    contrasts = build_contrasts(rows)
    write_csv(ROOT / "paired_contrasts.csv", contrasts)
    write_report(groups, contrasts)
    print(f"Analyzed {len(rows)} runs across {len(groups)} conditions")


if __name__ == "__main__":
    main()
