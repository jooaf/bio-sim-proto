# Phase 1 final report: conserved-symbol program soup

**Date:** 2026-08-12
**Scope:** Phase 1 symbol conservation only—no energy, dissolution, space, signals, task bias, or external fitness.

## Gate-closing addendum: metabolic paths and SKI

The two open follow-ups were completed after the original report:

- **Explicit path tracing:** nine 20,000-epoch BFF runs at multipliers 0.5, 2, and 16 reconstructed deterministic token witnesses without changing byte trajectories. Every run showed return→reacquisition, cross-tape transfer, reciprocal flow, and directed cycles with zero byte/token conservation failures.
- **Burst mechanism:** in the most blocked 1% of epochs, one interaction explained 80.4% of blocking at multiplier 0.5 and 97.8% at multiplier 2; its leading symbol explained 99.1% and 99.9%, and it exhausted the full execution budget in every case. At multiplier 16, the leading symbol remained exclusive, but one interaction explained 57.8% and only 19.8% exhausted the budget.
- **Ecological qualification:** donor→receiver graphs were essentially complete and reciprocal. This proves explicit matter circulation, but it looks well-mixed rather than like a sparse, persistent metabolic organization.
- **SKI validation:** nine 5,000-tick, 256-tape SKI runs completed through the existing world, scheduler, invariants, six Parquet tables, and Stage 1 report pipeline. Every expression snapshot remained valid and every conservation residual was zero.
- **SKI determinism:** two independent short runs produced byte-identical output for all six Parquet tables, digest `c56352a9ce4b425692156556c9625be51f837c4e614a5e49da1c0411a958d5c8`.
- **Unexpected SKI result:** scarcity was non-monotonic. Mean blocked-slot fractions were 76.82% at multiplier 0.5, 89.29% at 2, and 0.55% at 16. Multiplier 2 supported longer expressions than 0.5, then those expressions demanded more scarce combinator/application symbols.

These results close the two requested mechanical Phase 1 items. They do **not** establish organism-like metabolism: explicit circulation is currently compatible with globally mixed random turnover.

Detailed addendum reports:

- `reports/phase1_metabolic_trace_report.md`
- `reports/phase1_metabolic_path_examples.csv`
- `reports/phase1_ski_validation_report.md`
- `reports/phase1_ski_determinism.json`

## Short version

Phase 1’s conservation mechanism is mechanically sound and scientifically active.

- **Exact conservation held:** every recorded per-symbol residual was zero, including a 100,000-epoch validation.
- **Scarcity is tunable and monotonic:** mean blocked-write rate at 256 tapes fell from **30.30%** at pool multiplier 0.1 to **0%** at 256.
- **There are two scarcity regimes:** very tight pools impose broad, nearly continuous blocking; moderate/loose pools create rare, byte-specific bursts.
- **The limiting bytes are structured:** at moderate and larger scales, byte 60 (`<`) dominated blocking; byte 93 (`]`) dominated several tighter 256-tape runs.
- **Bytes are genuinely recycled:** all runs showed successful cross-tape copying, and repeated withdrawal beyond the initial reservoir proves return/re-acquisition of byte values through the pool.
- **Intermediate scarcity may increase organization, but the evidence is not decisive:** multiplier 2 had the highest mean peak high-order entropy, but its matched-seed contrast had a 95% bootstrap interval crossing zero.
- **No replication-scale transition occurred:** none of nine 4,096-tape runs crossed 1 bit/byte high-order entropy by epoch 20,000, and no exact tape dominated.
- **Uniform pool initialization is not a clear improvement:** it slightly reduced early blocking at multiplier 0.5, but did not reliably improve long-run behavior.

The key practical conclusion is that **pool multiplier 2 is a useful genuinely constrained regime**, not an effectively unlimited control. Use 0.5 as a scarcity stress condition and 16 as a near-unconstrained comparison.

---

## What was run

### Main replicated campaign

| Matrix | Conditions | Seeds | Runs | Duration |
|---|---|---:|---:|---:|
| Mechanism sweep | 256 tapes; multipliers 0.1, 0.5, 2, 16, 256 | 0–4 | 25 | 20,000 epochs |
| Scale follow-up | 4,096 tapes; multipliers 0.5, 2, 16 | 0–2 | 9 | 20,000 epochs |
| Pool-initialization follow-up | 256 tapes; uniform pools at 0.1 and 0.5, paired with existing matched-pool runs | 0–4 | 10 new | 20,000 epochs |
| Long validation | 256 tapes; multiplier 2 | 0 | 1 | 100,000 epochs |

