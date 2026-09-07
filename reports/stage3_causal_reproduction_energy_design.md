# Stage 3 causal reproduction, energy, persistence, and organization design

**Status:** model-development specification; no outcome thresholds in this document may be changed after the corresponding preregistration is committed.

## Purpose

The Stage 2 locality mechanism and Stage 3R neutral lineage clustering are established within their tested simulator conditions. The next phase asks what causes birth, what constrains it, whether inherited patches persist, and whether interaction-derived organizations can be identified without calling neutral families organisms.

This phase is divided into five independently gated experiments. Failure at one gate is retained and does not invalidate completed mechanics tests or license nearby parameter fishing.

## Terminology and claims

- **Scheduled birth:** the existing Bernoulli-selected pool-funded clone operation.
- **Interaction-gated birth:** a pool-funded clone attempted only after an exact execution-mediated copy event. Allocation remains simulator-mediated, so this is stronger than scheduled cloning but is not fully endogenous self-reproduction.
- **Energy Stage 3:** explicit spatial energy influx, transfer, execution expenditure, and dissipation. This is separate from Stage 3R's energy-free positive control.
- **Neutral family:** an offline lineage measurement label, never an organism definition.
- **Empirical organization:** a closed and self-maintaining set in an observed, coarse-grained reaction network. It is evidence about organization under a declared representation, not proof of organism identity.

## Backward compatibility

When all new options are disabled:

- Stages 0–2 consume the same RNG draws and produce the same simulated tape, occupancy, pool, and interaction trajectories as before this phase;
- existing Parquet schemas remain unchanged;
- Stage 3R `parent_first` scheduled birth remains available and unchanged;
- energy arrays contain only zeros and cannot influence selection or dissolution.

Every mechanism is selected by typed configuration rather than hidden conditionals or content-specific constants.

# Gate A: vacancy-opportunity control

## Confound addressed

The original parent-first local-placement campaign produced fewer births and 448 no-space blocks at radius 1, versus no blocks at radius 8. It established the complete local-placement mechanism but did not isolate displacement from vacancy access.

## New placement protocol: `vacancy_first`

For each scheduled attempt:

1. snapshot free cells and choose one target uniformly;
2. find occupied prospective parents within the configured toroidal radius of that same target;
3. choose one eligible parent uniformly;
4. atomically withdraw the selected parent's exact tape from the symbol pool;
5. place its child into the preselected vacancy.

A vacancy lacking a parent in range records `reproduction_blocked_no_parent`. The vacancy draw is independent of tape content. At the established occupancy range, the protocol should make target opportunity nearly identical across radii while retaining different parent-child displacement.

The experiment will compare radii 1 and 8 under `vacancy_first`. A mechanics-only pilot may select a bounded occupancy/rate setting using only block frequency, birth count, occupancy, pool turnover, and invariant outcomes. No family statistic may be inspected during pilot selection.

The confirmatory campaign must require negligible no-parent and pool blocks in both treatments and comparable successful birth counts before interpreting a spatial effect.

# Gate B: interaction-gated exact-copy birth

## Frozen trigger definition

During one BFF interaction, direction A→B is an exact copy event only if:

- A is byte-identical before and after execution;
- B differs from its pre-interaction state;
- B after execution is byte-identical to A after execution.

B→A is defined symmetrically. Equality is checked on complete byte arrays, not hashes or opcode composition.

The engine records a trigger fact at the instant the criterion is met, containing source/target IDs, cells, exact copied tape, direction, tick, and interaction round. After dissolution, birth is eligible only if the source is still alive and still byte-identical to the recorded source. Otherwise it records an invalidated trigger. Each surviving trigger receives at most one pool-funded placement attempt; the configured per-tick birth cap remains binding.

There is no Bernoulli reproduction rate in exact-copy mode. Trigger frequency is entirely produced by ordinary interaction and mutation dynamics. Trigger detection consumes no RNG.

## Interpretation

A viable campaign would show that execution-mediated exact copying can causally gate conserved births. It would not show autonomous allocation, membrane construction, or organismal reproduction.

A bounded liveness pilot is mandatory because the trigger may be absent or too rare. A zero-trigger outcome is a valid negative result and does not permit weakening the criterion.

# Gate C: explicit energy ledger

## State

Each spatial cell has nonnegative field energy. Each occupied tape has nonnegative held energy with a fixed capacity. The ledger records cumulative external influx and cumulative dissipation.

Initial field and tape energy are zero unless explicitly configured. Empty cells always have zero tape energy.

## Tick order

1. add configured total influx to the field;
2. diffuse field energy conservatively on the torus;
3. dissipate the configured field-decay fraction;
4. transfer local field energy into occupied tapes, bounded by absorption rate and tape capacity;
5. execute local interactions;
6. age tapes and update starvation state;
7. dissolve eligible tapes;
8. attempt reproduction;
9. attempt random reseeding;
10. check matter, occupancy, lineage, and energy invariants;
11. log facts.

## Influx, diffusion, and absorption

