from organism_sim import Simulation, SimulationConfig


def small_config(seed: int = 11) -> SimulationConfig:
    return SimulationConfig(
        seed=seed,
        width=32,
        height=32,
        founder_count=30,
        element_count=6,
        molecule_count=24,
        initial_deposits=240,
        audit_every=5,
    )


def test_matter_and_energy_are_conserved() -> None:
    simulation = Simulation(small_config())
    initial_matter = simulation.current_element_totals()
    initial_energy = simulation.total_energy()
    initial_generated_elements = simulation.world.generated_elements
    initial_generated_energy = simulation.world.generated_energy

    simulation.step(120)

    # Newly explored chunks generate terrain on demand; only the dynamic
    # budget above the geological baseline must be conserved.
    generated_elements = tuple(
        current - before
        for current, before in zip(simulation.world.generated_elements, initial_generated_elements)
    )
    assert simulation.current_element_totals() == tuple(
        total + generated for total, generated in zip(initial_matter, generated_elements)
    )
    generated_energy = simulation.world.generated_energy - initial_generated_energy
    dynamic_energy = simulation.total_energy() - generated_energy
    assert abs(dynamic_energy - initial_energy) <= max(1e-7, initial_energy * 1e-10)
    simulation.audit()


def test_primary_production_moves_heat_to_chemical_energy_without_creating_energy() -> None:
    simulation = Simulation(
        small_config().evolved(
            primary_production_rate=0.25,
            maintenance_cost_multiplier=0.0,
            mana_decay=0.0,
        )
    )
    organism = next(iter(simulation.organisms.values()))
    for batch in organism.body.values():
        batch.energy = 0.0
    simulation.world.add_heat(organism.position, simulation.reference_energy)
    before_heat = simulation.world.total_heat()
    before_chemical = organism.chemical_energy()
    before_total = simulation.total_energy()

    simulation._upkeep(organism)

    chemical_gain = organism.chemical_energy() - before_chemical
    heat_loss = before_heat - simulation.world.total_heat()
    assert chemical_gain > 0.0
    assert abs(heat_loss - chemical_gain) <= 1e-9
    assert abs(simulation.total_energy() - before_total) <= 1e-9


def test_molecule_counts_remain_discrete() -> None:
    simulation = Simulation(small_config())
    simulation.step(25)
    for inventory in simulation.all_inventories():
        for batch in inventory.values():
            assert isinstance(batch.count, int)
            assert batch.count >= 0
