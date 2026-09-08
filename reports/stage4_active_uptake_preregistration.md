# Stage 4 active energy-uptake mechanics preregistration

**Frozen before execution:** 2026-09-08

## Question and scope

Can execution of a tape opcode, rather than passive occupancy, control transfer
of environmental field energy into a tape while preserving the exact energy
ledger? This is a mutation-free mechanics positive control. It cannot establish
fitness, adaptation, trophic ecology, reproduction, or organism identity.

## Frozen mechanism

Reserve byte `0x3a` (`:`), which is inert under the ten-opcode BFF semantics, as
the opt-in Stage 4 uptake instruction. It remains inert whenever active uptake
is disabled. When enabled and actually reached by the instruction pointer, it
requests at most `1.0` energy unit from the active tape's local field cell,
bounded by available field energy and tape capacity. Transfer occurs before the
ordinary instruction charge, allowing the uptake instruction to bootstrap from
zero held energy. The reached instruction then pays the unchanged per-instruction
cost `0.01`; all subsequent executed bytes pay the same cost. Gross transfer and
execution dissipation remain separately auditable in the existing ledger.

Passive absorption is zero. The active feature is valid only for BFF at Stage 4
with the energy ledger enabled. Disabled configurations must preserve prior BFF
semantics and consume no additional simulation RNG.

## Seeded positive-control assay

Use a 4×4 lattice with eight occupied cells. Before each run, atomically replace
all initial tapes with the same frozen 8-byte tape:

```text
3a 00 00 00 00 00 00 00
```

The control uses byte-identical tapes; only `energy.active_uptake_enabled`
changes. This isolates mechanism enablement rather than sequence composition.
Use five matched seeds `202609210`–`202609214`, 100 ticks, eight local
interactions per tick, maximum 16 instruction reads per interaction, total field
influx 16 per tick, tape capacity 10, uptake amount 1, diffusion 0.1, field decay
0.01, and zero passive absorption. Mutation, dissolution, reseeding,
reproduction, signals, and tasks are disabled. Log every interaction and one
aggregate uptake event per tick when uptake occurs.

## Primary outcomes and gate

For each run report uptake-instruction executions, gross transferred energy,
final field/tape/dissipated energy, executed steps, and maximum relative energy
residual. The positive control passes only if:

- every enabled run records at least one reached uptake instruction and positive
  gross uptake;
- every disabled run records exactly zero uptake instructions and zero gross
  uptake;
- enabled gross uptake and final tape-held energy exceed their matched disabled
  controls in 5/5 seed pairs;
- disabled runs retain zero tape-held energy because passive absorption is off;
- all ten runs exit successfully with unchanged occupancy and zero invariant
  failures;
- every run has maximum relative energy error at most `1e-9`; and
- direct synthetic tests show transfer is bounded by local field and tape
  capacity, pays execution cost, and leaves disabled BFF execution unchanged.

## Integrity and interpretation

Do not alter the opcode, seeded tape, transfer amount, costs, seeds, horizon,
field settings, controls, or thresholds after execution starts. A pass only
establishes behaviorally accessible energy mechanics. A subsequent campaign must
separately test heterogeneous access or ecological consequences.
