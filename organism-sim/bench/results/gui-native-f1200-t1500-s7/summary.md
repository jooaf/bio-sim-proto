# Native GUI benchmark: gui-native-f1200-t1500-s7

Display: `SDL dummy`

| mode | ticks/s | wall seconds | final population |
|---|---:|---:|---:|
| Rust headless | 463.1 | 3.239 | 1372 |
| Rust pygame | 453.9 | 3.325 | 1364 |

GUI/headless throughput: **98.0%** (85% target: **PASS**).
Rendered snapshot frames: `29` (8.7/s).

The dummy-display result includes pygame drawing and snapshot conversion but excludes an OS compositor/GPU presentation cost.
