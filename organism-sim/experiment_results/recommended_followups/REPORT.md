# Recommended follow-up results

## Executive summary

All **40/40** runs completed and passed integrity checks. The split counters show which resource bottleneck dominates rather than treating all failed attempts as one category.

## F1 — 10,000-tick persistence

- Extinctions: **8/10**.
- Mean final retention: **0.1%** [0.0%, 0.3%].
- Median extinction tick among extinct runs: **5,300**.
- Mean births/death: **0.614**.
- Mean populations at ticks 2,500/5,000/7,500/10,000: **124.0 / 33.4 / 3.8 / 0.4**.
- Mean late-window population slope: **-0.0013 organisms/tick**; 0/10 were positive.
- Resource-block causes per attempt: energy **72.4%**, body matter **1.4%**, mate readiness **0.0%**.

## F2 — Reproduction cost × deposits

| Condition | Retention mean / median | Births/death mean / median | Resource blocked | Energy blocked | Body blocked | Mate blocked | Extinct |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cost-0p5_deposits-2600` | 100.1% / 20.7% | 0.691 / 0.596 | 91.7% | 91.0% | 0.7% | 0.0% | 0/5 |
| `cost-0p5_deposits-4900` | 30.9% / 21.7% | 0.615 / 0.525 | 60.2% | 58.7% | 1.5% | 0.0% | 0/5 |
| `cost-0p75_deposits-2600` | 93.3% / 19.3% | 0.681 / 0.584 | 92.2% | 91.5% | 0.7% | 0.0% | 0/5 |
| `cost-0p75_deposits-4900` | 31.3% / 20.3% | 0.605 / 0.515 | 60.1% | 59.1% | 1.1% | 0.0% | 0/5 |

Best median-retention cell: `cost-0p5_deposits-4900` at **21.7%**; heavy-tailed seed outcomes make medians more representative than means here.

Factor effects (five independent seed blocks):

- Cost 0.50 retention: +0.033 [+0.008, +0.061] (5+/0− pairs, exact p=0.0625).
- Cost 0.50 replacement: +0.011 [+0.006, +0.016] (5+/0− pairs, exact p=0.0625).
- Cost 0.50 energy blocking: -0.005 [-0.014, +0.004] (2+/3− pairs, exact p=0.5000).
- Deposits 4,900 retention: -0.656 [-1.625, +0.163] (3+/2− pairs, exact p=0.5000).
- Deposits 4,900 energy blocking: -0.324 [-0.483, -0.165] (0+/5− pairs, exact p=0.0625).

## F3 — Founder archetypes

| Archetypes | Retention | Births/death | Living species | Evenness | Resource blocked |
|---:|---:|---:|---:|---:|---:|
| 21 | 45.3% | 0.710 | 3.60 | 0.574 | 66.1% |
| 8 | 40.5% | 0.673 | 2.00 | 0.603 | 65.2% |

- 21-archetype living-species effect: +1.600 [+0.400, +2.800] (3+/0− pairs, exact p=0.2500).
- 21-archetype retention effect: +0.048 [-0.047, +0.127] (4+/1− pairs, exact p=0.4375).
- 21-archetype evenness effect: -0.029 [-0.369, +0.372] (2+/3− pairs, exact p=0.8750).

## Interpretation

Across all runs, **99.3%** of resource blocks were energy blocks, **0.7%** were body-matter blocks, and mate-readiness blocks were **0**. Mate readiness is normally filtered before `_attempt_reproduction`, so zero confirms that this guard is not a runtime bottleneck.

Lower reproduction cost produced small, consistent improvements in retention and births/death, but barely changed energy blocking. More deposits strongly reduced energy blocking in every seed, yet did not consistently improve retention or replacement. Deposit count is initialized before founders using one RNG stream, so changing deposits also changes the realized founder draw; the deposit survival contrast is therefore noisy and should be repeated after RNG streams are separated.

The 10K study rejects 2,500-tick retention as evidence of persistence: eight runs went extinct and the two survivors had only three and one organisms. Five-pair factorial and founder effects are estimates, not significance claims; their minimum two-sided exact p-value is 0.0625.

## Reproducibility

- Raw runs: `experiment_results/recommended_followups/runs/`
- Per-run summary: `experiment_results/recommended_followups/run_summary.csv`
- Group summary: `experiment_results/recommended_followups/group_summary.csv`
- Paired effects: `experiment_results/recommended_followups/paired_contrasts.csv`
- Runner: `experiments/run_recommended_followups.nu`
- Analyzer: `analyses/analyze_recommended_followups.py`
