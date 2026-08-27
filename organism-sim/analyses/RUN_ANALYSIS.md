# Organism Simulation Run Analysis

## Overview

This analysis covers all 14 SQLite runs under [`runs/`](runs/), totaling approximately 5.73 GB of data.

All runs used seed `7`. The ten completed 1,500-tick runs form a controlled sweep of founder archetype counts from 13 through 22; all other configuration values were identical. Runs using legacy configurations or shorter durations are presented separately and should not be treated as directly comparable to that sweep.

## Run-by-Run Summary

The **half-population tick** is the first tick at which the population fell to 50% or less of its initial value.

| Run suffix | Founder archetypes | Ticks | Population | Living species | Births | Deaths | Half-population tick |
|---|---:|---:|---:|---:|---:|---:|---:|
| `14122943` | Legacy | 2 | 10 → 10 | 3 → 3 | 0 | 0 | — |
| `70ed3046` | Legacy | 100 | 100 → 85 | 5 → 5 | 0 | 15 | — |
| `d7777624` | Legacy | 6,708 | 300 → **0** | 9 → 0 | 209 | 509 | 340 |
| `ed679e0c` | 12 | 1,000 | 300 → 92 | 12 → 7 | 106 | 314 | 397 |
| `0adcdd2f` | 13 | 1,500 | 300 → **116** | 13 → 6 | 198 | 382 | 504 |
| `e873f2de` | 14 | 1,500 | 300 → 84 | 14 → 5 | 165 | 381 | 476 |
| `2a8da6df` | 15 | 1,500 | 300 → 98 | 15 → 4 | 163 | 365 | 520 |
| `43c0dafd` | 16 | 1,500 | 300 → **65** | 16 → 8 | 110 | 345 | 465 |
| `027e9105` | 17 | 1,500 | 300 → 90 | 17 → 7 | 198 | 408 | 767 |
| `b40bab8d` | 18 | 1,500 | 300 → 75 | 18 → 5 | 149 | 374 | 430 |
| `4021e1af` | 19 | 1,500 | 300 → 90 | 19 → 8 | 176 | 386 | 470 |
| `01209c0c` | 20 | 1,500 | 300 → 94 | 20 → **9** | 172 | 378 | 423 |
| `d466fd35` | 21 | 1,500 | 300 → 81 | 21 → 7 | 161 | 380 | 550 |
| `9bf0febd` | 22 | 1,500 | 300 → 81 | 22 → 8 | 158 | 377 | 605 |

## Findings

### Population Survival

Across the ten directly comparable 1,500-tick runs:

- Mean final population: **87.4 organisms**
- Mean founder retention: **29.1%**
- Final population range: **65–116 organisms**
- Best final population: archetype count **13**, with **116 organisms**
- Worst final population: archetype count **16**, with **65 organisms**

Adding more founder archetypes did not produce a monotonic improvement in population survival. The Pearson correlation between archetype count and final population was **−0.39**.

### Species Diversity

Across the comparable runs:

- Mean final living species: **6.7**
- Final living-species range: **4–9**
- Highest final species count: archetype count **20**, with **9 species**

Archetype count had a moderately positive correlation with the absolute final species count (**r = 0.62**), but almost no relationship with the fraction of original species retained (**r = −0.12**). More starting lineages therefore increased the number of surviving lineages without clearly improving proportional diversity retention.

### Species Dominance

Several final ecosystems were dominated by one lineage:

| Founder archetypes | Largest species' share of final population |
|---:|---:|
| 21 | 79.0% |
| 14 | 75.0% |
| 13 | 65.5% |
| 18 | 57.3% |
| 22 | 50.6% |
| 17 | 50.0% |

This suggests that nominal species counts can overstate effective diversity. Some runs retained several species, but most organisms belonged to one dominant lineage.

### Mortality

Across the comparable runs, deaths were approximately:

- **60% attrition**
- **40% predation**

One fire death occurred in the archetype-18 run.

As founder archetype count increased, predation declined strongly:

- Correlation with predation deaths: **r = −0.87**
- Correlation with predation's share of deaths: **r = −0.90**

However, lower predation did not translate into consistently better survival because attrition became the dominant mortality source.

### Reproduction

Reproduction was constrained across the sweep:

- Mean births per run: **165.0**
- Mean deaths per run: **377.6**
- Approximate reproduction-attempt success rate: **22%**
- Sexual reproduction accounted for approximately **3% of births**
- Sexual events ranged from **0 to 6 per run**
- Maximum generation reached only **3–5** in the 1,500-tick runs

Births were insufficient to replace deaths in every comparable run.

### Alliances and Colonies

The comparable runs created between 89 and 123 alliances each, but **no colonies formed in any run**. This may indicate that colony prerequisites are too restrictive, colony formation is too improbable, or that the colony pathway is not being exercised as intended.

### Long-Run Extinction

The legacy run ending in `d7777624` reached complete extinction:

| Population threshold | First tick at or below threshold |
|---:|---:|
| 200 | 199 |
| 150 | 340 |
| 100 | 585 |
| 50 | 1,459 |
| 10 | 3,870 |
| 1 | 5,591 |
| 0 | 6,454 |

Recording continued through tick 6,708. The population briefly persisted between roughly 7 and 30 organisms before its final collapse.

### Conservation

Conservation behavior was excellent:

- Element-count drift was exactly **zero in every run**.
- Maximum absolute energy error across all runs was approximately **4.6 × 10⁻⁸**.
- Maximum absolute energy error in the 1,500-tick sweep was approximately **5.8 × 10⁻⁹**.

These errors are consistent with floating-point rounding rather than meaningful conservation loss.

### Performance

