# Phase 1 batch-7 report — specificity control

Generated 2026-08-19T21:23:36.536879+00:00. Preregistration: `reports/phase1_batch7_preregistration.md`.

- **I1:** emergence 3/5, held 2/5; median entropy 0.315; blocked-write totals 1.573e+08–8.763e+08 (batch-6 H1 reference ~2.5e+09–3.4e+09).
  - seed 0: emergent=False, held=False, Hmax 0.736, final H 0.347, blocked 1.573e+08.
  - seed 1: emergent=True, held=True, Hmax 2.273, final H 2.068, blocked 8.763e+08.
  - seed 2: emergent=False, held=False, Hmax 0.772, final H 0.276, blocked 1.717e+08.
  - seed 3: emergent=True, held=False, Hmax 1.362, final H 0.868, blocked 6.290e+08.
  - seed 4: emergent=True, held=True, Hmax 2.816, final H 2.193, blocked 5.438e+08.
- **I2:** emergence 1/3, held 0/3; median entropy 0.310; blocked-write totals 1.514e+08–3.110e+09 (batch-6 H1 reference ~2.5e+09–3.4e+09).
  - seed 0: emergent=False, held=False, Hmax 0.861, final H 0.286, blocked 1.552e+08.
  - seed 1: emergent=False, held=False, Hmax 0.921, final H 0.298, blocked 1.514e+08.
  - seed 2: emergent=True, held=False, Hmax 1.053, final H 0.988, blocked 3.110e+09.

**I1 (specificity):** I1 3/5 vs control 3/5 (Fisher two-sided p = 1.000). SUPPORTED (>= 2/5): suppression is class-specific.

**I2:** I2 1/3 vs control 3/5; H2 (symbol-0 exclusion) was 0/3. Consistent with null-byte specificity.

### I3 — mechanism in suppressed runs (analysis-only)
- H1 seed 0: structural-six share 0.0236 -> 0.0207.
- H1 seed 1: structural-six share 0.0235 -> 0.0207.
- H1 seed 2: structural-six share 0.0233 -> 0.0207.
- H1 seed 3: structural-six share 0.0234 -> 0.0207.
- H1 seed 4: structural-six share 0.0233 -> 0.0231.
- H2 seed 0: structural-six share 0.0236 -> 0.0444.
- H2 seed 1: structural-six share 0.0235 -> 0.0507.
- H2 seed 2: structural-six share 0.0233 -> 0.0505.
- matched m16 seed 0 (emergent=True): structural-six share 0.0236 -> 0.1490.
- matched m16 seed 1 (emergent=False): structural-six share 0.0235 -> 0.1095.
- matched m16 seed 2 (emergent=False): structural-six share 0.0233 -> 0.1092.
- matched m16 seed 3 (emergent=True): structural-six share 0.0234 -> 0.2014.
- matched m16 seed 4 (emergent=False): structural-six share 0.0233 -> 0.1109.

Conservation residuals nonzero in 0 runs (expected 0).
