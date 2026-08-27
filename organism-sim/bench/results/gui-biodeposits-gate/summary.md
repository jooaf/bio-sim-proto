# Native GUI benchmark: gui-biodeposits-gate

Display: `SDL dummy`

| mode | ticks/s | wall seconds | final population |
|---|---:|---:|---:|
| Rust headless | 303.2 | 2.474 | 1174 |
| Rust pygame | 315.5 | 2.399 | 1166 |

GUI/headless throughput: **104.1%** (85% target: **PASS**).
Rendered snapshot frames: `21` (8.8/s).

The dummy-display result includes pygame drawing and snapshot conversion but excludes an OS compositor/GPU presentation cost.
