from __future__ import annotations

import json

import numpy as np
import pytest

from organism_sim import Simulation
from organism_sim.cli import create_parser
from organism_sim.config import BehaviorModel, Scheduler, SimulationConfig
from organism_sim.rust_kernel import RustKernelSimulation, extension_available
from organism_sim.rust_run import run_rust_headless


def kernel_config(**changes: object) -> SimulationConfig:
    values = {
        "seed": 7,
        "founder_count": 120,
        "founder_archetype_count": 8,
        "audit_every": 0,
    }
    values.update(changes)
    return SimulationConfig(**values)


def test_rust_extension_is_installed() -> None:
    assert extension_available()


def test_rust_kernel_same_seed_digest() -> None:
    config = kernel_config(seed=41)
    left = RustKernelSimulation(config)
    right = RustKernelSimulation(config.evolved())

    left.step(150)
    right.step(150)

    assert left.digest() == right.digest()
    assert left.tick == 150
    assert left.population == right.population


def test_rust_kernel_coarse_step_matches_single_steps() -> None:
    coarse = RustKernelSimulation(kernel_config(seed=23))
    singles = RustKernelSimulation(kernel_config(seed=23))

    coarse.step(80)
    for _ in range(80):
        singles.step_one()

    assert coarse.digest() == singles.digest()


def test_parallel_v3_is_worker_count_invariant() -> None:
    base = kernel_config(
        behavior_model=BehaviorModel.LINEAR_INTENT_V2,
        scheduler=Scheduler.PARALLEL_V3,
    )
    single = RustKernelSimulation(base.evolved(parallel_workers=1))
    four = RustKernelSimulation(base.evolved(parallel_workers=4))

    single_profile = single.profile_step(80)
    four_profile = four.profile_step(80)

    assert single.digest() == four.digest()
    assert single_profile["parallel_intent"] > 0.0
    assert four_profile["parallel_prepare"] > 0.0
    assert four_profile["parallel_resolution"] > 0.0
    assert single.audit()["elements_ok"] is True
    assert single.audit()["energy_ok"] is True
    snapshot = single.snapshot()
    assert snapshot["scheduler"] == Scheduler.PARALLEL_V3
    assert snapshot["scheduler_schema_version"] == 3
    assert snapshot["parallel_rng_version"] == 2
    assert snapshot["parallel_resolver_version"] == 2
    assert snapshot["effective_parallel_workers"] == 1


def test_parallel_v3_requires_v2_behavior() -> None:
    with pytest.raises(ValueError, match="requires a V2 intent behavior model"):
        RustKernelSimulation(kernel_config(scheduler=Scheduler.PARALLEL_V3))


def test_rust_kernel_different_seed_diverges() -> None:
    left = RustKernelSimulation(kernel_config(seed=41))
    right = RustKernelSimulation(kernel_config(seed=42))

    left.step(80)
    right.step(80)

    assert left.digest() != right.digest()


def test_rust_phase_profile_advances_and_attributes_time() -> None:
    simulation = RustKernelSimulation(kernel_config(seed=17, founder_count=80))

    profile = simulation.profile_step(3)

    assert simulation.tick == 3
    assert profile["ticks"] == 3
    assert profile["final_population"] == simulation.population
    assert profile["total"] > 0.0
    assert profile["organism_loop"] >= profile["decision"]
    assert profile["organism_loop"] >= profile["upkeep"]


def test_rust_kernel_audit_and_snapshot() -> None:
    simulation = RustKernelSimulation(kernel_config(seed=13, founder_count=160))
    simulation.step(180)

    digest_before_audit = simulation.digest()
    audit = simulation.audit()
    assert simulation.digest() == digest_before_audit
    snapshot = simulation.snapshot()
    organisms = snapshot["organisms"]

    assert audit["elements_ok"] is True
    assert audit["energy_ok"] is True
    assert abs(audit["energy_error"]) / max(abs(audit["initial_energy"]), 1e-9) < 1e-6
    assert audit["energy_accounting_scale"] == pytest.approx(
        abs(audit["initial_energy"]) + abs(audit["generated_energy"])
    )
    assert audit["energy_relative_error"] == pytest.approx(
        abs(audit["energy_error"]) / audit["energy_accounting_scale"]
    )
    assert audit["energy_tolerance"] >= audit["energy_accounting_scale"] * 5e-12
    assert snapshot["tick"] == 180
    assert snapshot["population"] == simulation.population
    assert snapshot["behavior_model"] == BehaviorModel.LEGACY_LINEAR_MACRO_V1
    assert snapshot["observation_schema_version"] == 1
    assert snapshot["intent_schema_version"] == 1
    assert snapshot["brain_schema_version"] == 0
    assert snapshot["brain_cost_active"] is False
    assert snapshot["v2_founder_priors_enabled"] is True
    assert snapshot["v2_brain_dimensions"] == {
        "observations": 28,
        "hidden": 8,
        "controller_outputs": 26,
        "neural_loci": 979,
        "active_loci": 0,
        "candidate_features": 16,
        "intent_types": 10,
        "max_candidates": 33,
    }
    assert snapshot["v2_brain_cost_coefficients"] == {
        "multiplier": 1.0,
        "base": 0.001,
        "hidden": 0.002,
        "recurrent": 0.002,
    }
    assert simulation.stats_dict()["dense_living_slots"] == simulation.population
    assert len(organisms["id"]) == simulation.population
    assert len(organisms["energy"]) == simulation.population


