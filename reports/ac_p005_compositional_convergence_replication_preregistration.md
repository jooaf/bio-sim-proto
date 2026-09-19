# AC-P005 functional-origin compositional convergence replication preregistration

**Frozen before execution:** 2026-09-17

## Motivation and separation from prior failures

AC-P004 validly rejected its primary static structural-convergence hypothesis:
all usable witnesses had distinct opcode signatures and their Hamming distances
did not converge. That result remains negative. AC-P004's preregistered secondary
metric showed a small composition-JSD shift relative to immediate pre-origin
controls (observed median 0.713382 versus reference median 0.720477; lower-tail
reference probability 0.00009999). AC-P005 tests that composition-only signal on
new held-out origins. It cannot revive structural-class, resource-effect, or
opcode/Hamming claims.

## Frozen campaign

Run 20 new independently initialized seeds `202615000`–`202615019` under the
unchanged AC-P004 acquisition configuration:

- 32,768 tapes, histogram-matched pool multiplier 16;
- 100,000 epochs, mutation `1/4096`, and 8,192 maximum reads;
- callbacks every 100 epochs and exact serial conserved-pool execution;
- strict functional observer plus `pre-origin-control-v1` prospective snapshot;
- six concurrent processes (`logical CPUs - 2`) and `NUMBA_NUM_THREADS=1`.

A usable origin has the unchanged strict score-64 endpoint, complete integrity
and conservation, an immediately preceding persisted callback assay, and at
least one below-64 candidate in the witness's width-64 rank block or nearest
nonempty block under the frozen lower-block tie rule. Use every usable origin;
do not replace or extend runs.

The acquisition gate requires at least 6/20 usable origins. Fewer than six stops
the experiment without a composition conclusion.

## Frozen primary metric and local reference

Represent each 64-byte first-origin witness by its normalized 256-bin byte
histogram. Pairwise composition distance is base-2 Jensen–Shannon divergence,
without square root.

For each usable origin, use the frozen immediate pre-origin below-64 local pool.
Generate 10,000 deterministic reference replicates exactly as in AC-P004, with
one rank-authoritative candidate per pool, rejection-sampled uniform indexing,
with-replacement sampling across replicates, and SplitMix64 constant `0xAC005`
keyed by `replicate * n + checkpoint_index`.

Calculate observed median pairwise composition JSD and each replicate's median.
Report null quantiles 0.025, 0.5, and 0.975 and the add-one lower-tail reference
probability `(1 + count(null_median <= observed)) / 10001`.

## Frozen confirmation gate

Support **functional-origin compositional convergence relative to immediate
pre-origin controls** only if all are true:

1. all 20 runs pass run-level integrity;
2. at least six usable origins are acquired;
3. median reference composition JSD is positive;
4. observed median composition JSD is no more than 99% of the median reference
   median (at least a 1% reduction); and
5. the lower-tail reference probability is `<= 0.01`.

The 1% effect threshold is deliberately slightly stronger than the exploratory
AC-P004 ratio and is frozen before held-out execution. All criteria are
mandatory. Exact tapes, Hamming distance, opcode signatures, structural-symbol
shares, abundance, origin timing, and block mechanics are secondary and cannot
rescue a failed composition gate.

## Decision ladder and claims

- **Pass:** support a bounded, replicated composition-level convergence result
  among strict functional origins relative to local pre-origin controls. Design
  any causal composition perturbation as a separate future experiment.
- **Valid non-pass:** retain AC-P004's composition result as exploratory only and
  stop convergence work.
- **Unevaluable/integrity failure:** repair only a demonstrated implementation or
  artifact defect and rerun frozen code; do not add seeds or substitute controls.

A pass is not evidence of one structural class, common code, heredity,
maintenance, adaptation, ecology, organization, or organism identity. The
reference-tail probability is conditional on the frozen local-control model and
is not a general exchangeability test.
