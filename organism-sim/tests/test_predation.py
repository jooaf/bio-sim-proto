"""Predation and prey-selection mechanics that keep competition functional."""

from __future__ import annotations

from dataclasses import replace

from organism_sim import Simulation, SimulationConfig


def hunting_simulation(**changes: float) -> Simulation:
    config = SimulationConfig(
        seed=97,
        width=24,
        height=24,
        founder_count=2,
        element_count=4,
        molecule_count=12,
        initial_deposits=20,
        audit_every=0,
        **changes,
    )
    return Simulation(config)


def attack_pair(simulation: Simulation, *, attack: float = 0.8) -> tuple[object, object]:
    organisms = sorted(simulation.organisms.values(), key=lambda o: o.organism_id)
    attacker, target = organisms[0], organisms[1]
    for organism in organisms:
        organism.integrity = 100.0
        organism.max_integrity = 100.0
    attacker.phenotype = replace(attacker.phenotype, attack=attack)
    return attacker, target


def test_attack_damage_scales_with_multiplier() -> None:
    baseline = hunting_simulation(attack_damage_multiplier=1.0)
    boosted = hunting_simulation(attack_damage_multiplier=3.0)

    baseline_attacker, baseline_target = attack_pair(baseline)
    boosted_attacker, boosted_target = attack_pair(boosted)

    baseline._attack(baseline_attacker, baseline_target)
    boosted._attack(boosted_attacker, boosted_target)

    baseline_damage = 100.0 - baseline_target.integrity
    boosted_damage = 100.0 - boosted_target.integrity
    assert baseline_damage > 0.0
    assert abs(boosted_damage - 3.0 * baseline_damage) < 1e-9


def test_attack_can_complete_a_kill() -> None:
    simulation = hunting_simulation(attack_damage_multiplier=2.0)
    attacker, target = attack_pair(simulation, attack=1.2)
    target.integrity = 1.0

    simulation._attack(attacker, target)

    assert not target.alive
    assert target.last_action == "dead:predation"
    assert simulation.stats.deaths == 1


def test_prey_compatibility_threshold_filters_candidates() -> None:
    simulation = hunting_simulation(prey_compatibility_threshold=0.999999)
    attacker, target = attack_pair(simulation)
    # Random diet/body signature pairs never reach near-perfect similarity.
    assert simulation._best_prey(attacker, [target]) is None

    simulation.config = simulation.config.evolved(prey_compatibility_threshold=0.0)
    assert simulation._best_prey(attacker, [target]) is not None
