"""Run the frozen Stage 4 endogenous-neuroevolution experiment matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from organism_sim.config import BehaviorModel, SimulationConfig
from organism_sim.rust_kernel import RustKernelSimulation

SEEDS = (101, 211, 307, 401, 503, 601, 701, 809, 907, 1009, 1103, 1201)
TREATMENT_ORDER = (
    "legacy_control",
    "linear_priors",
    "linear_random",
    "recurrent",
    "recurrent_lesion",
    "recurrent_zero_cost",
)
TICKS = 4_000
INTERVAL = 250
FOUNDERS = 300
ARCHETYPES = 20
SOURCE_PATHS = (
    "rust/Cargo.toml",
    "rust/src/behavior/mod.rs",
    "rust/src/behavior/intent.rs",
    "rust/src/behavior/legacy.rs",
    "rust/src/behavior/neural.rs",
    "rust/src/behavior/observation.rs",
    "rust/src/chemistry.rs",
    "rust/src/config.rs",
    "rust/src/entities.rs",
    "rust/src/genetics.rs",
    "rust/src/lib.rs",
    "rust/src/rng.rs",
    "rust/src/world.rs",
    "src/organism_sim/config.py",
    "src/organism_sim/rust_kernel.py",
    "experiments/neuroevolution_stage4/PREREGISTRATION.md",
    "experiments/neuroevolution_stage4/run_stage4.py",
    "experiments/neuroevolution_stage4/analyze_stage4.py",
)


def treatment_config(label: str, seed: int) -> SimulationConfig:
    common: dict[str, Any] = {
        "seed": seed,
        "founder_count": FOUNDERS,
        "founder_archetype_count": ARCHETYPES,
        "audit_every": 0,
    }
    if label == "legacy_control":
        return SimulationConfig(
            behavior_model=BehaviorModel.LEGACY_LINEAR_MACRO_V1,
            **common,
        )
    if label == "linear_priors":
        return SimulationConfig(
            behavior_model=BehaviorModel.LINEAR_INTENT_V2,
            v2_founder_priors_enabled=True,
            **common,
        )
    if label == "linear_random":
        return SimulationConfig(
            behavior_model=BehaviorModel.LINEAR_INTENT_V2,
            v2_founder_priors_enabled=False,
            **common,
        )
    if label == "recurrent":
        return SimulationConfig(
            behavior_model=BehaviorModel.RECURRENT_INTENT_V2,
            memory_probe_enabled=True,
            **common,
        )
    if label == "recurrent_lesion":
        return SimulationConfig(
            behavior_model=BehaviorModel.RECURRENT_INTENT_V2,
            recurrent_state_lesion=True,
            memory_probe_enabled=True,
            **common,
        )
    if label == "recurrent_zero_cost":
        return SimulationConfig(
            behavior_model=BehaviorModel.RECURRENT_INTENT_V2,
            memory_probe_enabled=True,
            brain_recurrent_cost=0.0,
            **common,
        )
    raise ValueError(f"unknown treatment: {label}")


def source_fingerprint() -> tuple[str, dict[str, str]]:
    hashes: dict[str, str] = {}
    combined = hashlib.sha256()
    for relative in SOURCE_PATHS:
        data = (ROOT / relative).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        hashes[relative] = digest
        combined.update(relative.encode())
        combined.update(b"\0")
        combined.update(bytes.fromhex(digest))
    return combined.hexdigest(), hashes


def protocol_document() -> dict[str, Any]:
    source_digest, source_hashes = source_fingerprint()
    treatments = {
        label: asdict(treatment_config(label, SEEDS[0])) | {"seed": "varies"}
        for label in TREATMENT_ORDER
    }
    payload: dict[str, Any] = {
        "protocol_version": 3,
        "source_fingerprint": source_digest,
        "source_hashes": source_hashes,
        "seeds": list(SEEDS),
        "treatment_order": list(TREATMENT_ORDER),
        "ticks": TICKS,
        "recording_interval": INTERVAL,
        "founders": FOUNDERS,
        "founder_archetypes": ARCHETYPES,
        "treatments": treatments,
        "expected_schemas": {
            "legacy_control": {"observation": 1, "intent": 1, "brain": 0},
            "linear_priors": {"observation": 2, "intent": 2, "brain": 1},
            "linear_random": {"observation": 2, "intent": 2, "brain": 1},
            "recurrent": {"observation": 2, "intent": 2, "brain": 1},
            "recurrent_lesion": {"observation": 2, "intent": 2, "brain": 1},
            "recurrent_zero_cost": {"observation": 2, "intent": 2, "brain": 1},
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["protocol_id"] = hashlib.sha256(canonical).hexdigest()
    return payload


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def finite_float(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"non-finite metric: {result}")
    return result


def distribution(values: Any) -> dict[str, float | None]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return {"mean": None, "q10": None, "median": None, "q90": None, "max": None}
    if not np.all(np.isfinite(array)):
        raise ValueError("non-finite organism distribution")
    quantiles = np.quantile(array, (0.1, 0.5, 0.9))
    return {
        "mean": float(np.mean(array)),
        "q10": float(quantiles[0]),
        "median": float(quantiles[1]),
        "q90": float(quantiles[2]),
        "max": float(np.max(array)),
    }


def interval_record(
    simulation: RustKernelSimulation, treatment: str, seed: int
) -> dict[str, Any]:
    snapshot = simulation.snapshot()
    organisms = snapshot["organisms"]
    stats = snapshot["stats"]
    audit = simulation.audit()
    if not audit["energy_ok"] or not audit["elements_ok"]:
        raise RuntimeError(
            f"invariant failure at tick {simulation.tick}: "
            f"energy_ok={audit['energy_ok']} elements_ok={audit['elements_ok']}"
        )

    population = simulation.population
    states = np.asarray(organisms["neural_state"], dtype=np.float64)
    state_l1 = (
        np.sum(np.abs(states.reshape(population, 8)), axis=1)
        if population and states.size
        else np.empty(0, dtype=np.float64)
    )
    lineages = np.asarray(organisms["lineage_id"], dtype=np.int64)
    if lineages.size:
        _, lineage_counts = np.unique(lineages, return_counts=True)
        lineage_largest_fraction = float(np.max(lineage_counts) / lineages.size)
        lineage_simpson = float(np.sum((lineage_counts / lineages.size) ** 2))
    else:
        lineage_largest_fraction = 0.0
        lineage_simpson = 0.0

    ages = simulation.tick - np.asarray(organisms["birth_tick"], dtype=np.int64)
    total_brain = finite_float(stats["brain_energy_spent"])
    hidden_brain = finite_float(stats["hidden_brain_energy_spent"])
    recurrent_brain = finite_float(stats["recurrent_brain_energy_spent"])
    record = {
        "treatment": treatment,
        "seed": seed,
        "tick": simulation.tick,
        "population": population,
        "species_count": simulation.species_count,
        "digest": simulation.digest(),
        "births": int(stats["births"]),
        "deaths": int(stats["deaths"]),
        "successful_reproductions": int(stats["successful_reproductions"]),
        "asexual_reproduction_events": int(stats["asexual_reproduction_events"]),
        "sexual_reproduction_events": int(stats["sexual_reproduction_events"]),
        "intent_counts": [int(value) for value in stats["v2_intent_counts"]],
        "intent_failures": int(stats["v2_intent_failures"]),
        "move_intents": int(stats["v2_intent_counts"][1]),
        "brain_energy_spent": total_brain,
        "base_brain_energy_spent": total_brain - hidden_brain - recurrent_brain,
        "hidden_brain_energy_spent": hidden_brain,
        "recurrent_brain_energy_spent": recurrent_brain,
        "neural_numerical_errors": int(stats["neural_numerical_errors"]),
        "memory_probe_decisions": int(stats["memory_probe_decisions"]),
        "memory_probe_state_l1_sum": finite_float(stats["memory_probe_state_l1_sum"]),
        "memory_probe_argmax_changes": int(stats["memory_probe_argmax_changes"]),
        "memory_probe_ambiguous_food_events": int(
            stats["memory_probe_ambiguous_food_events"]
        ),
        "memory_probe_ambiguous_argmax_changes": int(
            stats["memory_probe_ambiguous_argmax_changes"]
        ),
        "memory_probe_stateful_return_choices": int(
            stats["memory_probe_stateful_return_choices"]
        ),
        "memory_probe_zero_state_return_choices": int(
            stats["memory_probe_zero_state_return_choices"]
        ),
        "energy": distribution(organisms["energy"]),
        "age": distribution(ages),
        "generation": distribution(organisms["generation"]),
        "offspring_count": distribution(organisms["offspring_count"]),
        "hidden_expression": distribution(organisms["hidden_expression_mean"]),
        "recurrent_expression": distribution(organisms["recurrent_expression_mean"]),
        "retention": distribution(organisms["retention_mean"]),
        "hidden_expression_genetic": distribution(
            organisms["hidden_expression_genetic_mean"]
        ),
        "recurrent_expression_genetic": distribution(
            organisms["recurrent_expression_genetic_mean"]
        ),
        "recurrent_expression_genetic_spread": distribution(
            organisms["recurrent_expression_genetic_spread_mean"]
        ),
        "retention_genetic": distribution(organisms["retention_genetic_mean"]),
        "state_l1": distribution(state_l1),
        "lineage_largest_fraction": lineage_largest_fraction,
        "lineage_simpson": lineage_simpson,
        "energy_error": finite_float(audit["energy_error"]),
        "energy_ok": bool(audit["energy_ok"]),
        "elements_ok": bool(audit["elements_ok"]),
    }
    return record


def final_columns(snapshot: dict[str, Any]) -> dict[str, np.ndarray[Any, Any]]:
    organisms = snapshot["organisms"]
    names = (
        "id",
        "species_id",
        "energy",
        "generation",
        "lineage_id",
        "birth_tick",
        "decision_count",
        "offspring_count",
        "brain_energy_spent",
        "hidden_expression_mean",
        "recurrent_expression_mean",
        "retention_mean",
        "hidden_expression_genetic_mean",
        "recurrent_expression_genetic_mean",
        "recurrent_expression_genetic_spread_mean",
        "retention_genetic_mean",
        "neural_numerical_errors",
        "neural_state",
    )
    return {name: np.asarray(organisms[name]) for name in names}


def run_one(
    output_root: Path, protocol: dict[str, Any], treatment: str, seed: int
) -> str:
    run_dir = output_root / f"seed-{seed}" / treatment
    run_dir.mkdir(parents=True, exist_ok=True)
    complete_path = run_dir / "complete.json"
    if complete_path.exists():
        complete = json.loads(complete_path.read_text())
        if complete.get("protocol_id") != protocol["protocol_id"]:
            raise RuntimeError(f"protocol mismatch in completed run: {run_dir}")
        return "skipped"

    config = treatment_config(treatment, seed)
    manifest = {
        "protocol_id": protocol["protocol_id"],
        "source_fingerprint": protocol["source_fingerprint"],
        "treatment": treatment,
        "seed": seed,
        "config": asdict(config),
        "status": "running",
    }
    atomic_json(run_dir / "manifest.json", manifest)
    metrics_temporary = run_dir / "metrics.jsonl.partial"
    started = time.perf_counter()
    try:
        simulation = RustKernelSimulation(config)
        metadata = simulation.snapshot()
        expected = protocol["expected_schemas"][treatment]
        for key, expected_value in (
            ("observation_schema_version", expected["observation"]),
            ("intent_schema_version", expected["intent"]),
            ("brain_schema_version", expected["brain"]),
        ):
            if int(metadata[key]) != expected_value:
                raise RuntimeError(f"schema mismatch for {key}: {metadata[key]}")

        with metrics_temporary.open("w") as metrics_file:
            metrics_file.write(
                json.dumps(interval_record(simulation, treatment, seed)) + "\n"
            )
            for target_tick in range(INTERVAL, TICKS + 1, INTERVAL):
                simulation.step(target_tick - simulation.tick)
                record = interval_record(simulation, treatment, seed)
                metrics_file.write(json.dumps(record) + "\n")
                metrics_file.flush()

        final_snapshot = simulation.snapshot()
        npz_temporary = run_dir / "final_state.npz.partial"
        with npz_temporary.open("wb") as output:
            np.savez_compressed(output, **final_columns(final_snapshot))
        os.replace(npz_temporary, run_dir / "final_state.npz")
        os.replace(metrics_temporary, run_dir / "metrics.jsonl")
        elapsed = time.perf_counter() - started
        final_record = interval_record(simulation, treatment, seed)
        complete = {
            "protocol_id": protocol["protocol_id"],
            "source_fingerprint": protocol["source_fingerprint"],
            "treatment": treatment,
            "seed": seed,
            "status": "complete",
            "wall_seconds": elapsed,
            "final_tick": simulation.tick,
            "final_population": simulation.population,
            "final_digest": simulation.digest(),
            "energy_ok": final_record["energy_ok"],
            "elements_ok": final_record["elements_ok"],
            "neural_numerical_errors": final_record["neural_numerical_errors"],
        }
        atomic_json(complete_path, complete)
        failure = run_dir / "failure.json"
        if failure.exists():
            failure.unlink()
        return "complete"
    except Exception as error:
        atomic_json(
            run_dir / "failure.json",
            {
                "protocol_id": protocol["protocol_id"],
                "treatment": treatment,
                "seed": seed,
                "status": "failed",
                "error": repr(error),
                "traceback": traceback.format_exc(),
            },
        )
        raise


def select_values(
    raw: str | None, allowed: tuple[Any, ...], converter: Any
) -> list[Any]:
    if raw is None:
        return list(allowed)
    selected = [converter(value.strip()) for value in raw.split(",") if value.strip()]
    unknown = [value for value in selected if value not in allowed]
    if unknown:
        raise ValueError(f"values outside frozen protocol: {unknown}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "experiment_results" / "neuroevolution_stage4_v3",
    )
    parser.add_argument("--seeds", help="comma-separated frozen seed subset")
    parser.add_argument("--treatments", help="comma-separated frozen treatment subset")
    parser.add_argument("--max-runs", type=int, default=None)
    args = parser.parse_args()

    seeds = select_values(args.seeds, SEEDS, int)
    treatments = select_values(args.treatments, TREATMENT_ORDER, str)
    protocol = protocol_document()
    args.output.mkdir(parents=True, exist_ok=True)
    protocol_path = args.output / "protocol.json"
    if protocol_path.exists():
        existing = json.loads(protocol_path.read_text())
        if existing != protocol:
            raise RuntimeError(
                "frozen protocol/source mismatch; use a new output directory"
            )
    else:
        atomic_json(protocol_path, protocol)

    run_count = 0
    failures = 0
    for seed in seeds:
        for treatment in treatments:
            if args.max_runs is not None and run_count >= args.max_runs:
                print(f"stopped after max-runs={args.max_runs}", flush=True)
                return
            run_count += 1
            print(f"[{run_count}] seed={seed} treatment={treatment}", flush=True)
            try:
                status = run_one(args.output, protocol, treatment, seed)
                print(f"  {status}", flush=True)
            except Exception as error:  # noqa: BLE001 - preserve all failed replicates
                failures += 1
                print(f"  FAILED: {error}", file=sys.stderr, flush=True)

    if failures:
        raise SystemExit(f"{failures} Stage 4 runs failed")


if __name__ == "__main__":
    main()
