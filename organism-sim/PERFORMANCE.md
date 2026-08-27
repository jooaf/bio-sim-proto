# Organism Simulation Performance and Porting Guide

## Outcome

The simulation now has two engines:

1. **Python reference engine** — behavior-compatible with the original synchronous pygame GUI and SQLite recorder.
2. **Rust native engine** — owns the complete tick kernel behind coarse PyO3 calls, powers both headless research runs and the default asynchronous pygame GUI, and writes compact records.

The target of at least 60 ticks/second at roughly 1,200 organisms was exceeded:

| Engine | 300 founders | 600 founders | 1,200 founders |
|---|---:|---:|---:|
| Python baseline | 35.6 t/s | 24.5 t/s | 5.6 t/s |
| Python optimized | 48.4 t/s | 33.2 t/s | 19.7 t/s |
| Rust native release | 1,043.4 t/s | 569.2 t/s | **295.4 t/s** |

The Rust result at 1,200 founders is 4.9 times the requested target and about 53 times the original measured Python result. Benchmark artifacts are under `bench/results/`.

The asynchronous native GUI retained **99.5–99.8%** of matched headless throughput in paired 1,200-founder runs while rendering snapshots at about 9 FPS under SDL's automated display driver. Rust stepping releases the GIL, uses adaptive batches, and publishes only the newest viewport snapshot. See [`GUI_PERFORMANCE.md`](GUI_PERFORMANCE.md).

An opt-in versioned `parallel-v3` scheduler now implements immutable V2 intent generation, parallel organism-local maintenance/digestion transactions, typed conflict components, and parallel commits for isolated self-only components. Counter-derived streams and canonical transaction application remain worker-count deterministic. Release gates conserved matter/energy. In a wide founder region retaining 9,973 and 29,662 organisms after ten ticks, four workers measured 1.84x and 2.00x over one worker; eight measured 1.78x and 2.26x. The 8-worker 30k throughput improved from resolver V1's 13.1 to 24.4 ticks/s. Sustained 100k ecological validation remains outstanding. `serial-v2` remains the default scientific law; see [`PARALLEL_ENGINE_DESIGN.md`](PARALLEL_ENGINE_DESIGN.md).

A subsequent 100k-scale investigation fixed quadratic heat lookup, per-tick sorting, linear genome lookup, dead-history memory retention, and several allocation/data-layout costs. These raised controlled throughput by roughly 1.2–1.7x, but a 20k replay showed only about 6% better late-window organism-ticks/second after normalizing for divergent population trajectories. Rich perception/decision work is now dominant. See [`SCALING_ALGORITHMS.md`](SCALING_ALGORITHMS.md) for run-data analysis, cited ALife/HPC research, implemented algorithms, and the required CPU/GPU intent-phase next step.

A real 10,000-tick Rust run starting with 1,200 founders completed in 184 seconds. The population grew to 14,166 organisms, and the whole run averaged 54.4 ticks/s across that nearly 12-fold growth. Matter and energy audits passed. At the requested approximately 1,200-organism scale, throughput is 295 ticks/s; the long-run average falls because every living organism still requires upkeep and scheduled behavior.

### Neuroevolution Stage 1 scaffold gate

The inert behavior-schema scaffold preserves the legacy controller as the default and rejects V2 execution at startup. A fixed 150-founder/60-tick release test retains the pre-scaffold digest `14019584453586675779`.

Five machine-local release runs of the existing 1,200-founder benchmark (`50` warmup ticks and `300` measured ticks, seed `7`) produced `338.1–342.4` ticks/s, mean `341.1` ticks/s. Every run ended at population `1,136` with digest `16544324249844359639`. This shows no observed legacy regression relative to the documented 295.4 ticks/s result, although the older result predates other kernel optimizations and is not a paired checkout comparison.

### Neuroevolution Stage 2 linear-intent gate

The V2 linear-intent treatment performs richer egocentric perception, builds up to 33 bounded candidates, and scores each with a genetic 451-locus direct policy. Five matched 1,200-founder release runs (`50` warmup ticks and `300` measured ticks, seed `7`) produced `316.5–324.2` ticks/s, mean `320.1` ticks/s. All runs ended at population `930` with digest `16913091282173780927`.

Relative to the Stage 1 legacy mean, V2 linear intent is approximately 6.2% slower despite materially richer perception and motor-level candidates. This is a treatment cost, not a legacy regression: the unchanged legacy digest gate still passes.

A 1,200-founder V2 viability run recovered from population `742` at tick 100 to `2,440` at tick 1,000, with 4,523 births and 3,283 deaths; conservation passed. Three 300-founder/300-tick seeds remained viable both with declared founder priors (final populations `601–2,097`) and with random direct-policy initialization (final populations `343–654`). These are calibration observations, not fitness-based selection or evidence of intelligence.

