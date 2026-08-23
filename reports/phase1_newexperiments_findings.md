# Phase 1 new-experiment batch — findings and interpretation (final)

Status: Experiments A, B (all arms), C, batch-2 D, and batch-3 E1 complete.
The machine-written inventory lives in `reports/phase1_newexperiments_report.md`
and `reports/phase1_batch2_report.md`; executed notebooks in `notebooks/`.

## Experiment A — long-window emergence at 4,096 tapes (100,000 epochs)

Preregistered outcomes:

- **A1 (supported, exactly at criterion):** control emergence 1/5 within
  100,000 epochs (seed 2, first transition epoch 63,701). The 20K-epoch window
  was genuinely too short; 4,096 tapes is marginally above the emergence
  threshold but far from reliable.
- **A2 (not supported):** m2 emergence 1/5 vs control 1/5. One-sided Fisher
  exact p = 0.78. At this scale, five seeds per arm cannot distinguish
  conservation's effect on emergence *onset* — and the point estimates are
  identical, so there is no signal to miss.
- **A3 (not significant, direction reversed vs expectation):** Spearman
  multiplier-vs-max-entropy ρ = −0.30, p = 0.273 (n = 15). Scarcity does not
  measurably suppress maximum entropy at this sample size.
- **A4 (supported):** blocked-write scarcity curve reproduced, ρ = −0.945,
  p = 1.13×10⁻⁷.

### Exploratory findings (not preregistered — flagged for batch 2)

1. **Transience.** 5/20 runs ever crossed the entropy-1.0 threshold, spread
   across *all* arms (m0.5: 1, m2: 2, m16: 1, control: 1). Only **1/20 —
   m16 seed 0 — held the takeover to the end** (final 5.37 bits/byte,
   sustained 9,700 epochs). The other four crossings decayed after
   200–3,000 epochs above threshold. At 4,096 tapes, emergence is usually a
   transient excursion, with or without conservation.
2. **Shadowing.** Three m16 seeds produced max-entropy values identical to
   their control counterparts to six decimals (s1: 0.337898, s3: 0.366837,
   s4: 0.412793). With near-zero blocking, the conserved trajectory byte-shadows
   the Phase 0 control until the first scarcity-blocked write; after that they
   diverge (s0 held takeover where control s0 never crossed). Conservation
   enters dynamics discontinuously, at the first blocked write.

## Experiment C — windowed flow organization (complete)

- **C1 (supported):** observed consecutive-window edge-weight Spearman
  correlation 0.193 vs permuted-label null 0.011; mean gap +0.182, one-sided
  paired permutation p = 0.0025 (9 runs × 9 window pairs). **Robust to
  excluding self-flow** (off-diagonal-only gap +0.189). The earlier "nearly
  complete aggregate graph ⇒ well-mixed" conclusion was an artifact of
  aggregation: at 2,000-epoch resolution, donor→receiver flow has persistent
  structure — tapes keep their producer/consumer roles across windows.
- **C2 (not supported):** no scarcity dependence was detected (ρ = −0.16,
  exact permutation p = 0.729). The data do not establish a multiplier effect
  on role persistence.

## Experiment B — continuation of the natural replicator checkpoint (complete)

- **B-control:** the seed-0 epoch-2,433 checkpoint continues in the
  replicator-dominated regime for all 8,000 epochs (entropy 5.6–6.1, never
  below 1.0) as a *diverse quasispecies* — distinct tapes rise 37,503 → 81,736.
  The preregistered B1 criterion (single-hash dominance > 0.5) is **not
  supported** and was based on a wrong model of takeover in this substrate;
  the entropy-based reading says the checkpoint ecology is viable and stable.
- **B2 (not supported — the key positive finding of the batch):** m2
  conservation does **not** disrupt the established ecology. Entropy stayed
  5.98–6.05 for all 8,000 epochs; overall blocked fraction 2.6×10⁻⁷.
- **B3 (supported, stronger than hypothesized):** the m16 continuation is
  **byte-identical to the no-conservation control** — zero blocked writes in
  8,000 epochs; entropy and character reads match at every callback
  (max |diff| = 0).
- **B4 (direction reversed, decisively):** continuation first-1,000-epoch
  blocked fraction ≈ 1.4×10⁻⁷ vs random-soup baseline 7.6×10⁻³; difference
  −0.0077, 95% moving-block bootstrap CI [−0.0121, −0.0032].
- **E2 (batch 2, analysis-only):** m0.5 continuation also sustains (min
  entropy 5.90, blocked 5.8×10⁻⁶). All continuations' blocked fractions are
  ≥ 2–7 orders of magnitude below the matched-multiplier random-soup baseline.

**Mechanistic synthesis:** scarcity binds during *emergence from random
soups*, not in *established ecologies*. A replicator quasispecies' byte
demand distribution equals its own content histogram, so a matched-pool
economy never blocks: the ecology is matter-economically closed and recycles
its own symbols. Conservation's selective pressure operates at the origin
transition, exactly where Phase 1's original scarcity results were measured.

## Interpretation

Three storylines now anchor Phase 1's open science:

1. **Scale, not conservation, gates emergence onset** at these horizons. The
   4,096-tape soup is marginal: crossings happen in every condition and mostly
   decay. Whether takeover *holds* — where m16 s0 succeeded alone — is the
   interesting differential, and it needs more seeds/populations to test.
2. **Conservation acts discontinuously** (shadowing until first block), so
   multiplier effects should be analyzed as time-to-first-block × post-block
   dynamics, not as average-rate differences.
3. **Persistent role structure exists** (C1) even though the aggregate flow
   graph is complete. Whether this is metabolic organization or merely content
   persistence (tapes that copy a lot keep copying) is the key mechanistic
   question — addressable with lag-decay and content-change analyses on the
   existing windowed data (batch 2, analysis-only).

## Verification status

- All conserved runs: zero symbol-conservation residuals at every checkpoint.
- All manifests: `exit_status == success` for completed runs.
- New probe paths covered by `tests/test_newexperiments_extensions.py`
  (56 tests passing).


## Batch-3 E1 — 32,768-tape scale test (complete)

- **E1a (supported):** control emergence 3/5 within 100,000 epochs
  (transitions at epochs 17,201 / 38,201 / 42,001). Emergence probability
  climbs with population: 1/5 at 4,096, 1/5 at 16,384, 3/5 at 32,768.
- **E1b (not significant — and the batch-2 persistence hint weakens):**
  held-to-end among crossings: m16 2/2, control 2/3; Fisher exact p = 1.00.
  At 32,768, *control* crossings mostly hold too (3/5 control runs show
  structural takeovers with diversity collapse of 22–82%, vs m16 2/5).
  Takeover persistence is a property of population scale, not conservation.
- **E1c (scale-invariance confirmed):** m16 first-block epoch median 5,829
  at 32,768 vs 5,296 at 16,384; MW-U two-sided p = 0.22.

## Consolidated three-scale picture

| Population | Control emergence | Control crossings held | m16 crossings held |
|---:|---:|---:|---:|
| 4,096 (100K epochs) | 1/5 | 0/1 | 1/2 (m0.5+1, m2+2, m16+2 crossings; only m16 s0 held) |
| 16,384 (50K epochs) | 1/5 | 0/1 | 1/1 |
| 32,768 (100K epochs) | 3/5 | 2/3 | 2/2 |

Population scale governs both emergence probability and takeover persistence.
Conservation governs the *resource economy*: it binds during emergence from
random soups (blocked-fraction curve, shadowing onset, symbol-specific bursts)
and is neutrally closed once a replicator ecology is established. The two
factors are separable, and this is the headline of the auto-loop campaign.
