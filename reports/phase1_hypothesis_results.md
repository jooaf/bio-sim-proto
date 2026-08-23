# Phase 1 hypothesis results

## Executive result

The campaign contains **34 completed exact-conservation runs**. All checkpoints had zero per-symbol conservation residual. At the 256-tape scale, the rank correlation between pool multiplier and mean blocked-write rate was **-1.00**.

## Confirmatory hypotheses

### H1 — Scarcity response: supported

Blocked-write rates decline with pool size, while tighter pools show larger composition drift. Because the free-pool total is exactly fixed, the constraint is selective symbol scarcity—not loss of total matter.

| Multiplier | Blocked fraction, mean [95% bootstrap CI] | Pool entropy change | Final pool JSD |
|---:|---:|---:|---:|
| 0.1 | 0.3030 [0.2556, 0.3630] | -0.549 [-0.564, -0.537] | 0.146 [0.143, 0.150] |
| 0.5 | 0.1486 [0.0945, 0.1939] | -0.195 [-0.223, -0.166] | 0.048 [0.040, 0.057] |
| 2 | 0.0308 [0.0178, 0.0475] | -0.070 [-0.077, -0.063] | 0.018 [0.015, 0.021] |
| 16 | 0.0014 [0.0004, 0.0024] | -0.008 [-0.010, -0.006] | 0.002 [0.001, 0.002] |
| 256 | 0.0000 [0.0000, 0.0000] | -0.000 [-0.000, -0.000] | 0.000 [0.000, 0.000] |

### H2 — Intermediate-scarcity organization: not resolved

For matched seeds, multiplier 2 minus the larger entropy maximum at multipliers 0.5 and 16 had mean difference **0.088 bits/byte** (95% bootstrap CI **[-0.071, 0.247]**); **3/5** seeds favored multiplier 2.

This tests the preregistered local contrast. It does not establish a universal optimum, and high-order entropy is not by itself a replication detector.

### H3 — Blocking regime changes with scarcity; periodicity not supported

At multiplier 0.1, blocking was broad and nearly continuous: the mean effective blocked-symbol count was **177.7** of 256, only **0.01%** of epochs had no blocking, and mean CV was **0.9**. At multiplier 2, the corresponding values were **17.2**, **67.4%**, and **4.9**; at multiplier 16, blocking was absent in **96.2%** of epochs and overwhelmingly targeted byte 60 (`<`) when it occurred. The median spectral peak across mechanism runs held only **1.1%** of non-DC power. Thus very tight scarcity is a broad global brake, while moderate/loose scarcity produces rare symbol-specific bursts; no narrow periodic oscillator is established.

### H4 — Recycling and cross-tape acquisition: supported at value level

Every completed run recorded successful cross-boundary copy events. The median final conservative lower bound on recycled withdrawals was **98.7%**. This proves repeated return/re-acquisition of byte values through the pool; it does not identify individual byte-token paths.

## Larger-scale exploratory result

| Population | Multiplier | Runs | Entropy transitions | Max high-order entropy | Dominant fraction |
|---:|---:|---:|---:|---:|---:|
| 4,096 | 0.5 | 3 | 0 | 0.406 [0.382, 0.437] | 0.0010 [0.0010, 0.0010] |
| 4,096 | 2 | 3 | 0 | 0.425 [0.367, 0.473] | 0.0010 [0.0007, 0.0012] |
| 4,096 | 16 | 3 | 0 | 0.347 [0.336, 0.366] | 0.0005 [0.0005, 0.0005] |

## Interpretation limits

- The exact conserved kernel is serial because interaction order changes access to the global pool.
- The accelerated probe follows the paper's SplitMix64 protocol; it is a mechanistic replication of the earlier NumPy-RNG Stage 1 pilot, not the same stochastic trajectory.
- Tape count and tape capacity are fixed in Phase 1, so literal population-growth saturation and genome-length shrinkage cannot be inferred.
- High-order entropy detects compressible population structure, not function by itself.
