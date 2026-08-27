# Organism-sim improvement screen

## Design

A paired 4 × 2 factorial screen with 40 independent runs:

- sexual success floor: disabled, 0.12, 0.30, 0.50;
- maintenance multiplier: 0.75, 1.00;
- matched seeds: 40–44;
- 2,500 ticks per run.

All other scientific parameters use the current project defaults: 300 founders, 8 founder archetypes, 48 molecules, 2,600 deposits, mutation multiplier 1, maturity multiplier 0.65, reproduction drive 1.25, reproduction cost/cooldown 0.75, and asexual floor 0.20. Reduced recording frequency changes storage cadence only; aggregate tick metrics and events remain complete.

## Motivation from new results

1. About 95% of observed deaths were attrition deaths.
2. Instrumented runs had 62–88% resource-blocked reproduction attempts.
3. Sexual floors increased sexual-event share, but high floors were confounded with deposit, mutation, maturity, and founder-lineage changes.

## Outcomes

Primary:

1. final population retention (`final / initial`);
2. replacement ratio (`births / deaths`);
3. attrition deaths per 1,000 organism-ticks.

Secondary:

- sexual-event share among successful reproduction events;
- successful births per reproduction attempt;
- reproduction resource-block rate;
- final living species;
- whether any colony forms;
- conservation error.

## Hypotheses

- H1: maintenance 0.75 improves retention and replacement by reducing attrition.
- H2: increasing the sexual floor increases sexual-event share monotonically.
- H3: very high sexual floors do not necessarily improve retention because probability is downstream of resource availability.
- H4: lower maintenance and a moderate sexual floor can improve both population retention and sexual reproduction without violating conservation.

## Analysis

Use matched-seed contrasts against the maintenance-1.0/floor-0.12 project-default control. Report means, paired differences, bootstrap 95% intervals, standardized effect sizes, and exact paired sign-flip permutation p-values. The independent seed is the inferential unit; repeated factorial cells within a seed are not independent replicates.

## Adaptive confirmation amendment

After all 40 screen runs completed, the maintenance effect was selected as the strongest primary-outcome signal. Before running further simulations, 10 additional runs were allocated to a paired confirmation at the project-default 0.12 sexual floor:

- maintenance multipliers 0.75 and 1.00;
- new seeds 45–49;
- all other parameters and the 2,500-tick duration unchanged.

This raises the total to 50 runs and gives 10 independent paired seeds for the maintenance contrast. Sexual-floor results remain screening/exploratory because they retain five independent seed blocks.
