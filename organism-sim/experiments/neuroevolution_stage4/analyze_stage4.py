"""Apply the frozen Stage 4 paired analysis and write reproducible reports."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = ROOT / "experiment_results" / "neuroevolution_stage4_v3"
ANALYSIS_SEED = 20_260_814
BOOTSTRAP_SAMPLES = 20_000
ALPHA = 0.05


@dataclass(frozen=True)
class PrimaryDefinition:
    identifier: str
    description: str
    alternative: str
    difference: Callable[[dict[str, dict[str, Any]]], float | None]


def safe_fraction(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return float(numerator / denominator)


def optional_difference(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return float(left - right)


def primary_definitions() -> tuple[PrimaryDefinition, ...]:
    return (
        PrimaryDefinition(
            "P1",
            "interface viability: final population, linear priors - linear random",
            "greater",
            lambda runs: float(
                runs["linear_priors"]["population"]
                - runs["linear_random"]["population"]
            ),
        ),
        PrimaryDefinition(
            "P2",
            "nonlinear ecological effect: final population, recurrent - linear priors",
            "two-sided",
            lambda runs: float(
                runs["recurrent"]["population"] - runs["linear_priors"]["population"]
            ),
        ),
        PrimaryDefinition(
            "P3",
            "memory consequence: final population, recurrent - recurrent lesion",
            "greater",
            lambda runs: float(
                runs["recurrent"]["population"] - runs["recurrent_lesion"]["population"]
            ),
        ),
        PrimaryDefinition(
            "P4",
            "within-agent ambiguous argmax-change fraction versus zero",
            "greater",
            lambda runs: safe_fraction(
                runs["recurrent"]["memory_probe_ambiguous_argmax_changes"],
                runs["recurrent"]["memory_probe_ambiguous_food_events"],
            ),
        ),
        PrimaryDefinition(
            "P5",
            "stateful minus zero-state return fraction in ambiguous events",
            "greater",
            lambda runs: _return_fraction_difference(runs["recurrent"]),
        ),
        PrimaryDefinition(
            "P6",
            "genetic recurrent-expression mean, recurrent - recurrent lesion",
            "greater",
            lambda runs: optional_difference(
                runs["recurrent"]["recurrent_expression_genetic"]["mean"],
                runs["recurrent_lesion"]["recurrent_expression_genetic"]["mean"],
            ),
        ),
    )


def _return_fraction_difference(record: dict[str, Any]) -> float | None:
    events = record["memory_probe_ambiguous_food_events"]
    if events <= 0:
        return None
    return float(
        (
            record["memory_probe_stateful_return_choices"]
            - record["memory_probe_zero_state_return_choices"]
        )
        / events
    )


def exact_sign_flip_p(differences: np.ndarray[Any, Any], alternative: str) -> float:
    observed = float(np.mean(differences))
    extreme = 0
    total = 1 << len(differences)
    tolerance = 1.0e-15
    for mask in range(total):
        signed_sum = 0.0
        for index, difference in enumerate(differences):
            sign = -1.0 if mask & (1 << index) else 1.0
            signed_sum += sign * float(difference)
        permuted = signed_sum / len(differences)
        if alternative == "two-sided":
            extreme += abs(permuted) >= abs(observed) - tolerance
        else:
            extreme += permuted >= observed - tolerance
    return extreme / total


def bootstrap_interval(
    identifier: str, differences: np.ndarray[Any, Any]
) -> tuple[float, float]:
    identifier_seed = int.from_bytes(
        hashlib.sha256(identifier.encode()).digest()[:8], "little"
    )
    rng = np.random.default_rng(ANALYSIS_SEED ^ identifier_seed)
    indices = rng.integers(
        0, len(differences), size=(BOOTSTRAP_SAMPLES, len(differences))
    )
    means = differences[indices].mean(axis=1)
    low, high = np.quantile(means, (0.025, 0.975))
    return float(low), float(high)


def holm_adjust(raw: dict[str, float]) -> dict[str, float]:
    ordered = sorted(raw.items(), key=lambda item: item[1])
    adjusted: dict[str, float] = {}
    running = 0.0
    count = len(ordered)
    for rank, (identifier, value) in enumerate(ordered):
        running = max(running, (count - rank) * value)
        adjusted[identifier] = min(1.0, running)
    return adjusted


def load_matrix(
    results: Path,
) -> tuple[
    dict[str, Any],
    dict[int, dict[str, dict[str, Any]]],
    list[dict[str, Any]],
]:
    protocol = json.loads((results / "protocol.json").read_text())
    matrix: dict[int, dict[str, dict[str, Any]]] = {}
    exclusions: list[dict[str, Any]] = []
    for seed in protocol["seeds"]:
        matrix[seed] = {}
        for treatment in protocol["treatment_order"]:
            run_dir = results / f"seed-{seed}" / treatment
            complete_path = run_dir / "complete.json"
            metrics_path = run_dir / "metrics.jsonl"
            if not complete_path.exists() or not metrics_path.exists():
                failure_path = run_dir / "failure.json"
                failure = (
                    json.loads(failure_path.read_text())
                    if failure_path.exists()
                    else {}
                )
                partial_path = run_dir / "metrics.jsonl.partial"
                partial = (
                    [json.loads(line) for line in partial_path.read_text().splitlines()]
                    if partial_path.exists()
                    else []
                )
                exclusions.append(
                    {
                        "seed": seed,
                        "treatment": treatment,
                        "reason": "invariant_or_incomplete_run",
                        "error": failure.get("error", "missing complete output"),
                        "last_valid_tick": partial[-1]["tick"] if partial else None,
                        "last_valid_population": (
                            partial[-1]["population"] if partial else None
                        ),
                        "last_valid_energy_error": (
                            partial[-1]["energy_error"] if partial else None
                        ),
                    }
                )
                continue
            complete = json.loads(complete_path.read_text())
            if complete["protocol_id"] != protocol["protocol_id"]:
                exclusions.append(
                    {
                        "seed": seed,
                        "treatment": treatment,
                        "reason": "protocol_mismatch",
                        "error": "completed run protocol does not match matrix protocol",
                        "last_valid_tick": None,
                        "last_valid_population": None,
                        "last_valid_energy_error": None,
                    }
                )
                continue
            records = [
                json.loads(line) for line in metrics_path.read_text().splitlines()
            ]
            expected_records = protocol["ticks"] // protocol["recording_interval"] + 1
            if (
                len(records) != expected_records
                or records[-1]["tick"] != protocol["ticks"]
            ):
                exclusions.append(
                    {
                        "seed": seed,
                        "treatment": treatment,
                        "reason": "recording_mismatch",
                        "error": "wrong interval count or final tick",
                        "last_valid_tick": records[-1]["tick"] if records else None,
                        "last_valid_population": (
                            records[-1]["population"] if records else None
                        ),
                        "last_valid_energy_error": (
                            records[-1]["energy_error"] if records else None
                        ),
                    }
                )
                continue
            final = records[-1]
            if not final["energy_ok"] or not final["elements_ok"]:
                exclusions.append(
                    {
                        "seed": seed,
                        "treatment": treatment,
                        "reason": "invariant_failure",
                        "error": "final interval invariant failed",
                        "last_valid_tick": final["tick"],
                        "last_valid_population": final["population"],
                        "last_valid_energy_error": final["energy_error"],
                    }
                )
                continue
            matrix[seed][treatment] = final
    return protocol, matrix, exclusions


def summarize_groups(
    protocol: dict[str, Any], matrix: dict[int, dict[str, dict[str, Any]]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for treatment in protocol["treatment_order"]:
        records = [
            matrix[seed][treatment]
            for seed in protocol["seeds"]
            if treatment in matrix[seed]
        ]
        populations = np.array(
            [record["population"] for record in records], dtype=np.float64
        )
        births = np.array([record["births"] for record in records], dtype=np.float64)
        recurrent_expression = np.array(
            [
                record["recurrent_expression_genetic"]["mean"]
                if record["recurrent_expression_genetic"]["mean"] is not None
                else np.nan
                for record in records
            ],
            dtype=np.float64,
        )
        ambiguous_events = sum(
            record["memory_probe_ambiguous_food_events"] for record in records
        )
        rows.append(
            {
                "treatment": treatment,
                "runs": len(records),
                "population_mean": float(np.mean(populations)),
                "population_sd": float(np.std(populations, ddof=1)),
                "population_min": int(np.min(populations)),
                "population_max": int(np.max(populations)),
                "extinctions": int(np.count_nonzero(populations == 0)),
                "births_mean": float(np.mean(births)),
                "genetic_recurrent_expression_mean": (
                    float(np.nanmean(recurrent_expression))
                    if np.any(np.isfinite(recurrent_expression))
                    else None
                ),
                "brain_energy_mean": float(
                    np.mean([record["brain_energy_spent"] for record in records])
                ),
                "recurrent_brain_energy_mean": float(
                    np.mean(
                        [record["recurrent_brain_energy_spent"] for record in records]
                    )
                ),
                "ambiguous_food_events": int(ambiguous_events),
                "ambiguous_argmax_change_fraction": safe_fraction(
                    sum(
                        record["memory_probe_ambiguous_argmax_changes"]
                        for record in records
                    ),
                    ambiguous_events,
                ),
                "stateful_return_fraction": safe_fraction(
                    sum(
                        record["memory_probe_stateful_return_choices"]
                        for record in records
                    ),
                    ambiguous_events,
                ),
                "zero_state_return_fraction": safe_fraction(
                    sum(
                        record["memory_probe_zero_state_return_choices"]
                        for record in records
                    ),
                    ambiguous_events,
                ),
                "neural_numerical_errors": int(
                    sum(record["neural_numerical_errors"] for record in records)
                ),
            }
        )
    return rows


def primary_analysis(
    protocol: dict[str, Any], matrix: dict[int, dict[str, dict[str, Any]]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw_p: dict[str, float] = {}
    for definition in primary_definitions():
        values: list[float | None] = []
        for seed in protocol["seeds"]:
            try:
                values.append(definition.difference(matrix[seed]))
            except KeyError:
                values.append(None)
        differences = np.array(
            [value for value in values if value is not None], dtype=np.float64
        )
        row: dict[str, Any] = {
            "id": definition.identifier,
            "description": definition.description,
            "alternative": definition.alternative,
            "valid_pairs": len(differences),
            "mean_difference": None,
            "ci_low": None,
            "ci_high": None,
            "raw_p": None,
            "holm_p": None,
            "positive_direction": False,
            "significant": False,
        }
        if len(differences) >= 8:
            row["mean_difference"] = float(np.mean(differences))
            row["ci_low"], row["ci_high"] = bootstrap_interval(
                definition.identifier, differences
            )
            row["raw_p"] = exact_sign_flip_p(differences, definition.alternative)
            row["positive_direction"] = row["mean_difference"] > 0.0
            raw_p[definition.identifier] = row["raw_p"]
        rows.append(row)
    adjusted = holm_adjust(raw_p)
    for row in rows:
        if row["id"] in adjusted:
            row["holm_p"] = adjusted[row["id"]]
            row["significant"] = row["holm_p"] < ALPHA
    return rows


def expression_deciles(results: Path, protocol: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for treatment in ("recurrent", "recurrent_lesion", "recurrent_zero_cost"):
        decile_values: list[list[float]] = [[] for _ in range(10)]
        for seed in protocol["seeds"]:
            state_path = results / f"seed-{seed}" / treatment / "final_state.npz"
            if not state_path.exists():
                continue
            state = np.load(state_path)
            expression = np.asarray(
                state["recurrent_expression_genetic_mean"], dtype=np.float64
            )
            offspring = np.asarray(state["offspring_count"], dtype=np.float64)
            if not len(expression):
                continue
            order = np.argsort(expression, kind="stable")
            deciles = np.minimum(9, np.arange(len(order)) * 10 // len(order))
            for rank, organism_index in enumerate(order):
                decile_values[int(deciles[rank])].append(
                    float(offspring[organism_index])
                )
        for decile, values in enumerate(decile_values):
            rows.append(
                {
                    "treatment": treatment,
                    "expression_decile": decile + 1,
                    "organisms": len(values),
                    "offspring_mean": float(np.mean(values)) if values else None,
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: Any, digits: int = 5) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def write_report(
    results: Path,
    protocol: dict[str, Any],
    groups: list[dict[str, Any]],
    primary: list[dict[str, Any]],
    exclusions: list[dict[str, Any]],
) -> dict[str, Any]:
    required = {row["id"]: row for row in primary}
    memory_claim = all(
        required[identifier]["positive_direction"]
        and required[identifier]["significant"]
        for identifier in ("P3", "P4", "P5", "P6")
    )
    no_numerical_errors = all(row["neural_numerical_errors"] == 0 for row in groups)
    memory_claim = memory_claim and no_numerical_errors

    analysis_path = Path(__file__).resolve()
    analysis_hash = hashlib.sha256(analysis_path.read_bytes()).hexdigest()
    frozen_analysis_hash = protocol["source_hashes"].get(
        "experiments/neuroevolution_stage4/analyze_stage4.py"
    )
    lines = [
        "# Stage 4 endogenous recurrent-memory report",
        "",
        f"Protocol: `{protocol['protocol_id']}`",
        "",
        "**Transparent analysis-loader amendment:** the frozen loader aborted when any preregistered invariant exclusion existed. After the batch, only exclusion handling was repaired so paired tests use available valid seeds as the preregistration specifies. Endpoints, alternatives, thresholds, bootstrap seed/count, sign-flip tests, Holm correction, and decision rules are unchanged.",
        "",
        f"Frozen analyzer hash: `{frozen_analysis_hash}`; executed analyzer hash: `{analysis_hash}`.",
        "",
        "## Primary preregistered tests",
        "",
        "| Test | Valid pairs | Mean difference | 95% bootstrap CI | Raw p | Holm p | Result |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in primary:
        result = (
            "significant, positive"
            if row["significant"] and row["positive_direction"]
            else "not positive/significant"
        )
        lines.append(
            f"| {row['id']} | {row['valid_pairs']} | {fmt(row['mean_difference'])} | "
            f"[{fmt(row['ci_low'])}, {fmt(row['ci_high'])}] | {fmt(row['raw_p'])} | "
            f"{fmt(row['holm_p'])} | {result} |"
        )
    lines.extend(
        [
            "",
            "## Treatment summaries",
            "",
            "| Treatment | Final population mean (range) | Extinctions | Births mean | Genetic recurrent expression | Recurrent energy | Ambiguous events | Argmax change | Stateful return | Zero-state return |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in groups:
        lines.append(
            f"| {row['treatment']} | {row['population_mean']:.1f} "
            f"({row['population_min']}–{row['population_max']}) | {row['extinctions']} | "
            f"{row['births_mean']:.1f} | {fmt(row['genetic_recurrent_expression_mean'], 6)} | "
            f"{row['recurrent_brain_energy_mean']:.3f} | {row['ambiguous_food_events']} | "
            f"{fmt(row['ambiguous_argmax_change_fraction'])} | "
            f"{fmt(row['stateful_return_fraction'])} | "
            f"{fmt(row['zero_state_return_fraction'])} |"
        )
    verdict = (
        "The full preregistered convergence rule is satisfied. This supports evolved ecological memory in this protocol."
        if memory_claim
        else "The full preregistered convergence rule is not satisfied. The result does not support a claim of evolved ecological memory. Individual positive effects remain narrower nonlinear, state-dependence, or exploratory findings."
    )
    lines.extend(["", "## Preregistered exclusions", ""])
    if exclusions:
        lines.extend(
            [
                "| Seed | Treatment | Reason | Last valid tick | Last valid population | Last valid energy error |",
                "|---:|---|---|---:|---:|---:|",
            ]
        )
        for exclusion in exclusions:
            lines.append(
                f"| {exclusion['seed']} | {exclusion['treatment']} | {exclusion['reason']} | "
                f"{fmt(exclusion['last_valid_tick'])} | {fmt(exclusion['last_valid_population'])} | "
                f"{fmt(exclusion['last_valid_energy_error'])} |"
            )
    else:
        lines.append("None.")
    lines.extend(
        [
            "",
            "## Preregistered verdict",
            "",
            verdict,
            "",
            "Extinctions, null effects, adverse effects, invariant status, and neural numerical errors are retained in the tables. No endpoint was optimized by the simulator.",
        ]
    )
    (results / "STAGE4_REPORT.md").write_text("\n".join(lines) + "\n")
    return {
        "protocol_id": protocol["protocol_id"],
        "frozen_analysis_hash": frozen_analysis_hash,
        "executed_analysis_hash": analysis_hash,
        "analysis_loader_amendment": "paired exclusion handling only",
        "exclusions": exclusions,
        "memory_claim_supported": memory_claim,
        "no_neural_numerical_errors": no_numerical_errors,
        "primary": primary,
        "groups": groups,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()

    protocol, matrix, exclusions = load_matrix(args.results)
    groups = summarize_groups(protocol, matrix)
    primary = primary_analysis(protocol, matrix)
    deciles = expression_deciles(args.results, protocol)
    write_csv(args.results / "treatment_summary.csv", groups)
    write_csv(args.results / "primary_tests.csv", primary)
    write_csv(args.results / "expression_deciles.csv", deciles)
    write_csv(args.results / "exclusions.csv", exclusions)
    analysis = write_report(args.results, protocol, groups, primary, exclusions)
    (args.results / "analysis.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n"
    )
    print(args.results / "STAGE4_REPORT.md")


if __name__ == "__main__":
    main()
