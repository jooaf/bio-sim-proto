from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

import numpy as np

from .config import SimulationConfig
from .rust_kernel import (
    RustKernelSimulation,
    config_sha256,
    rust_build_metadata,
    scheduler_metadata,
)

RUST_RECORDING_SCHEMA = 3
COMPOSITION_RECORDING_SCHEMA = 1
DEFAULT_COMPOSITION_INTERVAL = 100
_COMPOSITION_COMPARTMENTS = ("body", "gut", "waste")


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _write_composition_rows(file: Any, snapshot: dict[str, object]) -> None:
    """Stream one sparse JSONL row for each non-empty organism batch."""

    organism_ids = snapshot["organism_id"]
    compartments = snapshot["compartment"]
    molecule_ids = snapshot["molecule_id"]
    counts = snapshot["count"]
    energies = snapshot["chemical_energy"]
    tick = int(snapshot["tick"])
    for organism_id, compartment, molecule_id, count, energy in zip(
        organism_ids,
        compartments,
        molecule_ids,
        counts,
        energies,
        strict=True,
    ):
        compartment_id = int(compartment)
        if not 0 <= compartment_id < len(_COMPOSITION_COMPARTMENTS):
            raise ValueError(f"unknown organism composition compartment: {compartment_id}")
        file.write(
            _json(
                {
                    "tick": tick,
                    "organism_id": int(organism_id),
                    "compartment": _COMPOSITION_COMPARTMENTS[compartment_id],
                    "molecule_id": int(molecule_id),
                    "count": int(count),
                    "chemical_energy": float(energy),
                }
            )
            + "\n"
        )


