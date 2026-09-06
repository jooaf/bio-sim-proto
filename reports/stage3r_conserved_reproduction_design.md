# Stage 3R explicit conserved reproduction and lineage design

## Status

This is a model-development extension requested after Phase 2. The existing roadmap reserves Stage 3 for the energy ledger. To avoid silently redefining that gate, the implementation is called **Stage 3R**: it uses `run.stage = 3` with energy explicitly disabled to isolate reproduction mechanics. It does not constitute passage of the planned energy-ledger Stage 3.

## Goal

Add an explicit, neutral, exactly conserved copy-birth operation so parent–offspring lineage and lineage-defined spatial patches can be tested. This is not claimed to be endogenous self-replication: the simulator schedules birth and the selected parent's current tape is cloned.

## Configuration

Add `[reproduction]`:

- `enabled`: false by default; forced off below stage 3;
- `rate`: independent per-live-parent birth-attempt probability per tick;
- `placement_radius`: Moore radius for empty target cells;
- `max_births_per_tick`: hard upper bound on successful births.

All fields are frozen before experiments and included in run hashes/manifests.

## Tick order

For spatial stage 3R:

1. local interactions and conserved writes;
2. age increment;
3. dissolution and complete matter return;
4. pool-funded copy birth;
5. exogenous random reseeding;
6. invariant checks;
7. factual logging.

Birth follows dissolution so reclaimed matter and vacancies are immediately available. Random reseeding follows birth so inherited reproduction receives first access to a vacancy, but neither can overdraw the pool.

## Birth transaction

For each occupied tape after dissolution:

1. draw one Bernoulli attempt using the simulation's sole RNG;
2. randomize candidate-parent order to avoid flat-index priority;
3. find empty cells in the parent's toroidal Moore neighborhood;
4. choose one empty target uniformly;
5. copy the parent's full tape;
6. atomically withdraw that complete byte multiset from the symbol pool;
7. place the child with a new monotonically increasing tape ID;
8. append a birth fact with exactly one progenitor ID.

If no local vacancy exists or the pool cannot supply the tape, no state changes. The reason is counted and logged. Stop after `max_births_per_tick` successes.

## Conservation and occupancy invariants

Every successful child adds exactly one fixed-length tape and subtracts the identical byte histogram from the pool. Required invariants remain:

- occupied tape histogram + pool histogram equals frozen totals for every byte;
- no negative pool counts;
- unique nonnegative live tape IDs;
- empty cells have zero storage and sentinel metadata;
- child birth cell was empty and within the configured toroidal radius;
- child birth content equals the parent content at the birth transaction;
- each reproductive child has one existing parent ID;
- occupied + empty equals lattice capacity.

## Logging

Reuse the `lineage` table:

- child row at birth has `progenitor_ids = [parent_id]`;
- birth content hash and cell are recorded;
- the scheduler retains progenitor IDs in its live birth registry so terminal death rows remain attributable.

Add factual events:

- `offspring_born` with parent ID and cells;
- `reproduction_blocked_no_space` aggregate;
- `reproduction_blocked_pool` aggregate.

Add tick facts:

- successful births;
- no-space blocks;
- pool blocks.

## Backward compatibility

- Stages 0–2 force reproduction off.
- With reproduction disabled, RNG consumption and all existing Stage 2 Parquet values remain unchanged except no schema should be altered until compatibility implications are tested.
- To avoid changing old tick schemas, initial implementation records aggregate birth counts as events rather than adding tick columns. Offline reports aggregate events.

## Lineage-patch proxy

The project rule says not to hard-code an organism. Therefore the first test is explicitly a **neutral lineage-patch proxy**, not an organism detector.

Each root tape receives a neutral family label `root_tape_id mod 16`; reproductive children inherit their parent's root. Randomly placed tapes become new roots with the same deterministic modulo rule. Labels do not affect chemistry, birth probability, dissolution, or interaction.

At final snapshots:

- map each live tape through transitive parent links to its root family;
- compute equal-family radius-1 neighbor excess against fixed-occupancy label permutations;
- report lineage depth, reproductive births, family abundance, and patch persistence.

A matched experiment compares offspring placement radius 1 versus 8 with identical seeds and birth rates. A positive local-placement effect would validate lineage clustering, not organism-level closure or adaptation.

## Risks

1. Neutral copy birth may fill the lattice and suppress turnover.
2. Exact parent tape histograms may be unavailable in the pool, creating composition-dependent birth blocking.
3. Modulo root families are a measurement device and can merge unrelated roots.
4. Scheduled cloning bypasses endogenous BFF replication.
5. Python runtime may become prohibitive.

A bounded liveness pilot must precede any lineage-patch campaign. Birth rate is selected only on occupancy, turnover, and blocking—not spatial family effects.

## Explicit exclusions

- no fitness multiplier;
- no task or signal reward;
- no energy coupling;
- no mutation during the birth transaction;
- no multi-parent recombination;
- no claim that a tape or neutral family is an organism;
- no 500,000-tick Stage 3R run before bounded mechanics and liveness pass.
