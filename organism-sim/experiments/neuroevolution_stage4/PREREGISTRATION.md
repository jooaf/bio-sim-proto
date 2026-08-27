# Stage 4 preregistration: endogenous recurrent memory

**Protocol status:** Version 3 frozen before valid Stage 4 matrix data generation.

**Pre-data mechanical amendments:** Version one rejected `legacy_control` at tick zero because the runner incorrectly expected V2 observation/intent schema identifiers for every treatment. Version two corrected those identifiers but still expected legacy brain schema 1 rather than the implemented inactive value 0, and also stopped at tick zero. Neither attempt produced interval data or a completed run. Failed directories are retained as `experiment_results/neuroevolution_stage4_invalid_v1` and `experiment_results/neuroevolution_stage4_invalid_v2`. Version three validates legacy schema `1/1/0` and V2 schema `2/2/1`; no treatment, seed, coefficient, endpoint, threshold, or statistical rule changed.

## Scientific question

Does costly, initially dormant recurrent state become ecologically useful under ordinary endogenous reproduction in the spatial deposit ecology?

The simulator supplies no fitness, reward, episode, archive, parent ranking, or external optimizer. All reproduction, mutation, survival, and death remain ordinary kernel mechanics. Analysis telemetry is observational and cannot alter candidate scores, random draws, actions, inheritance, or world state.

## Frozen implementation

- Behavior schema: `recurrent_intent_v2`, observation schema 2, intent schema 2, brain schema 1.
- Neural dimensions: 28 observations, 16 candidate features, 10 intent kinds, 8 hidden/recurrent units, 451 direct loci, 528 recurrent loci, 979 total loci.
- Founder recurrence-expression and retention centers/spreads: exactly zero.
- Brain costs, as fractions of reference energy per upkeep tick: base `0.001`, maximum hidden `0.002`, maximum recurrent `0.002`.
- Recurrent-state lesion: clear and withhold recurrent state while retaining the same genome, developmental hidden path, and expression costs.
- Memory probe: observational counterfactual evaluation of the same current observation and candidate set with actual prior state versus zero state. It consumes no RNG and does not commit the counterfactual.
- Ambiguous food-loss event: current maximum directional food signal `<= 1e-6`, previous-decision maximum directional food signal `>= 0.05`, and a valid previous egocentric sector.
- Return choice: deterministic score argmax is a move into the previous strongest food sector. Ties use canonical first-candidate order.

No behavior coefficients or analysis thresholds may change after matrix generation begins. A simulator defect requires documenting the defect, invalidating the entire affected matrix, fixing it, and starting a newly versioned protocol.

## Fixed environment and run budget

- Engine: optimized Rust kernel through the PyO3 boundary.
- Founder region: `128 × 128`; world remains unbounded.
- Founders: `300`.
- Founder archetypes: `20`.
- Initial deposit positions: `2,600`.
- Deposit production rate: `0.10`; positions are spatially persistent while local availability changes through production and depletion.
- Tick budget: `4,000` per run.
- Observation/recording interval: every `250` ticks, including tick zero and tick 4,000.
- Explicit conservation audit: every recording interval and at termination.
- All other coefficients: `SimulationConfig` defaults at the frozen source fingerprint recorded in `protocol.json`.
- Extinction: retained as final population zero; the run still advances to the tick budget where possible.

## Fixed seeds

Twelve independent seeds:

```text
101, 211, 307, 401, 503, 601, 701, 809, 907, 1009, 1103, 1201
```

No seed is replaced because of extinction or an unfavorable result. A run is excluded only for an invariant failure, non-finite recorded metric, crash, schema mismatch, or output corruption. Exclusions are reported, not silently replaced.

## Treatments

