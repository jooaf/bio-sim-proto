# Stage 3 causal reproduction mechanics pilots preregistration

**Frozen before execution:** 2026-09-06

## Shared rules

These pilots validate two preregistered causal-mechanics changes. They do not test energy, fitness, organisms, or adaptation. All failures, extinctions, and invariant violations remain in denominators. No neutral-family or spatial-composition endpoint may be inspected during these pilots.

Both pilots retain the selected Stage 3R operating point except where explicitly varied:

- BFF, 64-byte tapes;
- 32×32 toroidal lattice, 80% initial fill;
- interaction radius 1 and 512 attempts/tick;
- mutation `1/4096`;
- dissolution and reseed rates `1e-5`;
- symbol-pool multiplier 16;
- energy, tasks, and signals disabled;
- maximum four births/tick.

## Pilot A: vacancy-first opportunity

### Matrix

- placement protocol: `vacancy_first`;
- placement radius: 1 versus 8;
- matched seeds: `202609120`–`202609122`;
- 5,000 ticks;
- scheduled birth rate: `2e-5`;
- six total runs.

### Endpoints

For each run report successful births, attempts, no-parent blocks, pool blocks, occupancy, interaction/write activity, dissolution, random placement, pool turnover, conservation, and invariant failures.

The mechanism is feasible only if:

- 6/6 runs exit successfully and conserve every symbol exactly;
- zero invariant failures;
- final-window occupancy is in `[0.40, 0.95]` for every run;
- interactions, successful writes, dissolution, random placement, reproduction, and pool turnover are nonzero in every run;
- aggregate pool blocks are zero;
- aggregate no-parent blocks are at most 2% of attempts in each radius treatment;
- median births are at least 50 in each treatment;
- the ratio of smaller to larger treatment median birth count is at least 0.90.

If feasible, proceed without changing parameters to a separately preregistered lineage-patch confirmation. If infeasible, stop Gate A; do not tune fill, rate, or radius.

## Pilot B: interaction-gated exact copy

### Matrix

- trigger: frozen byte-exact execution-mediated copy criterion;
- placement: parent-first, radius 1;
- reproduction rate: exactly zero;
- seeds: `202609123`–`202609125`;
- 10,000 ticks;
- three total runs.

### Endpoints

Report exact-copy trigger count, valid pool-funded births, invalidated triggers, no-space blocks, pool blocks, occupancy, turnover, conservation, and invariants.

The interaction-gated mechanism is viable only if:

- 3/3 runs exit successfully and conserve every symbol exactly;
- zero invariant failures;
- final-window occupancy is in `[0.40, 0.95]` for every run;
- at least two of three runs record an exact-copy trigger;
- at least two of three runs record a successful trigger-gated birth;
- aggregate successful trigger-gated births are at least three;
- pool-blocked births do not exceed successful births.

If the trigger or birth criterion fails, Gate B is a frozen negative result. Do not weaken byte equality, source stability, target change, source revalidation, horizon, or seed requirements.

## Analysis integrity

- Lifecycle events are summed from `details_json.count` for aggregate block events and row-counted for individual trigger/birth events.
- Mechanical liveness follows the existing Stage 3R pilot analyzer.
- Raw run directories remain outside Git; compact run/group reports and checksummed manifests are committed.
