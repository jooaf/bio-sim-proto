"""Deposit primary production: the renewable food-web energy influx.

Without it, chemical energy flows one way into heat and every run becomes a
slow-motion starvation lottery in which mortality is dominated by attrition and
selection has no renewable resource to compete over.
"""

from __future__ import annotations

from organism_sim import Simulation, SimulationConfig
from organism_sim.chemistry import inventory_energy


def production_config(rate: float, seed: int = 11) -> SimulationConfig:
    return SimulationConfig(
        seed=seed,
        width=32,
        height=32,
        founder_count=30,
        element_count=6,
        molecule_count=24,
        initial_deposits=240,
        audit_every=5,
        deposit_production_rate=rate,
    )


def test_production_moves_heat_into_deposit_chemical_energy() -> None:
    simulation = Simulation(production_config(rate=0.10))

    # Warm the deposit cells deterministically so production has fuel.
    for position in list(simulation.world.deposits):
        simulation.world.add_heat(position, 10.0)

    before_heat = simulation.world.total_heat()
    before_energy = sum(
        inventory_energy(inventory) for inventory in simulation.world.deposits.values()
    )

    simulation.step()

    after_heat = simulation.world.total_heat()
    after_energy = sum(
        inventory_energy(inventory) for inventory in simulation.world.deposits.values()
    )
    assert after_energy > before_energy  # deposits recharge from ambient heat
    assert after_heat < before_heat  # ... and the heat is actually consumed


def test_production_is_disabled_at_zero_rate() -> None:
    simulation = Simulation(production_config(rate=0.0))
    for position in list(simulation.world.deposits):
        simulation.world.add_heat(position, 10.0)
    before = simulation.world.total_heat()
    simulation.step()
    # Heat changes without production come only from metabolism, which adds
    # heat; nothing harvests ambient heat into deposits.
    assert simulation.world.total_heat() >= before - simulation.config.decomposition_rate


def inject_heat(simulation: Simulation, amount: float) -> None:
    """Warm deposit cells and re-baseline the audit budget for the injection."""
    for position in list(simulation.world.deposits):
        simulation.world.add_heat(position, amount)
    # The audit baseline was captured in __init__, before this artificial
    # injection; re-baseline so only dynamics are policed below.
    simulation.initial_energy = simulation.total_energy() - simulation.world.generated_energy


def test_production_conservs_total_energy_exactly() -> None:
    simulation = Simulation(production_config(rate=0.10))
    inject_heat(simulation, 50.0)
    baseline = simulation.total_energy() - simulation.world.generated_energy
    for _ in range(50):
        simulation.step()
    # audit() raises on matter drift and returns the dynamic energy error,
    # which excludes geological energy from chunks generated mid-run.
    error = simulation.audit()
    assert abs(error) <= max(1e-7, baseline * 1e-10)


def test_production_respects_batch_energy_capacity() -> None:
    simulation = Simulation(production_config(rate=1.0))  # extreme rate
    inject_heat(simulation, 1e6)
    for _ in range(200):
        simulation.step()
    # validate_batch inside audit asserts every batch stays within capacity.
    simulation.audit()


def test_production_sustains_population_beyond_baseline_food_budget() -> None:
    """With production on, a small closed ecosystem should still be alive with
    meaningful generational turnover after the initial budget era."""

    simulation = Simulation(production_config(rate=0.10, seed=3))
    simulation.step(1500)
    assert simulation.population > 0
    generations = [organism.generation for organism in simulation.organisms.values() if organism.alive]
    assert max(generations) >= 2
