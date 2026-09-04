# Phase 2 500,000-tick acceptance run report

- **Run completed:** 2026-09-03 17:59:30 UTC
- **Frozen source commit:** `02727ecf2764dac67dd51cde510b10912dfc3007`
- **Seed:** `202608300`

## Decision

**Integrated Phase 2 acceptance: NO-GO.**

The full-duration run completed successfully and passed the complete mechanical gate. Positional byte identity was significantly greater than the fixed-position permutation null. The preregistered opcode-signature q=1 block-beta criterion was not significant, so the combined spatial criterion and integrated Phase 2 gate did not pass.

No parameter, family, radius, horizon, metric, or significance threshold is changed after observing this result.

## Execution

- Ticks completed: **500,000 / 500,000**
- Exit status: **success**
- Parameter changes: **0**
- Invariant-log entries: **0**
- stderr bytes: **0**
- Wall time: **46,089.84 seconds (12.80 hours)**
- Raw run size: approximately **117 MiB**
- Earlier projected runtime: approximately 17.61 hours

The completed run—not the earlier projection—is the acceptance evidence.

## Mechanical gate

- Minimum live tapes: **480**
- Final-window mean occupancy: **0.479**
- Longest fully occupied interval: **0 ticks**
- Final-window active-interaction fraction: **1.000**
- Final-window successful writes: **203,101,045**
- Dissolutions: **2,815**
- Successful random placements: **2,495**
- Final-window pool-composition changes: **49,999**
- Exact per-symbol conservation: **passed**
- Anti-clogging criterion: **passed**
- Anti-extinction/liveness criterion: **passed**
- Combined mechanical gate: **passed**

The exact conservation Parquet digest recorded by the run is `c7e253ed9c33460ebaae0dfee279d18a24e95f8ccb74acab23bc570dbf2176ff`.

## Frozen final-window spatial tests

Ten complete full-byte snapshots at ticks 450,000 through 495,000 were analyzed with 999 permutations. Snapshots received equal weight.

### Positional byte identity

- Observed mean: **0.009658**
- Null mean: **0.005178**
- Excess: **+0.004481**
- One-sided pooled permutation: **p = 0.001**
- Criterion: **passed**

This supports persistent local sequence similarity under exact matter conservation. It does not by itself establish organism-like patches.

### BFF opcode-signature q=1 block beta

- Observed mean beta: **10.110814**
- Null mean: **10.072280**
- Excess: **+0.038534**
- One-sided pooled permutation: **p = 0.127**
- Criterion: **failed**

The observed effect was positive but not statistically distinguishable from the preregistered null. The statistic is identifiable; this is an unsupported result, not a missing measurement.

## Parasite criterion

The separately preregistered external Spatial Stringmol control passed:

- global passive-parent parasite ancestry reached 90% in 10/10 seeds;
- local ancestry reached 90% in 0/10;
- mean paired global-minus-local final effect was 0.661862;
- 95% paired bootstrap interval was [0.566007, 0.747191];
- exact one-sided sign-flip p = 0.000977.

This validates a locality-containment mechanism in pinned Stringmol. It does not establish a viable or contained parasite in the BFF soup.

## Final criterion table

| Criterion | Result |
|---|---|
| Full 500,000-tick completion | Pass |
| Exact BFF symbol conservation | Pass |
| Liveness / anti-extinction | Pass |
| Anti-clogging | Pass |
| Positional byte-identity structure | Pass, p = 0.001 |
| Opcode q=1 block-beta differentiation | **Fail, p = 0.127** |
| External parasite positive control | Pass |
| External matched-locality containment | Pass |
| Integrated Phase 2 acceptance | **NO-GO** |

## Interpretation

The defensible conclusion is narrow:

> A long-running, exactly matter-conserving BFF spatial soup remained live and unclogged for 500,000 ticks and maintained statistically detectable local byte-level sequence similarity. The preregistered opcode-level block differentiation criterion was unsupported. Separately, locality strongly contained a validated parasite in Spatial Stringmol.

Phase 2 therefore produced useful positive mechanism evidence but did not satisfy every frozen acceptance criterion.

## Raw evidence

Raw artifacts remain outside Git at:

`sweeps/phase2_acceptance_candidate/runs/20260903T051120.391509Z_2f2d06947bae_202608300`

Compact checksums and outcomes are recorded in `reports/phase2_acceptance_run_manifest.json` and `reports/phase2_acceptance_spatial_results.csv`.
