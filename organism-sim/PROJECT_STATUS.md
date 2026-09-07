# Emergent Organism Simulation — Project Status

## Status

The repository contains a playable Python/pygame-ce prototype, an implementation-ready conceptual specification, automatic run recording, headless configuration support, analysis tooling, tests, and an initial analysis-driven balancing pass.

This prototype is intentionally optimized for rapid experimentation. The complete design in [`SPEC.md`](SPEC.md) remains the source of truth for a future engineered implementation.

## Documentation

- [`SPEC.md`](SPEC.md) — full conceptual and implementation-level specification
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — prototype architecture, stages, simplifications, and acceptance criteria
- [`README.md`](README.md) — installation, launch commands, controls, recording, configuration, and reporting
- [`analyses/RUN_ANALYSIS.md`](analyses/RUN_ANALYSIS.md) — analysis of recorded runs and resulting balancing changes
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — this consolidated progress summary

## Specification Completed

The specification defines:

### World and simulation

- Finite two-dimensional toroidal grid
- Fixed deterministic simulation ticks
- Different action frequencies based on organism speed
- Initial target scale of hundreds of organisms
- Configurable generation and live simulation controls
- Python/pygame-ce prototype with optional future batch-oriented Rust FFI through PyO3

### Matter conservation

- Procedurally generated discrete elements
- Integer element and molecule counts
- Molecules represented as aggregated batches rather than individual objects
- Exact element-vector conservation through digestion, waste, reproduction, death, and decomposition
- Matter ownership across world cells, organisms, corpses, colonies, and transaction escrow

### Energy conservation

- Continuous chemical energy stored in molecule batches
- Environmental heat stored in grid cells
- Mana derived by absorbing environmental heat
- Active magical-effect energy
- Global invariant covering chemical energy, heat, mana, and magical effects
- Mana usable for magic, basal maintenance, and lifespan support
- Mana excluded from movement, growth material, repair material, and reproductive matter
- Expended energy returned to environmental heat

### Procedural chemistry

- Procedural element and molecule definitions
- Abstract four-dimensional chemical signatures separate from magical elements
- Bounded run-local molecule catalogs with latent molecule types
- Monatomic fallbacks ensuring all matter remains representable
- Digestion, assimilation, waste, detoxification, and decomposition reactions
- Relational toxicity based on molecule descriptors and organism phenotype
- Ecological molecule persistence through production, consumption, recycling, and preference

### Biological hierarchy

- Global procedural priors
- Immutable heritable genomes containing distributions
- Immutable phenotypes sampled at birth
- Mutable nested organism state
- Persistent species and candidate-lineage state

### Genome design

- Bounded scalar, probability, discrete, simplex, vector, and policy-weight distributions
- Pathway genes for digestion, waste, and detoxification
- Linkage modules preserving coherent inherited strategies
- Asexual mutation
- Multi-parent sexual recombination
- Bounded genomic distance based conceptually on Jensen–Shannon divergence
- Traits for morphology, metabolism, locomotion, chemistry, behavior, magic, aging, reproduction, sociality, and perception

### Phenotype design

- Realized morphology and tile footprint
- Metabolism independent of size
- Locomotion, digestion, thermal, mana, toxin, magic, aging, reproduction, social, and sensory traits
- Birth-time validation rules and deterministic phenotype sampling

### Organism design

- Identity, lineage, genome, phenotype, and species references
- Spatial, body, energy, health, lifecycle, behavior, chemistry, reproduction, social, schedule, and cache records
- Authoritative-versus-derived-state distinctions
- Matter and energy invariants
- Central registries for relationships, colonies, effects, species, chemistry, and corpses

### Reproduction

- No fixed sexes or genders
- One offspring per successful asexual event
- Genome-driven offspring count for sexual reproduction
- Sexual reproduction among two or more contacting ready organisms
- Probabilistic genomic compatibility with no absolute cutoff
- Nonrefundable attempt energy after reproductive commitment
- Matter transferred only for successfully created offspring
- Offspring placement on nearest valid wrapped cells
- Sampled birth size and growth toward adult size

