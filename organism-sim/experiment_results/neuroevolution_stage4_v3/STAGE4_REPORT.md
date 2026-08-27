# Stage 4 endogenous recurrent-memory report

Protocol: `440c187e98b84757c44f79346efd2a3c84aedf56964442d94bfdf1841fee1f7f`

**Transparent analysis-loader amendment:** the frozen loader aborted when any preregistered invariant exclusion existed. After the batch, only exclusion handling was repaired so paired tests use available valid seeds as the preregistration specifies. Endpoints, alternatives, thresholds, bootstrap seed/count, sign-flip tests, Holm correction, and decision rules are unchanged.

Frozen analyzer hash: `6159d4c714f8a8e0b9682f8b9161c6c1c678d2ef25c11c4c7c1cff7e59f313aa`; executed analyzer hash: `acc60ab7b7b730efaeacca8e0c75c31f99304131f489a87612e24470bb3ad29f`.

## Primary preregistered tests

| Test | Valid pairs | Mean difference | 95% bootstrap CI | Raw p | Holm p | Result |
|---|---:|---:|---:|---:|---:|---|
| P1 | 11 | 40969 | [15820, 71452] | 0.00048828 | 0.0024414 | significant, positive |
| P2 | 11 | -14039 | [-50549, 16104] | 0.46484 | 1 | not positive/significant |
| P3 | 9 | 177.78 | [-1196.8, 1710.4] | 0.41211 | 1 | not positive/significant |
| P4 | 12 | 0.0047502 | [0.0015489, 0.0082927] | 0.00024414 | 0.0014648 | significant, positive |
| P5 | 12 | -5.961e-05 | [-0.0001273, -4.7367e-06] | 0.95312 | 1 | not positive/significant |
| P6 | 9 | 0.0060862 | [-0.0044195, 0.020594] | 0.27734 | 1 | not positive/significant |

## Treatment summaries

| Treatment | Final population mean (range) | Extinctions | Births mean | Genetic recurrent expression | Recurrent energy | Ambiguous events | Argmax change | Stateful return | Zero-state return |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| legacy_control | 1082.8 (354–3968) | 0 | 4596.3 | 0 | 0.000 | 0 | NA | NA | NA |
| linear_priors | 41440.6 (2419–150802) | 0 | 81791.5 | 0 | 0.000 | 0 | NA | NA | NA |
| linear_random | 476.8 (153–1124) | 0 | 2328.3 | 0 | 0.000 | 0 | NA | NA | NA |
| recurrent | 41881.9 (2126–201160) | 0 | 92417.0 | 0.0688846 | 2681.047 | 2243281 | 0.01146 | 0.021323 | 0.02135 |
| recurrent_lesion | 8689.2 (2267–16824) | 0 | 33583.9 | 0.0268394 | 259.068 | 179502 | 0 | 0.018362 | 0.018362 |
| recurrent_zero_cost | 31403.1 (2158–238146) | 0 | 78694.7 | 0.0374332 | 0.000 | 1429733 | 0.003793 | 0.01166 | 0.011657 |

## Preregistered exclusions

| Seed | Treatment | Reason | Last valid tick | Last valid population | Last valid energy error |
|---:|---|---|---:|---:|---:|
| 211 | recurrent_lesion | invariant_or_incomplete_run | 3750 | 170232 | -2.836e-06 |
| 701 | recurrent_lesion | invariant_or_incomplete_run | 3500 | 230195 | 1.3936e-06 |
| 1103 | linear_priors | invariant_or_incomplete_run | 3500 | 344605 | 2.3305e-06 |
| 1103 | recurrent_lesion | invariant_or_incomplete_run | 3750 | 251999 | 1.2837e-06 |
| 1103 | recurrent_zero_cost | invariant_or_incomplete_run | 3500 | 205900 | 1.3582e-06 |

## Preregistered verdict

The full preregistered convergence rule is not satisfied. The result does not support a claim of evolved ecological memory. Individual positive effects remain narrower nonlinear, state-dependence, or exploratory findings.

Extinctions, null effects, adverse effects, invariant status, and neural numerical errors are retained in the tables. No endpoint was optimized by the simulator.
