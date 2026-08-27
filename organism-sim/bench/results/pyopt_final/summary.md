# Benchmark: pyopt_final

| label | founders | ticks | ticks/s | mean pop | peak pop | audit |
|---|---:|---:|---:|---:|---:|---:|
| f300 | 300 | 300 | 48.4 | 371 | 420 | 0 |
| f600 | 600 | 300 | 33.2 | 607 | 665 | 0 |
| f1200 | 1200 | 300 | 19.7 | 1106 | 1128 | 0 |

## Phase breakdown — f300 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 3.14 | 50.6% |
| deposits_produce | 2.53 | 40.8% |
| decompose | 0.83 | 13.3% |
| world_diffuse | 0.27 | 4.3% |
| upkeep | 0.26 | 4.1% |
| digest | 0.07 | 1.1% |

## Phase breakdown — f600 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 6.15 | 68.1% |
| deposits_produce | 2.63 | 29.2% |
| decompose | 0.86 | 9.5% |
| upkeep | 0.43 | 4.8% |
| world_diffuse | 0.28 | 3.1% |
| digest | 0.10 | 1.1% |

## Phase breakdown — f1200 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 12.77 | 83.9% |
| deposits_produce | 2.81 | 18.5% |
| decompose | 0.91 | 6.0% |
| upkeep | 0.87 | 5.7% |
| world_diffuse | 0.30 | 2.0% |
| digest | 0.18 | 1.2% |
| corpses | 0.04 | 0.2% |
