# Decision after the opcode-beta mechanistic follow-up

## Decision

**Keep the Phase 2 NO-GO. Do not tune mutation further.**

Forty preregistered runs tested radius 1 versus 8 and mutation 1/4,096 versus 1/16,384 on ten unseen matched seeds. All runs completed, conserved every symbol exactly, recorded no invariant failures, and met mechanical feasibility. The joint preregistered mechanism result nevertheless failed.

## Primary results

### H1: lower mutation should reduce ordered-opcode uniqueness locally

- Mean paired baseline-minus-low-mutation unique-fraction effect: **+0.004485**
- Exact one-sided sign-flip: **p = 0.291992**
- Holm decision: **failed**

Lowering mutation fourfold had little consistent effect at radius 1. It did not solve label sparsity.

### H2: lower-mutation locality should increase ordered-opcode block-2 beta

- Mean paired radius-1-minus-radius-8 beta-excess effect: **+0.238200**
- Seed effects were positive in 7/10 pairs
- Exact one-sided sign-flip: **p = 0.096680**
- Holm decision: **failed**

The average effect was in the predicted direction but heterogeneous and not statistically supported under the frozen two-test family.

## Secondary evidence

The preregistered secondary outcomes sharpen the diagnosis without becoming new confirmatory passes:

- radius 8 minus radius 1 ordered-signature unique fraction at low mutation: **+0.249366**, descriptive exact `p = 0.000977`;
- radius 1 minus radius 8 positional byte-identity excess: **+0.004797**, descriptive exact `p = 0.000977`;
- radius 1 minus radius 8 opcode-presence beta excess: **+0.248459**, descriptive exact `p = 0.026367`;
- mutation × radius interaction for ordered block-2 beta: only **+0.010030**.

Local interaction reproducibly creates sequence recurrence and byte-level spatial similarity. The fourfold mutation reduction was not the driver. Exact ordered opcode categories remain too sparse and seed-sensitive to provide a robust block-beta endpoint in this design.

## What was learned

1. **The negative acceptance result was not simply caused by excessive mutation.** Lower mutation did not consistently reduce local signature uniqueness.
2. **Locality is doing real structural work.** Radius-1 runs had substantially fewer private opcode signatures and stronger byte similarity than radius-8 runs.
3. **Categorical ordered-opcode beta is the weak link.** It discards graded similarity and depends on exact recurrence of long opcode sequences.
4. **Changing block size alone is insufficient.** The 2×2 ordered-label effect was positive on average but still inconsistent.
5. **The simulator remained mechanically robust.** All 40 follow-ups were live, conserved, and invariant-clean.

## Recommended next research

### Recommended: preregister a distance-based opcode spatial statistic

Use an opcode-frequency or opcode-sequence distance rather than exact categorical equality. Candidate statistics include:

- neighbor Jensen–Shannon similarity over ten-opcode frequency vectors;
- normalized opcode edit similarity;
- distance-decay or semivariogram curves over toroidal separation.

Validate the chosen statistic with synthetic clustered/null fixtures, freeze one endpoint, then test radius 1 versus 8 on new seeds at the unchanged baseline mutation. This tests the supported locality mechanism without tuning the simulator toward a desired result.

### Model-development track: explicit conserved reproduction

If the scientific goal is organism-like patches rather than only spatial sequence correlation, introduce a reviewed conserved birth operation with local offspring placement and parent–offspring lineage. The current Stage 2 system rewrites residents in place and has no interaction-driven offspring. Such a model change belongs to a new stage and requires a new preregistration.

## Prohibited interpretation

These follow-ups do not pass Phase 2, do not turn descriptive p-values into primary evidence, and do not justify another mutation search. The strongest defensible statement remains:

> Local interaction reproducibly increases byte-level similarity and opcode-sequence recurrence under exact conservation, but the preregistered categorical opcode block-beta endpoint was not robustly supported.
