"""Bounded Stage 2 benchmark ladder and 500,000-tick projection."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from soup.config import Config, PairingMode
from soup.simulation import Simulation


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    name: str
    width: int
    height: int
    ticks: int
    debug_invariants: bool


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    name: str
    width: int
    height: int
    ticks: int
    attempted_interactions_per_tick: int
    executed_interactions: int
    wall_time_s: float
    ticks_per_s: float
    executed_interactions_per_s: float
    output_bytes: int
    projected_500k_wall_time_s: float
    projected_500k_output_bytes: int
    final_tapes: int
    final_free_cells: int
    invariant_failures: int


def benchmark_config(case: BenchmarkCase) -> Config:
    """Return one aggregate-logging Stage 2 benchmark configuration."""

    capacity = case.width * case.height
    config = Config()
    config.run.stage = 2
    config.run.seed = 20260822
    config.run.n_ticks = case.ticks
    config.run.epoch_length = max(1, case.ticks // 10)
    config.run.debug_invariants = case.debug_invariants
    config.run.invariant_check_interval = max(1, case.ticks // 10)
    config.substrate.tape_length = 64
    config.substrate.max_steps = 8192
    config.world.width = case.width
    config.world.height = case.height
    config.world.interaction_radius = 1
    config.world.interactions_per_tick = capacity // 2
    config.world.pairing_mode = PairingMode.LOCAL_NEIGHBORHOOD.value
    config.world.mutation_rate = 1.0 / 4096.0
    config.world.reseed_rate = 0.00001
    config.symbols.pool_multiplier = 16.0
    config.symbols.initial_tape_fill = 0.8
    config.dissolution.enabled = True
    config.dissolution.inert_ticks = 10_000
    config.dissolution.max_age = 0
    config.dissolution.spontaneous_rate = 0.000001
    config.logging.tick_tables = ["ticks"]
    config.logging.epoch_tables = ["population", "tapes"]
    config.logging.tape_snapshot_interval = 1
    config.logging.full_tape_snapshot_interval = 0
    config.logging.interaction_log_rate = 0.0
    config.logging.flush_interval = max(1, case.ticks // 10)
    config.validate()
    return config


def run_case(case: BenchmarkCase, run_root: Path) -> BenchmarkResult:
    """Execute one case and derive a linear 500k projection."""

    config = benchmark_config(case)
    run_dir = run_root / case.name
    started = time.perf_counter()
    completed = Simulation(config, run_dir=run_dir).run()
    elapsed = time.perf_counter() - started
    ticks = pd.read_parquet(completed / "ticks.parquet")
    executed = int(ticks["n_interactions"].sum())
    output_bytes = sum(path.stat().st_size for path in completed.iterdir() if path.is_file())
    projection_factor = 500_000 / case.ticks
    invariant_log = completed / "invariant_log.jsonl"
    invariant_failures = sum(1 for line in invariant_log.read_text(encoding="utf-8").splitlines() if line)
    final = ticks.iloc[-1]
    return BenchmarkResult(
        name=case.name,
        width=case.width,
        height=case.height,
        ticks=case.ticks,
        attempted_interactions_per_tick=config.world.interactions_per_tick,
        executed_interactions=executed,
        wall_time_s=elapsed,
        ticks_per_s=case.ticks / elapsed,
        executed_interactions_per_s=executed / elapsed,
        output_bytes=output_bytes,
        projected_500k_wall_time_s=elapsed * projection_factor,
        projected_500k_output_bytes=int(output_bytes * projection_factor),
        final_tapes=int(final["n_tapes"]),
        final_free_cells=int(final["n_free_cells"]),
        invariant_failures=invariant_failures,
    )


def write_report(results: list[BenchmarkResult], target: Path) -> None:
    rows = [
        "# Stage 2 500,000-tick benchmark",
        "",
        "All cases use radius 1, 80% initial fill, multiplier 16, mutation 1/4,096, an 8,192-step interaction budget, and aggregate logging.",
        "",
        "| case | lattice | measured ticks | wall time | ticks/s | executed interactions/s | output | projected 500k wall | projected 500k output | invariant failures |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        rows.append(
            f"| {result.name} | {result.width}×{result.height} | {result.ticks:,} | "
            f"{result.wall_time_s:.3f} s | {result.ticks_per_s:.3f} | "
            f"{result.executed_interactions_per_s:,.0f} | {result.output_bytes / 1e6:.2f} MB | "
            f"{result.projected_500k_wall_time_s / 3600:.2f} h | "
            f"{result.projected_500k_output_bytes / 1e9:.2f} GB | {result.invariant_failures} |"
        )
    largest = max(results, key=lambda result: result.width * result.height)
    rows += [
        "",
        "## Decision",
        "",
        f"The largest measured case projects to approximately **{largest.projected_500k_wall_time_s / 3600:.2f} hours** and **{largest.projected_500k_output_bytes / 1e9:.2f} GB** for 500,000 ticks under the same logging cadence.",
        "",
        "This is a linear engineering projection, not a completed 500,000-tick scientific run. Replicator-rich long loops, changing occupancy, filesystem behavior, and spatial-analysis cost can make the full campaign slower.",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/stage2_benchmark.json"))
    parser.add_argument("--report", type=Path, default=Path("reports/stage2_benchmark.md"))
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--include-duration", action="store_true")
    args = parser.parse_args()
    cases = [
        BenchmarkCase("correctness_8x8", 8, 8, 100, True),
        BenchmarkCase("smoke_32x32", 32, 32, 1_000, False),
        BenchmarkCase("scale_64x64", 64, 64, 1_000, False),
    ]
    if args.include_duration:
        cases.append(BenchmarkCase("duration_64x64", 64, 64, 10_000, False))
    temporary: tempfile.TemporaryDirectory[str] | None = None
    if args.run_root is None:
        temporary = tempfile.TemporaryDirectory(prefix="stage2-benchmark-")
        run_root = Path(temporary.name)
    else:
        run_root = args.run_root
        run_root.mkdir(parents=True, exist_ok=True)
    results = [run_case(case, run_root) for case in cases]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps([asdict(result) for result in results], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(results, args.report)
    print(args.output)
    print(args.report)
    if temporary is not None:
        temporary.cleanup()


if __name__ == "__main__":
    main()
