# Phase 1 batch-4 report — mismatched-pool economies

Generated 2026-08-19T16:36:54.322423+00:00. Preregistration: `reports/phase1_batch4_preregistration.md`.

## F1/F3 — mismatched-pool continuation (headline)
- **U0.5:** viability every callback = True (min entropy 5.962), JSD(soup,pool) 0.0908 -> 0.1440 (ratio 1.586), blocked fraction 1.908e-06, longest sub-1.0 run 0 epochs.
- **U2:** viability every callback = True (min entropy 5.618), JSD(soup,pool) 0.0903 -> 0.1327 (ratio 1.469), blocked fraction 1.244e-05, longest sub-1.0 run 0 epochs.
- **U16:** viability every callback = True (min entropy 5.634), JSD(soup,pool) 0.0902 -> 0.1348 (ratio 1.495), blocked fraction 0.000e+00, longest sub-1.0 run 0 epochs.
- Control M0.5: JSD(soup,pool) 0.0001 -> 0.1070, viable = True, blocked 5.839e-06.
- Control M2: JSD(soup,pool) 0.0000 -> 0.0458, viable = True, blocked 2.560e-07.
- Control M16: JSD(soup,pool) 0.0000 -> 0.0782, viable = True, blocked 0.000e+00.

**F1-B: not met** (adapted+viable arms: []; control discrimination = False).
**F1-D: not observed** (no uniform arm sustains entropy < 1.0 for 2,000 epochs).

## F2 — mismatched-pool emergence at 32,768 tapes (paired seeds 0-2)
- U16: emergence 2/3, held 2/3, max entropy 6.389, final JSD(soup,uniform) median 0.1166.
- U2: emergence 1/3, held 0/3, max entropy 1.117, final JSD(soup,uniform) median 0.0204.
- M2: emergence 0/3, held 0/3, max entropy 0.948, final JSD(soup,uniform) median 0.0187.
- M16: emergence 2/5, held 2/5, max entropy 6.356, final JSD(soup,uniform) median 0.0881.

**F2a:** paired emergence U16 2/3 vs M16 1/3 (seeds [0, 1, 2]); Fisher exact two-sided p = 1.000. Directional note: uniform pool raises emergence at this scale.

**F2b:** among 0 emergent m16 seed pairs, uniform pool produced more-uniform content in 0/0.
- seed 0: overall blocked fraction U16 2.822e-06 vs M16 1.123e-06 (first block epoch U16 5811, M16 5829).
- seed 1: overall blocked fraction U16 1.540e-05 vs M16 4.676e-09 (first block epoch U16 5183, M16 5405).
- seed 2: overall blocked fraction U16 4.336e-06 vs M16 1.514e-06 (first block epoch U16 6807, M16 6030).

**F2c:** uniform pool blocked fraction exceeds matched pair in 3/3 m16 seed pairs.

Conservation residuals nonzero in 0 runs (expected 0).
