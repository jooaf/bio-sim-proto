# Stage 3 vacancy-controlled lineage-patch preregistration

**Frozen before execution:** 2026-09-07

## Preconditions

The mechanics pilot established that vacancy-first scheduled birth at the selected Stage 3R operating point produced zero vacancy-parent blocks, zero pool blocks, identical treatment median birth counts, exact conservation, and feasible dynamics in 6/6 runs. No family statistic was inspected.

The interaction-gated exact-copy pilot failed and remains closed. This experiment uses explicitly scheduled birth.

## Hypothesis

When vacancy opportunity is selected before the parent, radius-1 parent selection produces stronger neutral-family radius-1 neighbor excess than radius-8 parent selection.

## Matrix

- placement protocol: `vacancy_first`;
- parent-selection/offspring-displacement radius: 1 versus 8;
- matched unseen seeds: `202609130`–`202609139`;
- ten seeds per treatment, 20 runs;
- 10,000 ticks;
- scheduled birth rate `2e-5`;
- maximum four births/tick;
- all other parameters identical to the mechanics pilot.

Only placement radius varies.

## Family and statistic

Use the previously frozen neutral family definition `transitive root tape ID mod 16`. Randomly seeded tapes are new roots. Labels never affect dynamics.

At the final tape snapshot, calculate equal-family radius-1 Moore-neighbor frequency and excess over 999 fixed-occupancy family-label permutations. Analysis RNG is `20260913 + run seed`.

Primary paired effect:

```text
radius-1 family-neighbor excess − radius-8 family-neighbor excess
```

Report all ten paired effects, mean, median, 10,000-resample paired bootstrap interval with seed `20260913`, and exact one-sided sign-flip p-value.

## Frozen pass criteria

The causal placement result passes only if:

- mean paired effect > 0;
- bootstrap interval excludes zero positively;
- exact one-sided p ≤ 0.05;
- at least 8/10 paired effects are positive;
- 20/20 runs exit successfully, conserve all symbols, and have zero invariant failures;
- at least 8/10 runs per treatment meet the existing lineage-patch mechanical feasibility definition;
- median births ≥ 100 in each treatment;
- smaller/larger median-birth ratio ≥ 0.90;
- aggregate no-parent blocks ≤ 2% of observed reproduction attempts in each treatment;
- aggregate pool blocks are zero.

Failures remain in all denominators.

## Secondary outcomes

Descriptive only: exact-root neighbor excess, live reproductive-descendant fraction, lineage depth, family Hill q=1, opcode-composition JS excess, occupancy, turnover, and treatment birth-count difference.

## Interpretation

A pass supports a causal effect of local parent selection and offspring displacement when vacancy opportunity and realized birth count are comparable. It does not establish endogenous reproduction, selection, organisms, or the energy-ledger Stage 3 gate.

No parameter, family, null, seed, endpoint, or threshold may be changed after execution begins.