This is **45 new scientific Phase 1 runs**, totaling about **471 million ordered tape interactions**, plus one excluded 2,000-epoch scale benchmark. The earlier four-condition detailed pilot remains an independent supporting dataset.

Every automated batch finished successfully according to its manifest. The monitor found no failed campaign run.

### Instrumentation added

`experiments/phase1_probe.py` is a serial Numba probe with:

- deterministic SplitMix64 initialization, mutation, and shuffled-disjoint pairing;
- exact global-pool mediation for every changing mutation and BFF write;
- aggregate high-order entropy, exact-tape abundance, active-instruction fraction, and pool drift;
- per-epoch write/blocking time series;
- per-symbol withdrawals, returns, blocked requests, and cross-tape copy directions;
- run manifests and conservation checks.

The kernel is serial by design: interactions compete for one global pool, so reordering or parallel pool updates would change the physics.

---

## Main findings

## 1. Conservation and the scarcity curve

All 34 main-campaign runs and all 10 pool-initialization runs had **maximum conservation residual 0**. The 100,000-epoch run also had residual 0 at all 201 independent aggregate checks, a constant free-pool total of 32,768 bytes, and atomic conservation on every accepted write.

### 256-tape mechanism sweep

| Pool multiplier | Blocked fraction, mean [95% bootstrap CI] | Pool entropy change | Peak high-order entropy | Entropy transitions |
|---:|---:|---:|---:|---:|
| 0.1 | 0.3030 [0.2556, 0.3630] | -0.549 | 0.116 | 0/5 |
| 0.5 | 0.1486 [0.0945, 0.1939] | -0.195 | 0.362 | 0/5 |
| 2 | 0.0308 [0.0178, 0.0475] | -0.070 | 0.614 | 0/5 |
| 16 | 0.0014 [0.0004, 0.0024] | -0.008 | 0.476 | 0/5 |
| 256 | 0.0000 [0.0000, 0.0000] | approximately 0 | 0.476 | 0/5 |

The rank correlation between multiplier and mean blocked rate was **-1.00**. Total free matter never declined; only its composition changed. Phase 1 therefore creates **selective nutrient scarcity**, not total reservoir exhaustion.

### Interpretation

- **0.1:** severe global constraint.
- **0.5:** strong but dynamic scarcity.
- **2:** moderate, biologically interesting constraint.
- **16:** near-unconstrained on average, but still capable of rare blocking bursts.
- **256:** practical unlimited-pool control for this duration and scale.

## 2. Blocking changes character across regimes

At multiplier 0.1, blocking was broad and almost continuous:

- effective blocked-symbol count: **177.7 of 256**;
- epochs with zero blocking: **0.01%**;
- blocked-fraction coefficient of variation: **0.9**.

At multiplier 2, scarcity became episodic:

- effective blocked-symbol count: **17.2**;
- epochs with zero blocking: **67.4%**;
- coefficient of variation: **4.9**.

At multiplier 16:

- epochs with zero blocking: **96.2%**;
- coefficient of variation: **12.0**;
- almost every blocked request, when blocking occurred, targeted byte 60 (`<`).

The median strongest Fourier component contained only **1.1%** of non-DC power, so there is no evidence for a narrow periodic oscillator. The best current explanation is:

> tight pools are a broad global brake; moderate and loose pools are usually permissive but occasionally hit a long, symbol-specific request burst.

At 256 tapes, `]` was the leading blocked symbol in all multiplier-0.5 seeds. At 4,096 tapes, `<` led every condition and accounted for about **72–74%** of blocked attempts at multiplier 2. This suggests that conserved soups selectively accumulate particular control/head-motion bytes in tapes.

## 3. Recycling and acquire/decompose evidence

Every run recorded successful changed-value copy operations across the A/B tape boundary. The final median lower bound on recycled withdrawals was **98.7%** across the main campaign.

The lower bound is conservative: once cumulative withdrawals of symbol `v` exceed the initial free count of `v`, excess withdrawals must use copies returned by earlier tape replacement. This demonstrates:

1. byte values leave the pool and enter tapes;
2. overwritten values return to the pool;
3. returned values are subsequently acquired again;
4. cross-tape copy instructions move values between interacting tapes.

This is **value-level acquire→return→reacquire evidence**, not yet a complete metabolic lineage. Bytes are indistinguishable, and the aggregate ledger cannot identify an individual token’s path through tapes A, B, and C. A sampled requested-symbol event trace is needed for a stronger acquire/decompose claim.

Also, a high recycling fraction alone is not evidence of life-like metabolism: long random dynamics can repeatedly cycle values. It is a necessary flow signature that must be combined with persistence, replication, or closed reaction structure.

