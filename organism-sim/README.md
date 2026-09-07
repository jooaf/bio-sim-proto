# Emergent Organism Simulation Prototype

A playable Pygame prototype based on [`SPEC.md`](SPEC.md). Procedurally generated organisms inhabit a toroidal chemical world with discrete conserved matter, continuous conserved energy, heat-derived mana, inherited behavior, toxicity, magic, reproduction, species, and lightweight symbiosis.

## Run

From this folder:

```text
uv run organism-sim
```

When the native extension is installed, the GUI automatically uses an asynchronous Rust worker and starts at unthrottled **MAX** simulation speed. Pygame renders only the newest snapshot, so simulation throughput is independent of visual frame rate. Press `T` to toggle MAX/target speed.

```text
uv run organism-sim --engine rust    # require the native GUI
uv run organism-sim --engine python  # original engine and full genome inspector
```

In paired 1,200-founder benchmarks, the native GUI retained 99.5–99.8% of headless simulation throughput under SDL's automated display driver. It writes lightweight JSONL metrics and a final audit rather than per-tick SQLite detail. See [`GUI_PERFORMANCE.md`](GUI_PERFORMANCE.md) for architecture, controls, benchmark methodology, and limitations.

Headless smoke run:

```text
uv run organism-sim-headless --ticks 1000 --seed 7
uv run organism-sim-headless --ticks 1000 --founders 300 --genome-seeds 8
```

`founders` controls the total initial organism population. `genome-seeds` controls how many distinct founding genome lineages/species that population is seeded from.

### Headless configuration

Every GUI slider has a matching headless flag:

```text
uv run organism-sim-headless \
  --ticks 2000 \
  --founders 500 \
  --genome-seeds 12 \
  --elements 10 \
  --molecules 64 \
  --deposits 4000 \
  --heat-diffusion 0.10 \
  --primary-production 0.0 \
  --decomposition-rate 0.001 \
  --mutation-multiplier 1.5 \
  --maintenance-multiplier 0.75 \
  --maturity-multiplier 0.65 \
  --reproduction-drive 1.25 \
  --reproduction-cost 0.50 \
  --reproduction-cooldown 0.75 \
  --asexual-floor 0.20 \
  --sexual-floor-enabled \
  --sexual-floor 0.12
```

Load TOML or JSON:

```text
uv run organism-sim-headless --config configs/headless.example.toml
uv run organism-sim-headless --config configs/headless.example.json
```

Configuration files accept `[simulation]` and `[run]` sections. CLI flags override file values. `--set FIELD=VALUE` can override any `SimulationConfig` field, including fields without dedicated flags:

```text
uv run organism-sim-headless \
  --config configs/headless.example.toml \
  --set colony_bonus_cap=0.25 \
  --set max_sight=8
```

Inspect the merged configuration without launching a run:

```text
uv run organism-sim-headless \
  --config configs/headless.example.toml \
  --founders 200 \
  --print-effective-config
```

Disable the sexual floor for a control run with `--no-sexual-floor-enabled`; enable it explicitly with `--sexual-floor-enabled`. The GUI exposes the same setting as the **Sexual floor on** 0/1 slider.

Run `uv run organism-sim-headless --help` for all flags. Headless execution is unthrottled; `ticks_per_second` is retained in configuration for comparability with GUI runs.

### Native Rust research engine

Build and install the machine-local optimized PyO3 kernel:

```text
nu rust/install_release.nu
```

Run long headless experiments with the complete tick state owned by Rust:

```text
uv run organism-sim-headless \
  --engine rust \
  --ticks 10000 \
  --founders 1200 \
  --genome-seeds 20 \
  --progress-every 500
```

Record sparse per-organism molecule batches without changing simulation dynamics:

```text
uv run organism-sim-headless \
  --engine rust \
  --ticks 10000 \
  --record-composition \
  --composition-every 100
```