### Species

- Classification combining ancestry, genomic distance, compatibility, and persistence
- Candidate lineages before formal species promotion
- Species assignment, promotion, split, merge, and extinction rules
- Reproductive-history modifiers

### Behavior

- Stochastic inherited weighted-utility policy
- Bounded observations and target candidates
- Directed food seeking, hunting, fleeing, mate seeking, and heat seeking
- Random exploration retained through utility sampling and target noise
- Future neural-policy compatibility through stable observation and action interfaces

### Magic

- Fire, water, earth, and air as effect channels rather than chemical elements
- Affinity, resistance, efficiency, range, offense, defense, and escape traits
- Fire damage, water slowing, earth warding or immobilization, and air displacement or sensory disruption
- All magical energy returned to heat
- No magical creation of matter

### Cooperation and multicellularity

- Alliances and symbiotic relationships
- Resource and sensory sharing
- Metabolic chains and complementary strategies
- Colony records retaining separate member organisms
- Maintenance and duplicated-perception efficiency bonuses
- Composite asexual reproduction
- No energy or matter creation from cooperation bonuses

### Lifecycle

- Basal maintenance from chemical energy and mana
- Starvation and maintenance debt
- Probabilistic lifespan hazard
- Paid chemical/mana lifespan support
- Death through injury, aging, starvation, toxins, or magic
- Atomic transfer into corpse and environmental matter
- Stability-driven decomposition

### Auditing, persistence, and quality

- Exact integer matter ledger
- Floating-point energy ledger with bounded tolerance
- Transaction audit records
- Multiple audit levels
- Deterministic save/replay design
- UI, performance, testing, and Rust FFI requirements
- Eight staged implementation milestones

## Prototype Implemented

### Package structure

- `src/organism_sim/config.py` — simulation configuration and validation
- `src/organism_sim/config_io.py` — JSON/TOML loading and CLI overrides
- `src/organism_sim/chemistry.py` — procedural chemistry and molecule batches
- `src/organism_sim/genetics.py` — genes, genomes, phenotypes, mutation, and recombination
- `src/organism_sim/entities.py` — organisms, species, effects, corpses, colonies, and statistics
- `src/organism_sim/world.py` — toroidal world, footprints, deposits, occupancy, and heat
- `src/organism_sim/simulation.py` — simulation engine and ecological mechanics
- `src/organism_sim/app.py` — pygame application and controls
- `src/organism_sim/cli.py` — headless execution
- `src/organism_sim/recording.py` — automatic SQLite run recording
- `src/organism_sim/report.py` — recorded-run summaries

### Procedural world

- Configurable toroidal grid
- Procedural element definitions
- Procedural bounded molecule catalog
- Discrete molecule counts and continuous batch energy
- Environmental molecule deposits
- Heat field with toroidal diffusion
- Stability-driven environmental decomposition

### Organisms

- Sampled genomes and phenotypes
- Multiple seeded founder archetypes
- Independently sampled size and basal metabolism
- Variable connected tile footprints
- Body, gut, and waste inventories
- Chemical reserves, mana, integrity, maintenance debt, toxins, cooldowns, and status effects

### Behavior and movement

- Utility-driven stochastic action selection
- Directed movement toward molecule deposits
- Directed prey pursuit
- Directed mate seeking
- Directed fleeing from strong visible threats
- Directed heat seeking
- Heat absorption only after reaching a heated occupied tile
- Random wandering and noisy target selection
- Toroidal shortest-direction movement
- Collision-aware whole-footprint movement
- Failed movement energy cost

### Chemistry and ecology

