# Phase 1 batch-5 report — exclusion pools

Generated 2026-08-19T18:54:12.390769+00:00. Preregistration: `reports/phase1_batch5_preregistration.md`.

## Continuations (G1/G2/G3)
- **G1-excl6:** viable=True (min entropy 5.976), longest sub-1.0 run 0 epochs, excluded-symbol share 0.2027 -> 0.2005 (ratio 0.989), JSD(soup,pool) 0.1095 -> 0.1496 (ratio 1.366), blocked writes on excluded symbols 0.986, share non-increasing at 48.8% of callbacks.
  - **G1-excl6a/G1-excl6b: not met.**
  - G1-excl6c (ratchet + blocked concentration): not met.
- **G2-excl1:** viable=True (min entropy 5.983), longest sub-1.0 run 0 epochs, excluded-symbol share 0.0458 -> 0.0376 (ratio 0.822), JSD(soup,pool) 0.0233 -> 0.0533 (ratio 2.293), blocked writes on excluded symbols 0.919, share non-increasing at 50.0% of callbacks.
  - **G2-excl1a/G2-excl1b: not met.**
  - G2-excl1c (ratchet + blocked concentration): not met.
- **G3-U0.05:** viable=True (min entropy 5.131), blocked fraction 2.680e-04 -> G3 robustness SUPPORTED.
- **G3-U0.1:** viable=True (min entropy 5.517), blocked fraction 8.762e-05 -> G3 robustness SUPPORTED.

**G4:** uniform m16 emergence 2/5 vs matched m16 2/5; Fisher exact two-sided p = 1.000 (one-sided p = 0.738). Held-to-end: U16 2/5, M16 2/5. Not supported at the 4/5 criterion.

Conservation residuals nonzero in 0 runs (expected 0).
