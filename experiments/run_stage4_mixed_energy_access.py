"""Run the preregistered Stage 4 mixed-population energy-access assay."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from experiments.run_phase2_parasite_control import initial_occupied_order
from soup.config import Config
from soup.simulation import Simulation
from soup.substrate.bff import OP_ENERGY_UPTAKE


SEEDS = range(202609220, 202609225)
UPTAKE_BYTES = bytes((OP_ENERGY_UPTAKE, 0, 0, 0, 0, 0, 0, 0))
CONTROL_BYTES = bytes((0x3B, 0, 0, 0, 0, 0, 0, 0))


def tape(value: bytes) -> NDArray[np.uint8]:
    return np.frombuffer(value, dtype=np.uint8).copy()


def assignment(config: Config) -> tuple[dict[int, NDArray[np.uint8]], dict[str, Any]]:
    occupied_order = initial_occupied_order(config)
    tape_ids = {flat_index: tape_id for tape_id, flat_index in enumerate(occupied_order)}
    sorted_indices = sorted(occupied_order)
    records: list[dict[str, Any]] = []
    overrides: dict[int, NDArray[np.uint8]] = {}
    for position, flat_index in enumerate(sorted_indices):
        uptake_type = position % 2 == config.run.seed % 2
        type_name = "uptake" if uptake_type else "control"
        raw = UPTAKE_BYTES if uptake_type else CONTROL_BYTES
        overrides[flat_index] = tape(raw)
        records.append(
            {
                "type": type_name,
                "tape_id": tape_ids[flat_index],
                "flat_index": flat_index,
                "cell": [flat_index % config.world.width, flat_index // config.world.width],
                "hex": raw.hex(),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    protocol = {
        "assignment_rule": "sorted occupied indices alternate types; uptake parity equals seed parity",
        "uptake_opcode": OP_ENERGY_UPTAKE,
        "uptake_count": sum(record["type"] == "uptake" for record in records),
        "control_count": sum(record["type"] == "control" for record in records),
        "records": records,
    }
    return overrides, protocol


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
            protocol["active_uptake_enabled"] = enabled
            run_dir = output_root / "runs" / f"{arm}_seed_{seed}"
            manifest_path = run_dir / "manifest.json"
            protocol_path = run_dir / "mixed_access_protocol.json"
            if manifest_path.exists() and protocol_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                existing = json.loads(protocol_path.read_text(encoding="utf-8"))
                if manifest.get("exit_status") != "success" or existing != protocol:
                    raise RuntimeError(f"incomplete or mismatched existing run: {run_dir}")
            else:
                simulation = Simulation(
                    config,
                    run_dir=run_dir,
                    initial_tape_overrides=overrides,
                )
                protocol_path.write_text(
                    json.dumps(protocol, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
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
        "config",
        nargs="?",
        type=Path,
        default=Path("experiments/configs/stage4_mixed_energy_access.toml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("sweeps/stage4_mixed_energy_access"),
    )
    args = parser.parse_args()
    print(run_campaign(args.config, args.output_root))


if __name__ == "__main__":
    main()