This writes `organism_composition.jsonl`, with one row per non-empty `body`,
`gut`, or `waste` batch for living organisms at tick zero, each requested
sampling tick, and the final tick. It also writes `molecule_catalog.json`,
which maps run-local molecule IDs to elemental composition. Recording is
streamed and disabled by default; `--composition-every` must be positive and
is also accepted as `run.record_composition` and `run.composition_every` in a
config file. Each JSONL row contains `tick`, `organism_id`, `compartment`,
`molecule_id`, `count`, and `chemical_energy`; join `molecule_id` to the
catalog's `composition` vector to obtain elemental totals.

Run the opt-in versioned parallel scheduler with a V2 intent controller:

```text
uv run organism-sim-headless \
  --engine rust \
  --behavior-model recurrent_intent_v2 \
  --scheduler parallel-v3 \
  --parallel-workers 0 \
  --ticks 10000
```

The same flags select it for the asynchronous Rust GUI:

```text
uv run organism-sim \
  --engine rust \
  --behavior-model recurrent_intent_v2 \
  --scheduler parallel-v3 \
  --parallel-workers 0
```

`parallel_workers=0` uses Rayon's machine-local default. `parallel-v3` is deterministic across worker counts, but it is a distinct simulation law from the default `serial-v2`; do not mix scheduler versions inside an experimental block. The initial implementation supports linear/recurrent V2 controllers and rejects legacy macro behavior or coordinated cellular components. See [`PARALLEL_ENGINE_DESIGN.md`](PARALLEL_ENGINE_DESIGN.md).

Enable deterministic random environment seasons in the Rust engine:

```text
uv run organism-sim-headless \
  --engine rust \
  --ticks 10000 \
  --seasons \
  --season-duration-min 500 \
  --season-duration-max 1500 \
  --season-transition 100 \
  --season-strength 0.65
```

Seasons alter only exogenous resource-energy cycling: total deposit recharge, decomposition, and molecule-specific recharge availability. They never inspect or modify species fitness, genomes, mutation, or controller decisions. Adaptation can therefore arise only through existing inherited chemistry/behavior and ecological selection. See [`SEASONS.md`](SEASONS.md).

Enable generic stochastic cellular affordances without assigning any higher-level identity:

```text
uv run organism-sim-headless \
  --engine rust \
  --ticks 10000 \
  --cellular-emergence \
  --seasons
```

This mode provides chance-mutated generic modules, regulation, physical adhesion, signaling, conservative exchange, coordinated bond-derived components, complete component propagules, and bounded internal guests. Bonded connected components translate and act as one unit without storing a multicellularity flag or assigning a group-fitness bonus. In the native GUI, set **Cell affordances** to `1` and press `R`; the sidebar then reports `CELLULAR ON`, current/peak joined-group size, and the run's observed cellular state. Active bonds are drawn as bright cyan links with gold group markers; press `B` to toggle those highlights. If coordinated groups are enabled, the GUI automatically uses the supported serial scheduler. See [`CELLULAR_EMERGENCE.md`](CELLULAR_EMERGENCE.md) for mechanics, telemetry, controls, and limitations.

For a deliberately high-encounter reachability smoke test (not an evolved-biology control), use:

```text
uv run organism-sim-headless \
  --engine rust \
  --ticks 1200 \
  --founders 300 \
  --cellular-emergence \
  --set emergence_bond_rate=0.10 \
  --set emergence_bond_break_rate=0.0005 \
  --set emergence_engulfment_rate=1.0 \
  --set emergence_exchange_rate=0.10 \
  --set emergence_module_cost=0.001
```

Enable physical structure from accumulated dead biomass:

```nu
uv run organism-sim-headless --engine rust --ticks 10000 --biodeposits
```

Death matter remains in the ordinary edible molecule inventory while a decaying packing-density field raises movement work, attenuates attacks, and can conceal organisms. Nearby living mass also blocks placement and contributes physical cover. See [`BIODEPOSITS.md`](BIODEPOSITS.md).

### Reusable GUI settings