### Neuroevolution Stage 3 recurrent gate

The recurrent treatment adds an eight-unit expression-gated residual while preserving identical tick-zero physical state and direct policies for matched linear/recurrent seeds. Recurrent randomness is deterministically forked so developing or mutating the residual does not consume the primary ecological RNG stream.

Five matched 1,200-founder release runs (`50` warmup ticks and `300` measured ticks, seed `7`) measured:

| Treatment | Mean ticks/s | Range | Final population | Digest |
|---|---:|---:|---:|---:|
| linear intent V2 | 326.5 | 325.3–327.4 | 930 | `16913091282173780927` |
| recurrent intent V2 | 311.0 | 309.7–312.5 | 962 | `7929821334303126907` |

The recurrent treatment is 4.8% slower than its matching linear control in this full-kernel benchmark, below the 25% design budget. A 1,000-tick viability calibration ended with population `2,523`; a state-lesioned control ended with `2,567`. Both conserved matter and energy. Maximum developed recurrent-expression mean was approximately `0.0127` in the normal run and `0.0117` in the lesioned run. These values demonstrate mutation and inheritance of expression, not evolved memory utility.

A wide-world 10,000-founder initialization measured process maximum RSS of approximately 104 MB for legacy, 166 MB for linear V2, and 246 MB for recurrent V2. Large optional policy blocks are boxed so legacy and linear organisms do not pay inline storage for inactive controller families. The observed recurrent increment over linear is approximately 8.0 KB per founder including allocator overhead.

### Neuroevolution Stage 4 scientific matrix

The frozen 6-treatment × 12-seed, 4,000-tick matrix attempted 72 runs. Sixty-seven completed with valid audits. Five runs exceeded the existing floating-point energy tolerance after reaching approximately 170,000–345,000 organisms; integer element conservation remained exact. These were retained as preregistered exclusions and not rerun.

The recurrent treatment showed significant within-agent counterfactual state dependence (Holm `p = 0.00146`) but no significant ecological advantage over its state lesion, no beneficial delayed-food return effect, and no replicated genetic-expression advantage. The full preregistered memory criterion failed. Founder viability priors strongly improved linear V2 over random founders (Holm `p = 0.00244`). Detailed results are in [`NEUROEVOLUTION_STAGE4_RESULTS.md`](NEUROEVOLUTION_STAGE4_RESULTS.md).

## Reproduce

Build a machine-local optimized kernel:

```text
nu rust/install_release.nu
```

Run a recorded 10,000-tick research simulation:

```text
uv run organism-sim-headless \
  --engine rust \
  --ticks 10000 \
  --founders 1200 \
  --genome-seeds 20 \
  --progress-every 500
```

The Rust headless runner writes:

```text
runs/<run-id>/
├── manifest.json
├── metrics.jsonl
├── audit.json
├── final_species.json
└── final_state.npz
```

GUI selection:

```text
uv run organism-sim                         # auto: prefer asynchronous Rust GUI
uv run organism-sim --engine rust           # require Rust GUI
uv run organism-sim --engine python         # original synchronous GUI
uv run organism-sim-headless --ticks 1000   # Python + full SQLite recorder
```

## Performance loop

The optimization work used a repeatable measure-profile-change-validate loop rather than optimizing by intuition.

### 1. Fixed benchmark scenarios

`bench/perf.py` runs the Python engine without SQLite so the tick kernel is measured independently. It records:

- wall-clock ticks/second;
- population during the measured interval;
- phase attribution for heat, deposits, decomposition, upkeep, digestion, decisions, corpses, and audits;
- deterministic cProfile reports sorted by self and cumulative time;
- pyinstrument call-stack output and HTML flamegraphs.

`bench/perf_rust.py` measures one coarse `step(n)` PyO3 call and records the final digest and conservation flags.

### 2. Flamegraph and function metrics

The final Python flamegraph is:

```text
bench/results/pyopt_flamegraph/pyinstrument.html
```

The corresponding text report is `pyinstrument.txt`. Deterministic cProfile reports are in:

```text
bench/results/baseline/pstats_cumulative.txt
bench/results/baseline/pstats_self.txt
bench/results/profile_before/
bench/results/pyopt_profile_after/
```

After Python optimization, a profiled 1,200-founder interval attributed time as follows:

| Phase | Share |
|---|---:|
| Decisions | 73.6% |
| Deposit production | 14.2% |
| Decomposition | 4.5% |
| Upkeep | 3.7% |
| Other tick work | 2.4% |
| Digestion | 0.9% |
| Heat diffusion | 0.8% |

