# AC-I001 nonspecific-friction calibration preregistration

**Frozen before execution:** 2026-09-12

## Scope

This is a mechanics-only calibration for AC-I001. It may select one
symbol-independent write-rejection probability using blocked-write load only.
Entropy, compression, exact-tape abundance, functional replication, or emergence
must not be inspected during selection. Calibration seeds are excluded from all
confirmation.

## Deterministic friction semantics

For every requested changing write (background mutation or BFF execution), first
increment a run-global attempt counter. If friction rejection is enabled, derive
a 30-bit draw from SplitMix64 using a domain-separated combination of run seed
and that counter. Reject when the draw is below
`round(rate * 2^30)`. Rejection is independent of old byte, requested byte,
tape identity, epoch, and the simulation RNG stream. A rejected write leaves tape
and pool unchanged and is counted separately from symbol-scarcity blocking.
No-op writes are not eligible. Rate zero must preserve the exact legacy tape and
pool trajectory.

## Runs

Use calibration seeds `202610000`–`202610004`, 32,768 tapes, 5,000 epochs,
mutation `1/4096`, multiplier 2, 8,192 maximum reads, callbacks every 100 epochs,
and paper-style shuffled-disjoint pairing.

For every seed run:

- natural-six zero-supply with excluded symbols `{0,44,60,91,93,125}` and zero
  nonspecific rejection;
- histogram-matched pools with friction rates
  `{0.01, 0.02, 0.03, 0.05, 0.08}`.

This is 30 runs. Record changing-write attempts, successful writes, scarcity
blocks, friction blocks, per-symbol requests/blocks, exact conservation, runtime,
and manifests.

## Selection rule

For each treatment and seed, sum execution plus mutation blocks over epochs
1–5,000. Calculate the natural-six median blocked count and each friction rate's
median friction-block count. Select the rate minimizing absolute log ratio:

`abs(log(median_friction / median_natural_scarcity))`.

Ties within floating equality select the lower rate. The selected rate is
mechanically acceptable only when the median count ratio is in `[0.8, 1.25]` and
all runs succeed with zero conservation residual. Per-seed differences and the
full grid remain reported.

If no rate is acceptable, AC-I001 confirmation stops pending a new design; do not
expand the grid after inspecting these runs. If one is acceptable, freeze it in
a separate confirmation preregistration using held-out seeds. Do not inspect or
report emergence outcomes from calibration artifacts.
