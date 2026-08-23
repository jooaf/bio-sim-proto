# Phase 1 new-experiment batch: results

Preregistration: `reports/phase1_newexperiments_preregistration.md`.
Analyzer: `experiments/analyze_phase1_newexperiments.py` (numpy-only stats, seeded RNG 20260815).

## Verification

- Conserved runs with nonzero conservation residual: **0**
- Conserved runs in A+B: 20

## Run inventory

| experiment   | arm                  |   seed |   epochs | entropy_transition   |   first_transition_epoch |   max_high_order_entropy |   final_high_order_entropy |   max_dominant_fraction |   final_dominant_fraction |   overall_blocked_fraction |   wall_time_s |   max_conservation_residual | run_dir                                                      |   first_1000_blocked_fraction |
|:-------------|:---------------------|-------:|---------:|:---------------------|-------------------------:|-------------------------:|---------------------------:|------------------------:|--------------------------:|---------------------------:|--------------:|----------------------------:|:-------------------------------------------------------------|------------------------------:|
| A            | m0.5                 |      0 |   100000 | False                |                      nan |                 0.503376 |                  0.246152  |             0.0012207   |               0.000244141 |                0.0547801   |       245.866 |                           0 | experiments/phase1_runs/longwindow/p1_m0p5_n4096_s0          |                 nan           |
| A            | m0.5                 |      1 |   100000 | False                |                      nan |                 0.466107 |                  0.150265  |             0.0012207   |               0.000244141 |                0.0527523   |       250.813 |                           0 | experiments/phase1_runs/longwindow/p1_m0p5_n4096_s1          |                 nan           |
| A            | m0.5                 |      2 |   100000 | False                |                      nan |                 0.439842 |                  0.226076  |             0.00146484  |               0.000732422 |                0.0494988   |       231.115 |                           0 | experiments/phase1_runs/longwindow/p1_m0p5_n4096_s2          |                 nan           |
| A            | m0.5                 |      3 |   100000 | False                |                      nan |                 0.42422  |                  0.175263  |             0.0012207   |               0.000244141 |                0.0720072   |       179.059 |                           0 | experiments/phase1_runs/longwindow/p1_m0p5_n4096_s3          |                 nan           |
| A            | m0.5                 |      4 |   100000 | True                 |                    35501 |                 1.22649  |                  0.181827  |             0.0012207   |               0.000244141 |                0.0503356   |       181.276 |                           0 | experiments/phase1_runs/longwindow/p1_m0p5_n4096_s4          |                 nan           |
| A            | m16                  |      0 |   100000 | True                 |                    90401 |                 5.9537   |                  5.37281   |             0.0102539   |               0.00268555  |                0.000118791 |       722.608 |                           0 | experiments/phase1_runs/longwindow/p1_m16_n4096_s0           |                 nan           |
| A            | m16                  |      1 |   100000 | False                |                      nan |                 0.337898 |                  0.136137  |             0.000732422 |               0.000244141 |                0.000117356 |       392.005 |                           0 | experiments/phase1_runs/longwindow/p1_m16_n4096_s1           |                 nan           |
| A            | m16                  |      2 |   100000 | False                |                      nan |                 0.336284 |                  0.120206  |             0.000732422 |               0.000244141 |                0.000175028 |       389.398 |                           0 | experiments/phase1_runs/longwindow/p1_m16_n4096_s2           |                 nan           |
| A            | m16                  |      3 |   100000 | False                |                      nan |                 0.366837 |                  0.13296   |             0.000732422 |               0.000244141 |                7.88548e-05 |       401.219 |                           0 | experiments/phase1_runs/longwindow/p1_m16_n4096_s3           |                 nan           |
| A            | m16                  |      4 |   100000 | False                |                      nan |                 0.412793 |                  0.125566  |             0.000488281 |               0.000244141 |                3.28644e-05 |       400.63  |                           0 | experiments/phase1_runs/longwindow/p1_m16_n4096_s4           |                 nan           |
| A            | m2                   |      0 |   100000 | True                 |                    74901 |                 1.63247  |                  0.614836  |             0.0012207   |               0.000244141 |                0.0409179   |       276.027 |                           0 | experiments/phase1_runs/longwindow/p1_m2_n4096_s0            |                 nan           |
| A            | m2                   |      1 |   100000 | False                |                      nan |                 0.758213 |                  0.258396  |             0.000976562 |               0.000244141 |                0.014671    |       218.21  |                           0 | experiments/phase1_runs/longwindow/p1_m2_n4096_s1            |                 nan           |
| A            | m2                   |      2 |   100000 | False                |                      nan |                 0.468668 |                  0.32613   |             0.000976562 |               0.000244141 |                0.0182171   |       210.274 |                           0 | experiments/phase1_runs/longwindow/p1_m2_n4096_s2            |                 nan           |
| A            | m2                   |      3 |   100000 | False                |                      nan |                 1.06691  |                  0.27958   |             0.000976562 |               0.000244141 |                0.0170786   |       209.168 |                           0 | experiments/phase1_runs/longwindow/p1_m2_n4096_s3            |                 nan           |
| A            | m2                   |      4 |   100000 | False                |                      nan |                 0.47235  |                  0.297794  |             0.0012207   |               0.000244141 |                0.0150426   |       228.773 |                           0 | experiments/phase1_runs/longwindow/p1_m2_n4096_s4            |                 nan           |
| A            | control              |      0 |     1001 | False                |                      nan |                 0.366204 |                  0.134014  |             0.000488281 |               0.000244141 |                0           |       nan     |                           0 | reports/phase1_newexperiments/A_control_n4096_s0.csv         |                 nan           |
| A            | control              |      1 |     1001 | False                |                      nan |                 0.337898 |                  0.101133  |             0.000488281 |               0.000244141 |                0           |       nan     |                           0 | reports/phase1_newexperiments/A_control_n4096_s1.csv         |                 nan           |
| A            | control              |      2 |     1001 | True                 |                    63701 |                 3.92144  |                  0.0897158 |             0.0268555   |               0.000244141 |                0           |       nan     |                           0 | reports/phase1_newexperiments/A_control_n4096_s2.csv         |                 nan           |
| A            | control              |      3 |     1001 | False                |                      nan |                 0.366837 |                  0.1191    |             0.000732422 |               0.000244141 |                0           |       nan     |                           0 | reports/phase1_newexperiments/A_control_n4096_s3.csv         |                 nan           |
| A            | control              |      4 |     1001 | False                |                      nan |                 0.412793 |                  0.127382  |             0.000732422 |               0.000244141 |                0           |       nan     |                           0 | reports/phase1_newexperiments/A_control_n4096_s4.csv         |                 nan           |
| B            | control_continuation |      0 |       81 | True                 |                        1 |                 6.10536  |                  5.80386   |             0.00139618  |               0.000907898 |                0           |       nan     |                           0 | reports/phase1_newexperiments/B_control_continuation.csv     |                 nan           |
| B            | m0.5_continuation    |      0 |     8000 | True                 |                        1 |                 6.05123  |                  5.95279   |             0.00117493  |               0.000640869 |                5.83897e-06 |      6277.61  |                           0 | experiments/phase1_runs/continuation/p1_m0p5_n131072_s0_cont |                   1.77411e-06 |
| B            | m16_continuation     |      0 |     8000 | True                 |                        1 |                 6.10536  |                  5.80386   |             0.00139618  |               0.000907898 |                0           |      6716.59  |                           0 | experiments/phase1_runs/continuation/p1_m16_n131072_s0_cont  |                   0           |
| B            | m2_baseline          |      0 |     8000 | False                |                      nan |                 0.37954  |                  0.300651  |             9.91821e-05 |               3.05176e-05 |                0.0158916   |       779.367 |                           0 | experiments/phase1_runs/continuation/p1_m2_n131072_s0        |                   0.00758526  |
| B            | m2_continuation      |      0 |     8000 | True                 |                        1 |                 6.10955  |                  6.04632   |             0.00131989  |               0.000907898 |                2.55997e-07 |      6881.95  |                           0 | experiments/phase1_runs/continuation/p1_m2_n131072_s0_cont   |                   1.41129e-07 |

