# Stage 4 structured read-only signal-response preregistration

**Frozen before execution:** 2026-09-12

## Scope

This is a new read-only branch and does not revise the failed writable-signal
campaigns. It asks whether one immutable event-driven tape executes different
handlers according to a deterministic spatial signal field. It does not test
signal writing, communication, coordination, fitness, adaptation, or
organization.

## Frozen field and genome semantics

Add deterministic `split_x` signal initialization. Cells with
`x < width / 2` receive `signals.initial_tag_hex`; remaining cells receive
`signals.secondary_tag_hex`. Width must be even and the two fixed-width tags must
differ. Initialization consumes no simulation RNG. Uniform initialization and
disabled signals remain unchanged.

Use one immutable 16-byte dual-handler tape on every cell:

`aa bb cc dd 3a 00 00 00 11 22 33 44 00 00 00 00`

With tag length 4 and stride 8, tag `aabbccdd` dispatches to the validated uptake
opcode, while tag `11223344` dispatches to a no-op. One instruction is executed,
so the non-dispatched PC-zero control also performs no uptake.

## Campaign

Use five held-out seeds `202609290`–`202609294` and three arms:

1. signals enabled with the left/right `split_x` field;
2. signals enabled with uniform `aabbccdd`; and
3. signals disabled while retaining split-field configuration.

Run a fully occupied 4×4 torus for 100 ticks with 16 local interactions per tick.
Enable active uptake and a uniform energy field with total influx 16, uptake
amount 1, capacity 10, instruction cost 0.01, diffusion 0.1, decay 0.01, and no
passive absorption. Disable signal writing, mutation, ordinary writes,
dissolution, reproduction, and reseeding. Save exact signal profiles and
per-interaction signal/uptake facts.

## Gate

Structured read-only response passes only if:

- in every split run, every recorded active interaction reads and dispatches;
  uptake occurs exactly when active-cell `x < 2` and never when `x >= 2`;
- every one of the eight left-half cells records nonzero cumulative uptake and
  every right-half cell records zero uptake in 5/5 seeds;
- uniform runs read, dispatch, and execute uptake on every interaction, with
  nonzero uptake at all 16 cells;
- disabled runs record zero reads, dispatches, and uptake at every cell;
- split final mean tape energy is positive on the left and exactly zero on the
  right; uniform final energy is positive everywhere and disabled energy is zero;
- all 15 runs retain 16 byte-identical tapes, succeed with zero invariant
  failures, and have maximum relative energy error at most `1e-9`.

A pass supports spatially conditional behavior by one fixed tape under read-only
signals. It permits a later task-relevant interaction-probability experiment but
not communication or coordination claims. A failure stops structured-signal
response work. Do not alter tags, geometry, tape, seeds, treatments, horizon, or
gate after execution starts.
