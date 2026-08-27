"""Performance loop harness for the organism-sim tick kernel.

Runs the simulation headlessly WITHOUT the SQLite recorder so measurements
isolate the tick kernel itself. Collects:

- wall-clock ticks/sec at multiple founder scales (scaling curve)
- per-phase time attribution (world, upkeep, digest, decisions, ...)
- deterministic cProfile function stats (pstats text dumps)
- statistical pyinstrument call-stack profiles (flamegraph HTML)

Usage:
    uv run python bench/perf.py --scales 300,600,1200 --ticks 400
    uv run python bench/perf.py --scale 1200 --ticks 600 --flamegraph

Results land in bench/results/<label>/.
"""

from __future__ import annotations

import argparse
import cProfile
import json
import pstats
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from organism_sim.config import SimulationConfig
from organism_sim.simulation import Simulation

RESULTS_ROOT = Path(__file__).resolve().parent / "results"

PHASES = (
    "world_diffuse",
    "deposits_produce",
    "effects",
    "decompose",
    "organism_loop",
    "corpses",
    "audit",
    "other",
)


@dataclass
class PhaseTimer:
    """Accumulates per-phase seconds across all ticks of one run."""

    counts: dict[str, float] = field(default_factory=dict)

    def add(self, phase: str, seconds: float) -> None:
        self.counts[phase] = self.counts.get(phase, 0.0) + seconds


@dataclass
class RunMetrics:
    label: str
    founders: int
    ticks: int
    seed: int
    audit_every: int
    wall_seconds: float
    ticks_per_second: float
    mean_population: int
    final_population: int
    peak_population: int
    phases: dict[str, float]
    phase_share: dict[str, float]


def instrument(simulation: Simulation, timer: PhaseTimer) -> None:
    """Wrap the per-tick phases with wall-clock accumulation.

    Only phase *entry* points are wrapped; inner work is untouched, so the
    instrumentation overhead is a few datetime calls per tick.
    """

    import functools

    def timed(phase: str, fn):
        # Unwrap any previous bench wrapper so each run uses its own timer.
        fn = getattr(fn, "_bench_inner", fn)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                timer.add(phase, time.perf_counter() - start)

        wrapper._bench_phase = phase
        wrapper._bench_inner = fn
        return wrapper

    # World is a slotted dataclass: patch at class level. The guard above
    # keeps us from stacking wrappers across runs of the same process.
    from organism_sim.world import World

    World.diffuse_heat = timed("world_diffuse", World.diffuse_heat)
    simulation._produce_deposits = timed("deposits_produce", simulation._produce_deposits)
    simulation._resolve_effects = timed("effects", simulation._resolve_effects)
    simulation._decompose_environment = timed("decompose", simulation._decompose_environment)
    simulation._expire_corpses = timed("corpses", simulation._expire_corpses)
    simulation.audit = timed("audit", simulation.audit)
    # The organism loop is the remainder of step(); time it by wrapping the
    # internals that dominate it instead of the whole loop body.
    simulation._upkeep = timed("upkeep", simulation._upkeep)
    simulation._digest = timed("digest", simulation._digest)
    simulation._decide_and_act = timed("decisions", simulation._decide_and_act)


