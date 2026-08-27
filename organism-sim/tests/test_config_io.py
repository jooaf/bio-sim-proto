import json
from pathlib import Path

import pytest

from organism_sim.cli import create_parser
from organism_sim.config import BehaviorModel, Scheduler
from organism_sim.config_io import (
    SETTINGS_SCHEMA_VERSION,
    build_config,
    load_config_file,
    save_config_file,
)


def test_analysis_informed_balancing_defaults() -> None:
    config = build_config({})

    assert config.maintenance_cost_multiplier == 0.75
    assert config.reproduction_cost_multiplier == 0.50


def test_toml_config_and_cli_overrides(tmp_path: Path) -> None:
    path = tmp_path / "run.toml"
    path.write_text(
        """
[run]
ticks = 250
runs_dir = "/tmp/runs"

[simulation]
seed = 19
founder_count = 90
founder_archetype_count = 6
heat_diffusion = 0.12
"""
    )
    simulation_values, run_values = load_config_file(path)
    config = build_config(
        simulation_values,
        {"founder_count": 120},
        ["asexual_probability_floor=0.2", "max_sight=9"],
    )

    assert run_values == {"ticks": 250, "runs_dir": "/tmp/runs"}
    assert config.seed == 19
    assert config.founder_count == 120
    assert config.founder_archetype_count == 6
    assert config.heat_diffusion == 0.12
    assert config.asexual_probability_floor == 0.2
    assert config.max_sight == 9


def test_json_config_can_use_top_level_simulation_fields(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    path.write_text(json.dumps({"seed": 23, "founder_count": 40, "founder_archetype_count": 4}))

    simulation_values, run_values = load_config_file(path)
    config = build_config(simulation_values)

    assert run_values == {}
    assert config.seed == 23
    assert config.founder_count == 40


def test_saved_gui_settings_round_trip_into_headless_config(tmp_path: Path) -> None:
    path = tmp_path / "gui-settings.json"
    original = build_config(
        {
            "seed": 987,
            "founder_count": 420,
            "founder_archetype_count": 12,
            "heat_diffusion": 0.17,
            "cellular_emergence_enabled": True,
        }
    )

    save_config_file(path, original)
    payload = json.loads(path.read_text())
    simulation_values, run_values = load_config_file(path)
    restored = build_config(simulation_values)

    assert payload["schema_version"] == SETTINGS_SCHEMA_VERSION
    assert run_values == {}
    assert restored == original
    assert restored.seed == 987


def test_parallel_scheduler_round_trips_and_validates() -> None:
    config = build_config(
        {
            "behavior_model": "linear_intent_v2",
            "scheduler": "parallel-v3",
            "parallel_workers": 4,
        }
    )

    assert config.behavior_model == BehaviorModel.LINEAR_INTENT_V2
    assert config.scheduler == Scheduler.PARALLEL_V3
    assert config.parallel_workers == 4
    assigned = build_config(
        {},
        assignments=[
            "behavior_model=recurrent_intent_v2",
            "scheduler=parallel-v3",
        ],
    )
    assert assigned.behavior_model == BehaviorModel.RECURRENT_INTENT_V2
    assert assigned.scheduler == Scheduler.PARALLEL_V3
    with pytest.raises(ValueError, match="requires a V2 intent behavior model"):
        build_config({"scheduler": "parallel-v3"})


def test_unknown_settings_schema_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "future.json"
    path.write_text(json.dumps({"schema_version": 999, "simulation": {}}))

    with pytest.raises(ValueError, match="schema_version"):
        load_config_file(path)


def test_unknown_config_field_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown simulation configuration fields"):
        build_config({"not_a_real_field": 1})


def test_season_configuration_validation() -> None:
    config = build_config(
        {
            "seasons_enabled": True,
            "season_duration_min": 100,
            "season_duration_max": 200,
            "season_transition_ticks": 25,
            "season_strength": 0.75,
        }
    )
    assert config.seasons_enabled is True
    with pytest.raises(ValueError, match="duration bounds"):
        build_config({"season_duration_min": 200, "season_duration_max": 100})
    with pytest.raises(ValueError, match="season_strength"):
        build_config({"season_strength": 1.1})


def test_cellular_affordance_configuration_validation() -> None:
    config = build_config(
        {
            "cellular_emergence_enabled": True,
            "emergence_max_modules": 16,
            "emergence_structural_mutation_rate": 0.03,
        }
    )
    assert config.cellular_emergence_enabled is True
    with pytest.raises(ValueError, match="emergence_max_modules"):
        build_config({"emergence_max_modules": 0})


def test_biodeposit_configuration_validation() -> None:
    config = build_config(
        {
            "biodeposits_enabled": True,
            "biodeposit_decay_rate": 0.002,
            "biodeposit_movement_resistance": 0.5,
        }
    )
    assert config.biodeposits_enabled is True
    with pytest.raises(ValueError, match="biodeposit_decay_rate"):
        build_config({"biodeposit_decay_rate": -0.1})


def test_headless_parser_exposes_gui_slider_flags() -> None:
    parser = create_parser()
    args = parser.parse_args(
        [
            "--founders",
            "150",
            "--genome-seeds",
            "9",
            "--elements",
            "7",
            "--molecules",
            "36",
            "--deposits",
            "800",
            "--heat-diffusion",
            "0.11",
            "--primary-production",
            "0.0125",
            "--decomposition-rate",
            "0.002",
            "--mutation-multiplier",
            "2.0",
            "--asexual-floor",
            "0.3",
            "--sexual-floor",
            "0.09",
            "--no-sexual-floor-enabled",
            "--maintenance-multiplier",
            "0.85",
            "--maturity-multiplier",
            "0.6",
            "--reproduction-drive",
            "1.4",
            "--reproduction-cost",
            "0.7",
            "--reproduction-cooldown",
            "0.8",
            "--seasons",
            "--season-duration-min",
            "400",
            "--season-duration-max",
            "900",
            "--season-transition",
            "75",
            "--season-strength",
            "0.8",
            "--cellular-emergence",
            "--biodeposits",
        ]
    )

    assert args.founder_count == 150
    assert args.founder_archetype_count == 9
    assert args.element_count == 7
    assert args.molecule_count == 36
    assert args.initial_deposits == 800
    assert args.heat_diffusion == 0.11
    assert args.primary_production_rate == 0.0125
    assert args.decomposition_rate == 0.002
    assert args.mutation_multiplier == 2.0
    assert args.asexual_probability_floor == 0.3
    assert args.sexual_probability_floor == 0.09
    assert args.sexual_floor_enabled is False
    assert args.maintenance_cost_multiplier == 0.85
    assert args.maturity_age_multiplier == 0.6
    assert args.reproduction_action_bonus == 1.4
    assert args.reproduction_cost_multiplier == 0.7
    assert args.reproduction_cooldown_multiplier == 0.8
    assert args.seasons is True
    assert args.season_duration_min == 400
    assert args.season_duration_max == 900
    assert args.season_transition_ticks == 75
    assert args.season_strength == 0.8
    assert args.cellular_emergence is True
    assert args.biodeposits is True
