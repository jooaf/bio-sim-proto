# P0.7 — paper-scale time-to-emergence replicates (seeds 1–3)

## Scope

Three independent paper-protocol runs at the reference background mutation rate (`1/4096`) were completed for seeds 1–3. This is a bounded replication of P0.7, complementing the existing seed-0 pilot; it is not yet the planned 30-seed distribution study.

- Population: 131,072 tapes
- Tape length: 64 bytes
- Pairing: shuffled disjoint pairs (65,536 interactions/epoch)
- Execution budget: 8,192 character reads/interaction
- Epochs: 16,000
- Aggregate callback interval: 128 epochs

## Results

| Seed | Aggregate observations | Final epoch | First observed high-order-entropy transition (>= 1 bit/byte) | Maximum high-order entropy (bits/byte) | Final high-order entropy (bits/byte) | Runtime (s) | Final character reads |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 126 | 16,000 | none | 0.364 | 0.136 | 184.7 | 670,394,784,744 |
| 2 | 126 | 16,000 | 11,777 | 5.649 | 5.649 | 449.8 | 2,603,436,342,706 |
| 3 | 126 | 16,000 | none | 0.387 | 0.135 | 177.9 | 665,593,121,723 |

Raw aggregate trajectories:

- `reports/p0_7_reference_seed_1.csv`
- `reports/p0_7_reference_seed_2.csv`
- `reports/p0_7_reference_seed_3.csv`

A transition checkpoint was produced only for seed 2:

- `runs/p0_7_reference_seed_2_transition.npy`

## Interpretation

One of the three new seeds (seed 2) crossed the paper-style high-order-entropy threshold and remained in a high-complexity regime through epoch 16,000. Seeds 1 and 3 showed only transient, low-amplitude structure and finished below 0.14 bits/byte. The successful seed was also about 2.4–2.5 times slower and consumed about 3.9 times as many character reads, consistent with sustained long BFF execution loops after emergence.

The transition epoch is the first *observed* callback at or above the threshold; the true crossing may have occurred up to 127 epochs earlier. With seed 0's previously recorded transition at epoch 2,433, the four available reference-rate seeds yield two observed transitions by epoch 16,000 (seeds 0 and 2). This is descriptive only; substantially more seeds are required for an emergence-rate estimate or a time-to-emergence distribution.

## Completion checks

All three CSVs contain the final epoch-16,000 row and 126 aggregate observations. The batch stderr log is empty, and no `soup-paper-probe` or batch-runner process remains alive.
