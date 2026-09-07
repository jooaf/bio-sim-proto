# Stage 3 neutral lineage-patch persistence decision

## Decision

**Categorical NO-GO under the preregistered integrated gate.**

The stopped-birth arm retained a strong lineage patch, but the continued-birth positive-control arm violated the frozen long-run occupancy feasibility criterion in 9/10 runs.

## Stopped-birth persistence evidence

At tick 19,900, 9,900 ticks after birth stopped:

- mean neutral-family neighbor excess `+0.045945`;
- median `+0.047112`;
- 95% bootstrap interval `[+0.042071, +0.049567]`;
- exact one-sided sign-flip `p = 0.000977`;
- positive and individually significant outcomes in 10/10 runs;
- median retention ratio `0.999` relative to the switch checkpoint;
- 10/10 mechanically feasible stopped runs.

Mean exact-root final excess was `+0.050286`, supporting that the result is not solely a modulo-family collision artifact.

## Failed integrated prerequisite

With birth continuing:

- mean final family excess rose to `+0.080230`;
- all 10 final tests were positive and significant;
- median occupancy reached `0.971`;
- only 1/10 runs remained within the frozen occupancy ceiling of 0.95.

The continued arm therefore clogged under the declared 20,000-tick feasibility definition. Because the preregistration required at least 8/10 feasible runs in each arm, the integrated persistence gate fails despite the stopped-arm statistical result.

## Interpretation

The data support a narrower descriptive conclusion:

> Once created, neutral lineage spatial association remained almost unchanged for 9,900 ticks after scheduled birth stopped under ongoing interactions, mutation, dissolution, and random placement.

This longevity is not demonstrated self-maintenance. Slow lineage turnover can preserve labels without an organization actively rebuilding itself.

## Integrity decision

Do not lower the occupancy ceiling, reduce the continued birth rate, move the switch tick, or rerun nearby parameters to rescue this gate. The no-clogging failure is retained. Future persistence work must use a newly motivated population-regulation mechanism, not post-hoc tuning of this campaign.
