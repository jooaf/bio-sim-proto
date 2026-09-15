# AC-P002 conserved-resource abundance and functional origin preregistration

**Frozen before execution:** 2026-09-14

## Motivation and independence

AC-P001 passed its preregistered viability screen: 4/10 independent
histogram-matched multiplier-16 soups achieved strict score-64 functional origin.
AC-I001 remains failed and closed. AC-P002 asks a distinct causal question about
total conserved reservoir abundance, not symbol-class deprivation, and uses only
new held-out matched seeds. AC-I001 multiplier-2 outcomes are not reused as
confirmation controls.

## Frozen design

Use 20 new seeds `202613000`–`202613019`. For each seed, initialize the same
32,768-tape soup and run two exact-conservation arms:

- **m2:** histogram-matched pool multiplier 2;
- **m16:** histogram-matched pool multiplier 16.

Both arms use 100,000 epochs, mutation `1/4096`, 8,192 maximum reads per
interaction, shuffled disjoint pairing, serial exact-pool execution, callbacks
every 100 epochs, and the unchanged observer
`paper-selfrep-v1-top1024-abundance-lex-ties`.

Functional origin remains exactly: ten consecutive callbacks with high-order
entropy at least 1 and a contemporaneous score-64 tape among the 1,024 most
abundant exact tapes. The first qualifying callback is saved with the full
conserved state.

## Frozen gates

Support for a resource-abundance effect requires all of:

1. all 40 runs succeed with zero conservation residual, verified artifacts, and
   internally consistent score-64 checkpoints;
2. m16 produces functional origin in at least 5/20 seeds;
3. paired incidence `m16 - m2 >= 0.20`; and
4. the exact one-sided McNemar/binomial test over discordant pairs gives
   `p <= 0.05` in the predicted m16 direction.

The m16 positive-control threshold and paired contrast are both mandatory.
Failure of any gate stops this resource-abundance origin branch; do not alter the
horizon, endpoint, pool multipliers, or seeds, and do not extend selected runs.

## Secondary outcomes

Report origin epoch, callback entropy, maximum functional score, witness
abundance/composition, block timing and totals, final symbol composition,
runtime, and storage. Analyze block differences as possible mechanics, not as
independent evidence of replication. Secondary outcomes cannot rescue a failed
primary gate.

## Claims and follow-up

A pass supports only that a larger initially available conserved symbol reservoir
increases strict functional-origin incidence in this BFF artificial chemistry.
It does not establish adaptation, organization, ecology, self-maintenance, or
organism identity.

On pass, use independently generated m16 origin checkpoints for a separately
preregistered maintenance/hysteresis test, provided at least eight independent
checkpoints can be acquired under a seed-count extension frozen without examining
treatment outcomes. On failure, retain AC-P001 as a positive-control viability
result and stop this comparative branch.

## Execution

Run at most seven independent processes concurrently with
`NUMBA_NUM_THREADS=1`. Publish all raw runs centrally after deterministic
analysis.
