# Phase 2 preregistration — space, dissolution, and a nontrivial nutrient cycle

## Status

This document fixes Phase 2 semantics before implementation. Phase 2 adds space and dissolution only. Energy, signals, task bias, external fitness, and simulator-side replication detection remain disabled.

**Pre-acceptance amendment:** The liveness pilots found every exact content hash to be a singleton, making the original hash-label permutation statistics non-identifiable. `reports/phase2_spatial_metric_addendum.md` therefore freezes positional byte-identity excess and BFF-opcode-signature beta diversity before the matched radius campaign and before any 500,000-tick treatment. The original exact-hash statistics remain reported as diagnostics.

## 1. Scientific questions

1. Can a locally interacting conserved soup remain both unfilled and alive for 500,000 ticks?
2. Does locality produce content-hash patches above a well-mixed null?
3. Does locality increase block beta diversity?
4. Does locality contain a labeled hand-written parasite relative to a large-radius control?
5. How does interaction radius affect standing diversity?

## 2. State model

### 2.1 Lattice and occupancy

- The world is a `height × width` Moore lattice.
- Each cell is either empty or contains exactly one fixed-capacity tape.
- Occupied tapes retain stable, monotonically allocated `tape_id` values until dissolution.
- Empty cells contain no tape bytes and contribute no symbols to the tape histogram.
- The invariant `occupied cells + free cells = width × height` is checked at every configured invariant checkpoint.

### 2.2 Initial fill and conserved matter

- `symbols.initial_tape_fill` independently determines the target number of occupied cells, rounded to the nearest integer and clamped to at least two for runnable configurations.
- Occupied initial cells are chosen by one seeded permutation of lattice indices.
- A random substrate tape is generated for every occupied initial cell.
- The initial pool is proportional to the histogram of the occupied tapes only, using `symbols.pool_multiplier`.
- Conserved totals are fixed once initialization completes: `occupied tape histogram + pool histogram`.
- Vacancies contain no implicit null bytes.

This keeps the invariant unambiguous and makes placement possible only when the pool can supply a complete tape.

## 3. Tick order

Phase 2 uses this deterministic order:

1. local interaction round;
2. increment ages and update consecutive inert counters;
3. dissolve all candidates selected from the post-interaction state;
4. attempt exogenous placement into free cells;
5. check occupancy and symbol invariants;
6. log tick facts;
7. write epoch snapshots at configured cadence.

Environment and absorption remain no-ops until Phase 3.

## 4. Local interaction rule

- Tape A is sampled uniformly from occupied tapes.
- Tape B is sampled uniformly from occupied cells in A's Moore neighborhood at `world.interaction_radius`.
- A and B must be different cells.
- If fewer than two tapes are occupied, or A has no occupied neighbor, that attempted interaction is skipped and consumes no substrate execution.
- Sampling is with replacement across attempts. `world.interactions_per_tick` is the number of attempted local interactions.
- At a radius covering the entire toroidal lattice, this approaches the Stage 1 well-mixed control.
- Boundaries wrap toroidally so edge cells do not have systematically smaller neighborhoods.
- Mutation and pool-mediated execution are unchanged.
- Replication remains an offline hash inference; the interaction rule does not identify or reward replicators.

`shuffled_disjoint` remains a Stage 0/1 protocol. Stage 2 uses a new explicit `local_neighborhood` pairing mode.

## 5. Empty-cell placement rule

Phase 2 follows the original exogenous reseeding design rather than embedding a replication detector.

For every free cell, once per tick:

1. draw a Bernoulli event with probability `world.reseed_rate`;
2. on success, generate one random substrate tape using the simulation RNG;
3. atomically withdraw its complete 256-bin byte histogram from the pool;
4. if any required symbol is unavailable, reject the placement without changing pool or occupancy;
5. if available, occupy the cell, assign the next tape ID, age 0, inert count 0, and record a birth with no progenitor IDs.

A failed placement still consumes its documented RNG draws. There is no hidden fallback, designed organism, or free matter.

The primary 500,000-tick acceptance treatment will use a small positive, preregistered reseed rate selected by the benchmark/pilot ladder. A separate `reseed_rate = 0` control is allowed to die; that outcome is information, not a software failure.

## 6. Dissolution rule

A tape is selected for dissolution after interactions if any enabled condition holds:

- `substrate.is_inert(tape)` has been true for `dissolution.inert_ticks` consecutive ticks;
- age reaches nonzero `dissolution.max_age`;
- the seeded spontaneous draw is below `dissolution.spontaneous_rate`.

On dissolution:

- all tape bytes are atomically returned to the symbol pool;
- the cell becomes empty;
- a death fact records tape ID, tick, cell, and cause;
- no replacement occurs until the placement phase.

### 6.1 Inert timer

- The timer increments when `substrate.is_inert` is true in the post-interaction tape state.
- It resets to zero when `is_inert` is false.
- BFF's current structural definition—no write opcode—is retained for the first Phase 2 implementation and reported as a limitation because passive templates can still be useful to another tape.
- A later activity-based dissolution ablation must be a separate preregistered treatment, not a silent semantic change.

### 6.2 Starvation is disabled in Phase 2

`dissolution.starved_ticks` is ignored unless `energy.enabled` is true. Because energy begins in Phase 3, zero-energy placeholders cannot dissolve every Phase 2 tape.

## 7. Anti-clogging and anti-extinction rules

The original anti-clogging condition is necessary but not sufficient. A dead empty lattice must not pass.

### 7.1 Clogging

