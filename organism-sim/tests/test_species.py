from organism_sim import Simulation, SimulationConfig
from organism_sim.genetics import Genome


def test_founder_archetype_count_controls_initial_species() -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=101,
            width=32,
            height=32,
            founder_count=24,
            founder_archetype_count=6,
            element_count=4,
            molecule_count=12,
            initial_deposits=40,
            audit_every=0,
        )
    )

    assert len(simulation.species) == 6
    assert {species.origin for species in simulation.species.values()} == {"founder"}
    assert all(species.population > 0 for species in simulation.species.values())
    assert sum(species.population for species in simulation.species.values()) == simulation.population


def test_new_species_tracks_mutation_or_sexual_origin() -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=103,
            width=16,
            height=16,
            founder_count=2,
            founder_archetype_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            species_distance_threshold=0.0,
            audit_every=0,
        )
    )
    parents = tuple(simulation.organisms.values())[:2]
    mutation_genome = Genome.random(simulation._claim_genome_id(), simulation.rng)
    mutation_species_id = simulation._assign_species(
        mutation_genome,
        origin="mutation",
        parent_species_ids=(parents[0].species_id,),
        founder_organism_id=999,
    )
    sexual_genome = Genome.random(simulation._claim_genome_id(), simulation.rng)
    sexual_species_id = simulation._assign_species(
        sexual_genome,
        origin="sexual",
        parent_species_ids=tuple(sorted({parent.species_id for parent in parents})),
        founder_organism_id=1000,
    )

    mutation_species = simulation.species[mutation_species_id]
    sexual_species = simulation.species[sexual_species_id]
    assert mutation_species.origin == "mutation"
    assert mutation_species.parent_species_ids == (parents[0].species_id,)
    assert mutation_species.founder_organism_id == 999
    assert sexual_species.origin == "sexual"
    assert sexual_species.parent_species_ids == tuple(sorted({parent.species_id for parent in parents}))
    assert sexual_species.founder_organism_id == 1000
