# Native GUI benchmark: gui-after-simd-dense-render

Display: `SDL dummy`

| mode | ticks/s | wall seconds | final population |
|---|---:|---:|---:|
| Rust headless | 372.0 | 2.688 | 1253 |
| Rust pygame | 359.8 | 2.788 | 1243 |

GUI/headless throughput: **96.7%** (85% target: **PASS**).
Rendered snapshot frames: `24` (8.6/s).

The dummy-display result includes pygame drawing and snapshot conversion but excludes an OS compositor/GPU presentation cost.
