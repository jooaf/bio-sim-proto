# Native GUI benchmark: gui-native-scale-f5000-t500-s7

Display: `SDL dummy`

| mode | ticks/s | wall seconds | final population |
|---|---:|---:|---:|
| Rust headless | 258.4 | 1.935 | 1370 |
| Rust pygame | 257.5 | 1.996 | 1362 |

GUI/headless throughput: **99.6%** (85% target: **PASS**).
Rendered snapshot frames: `18` (9.0/s).

The dummy-display result includes pygame drawing and snapshot conversion but excludes an OS compositor/GPU presentation cost.