## Experiment C inventory

|   pool_multiplier |   seed |   n_windows |   observed_mean_corr |   null_mean_corr |      gap | run_dir                                                            |
|------------------:|-------:|------------:|---------------------:|-----------------:|---------:|:-------------------------------------------------------------------|
|               0.5 |      0 |          10 |             0.190824 |       0.00903103 | 0.181793 | experiments/phase1_runs/metabolic_trace_windows/trace_m0p5_n256_s0 |
|               0.5 |      1 |          10 |             0.20373  |       0.0104022  | 0.193328 | experiments/phase1_runs/metabolic_trace_windows/trace_m0p5_n256_s1 |
|               0.5 |      2 |          10 |             0.192272 |       0.0110058  | 0.181266 | experiments/phase1_runs/metabolic_trace_windows/trace_m0p5_n256_s2 |
|              16   |      0 |          10 |             0.186513 |       0.0115353  | 0.174978 | experiments/phase1_runs/metabolic_trace_windows/trace_m16_n256_s0  |
|              16   |      1 |          10 |             0.200016 |       0.0107879  | 0.189228 | experiments/phase1_runs/metabolic_trace_windows/trace_m16_n256_s1  |
|              16   |      2 |          10 |             0.203939 |       0.0123883  | 0.191551 | experiments/phase1_runs/metabolic_trace_windows/trace_m16_n256_s2  |
|               2   |      0 |          10 |             0.186255 |       0.0107932  | 0.175462 | experiments/phase1_runs/metabolic_trace_windows/trace_m2_n256_s0   |
|               2   |      1 |          10 |             0.180236 |       0.0109844  | 0.169252 | experiments/phase1_runs/metabolic_trace_windows/trace_m2_n256_s1   |
|               2   |      2 |          10 |             0.191982 |       0.0118147  | 0.180167 | experiments/phase1_runs/metabolic_trace_windows/trace_m2_n256_s2   |

