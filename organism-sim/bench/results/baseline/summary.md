# Benchmark: baseline

| label | founders | ticks | ticks/s | mean pop | peak pop | audit |
|---|---:|---:|---:|---:|---:|---:|
| f300 | 300 | 400 | 35.6 | 380 | 420 | 0 |
| f600 | 600 | 400 | 24.5 | 624 | 683 | 0 |
| f1200 | 1200 | 400 | 5.6 | 1100 | 1128 | 0 |
| cprofile_1200 | 1200 | 200 | 5.1 | 1114 | 1161 | 0 |

## Phase breakdown — f300 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| deposits_produce | 4.85 | 43.2% |
| decisions | 4.49 | 40.0% |
| decompose | 1.43 | 12.8% |
| upkeep | 1.15 | 10.3% |
| world_diffuse | 0.35 | 3.1% |
| digest | 0.09 | 0.8% |

## Phase breakdown — f600 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 8.82 | 54.0% |
| deposits_produce | 5.13 | 31.4% |
| upkeep | 2.05 | 12.5% |
| decompose | 1.73 | 10.6% |
| world_diffuse | 0.37 | 2.3% |
| digest | 0.14 | 0.9% |

## Phase breakdown — f1200 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 52.98 | 74.8% |
| deposits_produce | 13.15 | 18.6% |
| upkeep | 9.16 | 12.9% |
| decompose | 3.67 | 5.2% |
| digest | 0.72 | 1.0% |
| world_diffuse | 0.49 | 0.7% |

## Phase breakdown — cprofile_1200 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 31.11 | 79.0% |
| deposits_produce | 6.25 | 15.9% |
| upkeep | 4.67 | 11.9% |
| decompose | 1.83 | 4.7% |
| digest | 0.35 | 0.9% |
| world_diffuse | 0.24 | 0.6% |
