# Compressibility benchmark: compress-full-f1200-t10000-s7

Exact Rust run: seed `7`, founders `1200`, ticks `10000`, final population `14166`.

## Cohort representation estimates

| policy | median represented | mean represented | final represented | final protected | final classes | signal |
|---|---:|---:|---:|---:|---:|---|
| lineage_safe | 100.0% | 100.0% | 100.0% | 10874 | 2448 | little or no compression signal |
| species_safe | 99.9% | 99.9% | 99.7% | 10110 | 1600 | little or no compression signal |
| trait_only | 84.5% | 84.8% | 83.9% | 10097 | 550 | weak compression signal |

`represented` is protected individuals plus up to the configured number of representative particles in every non-protected class. It excludes implementation overheads and therefore measures opportunity, not predicted wall-clock speedup.

## Event and protection lower bounds

| diagnostic | mean population fraction | final population fraction |
|---|---:|---:|
| exact_policy_keys | 100.0% | 100.0% |
| rare_lineage_organisms | 49.9% | 16.1% |
| rare_species_organisms | 2.5% | 0.4% |
| novel_organisms | 9.8% | 10.0% |
| physiology_critical | 57.4% | 63.4% |
| low_reserve | 18.9% | 19.0% |
| post_lifespan | 10.0% | 6.3% |
| action_due_now | 0.2% | 0.2% |
| action_due_within_8 | 100.0% | 100.0% |
| nonempty_gut | 21.7% | 22.3% |

## Interpretation guardrails

- `exact_policy_keys` estimates exact-state batching; a value near 100% means lazy events alone cannot merge current states.
- Cohort representative particles carry phenotype, reserve, age, toxin, and inventory distributions rather than making those dimensions separate class keys.
- `lineage_safe` is the strongest evolutionary-conservation diagnostic.
- `species_safe` permits merging common lineages within a species and therefore needs drift validation.
- `trait_only` is an exploratory upper bound and is not safe for rare lineages.
- Frequent independent actions, digestion, spatial conflicts, output, or cohort churn can keep total work linear even when upkeep compresses.
- A fragmented ecology must fall back to finer classes; no preset guarantees sublinear scaling.

## Run integrity

- Final digest: `8667676842432433732`
- Elements conserved: `True`
- Energy conserved: `True`
- Simulation time: `165.701s`
- Metric observation time: `0.256s` (0.15% of measured total)
