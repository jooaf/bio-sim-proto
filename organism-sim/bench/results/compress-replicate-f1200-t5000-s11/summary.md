# Compressibility benchmark: compress-replicate-f1200-t5000-s11

Exact Rust run: seed `11`, founders `1200`, ticks `5000`, final population `29742`.

## Cohort representation estimates

| policy | median represented | mean represented | final represented | final protected | final classes | signal |
|---|---:|---:|---:|---:|---:|---|
| lineage_safe | 100.0% | 100.0% | 100.0% | 27004 | 1808 | little or no compression signal |
| species_safe | 90.9% | 92.2% | 93.6% | 18893 | 1969 | little or no compression signal |
| trait_only | 66.1% | 67.9% | 69.5% | 18881 | 475 | weak compression signal |

`represented` is protected individuals plus up to the configured number of representative particles in every non-protected class. It excludes implementation overheads and therefore measures opportunity, not predicted wall-clock speedup.

## Event and protection lower bounds

| diagnostic | mean population fraction | final population fraction |
|---|---:|---:|
| exact_policy_keys | 100.0% | 100.0% |
| rare_lineage_organisms | 87.4% | 79.0% |
| rare_species_organisms | 2.3% | 0.0% |
| novel_organisms | 14.0% | 11.4% |
| physiology_critical | 45.4% | 54.0% |
| low_reserve | 45.2% | 54.4% |
| critical_reserve | 44.3% | 53.7% |
| near_integrity_death | 1.7% | 0.4% |
| near_debt_death | 3.5% | 5.2% |
| near_toxin_threshold | 6.4% | 7.0% |
| post_lifespan | 17.2% | 26.9% |
| active_status | 0.1% | 0.1% |
| action_due_now | 0.2% | 0.2% |
| action_due_within_8 | 100.0% | 100.0% |
| nonempty_gut | 9.8% | 8.4% |

## Interpretation guardrails

- `exact_policy_keys` estimates exact-state batching; a value near 100% means lazy events alone cannot merge current states.
- Cohort representative particles carry phenotype, reserve, age, toxin, and inventory distributions rather than making those dimensions separate class keys.
- Toxin-threshold and post-lifespan organisms remain cohort-eligible only because the proposed engine uses representative toxin/age distributions and bounded event counts; both require convergence tests.
- `lineage_safe` is the strongest evolutionary-conservation diagnostic.
- `species_safe` permits merging common lineages within a species and therefore needs drift validation.
- `trait_only` is an exploratory upper bound and is not safe for rare lineages.
- Frequent independent actions, digestion, spatial conflicts, output, or cohort churn can keep total work linear even when upkeep compresses.
- A fragmented ecology must fall back to finer classes; no preset guarantees sublinear scaling.

## Run integrity

- Final digest: `632449686735025681`
- Elements conserved: `True`
- Energy conserved: `True`
- Simulation time: `134.076s`
- Metric observation time: `0.263s` (0.20% of measured total)