The GUI automatically restores and updates `runs/gui_settings.json`. It contains the complete simulation configuration, including the seed and pending reset-only slider values. Reuse it in another GUI or headless run:

```nu
uv run organism-sim --engine rust --config runs/gui_settings.json
uv run organism-sim-headless --engine rust --config runs/gui_settings.json --ticks 10000
```

Use `--fresh` to ignore the previous GUI settings, `--settings-out <path.json>` to choose another autosave file, or `--no-save-settings` to disable autosaving. Headless CLI flags and `--set FIELD=VALUE` continue to override loaded values.

Rust headless runs write compact `metrics.jsonl`, `season_events.jsonl`, `audit.json`, `final_species.json`, and `final_state.npz` artifacts. Native GUI runs also add `config_events.jsonl`, which records each live kernel configuration update at the tick where it was applied. Metrics retain aligned `species_ids` and `species_populations`, while each season event records the complete environmental profile, allowing species viability around transitions to be analyzed without reconstructing RNG state. The compact format avoids making SQLite detail recording the new bottleneck. The Python engine rejects season-enabled configurations rather than silently running a non-seasonal control.

At 1,200 founders the native kernel measures approximately 295 ticks/second on the development Apple arm64 machine. A 10,000-tick run that grew from 1,200 to 14,166 organisms completed in 184 seconds. See [`PERFORMANCE.md`](PERFORMANCE.md) for flamegraphs, metrics, validation, architecture, limitations, and Rust/Odin porting lessons.

Measure event/cohort compression opportunity without changing exact dynamics:

```text
uv run python bench/compressibility.py \
  --founders 1200 --ticks 10000 --interval 500 --burn-in 1000 --seed 7
```

The initial campaign found no lineage-safe compression and only moderate compression under an exploratory guild-level cohort. See [`COMPRESSIBILITY.md`](COMPRESSIBILITY.md) for methods, multi-seed results, and implications for the sublinear design.

A later GUI run grew to 134,811 organisms and fell to 0.49 ticks/s. [`SCALING_ALGORITHMS.md`](SCALING_ALGORITHMS.md) analyzes that trajectory with structured data, reviews cited ALife/HPC algorithms, documents the implemented exact/data-oriented fixes, and explains why the remaining decision workload requires a versioned parallel/GPU or super-individual engine.

### Analysis-informed balancing controls

The initial recorded sweep showed low replacement fertility, approximately 3% sexual births, attrition-dominated mortality, and no colonies. The prototype therefore now provides:

- An optional sexual-success floor, defaulting to 12%
- An asexual-success floor of 20%
- Effective maturity at 65% of the genetically sampled maturity age
- A 1.25 reproduction utility bonus for mature organisms with reserves
- A reproduction energy-cost multiplier of 0.50 and cooldown multiplier of 0.75
- Independent sexual propensity: high asexual propensity no longer prevents mate selection
- A maintenance-cost multiplier defaulting to 0.75, which improved retention and replacement across paired seeds
- Less restrictive colony defaults: sexual propensity at most 0.25 and asexual propensity at least 0.35

New recordings include exact reproduction-attempt, probability-failure, and placement-failure counters. Resource blocks are split into mate-readiness, energy, and transferable-body-matter causes while retaining the aggregate counter for compatibility, so analysis can identify the actual reproductive bottleneck.

Chemistry, world generation, founder generation, and runtime dynamics use independent deterministic random streams derived from the run seed. Changing deposit count therefore no longer changes the realized founder genomes, phenotypes, inventories, or positions, making paired ecological comparisons interpretable.

The 10,000-tick follow-up still produced eight extinctions in ten seeds, so these defaults improve the tested operating point but do not establish long-term persistence. Deposit count and founder-archetype defaults remain unchanged because their retention effects were inconsistent.

### Experimental dynamic-equilibrium profile

