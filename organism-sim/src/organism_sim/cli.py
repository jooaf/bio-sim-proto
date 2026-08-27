from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import BehaviorModel, Scheduler
from .config_io import build_config, load_config_file
from .recording import RunRecorder
from .simulation import Simulation

SLIDER_ARGUMENTS: tuple[tuple[str, str, type, str], ...] = (
    ("--founders", "founder_count", int, "initial organism count"),
    ("--genome-seeds", "founder_archetype_count", int, "initial distinct genome lineages/species"),
    ("--elements", "element_count", int, "procedural element count"),
    ("--molecules", "molecule_count", int, "molecule catalog size"),
    ("--deposits", "initial_deposits", int, "initial environmental deposit count"),
    ("--ticks-per-second", "ticks_per_second", float, "recorded target rate; headless mode remains unthrottled"),
    ("--heat-diffusion", "heat_diffusion", float, "heat diffusion coefficient"),
    ("--primary-production", "primary_production_rate", float, "passive local heat-to-chemical conversion rate"),
    ("--deposit-production", "deposit_production_rate", float, "per-tick fraction of ambient heat recharged into deposit chemical energy"),
    ("--prey-threshold", "prey_compatibility_threshold", float, "minimum diet/body signature similarity for an organism to count as prey"),
    ("--attack-damage", "attack_damage_multiplier", float, "integrity damage multiplier per completed attack"),
    ("--decomposition-rate", "decomposition_rate", float, "chemical decomposition rate"),
    ("--mutation-multiplier", "mutation_multiplier", float, "mutation multiplier for future births"),
    ("--maintenance-multiplier", "maintenance_cost_multiplier", float, "basal maintenance cost multiplier"),
    ("--maturity-multiplier", "maturity_age_multiplier", float, "effective maturity-age multiplier"),
    ("--reproduction-drive", "reproduction_action_bonus", float, "baseline utility bonus for ready reproduction"),
    ("--reproduction-cost", "reproduction_cost_multiplier", float, "reproduction energy-cost multiplier"),
    ("--reproduction-cooldown", "reproduction_cooldown_multiplier", float, "reproduction cooldown multiplier"),
    ("--asexual-floor", "asexual_probability_floor", float, "minimum asexual attempt success probability"),
    ("--sexual-floor", "sexual_probability_floor", float, "minimum sexual attempt success probability when enabled"),
)

