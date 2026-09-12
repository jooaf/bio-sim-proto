# Stage 4 signal-write reachability-control preregistration

**Frozen before execution:** 2026-09-12

## Status and purpose

S4S-I002 remains a failed confirmatory gate: random half occupancy left isolated
cells that could never be interaction partners. This new experiment is a
mechanics defect-isolation positive control, not a rerun, threshold change, or
retroactive reinterpretation of S4S-I002. It asks whether the unchanged
partner-cell write semantics cover every cell when the interaction graph is
known to be fully connected.

## Frozen design

Use five new seeds `202609280`–`202609284`, a fully occupied 4×4 toroidal lattice,
100 ticks, eight local interactions per tick, radius 1, and one instruction per
interaction. Retain the exact S4S-I002 writer tape, tags, opcode `0x21`, tag length
4, stride 16, partner-cell target semantics, and three arms:

- matched write-enabled, initial tag `aabbccdd`;
- matched write-disabled, initial tag `aabbccdd`; and
- write-enabled dispatch-mismatched, initial tag `55667788`.

Energy, uptake, mutation, tape writes, dissolution, reproduction, and reseeding
remain disabled. Save exact initial and final signal profiles and all per-
interaction signal facts.

## Gate

The reachability positive control passes only if:

- each write-enabled run records exactly 16 changed writes and finishes with all
  16 tags equal to `11223344`;
- write-disabled runs read and dispatch every interaction but record zero writes
  and no field change;
- mismatched runs read every interaction, dispatch and write zero times, and have
  no field change;
- all changed targets are recorded partner cells;
- all 15 runs retain 16 byte-identical tapes, succeed with zero invariant
  failures, and preserve exact matter totals.

A pass establishes only that the unchanged write operation works over a fully
connected interaction graph. It does not erase S4S-I002's failure or establish
niche construction. It permits a separately preregistered inter-tape response
positive control under the same fully connected geometry. A failure stops the
writable-signal branch completely. No parameter or threshold changes are allowed
after execution starts.
