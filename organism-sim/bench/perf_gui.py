"""Compare asynchronous Rust pygame throughput with the Rust headless kernel."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from time import perf_counter, sleep

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from organism_sim.config import SimulationConfig
from organism_sim.rust_kernel import RustKernelSimulation

RESULTS_ROOT = Path(__file__).resolve().parent / "results"


def build_config(
    founders: int,
    seed: int,
    render_fps: int,
    cellular_emergence: bool,
    biodeposits: bool,
) -> SimulationConfig:
    return SimulationConfig(
        founder_count=founders,
        founder_archetype_count=min(20, max(8, founders // 40)),
        seed=seed,
        audit_every=0,
        render_fps=render_fps,
        cellular_emergence_enabled=cellular_emergence,
        biodeposits_enabled=biodeposits,
    )


def run_headless(
    config: SimulationConfig, ticks: int, bounds: tuple[int, int, int, int]
):
    simulation = RustKernelSimulation(config)
    # Match the chunks materialized by the initial camera viewport.
    simulation.gui_snapshot(bounds, include_food=True)
    started = perf_counter()
    simulation.step(ticks)
    elapsed = perf_counter() - started
    return {
        "ticks": ticks,
        "wall_seconds": elapsed,
        "ticks_per_second": ticks / elapsed,
        "final_population": simulation.population,
        "digest": simulation.digest(),
        "audit": simulation.audit(),
    }


def run_gui(config: SimulationConfig, ticks: int):
    import pygame

    from organism_sim.gui_backend import RustGuiWorker
    from organism_sim.native_app import NativeApp

    app = NativeApp(config, record=False)
    app.worker = RustGuiWorker(config, snapshot_hz=10, start_paused=True)
    app.paused = True
    app.worker.start()
    app._request_viewport(force=True)

    deadline = perf_counter() + 10.0
    while app.snapshot is None and perf_counter() < deadline:
        update = app.worker.poll_snapshot(app._snapshot_sequence)
        if update is not None:
            app._snapshot_sequence, app.snapshot = update
        else:
            sleep(0.005)
    if app.snapshot is None:
        app.worker.stop()
        pygame.quit()
        raise TimeoutError("initial GUI snapshot was not published")

    app.draw()
    start_tick = app.worker.status.tick
    app.paused = False
    app.worker.set_paused(False)
    started = perf_counter()
    frames = 1
    snapshots = 1
    try:
        while app.worker.status.tick - start_tick < ticks:
            pygame.event.pump()
            update = app.worker.poll_snapshot(app._snapshot_sequence)
            if update is not None:
                app._snapshot_sequence, app.snapshot = update
                app.draw()
                frames += 1
                snapshots += 1
            app.clock.tick(config.render_fps)
        elapsed = perf_counter() - started
        app.worker.set_paused(True)
        final_tick = app.worker.status.tick
        final_population = int(app.snapshot["population"])
        status_tps = app.worker.status.ticks_per_second
    finally:
        app.worker.stop()
        audit = app.worker.status.final_audit
        pygame.quit()

    executed = final_tick - start_tick
    return {
        "ticks": executed,
        "wall_seconds": elapsed,
        "ticks_per_second": executed / elapsed,
        "worker_reported_ticks_per_second": status_tps,
        "rendered_frames": frames,
        "published_snapshots": snapshots,
        "rendered_frames_per_second": frames / elapsed,
        "final_population_from_snapshot": final_population,
        "audit": audit,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--founders", type=int, default=1200)
    parser.add_argument("--ticks", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--render-fps", type=int, default=30)
    parser.add_argument("--real-display", action="store_true")
    parser.add_argument("--cellular-emergence", action="store_true")
    parser.add_argument("--biodeposits", action="store_true")
    parser.add_argument("--label")
    args = parser.parse_args()
    if args.founders < 1 or args.ticks < 1 or args.render_fps < 1:
        parser.error("founders, ticks, and render-fps must be positive")
    if not args.real_display:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    config = build_config(
        args.founders,
        args.seed,
        args.render_fps,
        args.cellular_emergence,
        args.biodeposits,
    )
    half_tiles = 768 / (2 * config.tile_pixels)
    bounds = (
        int(config.width / 2 - half_tiles) - 1,
        int(config.height / 2 - half_tiles) - 1,
        int(config.width / 2 + half_tiles) + 2,
        int(config.height / 2 + half_tiles) + 2,
    )
    headless = run_headless(config, args.ticks, bounds)
    gui = run_gui(config, args.ticks)
    ratio = gui["ticks_per_second"] / headless["ticks_per_second"]
    result = {
        "schema_version": 1,
        "config": asdict(config),
        "display": "real" if args.real_display else "SDL dummy",
        "headless": headless,
        "gui": gui,
        "gui_to_headless_throughput": ratio,
        "target_met": ratio >= 0.85,
    }

    label = args.label or f"gui-native-f{args.founders}-t{args.ticks}-s{args.seed}"
    out_dir = RESULTS_ROOT / label
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    (out_dir / "summary.md").write_text(
        "\n".join(
            [
                f"# Native GUI benchmark: {label}",
                "",
                f"Display: `{result['display']}`",
                "",
                "| mode | ticks/s | wall seconds | final population |",
                "|---|---:|---:|---:|",
                f"| Rust headless | {headless['ticks_per_second']:.1f} | {headless['wall_seconds']:.3f} | {headless['final_population']} |",
                f"| Rust pygame | {gui['ticks_per_second']:.1f} | {gui['wall_seconds']:.3f} | {gui['final_population_from_snapshot']} |",
                "",
                f"GUI/headless throughput: **{ratio:.1%}** (85% target: **{'PASS' if result['target_met'] else 'FAIL'}**).",
                f"Rendered snapshot frames: `{gui['rendered_frames']}` ({gui['rendered_frames_per_second']:.1f}/s).",
                "",
                "The dummy-display result includes pygame drawing and snapshot conversion but excludes an OS compositor/GPU presentation cost.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        f"headless={headless['ticks_per_second']:.1f} ticks/s "
        f"gui={gui['ticks_per_second']:.1f} ticks/s ratio={ratio:.1%}"
    )
    print(f"results: {out_dir}")


if __name__ == "__main__":
    main()