A closed simulation eventually exhausts chemical free energy into heat, making extinction its only true long-run equilibrium. The optional **Primary production** control closes that energy loop by converting local environmental heat into available chemical energy in an organism's existing body molecules. The transfer is one-to-one, remains bounded by local heat and chemical storage capacity, and preserves total energy. Its default is `0.0`, so the established model is unchanged unless explicitly enabled.

The best exploratory 10,000-tick profile was:

```text
uv run organism-sim-headless \
  --ticks 10000 \
  --seed 80 \
  --deposits 4900 \
  --maintenance-multiplier 0.40 \
  --reproduction-cost 0.20 \
  --asexual-floor 0.50 \
  --primary-production 0.0125
```

Across ten seeds this profile had no extinctions, four strict equilibrium passes, a median late population of 618, a median trend of -4.4% per 1,000 ticks, and median late births/death of 0.882. Seed 80 was especially stationary: mean late population 4,029, trend -0.3% per 1,000 ticks, births/death 0.995, and population CV 0.004. Outcomes remain seed-sensitive, so this is an experimental profile rather than a new default. The GUI exposes the same value through the live **Primary production** slider.

Full methods and results are in [`experiment_results/equilibrium_search/REPORT.md`](experiment_results/equilibrium_search/REPORT.md).

### Renewable food web and predation defaults

Two further analysis-driven changes restore genuine natural selection:

- **Deposit production** (`--deposit-production`, default `0.10`): each tick, deposit cells convert a fraction of their local ambient heat into chemical energy stored in the deposits themselves, bounded by batch capacity. Unlike the organism-level **Primary production** control above, this recharges the shared food web, so organisms compete over a renewable, rate-limited resource instead of a one-shot initial budget. The transfer is one-to-one and conserves total energy exactly; matter is untouched. With it disabled, every run is a depleting battery: deposits drain, mortality becomes ~95% attrition, generations stall near zero, and reproduction never reaches replacement.
- **Attack damage multiplier** (`--attack-damage`, default `2.0`): integrity damage per completed attack. At the previous implicit 1.0, roughly 5,000 attacks produced ~25 kills (0.5% completion), so hunting could never pay for itself and the hunter guild was inviable. At 2.0, predation accounts for roughly 5–12% of deaths, locomotion traits stop degrading population-wide, and both tested seeds settled into births-near-deaths equilibria. At 3.0 a stronger predator-prey arms race emerges (generations 40+ by tick 8,000) but populations can boom into the thousands through colonization of new geological chunks.
- **Prey compatibility threshold** (`--prey-threshold`, default `0.35`, previously hardcoded `0.45`): minimum diet/body signature similarity for an organism to count as prey.

With the new defaults, 8,000-tick probe runs on seeds 7 and 41 stabilized near 540 and 200 organisms respectively, with generational turnover reaching 10+, sustained directional selection on digestion (0.66 → 0.88 mean), and reproduction resource blocks falling from ~78% to ~35% of attempts. Conservation audits remain within float rounding (|error| < 2e-8). See `experiments/selection_probe.py` to reproduce:

```text
uv run python experiments/selection_probe.py --ticks 8000 --interval 2000 --seed 7
```

The sexual floor affects only attempts that already satisfy maturity, contact, energy, matter, and action-selection requirements. It does not guarantee encounters or births. All values are recorded with each run.

Tests:

```text
uv run --extra dev pytest
```

## Automatic run data

Every Python GUI and Python headless launch automatically creates:

```text
runs/<timestamp>-seed<seed>-<run-id>/
├── manifest.json
└── run.sqlite
```

Rust headless runs use the compact JSONL/NPZ layout described above. The Python SQLite database records:

- Initial configuration, elements, molecules, and conservation baselines
- Every genome and realized phenotype
- Global metrics, conservation totals, element totals, and molecule totals every 5 ticks by default
- Birth, death, speciation, alliance, colony, and sexual-parent events with their exact source ticks
- Every living organism's state and complete compartment inventories every 20 ticks by default
- Final detailed organism/species/world state when a run closes
- Species, corpses, magic effects, and colonies every 20 ticks by default
- Alliances stored once at creation instead of duplicated in every detail snapshot
- Compressed heat grids and sparse environmental molecule fields every 50 ticks by default
- Tick-stamped live configuration changes