- Eating environmental molecule batches
- Digestion and energy capture
- Assimilation into body matter
- Waste production and excretion
- Relational toxin exposure
- Passive and active detoxification
- Predation based partly on body compatibility
- Matter recycling through death and environmental deposits
- Optional element-conserving environmental reactions (`A + B → C`)
- Sparse catalyst/toxin byproduct fields with scale-based decay
- Local chemistry fit coupled to digestion, observations, and guest upkeep
- Bounded internal guests with chemistry-dependent demand/exchange telemetry

### Energy and mana

- Chemical energy expenditure returned to heat
- Basal maintenance paid from chemical energy and mana
- Heat absorption into mana
- Mana decay into heat
- Paid lifespan support
- Conservation audits

### Magic

- Fire integrity damage
- Water slowing
- Earth defensive warding
- Air forced displacement
- Mana commitment and effect expiration
- Effect energy returned to heat

### Reproduction

- Asexual and sexual reproduction
- Genome recombination and mutation
- Reproduction cooldowns
- Energy commitment regardless of post-commitment outcome
- Matter transfer only after successful offspring placement
- Offspring growth targets
- Configurable asexual probability floor
- Heritable `asexual_rate` from `0.25×` to `4×`
- Optional configurable sexual probability floor
- Sexual success using both parents' propensity, fertility, and genomic distance
- Independent sexual and asexual strategies
- Tracking of unique sexual parents and successful sexual events

### Species

- Configurable total founder organisms
- Configurable founder genome seeds/archetypes
- One initial species per founder archetype
- Online offspring species assignment by genomic distance
- Species colors, populations, births, deaths, and representative genomes

### Alliances and colonies

- Utility-selected alliance attempts
- Compatibility-based alliance probability
- Central alliance set
- Colony formation for qualifying asexual specialists
- Maintenance reduction from colony membership
- Analysis-informed relaxed colony eligibility defaults

### Pygame interface

- Real-time toroidal world display
- Organism footprints colored by species or energy
- Environmental molecule overlay
- Heat overlay
- Mana indicators
- Corpse markers
- Pause, resume, step, reset, seed, and speed controls
- Live and reset-required sliders
- Selected-organism highlighting

### Organism and genome inspector

Clicking an organism displays:

- Identity, species, age, generation, and parents
- Area, mass, energy, mana, integrity, toxins, action, offspring, and kills
- Sexual-parent status
- Asexual propensity and reproduction rate
- Genome ID and parent genomes
- Distance from species representative genome
- Every trait distribution's center and spread
- Diet, toxin, magic affinity, and magic resistance vectors
- Dominant inherited policy drive per action
- Scrollable genome details

### Species catalog

Pressing `V` opens a scrollable active-species view containing:

- Species ID and color
- `NEW MUT` or `NEW SEX` markers for recently created species
- Origin type, creation tick, and parent species
- Population
- Births and deaths
- Representative genome ID
- Typical area and basal metabolism
- Asexual and sexual propensities
- Asexual reproduction rate
- Click-through to inspect a living species member and its genome

### Adjustable GUI defaults

Reset-required controls include:

- Founder organism count
- Founder genome-seed count
- Element count
- Molecule count
- Deposit count

Live controls include:

- Simulation ticks per second
- Heat diffusion
- Experimental primary production (local heat-to-chemical recycling; off by default)
- Decomposition
- Mutation multiplier
- Maintenance-cost multiplier
- Asexual probability floor
- Sexual-floor enabled toggle
- Sexual probability floor

## Headless Operation

### Dedicated CLI flags

Headless mode exposes flags corresponding to GUI controls, including:

- Founder and genome-seed counts
- Element, molecule, and deposit counts
- Heat diffusion and decomposition
- Mutation and maintenance multipliers
- Asexual and sexual probability floors
- Sexual-floor enable/disable toggle
- World dimensions
- Mana decay and reaction rate
- Audit and recording intervals

### JSON and TOML configuration

Example files:

- [`configs/headless.example.toml`](configs/headless.example.toml)
- [`configs/headless.example.json`](configs/headless.example.json)

Configuration supports:

