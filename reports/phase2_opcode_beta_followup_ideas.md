# Ideas after the Phase 2 opcode-beta NO-GO

## What failed

The frozen 500,000-tick run had positive opcode-signature q=1 beta excess (`+0.038534`) but the pooled permutation result was not significant (`p = 0.127`). This remains a failed acceptance criterion.

## Exploratory diagnosis

Post-decision inspection of the ten final-window snapshots found:

- mean ordered-opcode-signature unique fraction: **0.767**;
- mean fraction of tapes carrying a singleton signature: **0.687**;
- ordered-full beta remained nonsignificant at block sizes 2, 4, 8, and 16 in 199-permutation diagnostics;
- a coarse opcode-presence label reduced singleton prevalence to **0.278**;
- opcode-presence beta was strongest at 2×2 blocks (`p = 0.005`, exploratory);
- the first-eight-opcode prefix also showed exploratory structure at some scales.

The most likely statistical explanation is label sparsity: ordered opcode strings are still so specific that most tapes have private categories. The categorical beta statistic then has limited shared-type information even though positional byte similarity is reproducibly positive.

## Follow-up ideas

### 1. Test whether mutation fragments local opcode families

Lower background mutation from 1/4,096 to 1/16,384 while holding chemistry and interaction count fixed. Prediction: fewer private opcode signatures and stronger local categorical differentiation.

Caveat: this is a new mechanistic treatment, not a retroactive repair of the acceptance run.

### 2. Add a matched wide-radius control

Compare radius 1 with radius 8 using identical seeds. If local interaction creates the effect, reduced singleton prevalence alone is insufficient: radius 1 should exceed radius 8.

### 3. Match measurement scale to interaction scale

The frozen 8×8 blocks aggregate far beyond a radius-1 neighborhood. Test 2×2 blocks on unseen runs. Because this scale was selected after exploratory inspection, it is a follow-up metric and cannot replace the frozen 8×8 acceptance result.

### 4. Use functional coarse types

Possible labels include opcode presence, opcode-count vectors, bounded opcode prefixes, execution traces, write footprints, and halt-reason profiles. Opcode presence is cheap and identifiable, but it discards order and is only a syntax-capability proxy. Execution-derived labels would be more functional but require a carefully standardized assay.

### 5. Replace categorical identity with continuous instruction distance

Use Jensen–Shannon distance between opcode-frequency vectors, edit distance between opcode strings, or instruction-position identity. A distance-based spatial statistic retains information when every full category is unique.

### 6. Measure spatial correlation length directly

Estimate a semivariogram or distance-decay curve over tape and opcode similarity rather than selecting one block size. This could distinguish cell-scale patches from broad gradients.

### 7. Add explicit reproduction and local offspring dispersal

The current Stage 2 chemistry rewrites two resident tapes in place; interactions do not create offspring. Random reseeding is exogenous and globally located. Stable organism-like patches may require a conserved birth operation with local placement and parent–offspring lineage.

This is a model change suitable for a later stage, not a parameter sweep.

### 8. Couple persistence to behavior

Spontaneous/inert dissolution is not a fitness competition. A lifecycle where successful copying or resource processing changes persistence could allow coherent opcode organizations to be selected rather than merely rewritten.

### 9. Track lineage-defined patches

Content labels are brittle under mutation. Neutral lineage or inherited tags could test whether descendants remain spatially clustered even when their opcode strings diverge.

### 10. Test temporal stability, not only pooled magnitude

Report per-snapshot effects, sign consistency, residence times, and transitions between local families. A pooled positive mean can conceal intermittent structure.

## Selected bounded experiment

The immediate follow-up will test ideas 1–3 with a preregistered 2×2 matched factorial:

- interaction radius: 1 versus 8;
- mutation: 1/4,096 versus 1/16,384;
- ten unseen matched seeds;
- 5,000 ticks per run;
- unchanged conserved Stage 2 mechanics.

This design separates a mutation-driven identifiability change from a locality effect. It is bounded to 40 runs and cannot overturn the completed Phase 2 NO-GO.
