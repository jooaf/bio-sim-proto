# Stage 3 regulated lineage switch-off persistence

## Decision

Integrated regulated persistence supported: **True**.

## Co-primary endpoints

| endpoint | mean | median | bootstrap interval | raw p | Holm p |
|---|---:|---:|---:|---:|---:|
| stopped final excess | 0.043097 | 0.041138 | [0.040045, 0.046359] | 0.000977 | 0.001953 |
| continued minus stopped | 0.045861 | 0.046852 | [0.040967, 0.050633] | 0.000977 | 0.001953 |

## Integrated criteria

- Stopped final excess positive: 10/10
- Stopped final within-run p <= 0.05: 10/10
- Median stopped retention: 0.881139
- Continued final excess positive: 10/10
- Continued final within-run p <= 0.05: 10/10
- Mechanically feasible stopped/continued: 8/10, 10/10
- Successful and conserved runs: 20/20
- Invariant failures: 0

## Arm summaries

| stop tick | feasible | births | occupancy | switch excess | final excess | retention |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 10/10 | 353 | 0.839 | 0.050333 | 0.088958 | 1.759 |
| 10000 | 8/10 | 174 | 0.717 | 0.050333 | 0.043097 | 0.881 |

This result concerns a neutral lineage label pattern under exogenous mortality and scheduled cloning. It is not endogenous reproduction or organismal self-maintenance.
