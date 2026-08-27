# Rust Kernel Port Notes

## Status

The existing Rust port is complete and operational. It owns the full simulation tick behind one coarse PyO3 boundary; Python invokes `KernelSimulation.step(n_ticks)` rather than crossing FFI per organism or per tick.

The release wheel built and tested in this work is:

```text
rust/target/wheels/organism_sim_kernel-0.1.0-cp312-cp312-macosx_11_0_arm64.whl
```

`rust/target/` is intentionally ignored.

## Layout

- `src/lib.rs` — kernel lifecycle, actions, reproduction, species/social state, audits, deterministic digest, and PyO3 API
- `src/config.rs` — Rust configuration defaults, parsing target, and defensive validation
- `src/chemistry.rs` — procedural elements/molecules and conserved inventories
- `src/genetics.rs` — fixed-index genes, genomes, phenotypes, policy vectors, and distances
- `src/entities.rs` — organisms, species, effects, corpses, colonies, and counters
- `src/world.rs` — deterministic infinite chunk generation, deposits, occupancy, and heat diffusion
- `src/rng.rs` — xoshiro256++ dynamics RNG, SplitMix64 seeding, and FNV-1a digest support
- `../src/organism_sim/rust_kernel.py` — thin Python loader
- `../tests/test_rust_kernel.py` — extension, determinism, coarse-step, snapshot, and conservation tests
- `../bench/perf_rust.py` — release-kernel coarse-step benchmark

## Build and install

Build a release wheel from the repository root:

```text
uv run maturin build --release --manifest-path rust/Cargo.toml --out rust/target/wheels
```

Install the wheel into the project environment:

```text
uv pip install --python .venv/bin/python --reinstall rust/target/wheels/*.whl
```

For an editable machine-local release build, `nu rust/install_release.nu` runs `maturin develop` through `uv` with native CPU optimization. `rust/install_release.sh` is retained as a compatibility helper.

## Python API

```python
from organism_sim.config import SimulationConfig
from organism_sim.rust_kernel import RustKernelSimulation

simulation = RustKernelSimulation(SimulationConfig(seed=7))
simulation.step(300)  # one coarse FFI call
snapshot = simulation.snapshot()
audit = simulation.audit()
digest = simulation.digest()
```

The wrapper also exposes `step_one`, `profile_step`, viewport-oriented `gui_snapshot`, runtime-safe `update_config`, `tick`, `population`, `species_count`, `stats_dict`, and `extension_available`.

## Determinism

The Rust kernel is self-deterministic. It intentionally does not reproduce Python's Mersenne Twister sequence, so Python/Rust bitwise trajectory parity is not expected. Chemistry, world, founder, and dynamics streams are deterministically derived from the configured seed.

The current digest covers the dynamics RNG, all living organism state, compact dead genealogy records, living IDs, deposits, every heat cell, generated geology totals, species, effects, corpses, colonies, alliances, counters, and ID allocators. Calling `audit()` does not alter the digest.

The dense-living/compact-dead state format intentionally changed the digest schema from the original port, so old numeric digest constants are not comparable. Same-seed runs remain deterministic, different seeds diverge, and repeated `step_one()` calls match coarse `step(n)` calls within the current schema.

## 100k-scale data structures

After a GUI experiment reached 134,811 living organisms and 612,431 total births/founders, the kernel adopted:

- a dense swap-removed living arena plus sparse permanent-ID index;
- compact dead genealogy records instead of retaining full dead policies;
- `Arc`-separated cold genome/phenotype state;
- a maintained ordered living-ID tree for canonical shuffling;
- direct genome-owner lookup and a bounded pair-distance cache;
- chunk-local dense occupancy arrays;
- indexed heat-source chunks, removing quadratic neighbor searches;
- shared footprint/neighborhood offsets and reusable action buffers;
- native phase/subphase profiling through `profile_step`.

These changes preserve the selected biological mechanisms and conservation, but the compact-dead representation defines a new Rust state/digest schema. Detailed measurements and literature are in `../SCALING_ALGORITHMS.md`.

## Conservation model

