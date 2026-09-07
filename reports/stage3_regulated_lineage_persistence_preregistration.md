# Stage 3 regulated lineage switch-off persistence preregistration

**Frozen before execution:** 2026-09-07

## Scope and predecessor

S3-E007 selected spontaneous dissolution `2e-5` without inspecting spatial
lineage outcomes, then confirmed a non-clogging continued-birth positive control
on held-out seeds. This new experiment tests whether an already formed neutral
lineage patch persists after scheduled birth stops under that stronger turnover.
It does not reopen the original failed switch-off gate and cannot establish
adaptation, endogenous reproduction, or organismal self-maintenance.

## Frozen matrix

- spontaneous dissolution: `2e-5` in both arms;
- vacancy-first scheduled birth rate: `2e-5` in both arms;
- arm 1: birth continues through 20,000 ticks (`stop_tick = 0`);
- arm 2: birth stops before tick 10,000 (`stop_tick = 10000`);
- ten new matched seeds: `202609193`–`202609202`;
- 20 runs total, 32×32 lattice, 20,000 ticks;
- all other settings equal to the S3-E007 confirmation.

Only `reproduction.stop_tick` varies. A stopped mechanism consumes no
reproduction RNG after the switch, so post-switch trajectories are not expected
to remain pairwise RNG-aligned.

## Frozen lineage measurements

At tape snapshots 10,000, 12,000, 15,000, and 19,900, compute radius-1 equal
modulo-16 transitive-root family-neighbor excess against 499 fixed-occupancy
label permutations. Use analysis RNG `20260919 + run seed + checkpoint`.

Compute exact-root excess with 199 permutations as descriptive evidence only,
using an additional RNG offset of 1,000,000. Family definitions, checkpoints,
and null construction are unchanged from the original persistence study.

## Co-primary endpoints

1. **Stopped-arm persistence:** final family-neighbor excess at tick 19,900 is
   positive after birth has been absent for 9,900 ticks.
2. **Continued-birth contrast:** matched continued-minus-stopped final family
   excess is positive, showing that continued causal input remains detectably
   stronger than the residual patch.

For each endpoint report the mean, median, 10,000-resample paired bootstrap
interval using seed `20260919`, and an exact one-sided sign-flip test. Apply Holm
correction across the two p-values at family-wise alpha 0.05. Both adjusted tests
must pass, and both bootstrap intervals must exclude zero positively.

## Integrated pass criteria

The regulated switch-off result passes only if:

- both co-primary endpoint means are positive;
- both positive bootstrap intervals exclude zero;
- both one-sided sign-flip tests survive Holm correction at 0.05;
- at least 8/10 stopped-arm final excesses are positive;
- at least 8/10 stopped-arm final within-run permutation tests have `p <= 0.05`;
- median stopped-arm retention, final excess divided by tick-10,000 excess, is
  at least 0.25; nonpositive switch values have undefined retention and fail;
- at least 8/10 continued-arm final excesses are positive and individually
  significant at `p <= 0.05`;
- at least 8/10 runs per arm satisfy the already frozen S3-E007 regulation
  feasibility criteria: late and final occupancy 0.50–0.90, absolute
  10k-to-19.9k occupancy change at most 0.05, at least 100 births and 100
  dissolutions, lineage depth at least 3, nonzero placement/interactions/writes/
  pool turnover, and pool blocks no greater than births;
- all 20 runs exit successfully and conserve symbols exactly; and
- total invariant failures are zero.

The stopped arm's `at least 100 births` criterion counts the pre-switch formation
period. Failures and undefined retention values remain in all denominators.

## Interpretation and integrity

A pass supports turnover-resistant persistence of a neutral spatial lineage
pattern while showing that continued birth sustains a stronger patch. A failure
means the earlier persistence result was specific to slower turnover or that the
new positive-control contrast was not identified. Do not change rates, seeds,
checkpoints, family definitions, permutations, thresholds, multiplicity method,
or horizon after execution begins.
