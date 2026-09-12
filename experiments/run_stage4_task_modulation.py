"""Run the preregistered task-relevant signal-modulation campaign."""

from __future__ import annotations

import argparse
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

SEEDS = range(202609300, 202609310)
CORRECT_BYTES = bytes.fromhex("aabbccdd") + bytes((OP_ENERGY_UPTAKE, 0, 0, 0)) + bytes.fromhex("11223344") + bytes(4)
INCORRECT_BYTES = bytes.fromhex("aabbccdd") + bytes(4) + bytes.fromhex("11223344") + bytes((OP_ENERGY_UPTAKE, 0, 0, 0))


def tape(raw: bytes) -> NDArray[np.uint8]:
    return np.frombuffer(raw, dtype=np.uint8).copy()


def assignment(config: Config) -> tuple[dict[int, NDArray[np.uint8]], dict[str, Any]]:
    occupied = initial_occupied_order(config)
    tape_ids = {index: tape_id for tape_id, index in enumerate(occupied)}
    overrides: dict[int, NDArray[np.uint8]] = {}
    records: list[dict[str, Any]] = []
    for position, index in enumerate(sorted(occupied)):
        correct = position % 2 == config.run.seed % 2
        type_name = "correct" if correct else "incorrect"
        raw = CORRECT_BYTES if correct else INCORRECT_BYTES
        overrides[index] = tape(raw)
        records.append({
            "tape_id": tape_ids[index], "flat_index": index,
            "cell": [index % config.world.width, index // config.world.width],
            "type": type_name, "hex": raw.hex(),
        })
    return overrides, {
        "assignment_rule": "sorted cells alternate; correct parity equals seed parity",
        "correct_count": 8, "incorrect_count": 8, "records": records,
    }


def run_campaign(config_path: Path, output_root: Path) -> Path:
    rows: list[dict[str, Any]] = []
    for enabled in (False, True):
        arm = "task_enabled" if enabled else "task_disabled"
        for seed in SEEDS:
            config = Config.load(config_path)
            config.run.seed = seed; config.run.output_dir = str(output_root / "runs")
            config.task.enabled = enabled; config.validate()
            overrides, protocol = assignment(config)
            protocol |= {"arm": arm, "task_enabled": enabled, "task_bonus": 3.0, "task_spec": "signal_uptake"}
            run_dir = output_root / "runs" / f"{arm}_seed_{seed}"
            manifest_path = run_dir / "manifest.json"; protocol_path = run_dir / "task_modulation_protocol.json"; scores_path = run_dir / "task_scores_final.parquet"
            if all(path.exists() for path in (manifest_path, protocol_path, scores_path)):
                manifest = json.loads(manifest_path.read_text(encoding="utf-8")); existing = json.loads(protocol_path.read_text(encoding="utf-8"))
                if manifest.get("exit_status") != "success" or existing != protocol: raise RuntimeError(f"incomplete or mismatched existing run: {run_dir}")
            else:
                simulation = Simulation(config, run_dir=run_dir, initial_tape_overrides=overrides)
                protocol_path.write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                simulation.run()
                scores = np.zeros(simulation.world.capacity) if simulation.task is None else simulation.task.scores
                type_by_index = {int(record["flat_index"]): str(record["type"]) for record in protocol["records"]}
                indices = np.arange(simulation.world.capacity)
                pd.DataFrame({"flat_index": indices, "x": indices % config.world.width, "y": indices // config.world.width, "type": [type_by_index[int(index)] for index in indices], "score": scores}).to_parquet(scores_path, index=False, compression="zstd")
            rows.append({"seed": seed, "arm": arm, "task_enabled": enabled, "run_dir": str(run_dir)})
    output_root.mkdir(parents=True, exist_ok=True); index_path = output_root / "index.parquet"
    pd.DataFrame(rows).sort_values(["task_enabled", "seed"], ignore_index=True).to_parquet(index_path, index=False, compression="zstd"); return index_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("config", nargs="?", type=Path, default=Path("experiments/configs/stage4_task_modulation.toml")); parser.add_argument("--output-root", type=Path, default=Path("sweeps/stage4_task_modulation")); args = parser.parse_args(); print(run_campaign(args.config, args.output_root))


if __name__ == "__main__": main()