- `[simulation]` or `simulation` section
- `[run]` or `run` section
- CLI values overriding files
- Repeatable `--set FIELD=VALUE` for every `SimulationConfig` field
- `--print-effective-config` without launching a run
- Custom output through `--runs-dir` or `ORGANISM_SIM_RUNS_DIR`

## Automatic Data Collection

Every GUI and headless launch creates a unique directory under `runs/` unless redirected:

```text
runs/<timestamp>-seed<seed>-<run-id>/
├── manifest.json
└── run.sqlite
```

### Recorded static data

- Run metadata and schema version
- Initial configuration and conservation baseline
- Element definitions
- Molecule definitions
- Every genome
- Every realized phenotype
- Organism identity, ancestry, lineage, species, generation, and birth information

### Recorded metric data

The following are sampled every 5 ticks by default:

- Population, species, births, deaths, reproduction, attacks, magic, alliances, and colonies
- Chemical, mana, heat, magical-effect, and total energy
- Energy error
- Exact element totals
- Molecule abundance and chemical energy
- Lifecycle and relationship events
- Tick-stamped configuration events

### Sampled detailed data

The following are recorded every 20 ticks by default and always at run start and close:

- Organism position, footprint area, mass, reserves, mana, integrity, toxins, action, and social state
- Complete organism body, gut, and waste inventories
- Species, corpse, magic-effect, and colony state

Alliances are immutable relationships and are therefore stored once at creation rather than copied into every detail snapshot. Compressed exact heat grids and sparse environmental molecule fields are recorded every 50 ticks by default and at run boundaries. All detail, snapshot, and commit intervals are configurable; setting them to one restores full per-tick fidelity.

### Recorded lifecycle events

- Founder creation
- Birth
- Death
- Species creation
- Sexual-parent emergence
- Alliance creation
- Colony creation

Every GUI reset is counted as a distinct run. It finalizes the previous database, creates a new tick-zero dataset marked `gui_reset`, and records `previous_run_id` so reset sequences can be analyzed together.

## Analysis Tooling

The command:

```text
uv run organism-sim-report
```

summarizes the latest run. A specific database can be supplied explicitly.

Reports include:

- Tick count
- Final and peak population
- Peak species
- Births and deaths
- Asexual and sexual reproduction events
- Unique sexual parents
- Maximum energy error
- Final species populations
- Most abundant final molecules

Direct SQLite queries remain available for custom analysis.

## Recorded-Run Analysis Completed

[`analyses/RUN_ANALYSIS.md`](analyses/RUN_ANALYSIS.md) analyzes 14 recorded runs totaling approximately 5.73 GB.

### Controlled sweep

- Ten comparable 1,500-tick runs
- Founder archetype counts from 13 through 22
- Seed 7 for every run
- All other configuration values held constant

### Main findings

- Mean final population: 87.4
- Mean founder retention: 29.1%
- No monotonic survival improvement from more founder archetypes
- Moderate positive relationship between founder archetypes and absolute surviving species
- Strong species dominance in several runs
- Approximately 60% attrition mortality and 40% predation mortality
- Predation declined strongly as founder archetype count increased
- Births did not replace deaths
- Sexual reproduction was approximately 3% of births
- Maximum observed generation was only 3–5
- Alliances formed, but no colonies formed in the analyzed sweep
- One legacy long run reached complete extinction
- Exact element conservation across every analyzed run
- Energy errors consistent with floating-point rounding
- Full recording generated approximately 385–411 MB for each 1,500-tick run

## Analysis-Informed Improvements

Based on the initial run analysis:

