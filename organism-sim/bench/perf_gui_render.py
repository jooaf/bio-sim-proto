"""Measure native pygame draw cost against one immutable Rust snapshot."""

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

RESULTS_ROOT = Path(__file__).resolve().parent / "results"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--founders", type=int, default=1200)
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--tile-pixels", type=int, default=8)
    parser.add_argument("--heat", action="store_true")
    parser.add_argument(
        "--synthetic-visible",
        type=int,
        help="repeat organism columns to this visible count for renderer scaling",
    )
    parser.add_argument("--real-display", action="store_true")
    parser.add_argument("--label")
    args = parser.parse_args()
    if args.founders < 1 or args.frames < 1 or not 2 <= args.tile_pixels <= 16:
        parser.error("founders/frames must be positive and tile-pixels must be 2..16")
    if not args.real_display:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    import pygame

    from organism_sim.gui_backend import RustGuiWorker
    from organism_sim.native_app import NativeApp

    config = SimulationConfig(
        founder_count=args.founders,
        founder_archetype_count=min(20, max(8, args.founders // 40)),
        seed=args.seed,
        tile_pixels=args.tile_pixels,
        audit_every=0,
    )
    app = NativeApp(config, record=False)
    app.show_heat = args.heat
    app.worker = RustGuiWorker(config, snapshot_hz=10, start_paused=True)
    app.paused = True
    app.worker.start()
    app._request_viewport(force=True)

    deadline = perf_counter() + 30.0
    try:
        while app.snapshot is None and perf_counter() < deadline:
            update = app.worker.poll_snapshot(app._snapshot_sequence)
            if update is not None:
                app._snapshot_sequence, app.snapshot = update
            else:
                sleep(0.005)
        if app.snapshot is None:
            raise TimeoutError("initial GUI snapshot was not published")

        if args.synthetic_visible is not None:
            if args.synthetic_visible < 1:
                parser.error("synthetic-visible must be positive")
            import numpy as np

            organisms = app.snapshot["organisms"]
            source_count = len(organisms["id"])
            for name, values in organisms.items():
                if name == "neural_state":
                    organisms[name] = np.resize(
                        values.reshape(source_count, -1),
                        (args.synthetic_visible, values.size // source_count),
                    ).reshape(-1)
                else:
                    organisms[name] = np.resize(values, args.synthetic_visible)
            organisms["id"] = np.arange(1, args.synthetic_visible + 1, dtype=np.uint32)
            x0, y0, x1, y1 = app._visible_tiles()
            width = x1 - x0
            height = y1 - y0
            sequence = np.arange(args.synthetic_visible, dtype=np.int64)
            organisms["x"] = x0 + sequence % width
            organisms["y"] = y0 + sequence // width % height
            overview = app.snapshot["overview"]
            overview["id"] = organisms["id"].copy()
            overview["species_id"] = organisms["species_id"].copy()
            overview["x"] = organisms["x"].copy()
            overview["y"] = organisms["y"].copy()
            app.snapshot["population"] = args.synthetic_visible

        for _ in range(5):
            app.draw()
        started = perf_counter()
        for _ in range(args.frames):
            app.draw()
        elapsed = perf_counter() - started
        result = {
            "schema_version": 1,
            "config": asdict(config),
            "display": "real" if args.real_display else "SDL dummy",
            "frames": args.frames,
            "wall_seconds": elapsed,
            "milliseconds_per_frame": elapsed * 1000.0 / args.frames,
            "frames_per_second": args.frames / elapsed,
            "snapshot_population": int(app.snapshot["population"]),
            "visible_organisms": len(app.snapshot["organisms"]["id"]),
            "visible_deposits": len(app.snapshot["deposits"]["x"]),
            "visible_heat_cells": len(app.snapshot["heat"]["x"]),
        }
    finally:
        app.worker.stop()
        pygame.quit()

    label = args.label or (
        f"gui-render-f{args.founders}-tile{args.tile_pixels}"
        f"-heat{int(args.heat)}-s{args.seed}"
    )
    out_dir = RESULTS_ROOT / label
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(
        f"population={result['snapshot_population']} "
        f"visible={result['visible_organisms']} "
        f"draw={result['milliseconds_per_frame']:.3f} ms/frame "
        f"({result['frames_per_second']:.1f} FPS)"
    )
    print(f"results: {out_dir}")


if __name__ == "__main__":
    main()
