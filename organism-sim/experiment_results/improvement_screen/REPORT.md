# Improvement-screen results

## Executive summary

All **40/40** screening runs and **10/10** adaptive confirmation runs completed for **50 total 2,500-tick experiments**. At the default 0.12 sexual floor, the maintenance-1.0 control retained **13.8%** of founders on average; the best-retention cell was `maint-0p75_floor-0p12` at **18.8%**.

- Combined 10-seed maintenance-0.75 retention effect: **+0.051 [+0.021, +0.086], exact p=0.0078, Holm p=0.0078**.
- Combined replacement-ratio effect: **+0.058 [+0.035, +0.082], exact p=0.0039, Holm p=0.0039**.
- Combined attrition-rate effect: **-0.335 [-0.430, -0.230], exact p=0.0039, Holm p=0.0039** deaths/1,000 organism-ticks.
- The largest sexual-event share was `maint-0p75_floor-0p50` at **13.0%**.

## Cell means

The floor-0.12 cells contain 10 seeds after confirmation; all other cells contain five.

| Condition | n | Retention | Births/death | Attrition/1K org-ticks | Sexual share | Success/attempt | Resource blocked | Extinct | Colonies |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `maint-0p75_floor-0p12` | 10 | 18.8% | 0.597 | 1.821 | 8.6% | 9.0% | 73.5% | 2/10 | 6/10 |
| `maint-0p75_floor-0p30` | 5 | 14.3% | 0.600 | 1.855 | 11.2% | 10.6% | 74.4% | 1/5 | 1/5 |
| `maint-0p75_floor-0p50` | 5 | 14.4% | 0.607 | 1.892 | 13.0% | 11.1% | 74.6% | 1/5 | 3/5 |
| `maint-0p75_floor-off` | 5 | 13.3% | 0.573 | 1.813 | 6.7% | 9.5% | 74.8% | 1/5 | 1/5 |
| `maint-1_floor-0p12` | 10 | 13.8% | 0.539 | 2.156 | 6.5% | 11.2% | 66.7% | 2/10 | 4/10 |
| `maint-1_floor-0p30` | 5 | 9.6% | 0.552 | 2.225 | 10.7% | 13.0% | 68.3% | 2/5 | 2/5 |
| `maint-1_floor-0p50` | 5 | 9.3% | 0.553 | 2.238 | 12.9% | 13.2% | 69.1% | 1/5 | 1/5 |
| `maint-1_floor-off` | 5 | 9.1% | 0.554 | 2.235 | 5.2% | 13.6% | 65.3% | 1/5 | 1/5 |

## Sexual-floor screening effects relative to 0.12

Each effect first averages the two maintenance cells within each seed, leaving five independent seed blocks. These are screening estimates; with n=5, the smallest possible two-sided exact p-value is 0.0625.

| Contrast | Sexual-share difference | Retention difference | Resource-block difference |
|---|---:|---:|---:|
| floor-off − 0.12 | -0.013 [-0.040, +0.002], exact p=0.6250, Holm p=0.6250 | -0.005 [-0.015, +0.000], exact p=0.5000, Holm p=1.0000 | -0.003 [-0.010, +0.004], exact p=0.5000, Holm p=0.7500 |
| floor-0p30 − 0.12 | +0.037 [+0.009, +0.081], exact p=0.1250, Holm p=0.5000 | +0.002 [-0.007, +0.012], exact p=0.7500, Holm p=1.0000 | +0.011 [-0.005, +0.031], exact p=0.3750, Holm p=0.7500 |
| floor-0p50 − 0.12 | +0.057 [+0.018, +0.098], exact p=0.1250, Holm p=0.5000 | +0.001 [-0.010, +0.014], exact p=1.0000, Holm p=1.0000 | +0.015 [+0.004, +0.029], exact p=0.1250, Holm p=0.3750 |

## What worked

- **Maintenance 0.75 is the only strongly supported general improvement.** Across all 10 paired seeds at floor 0.12 it improved retention and births/death while reducing exposure-adjusted attrition.
- **The five new seeds replicated the direction:** retention +0.041 [+0.011, +0.072], exact p=0.1250, Holm p=0.1250, replacement +0.064 [+0.051, +0.076], exact p=0.0625, Holm p=0.0625, and attrition -0.294 [-0.445, -0.129], exact p=0.1250, Holm p=0.1250. Exact significance is unattainable with only five two-sided pairs, so this is directional held-out support.
- **Best observed retention:** `maint-0p75_floor-0p12` (18.8%, n=10).
- **Higher sexual floors changed reproductive mode directionally:** floor 0.30 and 0.50 raised mean sexual share, but effects were not positive in every seed and the screening sample cannot provide p<0.05.
- **Conservation:** all runs had zero per-element residual; maximum energy error remained below 1.37e-08.

## What did not work

- **Sexual floor did not improve survival.** Relative to 0.12, floors 0.30 and 0.50 changed retention by only about 0–0.2 percentage points, with intervals spanning harm and benefit.
- **Maintenance relief did not solve reproduction scarcity.** It changed resource blocking by +0.068 [+0.053, +0.082], exact p=0.0020, Holm p=0.0020 and success per attempt by -0.022 [-0.034, -0.013], exact p=0.0020, Holm p=0.0020. More organisms survived long enough to attempt reproduction, but roughly 70% of attempts still lacked energy/body matter.
- **No condition reached replacement.** Even the best cell averaged only 0.607 births per death, and extinctions still occurred.
- **Colonies remained inconsistent.** Incidence varied from 1/5 to 3/5 in screening cells with no reliable floor or maintenance effect.

## Recommended next experiments

1. Run maintenance 0.75/floor 0.12 for 10,000 ticks on 10 new seeds to estimate extinction probability and late-window population slope.
2. Cross reproduction cost {0.50, 0.75} with deposits {2,600, 4,900} at maintenance 0.75/floor 0.12. This directly targets the unresolved resource block while separating reproductive cost from food availability.
3. Split `reproduction_resource_blocks` into energy, reproductive-body, and mate-readiness counters before that sweep; the current combined counter limits causal diagnosis.
4. Test founder-archetype counts 8 versus 21 only with mutation and ecology fixed; the historical GUI runs confound these factors.
5. Treat floor 0.30 as the next moderate sexual-diversity candidate; 0.50 produced more sexual events but no survival gain and a directional rise in resource blocking.

## Statistical notes

Intervals are paired bootstrap percentile intervals over independent seeds. Exact p-values enumerate paired sign flips. The combined 10-seed maintenance result is nominal because the second five-seed allocation followed inspection of the screen, although H1 was specified before any runs. The separate new-seed contrast is the clean directional replication and has a minimum possible two-sided p-value of 0.0625. Screening factor effects average repeated cells within each seed before testing and receive Holm adjustment within each metric. Individual cell contrasts remain exploratory.
