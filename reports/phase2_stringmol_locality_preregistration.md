# Phase 2 Stringmol matched-locality preregistration

**Frozen before local-treatment execution:** 2026-08-26

## Valid positive control

The ten-seed global Stringmol control passed every preregistered criterion:

- passive-parent parasite ancestry reached 90% in 10/10 seeds;
- exact R exceeded its inoculum in 10/10;
- populations persisted in 10/10;
- all provenance and explicit-loader checks passed.

The local treatment is therefore valid to launch.

## Fixed matched comparison

Reuse global-control seeds **202608320–202608329** and the identical:

- 140 canonical host molecules;
- 10 exact R parasites;
- 40×40 toroidal grid;
- fixed host block and centered parasite stripe;
- 10,000-step horizon;
- mutation 0.0002;
- decay 0.0005;
- ALXII matrix;
- source commit and patch series;
- report cadence and offline family definitions.

Global treatment already completed:

- interaction radius 0;
- offspring-placement radius 0.

Local treatment changes only:

- interaction radius **1**;
- offspring-placement radius **1**.

Both mechanisms are changed together because the primary biological contrast is globally mixed versus locally interacting and locally dispersing chemistry. The two radius fields remain independently configurable; a later 2×2 mechanistic factorial may separate them, but cannot replace this primary comparison.

## Primary parasite family

Use the same transitive passive-parent ancestry rooted at initial exact R species 2. This follows Stringmol's inherited passive label. Exact R abundance remains secondary.

For each seed and treatment, report:

- maximum ancestry fraction;
- final ancestry fraction;
- whether ancestry ever reaches 90%;
- maximum and final exact R abundance/fraction;
- total population persistence;
- family species count.

## Focused paired effect

Primary paired effect:

```text
global final ancestry fraction − local final ancestry fraction
```

Report:

- all ten seed differences;
- mean and median paired difference;
- 95% percentile bootstrap interval over matched seeds, using 10,000 resamples and analysis seed 20260826;
- exact one-sided paired sign-flip p-value for a positive global-minus-local mean.

Secondary paired effects use maximum ancestry fraction and final exact R fraction.

## Containment decision

The external Stringmol containment control passes only if all hold:

1. the 95% paired bootstrap interval for global-minus-local final ancestry excludes zero on the positive side;
2. local ancestry does **not** reach 90% in at least 8/10 seeds;
3. global ancestry reaches 90% in at least 8/10 seeds (already 10/10);
4. local populations persist in at least 8/10 seeds;
5. all local processes exit successfully with matching source/config/patch hashes and no loader fallback warning.

Failures remain in the denominator. Maximum abundance alone cannot override a failed final or 90%-containment criterion.

## Interpretation boundary

A pass demonstrates locality-based parasite containment in pinned Spatial Stringmol, an independently established automata chemistry. It supports the general Phase 2 experimental mechanism. It does not retroactively make the rejected BFF parasite viable and does not show containment in the conserved BFF substrate.

A failure is reported without changing radius, horizon, mutation, inoculum, ancestry, or thresholds.
