# Phase 1 hypothesis report and bounded follow-up plan

## Scope

This campaign tests **Stage/Phase 1 symbol conservation only**. Energy, dissolution, space, signals, task bias, and externally imposed fitness remain disabled. Existing Phase 0 results are used only as a baseline comparator.

The current Stage 1 world has a fixed tape count, so the original phrase “population growth saturates” is not measurable. The scientifically valid replacement is **content-turnover saturation**: successful changes slow as requested byte values become scarce.

## Confirmatory hypotheses

### H1 — Scarcity response

As `pool_multiplier` increases, the blocked-write fraction and pool-composition drift decrease.

- Primary response: interval blocked writes / interval attempted writes.
- Secondary responses: pool entropy change, zero-count symbol count, and changed-state entropy.
- Expected direction: monotonic decrease in scarcity with multiplier.

### H2 — Intermediate-scarcity organization

The single-seed pilot suggested that intermediate scarcity (`pool_multiplier = 2`) can create more high-order structure than either tighter (`0.1–0.5`) or looser (`16+`) pools.

- Primary response: maximum Brotli-based high-order entropy.
- Decision rule: treat this as supported only if the intermediate condition exceeds both neighboring regimes in the replicated distribution, not just one seed.
- Status: confirmatory follow-up to an exploratory pilot; effect size and uncertainty matter more than a binary p-value.

### H3 — Blocking is bursty and symbol-specific, not a smooth global shortage

Blocked writes should cluster within long-running interactions that repeatedly request one scarce symbol.

- Responses: coefficient of variation, lag autocorrelation, spectral concentration, zero-block interval fraction, and per-symbol blocked-write concentration.
- Competing explanation: a broad global shortage would distribute blocked attempts across many symbols and produce smoother time series.

### H4 — Conservation produces measurable byte recycling and cross-tape acquisition

Pool-mediated writes should recycle byte values and successful copy instructions should transfer values across the A/B tape boundary.

- Cross-tape acquisition: successful `.` or `,` operations whose source and destination heads are on opposite tapes.
- Conservative lower bound on recycling: once cumulative withdrawals of symbol `v` exceed its initial free-pool count, the excess withdrawals must use copies of `v` previously returned by tape replacement. Summed over symbols:

  `recycled_lower_bound = Σ max(0, withdrawals[v] - initial_pool[v]) / Σ withdrawals[v]`

- Limitation: bytes are indistinguishable, so this proves value-level recycling, not the identity path of an individual byte token.

## Exploratory hypotheses

### E1 — Conservation changes emergence at a larger, more capable scale

At larger populations, intermediate conservation may delay, suppress, or organize the Phase 0 emergence pathway. This is exploratory because exact Stage 1 execution must serialize access to the global pool, limiting affordable scale.

### E2 — Conservation alters the active-instruction trajectory

Scarcity may enrich compact instruction configurations, or may suppress them by withholding critical operator/data bytes. Active BFF instruction fraction and exact-tape dominance are tracked as imperfect minimization proxies. Fixed 64-byte tapes do not permit literal genome-length shrinkage, so no claim about length minimization will be made from `length_nonzero` alone.

## Experiment matrix

### A. Replicated 256-tape mechanism sweep

- Multipliers: `0.1, 0.5, 2, 16, 256`
- Seeds: `0–4`
- Population: 256 tapes
- Epochs: 20,000
- Pairing: shuffled disjoint
- Mutation: `1/4096` per byte
- Callback: every 100 epochs

Purpose: estimate mechanism-level distributions cheaply and test H1–H4.

### B. Larger-scale follow-up

Chosen after benchmarking the exact conserved probe. Priority conditions are `0.5, 2, 16`; at least three seeds are attempted if runtime is tractable.

Purpose: test whether the 256-tape patterns persist when more interactions and exact-tape collisions are available.

## Stopping and integrity rules

1. No conditions or seeds will be discarded because their outcomes are uninteresting.
2. Any invariant failure stops that run and is reported.
3. The per-symbol invariant `tape histogram + pool histogram = initial conserved totals` must be exact at every aggregate checkpoint.
4. A high-order-entropy threshold crossing is evidence of large-scale correlation, not by itself proof of self-replication.
5. Exact hash dominance and cross-tape copy flux are supporting observables; no simulator-side fitness or replication detector is introduced.
6. Follow-ups are labeled exploratory when selected after inspecting this campaign.

## Planned outputs

- One manifest and two CSVs per run: aggregate trajectory and per-symbol ledger trajectory.
- One campaign summary CSV with one row per condition and seed.
- A hypothesis-results report separating supported, unsupported, and unresolved claims.
- A final readable Phase 1 report linking findings to Phase 0 and giving integration steps and reading priorities.
