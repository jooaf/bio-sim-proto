from organism_sim import Simulation, SimulationConfig


def behavior_simulation() -> Simulation:
    return Simulation(
        SimulationConfig(
            seed=83,
            width=24,
            height=24,
            founder_count=1,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            audit_every=0,
        )
    )


def test_directed_movement_reduces_target_distance() -> None:
    simulation = behavior_simulation()
    organism = next(iter(simulation.organisms.values()))
    target = (organism.position[0] + 5, organism.position[1] + 3)
    before = simulation.world.distance(organism.position, target)

    moved = simulation._move(organism, target)

    assert moved
    assert simulation.world.distance(organism.position, target) < before


def test_heat_must_be_reached_before_it_can_be_absorbed() -> None:
    simulation = behavior_simulation()
    organism = next(iter(simulation.organisms.values()))
    target = (organism.position[0] + 4, organism.position[1])
    simulation.world.clear_heat()
    simulation.world.add_heat(target, 10.0)
    mana_before = organism.mana
    distance_before = simulation.world.distance(organism.position, target)

    simulation._seek_or_absorb_heat(organism, target)

    assert organism.mana == mana_before
    assert simulation.world.distance(organism.position, target) < distance_before
    assert simulation.world.heat_at(target) == 10.0


def test_fleeing_increases_distance_from_threat() -> None:
    simulation = behavior_simulation()
    organism = next(iter(simulation.organisms.values()))
    threat = (organism.position[0] + 4, organism.position[1] + 2)
    before = simulation.world.distance(organism.position, threat)

    moved = simulation._move_away(organism, threat)

    assert moved
    assert simulation.world.distance(organism.position, threat) > before
