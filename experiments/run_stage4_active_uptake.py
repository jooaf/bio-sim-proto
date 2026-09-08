"""Run the preregistered Stage 4 seeded active-uptake mechanics assay."""

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


SEEDS = range(202609210, 202609215)
ASSAY_TAPE = bytes((OP_ENERGY_UPTAKE, 0, 0, 0, 0, 0, 0, 0))
ASSAY_SHA256 = hashlib.sha256(ASSAY_TAPE).hexdigest()


def assay_tape() -> NDArray[np.uint8]:
    return np.frombuffer(ASSAY_TAPE, dtype=np.uint8).copy()


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
            run_dir = output_root / "runs" / f"{arm}_seed_{seed}"
            manifest_path = run_dir / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest.get("exit_status") != "success":
                    raise RuntimeError(f"incomplete existing assay run: {run_dir}")
            else:
                indices = initial_occupied_order(config)
                overrides = {index: assay_tape() for index in indices}
                Simulation(
                    config,
                    run_dir=run_dir,
                    initial_tape_overrides=overrides,
                ).run()
            rows.append(
                {
                    "seed": seed,
                    "active_uptake_enabled": enabled,
                    "assay_tape_sha256": ASSAY_SHA256,
                    "run_dir": str(run_dir),
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
        default=Path("experiments/configs/stage4_active_uptake.toml"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("sweeps/stage4_active_uptake"),
    )
    args = parser.parse_args()
    print(run_campaign(args.config, args.output_root))


if __name__ == "__main__":
    main()
