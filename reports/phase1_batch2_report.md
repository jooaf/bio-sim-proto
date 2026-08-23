# Phase 1 batch-2 analysis

## D1 — 16,384-tape runs

| arm     |   seed | entropy_transition   |   first_transition_epoch |   final_entropy | held_to_end   |   max_diversity_collapse | structural_takeover   |   first_blocked_epoch |
|:--------|-------:|:---------------------|-------------------------:|----------------:|:--------------|-------------------------:|:----------------------|----------------------:|
| m16     |      0 | False                |                      nan |        0.136003 | False         |              0.000305176 | False                 |                  5441 |
| m16     |      1 | False                |                      nan |        0.129762 | False         |              0.000244141 | False                 |                  4383 |
| m16     |      2 | False                |                      nan |        0.13745  | False         |              0.000183105 | False                 |                  4634 |
| m16     |      3 | True                 |                    24701 |        5.12682  | True          |              0.415771    | True                  |                  5296 |
| m16     |      4 | False                |                      nan |        0.114148 | False         |              0.000183105 | False                 |                 11156 |
| control |      0 | False                |                      nan |        0.129166 | False         |              0.000305176 | False                 |                    -1 |
| control |      1 | False                |                      nan |        0.121053 | False         |              0.000244141 | False                 |                    -1 |
| control |      2 | False                |                      nan |        0.112405 | False         |              0.000183105 | False                 |                    -1 |
| control |      3 | False                |                      nan |        0.106821 | False         |              0.000305176 | False                 |                    -1 |
| control |      4 | True                 |                    44101 |        0.046982 | False         |              0.00134277  | False                 |                    -1 |

- D1a: control emergences 1/5 (criterion >= 2/5: NOT SUPPORTED)
- D1b: held-to-end among emergent controls: 0/1
- Structural takeovers (entropy crossing + >=5% diversity collapse): m16 1/5, control 0/5

- D1c: first-block epoch median 16,384 = 5296 vs 4,096 batch-1 median = 4749; MW-U one-sided p = 0.4206

## E1 — 32,768-tape runs

| arm     |   seed | entropy_transition   |   first_transition_epoch |   final_entropy | held_to_end   |   max_diversity_collapse | structural_takeover   |   first_blocked_epoch |
|:--------|-------:|:---------------------|-------------------------:|----------------:|:--------------|-------------------------:|:----------------------|----------------------:|
| m16     |      0 | True                 |                    81401 |        4.11814  | True          |              0.606018    | True                  |                  5829 |
| m16     |      1 | False                |                      nan |        0.126173 | False         |              0.000366211 | False                 |                  5405 |
| m16     |      2 | False                |                      nan |        0.126977 | False         |              0.000183105 | False                 |                  6030 |
| m16     |      3 | True                 |                    87601 |        6.32804  | True          |              0.779419    | True                  |                 13849 |
| m16     |      4 | False                |                      nan |        0.143904 | False         |              0.000152588 | False                 |                  5362 |
| control |      0 | True                 |                    17201 |        6.46525  | True          |              0.816742    | True                  |                    -1 |
| control |      1 | True                 |                    38201 |        0.137141 | False         |              0.220337    | True                  |                    -1 |
| control |      2 | False                |                      nan |        0.140258 | False         |              0.000183105 | False                 |                    -1 |
| control |      3 | False                |                      nan |        0.135004 | False         |              0.000579834 | False                 |                    -1 |
| control |      4 | True                 |                    42001 |        6.31216  | True          |              0.624512    | True                  |                    -1 |

- E1a: control emergences 3/5 (criterion >= 2/5: SUPPORTED)
- E1b: held-to-end among crossings — m16 2/2, control 2/3; Fisher exact two-sided p = 1.0000
- Structural takeovers: m16 2/5, control 3/5
- E1c: first-block epoch median 32,768 = 5829 vs 16,384 = 5296; MW-U two-sided p = 0.2222 (scale-invariance confirmed if p > 0.05)

## D2 — shadowing onset (batch-1 A runs)

|   seed |   0.5 |   2.0 |   16.0 |
|-------:|------:|------:|-------:|
|      0 |   155 |   547 |   3575 |
|      1 |   133 |   562 |   4749 |
|      2 |   200 |   716 |   5516 |
|      3 |   177 |   577 |   7217 |
|      4 |    17 |    86 |   4537 |

Spearman rho = 0.869, p = 2.57e-05 (n = 15).

## D3 — role-persistence decay and self-flow share

|   lag |      mean |        std |
|------:|----------:|-----------:|
|     1 | 0.192863  | 0.00822069 |
|     2 | 0.0630123 | 0.00893814 |
|     3 | 0.0297881 | 0.00672448 |
|     4 | 0.0242327 | 0.0136806  |

D3a decay Spearman rho = -1.000, p = 0.0833: no significant monotone decay

D3b self-flow share mean = 0.2900, CV across windows mean = 0.364 (non-stationary)