1. Added an optional sexual reproduction probability floor, now enabled at 12% by default.
2. Raised the asexual reproduction floor to 20%.
3. Made effective maturity earlier through a 0.65 maturity-age multiplier.
4. Added a 1.25 reproduction action-utility bonus for ready organisms with reserves.
5. Reduced default reproduction energy cost to 50% and cooldown to 75% of the original values.
6. Added exact attempt, resource-block, probability-failure, and placement-failure counters.
7. Removed the requirement that sexual propensity exceed asexual propensity before mate selection.
8. Included both parents' sexual propensity in sexual success.
9. Added a maintenance-cost multiplier and adopted the supported 0.75 setting as the default.
10. Relaxed colony specialist defaults:
   - Maximum sexual propensity: `0.10 → 0.25`
   - Minimum asexual propensity: `0.50 → 0.35`

A same-seed, 900-tick smoke comparison using a 15% sexual floor produced:

| Setting | Final population | Births | Sexual events | Unique sexual parents | Colonies |
|---|---:|---:|---:|---:|---:|
| Floor disabled | 107 | 80 | 1 | 2 | 0 |
| Floor enabled at 15% | 109 | 86 | 5 | 9 | 3 |

This was a directional smoke test, not a statistically robust experiment.

The subsequent recommended follow-ups found that maintenance 0.75 remained the strongest supported general improvement and reproduction cost 0.50 improved retention and replacement in all five paired seed blocks. Deposit count and founder-archetype effects on retention were inconsistent, so their defaults were not changed. Chemistry, world, founder, and runtime random streams are now independent, preventing deposit-count changes from altering founder draws in future paired experiments. The 10,000-tick study still had eight extinctions in ten runs, so the new defaults are not evidence of long-term persistence.

## Defects Fixed

- Fixed direct comparison of tied `MoleculeBatch` objects during reproductive preview.
- Added a regression test for tied reproductive molecule batches.
- Fixed logarithmic-trait overflow causing `math range error`.
- Logarithmic recombination, mutation, and sampling now remain bounded in transformed space.
- Fixed organisms selecting rest and then moving randomly.
- Fixed organisms absorbing heat remotely rather than moving to it.
- Fixed directed movement to use wrapped target distance.
- Fixed founder lineage IDs and initial species seeding behavior.
- Added deterministic and conservation checks around these changes.

## Validation Status

At the time this file was written:

- **64 tests pass**
- Ruff reports no issues
- Headless and dummy-display Pygame smoke tests pass
- Matter remains exactly conserved in tests and analyzed runs
- Energy remains conserved within floating-point tolerance
- GUI and headless automatic recording both work
- JSON and TOML headless configuration both work

Tests cover:

- Directed movement, heat seeking, and fleeing
- Configuration loading and CLI overrides
- Conservation
- Determinism and random-stream isolation across deposit conditions
- Genetics and logarithmic overflow protection
- Automatic recording
- Reproduction costs, floors, cooldowns, and sexual-parent tracking
- Colony formation
- Founder species seeding
- Toroidal topology and heat diffusion

## Performance Improvements

- Cached footprints, visibility cells, body-derived values, chemistry preferences, policy vectors, maturity ages, genome distances, and repeated spatial distances
- Reused radius-one observations for contact detection
- Maintained a live-organism index rather than scanning all historical organisms
- Replaced full occupancy rebuilds after every birth with dirty-footprint refreshes
- Added automatic dense-scene rendering through one logical pixel map
- Capped scheduler work at one simulation tick per event-loop pass so an overloaded engine cannot enter multi-tick catch-up freezes
- Sampled metrics, conservation, and molecule totals every 5 ticks while retaining exact source ticks for lifecycle events
- Stored immutable alliances once rather than duplicating every edge in every detail snapshot
- Sampled large organism/species tables every 20 ticks
- Sampled compressed heat/deposit snapshots and committed SQLite every 50 ticks
- Preserved final detailed and spatial state at run close
- Added full-fidelity interval overrides through config and CLI
- Indexed environmental reaction candidates and staged product writes to keep the dynamic phase bounded

The 3,418-tick seed-7 equilibrium run originally completed at approximately 6.3 recorded ticks/second and produced an approximately 363 MB database. The optimized implementation reproduced its exact final state and produced an approximately 125 MB database. A later GUI run reached 1,206 living organisms at tick 5,518 and averaged about 12.1 ticks/second wall-clock. Dense rendering reduced a synthetic 1,200-organism, 4,200-deposit frame from 19.0 ms to 8.2 ms.