## 4. Intermediate scarcity and organization

The preregistered hypothesis was that multiplier 2 would exceed both 0.5 and 16 in peak high-order entropy.

- Mean peak entropy at 256 tapes: **0.362** at 0.5, **0.614** at 2, and **0.476** at 16.
- Matched-seed multiplier-2 advantage over the better of 0.5 and 16: **+0.088 bits/byte**.
- 95% bootstrap interval: **[-0.071, 0.247]**.
- Seeds favoring multiplier 2: **3/5**.

**Decision: unresolved.** The point estimate supports an intermediate-scarcity effect, but the uncertainty and seed consistency do not.

At 4,096 tapes the same ordering was weakly visible—0.406, 0.425, and 0.347—but only three seeds were run per cell. No condition crossed the 1-bit/byte transition threshold.

## 5. No emergence at 4,096 tapes within 20,000 epochs

| Multiplier | Runs | Entropy transitions | Mean peak high-order entropy | Mean maximum dominant fraction |
|---:|---:|---:|---:|---:|
| 0.5 | 3 | 0 | 0.406 | 0.00098 |
| 2 | 3 | 0 | 0.425 | 0.00098 |
| 16 | 3 | 0 | 0.347 | 0.00049 |

There was no sustained exact-tape takeover and no high-order-entropy transition. This is a negative result, not proof that conservation prevents emergence. Phase 0 already showed that 256 tapes are underpowered, and the known reliable Phase 0 regime uses 131,072 tapes—32 times larger than this Phase 1 matrix.

Exact conserved execution is serial, so paper-scale Stage 1 runs need a faster compiled implementation or a carefully validated deterministic architecture.

## 6. Pool-initialization follow-up

Uniform and histogram-matched pools were compared at equal total free matter.

- Both modes had **zero truly initial missing symbols** in these SplitMix64 soups. The earlier pilot’s “initial zero symbols” were measured after the first interaction tick, not before execution; that wording should be corrected.
- At multiplier 0.5, uniform initialization reduced first-100 blocking by **0.0109** with paired 95% CI **[-0.0276, -0.0003]**.
- The overall blocked-rate difference at 0.5 was unresolved: **-0.0111 [-0.0735, 0.0653]**.
- At multiplier 0.1, uniform initialization unexpectedly increased final pool divergence by **0.0150 [0.0075, 0.0236]**.
- The multiplier-0.5 entropy increase was large in mean (**+0.179**) but inconsistent across seeds and unresolved (**[-0.010, 0.412]**).

**Decision:** keep histogram matching as the default. Uniform initialization is a useful control, not a demonstrated improvement.

---

## Hypothesis decisions

| Hypothesis | Decision | Why |
|---|---|---|
| H1: blocked writes and pool drift decline with multiplier | **Supported** | Strict monotonic group means; rank correlation -1.00 |
| H2: intermediate scarcity maximizes organization | **Unresolved** | Positive point estimate, but bootstrap interval crosses zero and only 3/5 paired seeds agree |
| H3: blocking is bursty and symbol-specific | **Regime-dependent support** | Broad/continuous at 0.1; rare and highly concentrated at 2–16 |
| H3b: blocking is periodic | **Not supported** | Weak, diffuse spectral peaks |
| H4: conservation creates byte recycling and acquisition | **Supported at value level** | Cross-tape changed copies in every run; withdrawals necessarily reuse returned values |
| E1: larger Phase 1 populations show emergence by 20K | **Not observed** | 0/9 transitions at 4,096 tapes |
| P1.6: uniform initialization materially improves dynamics | **Mostly unsupported** | Small early effect at 0.5; no robust long-run benefit |

---

## How this ties to Phase 0

Phase 0 established three important baselines:

1. **Scale dominates emergence.** The 256-tape soup rarely replicated, while the 131,072-tape paper protocol produced transitions in seeds 0 and 2 of the four reference-rate seeds run so far.
2. **Mutation has a Goldilocks regime.** Seed 0 transitioned at the reference mutation rate `1/4096`, but not at zero or `1/128` within 16,000 epochs.
3. **Long BFF loops are scientifically meaningful.** Replicator-rich Phase 0 runs were much slower and consumed more character reads.

Phase 1 held the mutation rate at the Phase 0 reference value, isolating the conservation effect. It then showed that long-loop behavior couples to scarcity: an interaction can repeatedly request one depleted byte and create a sharp blocked-write burst.

What cannot yet be claimed:

