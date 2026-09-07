# Stage 3 energy-ledger liveness pilot

## Decision

Selected total influx per tick: **1024**.

No lineage, composition, trophic, organization, or fitness endpoint was computed for selection.

| influx | feasible | energy error | interactions | writes | occupancy | tape energy | dissipated | starvation | conserved | invariants | eligible |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---:|:---:|
| 64 | 0/3 | 2.254e-12 | 1.000 | 35194 | 0.779 | 1.353 | 0.996 | 0 | True | 0 | False |
| 256 | 0/3 | 5.498e-12 | 1.000 | 151600 | 0.769 | 4.972 | 0.995 | 0 | True | 0 | False |
| 1024 | 3/3 | 1.721e-11 | 1.000 | 159998 | 0.771 | 4.949 | 0.984 | 0 | True | 0 | True |

This is an energy-accounting and liveness gate, not evidence of trophic structure.