Define a clogged tick as `n_free_cells == 0`. A run fails the anti-clogging gate if a consecutive clogged interval exceeds `clog_threshold = 1,000` ticks.

### 7.2 Extinction and liveness

The primary acceptance run must also satisfy all of:

- `n_tapes > 0` at every tick;
- mean occupied fraction in the final 10% of ticks is at least 0.20;
- at least one interaction executes in at least 90% of final-window ticks;
- successful content-changing writes occur in the final 10% window;
- cumulative dissolutions and successful placements are both greater than zero;
- pool turnover continues in the final window.

A consecutive interval with `n_tapes == 0` longer than `extinction_threshold = 1` is extinction and fails the primary gate.

These thresholds will not be changed after the 500,000-tick treatment starts.

## 8. Spatial analyses fixed in advance

### 8.1 Content-hash spatial autocorrelation

Exact hashes are categorical, so numeric hash values will not be inserted into Moran's I. The primary statistic is **neighbor identity excess**:

- observed: fraction of occupied, undirected radius-1 neighbor pairs with equal content hash;
- null: randomly permute observed hashes over the same occupied cells, preserving occupancy and abundance;
- effect: observed identity fraction minus mean null fraction;
- p-value: one-sided permutation probability using 999 permutations and a seeded analysis RNG;
- report a z-score only as a secondary descriptive quantity.

Primary decision: final-window mean effect > 0 and pooled permutation p < 0.05.

### 8.2 Block beta diversity

Partition the lattice into fixed nonoverlapping blocks. For q ∈ {0, 1, 2}:

- gamma diversity: Hill diversity of the whole occupied lattice;
- alpha diversity: occupancy-weighted mean within-block Hill diversity;
- beta diversity: gamma / alpha.

Report empty blocks but exclude them from alpha's occupied weighting. Beta = 1 means no compositional differentiation; values above 1 indicate block differentiation.

Primary decision: final-window beta is above the hash-permutation null with pooled p < 0.05 for q=1. “Significantly above zero” is replaced because multiplicative beta diversity has a minimum of 1, not 0.

## 9. Parasite containment experiment

This is the one allowed designed-parasite exception.

- Start from the same host soup and insert the same labeled parasite count and locations for every treatment.
- Compare radius 1 with a radius covering the lattice.
- Use at least 10 matched seeds.
- Primary outcome: maximum and final fraction of the parasite hash/family.
- Containment criterion: radius 1 has a lower final parasite fraction than the large-radius treatment with a paired effect interval excluding zero, and does not reach 90% global occupancy in at least 8/10 seeds while the large-radius treatment does in at least 8/10.
- If the designed parasite is not viable in the large-radius positive control, the experiment is invalid rather than evidence for containment.

## 10. Radius sweep

- Radii: 1, 2, 4, 8.
- At least 5 matched seeds per radius for the pilot; 10 per radius for the acceptance result if feasible.
- Fixed capacity, initial fill, pool multiplier, mutation, reseed, dissolution, horizon, and logging cadence.
- Outcomes: Hill q-profile, neighbor identity excess, block beta diversity, occupied fraction, turnover, and parasite fraction when applicable.
- Report effect sizes and intervals; monotonicity is not assumed.

## 11. Benchmark ladder and stopping rules

The 500,000-tick protocol is benchmarked without changing scientific parameters after outcomes are inspected:

1. correctness: 8×8, 100 ticks, full invariants/logging;
2. smoke: 32×32, 1,000 ticks, sampled logging;
3. scale: 64×64, 1,000 ticks, aggregate logging;
4. duration: selected acceptance lattice, 10,000 ticks;
5. projection: estimate 500,000-tick wall time and storage from steps 3–4;
6. full run only if projected wall time and storage fit the declared budget.

Performance runs use aggregate logging (`interaction_log_rate = 0`, sparse tape snapshots). The simulator still records tick and epoch facts needed by the gate.

A projection is not a completed 500,000-tick validation. If the full run is infeasible, report the measured projection and required optimization rather than silently reducing the gate.

## 12. Required software checks

Before the Phase 2 campaign:

- Stage 0/1 golden determinism remains unchanged;
- placement and dissolution preserve all 256 symbol totals;
- failed placement is atomic;
- occupancy, IDs, cells, ages, and inert timers remain consistent;
- local pairs obey radius and toroidal geometry;
- starvation cannot trigger in Stage 2;
- same seed/config gives byte-identical raw tables;
- spatial statistics pass clustered and shuffled fixtures;
- all existing tests and strict typing pass.

## 13. Original Phase 2 gate, with clarified decisions

| Original criterion | Operational version |
|---|---|
| 500k ticks without clogging | No >1,000-tick full-occupancy interval **and** all liveness/anti-extinction conditions pass |
| Visible and measurable spatial structure | Neighbor identity excess > 0 against a seeded permutation null |
| Beta diversity significantly above zero | Multiplicative beta > its permutation null; theoretical minimum is 1 |
| Parasite containment | Valid large-radius positive control plus preregistered matched-radius contrast |
| Radius 1–8 sweep | Radii 1, 2, 4, 8 with matched seeds and fixed non-radius parameters |

## 14. Integrity rules

- No fitness function, culling, elite archive, novelty search, or simulator-side replication detector.
- No parameter changes after observing an acceptance treatment.
- Pilot-selected parameters are frozen in a dated addendum before acceptance runs.
- Failed and extinct runs remain in the analysis.
- Invariant failure halts and fails a run.
- Negative spatial or containment results are reported without tuning until positive.
