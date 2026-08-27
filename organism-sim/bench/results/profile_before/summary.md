# Benchmark: profile_before

| label | founders | ticks | ticks/s | mean pop | peak pop | audit |
|---|---:|---:|---:|---:|---:|---:|
| f1200 | 1200 | 100 | 4.8 | 1116 | 1181 | 0 |
| cprofile_1200 | 1200 | 100 | 4.8 | 1116 | 1181 | 0 |

## Phase breakdown — f1200 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 16.63 | 79.4% |
| deposits_produce | 2.98 | 14.2% |
| upkeep | 2.30 | 11.0% |
| decompose | 0.82 | 3.9% |
| digest | 0.17 | 0.8% |
| world_diffuse | 0.12 | 0.6% |

## Phase breakdown — cprofile_1200 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 16.67 | 79.4% |
| deposits_produce | 3.00 | 14.3% |
| upkeep | 2.32 | 11.1% |
| decompose | 0.83 | 3.9% |
| digest | 0.17 | 0.8% |
| world_diffuse | 0.12 | 0.6% |
