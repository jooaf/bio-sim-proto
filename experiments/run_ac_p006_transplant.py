"""AC-P006 frozen transplantation mechanics; preparation is the default CLI action.

Use --execute explicitly to launch the prepared twenty-run campaign. Preparation
verifies first-origin sources, scores each single frozen shuffle once, and saves
all paired inputs before any simulation process is started.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, cast

import numpy as np
from numpy.typing import NDArray

from experiments import analyze_ac_p003_functional_origin_convergence as source
from experiments.paper_probe import initialize_soup, score_selfrep_candidates, shuffle_indices
from experiments.phase1_probe import exact_tape_count, file_sha256

U8 = NDArray[np.uint8]
SOURCE_SEEDS = (202615001, 202615004, 202615006, 202615007, 202615008,
                202615011, 202615014, 202615015, 202615017, 202615018)
POPULATION = 32768
COPIES = 32
DOMAIN = 0xAC006


def shuffled_control(witness: U8, index: int) -> U8:
    if witness.dtype != np.uint8 or witness.shape != (64,) or not 0 <= index < 10:
        raise ValueError("expected uint8 witness of length 64 and index 0..9")
    control = witness.copy()
    for i in range(63, 0, -1):
        j = source.splitmix64(DOMAIN ^ source.splitmix64(index * 64 + i)) % (i + 1)
        control[i], control[j] = control[j], control[i]
    return control


def validate_control(witness: U8, control: U8) -> int:
    if control.dtype != np.uint8 or control.shape != (64,):
        raise ValueError("invalid control tape")
    if np.array_equal(witness, control) or not np.array_equal(
        np.bincount(witness, minlength=256), np.bincount(control, minlength=256)
    ):
        raise ValueError("invalid control construction: unchanged or composition mismatch")
    evaluator = cast(Callable[[U8, int], NDArray[np.int64]], score_selfrep_candidates)
    score = int(evaluator(control.reshape(1, 64), 0)[0])
    if not 0 <= score < 64:
        raise ValueError("invalid control construction: control score must be below 64")
    return score


def paired_inocula(witness: U8, control: U8, index: int) -> tuple[U8, U8, NDArray[np.uint32]]:
    """Use the frozen recipient seed, size, copy count and replacement domain."""
    if not 0 <= index < 10 or any(t.shape != (64,) or t.dtype != np.uint8 for t in (witness, control)):
        raise ValueError("invalid pair arguments")
    if not np.array_equal(np.bincount(witness, minlength=256), np.bincount(control, minlength=256)):
        raise ValueError("inocula composition mismatch")
    initialize = cast(Callable[[int, int], U8], initialize_soup)
    shuffle = cast(Callable[[NDArray[np.uint32], int, int], None], shuffle_indices)
    background = initialize(POPULATION, 202616000 + index)
    order = np.arange(POPULATION, dtype=np.uint32)
    shuffle(order, 202616000 + index, DOMAIN + index)
    indices = order[:COPIES].copy()
    left, right = background.copy(), background.copy()
    left[indices], right[indices] = witness, control
    if not np.array_equal(np.bincount(left.ravel(), minlength=256), np.bincount(right.ravel(), minlength=256)):
        raise ValueError("paired initial histogram mismatch")
    return left, right, indices


def prepare(source_root: Path, output: Path) -> list[list[str]]:
    """Fail closed on any source/control error before constructing recipient soups."""
    validated = []
    for index, seed in enumerate(SOURCE_SEEDS):
        run = source.Run("AC-P005", 16, seed)
        checkpoint = source.load_checkpoint(source_root / (run.name + "_prectrlv1"), run)
        witness = checkpoint.witness.copy()
        control = shuffled_control(witness, index)
        score = validate_control(witness, control)
        validated.append((checkpoint, witness, control, score))
    output.mkdir(parents=True, exist_ok=False)
    commands: list[list[str]] = []
    pairs: list[dict[str, Any]] = []
    for index, (checkpoint, witness, control, score) in enumerate(validated):
        left, right, indices = paired_inocula(witness, control, index)
        pair: dict[str, Any] = {
            "index": index, "source_seed": SOURCE_SEEDS[index], "recipient_seed": 202616000 + index,
            "source_checksums": checkpoint.checksums, "source_epoch": checkpoint.epoch,
            "witness_rank": checkpoint.witness_rank, "witness_score": 64, "control_score": score,
            "hamming_changes": int(np.count_nonzero(witness != control)),
            "replacement_indices": indices.tolist(), "arms": {},
        }
        histograms = []
        for arm, soup, target in (("witness", left, witness), ("shuffle", right, control)):
            path = (output / f"pair_{index:02d}_{arm}.npy").resolve()
            np.save(path, soup)
            saved = np.load(path, allow_pickle=False)
            if not np.array_equal(saved, soup):
                raise ValueError("saved initial soup mismatch")
            histogram = np.bincount(saved.ravel(), minlength=256).astype(np.int64)
            histograms.append(histogram)
            count = exact_tape_count(saved, target.tobytes())
            if count < COPIES:
                raise ValueError("initial exact count below inoculum size")
            pair["arms"][arm] = {"path": str(path), "sha256": file_sha256(path),
                                  "target_hex": target.tobytes().hex(), "initial_exact_target_count": count}
            commands.append([
                sys.executable, "-m", "experiments.phase1_probe", "--population-size", str(POPULATION),
                "--epochs", "10000", "--seed", str(202616000 + index), "--mutation-rate", str(1 / 4096),
                "--pool-multiplier", "16", "--callback-interval", "100", "--max-steps", "8192",
                "--initial-soup", str(path), "--tracked-tape-hex", target.tobytes().hex(),
                "--save-final-soup", str((output / f"final_{index:02d}_{arm}.npy").resolve()),
                "--output-dir", str((output / "runs").resolve()),
            ])
        if not np.array_equal(histograms[0], histograms[1]):
            raise ValueError("saved pair histogram mismatch")
        pair["initial_histogram"] = histograms[0].tolist()
        pair["initial_pool"] = (histograms[0] * 16).tolist()
        pairs.append(pair)
    (output / "preparation.json").write_text(json.dumps({"campaign": "AC-P006", "pairs": pairs,
        "commands": commands}, indent=2, sort_keys=True) + "\n")
    return commands


def execute(commands: list[list[str]]) -> None:
    env = {**os.environ, "NUMBA_NUM_THREADS": "1"}
    def run(command: list[str]) -> None:
        subprocess.run(command, env=env, check=True, cwd=Path(__file__).resolve().parents[1])
    with ThreadPoolExecutor(max_workers=6) as workers:
        list(workers.map(run, commands))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="new preparation directory")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    commands = prepare(args.source_root, args.output_dir)
    if args.execute:
        execute(commands)


if __name__ == "__main__":
    main()
