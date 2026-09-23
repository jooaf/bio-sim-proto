# AC-P006 composition-preserving functional-witness transplantation preregistration

**Frozen before implementation and execution:** 2026-09-17

## Motivation and claim boundary

AC-P005 confirmed composition-level convergence among strict functional-origin
witnesses relative to immediate pre-origin controls. AC-P004 simultaneously
rejected one shared static opcode/Hamming class. AC-P006 asks whether the exact
ordering of bytes in independently originated score-64 witnesses produces
realized amplification in fresh conserved soups beyond a deterministic control
with exactly the same 64-byte composition.

This is not a test of the cause of compositional convergence itself. A pass would
show that composition alone is insufficient and that the exact witness sequence
has a realized propagation advantage under the tested transplantation regime.

## Frozen biological replicates

Use exactly the ten usable AC-P005 first-origin witnesses, ordered by source seed:

`202615001, 202615004, 202615006, 202615007, 202615008, 202615011,
202615014, 202615015, 202615017, 202615018`.

Each source witness contributes one biological replicate. Extract the persisted
lowest-rank score-64 first-origin witness and verify its source checkpoint before
building inocula. Pair witness index 0–9 with fresh recipient seed
`202616000 + index`.

## Frozen composition-preserving control

For each witness, create one deterministic shuffled control by Fisher–Yates over
all 64 byte positions. For descending position `i = 63..1`, compute
`draw = splitmix64(0xAC006 XOR splitmix64(index * 64 + i))`, choose
`j = draw mod (i + 1)`, and swap positions `i` and `j`.

The shuffled tape must have exactly the same 256-bin byte histogram and must
differ bytewise from its witness. Before any simulation run, evaluate it once
with the unchanged functional evaluator at seed 0. Every shuffled control must
score below 64. If any control is unchanged, composition-mismatched, or scores
64, declare the control construction invalid and stop without generating an
alternative shuffle.

## Frozen recipient construction

For each recipient seed, generate the existing deterministic 32,768-tape random
soup. Select 32 distinct replacement indices using the existing deterministic
shuffle order at epoch-domain constant `0xAC006 + index`; use the same indices in
both paired arms. Replace those tapes with 32 exact copies of either the witness
or its shuffled control.

Because each pair's inocula have identical byte composition and modifies the same
background indices, paired initial tape histograms and histogram-matched
multiplier-16 conserved pools must be byte-for-byte identical. Save and verify
both initial soups before execution. Record actual initial exact-target count,
which must be at least 32.

## Frozen simulation

Run 20 paired fresh-soup simulations:

- 32,768 tapes, length 64;
- histogram-matched pool multiplier 16;
- 10,000 epochs;
- mutation `1/4096`, 8,192 maximum reads;
- callbacks every 100 epochs;
- exact serial conserved-pool interactions;
- no functional-origin selection or prospective-control mode; and
- six concurrent run processes with `NUMBA_NUM_THREADS=1`.

Add opt-in exact target-tape tracking that records target abundance at each
callback without altering soup, pool, counters, ordering, or RNG. The tracked
tape bytes and tracker version are part of the run configuration and run ID.
Disabled tracking must preserve legacy trajectories.

## Frozen endpoints

For each run calculate:

- initial exact-target count;
- maximum exact-target count;
- final exact-target count; and
- post-transient mean exact-target abundance over callbacks at epochs `>= 1001`,
  divided by initial exact-target count (`mean_fold_abundance`).

A witness replicate is established for the positive-control gate only if its
maximum exact count is at least 64 and its final exact count is at least 16.
A shuffled replicate is spuriously established by the same definition.

## Frozen composite gate

Support **realized sequence-specific propagation beyond composition** only if all
are true:

1. all 20 runs finish with exact conservation, verified paired initial
   composition, truthful target logs, and complete artifacts;
2. at least 5/10 witness arms meet the establishment definition;
3. no more than 2/10 shuffled arms meet it;
4. witness `mean_fold_abundance` exceeds its paired shuffle in at least 9/10
   replicates, with the exact one-sided paired sign probability `<= 0.05`; and
5. the median across pairs of
   `(witness mean_fold_abundance + 1e-12) /
   (shuffle mean_fold_abundance + 1e-12)` is at least 2.

All conditions are mandatory. Report exact paired values and the exact sign
probability; nonsignificance is not equivalence.

## Secondary outcomes

Report time to first abundance above initial, abundance trajectories, block
mechanics, entropy trajectories, witness/control functional scores, Hamming
change caused by shuffling, and runtime. These cannot rescue a failed gate.

## Decision ladder

- **Pass:** support sequence-specific realized propagation for composition-
  preserving transplants in fresh conserved soups; separately preregister any
  long-term maintenance or competition assay.
- **Valid non-pass:** retain score-64 functional proxy and composition convergence
  but conclude this transplantation regime did not establish realized sequence-
  specific propagation; stop this branch.
- **Unevaluable/integrity failure:** repair only a demonstrated implementation or
  artifact defect and rerun frozen code; do not regenerate shuffles, replace
  witnesses, or tune inoculum/horizon.

No result establishes organisms, adaptation, ecology, organization, or open-ended
heredity.