| Label | Behavior | Founder priors | State lesion | Recurrent cost | Probe |
|---|---|:---:|:---:|---:|:---:|
| `legacy_control` | legacy macro V1 | n/a | no | n/a | no |
| `linear_priors` | linear intent V2 | yes | no | n/a | no |
| `linear_random` | linear intent V2 | no | no | n/a | no |
| `recurrent` | recurrent intent V2 | yes | no | `0.002` | yes |
| `recurrent_lesion` | recurrent intent V2 | yes | yes | `0.002` | yes |
| `recurrent_zero_cost` | recurrent intent V2 | yes | no | `0.0` | yes |

This is a `6 × 12 = 72` run matrix. Treatments never coexist within one ecology.

## Recorded metrics

At every interval:

- population, births, deaths, successful reproductions, species, and digest;
- intent counts/failures and movement count;
- total/base-derived, hidden, and recurrent brain energy paid;
- living-organism energy, age, generation, offspring-count, and lineage distributions;
- developed hidden/recurrent expression and retention distributions;
- genetic hidden/recurrent expression center means, recurrent spread means, and retention center means;
- recurrent-state L1 norm;
- memory-probe decisions, stateful-versus-zero argmax changes, ambiguous food-loss events, ambiguous changes, stateful return choices, and zero-state return choices;
- conservation and numerical-failure status.

Final living-organism columns are retained in compressed NPZ form. Metrics are post hoc observations and do not feed back into simulation.

## Primary endpoints and tests

The independent replicate is a seed. Treatment comparisons are paired by numeric seed. Effect estimates are mean paired differences with deterministic 95% bootstrap intervals (20,000 resamples; analysis seed `20260814`). P-values use exact paired sign-flip permutation tests. Directional hypotheses use one-sided tests; nonlinear-capacity P2 is two-sided. Six primary p-values receive Holm family-wise correction at `alpha = 0.05`.

1. **P1 interface viability:** final population, `linear_priors - linear_random`, one-sided positive.
2. **P2 nonlinear ecological effect:** final population, `recurrent - linear_priors`, two-sided.
3. **P3 memory ecological consequence:** final population, `recurrent - recurrent_lesion`, one-sided positive.
4. **P4 within-agent state dependence:** recurrent ambiguous argmax-change fraction is greater than zero, one-sided.
5. **P5 directional delayed-information use:** recurrent stateful-return fraction minus its zero-state counterfactual return fraction is positive, one-sided.
6. **P6 selected recurrent expression:** final living-population genetic recurrent-expression mean, `recurrent - recurrent_lesion`, one-sided positive.

Fractions with zero eligible events are recorded as missing for that endpoint, never changed to zero. A primary test requires at least eight valid paired seeds; otherwise it is underpowered/inconclusive.

## Secondary, explicitly exploratory endpoints

- births/founder, deaths, extinction count, generation, living energy, offspring count, and lineage concentration;
- developed recurrent expression and retention trajectories;
- `recurrent_zero_cost - recurrent` expression, testing whether metabolic cost suppresses neutral accumulation;
- recurrent energy premium per decision and per successful reproduction;
- state L1 norm and all-decision argmax-change fraction;
- expression-decile offspring distributions among final living organisms;
- descriptive legacy outcomes, which are not interface-matched.

Secondary intervals and p-values are labeled exploratory and are not used to rescue failed primary criteria.

## Decision rules

A claim of **evolved ecological memory** requires all of the following:

1. P3, P4, P5, and P6 have preregistered positive signs and Holm-adjusted `p < 0.05`;
2. recurrent expression is nonzero and numerical failures do not explain the effect;
3. effects are supported by at least eight valid seeds;
4. the recurrent energy premium is reported;
5. no invariant failure affected included runs.

P2 without the memory criteria supports only a nonlinear-controller effect. Rising recurrent genes without P3/P5 is drift or inconclusive, not memory. Null, mixed, adverse, and extinction outcomes are reported without retuning.

## Reproducibility and interruption

Each run writes an atomic manifest, interval JSONL, final NPZ, and completion record. Existing valid completed runs are skipped only when protocol and source fingerprints match. Interrupted partial runs restart from tick zero because the kernel has no checkpoint loader. Run order is fixed by seed, then the treatment order in the table. The analysis reads only complete runs matching `protocol.json`.
