# Long-horizon opcode-composition locality result

## Decision

Preregistered 50,000-tick temporal-persistence result supported: **True**.

- Mean paired pooled-JS effect: 0.005324
- Median paired effect: 0.004387
- 95% paired bootstrap interval: [0.003924, 0.007259]
- Exact one-sided sign-flip p: 0.000977
- Positive seed effects: 10/10
- Positive mean final-window checkpoint contrasts: 10/10
- Mechanically feasible: radius 1 = 10/10; radius 8 = 10/10

This result cannot retroactively alter the categorical Phase 2 acceptance NO-GO.

## Radius summary

| radius | feasible | pooled JS | pooled null | pooled excess | median p | early excess | final excess | positive final snapshots/run | occupancy |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10/10 | 0.942289 | 0.936155 | 0.006135 | 0.001 | 0.003446 | 0.006151 | 10.0/10 | 0.608 |
| 8 | 10/10 | 0.924846 | 0.924036 | 0.000810 | 0.013 | 0.000647 | 0.000792 | 7.5/10 | 0.612 |

## Matched pooled effects

- 0.004148, 0.012810, 0.007180, 0.002797, 0.004769, 0.004626, 0.004040, 0.003869, 0.003075, 0.005926

## Integrity

- Runs: 20
- Successful exits: 20/20
- Exactly conserved: 20/20
- Invariant failures: 0
- Mechanically feasible: 20/20

JS similarity is a graded syntax-composition statistic. It does not establish phenotype, heredity, or organism identity.
