"""Run seeded BFF parasite positive-control development steps."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from soup.config import Config
from soup.rng import make_rng
from soup.simulation import Simulation


PARASITE_HEX = (
    "cda1b9cdfcffd3e15333691611dfbb4d3160426bb9bc465b3ca72466e02c8fea3"
    "250c9187df81cd35e5df4f87dd59adb8913295267a4f52c3c5b53194db269dd"
)
PARASITE_SHA256 = "c5688eb24e41bc415ac02194eacc3b5ba93297c458aee6cdf3527283bb317f62"
PARASITE_CONTENT_HASH = "81603f482497218f10250a43385710f6"
PARASITE_CHECKPOINT_SHA256 = "7530db43af8177bc141eda022ddc037edf61d48d1d6dbd73284f64c816d3c573"
DEFAULT_INSERTED_COUNT = 16


def parasite_tape() -> NDArray[np.uint8]:
    """Return a fresh copy of the frozen 64-byte parasite candidate."""

    tape = np.frombuffer(bytes.fromhex(PARASITE_HEX), dtype=np.uint8).copy()
    if hashlib.sha256(tape.tobytes()).hexdigest() != PARASITE_SHA256:
        raise RuntimeError("frozen parasite bytes do not match their declared SHA-256")
    return tape


def override_indices(config: Config, count: int) -> list[int]:
    """Select the first sorted occupied cells without consuming the simulation RNG."""

    capacity = config.world.width * config.world.height
    population = min(
        capacity,
        max(2, int(round(capacity * config.symbols.initial_tape_fill))),
    )
    if count <= 0 or count > population:
        raise ValueError("inserted parasite count must be in 1..initial population")
    rng = make_rng(config.run.seed)
    chosen = rng.permutation(capacity)[:population]
    return sorted(int(index) for index in chosen)[:count]


def protocol(config: Config, indices: list[int]) -> dict[str, Any]:
    """Return the complete experiment-specific initialization record."""

    return {
        "candidate_hex": PARASITE_HEX,
        "candidate_sha256": PARASITE_SHA256,
        "candidate_content_hash": PARASITE_CONTENT_HASH,
        "source_checkpoint_sha256": PARASITE_CHECKPOINT_SHA256,
        "candidate_functional_selfrep_score": 64,
        "candidate_checkpoint_abundance": 116,
        "family_definitions": {
            "exact": "all 64 bytes equal candidate",
            "near": "Hamming distance from candidate <= 8",
            "opcode": "ordered BFF opcode sequence equals candidate",
        },
        "inserted_count": len(indices),
        "flat_indices": indices,
        "cells": [[index % config.world.width, index // config.world.width] for index in indices],
    }


def run_one(config_path: Path, seed: int, output_root: Path, inserted_count: int) -> Path:
    """Run or resume one exact config/seed/candidate positive-control replicate."""

    config = Config.load(config_path)
    config.run.seed = seed
    config.run.output_dir = str(output_root)
    config.validate()
    indices = override_indices(config, inserted_count)
    run_dir = output_root / f"seed_{seed}"
    protocol_path = run_dir / "parasite_protocol.json"
    manifest_path = run_dir / "manifest.json"
    expected_protocol = protocol(config, indices)
    if manifest_path.exists() and protocol_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing_protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        if manifest.get("exit_status") == "success" and existing_protocol == expected_protocol:
            return run_dir
        raise FileExistsError(f"refusing to overwrite incomplete or mismatched run: {run_dir}")
    candidate = parasite_tape()
    overrides = {index: candidate for index in indices}
    simulation = Simulation(
        config,
        run_dir=run_dir,
        initial_tape_overrides=overrides,
    )
    protocol_path.write_text(
        json.dumps(expected_protocol, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return simulation.run()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--start-seed", type=int, required=True)
    parser.add_argument("--n-seeds", type=int, required=True)
    parser.add_argument("--inserted-count", type=int, default=DEFAULT_INSERTED_COUNT)
    args = parser.parse_args()
    if args.n_seeds <= 0:
        raise ValueError("n-seeds must be positive")
    args.output_root.mkdir(parents=True, exist_ok=True)
    paths = [
        run_one(args.config, seed, args.output_root, args.inserted_count)
        for seed in range(args.start_seed, args.start_seed + args.n_seeds)
    ]
    index = {
        "config": str(args.config),
        "start_seed": args.start_seed,
        "n_seeds": args.n_seeds,
        "inserted_count": args.inserted_count,
        "run_dirs": [str(path) for path in paths],
    }
    index_path = args.output_root / "index.json"
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(index_path)


if __name__ == "__main__":
    main()
