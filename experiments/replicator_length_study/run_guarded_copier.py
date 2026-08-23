#!/usr/bin/env python3
"""Run one guarded-copier within-family pair-soup intervention replicate.

Each tape uses a four-symbol alphabet.  The sole active instruction is COPY
(symbol 3).  It has exactly the same action in every condition: copy the entire
first tape of an ordered pair into the second tape.  COPY is enabled only when
its following credential bytes match a fixed family code.  Increasing the
credential length changes the known functional-basin density without changing
pairing, mutation, copy action, tape size, or instruction budget.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from numpy.typing import NDArray


ALPHABET_SIZE = 4
COPY = np.uint8(3)
Initialization = Literal["seeded", "random"]


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    """Fully resolved protocol for one intervention replicate."""

    initialization: Initialization
    credential_length: int
    population_size: int
    tape_length: int
    ticks: int
    seed: int
    mutation_rate: float
    execution_budget: int
    seeded_copies: int
    metric_interval: int
    takeover_fraction: float

    def validate(self) -> None:
        if self.initialization not in {"seeded", "random"}:
            raise ValueError("initialization must be seeded or random")
        if self.credential_length < 1:
            raise ValueError("credential_length must be positive")
        if self.tape_length <= self.credential_length:
            raise ValueError("tape_length must exceed credential_length")
        if self.population_size < 2 or self.population_size % 2:
            raise ValueError("population_size must be an even integer of at least two")
        if self.ticks < 1 or self.execution_budget < 1 or self.metric_interval < 1:
            raise ValueError("ticks, execution_budget, and metric_interval must be positive")
        if not 0.0 <= self.mutation_rate <= 1.0:
            raise ValueError("mutation_rate must be in 0..1")
        if self.seeded_copies < 0 or self.seeded_copies > self.population_size:
            raise ValueError("seeded_copies must be in 0..population_size")
        if self.initialization == "random" and self.seeded_copies:
            raise ValueError("random initialization cannot include seeded copies")
        if self.initialization == "seeded" and not self.seeded_copies:
            raise ValueError("seeded initialization requires at least one seeded copy")
        if not 0.0 < self.takeover_fraction <= 1.0:
            raise ValueError("takeover_fraction must be in (0, 1]")

    @property
    def functional_information_bits(self) -> int:
        """Information needed for COPY plus the credential in a uniform soup."""

        return int((self.credential_length + 1) * math.log2(ALPHABET_SIZE))

    @property
    def basin_density(self) -> float:
        """Exact fraction of uniform tapes that enable the fixed COPY action."""

        return float(ALPHABET_SIZE ** -(self.credential_length + 1))


def parse_args() -> tuple[ExperimentConfig, Path]:
    """Parse a single explicit replicate command."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initialization", choices=("seeded", "random"), required=True)
    parser.add_argument("--credential-length", type=int, required=True)
    parser.add_argument("--population-size", type=int, default=256)
    parser.add_argument("--tape-length", type=int, default=16)
    parser.add_argument("--ticks", type=int, default=512)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--mutation-rate", type=float, default=1.0 / 4096.0)
    parser.add_argument("--execution-budget", type=int, default=16)
    parser.add_argument("--seeded-copies", type=int, default=0)
    parser.add_argument("--metric-interval", type=int, default=1)
    parser.add_argument("--takeover-fraction", type=float, default=0.5)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    config = ExperimentConfig(
        initialization=args.initialization,
        credential_length=args.credential_length,
        population_size=args.population_size,
        tape_length=args.tape_length,
        ticks=args.ticks,
        seed=args.seed,
        mutation_rate=args.mutation_rate,
        execution_budget=args.execution_budget,
        seeded_copies=args.seeded_copies,
        metric_interval=args.metric_interval,
        takeover_fraction=args.takeover_fraction,
    )
    config.validate()
    return config, args.output_dir


def credential(length: int) -> NDArray[np.uint8]:
    """Return the fixed non-COPY guard sequence shared by one family condition."""

    return np.asarray([(2 * index + 1) % 3 for index in range(length)], dtype=np.uint8)


def seeded_replicator(config: ExperimentConfig) -> NDArray[np.uint8]:
    """Return the shortest active prefix followed by inert, heritable payload bytes."""

    tape = np.zeros(config.tape_length, dtype=np.uint8)
    tape[0] = COPY
    tape[1 : config.credential_length + 1] = credential(config.credential_length)
    return tape


def functional_mask(tapes: NDArray[np.uint8], config: ExperimentConfig) -> NDArray[np.bool_]:
    """Identify tapes that activate the invariant COPY instruction."""

    return np.asarray(
        (tapes[:, 0] == COPY)
        & np.all(tapes[:, 1 : config.credential_length + 1] == credential(config.credential_length), axis=1),
        dtype=np.bool_,
    )


