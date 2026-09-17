# AC-P004 prospective controlled functional-origin convergence preregistration

**Frozen before implementation-specific runs:** 2026-09-16

## Motivation and boundary

AC-P003 was unevaluable because one valid first-origin assay contained no
below-64 tape among its top 1,024 candidates. That result remains unevaluable;
its checkpoints, metrics, and controls will not be reselected. AC-P004 is a new
prospective experiment that captures a temporally adjacent control assay before
origin and tests convergence only if enough independently initialized runs
produce both strict functional origin and a usable frozen control.

This does not reopen the failed AC-P002 resource comparison. Multiplier 16 is
used solely as the previously validated origin-acquisition regime.

## Required observational implementation

Add an opt-in prospective-control mode to the committed functional observer.
At every callback, rank the current exact tapes by descending abundance with
lexicographic stable ties and retain only the current top 1,024 candidates and
abundances in a rolling in-memory snapshot. This is observational and must not
alter soup, pool, counters, scheduling, or simulation RNG.

When the first strict functional origin qualifies:

1. persist the immediately preceding callback's ranked candidates, abundances,
   local/absolute epoch, and observer version;
2. score that saved prior set once with the unchanged paper evaluator, base seed
   0, and original rank offsets;
3. persist all resulting scores as `pre_origin_control.npz`; and
4. never overwrite it at later callbacks.

The prior snapshot must precede the origin by exactly one scheduled callback.
The existing first-origin assay and checkpoint remain unchanged. Runs without
origin create no pre-origin control artifact. Add tests for exact candidate
ordering, assay agreement, first-origin non-overwrite, artifact checksums,
observational trajectory identity, and disabled-mode compatibility.

## Frozen acquisition campaign

Run 20 new independently initialized seeds `202614000`–`202614019` with:

- 32,768 tapes of length 64;
- histogram-matched conserved pool multiplier 16;
- 100,000 epochs;
- mutation `1/4096`;
- 8,192 maximum reads per interaction;
- callbacks every 100 epochs;
- serial exact-pool interactions; and
- unchanged strict functional observer plus prospective-control mode.

Use six concurrent run processes (`logical CPU count - 2`) and
`NUMBA_NUM_THREADS=1`.

## Frozen usable-origin definition

A run contributes one usable origin only if:

- all manifest, assay, checkpoint, and exact-conservation integrity checks pass;
- it reaches the existing ten-callback entropy plus score-64 endpoint;
- its persisted prior-callback assay is exactly one callback earlier and passes
  evaluator/order checks; and
- after excluding every score-64 prior candidate, at least one below-64 candidate
  exists in the origin witness's zero-based rank block of width 64. If that block
  is empty, use the nonempty below-64 rank block with minimum absolute block
  distance, ties choosing the lower block.

Do not replace an unusable origin with a later callback or another run. The
acquisition gate requires at least 6/20 usable independent origins. If fewer than
six qualify, stop without a convergence claim or seed extension.

## Frozen convergence analysis

Let `n` be all usable origins if `n >= 6`. Extract the lowest-rank score-64 tape
from each first-origin assay. Represent witnesses by exact bytes, normalized
aligned-byte Hamming distance, base-2 256-bin composition JSD (divergence, no
square root), and the static ordered BFF opcode subsequence `< > { } - + . , [ ]`.

For each usable origin, the local reference pool is the frozen below-64 prior-
callback rank block above. Generate 10,000 deterministic reference replicates,
one rank-authoritative candidate per pool, using SplitMix64 constant `0xAC004`
and the same rejection-sampling uniform-index algorithm specified in AC-P003,
with key index `replicate * n + checkpoint_index`. Sampling is with replacement
across replicates.

For witnesses and each replicate, calculate median pairwise normalized Hamming
and composition JSD. Report lower-tail reference probabilities with add-one
correction and null quantiles 0.025, 0.5, and 0.975.

## Frozen composite gate

Support **prospective functional-origin structural convergence** only if:

1. all 20 campaign runs pass run-level integrity;
2. at least six usable origins are acquired;
3. one nonempty exact static opcode-signature class contains at least
   `ceil(0.8 * n)` witnesses;
4. median null Hamming distance is positive and observed median Hamming is no
   more than 75% of it; and
5. the Hamming reference-tail probability is `<= 0.01`.

All conditions are mandatory. The reference probability is conditional on the
frozen local-control model, not a general exchangeability-based significance
claim. Composition JSD, exact duplicates, structural-symbol shares, witness
abundance/rank, origin time, and block mechanics are secondary and cannot rescue
a failed gate.

## Decision ladder

- **Pass:** preregister a fresh transplantation experiment comparing members of
  the modal static class against prospectively matched below-64 tapes.
- **Valid non-pass:** conclude only that this prospective convergence criterion
  was not met and stop structural-class claims.
- **Unevaluable/integrity failure:** repair only a demonstrated implementation or
  artifact defect and rerun the frozen code; do not substitute controls, add
  seeds, or tune thresholds.

No outcome establishes heredity, maintenance, adaptation, organization, ecology,
or organism identity.
