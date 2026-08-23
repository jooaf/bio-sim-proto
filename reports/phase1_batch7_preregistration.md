# Phase 1 batch 7 preregistration — specificity control: class filter vs generic friction

Date: 2026-08-19. Generated under the batch-6 decision rule: H1a supported
(0/5 emergence under exclusion of the natural six vs 3/5 control, one-sided
Fisher p = 0.083); H2 0/3 descriptively consistent. Before claiming a
**class-specific origin filter**, the generic-friction alternative must be
excluded: H1 runs had 2.5–3.4×10⁸ blocked writes; maybe *any* exclusion pool
at multiplier 2 blocks enough writes to suppress emergence regardless of
which symbols are excluded.

Existing partial rebuttal (batch 4): uniform m2 pools (~10⁸ blocked writes,
similar magnitude) still produced 1/3 emergence — but that was a different
mismatch geometry. A direct control is required.

## I1 — exclusion of six NON-structural symbols (specificity control)

**Design:** 32,768 tapes × 100,000 epochs, mutation 1/4096, multiplier 2,
pool mode `excluded_list` with symbols **[200, 201, 202, 203, 204, 205]**
(six arbitrary bytes that are neither BFF opcodes, nor enriched in the
natural replicator class, nor special in any known way), seeds 0–4.

**Hypothesis I1 (specificity):** emergence ≥ 2/5. If met, suppression in
batch 6 is specific to the natural replicator symbols — the matter economy
filters by *class*, not by friction volume. If emergence ≤ 1/5, suppression
is generic (any m2 exclusion pool kills the origin transition) and the
batch-6 result is a friction effect; report honestly and conclude
"conservation as blunt origin suppressor" instead.

**Registered secondary metrics:** blocked-write totals (must be comparable
to H1's 2.5–3.4×10⁸ for the contrast to be clean — if I1 blocks far less,
note the asymmetry), final share of symbols 200–205, entropy trajectories.

## I2 — single non-structural symbol exclusion (H2's specificity pair)

Same design with excluded list **[42]** (a single arbitrary non-opcode
byte), seeds 0–2. Hypothesis I2: emergence ≥ 1/3 (control rate 3/5). Pairs
with H2 (symbol-0-only exclusion, 0/3) to isolate the null-byte dependence.

## I3 — analysis-only: mechanism in suppressed runs

From existing batch-6 symbols.csv: per-symbol content trajectories of the
loop/copy opcodes ([, ], <, ,, }) and byte 0 in H1/H2 runs vs batch-3
control emergent runs — verify suppressed runs never grow structural-symbol
content (bounded at random-soup levels with slow ratchet decline), while
control emergent runs grow them 4–40×. Also: entropy distribution of
suppressed runs vs random-soup baseline (elevated 0.25–0.4 — quantify).

## Decision rules

- I1 met (≥ 2/5) → **breakthrough confirmed: the conserved matter economy
  is a class-specific origin filter** — it determines whether replication
  can emerge (zero-supply of the natural class's structural symbols blocks
  the origin transition) while remaining homeostatic in established
  ecologies. Close the campaign and consolidate.
- I1 not met (≤ 1/5) → suppression is generic friction; consolidate with
  the honest headline "conservation suppresses origin at m2 exclusion
  regardless of class; homeostatic otherwise."
- No further batches after I regardless of outcome unless a new concrete
  question emerges from I3.

## Runs

`experiments/run_phase1_batch7.nu` (8 runs: I1 seeds 0–4, I2 seeds 0–2,
final-soup checkpoints saved). Analysis: `experiments/analyze_phase1_batch7.py`
(includes I3).

## Campaign status note

Batches 4–6 cost summary to date: 26 completed runs (~14.5 core-hours),
all conserved runs at zero conservation residual, all manifests success.
