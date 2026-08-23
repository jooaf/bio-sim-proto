# Phase 1 batch 3 preregistration — population scale for reliable, persistent takeover

Date: 2026-08-17. Generated from batch-2 D1 results (`reports/phase1_batch2_report.md`)
under the pre-committed decision rule: "If D1a fails (< 2/5), jump to 32,768
rather than adding seeds at 16,384."

## E1 — 32,768-tape emergence and persistence

**Background:** control emergence remains 1/5 at 16,384 (50K epochs) and 1/5 at
4,096 (100K epochs); most crossings decay. Under m16, takeover was *held* in
2/5 seeds at 16,384 (s3) and 1/5 at 4,096 (s0), while emergent controls decayed
(0/1 and 0/1 held). Sample sizes forbid inference; this batch scales up.

**Design:** 32,768 tapes × 100,000 epochs, mutation 1/4096, shuffled-disjoint.
Arms: control (`paper_probe`) seeds 0–4; conserved m16 (`phase1_probe`) seeds
0–4. Callback interval 100.

**Hypotheses:**
- **E1a (scale):** control emergence ≥ 2/5 at 32,768 within 100,000 epochs.
  If not, the emergence process is not population-limited in this range and
  the bottleneck is elsewhere (e.g., takeover decay rate vs. seed rate).
- **E1b (persistence, exploratory-to-confirmatory):** among runs that cross,
  m16 held-to-end rate exceeds control held-to-end rate. Two-sided Fisher
  exact on pooled crossings; reported regardless of significance.
- **E1c (shadowing at scale):** m16 first-block epoch median at 32,768 vs
  16,384 batch-2 median (5,296): MW-U one-sided "greater". Batch-2 suggested
  scale-invariance (p = 0.42); this is the confirmation attempt with the
  prediction now reversed to invariance (two-sided test reported).

## E2 — quasispecies stability under conservation (analysis-only, B data)

**Background:** the m2 continuation of the natural checkpoint sustained the
replicator regime for 8,000 epochs with blocked fraction 2.6e-7 (vs 0.76%
for the m2 random-soup baseline over its first 1,000 epochs).

**Hypotheses (descriptive until m16 completes; single seed each):**
- **E2a:** m0p5 continuation also sustains entropy > 1.0 throughout (blocked
  fraction < 0.01). If scarcity were binding on established ecologies, m0.5
  would block heavily.
- **E2b:** m16 continuation sustains entropy > 1.0 throughout with blocked
  fraction < 1e-4.
- **E2c:** order-of-magnitude summary: continuation blocked fractions are ≥ 2
  orders of magnitude below the random-soup baseline at matched multiplier.

## Decision rules

- If E1a fails, stop adding population; instead investigate takeover decay
  (content-flow analysis of emergent-then-decayed checkpoints) in a future
  batch.
- Runs are resumed by manifest gating; no early stopping on observation.

## Runs

`experiments/run_phase1_batch3.nu` (E1; E2 executes in
`experiments/analyze_phase1_batch2.py` extension or the notebook).
