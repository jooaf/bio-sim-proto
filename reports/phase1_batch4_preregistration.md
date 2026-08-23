# Phase 1 batch 4 preregistration — mismatched-pool economies: conservation as a selective force

Date: 2026-08-19. Generated from the batch-1/2/3 campaign conclusion
(`reports/phase1_newexperiments_findings.md`): population scale governs
emergence onset and takeover persistence; conservation governs the resource
economy, binds during emergence from random soups, and is **neutrally closed**
once a replicator ecology is established.

## Motivating observation (computed before registration, no outcome peeking)

The "neutrally closed" result was obtained **only with histogram-matched
pools** (pool = content histogram × multiplier). Under a matched pool, an
ecology's per-symbol demand equals its own content histogram, so it never
blocks. This is a special case, not a law. The natural seed-0 epoch-2,433
replicator checkpoint (`runs/paper_probe_seed0_transition.npy`) is far from
uniform:

- JSD(checkpoint content, uniform) = **0.0901 bits** (random soup: 0.00018);
- symbol 0 (null byte) holds 4.6% of all matter (12× uniform share);
- BFF opcodes 60, 91, 44, 125, 93 are the next-most-enriched symbols;
- overall instruction fraction 0.1595.

A **uniform pool** of the same total mass therefore creates persistent
scarcity on precisely the symbols replicators need. The open question — and
Phase 1's remaining gap ("persistent metabolic organization remains
unobserved") — is whether the conserved matter economy can act as a
**selective force on program content**, not merely as a neutral constraint.

## F1 — mismatched-pool continuation of an established ecology (headline)

**Design:** continue the natural seed-0 epoch-2,433 checkpoint (131,072
tapes) for 8,000 epochs (epoch offset 2,433) under `--pool-mode uniform` at
pool multipliers **0.5, 2, 16** (arms U0.5, U2, U16; one run each; only one
natural checkpoint exists). Controls are the existing matched-pool
continuations (m0.5, m2, m16 — same checkpoint, same protocol, matched pool).

**Mechanism:** under a uniform pool the quasispecies cannot be matter-closed:
its demand for enriched symbols (0, 60, 91, 44, …) exceeds their pool share.
Every write of an enriched symbol can be blocked once the pool symbol is
locally exhausted. Outcomes:

- **Adaptation (F1-B, the breakthrough criterion):** the ecology remains
  viable *and* its content histogram moves toward the pool composition.
  Preregistered thresholds, all three required, in **≥ 2 of 3** uniform arms:
  1. sustained viability: high-order entropy > 1.0 at **every** callback
     through 8,000 epochs;
  2. content adaptation: JSD(soup content, pool) at the final callback is
     ≤ 50% of its value at the first callback;
  3. control discrimination: the matched-pool continuations change JSD
     (soup, pool) by < 10% over the same window (control JSD trajectories
     computed analytically from existing runs' symbols.csv in analysis arm F3).
  If met, this is the first demonstration that the conserved economy exerts
  sustained directional selection on replicator content — matter economy
  directing evolution — and Phase 1's selection gap closes.
- **Disruption (F1-D):** any uniform arm sustains high-order entropy < 1.0
  for ≥ 2,000 consecutive epochs. Matter-economy mismatch can be lethal to
  an established ecology; "neutral closure" is then a matched-pool artifact
  in the opposite direction.
- **Partial/mixed:** report honestly per arm and follow up in batch 5.

**Additional registered metrics:** blocked-write fraction (overall and by
symbol), zero-pool-symbol count, pool entropy, dominant-tape fraction,
distinct tapes, active instruction fraction, JSD(soup, uniform), and
JSD(soup, pool) trajectory (new probe metric; dynamics unaffected — metric
computed only at callbacks from already-computed counts).

## F2 — mismatched-pool emergence from random soup (paired seeds)

**Design:** 32,768 tapes × 100,000 epochs, mutation 1/4096, shuffled
disjoint pairing, callback interval 100. Uniform pool, multipliers 16 and 2,
**seeds 0–2** (arms U16 s0–2, U2 s0–2). Because the seed fixes the initial
soup and the shuffle/mutation streams, each uniform run is exactly paired
with the existing batch-3 matched m16 runs (seeds 0–4; use seeds 0–2 pairs)
and with new matched m2 runs (m2 s0–2, also run here) — identical starting
state and streams, differing only in pool composition. This is the same
shadowing-style paired contrast that isolated conservation entry in batch 1.

**Hypotheses:**
- **F2a (emergence rate):** uniform vs matched m16 emergence (entropy ≥ 1.0
  crossing) counts, Fisher exact two-sided, reported regardless of
  significance (3 paired seeds; underpowered by design — descriptive).
- **F2b (content selection at origin):** among runs that cross the entropy
  threshold, final JSD(soup, uniform) is lower under uniform pool than under
  the matched pool in ≥ 2/3 m16 seed pairs (sign test logic; also report m2).
- **F2c (scarcity during emergence):** uniform-pool blocked fraction exceeds
  its matched-pool pair's from the first callback in ≥ 2/3 seed pairs (m16
  and m2). Mismatch binds early, unlike matched pools whose first block is
  delayed (batch-1 shadowing result).

## F3 — analysis-only: matched-continuation control JSD trajectories

Compute JSD(soup, pool) and JSD(soup, uniform) trajectories for the existing
matched continuations (m0.5/m2/m16, `experiments/phase1_runs/continuation/`)
from symbols.csv + reconstructed conserved totals; verify the F1 control
discrimination threshold. No new runs.

## Decision rules (batch 5)

- If **F1-B** met → breakthrough declared; batch 5 deepens: generate
  additional natural checkpoints (paper_probe `--checkpoint` for emerging
  seeds at 32,768), replicate uniform-continuation adaptation across seeds,
  and run windowed flow analysis (role persistence) on adapting ecologies.
- If **F1-D** → batch 5 maps the disruption boundary (mismatch × multiplier
  grid, rescue dynamics at intermediate mismatch).
- If uniform arms neither adapt nor collapse (JSD flat, entropy sustained)
  → the quasispecies is robust to matter-economy mismatch; batch 5 tests
  stronger mismatches (e.g., pool matched to a *different* content class).
- Runs are resumed by manifest gating; no early stopping on observation.
- No parameters changed and no runs discarded after observing outcomes.

## Runs

`experiments/run_phase1_batch4.nu` (F1 continuations, F2 emergence + matched
m2 pairs). Analysis: `experiments/analyze_phase1_batch4.py`. New probe
metrics covered by tests in `tests/test_batch4_extensions.py`.
