# Phase 2 liveness larger-lattice confirmation

## Decision

Larger-lattice operating point confirmed: spontaneous dissolution `1e-05` and reseed `1e-05` (3/3 feasible seeds).

This is a 5,000-tick scale confirmation, not the 500,000-tick acceptance result. Spatial statistics are descriptive and did not affect the mechanical decision.

## Treatment summary

| dissolution | reseed | feasible | median late occupancy | min tapes | dissolutions | placements | median neighbor excess | median q=1 beta excess |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1e-05 | 1e-05 | 3/3 | 0.767 | 780 | 131 | 31 | 0.000000 | 0.000000 |

## Spatial-screening limitation

Every final tape hash was unique in every run. Exact-hash neighbor identity and hash-label beta permutation effects are therefore degenerate: relabeling unique hashes cannot change either statistic. The zero excesses are **uninformative**, not evidence that locality has no effect. The radius campaign needs replicated types, a coarser preregistered type definition, or an additional sequence-similarity statistic before these tests can answer the spatial question.

## Integrity

- Runs analyzed: 3
- Successful exits: 3/3
- Exactly conserved runs: 3/3
- Total invariant failures: 0
- Mechanically feasible runs: 3/3
- Every final hash unique in every run: **True**

Mechanical liveness is confirmed at 32×32, but the radius sweep remains blocked until its non-degenerate spatial metric is frozen.
