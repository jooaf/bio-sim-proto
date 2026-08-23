# Phase 1 batch 6 preregistration — origin under exclusion: does the matter economy set the replicator class?

Date: 2026-08-19. Generated under the batch-5 decision rule: exclusion
continuations were viable with no restructuring (G1/G2 not met) and tiny
uniform pools did not bind (G3 supported) — quasispecies robustness is the
batch-5 headline; the next test is exclusion applied **during emergence**.

## Batch-5 outcome recap (context)

- G1 (top-6 exclusion: symbols 0, 60, 91, 44, 125, 93 = null byte + five
  core opcodes, zero pool supply): viable for all 8,000 epochs (min entropy
  5.98); excluded-symbol share 0.2027 → 0.2005 (−1.1%); blocked writes 98.6%
  concentrated on excluded symbols (mechanism as designed) but absorbed as
  friction.
- G2 (symbol-0-only exclusion): viable; symbol-0 share 0.0458 → 0.0376
  (−17.8%, a slow ratchet — ~40K epochs to halve at this rate).
- G3 (uniform m0.05 / m0.1): viable, blocked fractions 2.7e-4 / 8.8e-5.
- G4: uniform m16 emergence 2/5 = matched 2/5 (Fisher p = 1.0) — batch-4's
  exploratory emergence hint did not replicate.

Conclusion so far: established ecologies are matter-economically homeostatic.
The untested lever is the **origin transition**: natural replicators grow the
excluded symbols from ~0.39% (random soup) to 4–16% of content
(checkpoint evidence). Under exclusion, that growth is capped at initial
random-soup levels. Can loop-based replicators emerge at all under a capped
supply of their structural symbols — and if they do, is their content class
different?

## H1 — emergence under natural-symbol exclusion (headline)

**Design:** 32,768 tapes × 100,000 epochs, mutation 1/4096, shuffled
disjoint pairing, callback interval 100, multiplier 2, pool mode
`excluded_list` with symbols **[0, 60, 91, 44, 125, 93]** (the natural
replicator's six most-enriched symbols: null loop-control byte + `<`, `[`,
`,`, `}`, `]`), mass redistributed over the other 250 symbols. Seeds 0–4.
Controls: existing batch-3 no-conservation control (3/5 emergence), matched
m16 (2/5), uniform m16 (2/5).

**Mechanism:** random soups start with ~0.39% per symbol (≈8,192 copies
each of the excluded six). Natural emergence grows these to 4–16%; under
exclusion the content of each excluded symbol is capped at its initial count
(returns create only a transient buffer). Loop-based replication must either
work with 9–40× lower densities of its structural symbols, or be replaced by
a different replicator class.

**Hypotheses:**
- **H1a (suppression):** excluded-list emergence < control emergence
  (one-sided Fisher exact on 0–4 seeds vs control 3/5; report two-sided).
  If 0/5 emerge, p = 0.079 (directionally decisive at this sample size).
- **H1b (class change — breakthrough if emergence occurs):** among emergent
  H1 runs, the combined content share of the six excluded symbols at the
  final callback is ≤ its random-soup baseline (≈ 6 × 0.39% = 2.34%, allow
  ≤ 3.0%), i.e. replicators emerged **without** growing the natural symbol
  set. Natural emergent runs (batch-3 control/m16 crossings) grow it well
  above 10% (verify from existing data; report measured values).
  Demonstrating a distinct emergent replicator class under matter-economy
  constraint would be the Phase 1 breakthrough: the conserved economy
  determines the replicator class at origin.
- **H1c (mechanism, registered):** blocked writes concentrate on excluded
  symbols (≥ 90% of blocked execution writes) in every H1 run.

## H2 — null-byte-only exclusion at origin (isolates loop-control dependence)

Same design with excluded list **[0]** (seeds 0–2), multiplier 2. The
`[`/`]` opcodes jump when the head byte is 0; with symbol-0 supply capped at
the random-soup level, loop-control data cannot be grown. Hypotheses:
- **H2a:** emergence count vs control (one-sided Fisher, seeds 0–2 vs
  control seeds 0–2 3/5... report exact comparison vs all five control
  seeds; descriptive at n=3).
- **H2b:** among emergent runs, symbol-0 final content share ≤ 0.6%
  (vs natural emergent ~4.6%).

## Decision rules (batch 7)

- If **H1b or H2b** → breakthrough: conserved-matter class selection at
  origin. Batch 7 deepens with continuation runs from the new-class
  checkpoints (probe now saves final soups), cross-seed replication, and
  functional self-replication scoring of the new class.
- If **H1a/H2a (suppression) with no emergence** → the matter economy acts
  as an origin filter: batch 7 sweeps which symbol subsets are necessary
  (K=1..6 singly) to map the boundary between filter and friction.
- If emergence occurs with the natural class anyway (excluded symbols stay
  capped yet replication works at low densities) → matter economy is
  permissive at origin too; Phase 1's conservation story closes as
  "friction, never selection" — a clean, publishable negative result.
- Runs are manifest-gated; no early stopping; no post-hoc parameter changes.

## Runs

`experiments/run_phase1_batch6.nu` (8 runs: H1 seeds 0–4, H2 seeds 0–2, all
with final-soup checkpoints saved for batch-7 continuation). New probe
capabilities: `--pool-mode excluded_list --pool-exclude-symbols "0,60,..."`,
`--save-final-soup PATH`; tests in `tests/test_batch6_extensions.py`.
Analysis: `experiments/analyze_phase1_batch6.py`.
