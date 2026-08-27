# Native GUI benchmark: gui-native-final-f1200-t1500-s7

Display: `SDL dummy`

| mode | ticks/s | wall seconds | final population |
|---|---:|---:|---:|
| Rust headless | 461.5 | 3.250 | 1372 |
| Rust pygame | 459.1 | 3.274 | 1383 |

GUI/headless throughput: **99.5%** (85% target: **PASS**).
Rendered snapshot frames: `28` (8.6/s).

The dummy-display result includes pygame drawing and snapshot conversion but excludes an OS compositor/GPU presentation cost.
