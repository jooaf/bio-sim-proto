from __future__ import annotations

from pathlib import Path

import pytest

from soup.config import Config, PairingMode


def test_config_toml_round_trip(tmp_path: Path) -> None:
    config = Config()
    config.run.seed = 987
    config.world.population_size = 33
    config.viz.live_tunable = ["world.interactions_per_tick"]
    path = tmp_path / "config.toml"
    config.save(path)
    loaded = Config.load(path)
    assert loaded.to_dict() == config.to_dict()


def test_stage_zero_forces_future_features_off(tmp_path: Path) -> None:
    path = tmp_path / "gated.toml"
    path.write_text("[run]\nstage=0\n[energy]\nenabled=true\n[signals]\nenabled=true\n", encoding="utf-8")
    with pytest.warns(UserWarning, match="forced off"):
        loaded = Config.load(path)
    assert not loaded.energy.enabled
    assert not loaded.signals.enabled


def test_unknown_field_fails_loudly(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text("[run]\nmagic_fitness=1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown"):
        Config.load(path)


def test_disjoint_pairing_rejects_tape_reuse() -> None:
    config = Config()
    config.world.population_size = 10
    config.world.interactions_per_tick = 6
    config.world.pairing_mode = PairingMode.SHUFFLED_DISJOINT.value
    with pytest.raises(ValueError, match="cannot exceed half"):
        config.validate()


def test_stage2_requires_local_pairing() -> None:
    config = Config()
    config.run.stage = 2
    with pytest.raises(ValueError, match="requires local_neighborhood"):
        config.validate()

    config.world.pairing_mode = PairingMode.LOCAL_NEIGHBORHOOD.value
    config.validate()


def test_stage2_rejects_an_effectively_empty_initial_fill() -> None:
    config = Config()
    config.run.stage = 2
    config.world.width = 4
    config.world.height = 4
    config.world.pairing_mode = PairingMode.LOCAL_NEIGHBORHOOD.value
    config.symbols.initial_tape_fill = 0.01
    with pytest.raises(ValueError, match="at least two tapes"):
        config.validate()


def test_flat_stages_reject_local_pairing() -> None:
    config = Config()
    config.world.pairing_mode = PairingMode.LOCAL_NEIGHBORHOOD.value
    with pytest.raises(ValueError, match="requires Stage 2"):
        config.validate()


def test_unknown_pairing_mode_fails_loudly() -> None:
    config = Config()
    config.world.pairing_mode = "magic"
    with pytest.raises(ValueError, match="pairing_mode"):
        config.validate()


def test_unsupported_live_parameter_fails_loudly() -> None:
    config = Config()
    config.viz.live_tunable = ["world.population_size"]
    with pytest.raises(ValueError, match="live_tunable"):
        config.validate()
