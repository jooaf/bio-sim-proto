# Phase 2 continuous opcode-composition follow-up preregistration

**Frozen before execution:** 2026-09-05

## Status

The 500,000-tick Phase 2 acceptance decision remains NO-GO. A subsequent 40-run mutation × radius follow-up also failed its two primary ordered-category hypotheses. It nevertheless found strong descriptive radius effects on positional byte similarity and opcode-sequence recurrence.

This new campaign tests one continuous endpoint on unseen seeds without changing baseline mutation or any lifecycle parameter. It cannot retroactively replace the failed categorical acceptance criterion.

## Primary metric

Represent each 64-byte tape by an eleven-component probability vector:

1. one component for the proportion of each of the ten BFF instruction bytes;
2. one component for the aggregate proportion of all non-instruction bytes.

The components sum to one. This avoids undefined empty-opcode vectors and retains both instruction composition and instruction density.

For each undirected occupied radius-1 Moore-neighbor edge, calculate base-2 Jensen–Shannon divergence between the two vectors and convert it to similarity:

```text
JS similarity = 1 − JS divergence
```

The value lies from zero to one. It is a graded syntax-composition similarity, not a phenotype, lineage, or organism identity.

For each run's last complete full-byte snapshot in the final 10% (intended tick 4,500):

1. average JS similarity over occupied radius-1 edges;
2. independently permute complete composition vectors over fixed occupied cells 999 times;
3. report observed similarity, null mean, observed-minus-null excess, and one-sided permutation p-value.

Use analysis seed `20260905 + run seed`.

## Frozen matched campaign

- interaction radii: **1 and 8**;
- unseen matched seeds: **202609060–202609069**;
- ten seeds per radius, **20 runs total**;
- baseline mutation: **1/4,096**;
- horizon: **5,000 ticks**;
- 32×32 torus and 80% initial fill;
- 512 attempted interactions per tick;
- spontaneous dissolution and reseed: 10⁻⁵ each;
- tape length 64 and BFF execution budget 8,192;
- full-byte snapshots every 500 ticks;
- energy, tasks, signals, maximum-age death, and starvation death disabled.

Only interaction radius varies within a matched seed.

## Primary hypothesis and decision

For each seed define:

```text
paired effect = radius-1 JS-similarity excess − radius-8 JS-similarity excess
```

Prediction: positive.

Report all ten differences, their mean and median, a 95% percentile paired-bootstrap interval using 10,000 resamples and seed 20260905, and an exact one-sided paired sign-flip p-value.

The continuous locality result is supported only if all hold:

1. mean paired effect > 0;
2. the 95% bootstrap interval excludes zero on the positive side;
3. exact one-sided p ≤ 0.05;
4. at least 8/10 paired effects are positive;
5. at least 8/10 radius-1 and 8/10 radius-8 runs are mechanically feasible.

There is one primary hypothesis, so no multiple-comparison adjustment is needed.

## Frozen secondary outcomes

Analyze descriptively and do not use to alter the primary decision:

- within-run JS permutation p-values and sign consistency;
- positional byte-identity excess;
- ordered-full opcode q=1 beta at 8×8 blocks;
- ordered-opcode unique and singleton-tape fractions;
- occupancy, writes, dissolution, placement, conservation, and invariant counts.

Secondary permutation diagnostics may use 199 replicates because they are not gate outcomes.

## Mechanical feasibility

A run is feasible only if it:

- exits successfully;
- conserves every symbol exactly;
- records zero invariant failures;
- maintains final-window mean occupancy ≥ 0.25;
- has nonzero final-window interactions and successful writes;
- records dissolution, successful random placement, and pool turnover.

## Integrity and stopping rules

- Failed or extinct runs remain in the denominator.
- An invariant failure stops and fails the affected run.
- Do not replace seeds or extend the campaign after outcomes are inspected.
- Do not change the eleven components, neighbor radius, null, or direction.
- Do not tune mutation, dissolution, reseed, or interaction count.
- A successful result supports graded opcode-composition locality over 5,000 ticks; it does not pass Phase 2 or establish organisms.
- A failed result is reported without trying edit distance on the same seeds as a replacement primary endpoint.