def mutate(tapes: NDArray[np.uint8], rng: np.random.Generator, mutation_rate: float) -> int:
    """Apply the same independent uniform replacement process to every byte."""

    if mutation_rate == 0.0:
        return 0
    mask = rng.random(tapes.shape) < mutation_rate
    count = int(np.count_nonzero(mask))
    if count:
        tapes[mask] = rng.integers(0, ALPHABET_SIZE, size=count, dtype=np.uint8)
    return count


def run(config: ExperimentConfig, output_dir: Path) -> Path:
    """Execute one deterministic replicate and write compact, self-describing artifacts."""

    config.validate()
    output_dir.mkdir(parents=True, exist_ok=False)
    protocol = {
        **asdict(config),
        "alphabet_size": ALPHABET_SIZE,
        "copy_symbol": int(COPY),
        "copy_semantics": "if first tape is functional, replace second tape with an exact copy",
        "pairing": "shuffled_disjoint_ordered_pairs",
        "functional_information_bits": config.functional_information_bits,
        "functional_basin_density": config.basin_density,
        "credential": credential(config.credential_length).tolist(),
    }
    (output_dir / "protocol.json").write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "manifest.json").write_text(json.dumps({"status": "running", "protocol": protocol}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    try:
        rng = np.random.default_rng(config.seed)
        tapes = rng.integers(0, ALPHABET_SIZE, size=(config.population_size, config.tape_length), dtype=np.uint8)
        seed_tape = seeded_replicator(config)
        if config.initialization == "seeded":
            tapes[: config.seeded_copies] = seed_tape

        metric_fields = [
            "tick", "mutations", "pairs", "instruction_dispatches", "copy_events",
            "functional_count", "functional_fraction", "seed_exact_abundance",
        ]
        metrics_path = output_dir / "metrics.csv"
        initial_functional = int(np.count_nonzero(functional_mask(tapes, config)))
        initial_seed_exact = int(np.count_nonzero(np.all(tapes == seed_tape, axis=1)))
        copy_events_total = 0
        first_functional_tick: int | None = -1 if initial_functional else None
        takeover_tick: int | None = -1 if initial_functional >= math.ceil(config.takeover_fraction * config.population_size) else None
        with metrics_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=metric_fields)
            writer.writeheader()
            writer.writerow({
                "tick": -1, "mutations": 0, "pairs": 0, "instruction_dispatches": 0, "copy_events": 0,
                "functional_count": initial_functional, "functional_fraction": initial_functional / config.population_size,
                "seed_exact_abundance": initial_seed_exact,
            })
            for tick in range(config.ticks):
                mutations = mutate(tapes, rng, config.mutation_rate)
                order = rng.permutation(config.population_size)
                functional_before_pairs = functional_mask(tapes, config)
                copy_events = 0
                for pair_start in range(0, config.population_size, 2):
                    source = int(order[pair_start])
                    target = int(order[pair_start + 1])
                    if functional_before_pairs[source]:
                        tapes[target] = tapes[source]
                        copy_events += 1
                copy_events_total += copy_events
                functional_count = int(np.count_nonzero(functional_mask(tapes, config)))
                seed_exact_abundance = int(np.count_nonzero(np.all(tapes == seed_tape, axis=1)))
                if functional_count and first_functional_tick is None:
                    first_functional_tick = tick
                if functional_count >= math.ceil(config.takeover_fraction * config.population_size) and takeover_tick is None:
                    takeover_tick = tick
                if tick % config.metric_interval == 0 or tick + 1 == config.ticks:
                    writer.writerow({
                        "tick": tick,
                        "mutations": mutations,
                        "pairs": config.population_size // 2,
                        "instruction_dispatches": config.population_size // 2,
                        "copy_events": copy_events,
                        "functional_count": functional_count,
                        "functional_fraction": functional_count / config.population_size,
                        "seed_exact_abundance": seed_exact_abundance,
                    })

        final_functional = int(np.count_nonzero(functional_mask(tapes, config)))
        summary = {
            "protocol": protocol,
            "aggregate": {
                "initial_functional_count": initial_functional,
                "initial_seed_exact_abundance": initial_seed_exact,
                "first_functional_tick": first_functional_tick,
                "takeover_tick": takeover_tick,
                "final_functional_count": final_functional,
                "copy_events": copy_events_total,
                "validation_passed": config.initialization != "seeded" or copy_events_total > 0,
            },
        }
        (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output_dir / "manifest.json").write_text(json.dumps({"status": "success", **summary}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except BaseException as error:
        (output_dir / "manifest.json").write_text(json.dumps({"status": "failed", "error": repr(error), "protocol": protocol}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise
    return output_dir


def main() -> None:
    """Run the CLI protocol and print the resulting artifact directory."""

    config, output_dir = parse_args()
    print(run(config, output_dir))


if __name__ == "__main__":
    main()