Matter uses integer molecule counts and exact per-element composition. Energy uses `f64` across chemical batches, mana, active effects, and heat. On-demand geological generation is tracked separately in `generated_elements` and `generated_energy`; audits compare the dynamic budget after subtracting generated geology.

For seed 7, 1,200 founders, tick 350:

```text
element deltas: [0, 0, 0, 0, 0, 0, 0, 0]
energy error:   -5.238689482212e-10
energy tolerance: 1.670446167592e-05
```

Both strict audit flags were true. Batch validation rejects negative counts/energy and energy above molecule capacity.

## Correctness repairs

The finished port retains the previous kernel rather than replacing it. Repairs made while completing it include:

- resolved the remaining compiler/borrow structure and removed warning-producing dead scaffolding;
- corrected the SplitMix64 increment constant used for stream/chunk seeding;
- corrected the action-policy hunger feature to `1 - energy_fraction`;
- tightened `energy_ok` and strict audit checks to the actual configured tolerance;
- expanded the digest from a partial summary to authoritative deterministic state;
- added defensive direct-extension configuration validation;
- updated PyO3/numpy calls to current non-deprecated APIs;
- exposed the conventional `__version__` module attribute and trait names;
- cached prey body signatures without violating Rust borrowing rules.

## Validation

Commands completed successfully:

```text
cargo fmt --all -- --check
cargo check --all-targets
cargo clippy --all-targets -- -D warnings
cargo test --all-targets                 # 11 passed
uv run --extra dev pytest -q             # 64 passed
uv run --extra dev pytest tests/test_rust_kernel.py -q  # 7 passed
uv run ruff check src/organism_sim/rust_kernel.py bench/perf_rust.py tests/test_rust_kernel.py
maturin build --release ...
```

The Rust-port Python files pass Ruff. Final integration also cleaned the benchmark/application lint findings; `uvx ruff check src tests bench` passes for the full project.

## Benchmark

Machine-local native release, CPython 3.12, Apple arm64. Each measured interval is one `step(500)` call after a 50-tick warm-up.

| founders | measured ticks | wall seconds | ticks/s | final population | audit |
|---:|---:|---:|---:|---:|:---:|
| 300 | 500 | 0.479 | 1,043.4 | 211 | pass |
| 600 | 500 | 0.878 | 569.2 | 676 | pass |
| 1,200 | 500 | 1.693 | 295.4 | 1,177 | pass |

These final numbers use the machine-local `target-cpu=native`, full-LTO build from `rust/install_release.nu`. The 1,200-founder result is 4.9 times the requested 60 ticks/s target. Raw results are in `bench/results/rust_final_native/`.

## Statistical parity review

A line-by-line review used the current `src/organism_sim/simulation.py` as the rule source. No probabilities or ecological constants were tuned.

### Reviewed rules

The following Rust behavior matches Python semantically:

- all ten `feature_values`, including hunger as `1 - energy_fraction` and hunger reused for `energy_cost`;
- eligible-action construction for food, heat, detox, prey contact, threats, mates, magic, maturity, and alliances;
- alphabetical softmax action order, weighted dot product, reproduction bonus, `[-30, 30]` exponent clamp, cumulative draw, and fallback;
- radius-one contact versus sight-radius nearby construction, alive filtering, prey/contact tests, and uniform alliance target choice;
- prey compatibility threshold, mass advantage, distance cost, risk-scaled noise, and maximum-score selection;
- mate readiness, sexual-propensity gate, genomic-distance noise, and minimum-score selection;
- water slowdown, `ceil(4 / speed * slowdown)`, and next-action scheduling;
- reproductive readiness, cooldowns, energy commitment, success formulas, body preview/extraction, placement, child counts, and species assignment;
- attack, magic, birth, death, successful-child, asexual-event, and sexual-event counter increments.

Candidate IDs come from different set implementations, but candidate-order differences do not bias selection: prey/mate/food candidates receive identically distributed independent noise, and alliance/choice selection is uniform. Exact trajectories remain intentionally different because the RNG engines and derived streams differ.

### Deviations fixed

Three actual semantic/primitive deviations were found:

1. Rust's `max_by` selected the last hottest cell on equal heat, while Python's manual scan retains the first. Rust now uses the same first-on-tie scan.
2. Rust's magic-affinity `max_by` likewise selected the last tied channel; it now retains the first like Python `max(range(4), key=...)`.
3. Integer choices used `u64 % n`. The bias was negligible at simulation sizes but real; `below` now uses rejection sampling, making `choice`, `randint`, shuffle, and sampling exactly uniform.

`uniform(a, b)` already used the same affine transform as Python. Rust's Box-Muller Gaussian has measured mean/variance consistent with standard normal draws; unlike CPython it does not cache the paired variate, which changes stream consumption but not the marginal distribution or independence. Partial Fisher-Yates sampling was already uniform.

Focused tests now cover first-on-tie heat selection, alphabetical action order, readiness boundaries, the sexual-success formula, one-event-per-successful-asexual-attempt counting, bounded-draw balance, and uniform/Gaussian moments.

### Five-seed before/after comparison

Configuration: seeds 1–5, 300 founders, 300 ticks. The corrected edge cases were not exercised in a way that changed these aggregate outcomes, so event means are identical before and after; throughput variation is ordinary timing noise.

| metric | Python mean | Rust before | before delta | Rust after | after delta |
|---|---:|---:|---:|---:|---:|
| population | 259.6 | 253.6 | -2.3% | 253.6 | -2.3% |
| births | 84.2 | 58.8 | -30.2% | 58.8 | -30.2% |
| deaths | 124.6 | 105.2 | -15.6% | 105.2 | -15.6% |
| attacks | 1,926.6 | 935.8 | -51.4% | 935.8 | -51.4% |
| magic casts | 532.2 | 528.8 | -0.6% | 528.8 | -0.6% |
| alliances | 36.2 | 38.6 | +6.6% | 38.6 | +6.6% |
| colonies | 0.8 | 0.8 | +0.0% | 0.8 | +0.0% |
| asexual events | 71.0 | 52.6 | -25.9% | 52.6 | -25.9% |
| sexual events | 7.8 | 2.6 | -66.7% | 2.6 | -66.7% |
| ticks/s | 50.5 | 947.6 | — | 1,001.3 | — |

Artifacts:

- before: `bench/results/kernel_comparison_before_parity/`
- after: `bench/results/kernel_comparison/`

All conservation checks passed.

### Evidence that residual five-seed deltas are stochastic

The five runs have very high between-seed variance and overlapping engine ranges. For example, Rust seed 4 produced 1,781 attacks versus Python seed 4's 723, despite the five-seed Rust mean being lower; Rust seed 4 also exceeded Python in births and asexual events. Thus the direction is not stable by seed.

A non-gating 20-seed follow-up (`bench/results/kernel_comparison_20seed_parity_review/`) reversed the small-sample reproduction direction and removed the apparent attack/sexual gaps:

| metric | Python mean | Rust mean | Rust delta |
|---|---:|---:|---:|
| population | 286.1 | 322.8 | +12.8% |
| births | 94.0 | 149.8 | +59.4% |
| deaths | 108.0 | 127.0 | +17.6% |
| attacks | 1,322.8 | 1,328.5 | +0.4% |
| magic casts | 543.2 | 497.8 | -8.4% |
| alliances | 45.1 | 49.6 | +10.0% |
| colonies | 4.8 | 5.2 | +9.4% |
| asexual events | 80.7 | 135.8 | +68.3% |
| sexual events | 7.0 | 7.2 | +2.8% |

Approximate 95% two-sample mean-difference intervals computed from the observed standard deviations include zero for every metric. In particular: attacks are about `5.7 ± 431`, sexual events `0.2 ± 5.3`, births `55.8 ± 77`, and asexual events `55.2 ± 72`. This supports broad statistical parity while also showing that 5 or even 20 seeds are underpowered for high-variance birth outcomes. A larger preregistered run would be required to claim tight equivalence bounds.

## Known boundary

The headless CLI can select the Rust engine and write compact research records. The pygame GUI still uses the Python simulation directly. Existing Python engine files were deliberately left unchanged during this parity review.
