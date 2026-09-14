# AC-P001 high-resource functional-origin viability preregistration

**Frozen before execution:** 2026-09-14

## Motivation and boundary

AC-I001 failed because the histogram-matched multiplier-2 control and matched
friction control produced zero functional origins in 20/20 seeds each. Therefore
class-specific chemistry cannot be tested at that regime, and AC-I002–AC-I004
remain stopped. This new experiment does not reinterpret or continue AC-I001.

Historical entropy-only work suggested that larger conserved reservoirs could
support transitions, but entropy was not functional replication. AC-P001 asks a
new bounded question: can the unchanged strict functional-origin endpoint produce
a repeatable positive-control incidence under a higher-resource exact-conservation
regime?

## Frozen design

Run ten new seeds `202612000`–`202612009`, each initialized independently with:

- 32,768 tapes of length 64;
- histogram-matched conserved pool multiplier 16;
- 100,000 epochs;
- mutation `1/4096`;
- 8,192 maximum reads per interaction;
- shuffled disjoint pairing and serial exact-pool execution;
- callbacks every 100 epochs; and
- committed functional observer
  `paper-selfrep-v1-top1024-abundance-lex-ties` unchanged.

The strict endpoint remains ten consecutive callbacks at high-order entropy at
least 1 followed by a contemporaneous score-64 tape among the top 1,024 exact
abundance-ranked tapes. Save the first qualifying conserved checkpoint and all
eligible assays.

## Gate

AC-P001 passes as a **functional-origin positive-control viability result** only
if:

1. all 10 runs succeed with zero conservation residual and verified artifacts;
2. at least 3/10 independently initialized seeds achieve functional origin; and
3. every counted origin has a persisted score-64 assay and checkpoint whose soup,
   pool, and conserved totals reconcile exactly.

The `3/10` threshold is a minimum repeatability screen, not a significance test.
On pass, preregister a new held-out multiplier-16 versus multiplier-2 comparison;
do not reuse AC-I001 outcomes as its confirmation controls. On failure, conclude
that de novo functional-origin discovery is not viable at the tested 32,768-tape,
100,000-epoch scales and stop this BFF origin campaign rather than tuning the
observer or extending successful-looking runs.

## Secondary reporting

Report origin epochs, entropy trajectories, functional scores and witness
abundances, block timing/totals, symbol composition, runtime, and storage. These
cannot rescue a failed incidence gate. A pass supports only repeatable functional
origin in a high-resource conserved artificial chemistry, not adaptation,
organization, ecology, or organism identity.

## Execution

Use at most seven concurrent processes and `NUMBA_NUM_THREADS=1`, as frozen by
the full-scale benchmark. Publish all raw runs centrally after completion.
