# Phase 1 new-experiment batch: preregistration

Date: 2026-08-15 (auto-loop batch 1)
Scope: three experiments targeting the top open items from `reports/phase1_final_report_2026-08-12.md` ("Next steps, in order") and `reports/phase1_follow_ups.md`.

All runs use the existing deterministic probes (`experiments/paper_probe.py`, `experiments/phase1_probe.py`, `experiments/metabolic_trace_probe.py`) with two additive, logging-only extensions:

1. `--initial-soup <npy>` / `--epoch-offset <int>` on `paper_probe` and `phase1_probe` (load a natural Phase 0 checkpoint; RNG streams continue at `derived_seed(seed, epoch + offset)`).
2. `--flow-window <int>` on `metabolic_trace_probe` (per-window donor→receiver flow edges derived as deltas of the cumulative flow matrix; kernel untouched, byte trajectories unchanged).

Verification for every run: manifest `exit_status == "success"`, `max_conservation_residual == 0` at every checkpoint (conserved runs), and aggregate row counts consistent with epochs/callback cadence. Determinism spot-check: one duplicated run per new code path must produce byte-identical `aggregate.csv`/`writes.csv`.

---

## Experiment A — Long-window emergence at 4,096 tapes (follow-up: "longer runs rather than a denser grid")

Prior result: 0 entropy transitions in 9 conserved runs (multipliers 0.5/2/16 × 3 seeds, 20,000 epochs, 4,096 tapes).

Design: 4,096 tapes, **100,000 epochs**, mutation 1/4096, shuffled-disjoint pairing.
Arms: conservation multipliers {0.5, 2, 16} × seeds {0–4} (phase1_probe) and a **no-conservation control** (paper_probe) × seeds {0–4}.

Transition criterion (unchanged from prior reports): high-order entropy ≥ 1.0 bits/byte sustained ≥ 3 consecutive callbacks.

### Hypotheses

- **A1 (horizon sufficiency, control):** emergence occurs in at least 1/5 control seeds within 100,000 epochs. If 0/5, the prior absence of transitions at 4,096 tapes is attributable to population sub-threshold, not horizon; report as such.
- **A2 (conservation suppresses emergence, main):** emergence probability under multiplier 2 ≤ control. Test: one-sided Fisher exact on 2×2 counts (5v5); report exact p regardless of outcome.
- **A3 (scarsity ordering):** within conserved arms, maximum high-order entropy decreases with multiplier scarcity: Spearman ρ between multiplier and max entropy over all 15 conserved runs, expected negative; two-sided p.
- **A4 (blocked-rate reproduction):** blocked-write fraction at 4,096 tapes/100K epochs matches the published 20K-epoch monotone scarcity curve (Spearman ρ(multiplier, blocked fraction) = −1 direction); deviation reported as a finding.

## Experiment B — Conserved continuation of a natural replicator ecology (follow-up: "checkpoint continuations")

Design: start from the Phase 0 seed-0 checkpoint at epoch 2,433 (`runs/paper_probe_seed0_transition.npy`, 131,072 tapes, replicators emerging but takeover incomplete). Continue **8,000 epochs** with `epoch_offset = 2433`. Pool is histogram-matched to the checkpoint soup.

Arms (1 seed each — single natural checkpoint, no replication available):
- B-control: paper_probe continuation (no conservation), also new-dominant-metrics columns.
- B-m0.5, B-m2, B-m16: phase1_probe continuations.
- B-baseline-m2: phase1_probe from a *random* soup, same scale/multiplier/epochs (blocked-rate comparator for B4).

### Hypotheses

- **B1 (control validity):** control continuation completes takeover: final dominant-tape fraction > 0.5 and sustained high-order entropy > 1 bit/byte. If not, the checkpoint is not a viable takeover precursor and B2–B3 are uninterpretable (report honestly).
- **B2 (intermediate conservation disrupts takeover):** at multiplier 2, final dominant fraction < 0.5 AND final high-order entropy below the control's by ≥ 0.5 bits/byte. (Directional prediction: replicators concentrate demand on `<`(60)/`]`(93); their pool supply at multiplier 2 cannot sustain the takeover rate.)
- **B3 (loose conservation is neutral):** at multiplier 16, final dominant fraction > 0.5 (same binary outcome as control).
- **B4 (replicator demand concentrates scarcity):** first-1,000-epoch blocked-write fraction under B-m2 exceeds the same measure under B-baseline-m2 (comparison of two epoch-series; report per-series means and the difference with a block-bootstrap CI over 100-epoch blocks).

## Experiment C — Windowed flow organization vs. null (follow-up: "test flow enrichment against a null model")

Prior result: aggregate donor→receiver graphs nearly complete → well-mixed circulation; windowed structure unknown.

Design: rerun the 9-cell metabolic-trace campaign (multipliers {0.5, 2, 16} × seeds {0–2}, 256 tapes, 20,000 epochs) with `--flow-window 2000` → 10 consecutive flow matrices per run. Verify aggregate outputs remain identical to prior campaign (same config ⇒ same run contract; prior runs will be re-executed into a new output dir because `flow_window` enters the config).

Null model: within each window, donor labels are permuted independently (uniform random permutation of rows/cols of the flow matrix), preserving out- and in-strength sequences approximately but destroying identity-specific structure. Statistic: Spearman correlation of edge weights between consecutive windows (observed) vs. permuted null (2,000 resamples per window pair).

### Hypotheses

- **C1 (main, two outcomes both informative):** observed mean window-to-window weight correlation exceeds the null mean (paired permutation test over the 9 window-pair series × 9 window pairs, α = 0.05, report effect size). If not significantly above null: conclude flow structure is consistent with well-mixed recycling — no persistent organizations at this scale; closes campaign H2 as a negative result.
- **C2 (scarsity sharpens structure):** observed-minus-null correlation gap decreases with multiplier (0.5 → 16). Spearman over 9 runs, two-sided. A significant *increase* (scarcer → less organized) is equally reportable.

## Statistical toolkit (implemented in `experiments/analyze_phase1_newexperiments.py`)

- Exact Mann-Whitney U (normal approximation with tie correction where n>20), one- and two-sided.
- Fisher exact (2×2), one- and two-sided.
- Spearman rank correlation with t-approximation p-values; exact where n ≤ 10 feasible is skipped in favor of the t approximation (n=15, 9).
- Bootstrap percentile CIs (10,000 resamples, seeded RNG) and moving-block bootstrap (block=100) for epoch-series comparisons.
- Paired permutation tests (2,000 resamples, seeded).
- All p-values reported regardless of significance; no post-hoc threshold changes.

## Decision rules (pre-committed)

- If A1 fails (0/5 control emergences), do not interpret A2 as evidence about conservation; instead report the 4,096-tape population as below the emergence threshold at 100K epochs and flag a population sweep (16,384/32,768) as the next batch.
- If B1 fails, B2/B3 become descriptive case studies only.
- If C1 null is not rejected, record "no persistent organization detectable at 256-tape scale" and defer organization search to larger scales with event-level logging.
