# Phase 2 acceptance readiness after the external Stringmol control

**Decision date:** 2026-08-26

## Superseding decision

**CONDITIONAL GO for the 500,000-tick conserved-BFF liveness/spatial treatment.**

The previously blocking parasite-mechanism control now passes in an independently established artificial chemistry. Pinned Spatial Stringmol provided a valid global positive control and a preregistered matched locality comparison.

Phase 2 is still **not passed**. The 500,000-tick BFF run has not been executed, its long-run spatial statistics remain unknown, and the external Stringmol result must not be presented as BFF parasite containment.

## Replacement parasite-control result

### Independently validated host dependence

Candidate R exact sequence:

```text
WWGEWLHHHRLUERWWRE$BLUBO^B>C$=?>$$BLUBO%}OYHOB
```

Across ten unseen seeds:

- mixed R increased above inoculum in **10/10**;
- R alone did not increase in **10/10**;
- mixed-minus-alone maximum abundance was positive in **10/10**;
- host-only populations persisted in **10/10**.

### Global positive control

Across ten new 10,000-step global runs:

- passive-parent parasite ancestry reached 90% in **10/10**;
- exact R exceeded inoculum in **10/10**;
- populations persisted in **10/10**;
- all pinned provenance and explicit-loader checks passed.

### Matched local containment

The same ten seeds, sequences, positions, mutation, decay, grid, and horizon were rerun with interaction and offspring placement changed from global radius 0 to local radius 1.

- Global final ancestry: approximately **0.964–1.000**.
- Local final ancestry: approximately **0.050–0.673**.
- Mean paired global-minus-local effect: **0.661862**.
- Median paired effect: **0.672612**.
- 95% paired bootstrap interval: **[0.566007, 0.747191]**.
- Exact one-sided paired sign-flip: **p = 0.000977**.
- Global reached 90%: **10/10**.
- Local reached 90%: **0/10**.
- Local populations persisted: **10/10**.

The preregistered external containment control passed.

## Why this is credible

- Source repository and commit are pinned.
- The upstream Catch suite passed 79 assertions in 15 cases.
- A source-level missing-braces/counter defect in random neighbor choice was identified, patched, and retained as an auditable external patch.
- Interaction and offspring-placement locality are explicit independent config fields.
- Chemistry, opcodes, binding, mutation, decay, copy, and cleavage behavior were not changed.
- Explicit one-agent-per-record loading removed the upstream reproducibility fallback warning.
- Candidate R was selected once, disclosed, then validated on unseen seeds.
- Global validation preceded local treatment.
- Passive-parent ancestry follows Stringmol's actual inherited passive label.
- All scientific failures would have remained in their denominators.

## Interpretation boundary

The supported claim is:

> Local interaction and local offspring placement strongly contained a validated host-dependent parasite in pinned Spatial Stringmol relative to a matched global control.

The unsupported claim is:

> The conserved BFF soup contains or controls a viable parasite.

The BFF candidate remains rejected. The Stringmol result is an external mechanism control chosen explicitly to retain the parasite gate without tuning the failed BFF candidate.

## Phase 2 criterion status

| Criterion | Status |
|---|---|
| Exact BFF symbol conservation | Ready; zero residual in 61 prior BFF runs |
| BFF lifecycle and occupancy invariants | Ready; zero invariant failures |
| BFF liveness operating point | Frozen at dissolution/reseed 10⁻⁵ / 10⁻⁵ |
| Short BFF radius effect | Supported for byte similarity |
| BFF block beta differentiation | Unsupported in short pilot; must be measured long-run |
| Parasite positive control | Passed externally in Stringmol |
| Matched parasite locality mechanism | Passed externally in Stringmol |
| 500,000-tick BFF liveness/spatial treatment | Not run |
| Integrated Phase 2 conclusion | Not passed |

## Remaining launch requirements

Before starting the 500,000-tick run:

1. validate the long-run analysis command against a short run containing full-byte snapshots;
2. ensure positional byte-identity and opcode-signature q=1 beta are computed over the final window with the frozen 999-permutation nulls;
3. record the current source commit in the run manifest;
4. launch only the frozen `experiments/configs/stage2_acceptance_candidate.toml` configuration;
5. retain failure/extinction/invariant outcomes;
6. report measured runtime rather than the earlier projection.

The run is projected to take approximately **17.6 hours** and produce roughly **0.65 GB** under aggregate logging.

## Key replacement-control artifacts

- `reports/phase2_replacement_host_parasite_audit.md`
- `reports/phase2_stringmol_candidate_preregistration.md`
- `reports/phase2_stringmol_candidate_report.md`
- `reports/phase2_stringmol_global_positive_control_preregistration.md`
- `reports/phase2_stringmol_global_report.md`
- `reports/phase2_stringmol_locality_preregistration.md`
- `reports/phase2_stringmol_locality_report.md`
- `experiments/stringmol/source.lock.json`
- `experiments/stringmol/patches/0001-fix-neighbor-selection-and-add-locality-controls.patch`

## Bottom line

Option 1 succeeded: an independently validated host–parasite system now supplies the required positive and locality controls. The next expensive action is the frozen 500,000-tick BFF run, after one final analysis smoke test.
