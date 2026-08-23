# Phase 1 batch-6 report — origin under exclusion

Generated 2026-08-19T19:50:28.984934+00:00. Preregistration: `reports/phase1_batch6_preregistration.md`.

Controls: no-conservation emergence 3/5; natural checkpoint excluded-six share 0.2027; random-soup baseline 0.0234.
Matched m16 emergent final six-share: 0.1490, 0.2014 (natural class grows the six symbols far above the baseline).
- **H1:** emergence 0/5, held 0/5; final excluded share 0.0236 -> median 0.0207; blocked-on-excluded median 0.835.
  - seed 0: emergent=False, Hmax 0.877, final H 0.290, excluded share 0.0236 -> 0.0207 (growth x0.88), blocked-on-excluded 0.815.
  - seed 1: emergent=False, Hmax 0.782, final H 0.291, excluded share 0.0235 -> 0.0207 (growth x0.88), blocked-on-excluded 0.835.
  - seed 2: emergent=False, Hmax 0.633, final H 0.300, excluded share 0.0233 -> 0.0207 (growth x0.89), blocked-on-excluded 0.820.
  - seed 3: emergent=False, Hmax 0.938, final H 0.293, excluded share 0.0234 -> 0.0207 (growth x0.88), blocked-on-excluded 0.845.
  - seed 4: emergent=False, Hmax 0.766, final H 0.253, excluded share 0.0233 -> 0.0231 (growth x0.99), blocked-on-excluded 0.935.
- **H2:** emergence 0/3, held 0/3; final excluded share 0.0039 -> median 0.0038; blocked-on-excluded median 0.066.
  - seed 0: emergent=False, Hmax 0.888, final H 0.358, excluded share 0.0039 -> 0.0039 (growth x0.99), blocked-on-excluded 0.356.
  - seed 1: emergent=False, Hmax 0.800, final H 0.380, excluded share 0.0039 -> 0.0038 (growth x0.99), blocked-on-excluded 0.066.
  - seed 2: emergent=False, Hmax 0.884, final H 0.291, excluded share 0.0039 -> 0.0037 (growth x0.95), blocked-on-excluded 0.035.

**H1a (suppression):** H1 0/5 vs control 3/5; one-sided Fisher p = 0.083 (two-sided 0.167). SUPPORTED.
**H1b:** no H1 emergent runs — class change untestable.
**H1c (mechanism):** blocked-write concentration on excluded symbols below threshold in some runs.

**H2a:** H2 0/3 vs control 3/5 (Fisher two-sided p = 0.196, one-sided control>exclusion p = 0.179; descriptive at n=3).

Conservation residuals nonzero in 0 runs (expected 0).
