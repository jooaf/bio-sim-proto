# Native GUI Performance

## Result

The pygame GUI now defaults to the Rust kernel when the extension is installed.
The simulation runs in a dedicated worker independently of rendering and
publishes only the newest viewport snapshot.

On the development Apple arm64 machine with 1,200 requested founders:

| run | Rust headless | Rust pygame | relative throughput |
|---|---:|---:|---:|
| cool machine | 461.5 t/s | 459.1 t/s | 99.5% |
| repeated after validation load | 393.1 t/s | 392.3 t/s | 99.8% |

Each benchmark executed 1,500 ticks and rendered viewport snapshots at about
nine frames/second while pygame continued polling events at 30 FPS. Both
passed the 85% acceptance target. Absolute throughput varies with thermal and
background load; the paired ratio is the relevant GUI-overhead measure.

Raw results:

- `bench/results/gui-native-final-f1200-t1500-s7/`
- `bench/results/gui-native-final2-f1200-t1500-s7/`

The SDL dummy benchmark includes Python snapshot conversion and pygame drawing,
but excludes OS compositor/GPU presentation cost. A real display can be
slightly slower depending on resolution, zoom, heat rendering, and GPU/driver.

## Run

Build the kernel once:

```nu
nu rust/install_release.nu
```

The normal command automatically prefers Rust:

```nu
uv run organism-sim
```

Explicit selection:

```nu
uv run organism-sim --engine rust
uv run organism-sim --engine python
```

The Python mode retains the original synchronous simulation and full genome
inspector. `auto` falls back to Python if the extension is unavailable.

## Native controls

- Native mode starts at **MAX** throughput.
- `T` toggles between MAX and the configured ticks/second target.
- `+` / `-` select a throttled target and leave MAX mode.
- `Space` pauses or resumes at a worker barrier.
- `N` advances one tick while paused.
- `R` replaces the worker with a newly seeded simulation.
- Live ecology sliders apply at the next worker barrier.
- Founder, chemistry, and deposit initialization sliders take effect on reset.
- `H`, `F`, `S`, `V`, camera, minimap, and selection remain available.
- `,` / `.` traverse zoom levels from 1 to 64 pixels per world tile.
- The inspector records parent joins, living offspring, alliances, and physical bonds. Click a cyan `JUMP` row, or use `J`, `P`, and `G`, to follow a related living organism.

The native inspector intentionally copies compact physiological fields. Use
`--engine python` when the complete live genome/policy inspector is required.

## Architecture

```text
Rust worker (sole mutable-state owner)
    adaptive step batch, <= about 40 ms
    PyO3 releases the GIL during Rust stepping
    runtime config changes at batch barriers
    viewport snapshot at <=10 Hz
              |
              | latest snapshot replaces previous snapshot
              v
pygame main thread
    event polling at render_fps
    immutable numpy-backed viewport rendering
    no simulation locks and no per-organism FFI calls
```

### Why it approaches headless speed

The old GUI performed one Python tick in the pygame loop and deliberately
refused multi-tick catch-up batches to remain responsive. It also recorded and
rendered from live Python objects. Its maximum throughput was therefore bound
by Python tick cost and frame scheduling.

The native GUI instead:

1. Keeps all hot mutable simulation state in Rust.
2. Releases the GIL for each adaptive coarse step.
3. Keeps batch wall time near 40 ms to bound pause/control latency.
4. Draws at most the newest snapshot; stale frames are never queued.
5. Copies detailed organisms, deposits, corpses, and heat only for the current
   viewport.
6. Copies only compact organism positions and chunk coordinates for the
   minimap.
7. Records aggregate JSONL rows at snapshot cadence, never per tick.

Rendering can fall behind without slowing simulation or consuming memory with
a frame backlog. Visual output therefore skips ticks at MAX speed.

## Snapshot contents

The viewport snapshot includes:

- visible organism position, footprint area, species, energy fraction, mana,
  integrity, toxin, age fields, colony, action, offspring, and kills;
- compact positions for the whole-population minimap;
- visible deposits reduced to richest molecule and total units;
- visible heat cells above 2% of viewport maximum, only when enabled;
- visible corpses;
- species colors/populations and aggregate statistics;
- generated chunk coordinates.

Panning still materializes procedural chunks, matching the original GUI's
observable world-exploration behavior.

## Recording

Native GUI runs write a lightweight directory under `runs/` containing:

- `manifest.json`
- `metrics.jsonl`
- `season_events.jsonl`
- `audit.json`

Rows are written only when a new visual snapshot arrives. This preserves
headline trajectories and final conservation status without introducing
SQLite detail work into the simulation path. Native GUI records do not contain
full organism/genome snapshots and are not currently accepted by the legacy
SQLite report command.

## Semantics and safety

- The native GUI uses the independently deterministic Rust engine, not the
  Python RNG trajectory.
- Only the worker thread touches the kernel.
- Runtime updates reject structural fields such as founder count, chemistry
  size, and chunk size; those require reset.
- Snapshot reads do not consume RNG.
- Final worker shutdown performs exact matter and energy audits.
- Snapshot publication is latest-only and bounded to one retained frame.

## Benchmark

```nu
uv run python bench/perf_gui.py \
    --founders 1200 \
    --ticks 1500 \
    --seed 7
```

Use `--real-display` to include the active display path. Without it, the
benchmark selects SDL's dummy video driver for reproducible automation.

## Dense zoomed-out rendering

The native renderer now switches to a NumPy/surfarray level-of-detail path when at least 10,000 organisms are visible at a tile size of four pixels or less. It vectorizes world-to-screen transforms and species/energy colors, writes organism markers into one RGBA layer, and performs one pygame blit. The minimap uses the same vectorized pixel publication above 10,000 organisms.

An SDL-dummy benchmark with a synthetic 100,000-organism visible snapshot at two pixels/tile improved from **529.4 ms/frame (1.9 FPS)** to **24.6 ms/frame (40.7 FPS)**, about **21.5x**. The ordinary 1,200-founder path remained above 118 FPS in the static draw benchmark. Reproduce with:

```nu
uv run python bench/perf_gui_render.py \
    --founders 1200 \
    --tile-pixels 2 \
    --frames 10 \
    --synthetic-visible 100000
```

Dense mode intentionally renders one marker per organism position rather than every multi-cell footprint and mana glyph. Full footprint/glyph rendering remains active below the threshold or while zoomed in.

## Limitations

- MAX simulation speed can advance hundreds of ticks between visual frames.
- Heat rendering can create many pygame draw calls and increase main-thread
  cost, although the worker continues independently.
- The native inspector is compact rather than a complete genome/policy view.
- GUI snapshots and aggregate recording are not full replay checkpoints.
- pygame still uses CPU drawing; a batched texture/instancing renderer would be
  needed for consistently high visual FPS at very large visible populations.
