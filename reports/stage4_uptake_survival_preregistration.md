# Stage 4 active-uptake survival consequence preregistration

**Frozen before execution:** 2026-09-11

## Question and scope

Does execution-mediated uptake cause differential persistence under existing
starvation mortality in a mixed immutable population? This is a bounded causal
survival test, not a test of adaptation, competition, reproduction,
organization, self-maintenance, or organism identity.

## Frozen design

Use the already validated static patch generator with correlation length 2
cells and log-contrast 1.0. This near-interaction scale is fixed by geometry,
not selected from S4-I003 outcomes. Use held-out seeds `202609240`–`202609249`.
For each seed run matched globally uptake-enabled and feature-disabled arms.

Each run uses a 16×16 toroidal lattice, 50% fixed initial occupancy, 500 ticks,
128 local interactions per tick, and 16 instruction reads. Alternate uptake and
control tapes through the deterministic seeded occupied-cell order, reversing
type phase on odd seeds. Uptake tapes are `3a 00 00 00 00 00 00 00`; controls
are `3b 00 00 00 00 00 00 00`. Mutation, writes, reproduction, reseeding, and
passive absorption remain disabled.

Use total influx 16, uptake amount 1, capacity 10, instruction cost 0.01,
diffusion 0.02, decay 0.01, and `min_to_interact = 0`. Enable dissolution only
for starvation: threshold 50 consecutive zero-energy ticks; set inert threshold
10,000 ticks, dissolve rate zero, and stop tick zero. Log tape state every 10
ticks and all dissolution events. Save the exact influx profile and immutable
initial type assignment.

## Frozen metrics and gate

Type survival fraction is final count divided by its initial count of 64. The
primary endpoint is enabled-arm uptake survival fraction minus enabled-arm
control survival fraction for each seed, with an exact one-sided sign test.

A causal survival consequence passes only if:

- the primary difference is positive in 10/10 seeds (`p = 1/1024`);
- enabled uptake-tape survival is at least 0.8 in every seed;
- enabled control-tape survival is zero in every seed;
- both types have zero survival in every feature-disabled arm;
- enabled runs retain at least two tapes, nonzero interactions after tick 100,
  and nonzero uptake;
- every dissolution is attributed to starvation;
- tape bytes remain type-consistent, all 20 runs succeed with zero invariant
  failures, and maximum relative energy error is at most `1e-9`.

The globally disabled arm controls the opcode label while within-enabled mixed
types control shared field and scheduler exposure. A pass supports only that
active uptake causes survival under this configured starvation regime. On pass,
a later preregistration may test resource-coupled birth or frequency change; on
failure, retain structured access as mechanics only and stop demographic claims.
Do not alter seeds, mechanics, thresholds, horizon, or endpoints after execution
starts.
