# Stage 4 Endogenous Neuroevolution Results

## Outcome

The preregistered Stage 4 experiment **does not support a claim of evolved ecological memory** under this protocol.

It does support two narrower conclusions:

1. founder viability priors strongly improved the V2 linear treatment relative to random V2 founders;
2. evolved recurrent state measurably changed some within-agent counterfactual argmax decisions.

State dependence was not translated into the preregistered delayed-food return behavior or a replicated ecological advantage. Recurrent expression alone is therefore not interpreted as memory utility.

The generated report and machine-readable analysis are under:

```text
experiment_results/neuroevolution_stage4_v3/
├── STAGE4_REPORT.md
├── analysis.json
├── primary_tests.csv
├── treatment_summary.csv
├── expression_deciles.csv
├── exclusions.csv
└── seed-*/<treatment>/
```

Protocol ID: `440c187e98b84757c44f79346efd2a3c84aedf56964442d94bfdf1841fee1f7f`.

## Frozen matrix

- 6 treatments;
- 12 fixed seeds;
- 300 founders and 20 archetypes per run;
- 4,000 ticks;
- observations and explicit conservation audits every 250 ticks;
- 72 attempted runs;
- 67 complete invariant-valid runs;
- 5 preregistered invariant exclusions.

Treatments were legacy macro, linear V2 with priors, linear V2 with random founders, recurrent V2, state-lesioned recurrent V2, and recurrent V2 with zero recurrent metabolic cost.

The five exclusions occurred only after populations reached approximately 170,000–345,000 organisms. Integer element conservation remained exact, but accumulated floating-point energy error exceeded the existing tolerance by roughly `1–3 × 10^-6`. Failed artifacts were retained and no seeds were replaced. All primary endpoints retained at least the preregistered minimum of eight paired seeds.

The frozen analysis loader initially aborted rather than applying its documented exclusion rule. After data generation, only paired-exclusion loading was repaired. The report records both analyzer hashes. No endpoint, direction, threshold, seed, bootstrap setting, permutation test, multiplicity correction, or claim criterion changed.

## Preregistered primary tests

Effects are seed-paired mean differences. Confidence intervals are deterministic 20,000-resample bootstrap intervals. P-values are exact paired sign-flip tests with Holm family-wise correction across six primary tests.

| Test | Valid pairs | Mean difference | 95% CI | Holm p | Interpretation |
|---|---:|---:|---:|---:|---|
| P1: linear priors − linear random population | 11 | +40,969 | +15,820 to +71,452 | 0.00244 | positive |
| P2: recurrent − linear population | 11 | −14,039 | −50,549 to +16,104 | 1.0 | no nonlinear ecological effect |
| P3: recurrent − lesion population | 9 | +178 | −1,197 to +1,710 | 1.0 | no memory-related ecological benefit |
| P4: ambiguous argmax changes versus zero | 12 | 0.00475 | 0.00155 to 0.00829 | 0.00146 | recurrent state sometimes affects decisions |
| P5: stateful − zero-state return fraction | 12 | −0.0000596 | −0.000127 to −0.00000474 | 1.0 | no beneficial delayed-food return; direction was adverse |
| P6: recurrent − lesion genetic expression | 9 | +0.00609 | −0.00442 to +0.02059 | 1.0 | no replicated expression difference |

The memory claim required P3, P4, P5, and P6 all to be positive and Holm-significant. Only P4 passed.

## Descriptive observations

Across all valid recurrent runs, the counterfactual probe evaluated more than 2.24 million ambiguous food-loss events. Prior state changed the deterministic argmax in about 1.15% of pooled events. Stateful return choices occurred in 2.132% of events versus 2.135% with state zeroed. Thus recurrent state was active but did not improve the specified behavior.

Mean final genetic recurrent expression was:

- recurrent: `0.0689`;
- state lesion: `0.0268`;
- zero recurrent cost: `0.0374`.

These unpaired descriptive means are affected by differential high-population exclusions and cannot replace P6. Recurrent expression also showed no monotonic living-organism offspring advantage: final offspring means generally declined across expression deciles in the normal recurrent treatment. This is exploratory and survivor-biased, but it argues against interpreting expression growth as straightforward adaptive memory.

The normal recurrent arm paid mean cumulative recurrent energy of approximately 2,681 reference-energy units per valid run. No neural numerical failures occurred.

## Interpretation

The experiment distinguishes **capacity**, **state dependence**, and **utility**:

- Unit tests establish that the recurrent architecture can distinguish identical present observations after different histories.
- P4 establishes that ecologically evolved recurrent states sometimes alter decisions.
- P3 and P5 fail to show that those alterations improve the preregistered ecological or delayed-information outcomes.
- P6 fails to establish replicated selection for recurrent expression relative to lesion controls.

Therefore the correct result is a null memory-utility finding, not a failed implementation and not evidence that memory cannot evolve in other endogenous niches.

## Limitations and principled follow-ups

1. The ordinary deposit ecology may not create a strong enough temporally aliased niche. A future, separately preregistered environment should strengthen intermittent directional information without supplying rewards or changing endogenous reproduction.
2. Very large population trajectories exposed a scale-dependent audit-tolerance limitation. This should be resolved independently of treatment outcomes before another large matrix.
3. The state probe used deterministic score argmax while actual actions are sampled. A future analysis may preregister same-draw counterfactual sampling, but it must not be retrofitted to this result.
4. Expression can drift through dormant bounded weights. Safe mutation or discrete recurrence remain separate future treatments, not post hoc changes to this matrix.
5. Group means are highly variable and, for treatments with exclusions, not directly comparable. Paired tests are authoritative.
