# Compressibility benchmark: compress-smoke-f120-t200-s7

Exact Rust run: seed `7`, founders `120`, ticks `200`, final population `140`.

## Cohort representation estimates

| policy | median represented | mean represented | final represented | final protected | final classes | signal |
|---|---:|---:|---:|---:|---:|---|
| lineage_safe | 100.0% | 100.0% | 100.0% | 140 | 0 | little or no compression signal |
| species_safe | 100.0% | 100.0% | 100.0% | 120 | 20 | little or no compression signal |
| trait_only | 100.0% | 100.0% | 100.0% | 53 | 87 | little or no compression signal |

`represented` is protected individuals plus up to the configured number of representative particles in every non-protected class. It excludes implementation overheads and therefore measures opportunity, not predicted wall-clock speedup.

## Event and protection lower bounds

| diagnostic | mean population fraction | final population fraction |
|---|---:|---:|
| rare_lineage_organisms | 100.0% | 100.0% |
| rare_species_organisms | 84.6% | 67.1% |
| novel_organisms | 36.6% | 15.0% |
| physiology_critical | 15.4% | 32.9% |
| low_reserve | 10.0% | 22.9% |
| post_lifespan | 0.0% | 0.0% |
| action_due_now | 0.0% | 0.0% |
| action_due_within_8 | 100.0% | 100.0% |
| nonempty_gut | 21.9% | 14.3% |

## Interpretation guardrails

- `lineage_safe` is the strongest evolutionary-conservation diagnostic.
- `species_safe` permits merging common lineages within a species and therefore needs drift validation.
- `trait_only` is an exploratory upper bound and is not safe for rare lineages.
- Frequent independent actions, digestion, spatial conflicts, output, or cohort churn can keep total work linear even when upkeep compresses.
- A fragmented ecology must fall back to finer classes; no preset guarantees sublinear scaling.

## Run integrity

- Final digest: `17883094755708958126`
- Elements conserved: `True`
- Energy conserved: `True`
- Simulation time: `0.146s`
- Metric observation time: `0.002s` (1.27% of measured total)
