# Equilibrium search preregistration

## Goal

Find a parameter region where populations persist without sustained growth or decline. A finite 3,000-tick screen is used only to nominate candidates; equilibrium requires fresh-seed 10,000-tick confirmation.

## Operational criteria

For the final 1,000 ticks of a run:

- mean population is at least 30 organisms;
- normalized trend is at most 20% of the late mean per 1,000 ticks in absolute value;
- late births/deaths is between 0.85 and 1.15;
- population coefficient of variation is at most 0.35;
- no extinction occurs;
- element residual is zero and maximum absolute energy error is below 1e-6.

A candidate condition must satisfy all criteria in at least two screen seeds. Confirmation will use new seeds and a 10,000-tick horizon; no default will be changed from this exploratory search alone.

## Stage A — energy-budget screen

Matched seeds 70–72; 3,000 ticks; 300 founders; 8 founder archetypes. Cross:

- maintenance multiplier: 0.25, 0.40, 0.55, 0.70;
- resource profile:
  - `standard`: 2,600 deposits, batches 4–20;
  - `distributed`: 4,900 deposits, batches 4–20;
  - `rich`: 2,600 deposits, batches 8–40.

All other balancing values use current defaults: reproduction cost 0.50, cooldown 0.75, maturity 0.65, reproduction drive 1.25, asexual floor 0.20, and sexual floor 0.12. Independent RNG streams ensure matched seeds have identical founders across resource profiles.

Maintenance directly targets attrition; resource profiles target the observed energy block. `distributed` changes spatial access while `rich` raises batch inventory without changing deposit locations/count.

## Stage B — refinement

Select at most three conditions using the preregistered criteria, then rank failures by distance to the criterion bounds. Run selected conditions to 6,000 ticks on seeds 73–77. If every screen condition fails badly, add one midpoint based on the direction of the screen rather than claiming success.

### Exploratory amendment after Stage A

All 12 Stage A cells declined, with median late births/death below 0.57 and energy blocking between 72.6% and 86.2%. Before long refinement, run a targeted reproduction screen at maintenance 0.55 with the distributed resource profile. Cross reproduction cost {0.00, 0.10, 0.20, 0.30} with asexual floor {0.20, 0.35} on matched seeds 70–72 for 3,000 ticks. This amendment is explicitly adaptive and exploratory: cost directly changes the dominant energy gate, while the floor controls success after that gate. Nominate at most three cells for fresh-seed refinement.

The first adaptive screen still had births/death below 0.54 at the median; zero cost replaced energy blocks with body-matter and probability failures. Run a second narrow fertility screen crossing reproduction cost {0.00, 0.10, 0.20} with asexual floor {0.50, 0.70, 0.90}, again at maintenance 0.55, distributed resources, seeds 70–72, and 3,000 ticks. This tests whether higher post-gate success can reach replacement while body availability supplies density dependence.

### Model amendment: closed energy loop

A 10,000-tick zero-maintenance/zero-reproduction-cost control peaked at 1,654 organisms but declined to 237, with late births/death 0.19. Aggregate chemical energy fell from about 286k to 20k while heat rose correspondingly. Because the model had no path from heat/mana back to chemical energy, extinction remained the only asymptotic state.

Add opt-in `primary_production_rate`, default zero. A pilot that transferred a fraction of stored mana had little effect because active heat seeking and mana capacity remained bottlenecks. The final experimental mechanism passively harvests up to `primary_production_rate × reference_energy` from an organism's occupied cells into available body-molecule chemical capacity each tick. The transfer is one-to-one and conserves total energy; local heat and molecule capacity bound it. Screen rates {0.005, 0.01, 0.025, 0.05} × maintenance {0.40, 0.55, 0.70}, with reproduction cost 0.20, asexual floor 0.50, distributed resources, matched seeds 70–72, and 3,000 ticks. This is a model-extension experiment, not directly comparable to the closed-system parameter screens.

Passive-production screening found `production=0.01, maintenance=0.40` passed in 2/3 seeds. Individual lower-production/higher-maintenance runs also passed, while production ≥0.025 often produced sustained growth. Refine `0.01/0.40`, `0.005/0.70`, and interpolated `0.0075/0.55` on fresh seeds 73–77 for 6,000 ticks.

## Stage C — confirmation

Run the best Stage B condition for 10,000 ticks on fresh seeds 78–87. Report the fraction satisfying all equilibrium criteria, extinction fraction, late normalized trend, late births/deaths, population variation, species diversity, and conservation checks.

The `production=0.01, maintenance=0.40` confirmation had 0/10 extinctions and 4/10 strict passes, with median late trend −4.6% per 1,000 ticks and median births/death 0.853. Run a paired boundary check at production 0.0125 on the same seeds to test whether slightly more recycling rescues low-productivity seeds without pushing productive seeds into sustained growth. This is adaptive comparison, not an independent confirmation.
