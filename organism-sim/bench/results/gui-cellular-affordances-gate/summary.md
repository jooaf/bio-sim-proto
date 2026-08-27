# Native GUI benchmark: gui-cellular-affordances-gate

Display: `SDL dummy`

| mode | ticks/s | wall seconds | final population |
|---|---:|---:|---:|
| Rust headless | 340.8 | 2.201 | 1206 |
| Rust pygame | 338.4 | 2.246 | 1200 |

GUI/headless throughput: **99.3%** (85% target: **PASS**).
Rendered snapshot frames: `20` (8.9/s).

The dummy-display result includes pygame drawing and snapshot conversion but excludes an OS compositor/GPU presentation cost.