Profiler instrumentation itself reduces measured throughput; use the unprofiled benchmark for speed claims and the profiler only for attribution.

### 3. Exact regression gate

`bench/regress_check.py` hashes authoritative Python state after a fixed seed-7, 600-founder, 1,500-tick scenario. It includes:

- population and all event counters;
- exact element totals and floating-point energy bits;
- every organism's alive/species/position/mass/generation state;
- every deposit batch and exact energy bits;
- living IDs and generated chunks.

Every retained Python optimization produces the exact stored fingerprint. The final check completed at 30.6 ticks/s and matched all fields.

### 4. Native validation gate

The Rust gate requires:

- same seed and config produce the same complete state digest;
- coarse `step(80)` equals 80 calls to `step_one()`;
- a different seed diverges;
- integer element totals match exactly;
- energy error remains inside the scale-dependent tolerance;
- deterministic digest covers authoritative state and RNG state;
- Rust unit tests, Python extension tests, Clippy with warnings denied, pytest, and Ruff all pass.

### 5. Statistical rule review

Rust deliberately uses its own deterministic RNG, so cross-engine bitwise parity is neither expected nor useful. `bench/compare_kernels.py` compares distributions across seeds instead.

A line-by-line rule review corrected three deviations:

- hottest-cell ties now keep the first cell, like Python;
- tied magic affinities now keep the first channel;
- bounded integer draws now use rejection sampling instead of biased modulo reduction.

A 20-seed, 300-founder, 300-tick comparison found:

| Metric | Python mean | Rust mean | Rust delta |
|---|---:|---:|---:|
| Population | 286.1 | 322.8 | +12.8% |
| Attacks | 1,322.8 | 1,328.5 | +0.4% |
| Magic casts | 543.2 | 497.8 | -8.4% |
| Alliances | 45.1 | 49.6 | +10.0% |
| Colonies | 4.8 | 5.2 | +9.4% |
| Sexual events | 7.0 | 7.2 | +2.8% |

Birth and asexual-event outcomes have very high seed variance; approximate 95% mean-difference intervals include zero for every measured metric. This supports broad rule parity but is not a claim of tight statistical equivalence. A larger preregistered experiment is needed before treating engine choice as an experimental factor with a known equivalence bound.

## Python changes and why they helped

Detailed evidence is in `PYOPT_NOTES.md`.

### Eliminate expensive no-ops

`_upkeep` called `remove_heat` for every organism even when primary production was disabled. The target amount was zero, but `remove_heat` still generated chunk keys, built lists, and summed heat. The code now skips the whole path, and `remove_heat` immediately returns for non-positive amounts.

**Porting lesson:** guard optional systems at the outermost level. A zero coefficient does not make an expensive function call free.

### Make reads read-only

`heat_at` previously called `ensure_chunk`, so a read could generate terrain and execute dictionary-heavy setup. Callers already ensure organism-visible cells and deposit chunks explicitly. Missing chunks now read as zero heat.

**Porting lesson:** separate `get` from `get_or_create`. Hidden mutation blocks caching, parallel reads, and reasoning about complexity.

### Fast-path the common inventory shape

Most deposit inventories contain one molecule batch. Production now has a one-batch path that avoids temporary tuples, headroom lists, and proportional redistribution. Multi-batch deposits preserve the original formula and order.

**Porting lesson:** profile data shape, not just functions. A common-shape specialization can outperform a general abstraction without duplicating the whole system.

### Avoid allocation in spatial queries

Hottest-cell selection is an ordered loop instead of `max(..., key=lambda ...)`; occupancy lookups no longer allocate empty sets; `can_place` scans cached footprint offsets rather than temporarily mutating an organism and rebuilding footprint state.

**Porting lesson:** millions of tiny Python allocations and callbacks dominate otherwise simple arithmetic.

### Cache derived state with explicit invalidation

Structural mass, energy capacity, body signature, food chemistry, policy vectors, maturity age, footprints, nearby cells, and distances are cached. Matter-transfer paths invalidate body-derived values.

**Porting lesson:** a cache is safe only when the authoritative state and every invalidation path are explicit. The exact fingerprint gate made these changes defensible.

## Rust architecture

The complete implementation is in `rust/`; detailed API notes are in `rust/PORT_NOTES.md`.

### Coarse ownership boundary

```text
Python CLI / future GUI adapter
          |
          |  KernelSimulation.step(n_ticks)
          v
+------------------------------------------+
| Rust owns the complete mutable tick state |
| organisms, genomes, chemistry, world,     |
| occupancy, heat, species, effects, RNG    |
+------------------------------------------+
          |
          | snapshot / stats / audit / digest
          v
Python recording and analysis artifacts
```

