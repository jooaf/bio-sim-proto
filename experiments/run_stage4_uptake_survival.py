"""Run the preregistered Stage 4 active-uptake survival campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from experiments.run_stage4_mixed_energy_access import assignment
from soup.config import Config
from soup.simulation import Simulation

SEEDS = range(202609240, 202609250)


def run_campaign(config_path: Path, output_root: Path) -> Path:
    rows: list[dict[str, Any]] = []
    for enabled in (False, True):
        arm = "enabled" if enabled else "disabled"
        for seed in SEEDS:
            config = Config.load(config_path)
            config.run.seed = seed
            config.run.output_dir = str(output_root / "runs")
            config.energy.active_uptake_enabled = enabled
            config.validate()
            overrides, protocol = assignment(config)
            protocol |= {
                "active_uptake_enabled": enabled,
                "field_spec": "patches",
                "correlation_length": 2.0,
                "influx_contrast": 1.0,
                "starved_ticks": 50,
            }
            run_dir = output_root / "runs" / f"{arm}_seed_{seed}"
            manifest_path = run_dir / "manifest.json"
            protocol_path = run_dir / "uptake_survival_protocol.json"
            profile_path = run_dir / "influx_profile.parquet"
            if manifest_path.exists() and protocol_path.exists() and profile_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                existing = json.loads(protocol_path.read_text(encoding="utf-8"))
                if manifest.get("exit_status") != "success" or existing != protocol:
                    raise RuntimeError(f"incomplete or mismatched existing run: {run_dir}")
            else:
                simulation = Simulation(config, run_dir=run_dir, initial_tape_overrides=overrides)
                if simulation.energy is None or simulation.energy.influx_weights is None:
                    raise RuntimeError("survival campaign requires a patch energy profile")
                protocol_path.write_text(
                    json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
                indices = np.arange(simulation.world.capacity)
                pd.DataFrame(
                    {
                        "flat_index": indices,
                        "x": indices % config.world.width,
                        "y": indices // config.world.width,
                        "weight": simulation.energy.influx_weights,
                    }
                ).to_parquet(profile_path, index=False, compression="zstd")
                simulation.run()
            rows.append(
                {
                    "seed": seed,
                    "active_uptake_enabled": enabled,
                    "run_dir": str(run_dir),
                    "protocol": str(protocol_path),
                }
            )
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = output_root / "index.parquet"
    pd.DataFrame(rows).sort_values(
        ["active_uptake_enabled", "seed"], ignore_index=True
    ).to_parquet(index_path, index=False, compression="zstd")
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config", nargs="?", type=Path,
        default=Path("experiments/configs/stage4_uptake_survival.toml"),
    )
    parser.add_argument(
        "--output-root", type=Path,
        default=Path("sweeps/stage4_uptake_survival"),
    )
    args = parser.parse_args()
    print(run_campaign(args.config, args.output_root))


if __name__ == "__main__":
    main()
