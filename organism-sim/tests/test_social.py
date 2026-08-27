from dataclasses import replace

from organism_sim import Simulation, SimulationConfig


def test_relaxed_default_specialist_thresholds_allow_colony_formation() -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=109,
            width=16,
            height=16,
            founder_count=2,
            founder_archetype_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            alliance_probability=1.0,
            audit_every=0,
        )
    )
    first, second = tuple(simulation.organisms.values())[:2]
    first.phenotype = replace(first.phenotype, sexual=0.2, asexual=0.4)
    second.phenotype = replace(second.phenotype, sexual=0.2, asexual=0.4)

    simulation._attempt_alliance(first, second)

    assert len(simulation.alliances) == 1
    assert len(simulation.colonies) == 1
    assert first.colony_id == second.colony_id