No Python callback occurs per organism or per tick. Python crosses the boundary for a block of ticks and only requests metrics or snapshots at configured intervals.

**Why this matters:** moving `_best_food` or `remove_heat` alone to Rust would repeatedly marshal Python dictionaries, dataclasses, sets, and inventories. FFI overhead and conversion would erase much of the native gain. The state—not just the arithmetic—must move with the hot loop.

### Data representation

- Actions, features, and traits use fixed integer indices, not hot-path strings.
- Organisms and genomes live in indexed Rust vectors with stable integer IDs.
- Inventories use compact molecule batches with integer counts and `f64` energy.
- Infinite terrain is divided into deterministic chunks.
- Chunk heat uses contiguous flat numeric storage and reusable diffusion scratch.
- Deposits and occupancy use fast hash maps keyed by integer coordinates.
- Chemistry, world, founders, and runtime dynamics have separate deterministic streams.
- The digest covers authoritative state plus RNG state for replay checks.

### Complexity

Literal logarithmic tick cost in organism count is impossible while every organism pays upkeep and some organisms act. The achievable target is:

```text
O(number of living organisms
  + number of active deposits
  + number of active heat cells
  + local spatial candidates)
```

The spatial occupancy index prevents global all-pairs scans, keeping behavior queries local. Measured Rust time per tick grows approximately with active population rather than quadratically. Further sub-linear wall-time scaling requires safe parallelism, not a different serial asymptotic claim.

### Determinism choice

The Rust kernel uses xoshiro256++ with SplitMix64-derived independent streams rather than emulating CPython's Mersenne Twister. This gives:

- deterministic Rust replay;
- stable complete-state digests;
- faster, portable native draws;
- no false promise of cross-language bitwise identity.

The cost is that Python and Rust runs with the same numeric seed are different experimental replicates. Engine identity must be recorded and should not change inside one experimental block.

## Future full Rust or Odin port

### Keep these boundaries

1. **Simulation kernel owns all hot mutable state.** Do not expose per-organism FFI methods.
2. **Configuration is a plain versioned data contract.** Reject unknown/out-of-range fields at the boundary.
3. **Facts leave in batches.** Use Arrow/Parquet or a stable columnar C ABI for production recording.
4. **Analysis remains separate.** Python/Polars can read the same files regardless of simulator language.
5. **Invariants are part of the API.** Keep exact matter audits, energy tolerance, deterministic digest, and per-engine replay tests.

### Rust direction

- Split the current large lifecycle module into systems only after profiling demonstrates a useful boundary.
- Move compact recording to Rust using Arrow/Parquet to avoid final snapshot copies.
- Add deterministic event batches for births, deaths, species, alliances, and colonies.
- Parallelize only phases with explicit read/write separation; preserve the deterministic serial scheduler as a reference mode.
- Consider generational arenas or stable slot maps if organism deletion/compaction becomes expensive.

### Odin direction

- Use struct-of-arrays where SIMD or cache-line scans dominate; retain stable integer IDs.
- Use explicit allocators for tick scratch, world chunks, and event batches.
- Represent actions/features/traits as enums and fixed arrays.
- Expose snapshots with the Arrow C Data Interface or a small versioned C ABI.
- Implement xoshiro/SplitMix directly to preserve Rust-run stream semantics if cross-port replay matters.
- Keep the Python analysis/visualization process out-of-process at first; Parquet is the language boundary.

## Known boundaries

- The pygame GUI still uses the Python reference engine. It remains functional and benefits from Python optimizations, but it does not yet render Rust snapshots.
- Python runs retain the full SQLite recorder. Rust runs use compact JSONL metrics and final NPZ/JSON state to avoid recording becoming the new bottleneck.
- The compact Rust record is not yet accepted by `organism-sim-report`, which expects the SQLite schema.
- The Rust kernel is statistically reviewed but not bitwise-equivalent to Python.
- The 10,000-tick average was 54.4 ticks/s because the population grew from 1,200 to 14,166; the 1,200-organism target-scale measurement is 295.4 ticks/s.

## Validation commands

```text
# Python
uv run python bench/regress_check.py
uv run --extra dev pytest -q
uvx ruff check src tests bench

# Rust
cd rust
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test --all-targets
cd ..
uv run --extra dev pytest tests/test_rust_kernel.py -q

# Performance and parity
uv run python bench/perf.py --scales 300,600,1200 --ticks 300 --warmup 50
uv run python bench/perf_rust.py --scales 300,600,1200 --ticks 500 --warmup 50
uv run python bench/compare_kernels.py --seeds 1,2,3,4,5 --founders 300 --ticks 300
```
