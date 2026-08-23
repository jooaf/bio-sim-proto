# Stage 0/1 targeted experiment pilots — 2026-08-09

## Scope

Two ideas from `experiments/EXPERIMENT_IDEAS.md` were selected for a bounded unattended campaign:

1. **P1.1/P1.4 pilot:** pool-multiplier sensitivity and blocked-write temporal structure at Stage 1.
2. **P0.3 pilot:** mutation-rate sensitivity at the paper's full 131,072-tape scale.

Runs were sequential within each campaign; no replicate batch was parallelized. These are deliberately **single-seed pilots**, intended to validate mechanisms and identify follow-up experiments—not estimate population-level probabilities or confidence intervals.

## Methods

### Stage 1 pool pilot

- Seed: 1
- Population: 256 tapes × 64 bytes
- Duration: 20,000 ticks
- Pairing: 128 shuffled disjoint pairs/tick
- BFF budget: 8,192 character reads/interaction
- Mutation: 1/4,096 per byte
- Pool multipliers: 0.1, 0.5, 2.0, 16.0
- Detailed logging: 2,560,000 interactions per condition

Spec: `experiments/sweeps/p1_pool_multiplier_pilot.toml`
Index: `sweeps/p1_pool_multiplier_pilot/index.parquet`
Summary: `reports/p1_pool_multiplier_pilot_summary.csv`

### Paper-scale mutation pilot

- Seed: 0
- Population: 131,072 tapes × 64 bytes
- Duration: 16,000 epochs
- Pairing: 65,536 shuffled disjoint pairs/epoch
- BFF budget: 8,192 character reads/interaction
- Mutation rates: 0, 1/4,096 (reference), 1/128 (32× reference)
- Bounded aggregate logging at 128-epoch intervals

Runner: `experiments/run_paper_mutation_pilot.nu`
Summary: `reports/p0_mutation_rate_pilot_summary.csv`

## Validation

All four Stage 1 runs completed successfully:

- 20,000/20,000 ticks and 2,560,000 interactions each;
- empty invariant logs;
- exact 256-component symbol conservation at every checked snapshot;
- maximum conservation residual: 0.

All three paper-scale runs contain 126 aggregate observations spanning epoch 1 through 16,000. The reference-rate transition checkpoint is byte-identical to the previously reproduced checkpoint (`SHA-256 3c0304ce770686749e328eaf2e136f69fbb9147c8b1271166a1d72d157369042`). Validation details are in `reports/pilot_experiments_validation.json`.

## Results A — pool multiplier and scarcity

| Pool multiplier | Free bytes | Overall blocked-write rate | First 100 ticks | Last 100 ticks | Pool entropy Δ | Final zero-count symbols | Changed interactions |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.1 | 1,637 | 30.79% | 63.03% | 20.71% | -0.515 bits | 31 | 33.96% |
| 0.5 | 8,190 | 14.95% | 34.84% | 1.62% | -0.176 bits | 4 | 30.29% |
| 2.0 | 32,768 | 3.05% | 0.78% | 0.82% | -0.063 bits | 1 | 37.23% |
| 16.0 | 262,144 | 0.12% | 0.00% | 0.00% | -0.007 bits | 0 | 57.29% |

### Finding A1: scarcity behaves monotonically in aggregate

Increasing the reservoir reduced both blocked-write rate and pool-composition drift. The default multiplier 2.0 was already close to the unconstrained regime in aggregate, while multiplier 0.1 remained strongly constrained after 20,000 ticks.

### Finding A2: scarcity relaxes rather than exhausting total pool matter

At multipliers 0.5 and 2.0, blocking declined substantially after the initial transient. Crucially, **pool total never changes**: every accepted replacement consumes one symbol and returns one symbol. The "pool exhaustion" proposal P1.8 should therefore be reframed as **critical-symbol depletion**, not total-pool exhaustion. Only composition can exhaust.

At multiplier 0.1, five symbols were absent initially because proportional integer rounding acted on a very small reservoir; 31 were absent at the end. At multiplier 2.0, only byte 63 (a noop) ended at zero. The constrained trajectories did not simply consume all BFF instructions: changes were selective and condition-dependent. At multiplier 2.0 the largest instruction-pool losses were `<` (-142), `>` (-128), and `,` (-87), indicating accumulation of these operators in tapes.

### Finding A3: blocking is episodic even when its average is tiny

Peak single-tick blocked-write fractions were 96.4%, 94.7%, 88.3%, and 84.6% for multipliers 0.1, 0.5, 2.0, and 16.0 respectively. At multiplier 16, blocking was zero in the final 100 ticks and only 0.12% overall, yet one tick blocked 2,694 writes. Lag-1 autocorrelation fell from 0.32 at multiplier 0.1 to 0.02 at multiplier 16, while the blocked-count coefficient of variation rose sharply.

This supports a **rare local burst** interpretation: a long-running tape can repeatedly request one scarce symbol during a single interaction, producing a blocking spike even when the global reservoir is generous. There is no evidence yet for periodic oscillation; a spectral/long-lag analysis is the appropriate P1.4 follow-up.

### Finding A4: intermediate scarcity may increase structure, but not replication at this scale

Maximum high-order entropy was 0.020, 0.177, 0.635, and 0.360 bits/byte across increasing multipliers. The default multiplier 2.0 produced the strongest correlations, exceeding both tighter and looser reservoirs. This is a potentially interesting non-monotonic effect, but it is one seed and remains below the paper-style transition threshold of 1 bit/byte.

No condition produced an exact full-tape replication event or sustained exact-hash abundance above 2. This is consistent with the already established underpowered 256-tape regime and must not be interpreted as conservation preventing replication.

