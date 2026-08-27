"""Benchmark the coarse-step Rust kernel via the PyO3 extension."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from organism_sim.config import BehaviorModel, Scheduler, SimulationConfig
from organism_sim.rust_kernel import RustKernelSimulation

RESULTS_ROOT = Path(__file__).resolve().parent / "results"


@dataclass
class RunMetrics:
    behavior_model: str
    scheduler: str
    parallel_workers: int
    seasons_enabled: bool
    season_strength: float
    final_season_index: int
    cellular_emergence_enabled: bool
    biodeposits_enabled: bool
    founders: int
    ticks: int
    warmup_ticks: int
    seed: int
    wall_seconds: float
    ticks_per_second: float
    final_population: int
    species_count: int
    digest: int
    energy_error: float
    energy_ok: bool
    elements_ok: bool


def build_config(
    founders: int,
    seed: int,
    behavior_model: BehaviorModel,
    season_strength: float | None,
    cellular_emergence_enabled: bool,
    cellular_neutral: bool,
    biodeposits_enabled: bool,
    coordinated_components: bool,
    scheduler: Scheduler,
    parallel_workers: int,
    founder_region_size: int,
) -> SimulationConfig:
    return SimulationConfig(
        behavior_model=behavior_model,
        scheduler=scheduler,
        parallel_workers=parallel_workers,
        width=founder_region_size,
        height=founder_region_size,
        founder_count=founders,
        founder_archetype_count=min(20, max(8, founders // 40)),
        seed=seed,
        audit_every=0,
        seasons_enabled=season_strength is not None,
        season_strength=season_strength if season_strength is not None else 0.65,
        cellular_emergence_enabled=cellular_emergence_enabled or cellular_neutral,
        emergence_coordinated_components=coordinated_components,
        emergence_module_cost=0.0 if cellular_neutral else 0.002,
        emergence_module_effect=0.0 if cellular_neutral else 0.25,
        emergence_bond_rate=0.0 if cellular_neutral else 0.01,
        emergence_bond_break_rate=0.0 if cellular_neutral else 0.002,
        emergence_exchange_rate=0.0 if cellular_neutral else 0.02,
        emergence_engulfment_rate=0.0 if cellular_neutral else 0.01,
        biodeposits_enabled=biodeposits_enabled,
    )


def run_scale(
    founders: int,
    ticks: int,
    warmup_ticks: int,
    seed: int,
    behavior_model: BehaviorModel,
    season_strength: float | None,
    cellular_emergence_enabled: bool,
    cellular_neutral: bool,
    biodeposits_enabled: bool,
    coordinated_components: bool,
    scheduler: Scheduler,
    parallel_workers: int,
    founder_region_size: int,
) -> RunMetrics:
    simulation = RustKernelSimulation(
        build_config(
            founders,
            seed,
            behavior_model,
            season_strength,
            cellular_emergence_enabled,
            cellular_neutral,
            biodeposits_enabled,
            coordinated_components,
            scheduler,
            parallel_workers,
            founder_region_size,
        )
    )
    if warmup_ticks > 0:
        simulation.step(warmup_ticks)

    started = time.perf_counter()
    simulation.step(ticks)
    wall_seconds = time.perf_counter() - started

    audit = simulation.audit()
    season = simulation.season_state()
    return RunMetrics(
        behavior_model=behavior_model.value,
        scheduler=scheduler.value,
        parallel_workers=parallel_workers,
        seasons_enabled=bool(season["enabled"]),
        season_strength=season_strength if season_strength is not None else 0.0,
        final_season_index=int(season["index"]),
        cellular_emergence_enabled=cellular_emergence_enabled or cellular_neutral,
        biodeposits_enabled=biodeposits_enabled,
        founders=founders,
        ticks=ticks,
        warmup_ticks=warmup_ticks,
        seed=seed,
        wall_seconds=wall_seconds,
        ticks_per_second=ticks / wall_seconds if wall_seconds > 0 else float("inf"),
        final_population=simulation.population,
        species_count=simulation.species_count,
        digest=simulation.digest(),
        energy_error=float(audit["energy_error"]),
        energy_ok=bool(audit["energy_ok"]),
        elements_ok=bool(audit["elements_ok"]),
    )


def write_outputs(label: str, metrics: list[RunMetrics]) -> Path:
    out_dir = RESULTS_ROOT / label
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "metrics.json").write_text(json.dumps([asdict(m) for m in metrics], indent=2))
    lines = [
        f"# Rust kernel benchmark: {label}",
        "",
        "| behavior | scheduler | workers | founders | ticks | warmup | ticks/s | wall s | final pop | species | energy ok | elements ok |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|",
    ]
    for metric in metrics:
        lines.append(
            f"| {metric.behavior_model} | {metric.scheduler} | {metric.parallel_workers} | "
            f"{metric.founders} | {metric.ticks} | {metric.warmup_ticks} | "
            f"{metric.ticks_per_second:.1f} | {metric.wall_seconds:.3f} | "
            f"{metric.final_population} | {metric.species_count} | "
            f"{metric.energy_ok} | {metric.elements_ok} |"
        )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n")
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scales", default="300,600,1200")
    parser.add_argument("--ticks", type=int, default=300)
    parser.add_argument("--warmup", type=int, default=50)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--behavior-model",
        choices=tuple(model.value for model in BehaviorModel),
        default=BehaviorModel.LEGACY_LINEAR_MACRO_V1.value,
    )
    parser.add_argument(
        "--scheduler",
        choices=tuple(scheduler.value for scheduler in Scheduler),
        default=Scheduler.SERIAL_V2.value,
    )
    parser.add_argument("--parallel-workers", type=int, default=0)
    parser.add_argument(
        "--founder-region-size",
        type=int,
        default=128,
        help="square founder-region width/height; use a wider region for synthetic large populations",
    )
    parser.add_argument(
        "--season-strength",
        type=float,
        help="enable random seasons at this strength",
    )
    parser.add_argument("--cellular-emergence", action="store_true")
    parser.add_argument("--cellular-neutral", action="store_true")
    parser.add_argument("--biodeposits", action="store_true")
    parser.add_argument("--uncoordinated-components", action="store_true")
    parser.add_argument("--label", default=None)
    args = parser.parse_args()

    scales = [int(value) for value in args.scales.split(",") if value.strip()]
    behavior_model = BehaviorModel(args.behavior_model)
    scheduler = Scheduler(args.scheduler)
    season_label = (
        f"-season{args.season_strength:g}"
        if args.season_strength is not None
        else "-noseasons"
    )
    emergence_label = (
        "-cellular-neutral"
        if args.cellular_neutral
        else "-cellular" if args.cellular_emergence else "-nocellular"
    )
    label = args.label or (
        f"rust-{behavior_model.value}-{scheduler.value}-w{args.parallel_workers}"
        f"-f{min(scales)}-{max(scales)}"
        f"-t{args.ticks}-s{args.seed}{season_label}{emergence_label}"
        f"{'-biodeposits' if args.biodeposits else '-nobiodeposits'}"
    )

    metrics = [
        run_scale(
            founders,
            args.ticks,
            args.warmup,
            args.seed,
            behavior_model,
            args.season_strength,
            args.cellular_emergence,
            args.cellular_neutral,
            args.biodeposits,
            not args.uncoordinated_components,
            scheduler,
            args.parallel_workers,
            args.founder_region_size,
        )
        for founders in scales
    ]
    out_dir = write_outputs(label, metrics)

    for metric in metrics:
        print(
            f"behavior={metric.behavior_model} scheduler={metric.scheduler} "
            f"workers={metric.parallel_workers} founders={metric.founders} ticks={metric.ticks} "
            f"-> {metric.ticks_per_second:.1f} ticks/s "
            f"(wall={metric.wall_seconds:.3f}s pop={metric.final_population} species={metric.species_count})"
        )
    print(f"results: {out_dir}")


if __name__ == "__main__":
    main()