The completed 1,500-tick runs averaged approximately **15.4 ticks per second**. Full per-tick recording generated databases of roughly 385–411 MB per run.

## Conclusions

1. Increasing founder archetype count improves the absolute number of surviving species somewhat, but does not reliably improve organism survival or proportional species retention.
2. Higher archetype counts substantially reduce predation, yet attrition replaces predation as the primary mortality pressure.
3. Reproduction does not keep pace with mortality, and sexual reproduction is especially rare.
4. Several ecosystems retain multiple nominal species while remaining strongly dominated by one lineage.
5. Alliance creation is active, but colony formation appears absent or unreachable under the tested configuration.
6. Matter and energy conservation are functioning correctly to numerical precision.

## Limitations

- Every run used seed `7`, so the findings may reflect seed-specific behavior.
- Only ten runs share both the same 1,500-tick duration and otherwise identical configuration.
- Correlations are descriptive and should not be interpreted as causal.
- Multiple seeds per archetype count are needed to estimate variance and determine whether observed trends are robust.
- The `/data-explore` extension rejected the valid SQLite files as unsupported, so the analysis was performed with read-only `sqlite3` queries instead.

## Balancing Changes Motivated by This Analysis

The first response is deliberately configurable rather than a permanent rebalance because all comparable runs used one seed.

1. Added an optional sexual-attempt success floor, enabled by default at **8%**. Maturity, contact, action selection, matter, and energy requirements still apply.
2. Sexual propensity is now independent of asexual propensity. An organism may pursue both strategies; high asexual propensity no longer excludes it from mate selection.
3. Sexual success above the floor now explicitly incorporates both parents' sexual propensities, fertility, and genomic distance.
4. Added a maintenance-cost multiplier, default **1.0**, to support controlled attrition-pressure sweeps without rewriting organism genomes.
5. Relaxed colony specialist eligibility from sexual/asexual thresholds of **0.10/0.50** to **0.25/0.35**.

A same-seed, 900-tick directional smoke comparison with 300 founders and 20 genome seeds produced:

| Sexual floor | Final population | Births | Sexual events | Unique sexual parents | Living colonies |
|---|---:|---:|---:|---:|---:|
| Disabled | 107 | 80 | 1 | 2 | 0 |
| Enabled at 15% | 109 | 86 | 5 | 9 | 3 |

This is a smoke test rather than evidence of a robust effect. The next experiment should use multiple seeds and cross sexual-floor values with maintenance multipliers.

### Second fertility pass

Because births remained below replacement, later defaults also changed:

- Asexual floor: **12% → 20%**
- Sexual floor: **8% → 12%**
- Effective maturity-age multiplier: **1.0 → 0.65**
- Reproduction action utility bonus: **0 → 1.25**
- Reproduction energy-cost multiplier: **1.0 → 0.75**
- Reproduction cooldown multiplier: **1.0 → 0.75**

A same-seed 900-tick comparison with 300 founders and 20 genome seeds produced:

| Defaults | Final population | Births | Deaths | Attempts | Resource blocks | Probability failures | Asexual events | Sexual events |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Previous | 108 | 89 | 281 | 654 | 292 | 277 | 81 | 4 |
| Fertility pass | 164 | 199 | 335 | 1,696 | 888 | 625 | 167 | 16 |

Births increased by **124%**, and final population increased by **52%**. Deaths also rose because the more populous ecosystem created additional exposure and competition. Resource blocks are now the largest measured reproductive bottleneck. New run-schema counters separately record attempts, resource blocks, probability failures, and placement failures for follow-up analysis.


### Third pass: renewable food web and predation

An in-process probe (`experiments/selection_probe.py`) showed the deeper mechanism behind the earlier replacement deficit: with default settings chemical energy flows one way (deposits → organisms → heat diffusing into the infinite plane), nothing recycles heat into the food web, so deposit energy fell monotonically (2.33e5 → 1.20e5 by tick 3,000), ~95% of deaths were attrition, generations stalled at 0–3, and 78% of reproduction attempts were resource-blocked. Mortality was a starvation lottery rather than differential survival, which is why natural selection appeared absent.

Predation was also economically dead: 5,048 attacks over 1,000 ticks produced 24 kills (0.5% completion), so hunting could never pay its energy cost and the hunter guild was inviable.

Three changes followed, all conservation-safe and configurable:

1. **Deposit production** (new `deposit_production_rate`, default 0.10): deposit cells convert local ambient heat into chemical energy, bounded by batch capacity, exactly conserving total energy. This makes the food web renewable and rate-limited, giving competition something to act over.
2. **Attack damage multiplier** (new `attack_damage_multiplier`, default 2.0): predation now completes at meaningful rates.
3. **Prey compatibility threshold** (new `prey_compatibility_threshold`, default 0.35, previously hardcoded 0.45).

Probe results at 8,000 ticks (default otherwise):

| Seed | Production | Attack | Population trajectory | Late generations | Predation share | Audit error |
|---:|---:|---:|---|---:|---:|---:|
| 7 | off | 1.0 | 300 → 166, still falling | 0–3 | ~1% | 3e-8 |
| 7 | on | 2.0 | 300 → 543, births ≈ deaths | 1–10 | 5–12% | 1e-8 |
| 41 | on | 2.0 | 300 → ~150 → 204, recovering | 1–8 | ~10% | 7e-10 |

Directional selection on digestion is now visible in the living population (mean 0.66 → 0.88), reproduction resource blocks fell from ~78% to ~35% of attempts, and locomotion traits stop degrading population-wide once predation can complete. At attack damage 3.0 the arms race intensifies (generations 40+ by tick 8,000) but populations can boom into the thousands via colonization, so 2.0 is the default.