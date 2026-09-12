# AC-R001 mechanics-derived friction validation preregistration

**Frozen before execution:** 2026-09-12

## Relationship to AC-I001

AC-I001's fixed probability grid failed and remains failed. This is a new control
design using new seeds. It does not expand the failed grid or inspect emergence.
Its sole purpose is to validate a continuous nuisance-control rate derived from
mechanics-only data before any origin experiment.

## Frozen rate derivation

For each natural-six calibration run, divide total scarcity-blocked changing
writes by total requested changing writes over 5,000 epochs. The five fractions
were 0.305101063, 0.275550276, 0.259847955, 0.310710962, and
0.258113101. The frozen derived rate is their median:

`friction_rejection_rate = 0.27555027572734614`.

No entropy, abundance, compression, or functional-emergence value was used.

## Validation

Use new seeds `202610010`–`202610014`, 32,768 tapes, 5,000 epochs,
mutation `1/4096`, multiplier 2, 8,192 reads, callbacks every 100 epochs, and two
matched arms per seed:

- natural-six zero-supply `{0,44,60,91,93,125}`;
- histogram-matched pool with the frozen symbol-independent rejection rate.

Record separate changing attempts, scarcity blocks, friction blocks, exact
conservation, and runtime. Do not inspect emergence-related artifacts.

## Gate

The derived control is validated only if all ten runs succeed with zero
conservation residual and:

- median friction blocks / median natural-six scarcity blocks lies in
  `[0.8, 1.25]`;
- at least four of five paired friction/natural block-count ratios lie in
  `[0.67, 1.5]`; and
- both arms have nonzero changing attempts in every seed.

On pass, freeze the rate in a separately preregistered held-out origin-filter
confirmation. On failure, stop demand-matched origin-filter work; do not derive
another rate from these validation seeds. Emergence inspection remains prohibited
regardless of outcome.
