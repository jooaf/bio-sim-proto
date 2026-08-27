# Benchmark: pyopt_probe

| label | founders | ticks | ticks/s | mean pop | peak pop | audit |
|---|---:|---:|---:|---:|---:|---:|
| f300 | 300 | 300 | 41.0 | 363 | 420 | 0 |
| f600 | 600 | 300 | 28.0 | 602 | 655 | 0 |
| f1200 | 1200 | 300 | 17.3 | 1109 | 1145 | 0 |

## Phase breakdown — f300 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| deposits_produce | 3.51 | 48.0% |
| decisions | 3.07 | 42.0% |
| decompose | 0.77 | 10.5% |
| world_diffuse | 0.25 | 3.4% |
| upkeep | 0.23 | 3.2% |
| digest | 0.06 | 0.9% |

## Phase breakdown — f600 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 6.29 | 58.8% |
| deposits_produce | 3.73 | 34.9% |
| decompose | 0.83 | 7.7% |
| upkeep | 0.43 | 4.0% |
| world_diffuse | 0.27 | 2.5% |
| digest | 0.10 | 0.9% |

## Phase breakdown — f1200 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 12.85 | 74.2% |
| deposits_produce | 3.95 | 22.8% |
| decompose | 0.87 | 5.0% |
| upkeep | 0.85 | 4.9% |
| world_diffuse | 0.29 | 1.7% |
| digest | 0.17 | 1.0% |
| corpses | 0.09 | 0.5% |
