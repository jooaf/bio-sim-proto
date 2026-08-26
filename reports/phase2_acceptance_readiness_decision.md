# Phase 2 research status and acceptance-readiness decision

**Decision date:** 2026-08-26

## Decision

**NO-GO for the integrated Phase 2 acceptance campaign.**

The spatial mechanics, conservation, liveness operating point, and radius effect are ready. The required parasite positive control is not viable, so a local-versus-large-radius containment result would be invalid. The 500,000-tick treatment has not started and Phase 2 has not passed.

A standalone 500,000-tick liveness run is technically feasible and scientifically useful, but it cannot by itself close Phase 2 while the parasite criterion remains part of the gate.

## Research completed

### Campaign inventory

| Campaign | Runs | Main purpose | Result |
|---|---:|---|---|
| 8×8 liveness operating-point grid | 27 | Select dissolution/reseed balance | 18/27 mechanically feasible; selected 10⁻⁵ / 10⁻⁵ |
| 32×32 liveness confirmation | 3 | Confirm selected rates at scale | 3/3 feasible |
| 32×32 radius pilot | 20 | Compare radii 1, 2, 4, 8 | 20/20 feasible; radius effect detected |
| Parasite strict mechanics | 1 | Test exact copying without mutation | Passed; exact count rose 16→32 maximum |
| Parasite content-family viability | 5 | Test large-radius invasion with mutation | Failed preregistered rule |
| Parasite neutral-ancestry diagnostic | 5 | Check whether content metrics missed descendants | Failed preregistered rule |
| **Total** | **61** |  |  |

Every run exited successfully, preserved all 256 symbol totals exactly, and recorded zero invariant failures.

## Finding 1 — a live, partially empty operating point exists

The preregistered 9-treatment liveness grid selected:

- per-tape spontaneous dissolution: **10⁻⁵ per tick**;
- per-free-cell reseed: **10⁻⁵ per tick**.

At 32×32 and 5,000 ticks:

- 3/3 matched seeds passed mechanical liveness;
- median final-window occupied fraction was **0.767**;
- minimum population across seeds was **780 tapes** of 1,024 cells;
- 131 dissolutions and 31 placements occurred across the three runs;
- no clogging, extinction, conservation drift, or invariant failure occurred.

This operating point is frozen for any future 32×32 acceptance run.

## Finding 2 — locality changes sequence similarity

The original exact-hash spatial statistic was non-identifiable because every final tape hash was unique. This was reported before the radius campaign. A pre-campaign addendum froze positional byte-identity excess and BFF-opcode-signature beta diversity.

Across five unseen matched seeds per radius:

| Radius | Median byte-identity excess | Median opcode q=1 beta excess |
|---:|---:|---:|
| 1 | 0.005018 | 0.050300 |
| 2 | 0.016375 | 0.125999 |
| 4 | 0.008015 | 0.081421 |
| 8 | 0.001459 | -0.037983 |

Results:

- byte-identity excess was positive in **20/20 runs**;
- every within-run 999-permutation p-value was **0.001**;
- radius 1 exceeded radius 8 in **5/5 matched seeds**;
- mean radius-1 minus radius-8 effect was **0.004050**;
- exact one-sided paired sign-flip **p = 0.03125**;
- radius 2 was strongest, so the response was **nonmonotonic**;
- the opcode-signature radius-1 minus radius-8 contrast was inconsistent (**p = 0.125**).

The defensible claim is narrow: interaction radius affects local sequence similarity in this short pilot. The pilot does not establish a monotonic law, organism-level patches, or the full beta-diversity criterion.

## Finding 3 — the parasite positive control is invalid

A naturally emerged 64-byte BFF copier was frozen from a pre-Phase-2 checkpoint using a deterministic abundance/function/tie-break rule.

Strict mutation-free mechanics passed:

- 16 exact inserted copies;
- maximum exact count: **32**;
- maximum near-family fraction: **0.627**.

Under the actual mutation rate at large radius, the bounded content-family pilot failed:

