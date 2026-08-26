# Phase 2 liveness operating-point pilot

## Decision

Selected for larger-lattice confirmation: spontaneous dissolution `1e-05` and reseed `1e-05` (3/3 feasible seeds).

This is a short parameter-selection pilot, not the 500,000-tick acceptance result. Spatial statistics are descriptive and were not used for treatment selection.

## Treatment summary

| dissolution | reseed | feasible | median late occupancy | min tapes | dissolutions | placements | median neighbor excess | median q=1 beta excess |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1e-05 | 1e-05 | 3/3 | 0.797 | 49 | 6 | 4 | 0.000000 | 0.000000 |
| 1e-05 | 0.0001 | 3/3 | 0.844 | 50 | 12 | 22 | 0.000000 | 0.000000 |
| 0.0001 | 0.001 | 3/3 | 0.901 | 50 | 76 | 94 | 0.000000 | 0.000000 |
| 0.0001 | 0.0001 | 3/3 | 0.606 | 35 | 75 | 33 | 0.000000 | 0.000000 |
| 0.0001 | 1e-05 | 3/3 | 0.554 | 31 | 50 | 6 | 0.000000 | 0.000000 |
| 1e-05 | 0.001 | 2/3 | 0.983 | 50 | 16 | 51 | 0.000000 | 0.000000 |
| 1e-06 | 0.0001 | 1/3 | 0.891 | 51 | 1 | 20 | 0.000000 | -0.000000 |
| 1e-06 | 1e-05 | 0/3 | 0.812 | 51 | 0 | 4 | 0.000000 | 0.000000 |
| 1e-06 | 0.001 | 0/3 | 1.000 | 51 | 0 | 39 | 0.000000 | -0.000000 |

## Spatial-screening limitation

Every final tape hash was unique in every run. Exact-hash neighbor identity and hash-label beta permutation effects are therefore degenerate: relabeling unique hashes cannot change either statistic. The zero excesses are **uninformative**, not evidence that locality has no effect. The radius campaign needs replicated types, a coarser preregistered type definition, or an additional sequence-similarity statistic before these tests can answer the spatial question.

## Integrity

- Runs analyzed: 27
- Successful exits: 27/27
- Exactly conserved runs: 27/27
- Total invariant failures: 0
- Mechanically feasible runs: 18/27
- Every final hash unique in every run: **True**

The selected treatment, if any, must pass a larger-lattice confirmation before the matched radius sweep.
