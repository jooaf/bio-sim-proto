# Phase 2 pilot preregistration addendum — liveness operating point

**Frozen before pilot execution:** 2026-08-25

## Purpose

This pilot selects a reseeding/dissolution operating point for later Phase 2 spatial experiments. It is parameter selection, not the 500,000-tick acceptance treatment and not evidence that the Phase 2 scientific gate passed.

The acceptance criteria in `reports/phase2_preregistration.md` remain unchanged.

## Questions

1. Which tested reseed/dissolution pairs preserve a live, partially empty world while producing actual material turnover?
2. Which pairs clog because placement is too fast relative to dissolution?
3. Which pairs lose occupancy because dissolution is too fast relative to placement?
4. Are conservation and occupancy invariants exact in every completed run?
5. Do any short runs show descriptive spatial structure worth testing at larger scale?

## Fixed pilot design

- Lattice: 8×8 torus
- Initial occupied fraction: 0.8
- Tape length: 64 bytes
- Substrate: BFF
- Interaction radius: 1
- Attempted interactions: 32 per tick
- Mutation rate: 1/4,096 per byte before interaction
- Pool multiplier: 16
- Horizon: 5,000 ticks
- Matched seeds: 202608250, 202608251, 202608252
- Invariant cadence: every 100 ticks
- Epoch/tape census cadence: every 100 ticks
- Interaction logs: disabled; aggregate tick, population, tape, lifecycle, and invariant facts remain enabled
- Energy, signals, tasks, and starvation dissolution: disabled
- Structural-inertness threshold: 10,000 ticks, so it cannot trigger during this pilot
- Maximum-age dissolution: disabled

### Cartesian treatment matrix

| Parameter | Values |
|---|---|
| Per-tape spontaneous dissolution probability per tick | 10⁻⁶, 10⁻⁵, 10⁻⁴ |
| Per-free-cell reseed probability per tick | 10⁻⁵, 10⁻⁴, 10⁻³ |

This gives 9 treatments and 27 runs. The Cartesian grid deliberately includes expected under-reseeding, approximately balanced, and over-reseeding cases. No treatment will be removed because it performs badly.

## Pilot outcomes

For every run, report:

- exit status and invariant failures;
- exact per-symbol conservation at aligned snapshots;
- minimum population;
- final-window occupied fraction;
- longest full-occupancy interval;
- active-interaction fraction in the final window;
- final-window successful writes;
- cumulative dissolutions and successful placements;
- final-window pool-composition changes;
- final-snapshot neighbor-identity excess;
- final-snapshot q=1 block beta excess.

Spatial p-values use 199 permutations in this screening pilot. They are descriptive and will not be treated as confirmatory evidence.

## Mechanical feasibility rule

A run is mechanically feasible when all of the following hold:

1. successful exit;
2. zero invariant failures;
3. exact symbol conservation at all aligned snapshots;
4. minimum tape count above zero;
5. final-window mean occupied fraction at least 0.20;
6. no fully occupied interval longer than 1,000 ticks;
7. interactions execute in at least 90% of final-window ticks;
8. successful writes occur in the final window;
9. at least one dissolution and at least one successful placement occur;
10. pool composition changes in the final window.

This mirrors the acceptance mechanics but does not substitute for the 500,000-tick horizon.

## Operating-point selection rule

Treatments are ranked without inspecting spatial effects:

1. maximize the number of mechanically feasible seeds;
2. among ties, minimize the absolute distance between the treatment's median final-window occupied fraction and 0.8;
3. among remaining ties, choose the smaller spontaneous dissolution rate;
4. then choose the smaller reseed rate.

A treatment is eligible for scale confirmation only if at least 2 of 3 seeds are mechanically feasible. If no treatment is eligible, no operating point is selected; a new pilot must be separately preregistered.

Spatial results cannot be used to choose the liveness operating point. This prevents selecting parameters merely because a short run happened to look patchy.

## Next step after selection

The selected operating point will receive a larger-lattice confirmation before the matched radius sweep. The radius sweep remains fixed at radii 1, 2, 4, and 8 with at least five matched seeds per radius. The parasite campaign cannot support a containment claim until its large-radius positive control is viable.

## Provenance

The Phase 1 closeout baseline is commit `ff52403`, tagged `phase1-closeout-v1`. Pilot source, config, analysis code, and this addendum must be committed before execution. Raw outputs remain outside Git and are referenced by run manifests and compact summary tables.
