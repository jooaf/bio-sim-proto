# Phase 1 batch 2 preregistration — generated from batch-1 exploratory findings

Date: 2026-08-16. Batch 1 results in `reports/phase1_newexperiments_findings.md`.

## D1 — Population scale and takeover persistence (new runs)

**Background:** at 4,096 tapes, 5/20 runs crossed the entropy threshold but
only 1/20 (m16 s0) held it to the end (batch-1 exploratory finding 1).

**Design:** 16,384 tapes × 50,000 epochs, mutation 1/4096, shuffled-disjoint.
Arms: control (`paper_probe`) seeds 0–4; conserved m16 (`phase1_probe`) seeds
0–4. (m16 chosen because it shadows control until first block — it isolates the
scale question from blocking.)

**Hypotheses:**
- **D1a (supported if):** control emergence (sustained ≥ 3 callbacks ≥ 1.0
  bits/byte) occurs in ≥ 2/5 seeds at 16,384 tapes within 50,000 epochs.
- **D1b:** among emergent control runs, the fraction that *hold* to the end
  (final entropy > 1.0) is greater than the batch-1 4,096-tape rate (1/5 of
  crossers). One-sided comparison of two binomials; reported with exact p.
- **D1c (shadowing at scale):** for m16 runs, the epoch of the first
  blocked write is later at 16,384 tapes than the median at 4,096 tapes
  (batch-1 A runs), because blocking probability per epoch scales down with
  pool size. Mann-Whitney U, one-sided.

## D2 — Shadowing onset analysis (analysis-only, batch-1 A data)

**Hypothesis:** time-to-first-blocked-write (in epochs) increases monotonically
with pool multiplier across m0.5/m2/m16 at 4,096 tapes. Spearman over 15 runs;
expected ρ = +1 direction. Also report per-arm median and range. This
calibrates "when conservation begins to matter" as a function of scarcity.

## D3 — Role-persistence decay and mechanism screen (analysis-only, batch-1 C data)

**Background:** consecutive-window flow correlation ≈ 0.19 above null (C1).

**Hypotheses:**
- **D3a (persistence decay):** lag-k window flow correlation decreases
  monotonically in k (k = 1..4). Supported if Spearman(k, mean lag-k corr)
  < 0 with p < 0.05 across the 9 runs. Monotone decay indicates drifting role
  structure; a plateau would indicate fixed roles (stronger organization).
- **D3b (self-flow share):** the diagonal (self-return-and-reacquire) share of
  within-window transfers is stable across windows (CV < 0.2), i.e., the
  recycled fraction is a stationary property of the soup rather than an
  emerging structure. Descriptive, no significance test.

## Decision rules

- If D1a fails (< 2/5), the 16,384-tape control is still marginal; next batch
  jumps to 32,768 rather than adding seeds at 16,384.
- D2/D3 are analysis-only and cannot fail to run; all outcomes reported.

## Runs

- `experiments/run_phase1_batch2.nu` (D1; D2/D3 execute in the analyzer
  `experiments/analyze_phase1_batch2.py`).
