# Phase 1 follow-up report

## Highest-value next experiments

1. **Requested-symbol event tracing.** Add a sampled event table containing interaction, opcode, requested symbol, source side, destination side, and outcome. This upgrades value-level recycling into explicit acquire→return→reacquire path evidence.
2. **Emergent-checkpoint intervention.** Start clearly labeled Stage 1 continuations from naturally emerged Phase 0 checkpoints, with matched multipliers 0.5, 2, and 16. This directly tests whether conservation stabilizes, disrupts, or reorganizes an existing replicator ecology without seeding a hand-designed organism.
3. **Pool initialization control.** Compare histogram-matched and uniform free pools at equal total matter. This tests whether low-multiplier zero counts create path dependence.
4. **Long-window burst mechanism test.** Around extreme blocked epochs, record per-interaction requested-symbol counts and execution length. The prediction is that one long loop dominates each spike.
5. **Phase 1 semantics correction.** Rename the acceptance target from population saturation to turnover saturation until placement/birth exists. Do not infer genome minimization from nonzero length on fixed random-byte tapes.

## Decision guidance

The larger-scale matrix produced **0 high-order-entropy transitions**. Prioritize longer runs or checkpoint continuation rather than a denser multiplier sweep.

## Integration tasks

- Keep `experiments/phase1_probe.py` separate from the detailed Parquet simulator: it is a bounded aggregate instrument, analogous to `paper_probe.py`.
- Preserve `aggregate.csv`, `writes.csv`, `symbols.csv`, `config.json`, and `manifest.json` as the run contract.
- Add the campaign summary to the experiment registry when the Polars/SQLite refactor lands.
- Use the per-symbol ledger columns to design Stage 2 dissolution measurements: dissolution should return the symbols identified as repeatedly limiting.
- Treat runtime/character reads as a scientific observable; long loops and scarcity bursts are coupled.
