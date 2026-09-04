# Phase 2 opcode-beta mechanistic follow-up preregistration

**Frozen before execution:** 2026-09-04

## Status and scope

The completed 500,000-tick acceptance run remains a NO-GO because ordered-opcode q=1 beta at 8×8 blocks was unsupported (`p = 0.127`). The analyses and treatments below are new mechanistic follow-ups. They cannot retroactively change that decision.

Post-decision exploratory diagnosis found that 76.7% of ordered opcode labels were unique and 68.7% of tapes carried singleton labels. It also suggested stronger structure at smaller blocks and with coarser opcode-presence labels. This inspection is disclosed because it selected the follow-up hypotheses and 2×2 scale.

## Questions

1. Does reducing background mutation make exact ordered opcode signatures less private under local interaction?
2. Under lower mutation, does radius-1 interaction produce stronger cell-scale ordered-opcode differentiation than radius 8?
3. Are any effects accompanied by positional byte similarity and preserved mechanical feasibility?

## Frozen factorial

- interaction radius: **1, 8**;
- mutation rate: **1/16,384, 1/4,096**;
- matched unseen seeds: **202609050–202609059**;
- ten seeds per cell, **40 total runs**;
- horizon: **5,000 ticks**;
- 32×32 torus, 80% initial fill;
- 512 attempted interactions per tick;
- dissolution and reseed: 10⁻⁵ each;
- tape length 64, BFF budget 8,192;
- full-byte snapshots every 500 ticks;
- energy, tasks, signals, maximum-age death, and starvation death disabled.

Only radius and mutation vary. All random failures, extinctions, and invariant failures remain in the denominator.

## Primary outcomes

Use the last complete full-byte snapshot in the final 10% of each run (intended tick 4,500).

### H1: mutation and label recurrence

At radius 1, define per run:

```text
unique fraction = number of distinct ordered-full opcode signatures / occupied tapes
```

Primary paired effect:

```text
baseline-mutation unique fraction − low-mutation unique fraction
```

Prediction: positive. Test with an exact one-sided paired sign-flip test across ten seeds.

Also report the singleton-tape fraction, but it is supportive rather than a separate primary test.

### H2: locality under lower mutation

For exact ordered-full opcode signatures, compute q=1 multiplicative beta in nonoverlapping **2×2 blocks**. Within each run, estimate beta excess relative to 999 fixed-occupancy label permutations using analysis seed `20260904 + seed offset`.

Primary paired effect at mutation 1/16,384:

```text
radius-1 beta excess − radius-8 beta excess
```

Prediction: positive. Test with an exact one-sided paired sign-flip test across the same ten seeds.

The 2×2 block was selected after exploratory inspection and is valid only as this new follow-up endpoint.

## Multiplicity

H1 and H2 form one two-test primary family. Apply Holm's step-down procedure at familywise alpha 0.05:

1. order the two raw p-values;
2. the smaller must be ≤ 0.025;
3. if it passes, the larger must be ≤ 0.05.

Both hypotheses must pass Holm correction for the joint mechanistic result to be called supported. Report raw p-values and effects regardless.

## Frozen secondary outcomes

These do not alter the primary decision:

- ordered-full q=1 beta excess at the old 8×8 scale;
- opcode-presence q=1 beta excess at 2×2 blocks;
- radius-1 positional byte-identity excess;
- within-run permutation p-values;
- final occupancy, writes, dissolution, placement, conservation, and invariant counts;
- the mutation × radius interaction in paired effect sizes.

The opcode-presence label is a ten-bit vector indicating whether each BFF instruction appears anywhere on the tape. It is a coarse syntax-capability proxy, not a phenotype.

## Mechanical requirements

A run is mechanically feasible only if it:

- exits successfully;
- has exact per-symbol conservation;
- records zero invariant failures;
- maintains at least 25% mean occupancy in the final 10%;
- has nonzero final-window active interactions and successful writes;
- records both dissolution and successful random placement.

If fewer than 8/10 low-mutation radius-1 runs are mechanically feasible, H1/H2 statistics are still reported but the treatment is not considered operationally viable.

## Stopping and interpretation rules

- Invariant failure stops and fails that run.
- No seed replacement or campaign extension after outcomes are inspected.
- Do not tune mutation further from these results.
- Do not substitute opcode presence for ordered-full signatures in H1/H2.
- Do not call a positive within-run p-value evidence for the paired treatment contrast.
- This campaign estimates mechanisms over 5,000 ticks; it cannot pass a 500,000-tick gate.
- A successful result motivates a later model/protocol decision, not a rewritten Phase 2 verdict.
