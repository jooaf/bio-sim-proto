# Benchmark: pyopt_profile_after

| label | founders | ticks | ticks/s | mean pop | peak pop | audit |
|---|---:|---:|---:|---:|---:|---:|
| f1200 | 1200 | 100 | 5.7 | 1116 | 1181 | 0 |
| cprofile_1200 | 1200 | 100 | 5.8 | 1116 | 1181 | 0 |

## Phase breakdown — f1200 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 14.47 | 83.2% |
| deposits_produce | 3.14 | 18.0% |
| upkeep | 0.66 | 3.8% |
| decompose | 0.61 | 3.5% |
| digest | 0.16 | 0.9% |
| world_diffuse | 0.12 | 0.7% |

## Phase breakdown — cprofile_1200 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 14.44 | 83.2% |
| deposits_produce | 3.16 | 18.2% |
| upkeep | 0.66 | 3.8% |
| decompose | 0.61 | 3.5% |
| digest | 0.17 | 0.9% |
| world_diffuse | 0.12 | 0.7% |
