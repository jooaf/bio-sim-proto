# Cohort analysis of previously unseen native-GUI runs

## Scope

This analysis intentionally excludes the two runs already analyzed in detail:

- `20260824T054610.606059Z-seed85-rust-gui-c5246f32`;
- `20260825T153148.201047Z-seed24-rust-gui-b7c342d1`.

It inventories every later run between them. There are 54 records, of which 46
ran beyond 500 ticks. Thirty-two of those had no live configuration updates;
14 had one or more recorded slider changes.

Metrics were interpreted by configuration cohort rather than pooled as if all
runs were replicates. Extinction means the first sampled zero-population tick,
not the later tick at which the user closed or reset the GUI.

## 1. Default-like seed-7 lineage

Two schema-2 runs have the same seed and complete configuration fingerprint:

| run | final tick | final population | species |
|---|---:|---:|---:|
| `...123907...seed7...de2f4e13` | 11,195 | 1,408 | 2 |
| `...225709...seed7...0a740611` | 16,283 | 6,467 | 5 |

Their overlapping checkpoints agree closely: around tick 11,000 both had
approximately 1,380 organisms, two species, about 6,400 births, and about 5,300
deaths. This is consistent with deterministic continuation under one build.

A later clean schema-3 seed-7 run reached 151,440 organisms at tick 36,112,
with 19 species and late births/death 1.265. Its configuration record contains
new schema fields and cannot establish whether the larger outcome came from a
code revision, a newly active mechanism, or a meaningful configuration change
because historical manifests did not identify the compiled kernel binary.

## 2. Founder-diversity stress series did not rescue a hostile ecology

The clean seed -33 series held 110 founders and the hostile profile constant
while using 1, 2, 4, 6, 8, 10, or 20 founder archetypes. All seven completed
arms went extinct:

| archetypes | first extinction tick | peak population |
|---:|---:|---:|
| 1 | 3,446 | 110 |
| 2 | 9,331 | 110 |
| 4 | 9,674 | 110 |
| 6 | 12,474 | 122 |
| 8 | 7,641 | 110 |
| 10 | 8,564 | 110 |
| 20 | 10,861 | 119 |

The profile used only 700 initial deposits, maintenance 1.2, maturity 1.5,
reproduction drive 0.5, and reproduction cost/cooldown 0.95. More initial
lineages delayed extinction in some arms but did not create replacement
fertility. This supports the existing conclusion that founder diversity cannot
repair an energetically inviable operating point. It does **not** justify
changing global defaults because this was a deliberately non-default stress
profile and only one ecological seed.

Scaling the same profile to 1,290 founders also ended in extinction at sampled
tick 39,089. A 2,630-founder mutation-2.2 run ended extinct before its mutation
slider was changed at shutdown. A subsequent clean mutation-4.0 run survived
to tick 76,925 with 5,711 organisms. That single contrast confounds mutation
with survivor stochasticity and is insufficient for adopting mutation 4.0.

## 3. Multi-seed low-resource screen was uniformly inviable

Five clean 220-founder/20-archetype runs used the same core low-resource
profile (500 deposits, maintenance 1.2, maturity 1.0, mutation 3.6) across seeds
82, 86, 88, 91, and 93. All five went extinct between sampled ticks 1,755 and
14,451. Peak populations were only 220–284.

Reproduction success was 4.6–8.7%; energy blocks accounted for 69–79% of
attempts. This is a replicated result for that stress profile: it should be
labeled inviable rather than tuned interactively. It remains far from the
project defaults, so no default change follows.

## 4. Seed-95 deposit exploration shows a threshold, not a calibrated optimum

Clean seed-95 runs show:

- 500 initial deposits: extinction or near-extinction under several settings;
- 1,300 deposits: three survivors at tick 9,570;
- 3,600 deposits: growth to 3,885 and 9,743 in two exploratory settings;
- 3,000 deposits: eventual growth to 420,680 after a long bottleneck.

The 420k run is especially nonlinear: population was 25 at tick 11k, 30 at
22k, 118 at 33k, 2,880 at 44k, then 420,680 at 55k. It ended with 841 species
and only 9.6% dominance. This is an escape from a long stochastic bottleneck,
not evidence for a smooth response to one parameter.

Two apparently similar 3,600-deposit runs diverged by roughly an order of
magnitude by tick 6,600. Their only manifest differences were inactive season
schedule parameters. The current kernel was explicitly checked and produces
identical 7,000-tick digests when those disabled parameters differ. Historical
runs cannot be compared conclusively because their manifests lack a binary
build identifier. This provenance gap is now fixed for future runs.

## 5. High-population outcomes are repeated but remain frontier-limited

Among clean unseen runs, seed -17 reached 298,416 organisms and seed 7 reached
151,440. Their late births/death ratios were 1.203 and 1.265. Seed -17's
population per generated chunk fell 8.1% late; seed 7's rose 14.7%. Together
with the separately analyzed seed-24 result, high global population is often a
spatial frontier phenomenon, though density can still rise during bottleneck
escape.

Throughput fell to 0.60 ticks/s at 298k and 1.90 ticks/s at 151k. This confirms
that total individual and field count, not rendering, is the practical limit.
It supports the existing versioned parallel-engine work, not an ad hoc
population cap.

## 6. Conservation across the unseen cohort

- Matter failures: 0.
- Old-tolerance energy failures: 4.
- Maximum absolute relative energy error across completed unseen runs:
  `3.30e-12`.
- 90th-percentile relative energy error: approximately `1.03e-12`.

Every observed failure lies below the new `5e-12` generated-energy-aware bound.
The previously implemented audit change is therefore supported by the full
unseen cohort, not only the latest seed-24 run.

## Changes warranted by this cohort

1. **Compiled-kernel provenance:** native GUI and Rust headless manifests now
   record the extension version, SHA-256 of the actual loaded kernel binary,
   and SHA-256 of the canonical startup configuration. Recording schema
   versions were incremented.
2. **Extinction timing:** native reports now show peak tick and first sampled
   extinction tick instead of making GUI close/reset time look like survival
   duration.
3. **No ecological default changes:** extinction was concentrated in explicit
   stress profiles, while viable profiles ranged from near-extinction to
   frontier booms. The existing data do not isolate one generally beneficial
   parameter adjustment.

## Next controlled work

- Re-run the five-seed low-resource screen only if that stress profile is a
  desired operating regime; otherwise preserve it as a negative control.
- Run a paired deposit series across multiple seeds with one frozen kernel
  binary hash and no live updates.
- Treat bottleneck escape as a time-to-event endpoint; predeclare the tick
  budget and report extinction, escape time, and frontier-normalized density.
- Profile at matched populations before selecting work from
  `PARALLEL_ENGINE_DESIGN.md`.
