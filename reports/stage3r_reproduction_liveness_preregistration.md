# Stage 3R reproduction liveness-pilot preregistration

**Frozen before execution:** 2026-09-06

## Purpose

Select one mechanically viable neutral copy-birth rate without inspecting lineage spatial clustering. This pilot cannot support a patch claim.

## Matrix

- reproduction rates: 5×10⁻⁶, 10⁻⁵, 2×10⁻⁵, 5×10⁻⁵ per live tape per tick;
- offspring placement radius: 1;
- seeds: 202609090–202609092;
- 5,000 ticks;
- 12 total 32×32 runs;
- maximum four successful births/tick;
- baseline Stage 2 mutation, interaction, dissolution, reseed, pool, and logging;
- energy, tasks, and signals disabled.

Only reproduction rate varies.

## Outcomes allowed for selection

- successful copy births;
- attempts and pool/no-space blocks;
- final-window occupancy;
- dissolution, random placement, writes, interactions, and pool turnover;
- maximum lineage depth and number of reproductive children;
- exact conservation and invariant failures.

Do not calculate same-family neighbor statistics until one rate is frozen.

## Per-run feasibility

A run is feasible if it:

- exits successfully;
- conserves every symbol exactly;
- records zero invariant failures;
- has final-window mean occupancy from 0.40 through 0.90;
- records at least 25 successful reproductive births;
- has nonzero dissolution, random placement, interactions, writes, and pool turnover;
- has pool-blocked births no greater than successful births;
- reaches lineage depth at least 2.

## Selection rule

A rate is eligible if at least 2/3 seeds are feasible. Rank eligible rates by:

1. most feasible seeds;
2. median absolute distance between successful births and 75;
3. median occupancy distance from 0.75;
4. lower rate.

Freeze the top rate before any family-patch analysis or placement-radius campaign.

## Integrity

Failures remain in the denominator. Do not add rates, seeds, or change thresholds after inspection. Scheduled copy birth is a mechanism probe, not endogenous self-replication, and Stage 3R is not the roadmap's energy-ledger Stage 3 gate.
