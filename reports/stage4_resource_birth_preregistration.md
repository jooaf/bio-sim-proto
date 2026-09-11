# Stage 4 resource-coupled birth and frequency-change preregistration

**Frozen before execution:** 2026-09-11

## Question and scope

Does energy obtained by execution-mediated uptake fund conserved exact-copy births
and thereby increase uptake-type frequency? This closes the bounded causal chain
from behavior to resource access to a demographic consequence. Scheduled
simulator-mediated cloning is not endogenous self-reproduction, adaptation,
competition, or organism identity.

## Frozen design

Use ten held-out seeds `202609250`–`202609259`. For each seed and each initial
uptake count 8, 32, and 56 out of 64 occupied tapes, run matched globally
uptake-enabled and feature-disabled arms (60 runs total). The three initial
frequencies are 0.125, 0.5, and 0.875.

Use the validated static patch field with correlation length 2 cells and
log-contrast 1.0, fixed by interaction geometry rather than selected outcomes.
The 16×16 toroidal lattice starts at 25% occupancy and runs 500 ticks with 128
local interactions and 16 instruction reads per tick. Uptake tapes are
`3a 00 00 00 00 00 00 00`; controls are
`3b 00 00 00 00 00 00 00`. Initial type assignment ranks occupied cells by
SHA-256 of `seed:flat_index` and assigns uptake to the first frozen count, so
matched arms are byte-identical and assignment consumes no simulation RNG.

Enable scheduled vacancy-first exact cloning at rate 0.05, radius 1, maximum four
births per tick, parent energy cost 5, and zero offspring energy. Use total
influx 16, uptake amount 1, capacity 10, instruction cost 0.01, diffusion 0.02,
decay 0.01, and `min_to_interact = 0`. Disable dissolution, passive absorption,
mutation, writes, reseeding, and exact-copy-triggered birth. Save the exact
profile and complete initial assignment. Log birth lineage and tape state every
10 ticks.

## Frozen metrics

Classify every descendant by its immutable root tape type. For each run report:

- initial and final uptake frequency;
- uptake- and control-parent successful births;
- attempted and energy-blocked births;
- final occupancy and type counts;
- interaction and uptake activity;
- type consistency and maximum relative energy residual.

The primary endpoint is enabled-arm final uptake frequency minus its frozen
initial frequency over all 30 seed-by-frequency cases. Report all differences
and an exact one-sided sign test. Disabled-arm change and matched enabled-minus-
disabled frequency difference are mandatory controls.

## Gate

Resource-coupled frequency change is supported only if:

- primary frequency change is positive in all 30 cases (exact one-sided sign
  `p = 2^-30`);
- matched enabled-minus-disabled final frequency is positive in all 30 cases;
- each of the three initial-frequency treatments has median enabled frequency
  increase at least 0.05;
- every enabled run records at least 16 successful births and at least one uptake
  execution, and at least 95% of births have uptake-type parents;
- every disabled run records zero births, unchanged type frequency, and at least
  one energy-blocked birth attempt;
- reproduction is the only population-changing mechanism, all descendants stay
  type-consistent, and no tape byte changes type;
- all 60 runs succeed with zero invariant failures and maximum relative energy
  error at most `1e-9`.

A pass supports scheduled resource-coupled reproduction and frequency change
only. A failure retains the causal starvation-survival result and stops claims
that uptake drives reproduction. Do not change seeds, assignment, treatments,
mechanics, horizon, endpoints, or thresholds after execution starts.