def test_rust_kernel_exposes_sparse_organism_composition() -> None:
    config = kernel_config(seed=19, founder_count=24, element_count=4, molecule_count=12)
    simulation = RustKernelSimulation(config)

    composition = simulation.organism_composition()
    catalog = simulation.molecule_catalog()

    assert composition["schema_version"] == 1
    assert composition["tick"] == 0
    row_count = len(composition["organism_id"])
    assert row_count > 0
    assert all(
        len(composition[name]) == row_count
        for name in ("compartment", "molecule_id", "count", "chemical_energy")
    )
    assert {int(value) for value in composition["compartment"]} <= {0, 1, 2}
    assert all(int(value) > 0 for value in composition["count"])
    assert all(int(value) >= 0 for value in composition["molecule_id"])
    assert catalog["schema_version"] == 1
    assert catalog["element_count"] == config.element_count
    assert catalog["molecule_count"] == config.molecule_count
    assert len(catalog["molecules"]) == config.molecule_count
    assert all(
        len(molecule["composition"]) == config.element_count
        for molecule in catalog["molecules"]
    )

    simulation.step(7)
    later = simulation.organism_composition()
    assert later["tick"] == 7
    assert len(later["organism_id"]) > 0


def test_linear_and_recurrent_intent_v2_run_only_in_rust() -> None:
    for behavior_model in (
        BehaviorModel.LINEAR_INTENT_V2,
        BehaviorModel.RECURRENT_INTENT_V2,
    ):
        with pytest.raises(ValueError, match="require the Rust engine"):
            Simulation(kernel_config(behavior_model=behavior_model))

    simulation = RustKernelSimulation(
        kernel_config(behavior_model=BehaviorModel.LINEAR_INTENT_V2),
    )
    simulation.step(40)
    snapshot = simulation.snapshot()

    assert snapshot["behavior_model"] == BehaviorModel.LINEAR_INTENT_V2
    assert snapshot["observation_schema_version"] == 2
    assert snapshot["intent_schema_version"] == 2
    assert snapshot["brain_schema_version"] == 1
    assert snapshot["brain_cost_active"] is True
    assert snapshot["v2_brain_dimensions"]["active_loci"] == 451
    assert snapshot["stats"]["brain_energy_spent"] > 0.0
    assert sum(snapshot["stats"]["v2_intent_counts"]) > 0
    assert len(snapshot["organisms"]["decision_count"]) == simulation.population
    assert len(snapshot["organisms"]["brain_energy_spent"]) == simulation.population

    recurrent = RustKernelSimulation(
        kernel_config(
            behavior_model=BehaviorModel.RECURRENT_INTENT_V2,
            memory_probe_enabled=True,
        ),
    )
    lesioned = RustKernelSimulation(
        kernel_config(
            behavior_model=BehaviorModel.RECURRENT_INTENT_V2,
            recurrent_state_lesion=True,
            memory_probe_enabled=True,
        ),
    )
    recurrent.step(40)
    lesioned.step(40)
    recurrent_snapshot = recurrent.snapshot()
    lesioned_snapshot = lesioned.snapshot()

    assert recurrent_snapshot["v2_brain_dimensions"]["active_loci"] == 979
    assert recurrent_snapshot["stats"]["hidden_brain_energy_spent"] > 0.0
    assert recurrent_snapshot["stats"]["neural_numerical_errors"] == 0
    assert recurrent_snapshot["stats"]["memory_probe_decisions"] > 0
    assert recurrent_snapshot["memory_probe_enabled"] is True
    assert (
        len(recurrent_snapshot["organisms"]["neural_state"]) == recurrent.population * 8
    )
    assert (
        len(recurrent_snapshot["organisms"]["recurrent_expression_genetic_mean"])
        == recurrent.population
    )
    assert (
        len(recurrent_snapshot["organisms"]["offspring_count"]) == recurrent.population
    )
    assert any(recurrent_snapshot["organisms"]["hidden_expression_mean"] > 0.0)
    assert all(lesioned_snapshot["organisms"]["neural_state"] == 0.0)
    assert recurrent.digest() != lesioned.digest()


