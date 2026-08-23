# Guarded-copier v2: credential-gradient follow-up

**Preregistered before launch.** This follow-up extends v1's four credential regimes (6, 10, 14, and 18 functional-information bits). It holds the guarded-copier mechanism and all operational parameters fixed while adding the missing 8-, 12-, and 16-bit regimes and increasing replication in the sparse 14- and 18-bit regimes.

## Hypothesis

For a uniformly random initial soup, the probability that a replicate has at least one functional tape and reaches at least 50% functional occupancy by tick 512 decreases monotonically as functional information increases. In the guarded-copier family, this prediction follows from the exact decline in functional-basin density, `4^-(k + 1)`, as credential length `k` increases.

The confirmatory null is no negative association between functional information and the replicate-level takeover probability. This is a within-family result only; it does not estimate the discovery rate of BFF, Forth, or another language.

## Fixed protocol

Every random-initialization replicate uses the unchanged v1 mechanics:

- 256 tapes of 16 symbols from a four-symbol alphabet;
- shuffled, disjoint, ordered pairs (128 pairs/tick);
- mutation rate `1/4096` independently per byte per tick;
- 16-instruction budget; 512 ticks; and
- `COPY` enabled only by a `COPY + credential` prefix.

The v1 seeded-validation phase already verified the unchanged COPY action in all 80 seeded runs. V2 therefore tests random emergence only, not mechanism validity.

## Design and sample allocation

| Credential length (`k`) | Information (bits) | Seeds in v2 | Role |
|---:|---:|---:|---|
| 2 | 6 | 0–19 (20) | existing low-information anchor |
| 3 | 8 | 0–19 (20) | new intermediate |
| 4 | 10 | 0–19 (20) | existing anchor |
| 5 | 12 | 0–19 (20) | new intermediate |
| 6 | 14 | 20–119 (100) | expanded rare-event regime |
| 7 | 16 | 0–19 (20) | new intermediate |
| 8 | 18 | 20–119 (100) | expanded rare-event regime |

For `k = 2, 4, 6, 8`, v1's non-overlapping seeds 0–19 are pooled only in the prespecified combined analysis. Thus the combined totals are 40, 40, 120, and 120 for those four regimes. No condition is rerun with the same seed.

## Outcomes

**Primary outcome:** `takeover_by_512`, one when `takeover_tick` is non-null (functional count reaches at least 128) and zero otherwise.

**Secondary outcomes:** (1) `functional_by_512`, one when `first_functional_tick` is non-null, including tick -1; and (2) `time_to_first_functional`, with right censoring at 512 for no discovery. Initial functional tapes have time -1 and are retained in the secondary survival data as observed at baseline.

## Confirmatory analysis

The primary model is a binomial logistic trend model on the combined v1/v2, non-duplicate-seed replicate data:

`logit P(takeover_by_512 = 1) = alpha + beta * functional_information_bits`.

The one-sided confirmatory alternative is `beta < 0`; report the coefficient, odds ratio per two additional information bits, 95% confidence interval, and one-sided p-value at `alpha = 0.05`. Because complete or quasi-complete separation is plausible at low information, the fitted model must use a documented bias-reduced (Firth) logistic implementation. If that implementation cannot be executed reproducibly in the project environment, the prespecified fallback is an exact one-sided Cochran–Armitage trend test with the same ordered bit scores. The fallback does not change the endpoint or directional hypothesis.

As a descriptive robustness analysis, fit the same trend to `functional_by_512`. A discrete-time rare-event survival model for `time_to_first_functional` may be reported as exploratory only, with the stated right censoring and baseline events; it is not used to replace the primary test.

No additional exclusions are permitted except failed runs recorded in their manifests. Results will show all denominators, failed-run count, and raw outcome counts by condition. No stopping, model, endpoint, or seed allocation changes will be made after launch.

## Post-launch implementation correction

The v2 script ran seeds 0–19 for `k = 2` and `k = 4`, which duplicate v1's deterministic seed IDs despite this preregistration incorrectly describing them as non-overlapping. Those 40 output directories are retained as reproducibility checks but **must not be pooled with v1** or counted as independent observations. This was identified while reconciling manifests after completion, before any confirmatory model was fit; it is a data-accounting correction, not an outcome-based analysis change. The combined confirmatory dataset uses v1 alone for `k = 2` and `k = 4`, v2 alone for `k = 3`, `5`, and `7`, and the non-overlapping v1+v2 seeds for `k = 6` and `k = 8`.
