# Stage 4 exact-tag signal dispatch mechanics

## Decision

Exact local signal dispatch supported: **True**.

| arm | runs | interactions | reads | dispatches | uptake executions | mean final energy | max error |
|---|---:|---:|---:|---:|---:|---:|---:|
| disabled | 5 | 4000 | 0 | 0 | 0 | 0.000000 | 1.005e-15 |
| matched | 5 | 4000 | 4000 | 4000 | 4000 | 9.990000 | 2.297e-15 |
| mismatched | 5 | 4000 | 4000 | 0 | 0 | 0.000000 | 1.005e-15 |

This is an exact-tag dispatch mechanics result only. Signal writing, coordination, fitness, adaptation, and organization were not tested.