- `influx_rate` means total energy added per tick, distributed uniformly in the first implementation.
- diffusion uses a synchronous four-neighbor conservative stencil and requires coefficient in `[0, 0.25]`;
- field decay is irreversible dissipation;
- absorption transfers `min(local field, absorption_rate, tape capacity − held energy)` and does not create or destroy energy.

Structured environmental fields remain a later Stage 4 concern.

## Execution cost

The first member of each ordered pair is the active tape and pays execution cost. It must meet `min_to_interact`. The BFF substrate already enforces an execution budget with per-instruction and successful-write costs, so execution halts before overdrawing held energy. The exact reported energy consumption is deducted from the active tape and added to cumulative dissipation.

Background mutation is treated as exogenous physical noise and is not charged to a tape. This distinction is logged and fixed for the first energy gate.

## Dissolution and starvation

Held energy remaining at dissolution is dissipated. With energy enabled, `starved_ticks` counts consecutive ticks at or below a declared zero tolerance; reaching the configured threshold adds starvation as a dissolution cause. Starvation is inactive when energy is disabled.

## Energy-funded reproduction

A birth can require `birth_energy_cost` from its parent. The cost is deducted atomically and dissipated only if symbol withdrawal and placement can also succeed. Optional `offspring_energy` is transferred from parent to child and is bounded by child capacity. Pool failure, space failure, invalid trigger, or insufficient parent energy leaves matter and energy unchanged.

## Invariant

At every check:

```text
field energy + live tape energy + cumulative dissipation
    = cumulative external influx + initial energy
```

within a preregistered floating tolerance scaled to total throughput. Arrays must be finite and nonnegative, tape capacity may not be exceeded, and empty cells must hold zero tape energy.

A mechanics pilot selects one operating point using only conservation, numerical error, interaction activity, occupancy, energy starvation, and turnover. Trophic or organization metrics are prohibited during selection.

# Gate D: lineage-patch persistence

Add `reproduction.stop_tick`, where zero means no scheduled stop. A stopped mechanism consumes no reproduction RNG.

Using the already selected local scheduled-birth operating point, compare:

- local birth continuing through the full run;
- local birth switched off at a frozen checkpoint.

Measure neutral-family and exact-root neighbor excess at the switch tick and fixed later checkpoints. Primary persistence is the switch-off arm's excess relative to its own switch value, with the continued-birth arm as a positive control. Family definitions, permutations, seeds, and endpoints are frozen before execution.

This tests patch lifetime after causal input removal. It does not test genetic adaptation.

# Gate E: empirical organizational analysis

## Species representation

Exact tape hashes are known to be sparse. The first organizational diagnostic therefore defines a species as the exact eleven-component BFF composition count vector: counts of the ten opcodes plus aggregate non-opcode count. Counts sum to tape length and avoid arbitrary continuous clustering thresholds.

## Empirical reactions

Each interaction contributes an observed reaction:

```text
{A_before, B_before} -> {A_after, B_after}
```

in composition-species space. Multiplicity is retained. No-change reactions are recorded but cannot alone qualify a candidate as active.

## Candidate construction

For each frozen time window:

1. build the directed species-production graph from changed reactions;
2. use weakly connected components as deterministic candidate seeds;
3. repeatedly add products of internal observed reactions to compute empirical closure;
4. calculate observed stoichiometric net production using reaction counts;
5. call a set self-maintaining only if every member's net production is nonnegative, every member participates in an active reaction, and at least one active reaction changed a species;
6. report nesting by strict set inclusion among accepted candidates.

The first campaign is explicitly an identifiability diagnostic. It reports species recurrence, singleton fraction, reaction support, closure sizes, and null behavior before any organism claim. A label-permutation null over product species with reactants and reaction counts fixed tests whether accepted organizations exceed representation-induced chance.

## Limits

Empirical closure is window- and representation-dependent. Nonnegative observed flux is not proof that the set could sustain itself under perturbation. Any positive diagnostic must be followed by intervention tests that remove external species inflow and assess recovery.

# Implementation order and stopping rules

1. Implement `vacancy_first`, `stop_tick`, and exact-copy trigger facts with isolated unit tests.
2. Run backward-compatibility and bounded smoke tests.
3. Commit Gate A/B mechanics and preregistrations before pilots.
4. Implement the energy ledger and invariants as a separate reviewed change.
5. Run an energy mechanics pilot before any energy-coupled reproduction comparison.
6. Implement organizational diagnostics offline; do not feed them back into dynamics.
7. Execute confirmatory gates only when their positive-control and feasibility prerequisites pass.

If exact-copy triggers are absent in the frozen pilot, stop Gate B and report the negative result. If energy conservation fails, stop all energy campaigns. If organization species are non-identifiable, stop before closure hypothesis testing rather than changing representations post hoc.

# Deferred expensive work

No 500,000-tick run is required by this design. Such a run remains conditional on a future gate whose uncertainty is specifically temporal persistence and cannot be answered by bounded switch-off experiments.
