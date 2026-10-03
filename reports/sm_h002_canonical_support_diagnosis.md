# SM-H002 canonical SUPPORT positive-control diagnosis

**Date:** 2026-10-02  
**Status:** bounded post-hoc diagnosis; the frozen SM-H002 decision remains unevaluable

## Finding

The failed canonical SUPPORT control was not a different molecular environment
from canonical SELF. For seed `202624012`, canonical EXACT_SELF and
EXACT_SUPPORT had:

- byte-identical simulator configs;
- identical initial material;
- byte-identical inventories for all 161 output files; and
- identical native totals: 804 productive births, 196 serial source births,
  source depth 3, and 5 late renewing descendants.

The only difference was observational analysis. SELF assigned all 140 identical
canonical founders to the candidate cohort. SUPPORT assigned IDs 0–69 to
`candidate` and IDs 70–139 to `support`, although both sets had the same canonical
sequence, label, positions, chemistry, and simulator behavior.

The identical native trajectory was partitioned as follows:

| Observational cohort | Productive births | Late productive births | Renewing descendants | Serial births | Depth | Late renewing descendants |
|---|---:|---:|---:|---:|---:|---:|
| candidate IDs 0–69 | 314 | 143 | 5 | 25 | 2 | 0 |
| support IDs 70–139 | 490 | 283 | 17 | 171 | 3 | 5 |
| combined/native | 804 | 426 | 22 | 196 | 3 | 5 |

The frozen SUPPORT positive control required the arbitrarily designated candidate
half itself to contain at least five late renewing descendants. All five late
renewals happened to descend through the observational support half, so the
control failed despite the molecular trajectory being exactly the passing SELF
trajectory.

## Interpretation boundary

This diagnoses an **observational cohort-partition sensitivity in the positive
control**, not a biological absence of canonical renewal and not a simulator or
integrity defect. It does not reverse SM-H002: the preregistration explicitly made
that candidate-cohort SUPPORT criterion mandatory, so SM-H002 remains
unevaluable. It also does not rescue the 10/15 SELF or 7/15 SUPPORT panel counts.

A new experiment should not require an arbitrary half of a molecularly identical
canonical population to satisfy a rare late-renewal count. A prospective
replacement should use whole-population canonical renewal as the assay-positive
control, retain candidate-cohort endpoints for genuinely distinct
candidate-versus-canonical mixtures, use multiple unseen seeds per genotype, and
keep genotype/context conclusions separate.
