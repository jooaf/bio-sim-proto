"""Compare Python and Rust ecology outcomes across independent seeded streams.

The Rust kernel deliberately uses a different RNG, so exact trajectories are
not expected. This harness compares population and event distributions while
requiring conservation in both implementations.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from organism_sim.config import SimulationConfig
from organism_sim.rust_kernel import RustKernelSimulation
from organism_sim.simulation import Simulation

RESULTS_ROOT = Path(__file__).resolve().parent / "results"
METRICS = (
    "population",
    "births",
    "deaths",
    "attacks",
    "magic_casts",
    "alliances",
    "colonies",
    "asexual_reproduction_events",
    "sexual_reproduction_events",
)


@dataclass
class Outcome:
    engine: str
    seed: int
    ticks: int
    wall_seconds: float
    population: int
    births: int
    deaths: int
    attacks: int
    magic_casts: int
    alliances: int
    colonies: int
    asexual_reproduction_events: int
    sexual_reproduction_events: int
    elements_ok: bool
    energy_ok: bool


def config_for(seed: int, founders: int) -> SimulationConfig:
    return SimulationConfig(
        seed=seed,
        founder_count=founders,
        founder_archetype_count=min(20, max(8, founders // 40)),
        audit_every=0,
    )


def run_python(seed: int, founders: int, ticks: int) -> Outcome:
    simulation = Simulation(config_for(seed, founders))
    started = time.perf_counter()
    simulation.step(ticks)
    wall = time.perf_counter() - started
    error = simulation.audit()
    stats = simulation.stats
    return Outcome(
        engine="python",
        seed=seed,
        ticks=ticks,
        wall_seconds=wall,
        population=simulation.population,
        births=stats.births,
        deaths=stats.deaths,
        attacks=stats.attacks,
        magic_casts=stats.magic_casts,
        alliances=stats.alliances,
        colonies=stats.colonies,
        asexual_reproduction_events=stats.asexual_reproduction_events,
        sexual_reproduction_events=stats.sexual_reproduction_events,
        elements_ok=True,
        energy_ok=abs(error) <= max(1e-7, abs(simulation.initial_energy) * 1e-10),
    )


def run_rust(seed: int, founders: int, ticks: int) -> Outcome:
    simulation = RustKernelSimulation(config_for(seed, founders))
    started = time.perf_counter()
    simulation.step(ticks)
    wall = time.perf_counter() - started
    audit = simulation.audit()
    stats = simulation.stats_dict()
    return Outcome(
        engine="rust",
        seed=seed,
        ticks=ticks,
        wall_seconds=wall,
        population=simulation.population,
        births=int(stats["births"]),
        deaths=int(stats["deaths"]),
        attacks=int(stats["attacks"]),
        magic_casts=int(stats["magic_casts"]),
        alliances=int(stats["alliances"]),
        colonies=int(stats["colonies"]),
        asexual_reproduction_events=int(stats["asexual_reproduction_events"]),
        sexual_reproduction_events=int(stats["sexual_reproduction_events"]),
        elements_ok=bool(audit["elements_ok"]),
        energy_ok=bool(audit["energy_ok"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="1,2,3,4,5")
    parser.add_argument("--founders", type=int, default=300)
    parser.add_argument("--ticks", type=int, default=300)
    parser.add_argument("--label", default="kernel_comparison")
    args = parser.parse_args()
    seeds = [int(value) for value in args.seeds.split(",") if value.strip()]

    outcomes = []
    for seed in seeds:
        python = run_python(seed, args.founders, args.ticks)
        rust = run_rust(seed, args.founders, args.ticks)
        outcomes.extend((python, rust))
        print(
            f"seed={seed} population python={python.population} rust={rust.population} "
            f"speedup={python.wall_seconds / rust.wall_seconds:.1f}x"
        )

    summaries: dict[str, dict[str, float]] = {}
    for engine in ("python", "rust"):
        rows = [row for row in outcomes if row.engine == engine]
        summaries[engine] = {
            metric: statistics.fmean(getattr(row, metric) for row in rows) for metric in METRICS
        }
        summaries[engine]["ticks_per_second"] = statistics.fmean(
            row.ticks / row.wall_seconds for row in rows
        )

    relative_deltas = {
        metric: (
            (summaries["rust"][metric] - summaries["python"][metric])
            / max(abs(summaries["python"][metric]), 1.0)
        )
        for metric in METRICS
    }
    conservation_ok = all(row.elements_ok and row.energy_ok for row in outcomes)

    out_dir = RESULTS_ROOT / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "founders": args.founders,
        "ticks": args.ticks,
        "seeds": seeds,
        "outcomes": [asdict(row) for row in outcomes],
        "means": summaries,
        "rust_relative_to_python": relative_deltas,
        "conservation_ok": conservation_ok,
    }
    (out_dir / "comparison.json").write_text(json.dumps(result, indent=2))

    lines = [
        f"# Kernel statistical comparison ({len(seeds)} seeds)",
        "",
        f"Founders: {args.founders}; ticks: {args.ticks}; conservation: **{conservation_ok}**.",
        "Rust has an independent deterministic RNG, so this checks ecological scale, not trajectory parity.",
        "",
        "| metric | Python mean | Rust mean | Rust relative delta |",
        "|---|---:|---:|---:|",
    ]
    for metric in METRICS:
        lines.append(
            f"| {metric} | {summaries['python'][metric]:.1f} | "
            f"{summaries['rust'][metric]:.1f} | {relative_deltas[metric]:+.1%} |"
        )
    lines.extend(
        [
            "",
            (
                f"Mean throughput: Python {summaries['python']['ticks_per_second']:.1f} ticks/s; "
                f"Rust {summaries['rust']['ticks_per_second']:.1f} ticks/s."
            ),
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n")
    if not conservation_ok:
        raise SystemExit("conservation failed in at least one comparison run")


if __name__ == "__main__":
    main()