EXTRA_ARGUMENTS: tuple[tuple[str, str, type, str], ...] = (
    ("--seed", "seed", int, "world seed"),
    ("--width", "width", int, "world width"),
    ("--height", "height", int, "world height"),
    ("--mana-decay", "mana_decay", float, "mana-to-heat decay rate"),
    ("--reaction-rate", "reaction_rate", float, "reaction execution multiplier"),
    ("--audit-every", "audit_every", int, "conservation audit interval"),
    ("--metrics-every", "recording_metrics_interval", int, "aggregate metric interval"),
    ("--detail-every", "recording_detail_interval", int, "organism/species detail interval"),
    ("--snapshot-every", "recording_snapshot_interval", int, "full spatial snapshot interval"),
    ("--commit-every", "recording_commit_interval", int, "SQLite commit interval"),
    ("--render-fps", "render_fps", int, "GUI render target retained in run configuration"),
    ("--season-duration-min", "season_duration_min", int, "minimum random season duration"),
    ("--season-duration-max", "season_duration_max", int, "maximum random season duration"),
    ("--season-transition", "season_transition_ticks", int, "season profile blend duration"),
    ("--season-strength", "season_strength", float, "environmental season variability in [0, 1]"),
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the organism simulation headlessly")
    parser.add_argument("--config", type=Path, help="JSON or TOML configuration file")
    parser.add_argument("--ticks", type=int, help="ticks to execute; overrides [run].ticks")
    parser.add_argument("--runs-dir", type=Path, help="recording output directory; overrides [run].runs_dir")
    parser.add_argument(
        "--engine",
        choices=("python", "rust"),
        default="python",
        help="tick kernel (Rust uses compact JSONL/NPZ recording; default: python)",
    )
    parser.add_argument(
        "--behavior-model",
        choices=tuple(model.value for model in BehaviorModel),
        help="startup-selected behavior/controller law",
    )
    parser.add_argument(
        "--scheduler",
        choices=tuple(scheduler.value for scheduler in Scheduler),
        help="versioned Rust scheduler (parallel-v3 requires a V2 behavior model)",
    )
    parser.add_argument(
        "--parallel-workers",
        type=int,
        help="parallel-v3 Rayon workers; zero uses the machine-local default",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=500,
        help="Rust-engine progress interval in ticks (0 disables progress output)",
    )
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
        help="override any SimulationConfig field; may be repeated",
    )
    parser.add_argument(
        "--sexual-floor-enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="enable or disable the sexual reproduction probability floor",
    )
    parser.add_argument(
        "--deposit-match-ecology",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="match newly generated deposit composition to founder body demand (phase-1 matched-pool economy)",
    )
    parser.add_argument(
        "--seasons",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="enable deterministic random exogenous environment seasons (Rust engine only)",
    )
    parser.add_argument(
        "--cellular-emergence",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="enable generic stochastic modules, bonds, regulation, and internal guests (Rust engine only)",
    )
    parser.add_argument(
        "--biodeposits",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="enable physical structure from accumulated dead biomass (Rust engine only)",
    )
    parser.add_argument(
        "--print-effective-config",
        action="store_true",
        help="print merged configuration and exit without running",
    )
    for option, destination, value_type, help_text in SLIDER_ARGUMENTS + EXTRA_ARGUMENTS:
        parser.add_argument(option, dest=destination, type=value_type, default=None, help=help_text)
    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()
    simulation_values: dict[str, Any] = {}
    run_values: dict[str, Any] = {}
    try:
        if args.config:
            simulation_values, run_values = load_config_file(args.config)
        unknown_run_fields = sorted(set(run_values) - {"ticks", "runs_dir"})
        if unknown_run_fields:
            raise ValueError(f"unknown run configuration fields: {', '.join(unknown_run_fields)}")
        overrides = {
            destination: getattr(args, destination)
            for _, destination, _, _ in SLIDER_ARGUMENTS + EXTRA_ARGUMENTS
            if getattr(args, destination) is not None
        }
        if args.behavior_model is not None:
            overrides["behavior_model"] = BehaviorModel(args.behavior_model)
        if args.scheduler is not None:
            overrides["scheduler"] = Scheduler(args.scheduler)
        if args.parallel_workers is not None:
            overrides["parallel_workers"] = args.parallel_workers
        if args.sexual_floor_enabled is not None:
            overrides["sexual_probability_floor_enabled"] = args.sexual_floor_enabled
        if args.deposit_match_ecology is not None:
            overrides["deposit_match_ecology"] = args.deposit_match_ecology
        if args.seasons is not None:
            overrides["seasons_enabled"] = args.seasons
        if args.cellular_emergence is not None:
            overrides["cellular_emergence_enabled"] = args.cellular_emergence
        if args.biodeposits is not None:
            overrides["biodeposits_enabled"] = args.biodeposits
        config = build_config(simulation_values, overrides, args.set)
        ticks = args.ticks if args.ticks is not None else int(run_values.get("ticks", 1000))
        runs_dir_value = args.runs_dir if args.runs_dir is not None else run_values.get("runs_dir")
        runs_dir = Path(runs_dir_value) if runs_dir_value else None
        if ticks < 0:
            raise ValueError("ticks must be nonnegative")
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    if args.print_effective_config:
        print(
            json.dumps(
                {
                    "simulation": asdict(config),
                    "run": {
                        "ticks": ticks,
                        "runs_dir": str(runs_dir) if runs_dir else None,
                        "engine": args.engine,
                        "progress_every": args.progress_every,
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    if args.engine == "rust":
        from .rust_run import run_rust_headless

        simulation, run_dir, elapsed = run_rust_headless(
            config,
            ticks,
            runs_root=runs_dir,
            progress_every=args.progress_every,
        )
        stats = simulation.stats_dict()
        audit = simulation.audit()
        print(f"recording={run_dir}")
        print(
            f"tick={simulation.tick} population={simulation.population} "
            f"species={simulation.species_count} births={stats['births']} "
            f"deaths={stats['deaths']} sexual_events={stats['sexual_reproduction_events']} "
            f"energy_error={audit['energy_error']:.3e} "
            f"average_tps={simulation.tick / elapsed if elapsed else float('inf'):.1f}"
        )
        return

    simulation = Simulation(config)
    recorder = RunRecorder(simulation, source="headless", runs_root=runs_dir)
    print(f"recording={recorder.run_dir}")
    try:
        for _ in range(ticks):
            simulation.step()
            recorder.record_tick(simulation)
        simulation.audit()
        print(
            f"tick={simulation.tick} population={simulation.population} "
            f"species={sum(s.population > 0 for s in simulation.species.values())} "
            f"births={simulation.stats.births} deaths={simulation.stats.deaths} "
            f"sexual_parents={len(simulation.sexual_parent_ids)} "
            f"sexual_events={simulation.stats.sexual_reproduction_events} "
            f"energy_error={simulation.last_audit_error:.3e}"
        )
    finally:
        recorder.close(simulation)


if __name__ == "__main__":
    main()
