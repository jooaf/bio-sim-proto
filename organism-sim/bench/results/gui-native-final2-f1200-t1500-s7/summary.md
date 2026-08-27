# Native GUI benchmark: gui-native-final2-f1200-t1500-s7

Display: `SDL dummy`

| mode | ticks/s | wall seconds | final population |
|---|---:|---:|---:|
| Rust headless | 393.1 | 3.815 | 1372 |
| Rust pygame | 392.3 | 3.836 | 1381 |

GUI/headless throughput: **99.8%** (85% target: **PASS**).
Rendered snapshot frames: `33` (8.6/s).

The dummy-display result includes pygame drawing and snapshot conversion but excludes an OS compositor/GPU presentation cost.
