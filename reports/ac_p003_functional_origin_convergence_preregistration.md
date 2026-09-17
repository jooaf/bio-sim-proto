# AC-P003 independent functional-origin structural convergence preregistration

**Frozen before witness-byte inspection:** 2026-09-16

## Question and boundary

Eleven runs across AC-P001 and AC-P002 reached the unchanged strict
functional-origin endpoint, representing ten distinct initial soups because two
arms share seed `202613013`. AC-P002's resource-abundance comparison failed and
remains closed. AC-P003 asks a different retrospective, outcome-blind question:
do first score-64 witnesses converge on a shared static tape structure more
strongly than locally abundant below-64 assay candidates at the same checkpoints?

This analysis cannot rescue AC-P002, establish a resource effect, or test
maintenance. Witness bytes, opcode signatures, pairwise distances, and
composition similarities must not be inspected before this document is pushed.

## Frozen checkpoint set

Use exactly the first-origin checkpoints from these 11 independently initialized
runs:

- AC-P001 m16 seeds `202612001`, `202612003`, `202612008`, `202612009`;
- AC-P002 m16 seeds `202613001`, `202613008`, `202613010`, `202613013`,
  `202613018`; and
- AC-P002 m2 seeds `202613013`, `202613015`.

The two arms sharing seed `202613013` are separate deterministic simulations from
the same initial soup and are not independent origins. The primary analysis uses
the m16 arm by the frozen treatment-label rule and excludes the m2 member, giving
ten independent initializations and 45 witness pairs. A sensitivity analysis
replaces the m16 member with the m2 member. Both are retained descriptively. No
later qualifying callback or alternate score-64 candidate may replace the first
checkpoint witness.

## Frozen witness extraction and integrity

For each run, verify published artifact checksums, exact conservation, the
manifest's first-origin epoch, the contemporaneous assay, and the checkpoint's
saved witness. Select the lowest abundance rank scoring 64 in that first assay,
which must equal the persisted checkpoint witness.

Represent each 64-byte witness by:

- its exact bytes;
- normalized byte Hamming distance: unequal aligned byte positions divided by 64,
  with no sequence alignment;
- byte-composition Jensen–Shannon divergence: normalized 256-bin byte histograms,
  base-2 logarithms, and no square root; and
- static ordered BFF opcode subsequence, retaining only bytes
  `< > { } - + . , [ ]` in tape order. This signature is not itself a functional
  architecture because removed spacing and data bytes can affect execution.

Any missing, corrupt, non-score-64, or inconsistent checkpoint fails integrity;
do not replace it.

## Frozen local null

For each origin checkpoint, define a local below-64 pool from the authoritative
saved rank ordering of the same top-1,024 assay candidates:

1. preserve each candidate's original assay rank and evaluator result; never
   filter then rescore or renumber candidates;
2. exclude every candidate scoring 64;
3. use distinct assay rows in the witness's zero-based rank block of width 64;
4. if that block is empty, use the nonempty rank block with minimum absolute
   block distance, ties choosing the lower block; and
5. if no below-64 candidate exists in the assay, declare the analysis unevaluable.

Generate 10,000 deterministic reference replicates over the ten primary
checkpoints. Pools are ordered by saved rank. For replicate `r` and zero-based
checkpoint index `i`, set `base = 0xAC003 XOR splitmix64(r * 10 + i)`. Draw
`splitmix64(base + k)` for `k = 0,1,...` until the unsigned result is below
`floor(2^64 / n) * n`, then select `draw mod n` from that checkpoint's pool.
Thus selection is uniform; each replicate samples one row per checkpoint, and
sampling is with replacement across replicates. Simulation RNG is not used.

For observed witnesses and each replicate, calculate the median of all 45
pairwise normalized Hamming distances and median pairwise composition JSD. The
reported values are deterministic Monte Carlo tail probabilities under this
rank-local reference model, not general exchangeability-based significance
claims. For each metric, use
`(1 + count(null_median <= observed)) / 10001`; Hamming is primary and JSD is
secondary. Report null quantiles 0.025, 0.5, and 0.975.

## Frozen primary gate

Support **independent functional-origin structural convergence** only if all are
true:

1. all 11 checkpoints pass integrity and every primary local pool is nonempty;
2. one nonempty exact opcode-signature class contains at least 8/10 primary
   witnesses;
3. the median null Hamming distance is positive and observed median pairwise
   normalized Hamming distance is no more than 75% of it; and
4. the one-sided Hamming reference-tail probability is `<= 0.01`.

All conditions are mandatory. The opcode criterion and Hamming/null criterion
are one composite primary gate, not alternative opportunities to claim a pass.

## Secondary and sensitivity reporting

Report exact-tape duplicate classes, opcode-signature classes, pairwise Hamming
and composition-JSD matrices, canonical structural-symbol shares for the frozen
set `{0,44,60,91,93,125}`, witness ranks and abundances, null quantiles, and the
composition-JSD reference-tail probability. Repeat the primary calculations with
the m2 seed-`202613013` witness replacing its m16 counterpart; use the same
8/10 modal-signature threshold and recompute the ten-checkpoint null. This
sensitivity analysis cannot override the primary decision.

## Decision ladder

- **Pass:** preregister a fresh functional transplantation assay testing the modal
  structural class against matched nonfunctional checkpoint tapes. Do not claim
  maintenance or adaptation from convergence alone.
- **Valid non-pass:** conclude only that the preregistered convergence criterion
  was not met and stop convergence/class claims. A descriptive catalog may be
  retained, but do not tune distance metrics, opcode definitions, null pools, or
  thresholds.
- **Unevaluable:** if integrity or local-control availability fails, repair only
  a demonstrated artifact/implementation defect and rerun this frozen analysis;
  do not classify missing evidence as structural diversity.

A pass supports only convergent structure among functional witnesses in this BFF
artificial chemistry. It does not establish heredity, long-term maintenance,
adaptation, ecology, organization, or organism identity.
