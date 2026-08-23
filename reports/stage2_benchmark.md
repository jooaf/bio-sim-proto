# Stage 2 500,000-tick benchmark

All cases use radius 1, 80% initial fill, multiplier 16, mutation 1/4,096, an 8,192-step interaction budget, and aggregate logging.

| case | lattice | measured ticks | wall time | ticks/s | executed interactions/s | output | projected 500k wall | projected 500k output | invariant failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| correctness_8x8 | 8×8 | 100 | 1.369 s | 73.030 | 2,337 | 0.16 MB | 1.90 h | 0.82 GB | 0 |
| smoke_32x32 | 32×32 | 1,000 | 126.825 s | 7.885 | 4,037 | 1.30 MB | 17.61 h | 0.65 GB | 0 |
| scale_64x64 | 64×64 | 1,000 | 461.636 s | 2.166 | 4,436 | 3.80 MB | 64.12 h | 1.90 GB | 0 |

## Decision

The largest measured case projects to approximately **64.12 hours** and **1.90 GB** for 500,000 ticks under the same logging cadence.

This is a linear engineering projection, not a completed 500,000-tick scientific run. Replicator-rich long loops, changing occupancy, filesystem behavior, and spatial-analysis cost can make the full campaign slower.