def run_rust_headless(
    config: SimulationConfig,
    ticks: int,
    *,
    runs_root: Path | None = None,
    progress_every: int = 500,
    record_composition: bool = False,
    composition_interval: int = DEFAULT_COMPOSITION_INTERVAL,
) -> tuple[RustKernelSimulation, Path, float]:
    """Run the native kernel and write its compact research record.

    Metrics are copied across PyO3 only at the configured metrics interval.
    The expensive full state snapshot is copied once, at run completion. This
    preserves coarse FFI calls while retaining a population trajectory and an
    exact final audit/digest.

    When ``record_composition`` is enabled, sparse organism molecule batches
    are sampled at tick zero, every ``composition_interval`` ticks, and the
    final tick. The rows are streamed to JSONL so recording does not retain a
    second copy of the trajectory in memory.
    """

    if composition_interval < 1:
        raise ValueError("composition_interval must be positive")

    root = runs_root or Path(__file__).resolve().parents[2] / "runs"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    run_id = f"{timestamp}-seed{config.seed}-rust-{uuid4().hex[:8]}"
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    started_at = datetime.now(UTC)
    manifest_path = run_dir / "manifest.json"
    manifest: dict[str, Any] = {
        "schema_version": RUST_RECORDING_SCHEMA,
        "run_id": run_id,
        "kernel": "rust",
        "recording_format": "compact-jsonl-npz",
        "seed": config.seed,
        "started_utc": started_at.isoformat(),
        "requested_ticks": ticks,
        "build": rust_build_metadata(),
        "execution": scheduler_metadata(config),
        "config": asdict(config),
        "config_sha256": config_sha256(config),
        "metrics": "metrics.jsonl",
        "season_events": "season_events.jsonl",
        "final_snapshot": "final_state.npz",
        "final_species": "final_species.json",
        "audit": "audit.json",
        "organism_composition_enabled": bool(record_composition),
        "organism_composition_interval": composition_interval if record_composition else None,
        "organism_composition_schema_version": (
            COMPOSITION_RECORDING_SCHEMA if record_composition else None
        ),
        "organism_composition": (
            "organism_composition.jsonl" if record_composition else None
        ),
        "molecule_catalog": "molecule_catalog.json" if record_composition else None,
    }
    manifest_path.write_text(_json(manifest) + "\n", encoding="utf-8")

    simulation = RustKernelSimulation(config)
    if record_composition:
        (run_dir / "molecule_catalog.json").write_text(
            _json(simulation.molecule_catalog()) + "\n", encoding="utf-8"
        )
    interval = max(1, config.recording_metrics_interval)
    progress_every = max(0, progress_every)
    next_progress = progress_every
    started = perf_counter()
    composition_file = (
        (run_dir / "organism_composition.jsonl").open(
            "w", encoding="utf-8", buffering=1
        )
        if record_composition
        else None
    )

    try:
        with (
            (run_dir / "metrics.jsonl").open("w", encoding="utf-8") as metrics_file,
            (run_dir / "season_events.jsonl").open(
                "w", encoding="utf-8"
            ) as season_events_file,
        ):
            recorded_season_events = 0
            next_metrics_tick = interval
            next_composition_tick = composition_interval

            def record_metrics() -> None:
                nonlocal recorded_season_events
                season = simulation.season_state(recorded_season_events)
                row = {
                    "tick": simulation.tick,
                    "population": simulation.population,
                    "living_species": simulation.species_count,
                    **simulation.stats_dict(),
                }
                metrics_file.write(_json(row) + "\n")
                events = season["events"]
                for event in events:
                    season_events_file.write(
                        _json({"enabled": bool(season["enabled"]), **event}) + "\n"
                    )
                recorded_season_events = int(season["event_count"])

            def record_composition_snapshot() -> None:
                if composition_file is not None:
                    _write_composition_rows(
                        composition_file, simulation.organism_composition()
                    )

            record_metrics()
            record_composition_snapshot()
            while simulation.tick < ticks:
                next_tick = ticks
                if simulation.tick < next_metrics_tick:
                    next_tick = min(next_tick, next_metrics_tick)
                if record_composition and simulation.tick < next_composition_tick:
                    next_tick = min(next_tick, next_composition_tick)
                simulation.step(next_tick - simulation.tick)
                if simulation.tick == next_metrics_tick or simulation.tick == ticks:
                    record_metrics()
                    if simulation.tick == next_metrics_tick:
                        next_metrics_tick += interval
                if record_composition and (
                    simulation.tick == next_composition_tick or simulation.tick == ticks
                ):
                    record_composition_snapshot()
                    if simulation.tick == next_composition_tick:
                        next_composition_tick += composition_interval
                if progress_every and simulation.tick >= next_progress:
                    elapsed = perf_counter() - started
                    print(
                        f"tick={simulation.tick} population={simulation.population} "
                        f"species={simulation.species_count} average_tps={simulation.tick / elapsed:.1f}"
                    )
                    next_progress = simulation.tick + progress_every
    finally:
        if composition_file is not None:
            composition_file.close()

    elapsed = perf_counter() - started
    audit = simulation.audit()
    snapshot = simulation.snapshot()
    organisms = snapshot["organisms"]
    deposits = snapshot["deposits"]
    biodeposits = snapshot["biodeposits"]
    byproducts = snapshot["byproducts"]
    bonds = snapshot["bonds"]
    arrays = {
        **{f"organisms_{name}": values for name, values in organisms.items()},
        **{f"deposits_{name}": values for name, values in deposits.items()},
        **{f"biodeposits_{name}": values for name, values in biodeposits.items()},
        **{f"byproducts_{name}": values for name, values in byproducts.items()},
        **{f"bonds_{name}": values for name, values in bonds.items()},
    }
    np.savez_compressed(run_dir / "final_state.npz", **arrays)
    (run_dir / "final_species.json").write_text(
        json.dumps(snapshot["species"], indent=2), encoding="utf-8"
    )
    (run_dir / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    ended_at = datetime.now(UTC)
    manifest.update(
        {
            "ended_utc": ended_at.isoformat(),
            "final_tick": simulation.tick,
            "final_population": simulation.population,
            "final_species_count": simulation.species_count,
            "digest": simulation.digest(),
            "wall_seconds": elapsed,
            "average_ticks_per_second": simulation.tick / elapsed if elapsed else None,
            "elements_ok": bool(audit["elements_ok"]),
            "energy_ok": bool(audit["energy_ok"]),
            "final_season": simulation.season_state(recorded_season_events),
            "effective_parallel_workers": snapshot["effective_parallel_workers"],
        }
    )
    manifest_path.write_text(_json(manifest) + "\n", encoding="utf-8")
    return simulation, run_dir, elapsed
