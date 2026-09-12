"""Run the preregistered Stage 4 local signal-write mechanics assay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

from experiments.run_phase2_parasite_control import initial_occupied_order
from soup.config import Config
from soup.simulation import Simulation
from soup.substrate.bff import OP_SIGNAL_WRITE

SEEDS = range(202609270, 202609275)
ARMS: tuple[tuple[str, bool, str], ...] = (
    ("write_enabled", True, "aabbccdd"),
    ("write_disabled", False, "aabbccdd"),
    ("mismatched", True, "55667788"),
)
WRITER_BYTES = bytes.fromhex("aabbccdd") + bytes((OP_SIGNAL_WRITE,)) + bytes.fromhex("11223344") + bytes(7)


def writer_tape() -> np.ndarray[Any, np.dtype[np.uint8]]:
    return np.frombuffer(WRITER_BYTES, dtype=np.uint8).copy()


def profile(simulation: Simulation, occupied: set[int]) -> pd.DataFrame:
    if simulation.signals is None:
        raise RuntimeError("signal-write assay requires a signal field")
    indices = np.arange(simulation.world.capacity)
    return pd.DataFrame(
        {
            "flat_index": indices,
            "x": indices % simulation.config.world.width,
            "y": indices // simulation.config.world.width,
            "occupied": [int(index) in occupied for index in indices],
            "tag_hex": [bytes(row).hex() for row in simulation.signals.tags],
        }
    )


def run_campaign(
    config_path: Path,
    output_root: Path,
    seeds: Iterable[int] = SEEDS,
) -> Path:
    rows: list[dict[str, Any]] = []
    frozen_seeds = tuple(seeds)
    for arm, writes_enabled, tag_hex in ARMS:
        for seed in frozen_seeds:
            config = Config.load(config_path)
            config.run.seed = seed
            config.run.output_dir = str(output_root / "runs")
            config.signals.writes_enabled = writes_enabled
            config.signals.initial_tag_hex = tag_hex
            config.validate()
            occupied = initial_occupied_order(config)
            protocol = {
                "arm": arm,
                "writes_enabled": writes_enabled,
                "initial_tag_hex": tag_hex,
                "written_tag_hex": "11223344",
                "writer_tape_hex": WRITER_BYTES.hex(),
                "occupied_indices": sorted(occupied),
                "signal_write_target": "current interaction partner cell",
            }
            run_dir = output_root / "runs" / f"{arm}_seed_{seed}"
            manifest_path = run_dir / "manifest.json"
            protocol_path = run_dir / "signal_write_protocol.json"
            initial_path = run_dir / "signal_profile_initial.parquet"
            final_path = run_dir / "signal_profile_final.parquet"
            if all(path.exists() for path in (manifest_path, protocol_path, initial_path, final_path)):
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                existing = json.loads(protocol_path.read_text(encoding="utf-8"))
                if manifest.get("exit_status") != "success" or existing != protocol:
                    raise RuntimeError(f"incomplete or mismatched existing run: {run_dir}")
            else:
                simulation = Simulation(
                    config, run_dir=run_dir,
                    initial_tape_overrides={index: writer_tape() for index in occupied},
                )
                protocol_path.write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                occupied_set = set(occupied)
                profile(simulation, occupied_set).to_parquet(initial_path, index=False, compression="zstd")
                simulation.run()
                profile(simulation, occupied_set).to_parquet(final_path, index=False, compression="zstd")
            rows.append({"seed": seed, "arm": arm, "run_dir": str(run_dir)})
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = output_root / "index.parquet"
    pd.DataFrame(rows).sort_values(["arm", "seed"], ignore_index=True).to_parquet(index_path, index=False, compression="zstd")
    return index_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", nargs="?", type=Path, default=Path("experiments/configs/stage4_signal_write.toml"))
    parser.add_argument("--output-root", type=Path, default=Path("sweeps/stage4_signal_write"))
    args = parser.parse_args()
    print(run_campaign(args.config, args.output_root))


if __name__ == "__main__":
    main()
