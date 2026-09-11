"""Run the preregistered Stage 4 exact-tag signal-dispatch assay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from experiments.run_phase2_parasite_control import initial_occupied_order
from soup.config import Config
from soup.simulation import Simulation
from soup.substrate.bff import OP_ENERGY_UPTAKE

SEEDS = range(202609260, 202609265)
ARMS: tuple[tuple[str, bool, str], ...] = (
    ("matched", True, "aabbccdd"),
    ("mismatched", True, "11223344"),
    ("disabled", False, "aabbccdd"),
)
ASSAY_BYTES = bytes.fromhex("aabbccdd") + bytes((OP_ENERGY_UPTAKE, 0, 0, 0))


def assay_tape() -> np.ndarray[Any, np.dtype[np.uint8]]:
    return np.frombuffer(ASSAY_BYTES, dtype=np.uint8).copy()


def run_campaign(config_path: Path, output_root: Path) -> Path:
    rows: list[dict[str, Any]] = []
    for arm, enabled, tag_hex in ARMS:
        for seed in SEEDS:
            config = Config.load(config_path)
            config.run.seed = seed
            config.run.output_dir = str(output_root / "runs")
            config.signals.enabled = enabled
            config.signals.initial_tag_hex = tag_hex
            config.validate()
            occupied = initial_occupied_order(config)
            protocol = {
                "arm": arm,
                "signals_enabled": enabled,
                "signal_tag_hex": tag_hex,
                "assay_tape_hex": ASSAY_BYTES.hex(),
                "seeded_count": len(occupied),
                "dispatch_rule": "first exact active-tape block; handler follows tag",
            }
            run_dir = output_root / "runs" / f"{arm}_seed_{seed}"
            manifest_path = run_dir / "manifest.json"
            protocol_path = run_dir / "signal_dispatch_protocol.json"
            profile_path = run_dir / "signal_profile.parquet"
            if manifest_path.exists() and protocol_path.exists() and profile_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                existing = json.loads(protocol_path.read_text(encoding="utf-8"))
                if manifest.get("exit_status") != "success" or existing != protocol:
                    raise RuntimeError(f"incomplete or mismatched existing run: {run_dir}")
            else:
                simulation = Simulation(
                    config,
                    run_dir=run_dir,
                    initial_tape_overrides={index: assay_tape() for index in occupied},
                )
                protocol_path.write_text(
                    json.dumps(protocol, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                indices = np.arange(simulation.world.capacity)
                pd.DataFrame(
                    {
                        "flat_index": indices,
                        "x": indices % config.world.width,
                        "y": indices // config.world.width,
                        "tag_hex": [tag_hex] * simulation.world.capacity,
                    }
                ).to_parquet(profile_path, index=False, compression="zstd")
                simulation.run()
            rows.append({"seed": seed, "arm": arm, "run_dir": str(run_dir)})
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = output_root / "index.parquet"
    pd.DataFrame(rows).sort_values(["arm", "seed"], ignore_index=True).to_parquet(
        index_path, index=False, compression="zstd"
    )
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config", nargs="?", type=Path,
        default=Path("experiments/configs/stage4_signal_dispatch.toml"),
    )
    parser.add_argument(
        "--output-root", type=Path,
        default=Path("sweeps/stage4_signal_dispatch"),
    )
    args = parser.parse_args()
    print(run_campaign(args.config, args.output_root))


if __name__ == "__main__":
    main()
