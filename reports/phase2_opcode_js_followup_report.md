# Phase 2 continuous opcode-composition locality follow-up

## Decision

Preregistered continuous locality result supported: **True**.

- Mean radius-1-minus-radius-8 JS-excess effect: 0.005173
- Median paired effect: 0.005282
- 95% paired bootstrap interval: [0.003828, 0.006607]
- Exact one-sided sign-flip p: 0.000977
- Positive matched effects: 10/10
- Mechanically feasible radius-1 runs: 10/10
- Mechanically feasible radius-8 runs: 10/10

This follow-up cannot retroactively pass the frozen Phase 2 opcode-beta gate.

## Radius summary

| radius | feasible | mean JS | null mean | mean excess | median within-run p | positive excess | byte excess | ordered beta-8 excess | unique fraction | singleton fraction |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10/10 | 0.942157 | 0.936008 | 0.006149 | 0.001 | 10/10 | 0.005465 | 0.038063 | 0.740 | 0.658 |
| 8 | 10/10 | 0.925482 | 0.924506 | 0.000976 | 0.160 | 10/10 | 0.001526 | 0.027504 | 0.920 | 0.884 |

## Matched effects

- 0.003454, 0.003288, 0.006548, 0.008855, 0.005653, 0.008528, 0.001557, 0.005101, 0.005463, 0.003288

## Integrity

- Runs: 20
- Successful exits: 20/20
- Exactly conserved: 20/20
- Invariant failures: 0
- Mechanically feasible: 20/20

JS similarity measures graded instruction composition, including aggregate non-instruction density. It is not evidence of phenotype, lineage, or organism identity.
