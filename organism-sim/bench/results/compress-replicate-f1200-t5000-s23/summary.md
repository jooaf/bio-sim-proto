# Compressibility benchmark: compress-replicate-f1200-t5000-s23

Exact Rust run: seed `23`, founders `1200`, ticks `5000`, final population `3438`.

## Cohort representation estimates

| policy | median represented | mean represented | final represented | final protected | final classes | signal |
|---|---:|---:|---:|---:|---:|---|
| lineage_safe | 100.0% | 100.0% | 100.0% | 2830 | 372 | little or no compression signal |
| species_safe | 84.4% | 87.6% | 83.4% | 686 | 563 | weak compression signal |
| trait_only | 44.6% | 47.8% | 37.7% | 666 | 184 | moderate compression signal |

`represented` is protected individuals plus up to the configured number of representative particles in every non-protected class. It excludes implementation overheads and therefore measures opportunity, not predicted wall-clock speedup.

## Event and protection lower bounds

| diagnostic | mean population fraction | final population fraction |
|---|---:|---:|
| exact_policy_keys | 100.0% | 100.0% |
| rare_lineage_organisms | 84.2% | 78.5% |
| rare_species_organisms | 2.5% | 0.7% |
| novel_organisms | 8.2% | 5.8% |
| physiology_critical | 21.6% | 14.2% |
| low_reserve | 20.0% | 11.9% |
| critical_reserve | 19.5% | 11.7% |
| near_integrity_death | 1.9% | 2.1% |
| near_debt_death | 2.2% | 1.8% |
| near_toxin_threshold | 26.6% | 35.5% |
| post_lifespan | 15.5% | 22.4% |
| active_status | 0.6% | 0.6% |
| action_due_now | 0.1% | 0.1% |
| action_due_within_8 | 100.0% | 100.0% |
| nonempty_gut | 17.5% | 20.5% |

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

- Final digest: `456306364783143780`
- Elements conserved: `True`
- Energy conserved: `True`
- Simulation time: `28.585s`
- Metric observation time: `0.070s` (0.24% of measured total)
