# Phase 1 batch 5 preregistration — exclusion pools: lethal selection or restructuring rescue

Date: 2026-08-19. Generated under the batch-4 decision rule: uniform arms
neither adapted (F1-B) nor collapsed (F1-D) — the quasispecies is robust to
weak matter-economy mismatch; test stronger mismatches.

## Batch-4 outcome recap (context for design)

- All three uniform-pool continuations (U0.5/U2/U16) of the natural
  epoch-2,433 checkpoint stayed viable for 8,000 epochs (min entropy 5.62).
- JSD(soup,pool) rose 0.090 → 0.13–0.14 in uniform arms, a drift comparable
  to matched-pool controls' own endogenous drift (0 → 0.046–0.107). No
  preregistered adaptation signal.
- Exploratory symbol-level detail (motivating this batch): under U2,
  symbol-0 content fell 36% (385,981 → 244,938) while viability held, with
  blocked writes concentrated on enriched instruction symbols (125: 1.34M,
  44: 0.78M). Under U16 there was zero blocking — per-symbol pool stock
  exceeded net flux. Weak mismatch produces measurable but non-lethal
  directional content pressure; the pool buffers it.
- F2 exploratory hint: uniform pools raised emergence onset (U16 2/3 vs
  M16 1/3 paired seeds; U2 1/3 vs M2 0/3; all Fisher p ≥ 0.5).

## G1 — top-6 exclusion pool continuation (headline)

**Design:** continue the natural seed-0 epoch-2,433 checkpoint (131,072
tapes, 8,000 epochs, offset 2,433, mutation 1/4096). Pool mode
`excluded_top`, K=6: the six most-enriched symbols of the checkpoint
histogram (0, 60, 91, 44, 125, 93 — jointly 25.9% of tape matter; five are
BFF opcodes, one is the null byte controlling loop jumps) receive **zero
initial pool stock**; the multiplier-2 mass is redistributed proportionally
over the remaining 250 symbols.

**Mechanism:** writes *to* an excluded symbol require pool stock that starts
at zero, so excluded-symbol content is capped at its initial level and can
decline (returns create a small transient buffer, permitting slow exchange —
a near-ratchet). Replicators depend on these symbols structurally (loop
control via byte 0; copy/head opcodes), so this is the strongest matter
economy stress constructible without changing BFF semantics.

**Hypotheses (mutually exclusive headline outcomes):**
- **G1a (disruption):** high-order entropy < 1.0 sustained ≥ 2,000
  consecutive epochs. Would show conservation can be *lethal* to an
  established ecology — matter economy as an extinction force.
- **G1b (restructuring rescue — breakthrough):** viability at every callback
  (entropy > 1.0) **and** excluded-symbol content share falls by ≥ 50%
  (from 25.9% to < 13.0%) **and** JSD(soup, pool) at the final callback is
  ≤ 50% of its first-callback value. Would demonstrate the conserved economy
  reorganizing replicator content at scale while remaining functional —
  sustained directional selection with an adaptive response.
- **G1c (mechanism, registered regardless):** blocked writes concentrate on
  excluded symbols (≥ 80% of all blocked execution writes), and
  excluded-symbol content share is non-increasing over ≥ 95% of callbacks
  (ratchet behavior).

## G2 — symbol-0-only exclusion (isolates null-byte dependence)

Same design with K=1 (symbol 0 only; 4.6% of content). Same hypotheses
G2a/G2b/G2c with share threshold applied to symbol 0 alone (≥ 50% decline
from 4.58%). Tests whether loop-control null bytes are the load-bearing
dependence or whether opcode scarcity alone (G1) drives any outcome.

## G3 — absolute-scarcity stress (uniform, tiny multipliers)

Uniform pool continuations at multipliers **0.05 and 0.1** (pool total 5–10%
of tape matter; per-symbol stock 0.0002–0.0004 of tape matter). Hypothesis
**G3 (robustness):** both arms remain viable at every callback with overall
blocked fraction < 1e-3. If violated, absolute pool size — not composition —
is the binding constraint, revising the batch-4 robustness conclusion.

## G4 — completing the emergence pairing (exploratory-to-confirmatory)

Run uniform m16 emergence at 32,768 tapes × 100,000 epochs for **seeds 3–4**,
completing five paired seeds against existing batch-3 matched m16 runs
(seeds 0–4). Hypothesis **G4:** uniform-pool emergence count exceeds matched
(≥ 4/5 vs ≤ 2/5 would give one-sided Fisher p ≈ 0.11; any result reported).
Also report held-to-end among crossings. If uniform emergence ≥ 4/5, mild
matter-economy stress promoting origin-of-replication becomes a lead
hypothesis for batch 6 (mechanism: scarcity as variation/selection source
during the random-soup phase).

## Decision rules (batch 6)

- If **G1b or G2b** → breakthrough declared: conserved-matter economy
  demonstrably directs content evolution. Batch 6 replicates across
  multiplier and additional checkpoints, and runs windowed flow analysis on
  the restructured ecology.
- If **G1a or G2a** → batch 6 maps the lethality boundary (K sweep, rescue
  by partial restocking) and asks whether *emergence* can occur under
  exclusion (origin under lethal scarcity).
- If neither (viable but no restructuring) → quasispecies robustness is the
  headline; batch 6 tests whether exclusion applied *during emergence*
  changes the replicator class that emerges (content-class selection at
  origin).
- If **G4** supported → batch 6 adds seeds 5–9 for power and probes the
  mechanism (blocked-write timing relative to transition onset).
- Runs are manifest-gated and resumable; no early stopping; no parameter
  changes after observation; exploratory analyses labeled as such.

## Runs

`experiments/run_phase1_batch5.nu` (7 runs: G1, G2, G3×2 continuations;
G4×2 emergence). New probe capability: `--pool-mode excluded_top
--pool-exclude-top K` (mass-preserving redistribution), covered by tests in
`tests/test_batch5_extensions.py`. Analysis:
`experiments/analyze_phase1_batch5.py`.
