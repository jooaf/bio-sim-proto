# Phase 2 replacement host–parasite audit

**Audit date:** 2026-08-26

## Decision

**Select pinned Spatial Stringmol for replacement positive-control engineering.**

Do not reuse or tune the rejected BFF candidate. Do not use the repository's guarded copier as a parasite: it is a deliberately trivial exact copier with no independently published host exploitation ecology.

Stringmol is the only audited option that has all of:

- a published, hand-built replicase;
- mutation-on-copy;
- documented parasite emergence and host–parasite arms races;
- pairwise molecular binding and execution;
- a public spatial implementation originally developed for replicator–parasite evolution;
- source and fixed configurations that can be pinned and rerun.

Stringmol will be an **external ecological control**, not evidence that the conserved BFF substrate itself contains parasites.

## Required replacement-control properties

Before a containment comparison, the selected system must demonstrate:

1. **Independent provenance:** host and parasite behavior precede this Phase 2 campaign.
2. **Pinned mechanics:** exact source commit, compiler, patch set, and configuration hashes.
3. **Host dependence:** the parasite cannot reproduce alone but increases with the host.
4. **Large-radius viability:** the same inoculum reaches the preregistered takeover threshold in at least 8/10 seeds.
5. **Matched locality:** local and large-radius treatments differ only in interaction/dispersal locality explicitly declared before execution.
6. **Neutral measurement:** family labels and ancestry analysis cannot affect reproduction.
7. **Determinism/provenance:** fixed seeds reproduce compact population/species outputs byte-for-byte.
8. **Failure retention:** extinctions and software failures remain in the result set.

The original BFF candidate failed properties 3–4 under actual Stage 2 mutation and is permanently excluded from further tuning in this gate.

## Candidate audit

### 1. Rejected BFF copier

- Mechanically copied without mutation.
- Failed content-family viability.
- Failed conservative neutral-ancestry viability.
- No further seed-count, mutation, or family-definition tuning is permitted.

**Decision:** reject.

### 2. Four-symbol guarded copier

- Exact seeded copies are independently testable within this repository.
- Copying is a built-in one-op rule rather than exploitation of a host replication program.
- It has no published spatial host–parasite ecology and would make a positive control true by construction.

**Decision:** retain as a software fixture only, not the scientific control.

### 3. Spatial Stringmol

Pinned upstream source:

- repository: `https://github.com/uoy-research/stringmol`;
- branch inspected: `dev`;
- commit: `15dad84da126a4f887ba945c23a13e89e827f067`;
- commit date: 2025-01-17;
- license: GPL-3.0-or-later;
- declared software version in README: 0.2.2, with later development history and tags through 0.2.4.1.

Canonical seeded replicase:

```text
WWGEWLHHHRLUEUWJJJRJXUUUDYGRHJLRWWRE$BLUBO^B>C$=?>$$BLUBO%}OYHOB
```

The upstream `quick_test33.conf` seeds 55 copies on a 125×100 toroidal grid with mutation 0.0002 and decay 0.0005.

Published/source-grounded relevance:

- the technical report specifies the Stringmol language and seeded replicase;
- Hickinbotham et al. report mutation-on-copy diversity;
- Hickinbotham & Stepney report replicator–parasite dynamics and evolutionary innovation;
- upstream `DEVNOTES.md` says the spatial flavor was developed with Paulien Hogeweg for “R-P evolution”;
- upstream spatial/aspatial configs explicitly discuss collapse due to parasitism.

**Decision:** select, subject to the engineering blockers below.

## Local reproduction evidence

The pinned source was cloned and built on macOS arm64 after creating its expected `debug/` and `release/` directories.

Validation:

- upstream Catch tests: **79 assertions in 15 test cases passed**;
- release spatial smoke, trial type 30: exit 0;
- canonical 1,000-step spatial run: population changed from 55 to 104 molecules;
- at tick 950, the upstream species log contained 11 observed species records and 5 extant species;
- aspatial seeded smoke also completed and diversified;
- two identical spatial runs produced byte-identical `popdy001.dat`, `splist950.dat`, `out1_00950.conf`, and `RNGstate_950.txt`.

This establishes buildability, deterministic seeded growth, mutation, and diversification. It does **not yet** establish an explicit parasite inoculum.

## Engineering blockers found

### Blocker 1 — neighbor-selection defect

`Stringmol_Spatial::ReactionSeekRandomSpatialPartner` counts eligible Moore neighbors and draws a random ordinal, but the selection loop's `return` is not scoped by braces and its counter is not incremented. The current code therefore returns the first eligible neighbor rather than the drawn neighbor.

This must be fixed with a focused regression test before scientific spatial runs. Results from the unpatched smoke are only software-reproduction evidence.

### Blocker 2 — hard-coded radius 1

Binding searches and offspring placement use a Moore neighborhood hard-coded to radius 1. There is no matched large-radius treatment. A configurable radius must be added without changing chemistry, mutation, decay, binding probability, or execution.

Interaction radius and offspring-placement radius must be separate parameters so the experimental contrast is explicit. A global control cannot be described as matched if both are silently changed together.

### Blocker 3 — reproducible loading warning

Upstream prints:

> Number of agents not specified - impossible to configure using reproducible method... Reverting to original load method (pre 2017)

The fixed config still reproduced byte-identical compact outputs locally, but the warning must be removed by pinning an explicit agent-count/placement path and testing it across seeds.

### Blocker 4 — parasite identity is not pinned

The source contains commented shorter sequences labeled `R` and `S` for debugging, and deterministic runs produce short potential parasite species, including a one-symbol `B`. The available source comments do not establish which sequence should serve as the published parasite inoculum.

No candidate may be chosen merely because it produces the desired locality result. Candidate validation order must be:

1. one-on-one host dependence;
2. parasite-alone negative control;
3. host-plus-parasite large-radius invasion;
4. only then local containment.

### Blocker 5 — legacy output and analysis

The simulator emits many PNG, RNG, config, species, and population files. Spatial ancestry/community tools are marked as not fully migrated to the current spatial class. A wrapper must retain compact raw facts, hashes, exit status, and source/config metadata without relying on unreviewed R scripts.

## Implementation plan

1. Add a source lock and reproducible bootstrap/build script.
2. Carry a minimal patch series outside the upstream checkout.
3. Fix and test unbiased neighbor selection.
4. expose interaction and offspring-placement radii independently;
5. build compact parsers for species/population/config output;
6. validate candidate `R`, `S`, and any explicitly documented upstream parasite only through predeclared host-dependence assays;
7. freeze one candidate before large-radius viability;
8. run ten unseen large-radius seeds;
9. run the local comparison only if at least 8/10 large-radius controls reach the takeover threshold.

## Scope warning

A successful Stringmol control would show that locality contains a validated parasite in an independently established automata chemistry. It would support the **generality and experimental design** of the Phase 2 locality claim. It would not prove parasite containment in the conserved BFF soup, whose positive control failed.
