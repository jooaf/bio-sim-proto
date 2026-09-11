# Stage 4 structured-signal exact-dispatch mechanics preregistration

**Frozen before execution:** 2026-09-11

## Question and scope

Can a local environmental signal deterministically select an exact-tagged handler
on the active BFF tape, while matched disabled and mismatched controls preserve
legacy execution? This is a mechanics-positive control only. It does not test
fitness, coordination, niche construction, adaptation, organization, or organism
identity.

## Frozen semantics

A signal field stores one fixed-width byte tag per spatial cell. The first
implementation supports deterministic uniform initialization from
`signals.initial_tag_hex`; signal setup consumes no simulation RNG. When signals
and BFF dispatch are enabled, execution reads the active cell's tag once and
scans only the active tape at block offsets `0, tag_stride, 2*tag_stride, ...`.
The first block whose `tag_length` leading bytes exactly equal the local tag is
selected, and execution begins immediately after that tag. If no block matches,
execution begins at legacy PC zero. Disabled signals perform no read or scan and
must preserve legacy trajectories. Tags do not modify tapes or the symbol pool.
Signal writes and approximate matching are deferred.

Log signal reads and successful dispatches per interaction and aggregate them per
tick. A successful dispatch means an exact match selected a handler start inside
the active tape.

## Frozen assay

Use five held-out seeds `202609260`–`202609264` and three matched arms:

1. signals enabled with uniform tag `aabbccdd`;
2. signals enabled with mismatched uniform tag `11223344`; and
3. signals globally disabled while retaining the matched configured tag.

Use an eight-byte tagged assay tape
`aa bb cc dd 3a 00 00 00` on all eight occupied cells of a 4×4 lattice. Set
`tag_length = 4`, `tag_stride = 8`, one instruction read per interaction, eight
local interactions per tick, and 100 ticks. The exact-match handler therefore
executes the already validated uptake opcode while legacy PC zero executes only
the first tag byte. Enable active uptake and the energy ledger with uniform total
influx 16, uptake amount 1, capacity 10, instruction cost 0.01, diffusion 0.1,
decay 0.01, and no passive absorption. Disable mutation, writes, dissolution,
reproduction, and reseeding.

## Gate

Exact signal dispatch passes only if:

- every matched-arm interaction records one signal read and one dispatch;
- every mismatched-arm interaction records one signal read and zero dispatches;
- every disabled-arm interaction records zero reads and zero dispatches;
- matched arms record nonzero uptake and positive final tape energy in 5/5 seeds;
- mismatched and disabled arms record exactly zero uptake and zero final tape
  energy in 5/5 seeds;
- all arms retain eight byte-identical tapes and nonzero interactions;
- all 15 runs succeed with zero invariant failures and maximum relative energy
  error at most `1e-9`.

On success, preregister a local signal-write mechanics gate before any
coordination claim. On failure, stop the signal branch and repair only the
mechanics defect. Do not change semantics, bytes, seeds, arms, horizon, or gate
after execution starts.
