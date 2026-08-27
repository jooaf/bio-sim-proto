from __future__ import annotations

import json
import tomllib
from dataclasses import asdict, fields
from enum import StrEnum
from pathlib import Path
from typing import Any

from .config import BehaviorModel, Scheduler, SimulationConfig

SETTINGS_SCHEMA_VERSION = 1


def load_config_file(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load JSON or TOML and return simulation and run sections."""
    if not path.exists():
        raise ValueError(f"configuration file does not exist: {path}")
    with path.open("rb") as handle:
        if path.suffix.lower() == ".toml":
            payload = tomllib.load(handle)
        elif path.suffix.lower() == ".json":
            payload = json.load(handle)
        else:
            raise ValueError("configuration file must end in .json or .toml")
    if not isinstance(payload, dict):
        raise TypeError("configuration root must be an object/table")
    schema_version = payload.get("schema_version", SETTINGS_SCHEMA_VERSION)
    if schema_version != SETTINGS_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported configuration schema_version {schema_version}; "
            f"expected {SETTINGS_SCHEMA_VERSION}"
        )
    run_values = payload.get("run", {})
    if "simulation" in payload:
        simulation_values = payload["simulation"]
    else:
        simulation_values = {
            key: value
            for key, value in payload.items()
            if key not in {"run", "schema_version"}
        }
    if not isinstance(simulation_values, dict) or not isinstance(run_values, dict):
        raise TypeError("simulation and run configuration sections must be objects/tables")
    return dict(simulation_values), dict(run_values)


def build_config(
    simulation_values: dict[str, Any],
    overrides: dict[str, Any] | None = None,
    assignments: list[str] | None = None,
) -> SimulationConfig:
    valid_fields = {field.name for field in fields(SimulationConfig)}
    simulation_values = dict(simulation_values)
    if isinstance(simulation_values.get("behavior_model"), str):
        simulation_values["behavior_model"] = BehaviorModel(
            simulation_values["behavior_model"]
        )
    if isinstance(simulation_values.get("scheduler"), str):
        simulation_values["scheduler"] = Scheduler(simulation_values["scheduler"])
    unknown = sorted(set(simulation_values) - valid_fields)
    if unknown:
        raise ValueError(f"unknown simulation configuration fields: {', '.join(unknown)}")
    config = SimulationConfig().evolved(**simulation_values)
    if overrides:
        unknown = sorted(set(overrides) - valid_fields)
        if unknown:
            raise ValueError(f"unknown CLI configuration fields: {', '.join(unknown)}")
        config = config.evolved(**overrides)
    for assignment in assignments or []:
        if "=" not in assignment:
            raise ValueError(f"--set requires FIELD=VALUE, received: {assignment}")
        name, raw_value = assignment.split("=", 1)
        if name not in valid_fields:
            raise ValueError(f"unknown simulation configuration field: {name}")
        value = _coerce(raw_value, getattr(config, name))
        config = config.evolved(**{name: value})
    config.validate()
    return config


def config_json(
    config: SimulationConfig,
    *,
    run: dict[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "simulation": asdict(config),
    }
    if run:
        payload["run"] = run
    return json.dumps(payload, indent=2, sort_keys=True)


def save_config_file(
    path: Path,
    config: SimulationConfig,
    *,
    run: dict[str, Any] | None = None,
) -> None:
    """Atomically save a reusable GUI/headless JSON configuration."""
    if path.suffix.lower() != ".json":
        raise ValueError("saved configuration file must end in .json")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(config_json(config, run=run) + "\n")
    temporary.replace(path)


def _coerce(raw_value: str, current_value: Any) -> Any:
    if isinstance(current_value, StrEnum):
        return type(current_value)(raw_value)
    if isinstance(current_value, bool):
        normalized = raw_value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
        raise ValueError(f"cannot parse boolean value: {raw_value}")
    if isinstance(current_value, int):
        return int(raw_value)
    if isinstance(current_value, float):
        return float(raw_value)
    if isinstance(current_value, str):
        return raw_value
    raise ValueError(f"unsupported configuration value type for {current_value!r}")
