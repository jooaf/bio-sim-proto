# Stage 3 energy-ledger liveness preregistration

**Frozen before execution:** 2026-09-07

## Purpose

Validate explicit energy accounting and select at most one bounded operating point using mechanics only. Reproduction is disabled. No lineage, composition, trophic, organization, or fitness endpoint may be inspected for selection.

## Frozen energy semantics

- Energy starts at zero.
- `influx_rate` is total uniform field influx per tick.
- Four-neighbor toroidal diffusion is synchronous and conservative.
- Field decay is irreversible dissipation.
- Occupied tapes absorb locally up to the absorption rate and capacity.
- The first tape in an ordered interaction pays instruction and successful-write costs through the substrate's hard execution budget.
- Background mutation is exogenous noise and free.
- Held energy is dissipated at death.
- Starvation dissolution activates after 100 consecutive zero-energy ticks.

Required balance:

```text
field + live tapes + cumulative dissipation
    = cumulative influx + initial energy
```

## Matrix

- total influx per tick: `64`, `256`, `1024`;
- unseen seeds: `202609140`–`202609142`;
- three seeds per influx, nine runs;
- 5,000 ticks;
- absorption `0.5` energy/tape/tick;
- tape capacity `10`;
- instruction cost `0.01`;
- successful-write cost `0.1`;
- diffusion `0.1`;
- field decay `0.01`;
- minimum energy to initiate interaction `0.01`;
- BFF, 32×32 lattice, 80% initial fill, radius-1 interactions;
- Stage 2 mutation, spontaneous dissolution, reseeding, pool, and logging settings retained;
- reproduction, signals, and tasks disabled.

Only influx varies.

## Per-run feasibility

A run is feasible only if:

- it exits successfully;
- every byte count is exactly conserved;
- it records zero invariant failures;
- maximum relative energy-balance error over logged ticks is ≤ `1e-9`;
- late occupied fraction is in `[0.40, 0.90]`;
- late active-interaction fraction is at least `0.50`;
- late successful writes and pool changes are nonzero;
- final mean tape energy is in `[0.01, 9.0]`;
- final cumulative dissipation is from `0.05` through `0.99` of cumulative influx;
- starvation deaths do not exceed 50% of the initial population.

## Selection rule

An influx is eligible only if 3/3 runs are feasible. Select the **lowest eligible influx**. If none is eligible, no operating point is selected and energy-coupled reproduction does not proceed. Do not add influx values, change costs, extend runs, or add seeds after inspection.

## Integrity

All failed/extinct runs remain in denominators. Raw directories remain outside Git; compact reports and checksummed manifests are committed. This pilot validates an accounting mechanism, not trophic ecology.
