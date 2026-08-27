# Kernel statistical comparison (20 seeds)

Founders: 300; ticks: 300; conservation: **True**.
Rust has an independent deterministic RNG, so this checks ecological scale, not trajectory parity.

| metric | Python mean | Rust mean | Rust relative delta |
|---|---:|---:|---:|
| population | 286.1 | 322.8 | +12.8% |
| births | 94.0 | 149.8 | +59.4% |
| deaths | 108.0 | 127.0 | +17.6% |
| attacks | 1322.8 | 1328.5 | +0.4% |
| magic_casts | 543.2 | 497.8 | -8.4% |
| alliances | 45.1 | 49.6 | +10.0% |
| colonies | 4.8 | 5.2 | +9.4% |
| asexual_reproduction_events | 80.7 | 135.8 | +68.3% |
| sexual_reproduction_events | 7.0 | 7.2 | +2.8% |

Mean throughput: Python 49.0 ticks/s; Rust 919.2 ticks/s.
