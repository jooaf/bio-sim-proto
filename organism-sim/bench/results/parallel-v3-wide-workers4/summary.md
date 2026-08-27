# Rust kernel benchmark: parallel-v3-wide-workers4

| behavior | scheduler | workers | founders | ticks | warmup | ticks/s | wall s | final pop | species | energy ok | elements ok |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| recurrent_intent_v2 | parallel-v3 | 4 | 10000 | 10 | 0 | 66.9 | 0.149 | 9973 | 20 | True | True |
| recurrent_intent_v2 | parallel-v3 | 4 | 30000 | 10 | 0 | 21.6 | 0.463 | 29662 | 20 | True | True |