The headless command prints its run directory. The GUI displays the short run ID in the sidebar. Every GUI reset counts as a separate run: the prior run is finalized, and a new tick-zero dataset is created with `source = "gui_reset"` and `previous_run_id` linking it to the run that was reset. Set `ORGANISM_SIM_RUNS_DIR` to put datasets elsewhere.

Summarize the latest run, or pass a run directory, native `manifest.json`, or Python `run.sqlite` path:

```text
uv run organism-sim-report
uv run organism-sim-report runs/<run-id>
uv run organism-sim-report runs/<run-id>/manifest.json
uv run organism-sim-report runs/<run-id>/run.sqlite
```

For native records, the report highlights late growth/turnover, first sampled extinction, species dominance, reproduction bottlenecks, frontier-normalized density, world expansion, throughput retention, conservation, and live-configuration provenance. New manifests include hashes of the canonical startup configuration and the actual loaded Rust kernel binary, so runs from different builds cannot be mistaken for replicates. See [`analyses/RECENT_NATIVE_GUI_ANALYSIS.md`](analyses/RECENT_NATIVE_GUI_ANALYSIS.md), [`analyses/LATEST_SEASONAL_BIODEPOSIT_ANALYSIS.md`](analyses/LATEST_SEASONAL_BIODEPOSIT_ANALYSIS.md), and [`analyses/UNSEEN_RUN_COHORT_ANALYSIS.md`](analyses/UNSEEN_RUN_COHORT_ANALYSIS.md). High-scale Rust audits use total accounted energy (initial plus procedurally generated) when bounding floating-point drift, while integer matter remains exact.

Example direct query:

```text
sqlite3 runs/<run-id>/run.sqlite \
  "SELECT tick, population, living_species, sexual_events, energy_error FROM tick_metrics ORDER BY tick;"
```

Recording retains every data category while sampling state for performance. Configure `recording_metrics_interval`, `recording_detail_interval`, `recording_snapshot_interval`, and `recording_commit_interval`, or use `--metrics-every`, `--detail-every`, `--snapshot-every`, and `--commit-every`. Set all four to `1` for full per-tick fidelity; this is substantially slower and more storage-intensive.

## Performance

The default interactive profile now uses:

- Per-organism caches for footprints, neighborhoods, body-derived values, food chemistry, policy vectors, maturity, and repeated distances
- Incremental occupancy maintenance between births and at tick boundaries
- Living-organism indexes that avoid scanning historical tombstones
- Delta/event recording for births, deaths, species, colonies, and alliances
- One-pass energy aggregation with invariant matter counts
- Automatic dense-scene rendering: crowded worlds are composed as one logical pixel map and scaled in a single blit
- Bounded tick scheduling: an overloaded engine never batches accumulated tick debt, so event handling and drawing resume after every tick
- Aggregate metrics every 5 ticks and exact-tick lifecycle events
- Detailed organism/species state every 20 ticks
- Spatial heat/deposit snapshots and SQLite commits every 50 ticks

On the 3,418-tick seed-7 equilibrium profile that originally averaged approximately **6.3 recorded ticks/second**, the optimized run reproduced the exact final population, birth, death, and alliance counts while greatly reducing runtime and storage. The database shrank from approximately **363 MB** to **125 MB**. A synthetic 1,200-organism, 4,200-deposit render benchmark improved from **19.0 ms/frame** to **8.2 ms/frame**. The sidebar reports achieved versus requested ticks/second; very large populations can still make the simulation engine, rather than rendering, the limiting factor.

For maximum fidelity, use `--metrics-every 1 --detail-every 1 --snapshot-every 1 --commit-every 1`. For faster interactive runs and large sweeps, increase these intervals. Lifecycle events retain their original tick even when metrics are sampled.

