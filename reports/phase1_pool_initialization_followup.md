# Phase 1 pool-initialization follow-up

## Question

Does distributing the same free-pool total uniformly across byte values change low-pool dynamics relative to a pool matched to the initial tape histogram? This P1.6 experiment was selected after the main campaign and is therefore exploratory.

## Results

| Multiplier | Metric | Histogram-matched mean | Uniform mean | Paired uniform − matched [95% bootstrap CI] |
|---:|---|---:|---:|---:|
| 0.1 | Initial zero-count symbols | 0.00 | 0.00 | 0.00 [0.00, 0.00] |
| 0.1 | First-100 blocked fraction | 0.4449 | 0.4393 | -0.0056 [-0.0287, 0.0265] |
| 0.1 | Overall blocked fraction | 0.3030 | 0.3300 | 0.0270 [-0.0166, 0.0799] |
| 0.1 | Final pool JSD | 0.1456 | 0.1606 | 0.0150 [0.0075, 0.0236] |
| 0.1 | Maximum high-order entropy | 0.116 | 0.130 | 0.014 [-0.068, 0.113] |
| 0.5 | Initial zero-count symbols | 0.00 | 0.00 | 0.00 [0.00, 0.00] |
| 0.5 | First-100 blocked fraction | 0.1808 | 0.1699 | -0.0109 [-0.0276, -0.0003] |
| 0.5 | Overall blocked fraction | 0.1486 | 0.1375 | -0.0111 [-0.0735, 0.0653] |
| 0.5 | Final pool JSD | 0.0483 | 0.0488 | 0.0005 [-0.0104, 0.0103] |
| 0.5 | Maximum high-order entropy | 0.362 | 0.541 | 0.179 [-0.010, 0.412] |

## Interpretation

Uniform initialization changed the initial zero-count-symbol burden in **0/5** multiplier-0.1 pairs. It reduced early blocking in **4/5** pairs and increased maximum high-order entropy in **2/5** pairs.

The result tests path dependence, not a preferred default. Histogram matching remains the most direct continuation of the implemented Stage 1 physics; uniform pools are a controlled alternative world.

All runs preserved the exact per-symbol invariant at every aggregate checkpoint and used equal total free matter within each matched seed/multiplier pair.
