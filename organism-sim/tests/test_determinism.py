from organism_sim import Simulation, SimulationConfig


def test_seeded_runs_are_deterministic() -> None:
    config = SimulationConfig(
        seed=29,
        width=24,
        height=24,
        founder_count=18,
        element_count=5,
        molecule_count=20,
        initial_deposits=120,
        audit_every=10,
    )
    left = Simulation(config.evolved())
    right = Simulation(config.evolved())

    left.step(80)
    right.step(80)

    assert left.snapshot() == right.snapshot()


def test_deposit_count_does_not_change_founder_or_dynamics_draws() -> None:
    config = SimulationConfig(
        seed=31,
        width=24,
        height=24,
        founder_count=18,
        founder_archetype_count=6,
        element_count=5,
        molecule_count=20,
        initial_deposits=40,
        audit_every=0,
    )

    sparse = Simulation(config)
    dense = Simulation(config.evolved(initial_deposits=160))

    assert sparse.catalog == dense.catalog
    assert sparse.organisms == dense.organisms
    assert sparse.species == dense.species
    assert sparse.rng.getstate() == dense.rng.getstate()
    assert sparse.world.deposits != dense.world.deposits
