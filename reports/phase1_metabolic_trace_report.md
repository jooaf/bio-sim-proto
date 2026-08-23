# Phase 1 explicit metabolic path-tracing results

## Scope

Nine 20,000-epoch BFF runs reconstructed one deterministic token labeling of the conserved byte pool. Token labels are bookkeeping only; byte-level trajectories were regression-tested against the unlabelled probe and were identical.

## Results

| Multiplier | Cross-tape reacquisitions | Cross fraction | Cross-edge density | Reciprocal pair fraction | Extreme-epoch largest-interaction share | Extreme top-symbol share | Budget exhausted |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 1,416,426 | 59.3% | 100.0% | 99.9% | 80.4% | 99.1% | 100.0% |
| 2 | 1,574,410 | 73.7% | 100.0% | 100.0% | 97.8% | 99.9% | 100.0% |
| 16 | 3,806,127 | 67.5% | 100.0% | 100.0% | 57.8% | 100.0% | 19.8% |

## Hypothesis decisions

- **M1 supported:** every run contained returned tokens that were later withdrawn again.
- **M2 supported:** every run contained pool-mediated transfer from one persistent tape ID to another.
- **M3 mechanically supported but not ecologically specific:** reciprocal edges and directed cycles are abundant. The flow graph is nearly complete, indicating well-mixed circulation rather than a sparse, persistent metabolic organization.
- **M4 partially supported:** at multipliers 0.5 and 2, the most blocked 1% of epochs were dominated by one full-budget interaction requesting almost one symbol exclusively. At multiplier 16, the top symbol was still exclusive, but the largest interaction explained only about 58% of epoch blocking and exhausted the budget in about 20% of extreme epochs. Extreme bursts are local long loops in the constrained regimes, while the rare loose-pool events are less uniformly explained by budget exhaustion.

## What an explicit path looks like

`reports/phase1_metabolic_path_examples.csv` contains ordered events for repeatedly recycled sampled tokens. Each row identifies the token's symbol, donor tape, receiver tape, pool residence time, requesting opcode, and template-source tape. Consecutive rows provide concrete acquire→return→reacquire paths.

## Scientific interpretation

The open Phase 1 requirement for explicit byte movement is satisfied as an auditable bookkeeping witness: matter leaves one tape, resides in the pool, and enters another, often repeatedly and cyclically. However, this is not evidence of an organism-like metabolism. Tape IDs are fixed, interactions are globally mixed, and the donor→receiver graph approaches a complete network. A metabolic organization would require persistent, statistically enriched subgraphs or functional closure above a shuffled-pair null model.

All runs had zero per-symbol residual, passed token uniqueness/placement checks, and had no sampled-event overflow.
