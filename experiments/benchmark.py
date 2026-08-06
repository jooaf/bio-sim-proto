"""Benchmark the unoptimized plain-Python BFF hot loop."""

from __future__ import annotations

import argparse
import time

import numpy as np

from soup.substrate.base import ExecutionBudget
from soup.substrate.bff import BFFSubstrate


def benchmark(interactions: int, seed: int) -> tuple[int, float, float]:
    rng = np.random.Generator(np.random.PCG64(seed))
    substrate = BFFSubstrate()
    budget = ExecutionBudget(max_steps=8192)
    steps = 0
    started = time.perf_counter()
    for _ in range(interactions):
        joint = np.concatenate((substrate.random_tape(rng), substrate.random_tape(rng)))
        steps += substrate.execute(joint, None, budget, None).steps_executed
    elapsed = time.perf_counter() - started
    return steps, elapsed, steps / elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interactions", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    steps, elapsed, rate = benchmark(args.interactions, args.seed)
    print(f"steps={steps} seconds={elapsed:.6f} steps_per_second={rate:.2f}")


if __name__ == "__main__":
    main()
