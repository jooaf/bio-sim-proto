# Long-horizon opcode-composition locality preregistration

**Frozen before execution:** 2026-09-05

## Motivation and status

A preregistered 5,000-tick campaign found greater radius-1 than radius-8 neighbor similarity in eleven-part BFF opcode composition on all ten matched seeds (mean excess difference `+0.005173`, exact `p = 0.000977`). That result does not establish temporal persistence.

This campaign extends the horizon tenfold with new seeds and a pooled final-window test. It is a new follow-up and cannot alter the historical categorical block-beta NO-GO.

## Frozen treatments

- horizon: **50,000 ticks**;
- interaction radii: **1 and 8**;
- unseen matched seeds: **202609070–202609079**;
- ten seeds per radius, **20 runs total**;
- baseline mutation: 1/4,096;
- 32×32 torus, initial fill 0.8;
- 512 attempted interactions per tick;
- dissolution and reseed: 10⁻⁵ each;
- tape length 64 and BFF budget 8,192;
- full-byte snapshots every 500 ticks;
- energy, signals, tasks, maximum-age death, and starvation death disabled.

Only interaction radius varies within a matched seed. The projected wall time is approximately 2.6 hours with ten workers, but only measured runtime will be reported as evidence.

## Primary metric

Use the already frozen eleven-part tape composition:

- proportions of each of ten BFF opcode bytes;
- aggregate proportion of all non-opcode bytes.

For occupied radius-1 Moore-neighbor edges, compute base-2 Jensen–Shannon similarity (`1 − divergence`).

For each run, use the ten intended complete snapshots in the final 10%: ticks 45,000 through 49,500. Give snapshots equal weight. For each of 999 null replicates, independently permute complete composition vectors over fixed occupied cells within each snapshot and average the ten null statistics.

Report pooled observed similarity, null mean, excess, and one-sided permutation p-value. Use analysis seed `20260906 + run seed`.

## Primary matched hypothesis

For each seed:

```text
paired effect = radius-1 pooled final-window JS excess − radius-8 pooled final-window JS excess
```

Prediction: positive.

Report all differences, mean, median, a 95% percentile paired-bootstrap interval with 10,000 resamples and seed 20260906, and the exact one-sided sign-flip p-value.

Temporal persistence is supported only if all hold:

1. mean paired effect > 0;
2. 95% bootstrap interval excludes zero on the positive side;
3. exact one-sided p ≤ 0.05;
4. at least 8/10 paired effects are positive;
5. at least 8/10 runs at each radius are mechanically feasible.

There is one primary hypothesis and no multiple-comparison adjustment.

## Frozen temporal diagnostics

These are descriptive and cannot alter the primary decision:

- per-snapshot JS excess using 99 permutations;
- early-window versus final-window mean JS excess;
- number of final-window checkpoints whose mean radius-1-minus-radius-8 contrast is positive;
- minimum and maximum paired treatment effect;
- occupancy and pool-turnover trajectories.

The diagnostics test whether a pooled mean hides transient reversals, but no diagnostic p-value becomes a second primary hypothesis.

## Mechanical feasibility

A run is feasible only if it:

- exits successfully;
- conserves each symbol exactly;
- records zero invariant failures;
- has final-window mean occupancy ≥ 0.25;
- has nonzero final-window interactions and successful writes;
- records dissolution, successful random placement, and pool turnover.

## Integrity rules

- Every failure or extinction remains in the denominator.
- Invariant failure stops and fails the affected run.
- Do not replace seeds, shorten/extend the horizon, or change the final window after outcomes are inspected.
- Do not alter the composition vector, measurement-neighbor radius, permutation null, or test direction.
- Do not tune mutation or lifecycle rates.
- A pass supports persistence to 50,000 ticks, not 500,000 ticks, phenotype, lineage, or organism-level patches.
