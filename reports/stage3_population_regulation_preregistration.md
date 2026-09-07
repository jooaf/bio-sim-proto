# Stage 3 density-independent population-regulation preregistration

**Frozen before execution:** 2026-09-07

## Purpose and mechanism

The completed lineage switch-off campaign failed its integrated gate because the
continued scheduled-birth control clogged: median late occupancy was 0.971 and
only 1/10 runs met the frozen 0.95 ceiling. This experiment does not reduce the
selected birth rate or reopen that campaign. It tests whether the simulator's
existing density-independent spontaneous dissolution can provide neutral
turnover that maintains vacancies while preserving a scheduled-birth lineage
positive control.

Spontaneous dissolution is motivated as background mortality independent of
tape content, lineage, local density, or measured endpoints. Dissolved tape
symbols return to the conserved pool. The mechanism already exists and requires
no new simulator semantics.

## Phase A — mechanics-only liveness selection

Run four spontaneous dissolution rates: `2e-5`, `3e-5`, `5e-5`, and `1e-4` per
live tape per tick. The previous `1e-5` rate is excluded because its 20,000-tick
continued-birth arm clogged. Use seeds `202609180`–`202609182`, 20,000 ticks,
and the frozen vacancy-first scheduled-birth rate `2e-5`. All other settings
match the failed continued-birth control. This is 12 runs.

Selection may use only:

- successful births and birth blocks;
- dissolution and random-placement counts;
- occupancy at ticks 10,000 and 19,900 and mean occupancy over ticks
  15,000–19,900;
- interactions, successful writes, and pool turnover;
- maximum lineage depth, exact conservation, and invariant failures.

Do not calculate family-neighbor or exact-root spatial outcomes in Phase A.

A pilot run is feasible only if it:

- exits successfully, conserves every symbol, and has zero invariant failures;
- has late mean occupancy from 0.50 through 0.90 and occupancy at tick 19,900
  from 0.50 through 0.90;
- changes occupancy by at most 0.05 in absolute fraction from tick 10,000 to
  tick 19,900;
- records at least 100 successful scheduled births and at least 100
  dissolutions;
- has nonzero random placement, active interactions, successful writes, and
  late pool turnover;
- has pool-blocked births no greater than successful births; and
- reaches lineage depth at least 3.

A rate is eligible if at least 2/3 runs are feasible. Rank eligible rates by:

1. most feasible runs;
2. smallest median absolute occupancy change from tick 10,000 to 19,900;
3. smallest median late-occupancy distance from 0.75;
4. smallest median absolute difference between successful births and
   dissolutions;
5. lower dissolution rate.

Freeze the top rate. If no rate is eligible, stop and reject this regulation
mechanism without inspecting lineage spatial outcomes.

## Phase B — held-out lineage-control confirmation

Only after a Phase A GO, run the selected dissolution rate for 20,000 ticks on
held-out seeds `202609183`–`202609192` with scheduled birth continuing
throughout. No parameter changes are permitted.

At tick 19,900, compute radius-1 modulo-16 transitive-root family-neighbor excess
against 499 fixed-occupancy label permutations using analysis RNG
`20260918 + run seed + 19900`. Exact-root excess with 199 permutations is
secondary and descriptive.

The regulated lineage positive control passes only if:

- at least 8/10 runs satisfy the Phase A per-run feasibility criteria;
- mean final family-neighbor excess is positive;
- its 10,000-resample bootstrap interval using seed `20260918` excludes zero
  positively;
- exact one-sided sign-flip `p <= 0.05`;
- at least 8/10 final family excesses are positive;
- at least 8/10 within-run permutation tests have `p <= 0.05`;
- all 10 runs exit successfully and conserve every symbol;
- total invariant failures are zero.

## Interpretation and integrity

A pass supports only a non-clogging neutral scheduled-birth positive control and
justifies a separately preregistered lineage-persistence experiment. It does not
rescue the failed switch-off gate, demonstrate endogenous reproduction, or
establish self-maintenance. Failures remain in every denominator. Do not add
rates or seeds, alter windows or thresholds, inspect lineage spatial outcomes
before rate selection, or tune the selected rate after Phase A.