def test_rust_gui_snapshot_is_bounded_and_observational() -> None:
    simulation = RustKernelSimulation(kernel_config(seed=31, founder_count=120))
    simulation.step(40)
    digest_before = simulation.digest()

    snapshot = simulation.gui_snapshot((0, 0, 128, 128))

    assert simulation.digest() == digest_before
    assert snapshot["tick"] == 40
    assert len(snapshot["overview"]["id"]) == simulation.population
    assert len(snapshot["organisms"]["id"]) <= simulation.population
    assert len(snapshot["organisms"]["id"]) == len(snapshot["organisms"]["area"])
    assert len(snapshot["deposits"]["x"]) == len(snapshot["deposits"]["units"])
    assert snapshot["heat"]["maximum"] == 0.0
    assert snapshot["last_action_names"][20] == "wait"
    assert snapshot["last_action_names"][21] == "move_one_tile"
    assert set(snapshot["selected_relations"]) == {
        "parent_ids",
        "living_parent_ids",
        "offspring_ids",
        "alliance_ids",
        "bond_ids",
    }

    selected_id = int(snapshot["overview"]["id"][0])
    selected = simulation.gui_snapshot((0, 0, 128, 128), selected_id=selected_id)
    assert len(selected["selected_relations"]["parent_ids"]) in (0, 1, 2)


def test_rust_runtime_config_update_changes_future_dynamics() -> None:
    baseline = RustKernelSimulation(kernel_config(seed=37))
    changed = RustKernelSimulation(kernel_config(seed=37))

    changed.update_config(maintenance_cost_multiplier=0.0)
    baseline.step(20)
    changed.step(20)

    assert baseline.digest() != changed.digest()
    with pytest.raises(ValueError, match="cannot change"):
        changed.update_config(founder_count=999)
    with pytest.raises(ValueError, match="cannot change"):
        changed.update_config(brain_base_cost=0.0)
    with pytest.raises(ValueError, match="cannot change"):
        changed.update_config(
            behavior_model=BehaviorModel.RECURRENT_INTENT_V2,
        )


def test_rust_compressibility_metrics_are_observational_and_deterministic() -> None:
    simulation = RustKernelSimulation(kernel_config(seed=29, founder_count=120))
    simulation.step(100)
    digest_before = simulation.digest()

    first = simulation.compressibility_metrics()
    second = simulation.compressibility_metrics()

    assert first == second
    assert simulation.digest() == digest_before
    assert first["tick"] == 100
    assert first["population"] == simulation.population
    assert first["exact_policy_keys"] <= simulation.population
    for preset in ("lineage_safe", "species_safe", "trait_only"):
        assert 0.0 <= first[preset]["represented_fraction"] <= 1.0
        assert first[preset]["represented_work"] <= simulation.population


def test_random_environment_seasons_are_exposed_and_deterministic() -> None:
    config = kernel_config(
        founder_count=40,
        founder_archetype_count=4,
        seasons_enabled=True,
        season_duration_min=5,
        season_duration_max=5,
        season_transition_ticks=2,
        season_strength=0.8,
    )
    with pytest.raises(ValueError, match="seasons require the Rust engine"):
        Simulation(config)
    left = RustKernelSimulation(config)
    right = RustKernelSimulation(config)
    initial = left.season_state()
    assert initial["enabled"] is True
    assert initial["event_count"] == 1
    assert len(initial["target_molecule_charge_affinities"]) == config.molecule_count

    left.step(12)
    right.step(12)
    assert left.digest() == right.digest()
    season = left.season_state(after_event=1)
    assert season["index"] == 2
    assert season["event_count"] == 3
    assert [event["index"] for event in season["events"]] == [1, 2]
    assert left.stats_dict()["season_index"] == 2
    assert left.audit()["elements_ok"] is True
    assert left.audit()["energy_ok"] is True


