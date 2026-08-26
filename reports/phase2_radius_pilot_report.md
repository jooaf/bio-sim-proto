# Phase 2 matched interaction-radius pilot

## Scope

This is a five-seed, 5,000-tick pilot. It estimates radius effects but cannot pass the 500,000-tick Phase 2 acceptance gate.

## Radius summary

| radius | feasible | median late occupancy | dissolutions | placements | median byte-identity excess | median within-run p | median opcode q=1 beta excess | median within-run p |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 5/5 | 0.767 | 214 | 54 | 0.005018 | 0.0010 | 0.050300 | 0.2630 |
| 2 | 5/5 | 0.767 | 214 | 54 | 0.016375 | 0.0010 | 0.125999 | 0.0610 |
| 4 | 5/5 | 0.767 | 214 | 54 | 0.008015 | 0.0010 | 0.081421 | 0.1590 |
| 8 | 5/5 | 0.767 | 214 | 54 | 0.001459 | 0.0010 | -0.037983 | 0.7160 |

## Focused matched contrast: radius 1 minus radius 8

- Byte-identity excess differences: 0.004629, 0.003658, 0.005211, 0.003195, 0.003558
- Mean byte-identity difference: 0.004050
- Exact one-sided paired sign-flip p-value: 0.031250
- Opcode q=1 beta-excess differences: -0.102021, 0.088283, 0.037589, 0.199409, 0.171701
- Mean opcode beta-excess difference: 0.078992
- Exact one-sided paired sign-flip p-value: 0.125000

The exact test has only 2⁵ = 32 sign assignments, so its smallest possible one-sided p-value is 0.03125. Effect sizes and seed consistency are primary for this pilot.

## Interpretation

- Positive within-run byte-identity excess: 20/20 runs.
- Largest median byte-identity excess occurred at radius 2; the response was not monotonic.
- Radius 1 exceeded radius 8 for byte identity in all 5 matched seeds (exact one-sided p=0.03125).
- The opcode-signature radius-1 minus radius-8 contrast was inconsistent (p=0.125) and is not supported by this pilot.
- Occupancy, dissolution, and placement outcomes were exactly matched across radii within seed: **True**.

These results support a radius effect on local sequence similarity, not a general monotonic claim and not yet a Phase 2 acceptance result.

## Integrity

- Runs analyzed: 20
- Successful exits: 20/20
- Exactly conserved runs: 20/20
- Total invariant failures: 0
- Mechanically feasible runs: 20/20
- Every final exact hash unique: **True**
- Non-radius mechanics matched within seed: **True**

Exact-hash effects remain in the run table but are non-identifiable when all hashes are singletons. No monotonic radius response was assumed, and all four radii are reported.
