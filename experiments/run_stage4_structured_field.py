"""Run the preregistered Stage 4 structured-influx mechanics campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from experiments.run_phase2_parasite_control import initial_occupied_order
from experiments.run_stage4_active_uptake import assay_tape
from soup.config import Config
from soup.simulation import Simulation


SEEDS = range(202609230, 202609235)
CONDITIONS: tuple[tuple[str, float], ...] = (
    ("uniform", 0.0),
    ("patches", 0.5),
    ("patches", 2.0),
    ("patches", 8.0),
)


def run_one(
    config_path: Path,
    output_root: Path,
    seed: int,
    field_spec: str,
    correlation_length: float,
) -> Path:
    config = Config.load(config_path)
    config.run.seed = seed
    config.run.output_dir = str(output_root / "runs")
    config.environment.influx_spec = field_spec
    if field_spec == "patches":
        config.environment.correlation_length = correlation_length
    config.validate()
    label = "uniform" if field_spec == "uniform" else f"patches_{correlation_length:g}"
    run_dir = output_root / "runs" / f"{label}_seed_{seed}"
    manifest_path = run_dir / "manifest.json"
    protocol_path = run_dir / "structured_field_protocol.json"
    profile_path = run_dir / "influx_profile.parquet"
    expected_protocol = {
        "field_spec": field_spec,
        "correlation_length": None if field_spec == "uniform" else correlation_length,
        "influx_contrast": config.environment.influx_contrast,
        "environment_seed_xor": 0x534634,
        "seeded_tape_hex": assay_tape().tobytes().hex(),
        "seeded_count": len(initial_occupied_order(config)),
    }
    if manifest_path.exists() and protocol_path.exists() and profile_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing_protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        if manifest.get("exit_status") != "success" or existing_protocol != expected_protocol:
            raise RuntimeError(f"incomplete or mismatched existing run: {run_dir}")
        return run_dir
    indices = initial_occupied_order(config)
    simulation = Simulation(
        config,
        run_dir=run_dir,
        initial_tape_overrides={index: assay_tape() for index in indices},
    )
    protocol_path.write_text(
        json.dumps(expected_protocol, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if simulation.energy is None:
        raise RuntimeError("structured field campaign requires energy")
    weights = (
        np.ones(simulation.world.capacity, dtype=np.float64)
        if simulation.energy.influx_weights is None
        else simulation.energy.influx_weights
    )
    pd.DataFrame(
        {
            "flat_index": np.arange(simulation.world.capacity),
            "x": np.arange(simulation.world.capacity) % config.world.width,
            "y": np.arange(simulation.world.capacity) // config.world.width,
            "weight": weights,
        }
    ).to_parquet(profile_path, index=False, compression="zstd")
    return simulation.run()


def run_campaign(config_path: Path, output_root: Path) -> Path:
    rows: list[dict[str, Any]] = []
    for field_spec, correlation_length in CONDITIONS:
        for seed in SEEDS:
            run_dir = run_one(
                config_path,
                output_root,
                seed,
                field_spec,
                correlation_length,
            )
            rows.append(
                {
                    "seed": seed,
                    "field_spec": field_spec,
                    "correlation_length": (
                        np.nan if field_spec == "uniform" else correlation_length
                    ),
                    "run_dir": str(run_dir),
                }
            )
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = output_root / "index.parquet"
    pd.DataFrame(rows).sort_values(
        ["field_spec", "correlation_length", "seed"], ignore_index=True
    ).to_parquet(index_path, index=False, compression="zstd")
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config",
        nargs="?",
        type=Path,
        default=Path("experiments/configs/stage4_structured_field.toml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("sweeps/stage4_structured_field"),
    )
    args = parser.parse_args()
    print(run_campaign(args.config, args.output_root))


if __name__ == "__main__":
    main()
