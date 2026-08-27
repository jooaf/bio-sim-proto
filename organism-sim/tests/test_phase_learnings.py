"""Tests for observables and controls ported from bio-sim-proto phase 0/1."""

import sqlite3
from dataclasses import replace
from pathlib import Path

from organism_sim import Simulation, SimulationConfig
from organism_sim.chemistry import MoleculeBatch
from organism_sim.recording import SCHEMA_VERSION, RunRecorder


def small_config(**changes) -> SimulationConfig:
    values = {
        "seed": 211,
        "width": 16,
        "height": 16,
        "founder_count": 2,
        "element_count": 4,
        "molecule_count": 12,
        "initial_deposits": 20,
        "audit_every": 0,
    }
    values.update(changes)
    return SimulationConfig(**values)


def limiting_parent(simulation: Simulation):
    """A parent holding one unit of one molecule that a 40% split cannot share."""

    parent = next(iter(simulation.organisms.values()))
    molecule = simulation.catalog.molecules[0]
    parent.phenotype = replace(parent.phenotype, reproduction_fraction=0.4)
    parent.body = {0: MoleculeBatch(0, 1, molecule.energy_capacity)}
    parent.invalidate_body_cache()
    return parent


def test_matter_blocks_are_attributed_to_the_limiting_molecule(monkeypatch) -> None:
    simulation = Simulation(small_config(asexual_probability_floor=1.0))
    parent = limiting_parent(simulation)
    monkeypatch.setattr(simulation, "_preview_reproductive_body", lambda parents, phenotype: {})

    simulation._attempt_reproduction(parent, None)

    assert simulation.stats.reproduction_body_matter_blocks == 1
    assert simulation.stats.reproduction_matter_blocks_by_molecule == {0: 1}


def test_matter_block_with_empty_bodies_records_no_molecule(monkeypatch) -> None:
    simulation = Simulation(small_config(asexual_probability_floor=1.0))
    parent = next(iter(simulation.organisms.values()))
    parent.body = {}
    parent.invalidate_body_cache()
    monkeypatch.setattr(simulation, "_preview_reproductive_body", lambda parents, phenotype: {})

    simulation._attempt_reproduction(parent, None)

    assert simulation.stats.reproduction_body_matter_blocks == 1
    assert simulation.stats.reproduction_matter_blocks_by_molecule == {}


def test_matter_blocks_table_accumulates_cumulative_counters(tmp_path: Path) -> None:
    simulation = Simulation(
        small_config(
            seed=223,
            asexual_probability_floor=1.0,
            recording_metrics_interval=1,
        )
    )
    recorder = RunRecorder(simulation, source="test", runs_root=tmp_path)
    simulation._record_matter_block((limiting_parent(simulation),))
    simulation.tick = 1
    recorder.record_tick(simulation)
    simulation._record_matter_block((limiting_parent(simulation),))
    simulation.tick = 2
    recorder.record_tick(simulation)
    recorder.close(simulation)

    with sqlite3.connect(recorder.database_path) as database:
        assert database.execute("SELECT COUNT(*) FROM matter_blocks").fetchone()[0] >= 1
        latest = database.execute(
            "SELECT molecule_id, blocked_attempts FROM matter_blocks ORDER BY tick DESC LIMIT 1"
        ).fetchone()
        assert latest[1] == 2
        assert SCHEMA_VERSION >= 5


def test_deposit_match_ecology_sets_founder_demand_weights() -> None:
    matched = Simulation(small_config(seed=227, deposit_match_ecology=True))
    assert matched.world.molecule_weights is not None
    assert abs(sum(matched.world.molecule_weights) - 1.0) < 1e-12
    total_units = sum(
        batch.count
        for organism_id in matched.living_ids
        for batch in matched.organisms[organism_id].body.values()
    )
    assert total_units > 0
    # Zero-weight molecules never present in founder bodies.
    used = {
        molecule_id
        for organism_id in matched.living_ids
        for molecule_id in matched.organisms[organism_id].body
    }
    assert all(matched.world.molecule_weights[molecule_id] > 0.0 for molecule_id in used)

    unmatched = Simulation(small_config(seed=227, deposit_match_ecology=False))
    assert unmatched.world.molecule_weights is None


def test_weighted_chunks_draw_only_demand_molecules() -> None:
    simulation = Simulation(small_config(seed=229, deposit_match_ecology=True))
    simulation.world.molecule_weights = tuple(
        1.0 if molecule_id == 3 else 0.0 for molecule_id in range(12)
    )
    chunk = simulation.world.ensure_chunk(50, 50)
    positions = chunk.deposit_positions
    assert positions
    for position in positions:
        for molecule_id in simulation.world.deposits[position]:
            assert molecule_id == 3


def test_mutation_multiplier_reference_is_preserved_by_default() -> None:
    # Phase 0 Goldilocks: the reference multiplier is the operating point;
    # the default must stay exactly at 1.0 so profiles inherit it.
    assert SimulationConfig().mutation_multiplier == 1.0
    config = replace(SimulationConfig(), mutation_multiplier=1.0)
    config.validate()
