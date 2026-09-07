# Stage 3 energy-funded birth preregistration

**Frozen before execution:** 2026-09-07

## Preconditions and claim boundary

The energy liveness pilot selected total uniform influx 1024 by a frozen mechanics rule. Interaction-gated exact-copy birth failed and remains closed. This experiment therefore uses scheduled birth and tests only whether parent-held energy causally constrains it.

## Matrix

- birth energy cost: `0` versus `5`;
- offspring energy transfer: `0`;
- unseen matched seeds: `202609150`–`202609159`;
- ten seeds per treatment, 20 runs;
- 5,000 ticks;
- selected energy settings: influx 1024, absorption 0.5, capacity 10, instruction cost 0.01, write cost 0.1, diffusion 0.1, decay 0.01, minimum interaction energy 0.01;
- scheduled vacancy-first birth, rate `2e-5`, radius 1, maximum four births/tick;
- all other Stage 3 settings fixed.

Only dissipative birth cost varies. A failed birth transaction changes neither symbols nor energy.

## Primary outcome

Paired successful-birth effect:

```text
cost-0 births − cost-5 births
```

Report all ten effects, mean, median, 10,000-resample paired bootstrap interval using seed `20260915`, and exact one-sided sign-flip p-value.

## Pass criteria

Energy constraint is supported only if:

- mean paired effect > 0;
- bootstrap interval excludes zero positively;
- exact one-sided p ≤ 0.05;
- at least 8/10 paired effects are positive;
- energy-blocked attempts occur in at least 8/10 cost-5 runs;
- median cost-0 births ≥ 50, establishing a viable positive control;
- median cost-5 births ≥ 10 but less than 90% of the cost-0 median;
- 20/20 runs exit successfully and conserve every symbol exactly;
- zero invariant failures;
- maximum relative energy error ≤ `1e-9` in every run;
- late occupancy is `[0.40, 0.95]` and late interactions/writes/pool turnover are nonzero in every run.

## Secondary outcomes

Descriptive only: blocked-energy count, final tape and field energy, dissipated fraction, occupancy, dissolution, random placement, and lineage depth. No family, composition, trophic, or organization metric is tested.

## Integrity

All failures remain in denominators. Cost, seeds, horizon, thresholds, and energy settings cannot be changed after execution begins. A pass establishes energy-constrained scheduled reproduction, not endogenous reproduction, ecological fitness, or trophic structure.
