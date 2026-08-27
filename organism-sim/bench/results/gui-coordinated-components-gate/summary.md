# Native GUI benchmark: gui-coordinated-components-gate

Display: `SDL dummy`

| mode | ticks/s | wall seconds | final population |
|---|---:|---:|---:|
| Rust headless | 519.6 | 1.444 | 1087 |
| Rust pygame | 500.0 | 1.514 | 1079 |

GUI/headless throughput: **96.2%** (85% target: **PASS**).
Rendered snapshot frames: `14` (9.2/s).

The dummy-display result includes pygame drawing and snapshot conversion but excludes an OS compositor/GPU presentation cost.
