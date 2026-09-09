# Stage 4 mixed-population differentiated energy-access preregistration

**Frozen before execution:** 2026-09-09

## Question and scope

Does the S4-E001 execution-mediated uptake mechanism create differentiated
energy access between tape types coexisting in one uniform environment? This is
a mutation-free access assay. It does not test fitness, adaptation,
reproduction, mortality, trophic ecology, or organism identity.

## Frozen tape types and placement

Use eight occupied cells on the same 4×4 lattice as S4-E001. Seed four copies of
each immutable 8-byte type:

- uptake type: `3a 00 00 00 00 00 00 00`;
- one-byte matched control: `3b 00 00 00 00 00 00 00`.

Byte `0x3b` is inert under BFF. Mutation, writes, dissolution, reseeding, and
reproduction are disabled, so content type is immutable. For each seed, sort the
eight initially occupied flat indices and assign alternating types. Even seeds
assign uptake to positions 0, 2, 4, and 6 in that order; odd seeds reverse the
assignment. Record type, tape ID, flat index, cell, exact bytes, and SHA-256 in a
protocol file before execution.

## Matched campaign

Use held-out seeds `202609220`–`202609224`, 200 ticks, and two globally matched
arms:

1. active uptake enabled;
2. active uptake disabled.

Both arms retain the same mixed tape bytes and placement. Use eight local
interactions per tick, 16 instruction reads per interaction, total uniform field
influx 16 per tick, tape capacity 10, uptake amount 1, instruction cost 0.01,
diffusion 0.1, field decay 0.01, zero passive absorption, and
`min_to_interact = 0`. Log all interactions and every tape each tick. All other
settings match S4-E001.

## Endpoints and gate

For each run report by immutable type:

- final mean tape-held energy at tick 199;
- mean tape-energy area under the 200 logged snapshots;
- interactions as active first tape, funded executed steps, and gross campaign
  uptake;
- final field, tape, and dissipated energy and maximum relative ledger error.

The primary endpoint is the within-run uptake-minus-control difference in final
mean tape energy in the enabled arm. Report all five paired differences and the
exact one-sided sign test.

The mixed-access gate passes only if:

- the enabled-arm primary difference is positive in 5/5 seeds and its exact
  one-sided sign-test `p <= 0.05`;
- enabled uptake-minus-control energy-area difference is positive in 5/5 seeds;
- enabled uptake tapes have positive final mean energy and funded steps in 5/5
  seeds, while coexisting control tapes have exactly zero final energy and zero
  funded steps;
- every enabled run records positive gross uptake;
- disabled arms record exactly zero gross uptake, zero final tape energy, and
  zero funded steps for both tape types;
- all ten runs exit successfully with eight tapes, unchanged type counts, and
  zero invariant failures; and
- maximum relative energy error is at most `1e-9` in every run.

## Integrity and interpretation

Do not alter tape bytes, placement, labels, seeds, horizon, energy settings,
controls, endpoints, or thresholds after execution starts. A pass establishes
coexisting type-specific energy access under a uniform field. It does not show
that access affects survival or reproduction. Structured-field and ecological
consequence tests require separate preregistration.
