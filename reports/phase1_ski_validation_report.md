# Phase 1 SKI substrate-validation results

## Scope

Nine conservation-aware SKI runs used the existing flat world, ordered interaction runner, scheduler, invariant checker, six Parquet tables, and Stage 1 report pipeline. Each run contained 256 tapes, 5,000 ticks, and 640,000 interactions; mutation was disabled to avoid confounding prefix-grammar corruption.

## Multiplier response

| Multiplier | Blocked writes | First-100 blocked | Last-100 blocked | Valid expressions | Final mean tokens | Normal form | Pool-blocked reactions | Conservation residual |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 76.82% | 46.73% | 80.29% (3/3 runs attempted writes) | 100.00% | 4.03 | 61.2% | 36.6% | 0 |
| 2 | 89.29% | 51.11% | 92.42% (3/3 runs attempted writes) | 100.00% | 7.06 | 41.3% | 54.0% | 0 |
| 16 | 0.55% | 0.55% | 0.00% (1/3 runs attempted writes) | 100.00% | 23.07 | 82.5% | 0.0% | 0 |

## Mechanical criteria

- **S1 passed:** hand-worked `I x`, `K x y`, and one-step `S x y z` reductions have unit tests.
- **S2 passed:** an unavailable atomic rewrite leaves the joint tape and pool byte-identical; simultaneous swaps can use symbols returned by the same reaction.
- **S3 passed:** all sweep snapshots have exact 256-component conservation and every invariant log is empty.
- **S4 passed:** two independently executed short SKI runs with the same seed/config produce byte-identical raw Parquet digests.
- **S5 contradicted as a monotonic hypothesis:** multiplier 2 blocked more attempted slots than 0.5, while 16 was nearly unblocked. The intermediate reservoir supports longer expressions, which then demand scarce application/combinator symbols; the tighter reservoir collapses sooner to shorter expressions. This is a real substrate dynamic, not a conservation failure.
- **S6 passed with documented boundary work:** no changes were made to `soup/world.py`, `soup/scheduler.py`, or `soup/logging/` for SKI.

## Forced implementation changes

1. `WriteMediator` gained a generic atomic `write_batch` operation, implemented by `SymbolPool`. SKI rewrites must be all-or-nothing; partial serialized rewrites would corrupt grammar. BFF continues using single-slot writes unchanged.
2. `Simulation` now selects `BFFSubstrate` or `SKISubstrate` from config.
3. Stage 1 config validation now permits `substrate.name = "ski"`; Stage 0 remains BFF-only.
4. The visualizer received only a BFF type guard for BFF-specific live controls. SKI validation itself is headless.
5. The Stage 1 report label changed from “BFF writes” to “substrate writes.”

## Interpretation

The portability criterion is satisfied: a second execution chemistry uses the same state container, pair scheduling, mutation wrapper, conservation invariant, logging schemas, and offline conservation report. This validates the substrate boundary mechanically.

This SKI model is deliberately minimal. It stores one prefix expression per fixed tape; ordered interaction replaces A with a bounded reduction of application `A B`, while B remains unchanged. It is not claimed to reproduce Combinatory Chemistry or chemSKI ecology. Its purpose is to test substrate independence and conserved rewrite mechanics.

Across all runs, inactive byte values retained **0** free tokens at most (expected zero), and the sampled invalid-program fraction was **0.00%**, confirming that atomic rewrites preserved grammar without mutation.
