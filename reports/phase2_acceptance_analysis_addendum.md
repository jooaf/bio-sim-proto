# Phase 2 final-window acceptance-analysis addendum

**Frozen before the 500,000-tick treatment:** 2026-08-26

## Full-byte final window

Use every complete full-byte snapshot whose tick is in the final 10% of the configured horizon. Under the frozen 500,000-tick config and 5,000-tick full-byte cadence, this yields ten intended snapshots from ticks 450,000 through 495,000.

Snapshots receive equal weight so transient occupancy differences do not let one checkpoint dominate the final-window statistic.

## Pooled positional byte identity

For each snapshot:

1. compute mean positional byte identity over occupied undirected radius-1 neighbors;
2. independently permute complete tapes over fixed occupied cells for each null replicate;
3. average the snapshot statistics within that replicate.

Use 999 replicates and analysis seed 20260825. Report observed final-window mean, null mean, excess, and one-sided pooled permutation p-value.

Criterion: excess > 0 and pooled p < 0.05.

## Pooled opcode-signature beta

For every final-window snapshot:

1. derive the ordered BFF-opcode signature of each tape;
2. compute q=1 multiplicative beta diversity over fixed 8×8 blocks;
3. independently permute signatures over occupied cells;
4. average beta across snapshots within each null replicate.

Use 999 replicates and analysis seed 20260826. Report observed mean beta, null mean, excess, and one-sided pooled permutation p-value.

Criterion: excess > 0 and pooled p < 0.05.

## Mechanical gate

The existing Stage 2 mechanical report remains authoritative for:

- exact conservation;
- anti-clogging;
- anti-extinction/liveness;
- occupancy;
- successful writes;
- interactions;
- dissolution and placement;
- final-window pool turnover.

The final Phase 2 run passes only if both spatial criteria and the combined mechanical gate pass.

## Validated command

```nu
uv run python experiments/analyze_phase2_acceptance.py RUN_DIR
```

A short 32×32 confirmation run with a full-byte final-window snapshot successfully exercised the command with 199 smoke permutations. It detected byte-identity excess but did not pass opcode beta. That short result is software validation only and does not count toward acceptance.
