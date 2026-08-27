"""Seeded regression fingerprint for the Python tick kernel.

Runs one fixed scenario (matching the bench/perf.py harness configuration)
and produces a strict fingerprint of the final state:

- headline stats (population, births, deaths, attacks, magic casts, ...)
- element totals and dynamic energy error
- SHA-256 over the full organism table (id -> alive, species, position, mass)
- SHA-256 over the full deposit table (position -> batches with exact float
  bits via float.hex, so ANY numeric divergence is detected)

Usage:
    uv run python bench/regress_check.py                # compare to stored
    uv run python bench/regress_check.py --save         # (re)write stored
    uv run python bench/regress_check.py --save --file my.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from organism_sim.config import SimulationConfig
from organism_sim.simulation import Simulation

DEFAULT_FILE = Path(__file__).resolve().parent / "results" / "regress_baseline.json"

SEED = 7
FOUNDERS = 600
TICKS = 1500


def build_config(founders: int = FOUNDERS, seed: int = SEED) -> SimulationConfig:
    """Match bench/perf.py's run_scale configuration exactly."""

    return SimulationConfig(
        founder_count=founders,
        seed=seed,
        audit_every=0,
        founder_archetype_count=min(20, max(8, founders // 40)),
    )


def fingerprint(simulation: Simulation) -> dict[str, object]:
    catalog = simulation.catalog
    organism_rows = []
    for organism_id in sorted(simulation.organisms):
        organism = simulation.organisms[organism_id]
        organism_rows.append(
            (
                organism_id,
                organism.alive,
                organism.species_id,
                organism.position,
                organism.structural_mass(catalog),
                organism.generation,
            )
        )
    organism_repr = repr(tuple(organism_rows))

    deposit_rows = []
    for position in sorted(simulation.world.deposits):
        inventory = simulation.world.deposits[position]
        for molecule_id in sorted(inventory):
            batch = inventory[molecule_id]
            deposit_rows.append((position, molecule_id, batch.count, batch.energy.hex()))
    deposit_repr = repr(tuple(deposit_rows))

    stats = simulation.stats
    dynamic_energy = simulation.total_energy() - simulation.world.generated_energy
    return {
        "seed": SEED,
        "founders": simulation.config.founder_count,
        "ticks": simulation.tick,
        "population": simulation.population,
        "total_organisms_ever": len(simulation.organisms),
        "births": stats.births,
        "deaths": stats.deaths,
        "attacks": stats.attacks,
        "magic_casts": stats.magic_casts,
        "alliances": stats.alliances,
        "colonies": stats.colonies,
        "sexual_reproduction_events": stats.sexual_reproduction_events,
        "asexual_reproduction_events": stats.asexual_reproduction_events,
        "element_totals": list(simulation.current_element_totals()),
        "dynamic_energy": dynamic_energy.hex(),
        "dynamic_energy_error": (dynamic_energy - simulation.initial_energy).hex(),
        "organism_digest": hashlib.sha256(organism_repr.encode()).hexdigest(),
        "deposit_digest": hashlib.sha256(deposit_repr.encode()).hexdigest(),
        "living_ids": sorted(simulation.living_ids),
        "chunks_generated": len(simulation.world.chunks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", action="store_true", help="write fingerprint instead of comparing")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--ticks", type=int, default=TICKS)
    parser.add_argument("--founders", type=int, default=FOUNDERS)
    args = parser.parse_args()

    config = build_config(args.founders)
    start = time.perf_counter()
    simulation = Simulation(config)
    for _ in range(args.ticks):
        simulation.step()
    elapsed = time.perf_counter() - start

    current = fingerprint(simulation)
    print(
        f"tick={current['ticks']} pop={current['population']} "
        f"births={current['births']} deaths={current['deaths']} "
        f"attacks={current['attacks']} magic={current['magic_casts']} "
        f"alliances={current['alliances']} colonies={current['colonies']} "
        f"({elapsed:.1f}s, {args.ticks / elapsed:.1f} ticks/s)"
    )

    if args.save:
        args.file.parent.mkdir(parents=True, exist_ok=True)
        args.file.write_text(json.dumps(current, indent=2, sort_keys=True))
        print(f"saved: {args.file}")
        return 0

    if not args.file.exists():
        print(f"ERROR: no stored fingerprint at {args.file}; run with --save first")
        return 2
    stored = json.loads(args.file.read_text())
    mismatches = [key for key in stored if stored[key] != current.get(key)]
    if mismatches:
        print(f"FINGERPRINT DIVERGENCE in {len(mismatches)} field(s):")
        for key in mismatches:
            print(f"  {key}:\n    stored:  {stored[key]}\n    current: {current.get(key)}")
        return 1
    print("FINGERPRINT MATCH: all fields identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