def run_scale(
    *,
    founders: int,
    ticks: int,
    seed: int,
    audit_every: int,
    warmup_ticks: int,
    label: str,
    profile: str | None,
    flamegraph: bool,
) -> RunMetrics:
    config = SimulationConfig(
        founder_count=founders,
        seed=seed,
        audit_every=audit_every,
        founder_archetype_count=min(20, max(8, founders // 40)),
    )
    t_setup = time.perf_counter()
    simulation = Simulation(config)
    setup_seconds = time.perf_counter() - t_setup

    timer = PhaseTimer()
    instrument(simulation, timer)

    populations: list[int] = []

    profiler = cProfile.Profile() if profile == "cprofile" else None

    t_start = time.perf_counter()
    for _ in range(warmup_ticks):
        simulation.step()
    warmup_seconds = time.perf_counter() - t_start
    timer.counts.clear()

    if profiler is not None:
        profiler.enable()
    t_start = time.perf_counter()
    for _ in range(ticks):
        simulation.step()
        populations.append(simulation.population)
    wall_seconds = time.perf_counter() - t_start
    if profiler is not None:
        profiler.disable()

    timed_phases = sum(timer.counts.values())
    other = max(0.0, wall_seconds - timed_phases)
    phases = dict(sorted(timer.counts.items(), key=lambda kv: -kv[1]))
    phases["other(step remainder)"] = other

    metrics = RunMetrics(
        label=label,
        founders=founders,
        ticks=ticks,
        seed=seed,
        audit_every=audit_every,
        wall_seconds=wall_seconds,
        ticks_per_second=ticks / wall_seconds if wall_seconds > 0 else float("inf"),
        mean_population=sum(populations) // max(1, len(populations)),
        final_population=populations[-1] if populations else simulation.population,
        peak_population=max(populations) if populations else simulation.population,
        phases={k: round(v, 4) for k, v in phases.items() if v > 0.0005},
        phase_share={
            k: round(v / wall_seconds, 4) for k, v in phases.items() if v / wall_seconds > 0.001
        },
    )
    metrics.phases["__setup__"] = round(setup_seconds, 4)
    metrics.phases["__warmup__"] = round(warmup_seconds, 4)
    print(
        f"[{label}] founders={founders} ticks={ticks} -> "
        f"{metrics.ticks_per_second:.1f} ticks/s "
        f"(pop mean={metrics.mean_population} peak={metrics.peak_population}, "
        f"setup={setup_seconds:.2f}s warmup={warmup_seconds:.2f}s)"
    )
    return metrics


def write_outputs(label: str, metrics: list[RunMetrics], profiler: cProfile.Profile | None, flamegraph: bool, extra: dict) -> Path:
    out_dir = RESULTS_ROOT / label
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "metrics.json").write_text(
        json.dumps([asdict(m) for m in metrics], indent=2)
    )

    lines = [
        f"# Benchmark: {label}",
        "",
        "| label | founders | ticks | ticks/s | mean pop | peak pop | audit |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for m in metrics:
        lines.append(
            f"| {m.label} | {m.founders} | {m.ticks} | {m.ticks_per_second:.1f} | "
            f"{m.mean_population} | {m.peak_population} | {m.audit_every} |"
        )
    lines.append("")
    for m in metrics:
        lines.append(f"## Phase breakdown — {m.label} (share of tick wall time)")
        lines.append("")
        lines.append("| phase | seconds | share |")
        lines.append("|---|---:|---:|")
        for phase, share in m.phase_share.items():
            seconds = m.phases.get(phase, 0.0)
            lines.append(f"| {phase} | {seconds:.2f} | {share:.1%} |")
        lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines))

    if profiler is not None:
        stats = pstats.Stats(profiler)
        for sort_key, name in (("cumulative", "pstats_cumulative.txt"), ("tottime", "pstats_self.txt")):
            with (out_dir / name).open("w") as handle:
                stats.stream = handle
                stats.sort_stats(sort_key).print_stats(50)

    (out_dir / "context.json").write_text(json.dumps(extra, indent=2, default=str))
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scales", type=str, default="300,600,1200", help="comma-separated founder counts")
    parser.add_argument("--ticks", type=int, default=400)
    parser.add_argument("--warmup", type=int, default=50)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--audit-every", type=int, default=0, help="0 disables audits (kernel only)")
    parser.add_argument("--label", type=str, default=None)
    parser.add_argument("--profile", choices=["cprofile", "pyinstrument", "none"], default="none")
    parser.add_argument("--flamegraph", action="store_true", help="emit py-spy speedscope via subprocess if available")
    args = parser.parse_args()

    label = args.label or time.strftime("run_%Y%m%dT%H%M%S")
    scales = [int(s) for s in args.scales.split(",") if s.strip()]

    if args.profile == "pyinstrument":
        from pyinstrument import Profiler

        profiler_obj = Profiler()
        profiler_obj.start()
        metrics = [
            run_scale(
                founders=scale,
                ticks=args.ticks,
                seed=args.seed,
                audit_every=args.audit_every,
                warmup_ticks=args.warmup,
                label=f"pyinstrument_{scale}",
                profile=None,
                flamegraph=False,
            )
            for scale in scales
        ]
        profiler_obj.stop()
        out_dir = RESULTS_ROOT / label
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "pyinstrument.html").write_text(profiler_obj.output_html())
        (out_dir / "pyinstrument.txt").write_text(profiler_obj.output_text(unicode=True, color=False))
        write_outputs(label, metrics, None, False, {"profile": "pyinstrument"})
        print(f"pyinstrument flamegraph: {out_dir / 'pyinstrument.html'}")
        return

    cprof_scale = scales[-1]
    metrics: list[RunMetrics] = []
    cprofiler = cProfile.Profile()
    for scale in scales:
        use_cprofile = args.profile == "cprofile" and scale == cprof_scale
        m = run_scale(
            founders=scale,
            ticks=args.ticks,
            seed=args.seed,
            audit_every=args.audit_every,
            warmup_ticks=args.warmup,
            label=f"f{scale}",
            profile="cprofile" if use_cprofile else None,
            flamegraph=False,
        )
        metrics.append(m)
        if use_cprofile:
            # re-run quickly to capture profiler? No: run_scale already enabled it.
            pass
    # The cProfile instance inside run_scale is local; simpler approach: rerun last scale under profiler here if requested.
    if args.profile == "cprofile":
        cprofiler.enable()
        m = run_scale(
            founders=cprof_scale,
            ticks=max(100, args.ticks // 2),
            seed=args.seed,
            audit_every=args.audit_every,
            warmup_ticks=max(10, args.warmup // 2),
            label=f"cprofile_{cprof_scale}",
            profile=None,
            flamegraph=False,
        )
        cprofiler.disable()
        metrics.append(m)

    out_dir = write_outputs(
        label,
        metrics,
        cprofiler if args.profile == "cprofile" else None,
        args.flamegraph,
        {
            "python": sys.version,
            "machine": sys.platform,
            "scales": scales,
            "seed": args.seed,
        },
    )
    print(f"results: {out_dir}")


if __name__ == "__main__":
    main()