## Hypothesis decisions

### A1 — control emergence at 4,096 tapes / 100K epochs
Control emergences: **1/5**.
Per-seed first-transition epochs: [63701.0].

### A2 — conservation suppresses emergence (Fisher exact, one-sided)
m2 emergences: 1/5; control 1/5; one-sided p = **0.7778**.

### A3 — scarcity ordering (Spearman, multiplier vs max entropy)
rho = **-0.302**, p = 0.2733 (two-sided, n = 15).

### A4 — blocked-rate scarcity curve (Spearman)
rho = **-0.945**, p = 1.13e-07 (two-sided, n = 15).

### B1 — control continuation completes takeover
Control final dominant fraction = **0.0009**; final entropy = 5.804 bits/byte.
Decision: **not supported** (checkpoint not a viable takeover precursor)

### B2 — intermediate conservation disrupts takeover
m2 continuation final dominant fraction = **0.0009**; final entropy = 6.046 bits/byte (control: 5.804).
Decision: **not supported**

### B3 — loose conservation is neutral
m16 continuation final dominant fraction = **0.0009** (criterion > 0.5).
Decision: **not supported**

### B4 — replicator demand concentrates scarcity
Continuation first-1000-epoch blocked fraction = **0.0000**; random-soup baseline = 0.0076.
### C1 — windowed flow organization vs null
Mean observed corr = 0.1929; mean null = 0.0110; mean gap = **0.1819**; one-sided paired permutation p = **0.0025** (n = 9 runs, effect SD = 0.0081).
Decision: **flow structure exceeds null** (persistent organization evidence)

### C2 — scarcity sharpens structure (Spearman, multiplier vs gap)
rho = **-0.158**, p = 0.7286 (two-sided, n = 9).
