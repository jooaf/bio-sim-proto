# Compressibility benchmark: compress-calibration-v3-f1200-t1000-s7

Exact Rust run: seed `7`, founders `1200`, ticks `1000`, final population `1253`.

## Cohort representation estimates

| policy | median represented | mean represented | final represented | final protected | final classes | signal |
|---|---:|---:|---:|---:|---:|---|
| lineage_safe | 100.0% | 100.0% | 100.0% | 1253 | 0 | little or no compression signal |
| species_safe | 100.0% | 100.0% | 100.0% | 773 | 279 | little or no compression signal |
| trait_only | 82.1% | 75.9% | 84.4% | 745 | 117 | weak compression signal |

`represented` is protected individuals plus up to the configured number of representative particles in every non-protected class. It excludes implementation overheads and therefore measures opportunity, not predicted wall-clock speedup.

## Event and protection lower bounds

| diagnostic | mean population fraction | final population fraction |
|---|---:|---:|
| exact_policy_keys | 100.0% | 100.0% |
| rare_lineage_organisms | 100.0% | 100.0% |
| rare_species_organisms | 7.3% | 5.1% |
| novel_organisms | 11.2% | 11.5% |
| physiology_critical | 37.7% | 50.2% |
| low_reserve | 22.1% | 27.3% |
| post_lifespan | 7.7% | 13.2% |
| action_due_now | 0.1% | 0.0% |
| action_due_within_8 | 100.0% | 100.0% |
| nonempty_gut | 13.2% | 14.0% |

## Interpretation guardrails

- `exact_policy_keys` estimates exact-state batching; a value near 100% means lazy events alone cannot merge current states.
- Cohort representative particles carry phenotype, reserve, age, toxin, and inventory distributions rather than making those dimensions separate class keys.
- `lineage_safe` is the strongest evolutionary-conservation diagnostic.
- `species_safe` permits merging common lineages within a species and therefore needs drift validation.
- `trait_only` is an exploratory upper bound and is not safe for rare lineages.
- Frequent independent actions, digestion, spatial conflicts, output, or cohort churn can keep total work linear even when upkeep compresses.
- A fragmented ecology must fall back to finer classes; no preset guarantees sublinear scaling.

## Run integrity

- Final digest: `1096355010383785383`
- Elements conserved: `True`
- Energy conserved: `True`
- Simulation time: `3.301s`
- Metric observation time: `0.034s` (1.02% of measured total)
