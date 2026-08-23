"""Accelerated paper-protocol BFF emergence probe.

This deliberately emits bounded aggregate data rather than raw interaction tables: the
paper-scale protocol performs roughly one billion interactions per run. The ordinary
``Simulation`` remains the detailed trace backend for small runs.
"""

from __future__ import annotations

import argparse
import csv
import math
import time
from pathlib import Path

import brotli
import numba as nb
import numpy as np
from numpy.typing import NDArray

from analysis.complexity import byte_entropy


TAPE_LENGTH = 64
JOINT_LENGTH = 2 * TAPE_LENGTH
MIX_INCREMENT = np.uint64(0x9E3779B97F4A7C15)
MIX_FIRST = np.uint64(0xBF58476D1CE4E5B9)
MIX_SECOND = np.uint64(0x94D049BB133111EB)


@nb.njit(nb.uint64(nb.uint64), inline="always")
def splitmix64(value: np.uint64) -> np.uint64:
    """Match the unsigned SplitMix64 function used by the paper implementation."""

    z = value + MIX_INCREMENT
    z = (z ^ (z >> np.uint64(30))) * MIX_FIRST
    z = (z ^ (z >> np.uint64(27))) * MIX_SECOND
    return z ^ (z >> np.uint64(31))


@nb.njit(nb.uint64(nb.uint64, nb.uint64), inline="always")
def derived_seed(base_seed: np.uint64, value: np.uint64) -> np.uint64:
    return splitmix64(splitmix64(base_seed) ^ splitmix64(value))


@nb.njit
def initialize_soup(population_size: int, seed: int) -> NDArray[np.uint8]:
    """Initialize uniform bytes with the reference implementation's deterministic stream."""

    soup = np.empty((population_size, TAPE_LENGTH), dtype=np.uint8)
    initial_seed = derived_seed(np.uint64(seed), np.uint64(0))
    offset = np.uint64(TAPE_LENGTH * population_size) * initial_seed
    for tape_index in range(population_size):
        for byte_index in range(TAPE_LENGTH):
            value = offset + np.uint64(TAPE_LENGTH * tape_index + byte_index)
            soup[tape_index, byte_index] = splitmix64(value) & 0xFF
    return soup


@nb.njit
def shuffle_indices(order: NDArray[np.uint32], seed: int, epoch: int) -> None:
    """Apply the paper implementation's seeded Fisher-Yates shuffle in place."""

    population_size = len(order)
    for index in range(population_size):
        order[index] = index
    for index in range(population_size - 1, -1, -1):
        draw = splitmix64(
            derived_seed(np.uint64(seed), np.uint64(epoch * population_size + index))
        )
        other = int(draw % np.uint64(index + 1))
        temporary = order[index]
        order[index] = order[other]
        order[other] = temporary


@nb.njit(inline="always")
def execute_bff(joint: NDArray[np.uint8], max_steps: int) -> int:
    """Execute the released bff_noheads semantics and return character reads."""

    pc = 0
    head0 = 0
    head1 = 0
    steps = 0
    while steps < max_steps and 0 <= pc < JOINT_LENGTH:
        op = joint[pc]
        steps += 1
        next_pc = pc + 1
        if op == 60:  # <
            head0 = (head0 - 1) & (JOINT_LENGTH - 1)
        elif op == 62:  # >
            head0 = (head0 + 1) & (JOINT_LENGTH - 1)
        elif op == 123:  # {
            head1 = (head1 - 1) & (JOINT_LENGTH - 1)
        elif op == 125:  # }
            head1 = (head1 + 1) & (JOINT_LENGTH - 1)
        elif op == 43:  # +
            joint[head0] = (int(joint[head0]) + 1) & 0xFF
        elif op == 45:  # -
            joint[head0] = (int(joint[head0]) - 1) & 0xFF
        elif op == 46:  # .
            joint[head1] = joint[head0]
        elif op == 44:  # ,
            joint[head0] = joint[head1]
        elif op == 91 and joint[head0] == 0:  # [
            depth = 1
            candidate = pc + 1
            while candidate < JOINT_LENGTH and depth:
                if joint[candidate] == 91:
                    depth += 1
                elif joint[candidate] == 93:
                    depth -= 1
                candidate += 1
            if depth:
                break
            next_pc = candidate
        elif op == 93 and joint[head0] != 0:  # ]
            depth = 1
            candidate = pc - 1
            while candidate >= 0 and depth:
                if joint[candidate] == 93:
                    depth += 1
                elif joint[candidate] == 91:
                    depth -= 1
                candidate -= 1
            if depth:
                break
            next_pc = candidate + 2
        pc = next_pc
    return steps


