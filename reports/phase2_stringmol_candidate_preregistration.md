# Phase 2 Stringmol parasite-candidate preregistration

**Frozen before unseen-seed candidate validation:** 2026-08-26

## Candidate selection

The replacement audit selected pinned Spatial Stringmol. Three source-grounded shorter candidates were screened once in the upstream aspatial container at seed 1:

- one-symbol `B`;
- upstream commented debug candidate `R`;
- upstream commented debug candidate `S`.

Each candidate was compared alone and as a 10-molecule inoculum with 140 canonical replicases. This was candidate development, not confirmatory evidence.

Exploratory exact-candidate outcomes at 5,000 steps:

| Candidate | Alone: initial → max → final | With host: initial → max → final |
|---|---:|---:|
| B | 150 → 150 → 46 | 10 → 10 → 3 |
| R | 150 → 150 → 43 | 10 → 45 → 45 |
| S | 149 → 149 → 44 | 10 → 10 → 4 |

Only `R` increased above inoculum size in the host treatment. It is frozen before new seeds.

## Frozen host and parasite

Host replicase:

```text
WWGEWLHHHRLUEUWJJJRJXUUUDYGRHJLRWWRE$BLUBO^B>C$=?>$$BLUBO%}OYHOB
```

Parasite candidate R:

```text
WWGEWLHHHRLUERWWRE$BLUBO^B>C$=?>$$BLUBO%}OYHOB
```

Candidate R is shorter than the host and appears in multiple upstream spatial configuration files as an additional debugging species. It is source-grounded but not yet proven to be an obligate parasite. That is the purpose of this validation.

## Pinned software

- upstream commit: `15dad84da126a4f887ba945c23a13e89e827f067`;
- canonical ALXII substitution matrix;
- reviewed patch set from `experiments/stringmol/patches/`;
- upstream chemistry, opcodes, binding, mutation, decay, copying, and cleavage unchanged;
- fixed unbiased neighbor-selection repair;
- explicit global interaction and placement controls use radius 0.

## Unseen-seed validation matrix

Seeds: **202608310–202608319**.

For every seed, run:

1. **host-only:** 140 host molecules;
2. **parasite-only:** 10 R molecules;
3. **mixed:** the same 140 host molecules plus the same 10 R inoculum.

All use:

- 40×40 toroidal grid;
- 5,000 steps;
- global interaction radius 0;
- global offspring-placement radius 0;
- mutation 0.0002;
- decay 0.0005;
- identical chemistry, reporting cadence, and matrix;
- explicit `NUMAGENTS` and one-agent-per-record loading;
- fixed 15×10 host block with a centered ten-cell R stripe in mixed runs;
- parasite-only R cells at the identical stripe locations.

## Primary host-dependence outcomes

For each seed:

- exact R maximum and final abundance in parasite-only;
- exact R maximum and final abundance in mixed;
- maximum exact R fraction in mixed;
- host and total population persistence.

Candidate R passes host-dependence validation only if:

1. mixed exact R exceeds the ten-molecule inoculum in at least 8/10 seeds;
2. parasite-only exact R does not exceed ten in at least 8/10 seeds;
3. the paired mixed-minus-alone maximum-abundance difference is positive in at least 8/10 seeds;
4. at least 8/10 host-only runs retain host molecules at the final step;
5. all processes exit successfully with matching source/config/patch hashes and no reproducible-loader fallback warning.

This validation does not yet require 90% parasite occupancy. Passing it establishes a host-dependent candidate suitable for the subsequent ten-seed global positive-control test.

## Integrity rules

- Candidate, inoculum, horizon, and thresholds are frozen before unseen seeds.
- B and S are not reconsidered if R fails.
- Failed and extinct runs remain in the result.
- Local treatments are not run until host dependence and then global positive-control viability pass.
- A successful external Stringmol control does not establish BFF parasite containment.
