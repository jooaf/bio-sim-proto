# Benchmark: pyopt_flamegraph

| label | founders | ticks | ticks/s | mean pop | peak pop | audit |
|---|---:|---:|---:|---:|---:|---:|
| pyinstrument_1200 | 1200 | 150 | 7.5 | 1110 | 1145 | 0 |

## Phase breakdown — pyinstrument_1200 (share of tick wall time)

| phase | seconds | share |
|---|---:|---:|
| decisions | 14.76 | 73.6% |
| deposits_produce | 2.84 | 14.2% |
| decompose | 0.90 | 4.5% |
| upkeep | 0.74 | 3.7% |
| digest | 0.18 | 0.9% |
| world_diffuse | 0.15 | 0.8% |
| other(step remainder) | 0.48 | 2.4% |