## Controls

- `Space`: pause/resume
- `T`: toggle native MAX speed / configured target
- `N`: single simulation tick
- `R`: regenerate using pending reset-only slider values
- `[` / `]`: decrease/increase seed
- `H`: heat overlay
- `F`: molecule/food overlay
- `S`: toggle organism coloring by species
- `B`: toggle bright joined-cell/bond highlights (native Rust GUI)
- `V`: open the active-species catalog; recent species show `NEW MUT` or `NEW SEX`, creation tick, and parent species
- `+` / `-`: simulation speed
- `,` / `.`: zoom through 1–64 pixels per world tile
- `J` / `P` / `G` in the native inspector: jump to the newest living offspring, a living parent, or a joined living organism
- Left click: select an organism and inspect its realized state and genome
- Click a cyan `JUMP` relationship in the native inspector to follow that organism
- Click a species in the catalog to inspect one of its living members
- Mouse wheel: scroll genomes or the species catalog
- Click an empty tile: close the genome inspector
- `Esc`: quit

Generation sliders take effect on reset. **Founders** controls the total initial organisms, while **Genome seeds** controls the number of distinct founding lineages/species. Live sliders update the active simulation immediately. The **Asexual floor** slider controls the minimum success probability of an asexual attempt; inherited `asexual_rate` traits allow some organisms to reproduce up to four times faster than the baseline cooldown.

## Phase-learnings integration (bio-sim-proto phases 0 and 1)

Observations and controls distilled from the conserved-symbol program-soup
campaigns in the sibling `../bio-sim-proto` project. Companion profiles live in
`configs/phase_learnings/`.

| Phase finding | organism-sim translation |
|---|---|
| Population scale, not conservation, gates emergence and takeover persistence (1/5 events at 4k tapes, 3/5 at 32k) | `emergence_scale.toml`: 4x founders, 3x lineages, wider founder region at constant deposit density |
| Mutation has a Goldilocks regime: reference rate succeeds, zero and 8x fail | Default `mutation_multiplier = 1.0` is the reference; profiles pin it explicitly |
| Scarcity is resource-specific and structured, not uniform (`<`/`]` bottlenecks) | Every body-matter reproduction block is attributed to its limiting molecule; recorded per tick in the `matter_blocks` table and summarized by `organism-sim-report` |
| Conservation enters dynamics discontinuously (shadowing until first blocked write) | Report shows `first_body_matter_block_tick`, the tick the matter economy starts binding |
| An established ecology's demand equals its own content histogram, so a matched pool never blocks | `--deposit-match-ecology` / `deposit_match_ecology`: newly explored chunks draw deposits in proportion to founder body composition instead of uniformly; the founder region keeps primordial uniform geology |
| Saturation should be measured as content turnover, not population growth | Report prints late-window births/deaths per 1,000 ticks, births-per-death, and per-organism turnover |
| Most emergent takeovers are transient; crossings that hold are what matter | Report flags `transient_peak` (final below half of peak) and late-window population CV/trend |
| Intermediate scarcity (pool multiplier 2) is a genuinely constrained regime; 0.5 stress, 16 control | `scarcity_stress.toml` / `scarcity_moderate.toml` / `scarcity_rich.toml` vary deposit budget and recharge together |
| Decomposition must stay physically neutral, never target "bad" tapes | Decomposition already operates uniformly on chemical stability with no fitness term |

Quick comparison:

```text
uv run organism-sim-headless --config configs/phase_learnings/scarcity_moderate.toml
uv run organism-sim-report
```

In the 1,200-1,500 tick smoke runs, the moderate arm held births-per-death near
0.95 with a single limiting molecule, while the stress arm fell to 0.71 with
higher population variance and a different limiting molecule — the expected
phase-1 signature of regime-dependent, resource-specific scarcity.

## Scope

This implementation intentionally compresses the full design into a fast prototype. See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) for simplifications and [`SPEC.md`](SPEC.md) for the future engineered design.
