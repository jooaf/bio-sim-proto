# Phase 2 spatial metric and radius-pilot addendum

**Frozen before the matched radius campaign:** 2026-08-25

## Why the original metric needs an amendment

The original preregistration defined exact content hashes as spatial types. That test is valid only when at least one hash occurs more than once.

Across the 27-run 8×8 liveness pilot and all three unseen 32×32 confirmation runs, every final occupied tape had a unique exact hash. Under that condition:

- observed equal-hash neighbor frequency is zero;
- every hash-label permutation also gives zero;
- exact-hash block diversity is unchanged by permutation;
- p-values are 1 and effect sizes are zero by construction.

These values are non-identifiable, not negative evidence about locality. The issue was discovered before the radius campaign and before the 500,000-tick acceptance treatment.

## Disclosure of exploratory inspection

Before this addendum was frozen, two replacement diagnostics were implemented and inspected on the three 32×32 confirmation runs:

- median positional byte-identity neighbor excess: **0.004917**;
- per-run 199-permutation p-values for byte identity: **0.005, 0.005, 0.005**;
- median BFF-opcode-signature q=1 beta excess: **0.045140**, with mixed per-run p-values (**0.165, 0.645, 0.280**).

These are exploratory results. They motivated the definitions below but are not confirmatory evidence. The matched radius campaign uses new, unseen seeds.

## Frozen primary spatial statistic: positional byte-identity excess

For each complete full-byte tape snapshot:

1. enumerate undirected occupied radius-1 Moore-neighbor edges on the torus;
2. for every edge, compute the fraction of equal bytes at corresponding tape positions;
3. average across edges to obtain observed neighbor byte identity;
4. randomly permute complete tapes over the same occupied cells, preserving occupancy and the entire tape multiset;
5. recompute the statistic for each permutation;
6. report observed minus mean-null identity and the one-sided permutation p-value.

This detects near copies and shared sequence structure even when mutation makes every complete hash unique. It does not prove heredity: local rewriting, compositional gradients, or other mechanisms can also create sequence similarity.

For the radius pilot, use the last complete full-byte snapshot in the final 10% of ticks and 999 seeded permutations per run. The analysis seed is 20260825.

## Frozen block-diversity type: ordered BFF opcode signature

A tape's coarse type is the ordered sequence of its BFF instruction bytes after all non-instruction bytes are removed. The ten BFF opcodes retain their byte identities and order. Empty signatures form one valid type.

For each analyzed snapshot:

- partition the 32×32 lattice into nonoverlapping 8×8 blocks;
- compute q=1 Hill gamma diversity over opcode signatures;
- compute occupancy-weighted q=1 Hill alpha diversity within blocks;
- compute multiplicative beta = gamma / alpha;
- permute opcode-signature labels over fixed occupied cells 999 times;
- report observed beta minus mean-null beta and a one-sided p-value.

Opcode signatures are an intentionally coarse syntax proxy, not a demonstrated phenotype. Results must be described as spatial differentiation of instruction structure, not species or organism diversity.

## Status of the original exact-hash outcomes

Exact-hash neighbor identity and exact-hash block beta remain in all reports for continuity. When every hash is unique, they must be labeled **non-identifiable** and cannot pass or fail a spatial gate.

For Phase 2 acceptance, positional byte-identity excess replaces exact-hash identity as the primary sequence-structure statistic. Opcode-signature q=1 beta replaces exact-hash q=1 beta as the primary block-differentiation statistic. This amendment occurs before any acceptance treatment.

## Matched radius pilot

### Fixed design

- lattice: 32×32 torus;
- horizon: 5,000 ticks;
- full-byte snapshot interval: 500 ticks;
- block size: 8;
- radii: 1, 2, 4, 8;
- new matched seeds: 202608260–202608264;
- five seeds per radius, 20 runs total;
- spontaneous dissolution rate: 10⁻⁵;
- reseed rate: 10⁻⁵;
- initial fill: 0.8;
- pool multiplier: 16;
- mutation rate: 1/4,096;
- attempted interactions: 512 per tick;
- tape length: 64;
- interaction budget: 8,192;
- aggregate interaction logging;
- energy, signals, tasks, maximum-age death, and starvation death disabled.

All failed or extinct runs remain in the analysis.

### Questions and comparisons

1. Does radius 1 have positive byte-identity neighbor excess against its within-run permutation null?
2. Does radius 1 have positive opcode-signature q=1 beta excess?
3. How do both effects change at radii 2, 4, and 8?
4. Does increasing radius alter occupancy, turnover, or mechanical feasibility?

No monotonic radius response is assumed. Report every radius and matched-seed differences. The planned focused contrast is radius 1 minus radius 8, with an exact paired sign-flip permutation interval/test where applicable. Five-seed pilot results are effect-size estimates and cannot by themselves pass the full Phase 2 acceptance gate.

## Stopping and integrity rules

- Invariant failure halts and fails a run.
- Exact per-symbol conservation is required in every completed run.
- The campaign is not retuned after inspecting radius outcomes.
- A degenerate or negative statistic is reported as such.
- The parasite campaign remains separate and still requires a viable large-radius positive control.
- The 500,000-tick treatment remains unstarted.