A coarse whole-kernel Rust/PyO3 port now owns organisms, chemistry, genomes, the chunk world, spatial occupancy, heat, actions, reproduction, species, social state, effects, conservation, and deterministic RNG. The native release measures approximately 1,043 / 569 / 295 ticks per second at 300 / 600 / 1,200 founders. A 10,000-tick run grew from 1,200 to 14,166 organisms and completed in 184 seconds (54.4 ticks/second averaged across the growth). The Python reference engine was also accelerated without changing its exact seeded fingerprint. See `PERFORMANCE.md`. 

## Current Limitations

- The prototype does not implement every full-system detail in `SPEC.md`.
- Species assignment is online rather than full candidate-lineage clustering.
- Chemistry uses a simplified generated catalog and compact reactions. Dynamic runs reserve a bounded closure of dimer compounds at catalog generation; this is intentional and means dynamic/off runs should be interpreted as paired ecological conditions, not identical molecule catalogs.
- The dynamic-chemistry association and guest-economy metrics are descriptive; the five-seed study did not produce enough persistent internal guests to support an endosymbiosis claim.
- Multi-parent sexual reproduction is conceptually supported by genetics but runtime mating usually uses pairs.
- Colonies are lightweight and do not yet implement full composite reproduction.
- The neural policy remains future work.
- The Rust kernel is available for headless and native-GUI research and writes compact JSONL/NPZ records. The shared report command now reads both compact Rust and SQLite records, but compact recordings intentionally omit the Python engine's full per-organism time series.
- Full per-tick recording consumes substantial disk space and reduces headless performance.
- Without primary production, ten-seed follow-ups showed 8/10 extinctions by 10,000 ticks; the closed model drains chemical free energy into heat.
- Experimental passive primary production produced 0/10 extinctions at 10,000 ticks for the best profile, but only 4/10 runs met strict equilibrium criteria and outcomes remained seed-sensitive.

## Recommended Next Experiments

1. Repeat the deposit factorial with isolated RNG streams so each seed uses identical founders across deposit conditions.
2. Confirm reproduction cost 0.50 on at least five new paired seeds before treating its effect as established.
3. Test interventions that directly improve organism energy acquisition; 99.3% of observed resource blocks were energy blocks.
4. Re-run 10,000-tick persistence after any intervention and report extinction, replacement fertility, and late-window slope.
5. Track generation depth, species evenness, and colony persistence.
6. Profile recording and simulation separately before selecting any subsystem for Rust FFI.

## Common Commands

Launch the GUI:

```text
uv run organism-sim
```

Launch a headless run:

```text
uv run organism-sim-headless --ticks 1000 --founders 300 --genome-seeds 8
```

Launch from TOML:

```text
uv run organism-sim-headless --config configs/headless.example.toml
```

Run the current analysis-informed configuration explicitly:

```text
uv run organism-sim-headless \
  --ticks 1500 \
  --genome-seeds 20 \
  --sexual-floor-enabled \
  --sexual-floor 0.12 \
  --maturity-multiplier 0.65 \
  --reproduction-drive 1.25 \
  --reproduction-cost 0.50 \
  --reproduction-cooldown 0.75 \
  --maintenance-multiplier 0.75
```

Disable the sexual floor for a control:

```text
uv run organism-sim-headless --no-sexual-floor-enabled
```

Inspect effective configuration:

```text
uv run organism-sim-headless \
  --config configs/headless.example.toml \
  --print-effective-config
```

Summarize the latest run:

```text
uv run organism-sim-report
```

Run the paired dynamic-chemistry study (five seeds per condition):

```text
nu experiments/run_dynamic_chemistry.nu
```

Run tests and lint:

```text
uv run --extra dev pytest
uvx ruff check src tests
```
