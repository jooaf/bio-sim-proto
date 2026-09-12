# Stage 4 task-relevant signal modulation preregistration

**Frozen before execution:** 2026-09-12

## Question and scope

Does correct response to a local read-only signal causally increase future
interaction opportunity without assigning births, survival, or an external
fitness value? This is an interaction-selection mechanics gate. It does not test
demographic fitness, adaptation, communication, coordination, or organization.

## Frozen task semantics

Implement task specification `signal_uptake`. A per-cell task score starts at
zero. After a tick completes, process that tick's interaction facts in round
order; each active cell's last fact sets its next-tick score to one exactly when:

- the active cell carries the primary signal tag and the interaction executed at
  least one uptake instruction; or
- the active cell carries the secondary signal tag and the interaction executed
  zero uptake instructions.

An exact signal dispatch is required; otherwise score zero. Scores persist until
that cell acts again and are cleared when task evaluation is disabled. During the
next tick, active-cell selection weight is `1 + task_bonus * score`; partner
selection remains uniform among occupied local neighbors. Weighted draws use the
simulation RNG. With task evaluation disabled, retain the existing integer
uniform draw and consume exactly the legacy RNG sequence. Log each active
selection and save final task scores. The mechanism changes opportunity only—not
energy, tape bytes, mortality, or reproduction.

## Campaign

Use ten held-out seeds `202609300`–`202609309`, matched task-enabled and
task-disabled arms, 200 ticks, a fully occupied 4×4 torus, 64 interactions per
tick, radius 1, and one instruction per interaction. Set task bonus 3.

Seed eight correct and eight incorrect immutable tapes, alternating through
sorted cells with parity reversed on odd seeds. Correct tape:

`aa bb cc dd 3a 00 00 00 11 22 33 44 00 00 00 00`

Incorrect tape swaps handler behavior:

`aa bb cc dd 00 00 00 00 11 22 33 44 3a 00 00 00`

Use the deterministic left/right split signal field (`aabbccdd` left,
`11223344` right), exact tag dispatch, and read-only signals. Enable active uptake
and uniform total energy influx 16 with amount 1, capacity 10, instruction cost
0.01, diffusion 0.1, and decay 0.01. Disable passive absorption, signal writing,
mutation, ordinary writes, dissolution, reproduction, and reseeding.

## Frozen metrics and gate

Classify active selections by immutable tape type. Exclude tick zero from the
primary opportunity fraction to allow one scoring update. For each arm and seed
report correct-type active selections divided by all active selections over ticks
1–199. The primary endpoint is task-enabled minus matched task-disabled correct
selection fraction.

The gate passes only if:

- the paired primary difference is positive in 10/10 seeds (exact one-sided sign
  `p = 1/1024`);
- enabled correct-selection fraction is at least 0.70 in every seed;
- disabled correct-selection fraction lies in `[0.45, 0.55]` in every seed;
- every correct cell that acts after tick zero finishes with score one and every
  incorrect cell finishes with score zero in enabled arms;
- disabled arms retain all-zero scores;
- behavior classification remains exact: correct tapes respond correctly and
  incorrect tapes respond incorrectly for every dispatched interaction;
- all 20 runs retain eight tapes of each byte-exact type, succeed with zero
  invariant failures, and have maximum relative energy error at most `1e-9`.

A pass supports task-relevant modulation of interaction opportunity only. It may
justify a separately preregistered demographic consequence test. A failure
retains spatial conditional response but stops task-modulation claims. Do not
alter semantics, tapes, bonus, seeds, horizon, or thresholds after execution
starts.