- The 4,096-tape Phase 1 result is not directly comparable to the 131,072-tape Phase 0 emergence result.
- There is no matched Phase 0/Phase 1 4,096-tape matrix in this Phase 1-only campaign.
- Fixed 64-byte tapes do not permit literal genome-length shrinkage. `length_nonzero` is not a valid minimization measure for random byte tapes.

The cleanest bridge is a **continuation intervention**: take a naturally emerged Phase 0 checkpoint and continue it under Phase 1 conservation at multipliers 0.5, 2, and 16. This would directly test whether conservation disrupts, stabilizes, or reorganizes an existing replicator ecology without seeding a designed replicator.

---

## How to integrate the findings

### Experimental defaults

Use a three-condition core panel:

- **0.5:** strong-scarcity stress;
- **2:** primary Phase 1 regime;
- **16:** near-unconstrained control.

Use 0.1 only for freeze/global-brake tests and 256 only as a practical unlimited-pool control.

### Logging

The token-audited probe now emits:

- per-epoch largest blocked interaction, dominant requested symbol, and execution length;
- complete donor→receiver token-flow edges;
- per-token return and reacquisition totals;
- bounded sampled token paths with donor, receiver, pool residence, opcode, and template-source tape.

Keep this as an audit instrument rather than the default hot-loop logger. The next analysis step is a shuffled-pair/windowed null model for detecting flow enrichment above globally mixed circulation.

### Stage semantics

Replace “population growth saturation” with **content-turnover saturation** until birth, placement, and free cells exist. The current Phase 1 tape count is fixed, so population growth is structurally impossible.

Do not use nonzero byte count as genome length. Better minimization observables are:

- active instruction count;
- functional self-replication score;
- protected/overwritten regions;
- compressed phenotype length;
- persistent exact-tape or functional-family abundance.

### Software architecture

Keep the exact Phase 1 probe separate from the detailed Parquet simulator, as already done for the Phase 0 paper probe. Preserve this run contract:

- `config.json`
- `manifest.json`
- `aggregate.csv`
- `writes.csv`
- `symbols.csv`

When the Polars/SQLite experiment refactor lands, register these aggregate probe runs without forcing them through the detailed `FactEmitter` pipeline.

### Stage 2 preparation

Dissolution should remain physically neutral—it must not target “bad” tapes—but analysis should test whether dissolution relieves the specific `<` and `]` shortages found here. That is the direct bridge from conservation to a closed nutrient cycle.

---

## Next steps, in order

1. **Test flow enrichment against a null model.** Compute windowed donor→receiver networks and compare persistence/modularity with shuffled-pair trajectories. The complete aggregate graph is too well mixed to identify organizations.
2. **Continue natural Phase 0 replicator checkpoints under conservation** at 0.5, 2, and 16, with matched seeds and no designed replicators.
3. **Run longer 4,096-tape Phase 1 windows** for the most informative cells rather than widening the multiplier grid. Multiplier 2 remains the priority.
4. **Add functional phenotype scoring** to Phase 1 checkpoints; entropy and token circulation alone cannot prove replication or metabolism.
5. **Treat the minimal SKI model as a portability fixture, not an ecological reference.** A future chemSKI/Combinatory-Chemistry comparison needs explicit reaction-token semantics and its own preregistration.
6. **Move the exact global-pool kernels to Rust/Odin** before paper-scale conserved runs. Preserve serial deterministic semantics unless an alternative ordering is formally specified and validated.

---

## Phase 1 gate status

| Original criterion | Status |
|---|---|
| Exact symbol conservation | **Pass** mechanically; 100K BFF validation plus all BFF-token and SKI runs had zero residual |
| Pool-multiplier sweep across at least five values | **Pass** |
| Saturation scales with pool size | **Pass for turnover/scarcity; not measurable as population growth** |
| Acquire/decompose pattern | **Pass as explicit matter-path evidence**—auditable return→reacquire and cross-tape cycles; **no claim of organized metabolism** |
| SKI through the same pipeline | **Pass**—unchanged world, scheduler, invariants, and logging modules; deterministic Parquet output |

The two previously open implementation/mechanism criteria are now closed. Phase 1’s engineering gate is **complete**, while the stronger scientific question—whether conservation creates persistent metabolic organizations rather than well-mixed recycling—remains a negative/unresolved result for later analysis.

---

## Papers to read next

Companion plain-language guide: `reports/phase1_papers_eli5_reading_guide.md`. It explains every paper below with analogies, vocabulary, project connections, cautions, and reading questions.

### Read first

