# AC-I001 demand-matched functional-origin confirmation preregistration

**Frozen before confirmation execution:** 2026-09-12

## Question

Does deprivation of the previously defined canonical structural class
`S = {0,44,60,91,93,125}` suppress functional BFF replicator origin more than a
symbol-independent control with mechanically matched blocked-write load?

The failed fixed-grid calibration remains failed. AC-R001 independently
validated the replacement rejection rate `0.27555027572734614` on new
mechanics-only seeds. This confirmation is the first test allowed to inspect
emergence outcomes under that rate.

## Frozen design

Use 20 new matched seeds `202611000`–`202611019`. For every seed, initialize the
same deterministic 32,768-tape random soup and run three exact-conservation arms:

1. **control:** histogram-matched conserved pool;
2. **natural-six:** zero initial pool supply of `{0,44,60,91,93,125}`, with mass
   redistributed by the existing largest-remainder rule; and
3. **friction:** histogram-matched pool with symbol-independent rejection rate
   `0.27555027572734614`.

All arms use 100,000 epochs, mutation `1/4096`, pool multiplier 2, 8,192 maximum
reads per interaction, shuffled disjoint pairing, serial within-run execution,
and callbacks every 100 epochs. Independent runs may execute concurrently.

## Functional-origin endpoint

Functional observation uses the committed `paper-selfrep-v1-top1024-abundance-lex-ties`
rule:

- high-order entropy must be at least 1 bit/byte for ten consecutive callbacks;
- at each contemporaneously eligible callback, rank exact tapes by descending
  abundance with lexicographic stable ties and test at most 1,024;
- use the unchanged paper functional evaluator with base seed 0 and rank offset;
- origin qualifies only if at least one candidate scores exactly 64;
- save the first qualifying callback and full conserved state; never backdate or
  substitute a later checkpoint after qualification.

The primary outcome is one binary functional-origin incidence per independently
initialized seed and arm. Entropy alone does not count.

## Frozen gates

All following conditions are mandatory for class-specific support:

1. **Integrity:** all 60 runs finish successfully with zero conservation
   residual and complete verified artifacts.
2. **Positive controls:** control and friction each produce functional origin in
   at least 5/20 seeds.
3. **Full-run mechanical match:** friction/natural-six median total blocked-write
   ratio lies in `[0.8,1.25]`, and at least 16/20 paired count ratios lie in
   `[0.67,1.5]`.
4. **Selective incidence contrast:** for both friction versus natural-six and
   control versus natural-six, the paired incidence difference is at least 0.20
   and the exact one-sided McNemar/binomial test on discordant pairs gives
   `p <= 0.05` in the predicted direction.
5. **Nonspecific-control viability:** friction incidence is no more than 2/20
   below control incidence. This bounded descriptive requirement is not an
   equivalence claim.

If any gate fails, AC-I001 fails and AC-I002–AC-I004 stop. Do not change seeds,
horizon, evaluator seed, candidate count, callback schedule, rejection rate, or
acceptance thresholds after launch.

## Secondary outcomes

Report without gate tuning: origin epoch, entropy trajectory, maximum functional
score, score-64 candidate abundance/composition, final symbol composition,
time to first blocked changing write, block category totals, and exact
conservation. Save all eligible callback assays and first-origin checkpoints.

## Statistics and claims

Use exact paired discordance tests for incidence and report raw paired tables.
Do not interpret a nonsignificant contrast as equivalence. A pass supports only
a class-specific functional-origin filter in this artificial conserved chemistry;
it does not establish adaptation, ecological organization, communication,
self-maintenance, or organism identity.

## Runtime benchmark and execution plan

A disjoint control benchmark seed (`202610099`) completed the full
32,768×100,000 functional-observation path in 4,808.6 seconds and used about
25 MB without an eligible assay callback. That seed is excluded from analysis;
its scientific outcomes do not affect any threshold. Execute at most seven run
processes concurrently on the eight-logical-CPU host with
`NUMBA_NUM_THREADS=1`, leaving one CPU for monitoring and avoiding nested assay
oversubscription. Publish raw runs centrally after deterministic analysis.
