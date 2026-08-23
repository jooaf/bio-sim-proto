# Phase 1 campaign 2 — conserved-economy selection: filter at origin, friction in ecology

Consolidated report for batches 4–7 (2026-08-19). Preregistrations:
`phase1_batch4_preregistration.md` … `phase1_batch7_preregistration.md`.
Individual reports: `phase1_batch4_report.md` … `phase1_batch7_report.md`.

## Question

Phase 1 closed with an open question: the conserved symbol pool binds during
emergence but appears "neutrally closed" in established ecologies — can the
matter economy ever act as a *selective force* on program content?

## Campaign design and results

| Batch | Manipulation | Result |
|---|---|---|
| 4 | Uniform (mismatched) pools on established ecology + at origin | Robust: viable, no adaptation, no collapse |
| 5 | Zero supply of the ecology's six structural symbols (exclusion) | Robust: absorbed as friction (98.6% of blocked writes on excluded symbols) |
| 6 | Structural-symbol exclusion *during emergence* | Natural-six arm: **0/5 vs 3/5 control** (one-sided Fisher p = 0.083); null-only arm: 0/3 descriptive |
| 7 | Non-structural-symbol exclusion during emergence (specificity control) | **3/5 observed emergence**, the same count as control (p = 1.0), supporting specificity without proving equivalence |

34 runs total; every conserved run at zero symbol-conservation residual;
every manifest success; no parameters changed after observation; one
exploratory hint (batch 4) preregistered and honestly refuted (batch 5).

## Mechanism (batch-6/7 symbol-level analysis)

- Emergence in this substrate requires growing the structural six
  (`[ ] < , }` + null byte) from the 2.3% random-soup baseline to ≥ 11%
  (even *failed* natural runs reach ~11%; successful ones 15–20%).
- Under natural-six exclusion, structural content is capped at baseline and
  ratchets slightly down (0.023 → 0.021); the transition never fires.
- Under null-byte-only exclusion, the five opcodes still double (→ ~5%) but
  cannot compensate: loop control needs the falsy byte. No emergence.
- Under non-structural exclusion (200–205), structural growth and emergence
  proceed exactly as in the no-conservation control.

## Conclusion

**The conserved matter economy is a candidate class-specific origin filter
and an ecology-level homeostat.** Zero supply of the known class's structural
symbols was associated with suppression at origin, while the same constraint
was absorbed as friction by one established ecology and non-structural
exclusion still allowed emergence. The result supports an origin-specific
resource filter but does not prove equivalence or universality.

## Limitations

- The confirmatory natural-six contrast is 0/5 vs 3/5 (p = 0.083 one-sided);
  the additional null-only 0/3 arm is mechanistic support, not the same cell.
- The specificity control's 3/5 vs 3/5 (p = 1.0) does not prove equivalence.
- Non-structural control runs had 1.6e8–8.8e8 blocked writes versus roughly
  2.5e9–3.4e9 in the natural-six arm, so friction was not perfectly matched.
- Single natural checkpoint for all continuation experiments (seed 0,
  epoch 2,433).
- 100K-epoch horizon at 32,768 tapes; slower-acting origin mechanisms
  cannot be excluded.
- The "established ecology" claims are bounded to 8,000-epoch windows.

## Follow-ups

- K-sweep (which single structural symbols are necessary/sufficient for
  suppression) to map the filter's boundary.
- Continuation of batch-6/7 final soups (checkpoints saved) to test whether
  prolonged exclusion eventually admits an alternative replicator class.
- Functional self-replication scoring of I1's emergent class under
  non-structural exclusion vs natural replicators.
