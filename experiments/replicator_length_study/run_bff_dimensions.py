#!/usr/bin/env python3
"""Run a documented, bounded BFF 0D/1D/2D replicator-emergence experiment.

The implementation intentionally reuses the repository's reference BFF
interpreter. Results are compact CSV/JSON artifacts local to this experiment
folder; this is not a replacement for the paper-scale Numba probe.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Mapping, cast

import brotli  # type: ignore[import-untyped]
import numpy as np
from numpy.random import Generator
from numpy.typing import NDArray

from analysis.complexity import byte_entropy
from experiments.paper_probe import score_selfrep_candidates
from soup.substrate.base import ExecutionBudget
from soup.substrate.bff import BFFSubstrate


Dimension = Literal[0, 1, 2]


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    """Fully specified parameters for one bounded experiment run."""

    dimension: Dimension
    population_size: int
    width: int
    height: int
    radius: int
    ticks: int
    seed: int
    mutation_rate: float
    max_steps: int
    metric_interval: int
    functional_sample_size: int
    functional_density_samples: int
    functional_threshold: int
    takeover_fraction: float

    def validate(self) -> None:
        if self.dimension not in {0, 1, 2}:
            raise ValueError("dimension must be 0, 1, or 2")
        if self.population_size < 2:
            raise ValueError("population_size must be at least two")
        if self.width < 2 or self.height < 1:
            raise ValueError("width must be at least 2 and height at least 1")
        if self.dimension == 1 and self.population_size != self.width:
            raise ValueError("1D population_size must equal width")
        if self.dimension == 2 and self.population_size != self.width * self.height:
            raise ValueError("2D population_size must equal width * height")
        if self.radius < 1:
            raise ValueError("radius must be positive")
        if self.ticks < 1 or self.max_steps < 1 or self.metric_interval < 1:
            raise ValueError("ticks, max_steps, and metric_interval must be positive")
        if not 0.0 <= self.mutation_rate <= 1.0:
            raise ValueError("mutation_rate must be in 0..1")
        if self.functional_sample_size < 1 or self.functional_density_samples < 1:
            raise ValueError("functional sample sizes must be positive")
        if self.functional_threshold < 0:
            raise ValueError("functional_threshold must be nonnegative")
        if not 0.0 < self.takeover_fraction <= 1.0:
            raise ValueError("takeover_fraction must be in (0, 1]")


@dataclass(slots=True)
class Discovery:
    """Exact-content functional type observed in the sampled functional assay."""

    content_hash: str
    first_tick: int
    functional_score: int
    first_abundance: int
    extinction_tick: int | None = None
    takeover_tick: int | None = None


def parse_args() -> tuple[ExperimentConfig, Path]:
    """Parse and validate the explicit experiment protocol."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dimension", choices=("0", "1", "2"), required=True)
    parser.add_argument("--population-size", type=int, required=True)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--radius", type=int, default=2)
    parser.add_argument("--ticks", type=int, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--mutation-rate", type=float, default=1.0 / 4096.0)
    parser.add_argument("--max-steps", type=int, default=8192)
    parser.add_argument("--metric-interval", type=int, default=1)
    parser.add_argument("--functional-sample-size", type=int, default=32)
    parser.add_argument("--functional-density-samples", type=int, default=256)
    parser.add_argument("--functional-threshold", type=int, default=6)
    parser.add_argument("--takeover-fraction", type=float, default=0.5)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    dimension = cast(Dimension, int(args.dimension))
    if dimension == 2 and (args.width is None or args.height is None):
        parser.error("2D requires both --width and --height")
    width = args.width if args.width is not None else args.population_size
    height = args.height if args.height is not None else 1
    config = ExperimentConfig(
        dimension=dimension,
        population_size=args.population_size,
        width=width,
        height=height,
        radius=args.radius,
        ticks=args.ticks,
        seed=args.seed,
        mutation_rate=args.mutation_rate,
        max_steps=args.max_steps,
        metric_interval=args.metric_interval,
        functional_sample_size=args.functional_sample_size,
        functional_density_samples=args.functional_density_samples,
        functional_threshold=args.functional_threshold,
        takeover_fraction=args.takeover_fraction,
    )
    config.validate()
    return config, args.output_dir


def content_hash(tape: NDArray[np.uint8]) -> str:
    """Return a stable, collision-resistant content identifier for one tape."""

    return hashlib.blake2b(tape.tobytes(), digest_size=16).hexdigest()


def all_hashes(tapes: NDArray[np.uint8]) -> list[str]:
    """Hash the population in its fixed position order."""

    return [content_hash(tape) for tape in tapes]


def wilson_upper(successes: int, trials: int) -> float:
    """Return the two-sided 95% Wilson upper confidence bound for a proportion."""

    if not 0 <= successes <= trials or trials <= 0:
        raise ValueError("successes must be in 0..trials and trials must be positive")
    z = 1.959963984540054
    estimate = successes / trials
    denominator = 1.0 + z * z / trials
    centre = estimate + z * z / (2.0 * trials)
    radius = z * math.sqrt((estimate * (1.0 - estimate) + z * z / (4.0 * trials)) / trials)
    return min(1.0, (centre + radius) / denominator)


def functional_scores(candidates: NDArray[np.uint8], assay_seed: int) -> NDArray[np.int64]:
    """Run the paper's functional proxy on contiguous 64-byte candidate tapes."""

    if candidates.ndim != 2 or candidates.shape[1] != 64 or candidates.dtype != np.uint8:
        raise ValueError("candidates must be a uint8 matrix with 64-byte rows")
    return score_selfrep_candidates(np.ascontiguousarray(candidates), assay_seed)


def estimate_initial_basin_density(config: ExperimentConfig) -> dict[str, int | float]:
    """Estimate functional density from an independent, uniform random sample."""

    density_rng = np.random.default_rng(np.uint64(config.seed) ^ np.uint64(0xD1CE5EED))
    candidates = density_rng.integers(
        0, 256, size=(config.functional_density_samples, 64), dtype=np.uint8
    )
    scores = functional_scores(candidates, config.seed)
    successes = int(np.count_nonzero(scores >= config.functional_threshold))
    trials = config.functional_density_samples
    return {
        "functional_density_samples": trials,
        "functional_successes": successes,
        "functional_density_estimate": successes / trials,
        "functional_density_wilson95_upper": wilson_upper(successes, trials),
        "functional_threshold": config.functional_threshold,
        "max_functional_score": int(np.max(scores)),
    }


def mutate(tapes: NDArray[np.uint8], rng: Generator, mutation_rate: float) -> int:
    """Apply independent uniform byte replacements to every tape before pairing."""

    if mutation_rate == 0.0:
        return 0
    mask = rng.random(tapes.shape) < mutation_rate
    count = int(np.count_nonzero(mask))
    if count:
        tapes[mask] = rng.integers(0, 256, size=count, dtype=np.uint8)
    return count


def local_neighbors(config: ExperimentConfig) -> list[NDArray[np.int64]]:
    """Precompute open-boundary neighbors within the stated spatial radius."""

    neighbors: list[NDArray[np.int64]] = []
    if config.dimension == 1:
        for index in range(config.population_size):
            low = max(0, index - config.radius)
            high = min(config.population_size, index + config.radius + 1)
            neighbors.append(np.asarray([other for other in range(low, high) if other != index], dtype=np.int64))
        return neighbors
    if config.dimension == 2:
        for index in range(config.population_size):
            y, x = divmod(index, config.width)
            choices: list[int] = []
            for other_y in range(max(0, y - config.radius), min(config.height, y + config.radius + 1)):
                for other_x in range(max(0, x - config.radius), min(config.width, x + config.radius + 1)):
                    other = other_y * config.width + other_x
                    if other != index:
                        choices.append(other)
            neighbors.append(np.asarray(choices, dtype=np.int64))
        return neighbors
    raise ValueError("0D has no local neighbor table")


def select_pairs(
    config: ExperimentConfig, rng: Generator, neighbors: list[NDArray[np.int64]] | None
) -> list[tuple[int, int]]:
    """Select ordered, disjoint pairs using the dimension's predeclared protocol."""

    if config.dimension == 0:
        order = rng.permutation(config.population_size)
        return [(int(order[index]), int(order[index + 1])) for index in range(0, config.population_size - 1, 2)]

    if neighbors is None:
        raise ValueError("spatial pairing requires a neighbor table")
    taken = np.zeros(config.population_size, dtype=bool)
    pairs: list[tuple[int, int]] = []
    for raw_a in rng.permutation(config.population_size):
        a = int(raw_a)
        if taken[a]:
            continue
        choices = neighbors[a]
        if not len(choices):
            continue
        b = int(choices[rng.integers(len(choices))])
        if taken[b]:
            continue
        taken[a] = True
        taken[b] = True
        pairs.append((a, b))
    return pairs


def execute_pairs(
    tapes: NDArray[np.uint8],
    pairs: list[tuple[int, int]],
    substrate: BFFSubstrate,
    budget: ExecutionBudget,
) -> tuple[int, int]:
    """Execute ordered concatenated interactions and return pair/step counts."""

    total_steps = 0
    for a, b in pairs:
        joint = np.concatenate((tapes[a], tapes[b]))
        result = substrate.execute(joint, pool=None, budget=budget, signals=None)
        tapes[a] = joint[:64]
        tapes[b] = joint[64:]
        total_steps += result.steps_executed
    return len(pairs), total_steps


def high_order_entropy(tapes: NDArray[np.uint8]) -> tuple[float, float, float]:
    """Return byte entropy, compressed bits/byte, and their paper-defined difference."""

    content = tapes.tobytes()
    entropy = byte_entropy(content)
    compressed_bpb = 8.0 * len(brotli.compress(content, quality=2, lgwin=24)) / len(content)
    return entropy, compressed_bpb, entropy - compressed_bpb


def write_csv_row(
    path: Path, fieldnames: list[str], row: Mapping[str, object], write_header: bool
) -> None:
    """Append a single deterministic CSV row, creating the header exactly once."""

    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def run(config: ExperimentConfig, output_dir: Path) -> Path:
    """Execute one deterministic experiment and persist all stated measurements."""

    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "protocol.json").write_text(json.dumps(asdict(config), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    initial_density = estimate_initial_basin_density(config)
    initial_path = output_dir / "initial_basin_density.csv"
    write_csv_row(initial_path, list(initial_density), initial_density, write_header=True)

    rng = np.random.default_rng(config.seed)
    tapes = rng.integers(0, 256, size=(config.population_size, 64), dtype=np.uint8)
    substrate = BFFSubstrate(tape_length=64, head_wrap=True, pc_wrap=False)
    budget = ExecutionBudget(max_steps=config.max_steps)
    neighbors = None if config.dimension == 0 else local_neighbors(config)
    discoveries: dict[str, Discovery] = {}
    total_candidate_evaluations = 0
    total_discoveries = 0
    total_pairs = 0
    total_steps = 0
    total_mutations = 0
    takeover_count = math.ceil(config.takeover_fraction * config.population_size)

    metrics_path = output_dir / "metrics.csv"
    discovery_path = output_dir / "discoveries.csv"
    metric_fields = [
        "tick", "mutations", "pairs", "executed_steps", "byte_entropy", "compressed_bpb", "high_order_entropy",
        "functional_candidates_tested", "functional_candidates_positive", "functional_candidate_evaluations_cumulative",
        "discoveries_cumulative", "dynamic_discovery_hazard", "detected_types_alive", "largest_detected_exact_hash_abundance",
    ]
    discovery_fields = ["content_hash", "first_tick", "functional_score", "first_abundance", "extinction_tick", "takeover_tick"]

    for tick in range(config.ticks):
        mutations = mutate(tapes, rng, config.mutation_rate)
        pairs = select_pairs(config, rng, neighbors)
        pair_count, executed_steps = execute_pairs(tapes, pairs, substrate, budget)
        total_pairs += pair_count
        total_steps += executed_steps
        total_mutations += mutations

        if tick % config.metric_interval != 0 and tick + 1 != config.ticks:
            continue

        sample_size = min(config.functional_sample_size, config.population_size)
        sample_indices = np.sort(rng.choice(config.population_size, size=sample_size, replace=False))
        candidates = tapes[sample_indices]
        scores = functional_scores(candidates, config.seed)
        total_candidate_evaluations += sample_size
        hashes = all_hashes(tapes)
        abundance: dict[str, int] = {}
        for item in hashes:
            abundance[item] = abundance.get(item, 0) + 1

        positives = 0
        for index, score in zip(sample_indices, scores, strict=True):
            if int(score) < config.functional_threshold:
                continue
            positives += 1
            item = hashes[int(index)]
            if item not in discoveries:
                discoveries[item] = Discovery(
                    content_hash=item,
                    first_tick=tick,
                    functional_score=int(score),
                    first_abundance=abundance[item],
                )
                total_discoveries += 1

        largest_detected = 0
        alive = 0
        for discovery in discoveries.values():
            count = abundance.get(discovery.content_hash, 0)
            largest_detected = max(largest_detected, count)
            if count:
                alive += 1
            elif discovery.extinction_tick is None:
                discovery.extinction_tick = tick
            if count >= takeover_count and discovery.takeover_tick is None:
                discovery.takeover_tick = tick

        entropy, compressed_bpb, high_entropy = high_order_entropy(tapes)
        metric = {
            "tick": tick,
            "mutations": mutations,
            "pairs": pair_count,
            "executed_steps": executed_steps,
            "byte_entropy": entropy,
            "compressed_bpb": compressed_bpb,
            "high_order_entropy": high_entropy,
            "functional_candidates_tested": sample_size,
            "functional_candidates_positive": positives,
            "functional_candidate_evaluations_cumulative": total_candidate_evaluations,
            "discoveries_cumulative": total_discoveries,
            "dynamic_discovery_hazard": total_discoveries / total_candidate_evaluations,
            "detected_types_alive": alive,
            "largest_detected_exact_hash_abundance": largest_detected,
        }
        write_csv_row(metrics_path, metric_fields, metric, write_header=not metrics_path.exists())

    with discovery_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=discovery_fields)
        writer.writeheader()
        for discovery in sorted(discoveries.values(), key=lambda item: (item.first_tick, item.content_hash)):
            writer.writerow(asdict(discovery))

    summary = {
        "protocol": asdict(config),
        "initial_basin_density": initial_density,
        "aggregate": {
            "mutations": total_mutations,
            "pairs": total_pairs,
            "executed_steps": total_steps,
            "functional_candidate_evaluations": total_candidate_evaluations,
            "discoveries": total_discoveries,
            "dynamic_discovery_hazard": total_discoveries / total_candidate_evaluations,
            "takeovers": sum(item.takeover_tick is not None for item in discoveries.values()),
            "exact_hash_extinctions": sum(item.extinction_tick is not None for item in discoveries.values()),
        },
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_dir


def main() -> None:
    """Run the CLI protocol and print the resulting artifact directory."""

    config, output_dir = parse_args()
    print(run(config, output_dir))


if __name__ == "__main__":
    main()
