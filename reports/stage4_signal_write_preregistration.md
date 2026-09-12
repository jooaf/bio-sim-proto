# Stage 4 local signal-write mechanics preregistration

**Frozen before execution:** 2026-09-12

## Question and scope

Can an executing BFF tape atomically replace an interaction partner cell's local
signal tag using declared payload bytes, without modifying tape matter or
consuming simulation RNG? This is a mechanics-positive control only. It does not
test inter-tape response, coordination, niche construction, fitness, adaptation,
or organization.

## Frozen semantics

Reserve BFF opcode `0x21` as `OP_SIGNAL_WRITE`. It is active only when
`signals.enabled` and `signals.writes_enabled` are both true. On execution, the
next `tag_length` bytes in the active tape half are the payload. If the complete
payload does not fit inside that half, the operation is invalid and makes no
change. Otherwise it atomically replaces the current interaction partner cell's
tag. The operation does not advance over payload bytes specially, modify either
tape, touch the symbol pool, or consume RNG. A signal write is counted only when
the valid replacement changes the target tag; same-value replacement is a
successful no-op but is not counted as a changed write.

The existing exact dispatch reads the active cell before instruction execution,
so a write cannot retroactively alter the current dispatch. Log per interaction:
active and partner IDs/cells, reads, dispatches, changed signal writes, and uptake
executions; retain per-tick summaries. Disabled signal writes must preserve the
S4S-I001 dispatch behavior.

## Frozen assay

Use five held-out seeds `202609270`–`202609274` and three arms:

1. matched write-enabled, initial uniform tag `aabbccdd`;
2. matched write-disabled, initial uniform tag `aabbccdd`; and
3. write-enabled but dispatch-mismatched, initial uniform tag `55667788`.

Seed all eight occupied cells of a 4×4 lattice with the immutable 16-byte tape
`aa bb cc dd 21 11 22 33 44 00 00 00 00 00 00 00`. Use tag length 4, stride 16,
one instruction per interaction, eight local interactions per tick, and 100
ticks. Disable energy, active uptake, passive absorption, mutation, ordinary tape
writes, dissolution, reproduction, and reseeding. Save exact initial and final
signal profiles.

## Gate

Local signal writing passes only if:

- matched write-enabled runs finish with tag `11223344` at all eight occupied
  cells and exactly eight changed writes in 5/5 seeds;
- matched write-disabled runs record one read and one dispatch per interaction,
  zero signal writes, and an unchanged `aabbccdd` field;
- mismatched runs record one read, zero dispatches, zero writes, and an unchanged
  `55667788` field;
- every changed write targets the recorded interaction partner cell and no empty
  cell changes;
- all arms retain eight byte-identical tapes and nonzero interactions; and
- all 15 runs succeed with zero invariant failures and exact matter closure.

On success, preregister a mixed writer/responder causal assay with held-out seeds.
On failure, retain read-only exact dispatch and stop writable-signal and
niche-construction claims. Do not alter semantics, bytes, seeds, treatments,
horizon, or gate after execution starts.
