# Decision after the continuous opcode-composition experiment

## Decision

**The preregistered continuous locality hypothesis passed. The historical Phase 2 acceptance NO-GO remains unchanged.**

Twenty new baseline-mutation runs compared radius 1 with radius 8 on ten matched unseen seeds. Every run completed, conserved all symbols exactly, recorded zero invariant failures, and met mechanical feasibility.

## Primary result

The primary endpoint was neighbor Jensen–Shannon similarity over eleven-part tape compositions: ten BFF opcode proportions plus aggregate non-opcode proportion.

Radius-1 minus radius-8 JS-similarity excess:

- mean paired effect: **+0.005173**;
- median paired effect: **+0.005282**;
- 95% paired bootstrap interval: **[+0.003828, +0.006607]**;
- exact one-sided paired sign-flip: **p = 0.000977**;
- positive effects: **10/10 seeds**;
- mechanically feasible: **10/10 at each radius**.

All frozen decision criteria passed.

## Within-treatment context

- Radius 1 mean JS excess: **+0.006149**.
- Radius 8 mean JS excess: **+0.000976**.
- Radius-1 within-run tests were significant in **10/10** runs.
- Radius-8 within-run tests were significant in **1/10** runs.
- Mean late occupancy was nearly identical: approximately **0.7722** versus **0.7719**.

The absolute difference is modest because the composition vectors are dominated by shared non-instruction content, but its sign was consistent across every matched seed and its interval excluded zero.

## Relationship to earlier results

This result agrees with two independent observations:

1. positional byte-identity excess was positive and radius-sensitive;
2. local runs contained fewer private ordered opcode signatures than wider-radius runs.

It also explains why categorical block beta can fail while spatial structure is present. Jensen–Shannon similarity preserves graded differences between nonidentical opcode compositions; categorical beta reduces them to equal versus unequal labels.

## Supported claim

> Under baseline mutation and exact symbol conservation, radius-1 interaction produced greater local similarity in BFF instruction composition than radius-8 interaction over 5,000 ticks.

## Unsupported claims

The experiment does not establish:

- organism identity or organism-like patches;
- inherited lineages;
- functional equivalence of similar opcode compositions;
- monotonic behavior at every interaction radius;
- persistence of this continuous effect for 500,000 ticks;
- a retroactive pass of the frozen opcode block-beta criterion.

## Protocol consequence

For subsequent research, neighbor opcode-composition JS excess is a better identified spatial endpoint than exact ordered-signature block beta. It may be promoted only in a new protocol or phase, with its status and limitations stated in advance.

The next confirmatory choice is either:

1. test temporal persistence using a preregistered longer matched-radius campaign; or
2. move to a model-development stage with explicit conserved reproduction and lineage, where organism-level patch hypotheses become meaningful.

No further mutation tuning is recommended.
