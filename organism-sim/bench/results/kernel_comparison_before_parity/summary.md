# Kernel statistical comparison (5 seeds)

Founders: 300; ticks: 300; conservation: **True**.
Rust has an independent deterministic RNG, so this checks ecological scale, not trajectory parity.

| metric | Python mean | Rust mean | Rust relative delta |
|---|---:|---:|---:|
| population | 259.6 | 253.6 | -2.3% |
| births | 84.2 | 58.8 | -30.2% |
| deaths | 124.6 | 105.2 | -15.6% |
| attacks | 1926.6 | 935.8 | -51.4% |
| magic_casts | 532.2 | 528.8 | -0.6% |
| alliances | 36.2 | 38.6 | +6.6% |
| colonies | 0.8 | 0.8 | +0.0% |
| asexual_reproduction_events | 71.0 | 52.6 | -25.9% |
| sexual_reproduction_events | 7.8 | 2.6 | -66.7% |

Mean throughput: Python 50.5 ticks/s; Rust 947.6 ticks/s.
