# Decision after the 50,000-tick opcode-composition campaign

## Decision

**Temporal persistence is supported to 50,000 ticks. No immediate repeat or parameter sweep is necessary.**

The preregistered matched-radius campaign passed every primary criterion. The historical categorical Phase 2 acceptance NO-GO remains unchanged because this continuous metric was introduced afterward.

## Primary result

Across ten new matched seeds, radius-1 minus radius-8 pooled final-window Jensen–Shannon excess was:

- mean: **+0.005324**;
- median: **+0.004387**;
- 95% paired bootstrap interval: **[+0.003924, +0.007259]**;
- exact one-sided sign-flip: **p = 0.000977**;
- positive seed effects: **10/10**.

All ten final-window checkpoint-level mean contrasts were positive. Every radius-1 run had positive JS excess at every final-window snapshot. All 20 runs completed, conserved every symbol exactly, recorded no invariant failures, and met mechanical feasibility.

The batch completed with exit code 0 in **12 hours 43 minutes 48 seconds**, produced approximately **623 MiB** of raw artifacts, and emitted no stderr. This measured runtime supersedes the optimistic 2.6-hour projection.

## Temporal context

Radius 1:

- mean early-window JS excess: **+0.003446**;
- mean final-window JS excess: **+0.006151**;
- pooled final-window within-run p-value: `0.001` in every seed.

Radius 8:

- mean early-window JS excess: **+0.000647**;
- mean final-window JS excess: **+0.000792**;
- average positive final snapshots: **7.5/10 per run**.

The radius-8 treatment is wide but not globally mixed, so small positive local structure is plausible. The matched contrast, rather than a claim of zero radius-8 structure, is the primary evidence.

Median late occupancy declined to approximately 0.608–0.612 at 50,000 ticks but remained well above the frozen feasibility threshold and was similar between treatments.

## Replication status

The locality effect has now passed two preregistered campaigns:

| Horizon | Matched seeds | Mean radius-1 minus radius-8 effect | Exact p | Positive pairs |
|---:|---:|---:|---:|---:|
| 5,000 | 10 | +0.005173 | 0.000977 | 10/10 |
| 50,000 | 10 | +0.005324 | 0.000977 | 10/10 |

The nearly unchanged mean effect across a tenfold horizon increase argues against a short initialization transient, while still not proving persistence to 500,000 ticks.

## Supported claim

> Under baseline mutation and exact symbol conservation, radius-1 interaction reproducibly creates greater local similarity in BFF opcode composition than radius-8 interaction, and the effect persists through 50,000 ticks.

## Boundaries

The result does not establish:

- phenotype or functional equivalence;
- heredity or parent–offspring lineages;
- organism-like spatial patches;
- a monotonic radius law;
- a pass of the frozen ordered-signature block-beta endpoint;
- persistence to 500,000 ticks.

## Why another immediate sweep is not necessary

The same directional result occurred in 20/20 matched seed pairs across two horizons, with narrow positive intervals and clean mechanics. Repeating nearby radii, mutation rates, or another 50,000-tick batch would add relatively little and risks turning a clear result into parameter fishing.

## Better next questions

1. **Functional validation:** preregister whether compositionally similar neighbors also have similar execution outcomes, write footprints, or halt profiles.
2. **Spatial scale:** define a distance-decay/semivariogram endpoint and test whether similarity decays with toroidal separation on new seeds.
3. **Model development:** add an explicitly conserved birth operation with local offspring placement and neutral lineage, then test lineage-defined patch persistence.
4. **Very-long confirmation:** only if required for a future gate, run a resource-budgeted 500,000-tick matched-radius replication using the already frozen continuous metric.

The recommended next step is functional validation or explicit reproduction—not further mutation tuning.
