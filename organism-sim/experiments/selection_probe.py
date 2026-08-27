"""Headless selection-diagnostics probe.

Runs the Simulation engine in-process (no recording overhead) and prints a
per-interval table describing population, energy flow, mortality, reproduction
blocks, and standing trait variation. Used to diagnose whether natural
selection and competition are functioning.

Usage:
    uv run python experiments/selection_probe.py [--ticks N] [--seed S] [--set field=value ...]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from organism_sim.config import SimulationConfig  # noqa: E402
from organism_sim.simulation import Simulation  # noqa: E402

REPORT_TRAITS = ("digestion", "assimilation", "speed", "sight", "move_efficiency", "fertility", "asexual", "basal")


def parse_overrides(raw: list[str]) -> dict[str, object]:
    overrides: dict[str, object] = {}
    for item in raw:
        key, _, value = item.partition("=")
        field_type = type(getattr(SimulationConfig(), key, None))
        if field_type is bool:
            overrides[key] = value.lower() in {"1", "true", "yes", "on"}
        elif field_type is int:
            overrides[key] = int(value)
        elif field_type is float:
            overrides[key] = float(value)
        else:
            overrides[key] = value
    return overrides


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticks", type=int, default=3000)
    parser.add_argument("--interval", type=int, default=250)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--set", action="append", default=[])
    args = parser.parse_args()

    config = SimulationConfig(seed=args.seed, **parse_overrides(args.set))
    simulation = Simulation(config)
    header = (
        "tick pop births deaths b-d | depositE organismE heatE | "
        "attr pred fire | attempts blocks probfail placefail | gens | traits(dig,assim,spd,sight,meff,fert,asex,basal)"
    )
    print(header)

    def report() -> None:
        deaths = Counter(event_causes.get(oid, "unknown") for death_tick, oid in death_log if death_tick > last_report)
        deposit_energy = sum(
            batch.energy
            for inventory in simulation.world.deposits.values()
            for batch in inventory.values()
        )
        organism_energy = sum(
            simulation.organisms[oid].chemical_energy() for oid in simulation.living_ids
        )
        stats = simulation.stats
        living = [simulation.organisms[oid] for oid in simulation.living_ids]
        generations = [o.generation for o in living] or [0]
        trait_bits = []
        for trait in REPORT_TRAITS:
            values = [getattr(o.phenotype, trait) for o in living]
            trait_bits.append(f"{sum(values) / len(values):.3f}" if values else "n/a")
        print(
            f"{simulation.tick:5d} {simulation.population:4d} {stats.births:4d} {stats.deaths:4d} "
            f"{stats.births - stats.deaths:+5d} | "
            f"{deposit_energy:11.3e} {organism_energy:11.3e} {simulation.world.total_heat():11.3e} | "
            f"{deaths.get('attrition', 0):4d} {deaths.get('predation', 0):4d} {deaths.get('fire', 0):3d} | "
            f"{stats.reproduction_attempts:6d} {stats.reproduction_resource_blocks:6d} "
            f"{stats.reproduction_probability_failures:6d} {stats.reproduction_placement_failures:5d} | "
            f"{min(generations)}-{max(generations)} | " + ",".join(trait_bits)
        )

    event_causes: dict[int, str] = {}
    death_log: list[tuple[int, int]] = []
    last_report = 0

    # Patch _kill to record causes without changing dynamics.
    original_kill = simulation._kill

    def traced_kill(organism, cause: str) -> None:
        before = len(simulation.living_ids)
        original_kill(organism, cause)
        if len(simulation.living_ids) < before:
            event_causes[organism.organism_id] = cause
            death_log.append((simulation.tick, organism.organism_id))

    simulation._kill = traced_kill  # type: ignore[method-assign]

    report()
    for tick in range(1, args.ticks + 1):
        simulation.step()
        if tick % args.interval == 0:
            report()
            last_report = tick
    simulation.audit()
    print(f"audit_error={simulation.last_audit_error:.3e}")


if __name__ == "__main__":
    main()