def test_stochastic_cellular_affordances_have_no_assigned_higher_level_state() -> None:
    config = kernel_config(
        founder_count=80,
        founder_archetype_count=8,
        cellular_emergence_enabled=True,
        emergence_bond_rate=0.05,
        emergence_module_cost=0.001,
    )
    with pytest.raises(
        ValueError, match="cellular affordances require the Rust engine"
    ):
        Simulation(config)
    left = RustKernelSimulation(config)
    right = RustKernelSimulation(config)
    left.step(40)
    right.step(40)

    assert left.digest() == right.digest()
    stats = left.stats_dict()
    assert stats["cellular_affordances_enabled"] is True
    assert stats["module_instances"] >= left.population
    assert stats["expressed_module_instances"] > 0
    assert "multicellular" not in stats
    assert "adaptability" not in stats
    snapshot = left.gui_snapshot((-64, -64, 192, 192))
    assert len(snapshot["organisms"]["module_count"]) == left.population
    assert len(snapshot["organisms"]["component_id"]) == left.population
    assert len(snapshot["organisms"]["component_size"]) == left.population
    assert snapshot["stats"]["coordinated_components_enabled"] is True
    assert set(snapshot["bonds"]) == {
        "left_id",
        "right_id",
        "x1",
        "y1",
        "x2",
        "y2",
        "strength",
    }
    assert left.audit()["elements_ok"] is True
    assert left.audit()["energy_ok"] is True


def test_dynamic_chemistry_reactions_byproducts_and_conservation() -> None:
    config = kernel_config(
        seed=53,
        founder_count=60,
        founder_archetype_count=6,
        initial_deposits=900,
        dynamic_chemistry_enabled=True,
        environmental_reaction_rate=1.0,
        reaction_thermodynamics=0.25,
        byproduct_strength=0.10,
        byproduct_decay_rate=0.01,
        cellular_emergence_enabled=True,
        emergence_engulfment_rate=1.0,
    )
    simulation = RustKernelSimulation(config)
    simulation.step(80)

    stats = simulation.stats_dict()
    snapshot = simulation.snapshot()
    byproducts = snapshot["byproducts"]
    assert stats["dynamic_chemistry_enabled"] is True
    assert stats["environmental_reaction_rules"] > 0
    assert stats["environmental_reactions"] > 0
    assert stats["byproduct_emissions"] > 0
    assert stats["byproduct_positions"] > 0
    assert len(byproducts["x"]) == len(byproducts["catalyst"])
    assert len(byproducts["x"]) == len(byproducts["toxin"])
    assert stats["chemistry_regime_variance"] >= 0.0
    assert simulation.audit()["elements_ok"] is True
    assert simulation.audit()["energy_ok"] is True


def test_dynamic_chemistry_is_disabled_without_runtime_state() -> None:
    simulation = RustKernelSimulation(kernel_config(seed=54, founder_count=40))
    simulation.step(20)

    stats = simulation.stats_dict()
    snapshot = simulation.snapshot()
    assert stats["dynamic_chemistry_enabled"] is False
    assert stats["environmental_reaction_rules"] == 0
    assert stats["environmental_reactions"] == 0
    assert len(snapshot["byproducts"]["x"]) == 0


def test_biodeposit_snapshot_is_observational() -> None:
    config = kernel_config(
        founder_count=40,
        founder_archetype_count=4,
        biodeposits_enabled=True,
        biodeposit_decay_rate=0.0,
        maintenance_cost_multiplier=5.0,
    )
    with pytest.raises(ValueError, match="physical biodeposits require the Rust engine"):
        Simulation(config)
    simulation = RustKernelSimulation(config)
    simulation.step(120)
    digest_before = simulation.digest()

    snapshot = simulation.gui_snapshot((0, 0, 128, 128))

    assert simulation.digest() == digest_before
    assert set(snapshot["biodeposits"]) == {"x", "y", "density"}
    assert len(snapshot["biodeposits"]["x"]) == len(
        snapshot["biodeposits"]["density"]
    )
    assert snapshot["stats"]["biodeposits_enabled"] is True
    assert snapshot["stats"]["biodeposit_positions"] > 0
    assert simulation.audit()["elements_ok"] is True
    assert simulation.audit()["energy_ok"] is True


