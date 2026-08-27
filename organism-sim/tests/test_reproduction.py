from dataclasses import replace

from organism_sim import Simulation, SimulationConfig
from organism_sim.chemistry import MoleculeBatch


def test_reproduction_resource_block_causes_are_counted(monkeypatch) -> None:
    mate_simulation = Simulation(
        SimulationConfig(
            seed=37,
            width=16,
            height=16,
            founder_count=2,
            founder_archetype_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            audit_every=0,
        )
    )
    first, unready_mate = tuple(mate_simulation.organisms.values())[:2]
    mate_simulation._attempt_reproduction(first, unready_mate)
    assert mate_simulation.stats.reproduction_mate_readiness_blocks == 1

    energy_simulation = Simulation(
        SimulationConfig(
            seed=38,
            width=16,
            height=16,
            founder_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            audit_every=0,
        )
    )
    energy_parent = next(iter(energy_simulation.organisms.values()))
    for batch in energy_parent.body.values():
        batch.energy = 0.0
    energy_simulation._attempt_reproduction(energy_parent, None)
    assert energy_simulation.stats.reproduction_energy_blocks == 1

    matter_simulation = Simulation(
        SimulationConfig(
            seed=39,
            width=16,
            height=16,
            founder_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            asexual_probability_floor=1.0,
            audit_every=0,
        )
    )
    matter_parent = next(iter(matter_simulation.organisms.values()))
    monkeypatch.setattr(matter_simulation, "_preview_reproductive_body", lambda parents, phenotype: {})
    matter_simulation._attempt_reproduction(matter_parent, None)
    assert matter_simulation.stats.reproduction_body_matter_blocks == 1

    stats = (
        mate_simulation.stats,
        energy_simulation.stats,
        matter_simulation.stats,
    )
    assert all(
        item.reproduction_resource_blocks
        == item.reproduction_mate_readiness_blocks
        + item.reproduction_energy_blocks
        + item.reproduction_body_matter_blocks
        for item in stats
    )


def test_reproduction_attempt_energy_is_not_refunded(monkeypatch) -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=41,
            width=24,
            height=24,
            founder_count=12,
            element_count=5,
            molecule_count=18,
            initial_deposits=80,
            audit_every=0,
        )
    )
    parent = next(organism for organism in simulation.organisms.values() if organism.alive)
    before_energy = parent.chemical_energy()
    before_heat = simulation.world.total_heat()

    monkeypatch.setattr(simulation, "_find_child_position", lambda child, parents: None)
    simulation._attempt_reproduction(parent, None)

    assert parent.chemical_energy() < before_energy
    assert simulation.world.total_heat() > before_heat
    simulation.audit()


def test_reproductive_preview_handles_tied_molecule_batches() -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=43,
            width=16,
            height=16,
            founder_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            audit_every=0,
        )
    )
    parent = next(iter(simulation.organisms.values()))
    molecule = simulation.catalog.molecules[0]
    parent.body = {0: MoleculeBatch(0, 2, molecule.energy_capacity * 2)}

    preview = simulation._preview_reproductive_body((parent, parent), parent.phenotype)

    assert preview[0].count == 1


def test_asexual_rate_changes_reproduction_cooldown() -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=47,
            width=16,
            height=16,
            founder_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            audit_every=0,
        )
    )
    organism = next(iter(simulation.organisms.values()))
    organism.phenotype = replace(organism.phenotype, maturity_age=1000, asexual_rate=4.0)
    fast = simulation._reproduction_cooldown_ticks(organism, asexual=True)
    organism.phenotype = replace(organism.phenotype, asexual_rate=0.25)
    slow = simulation._reproduction_cooldown_ticks(organism, asexual=True)

    assert fast == 38
    assert slow == 600
    assert fast < simulation._reproduction_cooldown_ticks(organism, asexual=False) < slow


def test_maturity_multiplier_makes_organisms_ready_earlier() -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=51,
            width=16,
            height=16,
            founder_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            maturity_age_multiplier=0.5,
            audit_every=0,
        )
    )
    organism = next(iter(simulation.organisms.values()))
    organism.phenotype = replace(organism.phenotype, maturity_age=100)
    simulation.tick = 49
    assert not simulation._is_reproductively_ready(organism)
    simulation.tick = 50
    assert simulation._is_reproductively_ready(organism)


def test_asexual_probability_floor_guarantees_attempt_success_before_placement(monkeypatch) -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=53,
            width=16,
            height=16,
            founder_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            asexual_probability_floor=1.0,
            audit_every=0,
        )
    )
    organism = next(iter(simulation.organisms.values()))
    next_genome_id = simulation._next_genome_id
    monkeypatch.setattr(simulation, "_find_child_position", lambda child, parents: None)

    simulation._attempt_reproduction(organism, None)

    assert simulation._next_genome_id > next_genome_id


def test_sexual_probability_floor_can_be_enabled_and_disabled() -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=57,
            width=16,
            height=16,
            founder_count=2,
            founder_archetype_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            sexual_probability_floor_enabled=True,
            sexual_probability_floor=0.2,
            audit_every=0,
        )
    )
    first, second = tuple(simulation.organisms.values())[:2]
    first.phenotype = replace(first.phenotype, fertility=0.01, sexual=0.01)
    second.phenotype = replace(second.phenotype, fertility=0.01, sexual=0.01)

    assert simulation._sexual_success_probability(first, second) == 0.2
    simulation.config.sexual_probability_floor_enabled = False
    assert simulation._sexual_success_probability(first, second) < 0.2


def test_mate_selection_does_not_require_sexual_propensity_to_exceed_asexual() -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=58,
            width=16,
            height=16,
            founder_count=2,
            founder_archetype_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            audit_every=0,
        )
    )
    first, second = tuple(simulation.organisms.values())[:2]
    first.phenotype = replace(first.phenotype, asexual=0.9, sexual=0.4, maturity_age=1)
    second.phenotype = replace(second.phenotype, asexual=0.9, sexual=0.4, maturity_age=1)
    simulation.tick = 2

    assert simulation._best_mate(first, [second]) is second


def test_unique_sexual_parents_and_events_are_tracked() -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=59,
            width=16,
            height=16,
            founder_count=3,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            audit_every=0,
        )
    )
    first, second = tuple(simulation.organisms.values())[:2]

    simulation._record_reproduction_event((first, second))
    simulation._record_reproduction_event((first, second))

    assert simulation.stats.sexual_reproduction_events == 2
    assert simulation.sexual_parent_ids == {first.organism_id, second.organism_id}
    assert simulation.living_sexual_parent_count == 2