## Results B — mutation-rate Goldilocks pilot

| Mutation rate | First transition | Maximum high-order entropy | Final entropy | Runtime |
|---:|---:|---:|---:|---:|
| 0 | none | 0.658 | 0.482 | 281 s |
| 1/4,096 | epoch 2,433 | 6.055 | 6.026 | 870 s |
| 1/128 | none | 0.0127 | 0.0105 | 138 s |

### Finding B1: seed 0 has a narrow mutation-dependent transition

The reference mutation rate reproduced the known transition at epoch 2,433 and sustained a high-complexity replicator takeover. The same initialization with no mutation developed moderate correlations but did not cross the transition threshold by epoch 16,000. At 32× the reference mutation rate, the soup remained essentially incompressible random material.

This is strong within-seed evidence for a Goldilocks zone: modest noise opens the seed-0 emergence path, while high noise destroys heritable correlations. It does **not** establish that zero-mutation soups generally fail—the paper reports emergence without background mutation across other seeds.

### Finding B2: runtime itself tracks dynamical regime

The successful reference-rate run was 3.1× slower than the zero-mutation run and 6.3× slower than the high-mutation run. Replicator-rich soups spend far more time in long BFF loops, while heavy mutation continually disrupts those loops. Runtime/character-read distributions are therefore scientifically informative observables, not merely engineering noise.

## Corrections to the proposed experiment plan

1. P1.8 should measure per-symbol depletion/freeze events, not total-pool exhaustion.
2. Full interaction logging at 4,096 tapes for dense sweeps is not tractable with the current Python engine; use the accelerated probe or much lower sampling.
3. Exact 64-byte hash copying is too strict as the sole emergence detector. Paper-style high-order entropy and functional self-replication scoring must accompany it.
4. Single-seed pilots identify mechanisms but cannot support emergence probabilities, monotonic threshold claims, or significance tests.

## Recommended next experiments

1. **Replicate the mutation pilot** for seeds 1–4, sequentially, concentrating on rates 0, 1/4,096, and 1/128. This directly tests whether the seed-0 Goldilocks pattern generalizes.
2. **Replicate pool multipliers 0.5, 2.0, and 16.0** for at least five seeds. Test the non-monotonic high-order entropy signal with bootstrap intervals.
3. **P1.4 burst analysis:** log blocked writes by requested symbol and compute event-duration distributions, long-lag autocorrelation, and spectra. Determine whether spikes are isolated loops or endogenous cycles.
4. **Revised P1.8:** define freeze as sustained near-zero successful content-changing writes plus depletion of specific requested symbols.
5. **P1.6 pool initialization:** compare histogram-matched and uniform reservoirs, motivated by initial zero-count symbols at multiplier 0.1.
6. **P1.5 minimization:** compare multipliers 2 and 16 at a replication-capable scale; the current entropy result suggests intermediate scarcity may organize rather than merely suppress dynamics.

## Papers to follow up

1. **Agüera y Arcas et al. (2024), “Computational Life: How Well-formed, Self-replicating Programs Emerge from Simple Interaction.”** [arXiv:2406.19108](https://arxiv.org/abs/2406.19108)
   Direct comparator for the mutation ablation, high-order entropy transition, and long-loop runtime effect.

2. **Eigen (1971), “Selforganization of matter and the evolution of biological macromolecules.”** [DOI:10.1007/BF00623322](https://doi.org/10.1007/BF00623322)
   The classic error-threshold framework. The high-mutation condition's loss of compressible heredity is a computational analogue worth testing quantitatively.

3. **Wilke et al. (2001), “Evolution of digital organisms at high mutation rates leads to survival of the flattest.”** [DOI:10.1038/35099067](https://doi.org/10.1038/35099067)
   Suggests a follow-up beyond binary emergence: at intermediate/high mutation, measure whether robust, lower-peak replicator families replace fragile fast copiers.

4. **Kruszewski & Mikolov (2020), “Emergence of Self-Reproducing Metabolisms as Recursive Algorithms in an Artificial Chemistry.”** [arXiv:2003.07916](https://arxiv.org/abs/2003.07916)
   Closest comparison for conserved combinators, resource economies, and acquire/decompose/reassembly cycles. The selective symbol depletion observed here motivates their metabolic-flow analyses.

5. **Hickinbotham & Stepney (2020), “Innovation, Variation, and Emergence in an Automata Chemistry.”** [ALIFE 2020 proceedings](https://direct.mit.edu/isal/proceedings/isal2020/32/753/98477)
   Useful for interpreting mutation, parasites, and replicator robustness in Stringmol; provides phenotype-level analyses missing from aggregate entropy alone.

6. **Dolson et al. (2019), “The MODES Toolbox: Measurements of Open-Ended Dynamics in Evolving Systems.”** [DOI:10.1162/artl_a_00280](https://doi.org/10.1162/artl_a_00280)
   Provides change, novelty, complexity, and ecological-potential metrics needed to distinguish transient organization from open-ended dynamics.

7. **Sayama (2024), “Self-Reproduction and Evolution in Cellular Automata: 25 Years After Evoloops.”** [arXiv:2402.03961](https://arxiv.org/abs/2402.03961)
   The structural-dissolution lesson is directly relevant if critical-symbol depletion creates frozen tape debris in Stage 2.

## Bottom line

The simulator passed its mechanical checks across all runs. The pilots reveal two scientifically useful regimes: **selective, bursty symbol scarcity under conservation**, and a **mutation-dependent heredity threshold** at paper scale. The strongest new hypothesis is that intermediate conservation may increase organization while very tight scarcity suppresses it and a very loose reservoir removes that organizing constraint. Replicates are required before treating that pattern as a robust effect.