def test_rust_headless_writes_compact_research_record(tmp_path) -> None:
    config = kernel_config(
        founder_count=40,
        founder_archetype_count=4,
        recording_metrics_interval=5,
        seasons_enabled=True,
        season_duration_min=5,
        season_duration_max=5,
        season_transition_ticks=2,
        cellular_emergence_enabled=True,
        emergence_bond_rate=0.05,
        biodeposits_enabled=True,
    )
    simulation, run_dir, elapsed = run_rust_headless(
        config,
        12,
        runs_root=tmp_path,
        progress_every=0,
    )

    manifest = json.loads((run_dir / "manifest.json").read_text())
    metric_rows = (run_dir / "metrics.jsonl").read_text().splitlines()
    season_rows = (run_dir / "season_events.jsonl").read_text().splitlines()
    assert simulation.tick == 12
    assert elapsed > 0.0
    assert manifest["kernel"] == "rust"
    assert manifest["schema_version"] == 3
    assert len(manifest["config_sha256"]) == 64
    assert manifest["build"]["kernel_version"] == "0.1.0"
    assert len(manifest["build"]["kernel_binary_sha256"]) == 64
    assert manifest["execution"] == {
        "scheduler": "serial-v2",
        "scheduler_schema_version": 2,
        "configured_workers": 0,
        "partition_strategy": "serial-shuffled-v2",
        "rng_derivation_version": 0,
        "conflict_resolver_version": 0,
    }
    assert manifest["effective_parallel_workers"] == 1
    assert manifest["season_events"] == "season_events.jsonl"
    assert manifest["final_tick"] == 12
    assert manifest["elements_ok"] is True
    assert manifest["energy_ok"] is True
    assert len(metric_rows) == 4  # tick 0, 5, 10, and the final partial block
    assert [json.loads(row)["index"] for row in season_rows] == [0, 1, 2]
    assert json.loads(metric_rows[-1])["season_index"] == 2
    assert (run_dir / "final_state.npz").is_file()
    assert not (run_dir / "organism_composition.jsonl").exists()
    assert not (run_dir / "molecule_catalog.json").exists()
    assert manifest["organism_composition_enabled"] is False
    with np.load(run_dir / "final_state.npz") as state:
        assert "organisms_module_offsets" in state
        assert "organisms_module_primitives" in state
        assert "organisms_guest_offsets" in state
        assert "organisms_component_id" in state
        assert "organisms_component_size" in state
        assert "bonds_left_id" in state
        assert "biodeposits_x" in state
        assert "biodeposits_density" in state
    assert (run_dir / "final_species.json").is_file()
    assert (run_dir / "audit.json").is_file()


def test_rust_headless_records_sparse_organism_composition(tmp_path) -> None:
    config = kernel_config(
        seed=61,
        founder_count=40,
        founder_archetype_count=4,
        recording_metrics_interval=5,
    )
    control = RustKernelSimulation(config)
    control.step(7)
    simulation, run_dir, elapsed = run_rust_headless(
        config,
        7,
        runs_root=tmp_path,
        progress_every=0,
        record_composition=True,
        composition_interval=2,
    )

    manifest = json.loads((run_dir / "manifest.json").read_text())
    catalog = json.loads((run_dir / "molecule_catalog.json").read_text())
    rows = [
        json.loads(line)
        for line in (run_dir / "organism_composition.jsonl").read_text().splitlines()
        if line
    ]
    assert simulation.tick == 7
    assert simulation.digest() == control.digest()
    assert elapsed > 0.0
    assert manifest["organism_composition_enabled"] is True
    assert manifest["organism_composition_interval"] == 2
    assert manifest["organism_composition_schema_version"] == 1
    assert manifest["organism_composition"] == "organism_composition.jsonl"
    assert manifest["molecule_catalog"] == "molecule_catalog.json"
    assert catalog["schema_version"] == 1
    assert {int(row["tick"]) for row in rows} == {0, 2, 4, 6, 7}
    assert {row["compartment"] for row in rows} <= {"body", "gut", "waste"}
    assert all(row["count"] > 0 for row in rows)
    assert all(0 <= row["molecule_id"] < config.molecule_count for row in rows)
    assert all(row["organism_id"] > 0 for row in rows)


def test_cli_accepts_rust_engine() -> None:
    args = create_parser().parse_args(
        [
            "--engine",
            "rust",
            "--ticks",
            "10",
            "--record-composition",
            "--composition-every",
            "25",
        ]
    )
    assert args.engine == "rust"
    assert args.record_composition is True
    assert args.composition_every == 25
    assert args.ticks == 10
