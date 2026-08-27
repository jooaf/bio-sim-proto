# Benchmark: smoke

| label | founders | ticks | ticks/s | mean pop | peak pop | audit |
|---|---:|---:|---:|---:|---:|---:|
| f300 | 300 | 100 | 14.4 | 305 | 332 | 0 |
| cprofile_300 | 300 | 100 | 14.4 | 305 | 332 | 0 |

## Phase breakdown — f300 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 3.49 | 50.2% |
| deposits_produce | 2.69 | 38.6% |
| decompose | 0.64 | 9.2% |
| upkeep | 0.58 | 8.3% |
| world_diffuse | 0.10 | 1.5% |
| digest | 0.06 | 0.9% |

## Phase breakdown — cprofile_300 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 3.47 | 50.0% |
| deposits_produce | 2.68 | 38.7% |
| decompose | 0.65 | 9.4% |
| upkeep | 0.58 | 8.3% |
| world_diffuse | 0.10 | 1.5% |
| digest | 0.06 | 0.9% |