- family increased in **3/5** seeds, below the required 4/5;
- only **1/5** reached 50%;
- exact, near-seed, and opcode-family counts were zero at the final snapshot in all five seeds.

A separately preregistered neutral-ancestry diagnostic also failed:

- ancestry increased in **1/5** seeds;
- ancestry reached 50% in **0/5** seeds;
- maximum ancestry fraction was **0.099**;
- final ancestry fractions ranged approximately **0.074–0.095**.

Therefore the candidate is rejected. Radius 1 cannot be credited with containment because the required large-radius treatment does not support invasion.

## Readiness by criterion

| Phase 2 criterion | Status | Evidence |
|---|---|---|
| Exact conserved matter | **Ready** | Zero residual in all 61 runs |
| Occupancy and lifecycle mechanics | **Ready** | Zero invariant failures |
| Anti-clogging and anti-extinction semantics | **Ready** | 32×32 confirmation passed 3/3 |
| Pilot-selected dissolution/reseed point | **Frozen** | 10⁻⁵ / 10⁻⁵ |
| Spatial sequence structure | **Pilot support** | Byte excess positive 20/20; matched radius effect |
| Block beta differentiation | **Unsupported so far** | Opcode-signature contrast p=0.125 |
| Radius sweep | **Pilot complete** | Radii 1,2,4,8; five matched seeds each |
| Parasite large-radius positive control | **Failed / blocking** | Content and ancestry diagnostics failed |
| 500,000-tick liveness treatment | **Not run** | 32×32 projected ≈17.6 hours |
| Integrated Phase 2 gate | **Not passed** | Parasite control invalid; full duration absent |

## Frozen candidate acceptance configuration

If a standalone liveness run or a later integrated campaign is authorized, the pilot-supported primary configuration is:

- lattice: 32×32 torus;
- interaction radius: 1;
- attempted interactions: 512 per tick;
- duration: 500,000 ticks;
- new seed: 202608300;
- initial fill: 0.8;
- pool multiplier: 16;
- mutation: 1/4,096;
- spontaneous dissolution: 10⁻⁵;
- reseed: 10⁻⁵;
- inertness threshold: 10,000 ticks;
- maximum-age and starvation dissolution disabled;
- aggregate interaction logging;
- full-byte snapshots every 5,000 ticks;
- positional byte-identity analysis with 999 permutations;
- exact-hash statistics retained but labeled non-identifiable when all hashes are singletons.

The acceptance thresholds in `reports/phase2_preregistration.md` remain unchanged. A projection is not a completed run.

## Required decision before more expensive work

Choose one of two scientifically clean paths:

1. **Keep the parasite gate.** Identify an independently validated BFF or compatible artificial-chemistry host/parasite pair, preregister it without tuning against radius outcomes, and re-establish the large-radius positive control before containment testing.
2. **Revise the Phase 2 gate explicitly.** Treat parasite containment as a later dedicated ecology phase and authorize the 500,000-tick liveness/spatial treatment as Phase 2's remaining criterion. This is a protocol change and must be recorded before launch.

Do not seed more copies, lower mutation, shorten the horizon, broaden the family after inspection, or compare radius 1 against this failed positive control and call the result containment.

## Key artifacts

- `reports/phase2_pilot_preregistration_addendum.md`
- `reports/phase2_liveness_pilot_report.md`
- `reports/phase2_liveness_confirmation_report.md`
- `reports/phase2_spatial_metric_addendum.md`
- `reports/phase2_radius_pilot_report.md`
- `reports/phase2_parasite_positive_control_preregistration.md`
- `reports/phase2_parasite_viability_report.md`
- `reports/phase2_parasite_ancestry_addendum.md`
- `reports/phase2_parasite_ancestry_report.md`

## Bottom line

Phase 2 has produced a real result: local interaction radius changes spatial sequence similarity while conservation and liveness remain exact. It has also produced a useful negative result: the chosen BFF copier is not a valid parasite positive control under the actual conserved, mutating Stage 2 conditions.

The correct next action is a protocol decision, not more tuning.
