# Rust kernel benchmark: parallel-v3-wide-workers8

| behavior | scheduler | workers | founders | ticks | warmup | ticks/s | wall s | final pop | species | energy ok | elements ok |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| recurrent_intent_v2 | parallel-v3 | 8 | 10000 | 10 | 0 | 64.7 | 0.154 | 9973 | 20 | True | True |
| recurrent_intent_v2 | parallel-v3 | 8 | 30000 | 10 | 0 | 24.4 | 0.410 | 29662 | 20 | True | True |
