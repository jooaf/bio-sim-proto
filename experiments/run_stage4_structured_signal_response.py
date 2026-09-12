"""Run the preregistered structured read-only signal-response assay."""

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

SEEDS = range(202609290, 202609295)
ARMS: tuple[tuple[str, bool, str], ...] = (
    ("split", True, "split_x"),
    ("uniform", True, "uniform"),
    ("disabled", False, "split_x"),
)
DUAL_HANDLER_BYTES = (
    bytes.fromhex("aabbccdd") + bytes((OP_ENERGY_UPTAKE, 0, 0, 0))
    + bytes.fromhex("11223344") + bytes(4)
)


def dual_handler_tape() -> np.ndarray[Any, np.dtype[np.uint8]]:
    return np.frombuffer(DUAL_HANDLER_BYTES, dtype=np.uint8).copy()


def run_campaign(config_path: Path, output_root: Path) -> Path:
    rows: list[dict[str, Any]] = []
    for arm, enabled, signal_spec in ARMS:
        for seed in SEEDS:
            config = Config.load(config_path)
            config.run.seed = seed
            config.run.output_dir = str(output_root / "runs")
            config.signals.enabled = enabled
            config.signals.signal_spec = signal_spec
            config.validate()
            occupied = initial_occupied_order(config)
            protocol = {
                "arm": arm,
                "signals_enabled": enabled,
                "signal_spec": signal_spec,
                "primary_tag_hex": "aabbccdd",
                "secondary_tag_hex": "11223344",
                "dual_handler_tape_hex": DUAL_HANDLER_BYTES.hex(),
                "seeded_count": len(occupied),
            }
            run_dir = output_root / "runs" / f"{arm}_seed_{seed}"
            manifest_path = run_dir / "manifest.json"
            protocol_path = run_dir / "structured_signal_response_protocol.json"
            profile_path = run_dir / "signal_profile.parquet"
            if all(path.exists() for path in (manifest_path, protocol_path, profile_path)):
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                existing = json.loads(protocol_path.read_text(encoding="utf-8"))
                if manifest.get("exit_status") != "success" or existing != protocol:
                    raise RuntimeError(f"incomplete or mismatched existing run: {run_dir}")
            else:
                simulation = Simulation(
                    config, run_dir=run_dir,
                    initial_tape_overrides={index: dual_handler_tape() for index in occupied},
                )
                protocol_path.write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                indices = np.arange(simulation.world.capacity)
                tags = (
                    [config.signals.initial_tag_hex] * simulation.world.capacity
                    if simulation.signals is None
                    else [bytes(tag).hex() for tag in simulation.signals.tags]
                )
                pd.DataFrame(
                    {"flat_index": indices, "x": indices % config.world.width,
                     "y": indices // config.world.width, "tag_hex": tags}
                ).to_parquet(profile_path, index=False, compression="zstd")
                simulation.run()
            rows.append({"seed": seed, "arm": arm, "run_dir": str(run_dir)})
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = output_root / "index.parquet"
    pd.DataFrame(rows).sort_values(["arm", "seed"], ignore_index=True).to_parquet(index_path, index=False, compression="zstd")
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", nargs="?", type=Path, default=Path("experiments/configs/stage4_structured_signal_response.toml"))
    parser.add_argument("--output-root", type=Path, default=Path("sweeps/stage4_structured_signal_response"))
    args = parser.parse_args()
    print(run_campaign(args.config, args.output_root))


if __name__ == "__main__":
    main()
