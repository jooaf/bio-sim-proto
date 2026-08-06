from __future__ import annotations

from pathlib import Path

import pytest

from soup.config import Config


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
