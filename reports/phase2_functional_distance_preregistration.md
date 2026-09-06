# Functional-prediction and spatial distance-decay preregistration

**Frozen before execution:** 2026-09-06

## Scope

This campaign tests two distinct implications of the replicated opcode-composition locality effect. It uses unseen seeds and unchanged Stage 2 parameters. Neither endpoint can alter the historical categorical block-beta NO-GO.

## Frozen simulation matrix

- radii: **1 and 8**;
- matched unseen seeds: **202609080–202609089**;
- ten seeds per radius, **20 runs**;
- horizon: 5,000 ticks;
- mutation: 1/4,096;
- 32×32 torus, initial fill 0.8;
- 512 attempted interactions/tick;
- dissolution and reseed: 10⁻⁵ each;
- full-byte snapshots every 500 ticks;
- energy, signals, tasks, age death, and starvation death disabled.

Only interaction radius varies within seed.

## H1: opcode composition predicts execution behavior

### Sampling

At the last complete final-window snapshot (intended tick 4,500), select 128 occupied tapes without replacement using analysis seed `20260907 + run seed`. Selection is independent of tape content.

### Standardized offline assay

Execute each sampled focal tape as the first 64 bytes of a joint BFF tape against four fixed 64-byte partners:

1. all zero bytes;
2. all byte value 255;
3. a repeating cycle of the ten BFF opcodes;
4. a fixed uniform-byte probe generated once with seed 20260907.

Use the configured 8,192-step budget, no mutation, no energy cost, and no pool limit. This is an unconstrained standardized behavior assay, not a replay of in-soup fitness.

For each probe record normalized steps, successful writes, total/focal/partner changed-byte fractions, and halt-reason one-hot indicators. Concatenate all probe outcomes. Define behavioral similarity as one minus mean absolute feature difference (Gower similarity).

Compute eleven-part opcode-composition Jensen–Shannon similarity for the same tapes. Test Spearman association between upper triangles of the composition- and behavior-similarity matrices using a 999-permutation Mantel label test.

### Primary H1 statistic

Average the two run-level Mantel correlations within each matched seed, then test whether the ten seed averages have positive mean using an exact one-sided sign-flip test. Report a 10,000-resample bootstrap interval using seed 20260907.

Prediction: positive. H1 additionally requires at least 8/10 seed-average correlations > 0 and identifiable finite correlations in all 20 runs.

## H2: opcode similarity decays with spatial distance

At the same complete snapshot, compute Jensen–Shannon similarity for every occupied tape pair. Bin pairs by toroidal Chebyshev distance 1 through 16 and report the complete mean-similarity curve.

Fit an equal-distance-weighted linear slope through the 16 bin means and define:

```text
decay strength = −slope
```

For each run, permute complete composition vectors over fixed occupied cells 499 times and report decay-strength excess above the permutation-null mean.

### Primary H2 statistic

For each seed:

```text
radius-1 decay-strength excess − radius-8 decay-strength excess
```

Prediction: positive. Report the mean, median, 10,000-resample paired-bootstrap interval using seed 20260908, exact one-sided sign-flip p-value, and sign count. H2 requires at least 8/10 positive pairs and a positive bootstrap interval.

## Multiplicity

H1 and H2 form one two-test primary family. Apply Holm step-down familywise alpha 0.05. Both must pass Holm and their additional sign/interval criteria for the joint result to be supported.

## Secondary outcomes

Descriptive only:

- Mantel correlation by radius and within-run permutation p-values;
- observed and null distance-decay curves;
- radius effect on neighbor JS excess and byte identity;
- occupancy and lifecycle integrity;
- correlations among functional, neighbor, and distance-decay effects.

Secondary results cannot replace failed primary outcomes.

## Mechanical feasibility

A run must exit successfully, conserve every symbol exactly, record zero invariant failures, maintain final-window mean occupancy ≥ 0.25, retain active interactions and successful writes, and record dissolution, placement, and pool turnover. At least 8/10 runs per radius must be feasible.

## Integrity rules

- Preserve every failed/extinct run.
- Do not change sample size, probes, features, distance metric, bins, nulls, or directions after inspection.
- Do not substitute natural interaction logs for the frozen standardized assay.
- Do not try edit distance on these seeds if H1 fails.
- Do not tune simulator parameters.
- A pass supports predictive association and spatial scale structure, not heredity, organism identity, or adaptive fitness.
