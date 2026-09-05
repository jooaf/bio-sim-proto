# Phase 2 opcode-beta mechanistic follow-up

## Decision

Joint preregistered mechanism result supported: **False**.

- H1 mean baseline-minus-low-mutation unique-fraction effect: 0.004485
- H1 exact one-sided p: 0.291992; Holm pass: **False**
- H2 mean radius-1-minus-radius-8 block-2 beta-excess effect: 0.238200
- H2 exact one-sided p: 0.096680; Holm pass: **False**
- Low-mutation radius-1 mechanical feasibility: 10/10

These 5,000-tick follow-ups cannot overturn the completed 500,000-tick NO-GO.

## Factorial cells

| radius | mutation | feasible | unique fraction | singleton fraction | ordered block-2 excess | median within-run p | old block-8 excess | presence block-2 excess | byte excess |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.00006104 | 10/10 | 0.709 | 0.624 | 0.160055 | 0.320 | 0.064642 | 0.315393 | 0.005853 |
| 1 | 0.00024414 | 10/10 | 0.714 | 0.624 | 0.210356 | 0.277 | 0.022402 | 0.430931 | 0.006186 |
| 8 | 0.00006104 | 10/10 | 0.958 | 0.935 | -0.054033 | 1.000 | -0.007872 | 0.018243 | 0.001610 |
| 8 | 0.00024414 | 10/10 | 0.926 | 0.891 | -0.012539 | 0.702 | 0.020083 | 0.058174 | 0.001418 |

## Matched primary effects

- H1 seed effects: 0.013601, -0.001760, 0.006377, 0.052568, -0.021697, -0.015824, -0.007489, 0.006785, 0.016974, -0.004683
- H2 seed effects: 0.702286, -0.430898, 0.685077, 0.321323, -0.277125, 0.951005, -0.048103, 0.799907, -0.415728, 0.094254

## Frozen secondary and descriptive contrasts

- Baseline-mutation radius-1-minus-radius-8 block-2 beta effect: 0.228170; exact p = 0.115234
- Mutation × radius interaction (low-mutation radius effect minus baseline radius effect): 0.010030
- Low-mutation radius-8-minus-radius-1 unique-fraction effect: 0.249366; exact p = 0.000977
- Low-mutation radius-1-minus-radius-8 byte-excess effect: 0.004797; exact p = 0.000977
- Low-mutation radius-1-minus-radius-8 opcode-presence beta effect: 0.248459; exact p = 0.026367

These secondary p-values are descriptive and unadjusted; they are not additional passed hypotheses.

## Integrity

- Runs: 40
- Successful exits: 40/40
- Exactly conserved: 40/40
- Invariant failures: 0
- Mechanically feasible: 40/40

Secondary labels and scales are descriptive. A positive result motivates model/protocol design; it does not rewrite Phase 2 acceptance.
