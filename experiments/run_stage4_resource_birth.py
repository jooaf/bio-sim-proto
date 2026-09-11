"""Run the preregistered Stage 4 resource-coupled birth campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from experiments.run_phase2_parasite_control import initial_occupied_order
from experiments.run_stage4_mixed_energy_access import CONTROL_BYTES, UPTAKE_BYTES, tape
from soup.config import Config
from soup.simulation import Simulation

SEEDS = range(202609250, 202609260)
UPTAKE_COUNTS = (8, 32, 56)


def assignment(
    config: Config, uptake_count: int
) -> tuple[dict[int, NDArray[np.uint8]], dict[str, Any]]:
    occupied = initial_occupied_order(config)
    if len(occupied) != 64 or not 0 < uptake_count < len(occupied):
        raise ValueError("resource-birth assignment requires 64 occupied mixed tapes")
    ranked = sorted(
        occupied,
        key=lambda index: hashlib.sha256(
            f"{config.run.seed}:{index}".encode("ascii")
        ).digest(),
    )
    uptake_indices = set(ranked[:uptake_count])
    tape_ids = {index: tape_id for tape_id, index in enumerate(occupied)}
    overrides: dict[int, NDArray[np.uint8]] = {}
    records: list[dict[str, Any]] = []
    for index in sorted(occupied):
        type_name = "uptake" if index in uptake_indices else "control"
        raw = UPTAKE_BYTES if type_name == "uptake" else CONTROL_BYTES
        overrides[index] = tape(raw)
        records.append(
            {
                "tape_id": tape_ids[index],
                "flat_index": index,
                "cell": [index % config.world.width, index // config.world.width],
                "type": type_name,
                "hex": raw.hex(),
            }
        )
    return overrides, {
        "assignment_rule": "lowest SHA-256(seed:flat_index) ranks are uptake",
        "initial_uptake_count": uptake_count,
        "initial_control_count": len(occupied) - uptake_count,
        "records": records,
    }


def run_one(args: tuple[Path, Path, int, int, bool]) -> dict[str, Any]:
    config_path, output_root, seed, uptake_count, enabled = args
    config = Config.load(config_path)
    config.run.seed = seed
    config.run.output_dir = str(output_root / "runs")
    config.energy.active_uptake_enabled = enabled
    config.validate()
    overrides, protocol = assignment(config, uptake_count)
    protocol |= {
        "active_uptake_enabled": enabled,
        "field_spec": "patches",
        "correlation_length": 2.0,
        "influx_contrast": 1.0,
        "birth_energy_cost": 5.0,
    }
    arm = "enabled" if enabled else "disabled"
    run_dir = output_root / "runs" / f"{arm}_uptake_{uptake_count}_seed_{seed}"
    manifest_path = run_dir / "manifest.json"
    protocol_path = run_dir / "resource_birth_protocol.json"
    profile_path = run_dir / "influx_profile.parquet"
    if manifest_path.exists() and protocol_path.exists() and profile_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing = json.loads(protocol_path.read_text(encoding="utf-8"))
        if manifest.get("exit_status") != "success" or existing != protocol:
            raise RuntimeError(f"incomplete or mismatched existing run: {run_dir}")
    else:
        simulation = Simulation(config, run_dir=run_dir, initial_tape_overrides=overrides)
        if simulation.energy is None or simulation.energy.influx_weights is None:
            raise RuntimeError("resource-birth campaign requires patch energy")
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
    return {
        "seed": seed,
        "initial_uptake_count": uptake_count,
        "active_uptake_enabled": enabled,
        "run_dir": str(run_dir),
        "protocol": str(protocol_path),
    }


def run_campaign(config_path: Path, output_root: Path, processes: int) -> Path:
    jobs = [
        (config_path, output_root, seed, uptake_count, enabled)
        for enabled in (False, True)
        for uptake_count in UPTAKE_COUNTS
        for seed in SEEDS
    ]
    with ProcessPoolExecutor(max_workers=processes) as executor:
        rows = list(executor.map(run_one, jobs))
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = output_root / "index.parquet"
    pd.DataFrame(rows).sort_values(
        ["active_uptake_enabled", "initial_uptake_count", "seed"],
        ignore_index=True,
    ).to_parquet(index_path, index=False, compression="zstd")
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config", nargs="?", type=Path,
        default=Path("experiments/configs/stage4_resource_birth.toml"),
    )
    parser.add_argument(
        "--output-root", type=Path,
        default=Path("sweeps/stage4_resource_birth"),
    )
    parser.add_argument("--processes", type=int, default=10)
    args = parser.parse_args()
    print(run_campaign(args.config, args.output_root, args.processes))


if __name__ == "__main__":
    main()
