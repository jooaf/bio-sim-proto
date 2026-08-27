# Rust kernel benchmark: parallel-v3-wide-workers1

| behavior | scheduler | workers | founders | ticks | warmup | ticks/s | wall s | final pop | species | energy ok | elements ok |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| recurrent_intent_v2 | parallel-v3 | 1 | 10000 | 10 | 0 | 36.4 | 0.275 | 9973 | 20 | True | True |
| recurrent_intent_v2 | parallel-v3 | 1 | 30000 | 10 | 0 | 10.8 | 0.926 | 29662 | 20 | True | True |