1. **Kruszewski & Mikolov (2020), “Combinatory Chemistry: Towards a Simple Model of Emergent Evolution.”**
   [arXiv:2003.07916](https://arxiv.org/abs/2003.07916)
   The direct conservation comparator. Focus on how acquire/decompose/reassemble cycles are identified; use that standard to strengthen the current value-level recycling result.

2. **Kruszewski & Mikolov (2021), “Emergence of Self-Reproducing Metabolisms as Recursive Algorithms in an Artificial Chemistry.”**
   [arXiv:2103.08245](https://arxiv.org/abs/2103.08245)
   Best guide for deciding whether recurrent byte flow is genuinely metabolism-like rather than mere turnover.

3. **Agüera y Arcas et al. (2024), “Computational Life: How Well-formed, Self-replicating Programs Emerge from Simple Interaction.”**
   [arXiv:2406.19108](https://arxiv.org/abs/2406.19108)
   Re-read the entropy transition and functional self-replication methods before adding phenotype scoring to Phase 1.

### Read for the next analysis implementation

4. **Buliga (2023), “chemSKI with tokens: world building and economy in the SKI universe.”**
   [arXiv:2306.00938](https://arxiv.org/abs/2306.00938)
   Closest analogue to finite pool bytes as rewrite tokens; useful for interpreting ordering constraints and scarcity cost.

5. **Hordijk (2023), “A Concise and Formal Definition of RAF Sets and the RAF Algorithm.”**
   [arXiv:2303.01809](https://arxiv.org/abs/2303.01809)
   Practical foundation for detecting reflexively autocatalytic, food-generated subsets after event-level flow logging exists.

6. **Hordijk, Wills & Steel (2014), “Autocatalytic Sets and Biological Specificity.”**
   [arXiv:1307.2860](https://arxiv.org/abs/1307.2860)
   Relevant because BFF interactions combine cleavage-like splitting and ligation-like concatenation.

### Read for theory and the Phase 0 connection

7. **Kolchinsky, “Thermodynamics of Darwinian selection in molecular replicators.”**
   [arXiv:2112.02809](https://arxiv.org/abs/2112.02809)
   Provides a theoretical language for why stronger scarcity may reduce distinguishable selective differences and push dynamics toward effective neutrality.

8. **Eigen (1971), “Selforganization of matter and the evolution of biological macromolecules.”**
   [DOI:10.1007/BF00623322](https://doi.org/10.1007/BF00623322)
   Connects the Phase 0 mutation Goldilocks result to an error-threshold framework. The next major question is how that threshold shifts under conservation.

---

## Reproducibility map

- Preregistration: `reports/phase1_hypotheses_and_preregistration.md`
- Main hypothesis results: `reports/phase1_hypothesis_results.md`
- Follow-up plan: `reports/phase1_follow_ups.md`
- Pool-initialization result: `reports/phase1_pool_initialization_followup.md`
- Per-run main summary: `reports/phase1_campaign_runs.csv`
- Group bootstrap summary: `reports/phase1_campaign_group_summary.csv`
- Pool-initialization rows: `reports/phase1_pool_initialization_runs.csv`
- Main automation: `experiments/run_phase1_campaign.nu`
- Follow-up automation: `experiments/run_phase1_pool_initialization_followup.nu`
- Probe: `experiments/phase1_probe.py`
- Analyzer: `experiments/analyze_phase1_campaign.py`
- Pool-initialization analyzer: `experiments/analyze_phase1_pool_initialization.py`
- Gate-experiment preregistration: `reports/phase1_gate_experiments_preregistration.md`
- Metabolic trace report: `reports/phase1_metabolic_trace_report.md`
- Metabolic path examples: `reports/phase1_metabolic_path_examples.csv`
- Metabolic trace probe/analyzer: `experiments/metabolic_trace_probe.py`, `experiments/analyze_metabolic_trace.py`
- SKI report and run summary: `reports/phase1_ski_validation_report.md`, `reports/phase1_ski_validation_runs.csv`
- SKI determinism evidence: `reports/phase1_ski_determinism.json`
- SKI substrate: `soup/substrate/ski.py`

## Bottom line

Symbol conservation is not merely slowing the soup uniformly. It creates a measurable resource economy, a transition from broad scarcity to symbol-specific bursts, and explicit return→reacquisition cycles. The SKI experiment confirms that the conservation and logging architecture supports a second chemistry. What has **not** yet appeared is the higher-level payoff: no replication transition, takeover, or sparse persistent metabolic organization was detected at the scales run.

Phase 1’s two open mechanical criteria are now complete. The next move is not a wider blind sweep; it is a null-model test for organized flow and a conserved continuation of naturally emerged Phase 0 replicators.
