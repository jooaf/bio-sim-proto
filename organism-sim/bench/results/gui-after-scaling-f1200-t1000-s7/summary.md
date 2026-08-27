# Native GUI benchmark: gui-after-scaling-f1200-t1000-s7

Display: `SDL dummy`

| mode | ticks/s | wall seconds | final population |
|---|---:|---:|---:|
| Rust headless | 354.8 | 2.819 | 1253 |
| Rust pygame | 365.7 | 2.767 | 1251 |

GUI/headless throughput: **103.1%** (85% target: **PASS**).
Rendered snapshot frames: `24` (8.7/s).

The dummy-display result includes pygame drawing and snapshot conversion but excludes an OS compositor/GPU presentation cost.