@nb.njit(parallel=True)
def mutate_and_execute_epoch(
    soup: NDArray[np.uint8],
    order: NDArray[np.uint32],
    seed: int,
    epoch: int,
    mutation_threshold: int,
    max_steps: int,
) -> int:
    """Mutate and execute all disjoint ordered pairs for one epoch."""

    population_size = len(soup)
    step_counts = np.zeros(population_size // 2, dtype=np.int64)
    epoch_seed = derived_seed(np.uint64(seed), np.uint64(epoch))
    for pair_index in nb.prange(population_size // 2):
        first = order[2 * pair_index]
        second = order[2 * pair_index + 1]
        joint = np.empty(JOINT_LENGTH, dtype=np.uint8)
        joint[:TAPE_LENGTH] = soup[first]
        joint[TAPE_LENGTH:] = soup[second]
        for byte_index in range(JOINT_LENGTH):
            random_value = splitmix64(
                (np.uint64(population_size) * epoch_seed + np.uint64(pair_index))
                * np.uint64(JOINT_LENGTH)
                + np.uint64(byte_index)
            )
            probability_draw = (random_value >> np.uint64(8)) & np.uint64((1 << 30) - 1)
            if probability_draw < np.uint64(mutation_threshold):
                joint[byte_index] = random_value & 0xFF
        step_counts[pair_index] = execute_bff(joint, max_steps)
        soup[first] = joint[:TAPE_LENGTH]
        soup[second] = joint[TAPE_LENGTH:]
    return int(np.sum(step_counts))


@nb.njit
def functional_selfrep_score(program: NDArray[np.uint8], seed: int) -> int:
    """Return the released evaluator's minimum stable-byte score across both tapes."""

    outputs = np.empty((13, JOINT_LENGTH), dtype=np.uint8)
    local_seed = splitmix64(np.uint64(seed))
    for iteration in range(13):
        noise = np.empty(TAPE_LENGTH, dtype=np.uint8)
        for byte_index in range(TAPE_LENGTH):
            noise[byte_index] = splitmix64(
                local_seed
                ^ splitmix64(np.uint64((iteration + 1) * TAPE_LENGTH + byte_index))
            ) & np.uint64(0xFF)
        joint = np.empty(JOINT_LENGTH, dtype=np.uint8)
        joint[:TAPE_LENGTH] = program
        joint[TAPE_LENGTH:] = noise
        execute_bff(joint, 8192)
        for _ in range(4):
            joint[:TAPE_LENGTH] = joint[TAPE_LENGTH:]
            joint[TAPE_LENGTH:] = noise
            execute_bff(joint, 8192)
        outputs[iteration] = joint

    stable = np.zeros(2, dtype=np.int64)
    for position in range(JOINT_LENGTH):
        for first in range(13):
            count = 1
            for second in range(first + 1, 13):
                if outputs[first, position] == outputs[second, position]:
                    count += 1
            if count > 3:
                stable[position // TAPE_LENGTH] += 1
                break
    return int(min(stable[0], stable[1]))


@nb.njit(parallel=True)
def score_selfrep_candidates(candidates: NDArray[np.uint8], seed: int) -> NDArray[np.int64]:
    """Score candidate tapes independently with the paper's functional proxy."""

    scores = np.empty(len(candidates), dtype=np.int64)
    for index in nb.prange(len(candidates)):
        scores[index] = functional_selfrep_score(candidates[index], seed + index)
    return scores


def complexity_row(soup: NDArray[np.uint8], epoch: int, elapsed: float, total_steps: int) -> dict[str, int | float]:
    """Return the paper's aggregate state-transition metrics."""

    content = soup.tobytes()
    entropy = byte_entropy(content)
    compressed_size = len(brotli.compress(content, quality=2, lgwin=24))
    compressed_bpb = 8.0 * compressed_size / len(content)
    return {
        "epoch": epoch,
        "elapsed_seconds": elapsed,
        "character_reads": total_steps,
        "byte_entropy": entropy,
        "brotli_size": compressed_size,
        "compressed_bpb": compressed_bpb,
        "high_order_entropy": entropy - compressed_bpb,
    }


def run_probe(
    *,
    population_size: int,
    epochs: int,
    seed: int,
    mutation_rate: float,
    callback_interval: int,
    output: Path,
    checkpoint: Path | None = None,
    initial_soup: Path | None = None,
    epoch_offset: int = 0,
) -> Path:
    """Run one bounded-log paper protocol probe and write metrics incrementally."""

    if population_size <= 0 or population_size % 2:
        raise ValueError("population_size must be a positive even number")
    if not 0.0 <= mutation_rate <= 1.0:
        raise ValueError("mutation_rate must be in 0..1")
    if epochs <= 0 or callback_interval <= 0:
        raise ValueError("epochs and callback_interval must be positive")
    if epoch_offset < 0:
        raise ValueError("epoch_offset must be nonnegative")

    if initial_soup is None:
        soup = initialize_soup(population_size, seed)
    else:
        loaded = np.load(initial_soup)
        if loaded.shape != (population_size, TAPE_LENGTH) or loaded.dtype != np.uint8:
            raise ValueError(
                f"initial soup {initial_soup} must be uint8 of shape "
                f"({population_size}, {TAPE_LENGTH}); got {loaded.dtype} {loaded.shape}"
            )
        soup = loaded.copy()
    order = np.arange(population_size, dtype=np.uint32)
    mutation_threshold = round(mutation_rate * (1 << 30))
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "epoch",
        "elapsed_seconds",
        "character_reads",
        "byte_entropy",
        "brotli_size",
        "compressed_bpb",
        "high_order_entropy",
        "dominant_tape_count",
        "dominant_tape_fraction",
        "distinct_tapes",
    ]
    started = time.perf_counter()
    total_steps = 0
    checkpoint_saved = False
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for epoch in range(epochs):
            stream_epoch = epoch + epoch_offset
            shuffle_indices(order, seed, stream_epoch)
            total_steps += mutate_and_execute_epoch(
                soup,
                order,
                seed,
                stream_epoch,
                mutation_threshold,
                8192,
            )
            if epoch % callback_interval == 0 or epoch + 1 == epochs:
                row = complexity_row(soup, epoch + 1, time.perf_counter() - started, total_steps)
                _, counts = np.unique(soup, axis=0, return_counts=True)
                row["dominant_tape_count"] = int(counts.max())
                row["dominant_tape_fraction"] = float(counts.max() / population_size)
                row["distinct_tapes"] = int(len(counts))
                writer.writerow(row)
                handle.flush()
                if (
                    checkpoint is not None
                    and not checkpoint_saved
                    and float(row["high_order_entropy"]) >= 1.0
                ):
                    checkpoint.parent.mkdir(parents=True, exist_ok=True)
                    np.save(checkpoint, soup)
                    checkpoint_saved = True
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population-size", type=int, default=131_072)
    parser.add_argument("--epochs", type=int, default=16_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--mutation-rate", type=float, default=1.0 / 4096.0)
    parser.add_argument("--callback-interval", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--initial-soup", type=Path)
    parser.add_argument("--epoch-offset", type=int, default=0)
    args = parser.parse_args()
    print(
        run_probe(
            population_size=args.population_size,
            epochs=args.epochs,
            seed=args.seed,
            mutation_rate=args.mutation_rate,
            callback_interval=args.callback_interval,
            output=args.output,
            checkpoint=args.checkpoint,
            initial_soup=args.initial_soup,
            epoch_offset=args.epoch_offset,
        )
    )


if __name__ == "__main__":
    main()
