# Findings

## 2026-08-06 — Stage 0: bare soup

### What was built

- Deterministic, flat NumPy population of fixed-length BFF tapes with random ordered pairing.
- Plain-Python self-modifying BFF interpreter, tested against hand-worked examples for all ten opcodes.
- Explicit configuration tree and TOML round trips, single seeded `numpy.random.Generator`, stage gates, buffered raw Parquet logging, manifests, invariant log, experiment runner, and offline analysis/report pipeline.
- Raw tables: `ticks`, `interactions`, `tapes`, `lineage`, `population`, and `events`.
- Offline exact-copy inference from interaction hashes; no replication detector exists in the simulator.
- Hill effective-number diversity profiles and Stage 0 analysis skeletons for later metrics.

### Reference-semantic finding

The released `bff_noheads` implementation accompanying arXiv:2406.19108v2 wraps both data heads modulo the 128-byte joint tape. It bounds the instruction pointer, dynamically scans the current tape for brackets, wraps byte arithmetic, starts the PC and both heads at zero, and uses an 8,192-character budget. This differs from the build prompt's clamp-default statement. In accordance with the prompt's instruction to follow the paper, `head_wrap = true` is the documented Stage 0 default; clamping remains configurable.

### Acceptance results

Configuration: `experiments/configs/stage0.toml`; 20 seeds (0–19), 20,000 epochs/seed, 256 tapes, 256 interactions/epoch, 64 bytes/tape, 8,192-character budget. This produced 102,400,000 raw interaction records and approximately 5.0 GiB of run data.

1. **Replication emergence — FAIL.** Exact offline replication was found in **1/20 runs (5.0%)**, below the required 30%. Seed 18 had one event at epoch/tick **9,251**. Its inferred replicator hash reached maximum abundance **2**, so it did not take over.
2. **Distinct-hash collapse — FAIL.** All runs peaked at 256 distinct hashes. Final distinct count was 256 in 18 runs, 255 in seed 7, and 252 in seed 9 (mean **255.75**). No run crossed the report's predeclared clear-collapse threshold of 50%; the largest transient peak-to-minimum decline was **7.0%**. The one replication-positive run declined transiently by **5.469%** and finished at 256.
3. **Unattended load/report — PASS.** Every successful run loaded all six Parquet tables through `analysis/load.py`; `analysis/report.py` produced the 20-run report at `reports/stage0_batch_report.md` without manual data repair.
4. **Byte-identical deterministic Parquet — PASS.** Two independent short runs with identical seed/config produced exact byte equality for every raw Parquet file and the same aggregate SHA-256 digest: `12a44d46117095bef4502f32e0cabf111578fd904b34b8cc517e4a2f3207fb66`.

### Correctness and engineering

- Invariant violations: **0**; all 20 acceptance `invariant_log.jsonl` files were empty (0 bytes total).
- Tests: **24 passed**.
- Strict typing: `mypy --strict soup analysis` passed with **0 errors**.
- Golden short-run raw-Parquet digest: `f5cbbe69c6083390556a74c11a1ff68df6d58bd2b87105a1d767dc6e139a7906`.
- Plain-Python benchmark: **4,187,804 instruction-steps/s** (12,488,236 steps in 2.982 s), above the pre-Stage-2 target of 100,000/s. No JIT optimization was used.
- Acceptance run wall times under eight-way parallel load: min **505.52 s**, median **2,176.21 s**, max **5,624.07 s**. The wide range came from tapes entering long loops and consuming the full execution budget; this is substrate behavior, not scheduler nondeterminism.

### Diagnosis and surprise

The negative emergence result is not quantitatively comparable to the paper's ~40% result. The paper's usual soup contains **2^17 = 131,072 tapes** and executes a shuffled set of roughly population/2 disjoint interactions per epoch. The tractable Stage 0 config here contains 256 tapes and executes 256 with-replacement interactions per epoch: about **5.12 million interactions/run**, versus roughly **1.05 billion** in a 16,000-epoch paper run. The prompt did not specify Stage 0 population size or pairing-round cardinality. The lack of diversity collapse is therefore most plausibly an underpowered protocol mismatch, though it could still expose a semantic issue not covered by the paper/source verification.

No parameters were changed and no runs were discarded after observing the failure.

### What I would change (pending user decision)

Before Stage 1, choose one of:

1. define a feasible Stage 0 acceptance baseline for the 256-tape plain-Python soup;
2. reproduce the paper protocol exactly (131,072 tapes, shuffled disjoint pairs, 8,192 steps), which requires a major acceleration/compute-budget exception before Stage 1; or
3. add a configurable paper-style disjoint pairing mode and run an explicitly approved population/interaction-scale sweep to determine where the emergence rate changes.

The Stage 0 gate remains closed because criteria 1 and 2 failed. No Stage 1 mechanisms have been built.

## 2026-08-07 — Stage 0 protocol correction

The user approved correcting the protocol mismatch before rerunning acceptance. Stage 0 now supports both legacy with-replacement sampling and paper-style shuffled disjoint ordered pairs. The acceptance and visualization profiles use 128 disjoint pairs for the 256-tape population, so every tape participates exactly once per tick; the visualization profile also restores the 8,192-character execution budget. Existing findings above describe the old protocol and must not be combined with results from the corrected configuration.

### Corrected single-seed validation

At the user's request, the corrected validation was limited to seed 1 rather than a new 20-seed batch. The run completed all 20,000 ticks and 2,560,000 interactions with zero invariant violations. Every tick contained 128 disjoint pairs covering all 256 tapes exactly once, population counts remained exactly 256, and all raw tables loaded successfully. It produced 29,293,031 successful write attempts and 1,972,644 interactions that changed at least one byte, but no exact replication event; distinct hashes ended at 256 and the maximum transient collapse was 0.781%. Mechanical validation passed, while replication emergence and diversity-collapse evidence did not.

## 2026-08-07 — Paper-scale replication emergence reproduced

A source-level comparison with the released `cubff` implementation found a second protocol omission: its default run replaces each byte independently with probability 1/4096 (0.024414%) before interaction. Stage 0 now exposes and logs this mutation rate. A corrected 256-tape run produced 80,160 mutation events against an expectation of 80,000, but still showed no transition; this confirmed that population scale, not mutation alone, remained decisive.

The detailed Python logger cannot feasibly emit roughly one billion paper-scale interaction records. A bounded-log Numba probe was therefore added using the reference SplitMix64 initialization, Fisher-Yates shuffle, mutation stream, disjoint pairing, and 8,192-character BFF interpreter semantics. Its first-epoch 256-tape state is byte-identical to the released implementation, with SHA-256 `15b95a37cc6f48e526cbd8cd463607039f07da2d5c61714ac19d744e072871e3`.

One seed-0 run at the paper's 131,072-tape and 16,000-epoch scale reproduced the reported transition:

- first high-order entropy >=1 bit/byte: epoch 2,433;
- transition value: 1.827810 bits/byte;
- final value: 6.025684 bits/byte;
- minimum after the sustained second transition at epoch 2,817: 2.533667 bits/byte;
- maximum absolute difference from an independently built upstream run at matching epochs: 0.000001234 bits/byte;
- runtime: approximately 914 seconds with one experiment running;
- at epoch 2,433, 106 of the 1,024 most abundant exact tapes passed the paper's functional self-replication threshold, with a maximum score of 64;
- by the end, 1,023 of the 1,024 sampled abundant tapes passed, confirming persistent takeover rather than a transient compression artifact.

Metrics are in `reports/paper_probe_seed0.csv`; the first-transition soup is in `runs/paper_probe_seed0_first_transition.npy`. This closes the Stage 0 replication-emergence concern for the paper protocol. The earlier 256-tape acceptance criterion should be retired rather than treated as quantitatively comparable.

## 2026-08-08 — Stage 1: conserved symbol pool

Stage 1 introduces a global `SymbolPool` without changing BFF opcode semantics. Every mutation, increment, decrement, or copy that changes `old` to `new` must atomically consume one `new` byte from the pool and return `old`; if `new` is unavailable, the write is blocked and execution continues. No-op writes exchange nothing. The pool starts with twice the initial soup's observed count of each byte, matching `symbols.pool_multiplier = 2.0`.

The seed-1 validation ran 256 tapes for 20,000 ticks and 2,560,000 disjoint interactions. It completed in 391.34 seconds with zero invariant violations. Across 200 independently reconstructed tape/pool snapshots, every one of the 256 per-symbol totals was exactly conserved with maximum residual 0. The free pool remained exactly 32,768 bytes. BFF execution produced 7,453,461 accepted writes and 236,511 scarcity-blocked writes; background mutation produced 80,016 accepted replacements and 144 blocked replacements. Pool entropy moved from 7.988240 to 7.925357 bits while total matter remained fixed.

Raw run: `runs/20260808T061732.016519Z_6ca92e999401_1`; report: `stage1_report.md`; exact raw-Parquet digest: `4ab4d3a7c59eb81e7d59cdb9544a6fe35f06251792d22ae7f1a08c177db24488`.

### Pygame experiment controls and provenance

The viewer now supports both Stages 0 and 1 and exposes every runtime-safe parameter through keyboard and clickable controls. Initialization/shape values remain immutable within a run because changing them defines a new experiment. The UI displays the Stage 1 pool and permits validated tick-boundary changes to execution budget, BFF head behavior, pairing, interaction and mutation rates, logging cadence, render cadence, speed, and colour. Initial and final effective TOML configurations are retained separately; every accepted change is written immediately to `parameter_changes.jsonl`, duplicated in the Parquet event stream, and counted in the manifest. A headless Stage 1 visual smoke run completed with truthful pool and close events.

## 2026-08-09 — Targeted unattended experiment pilots

A four-condition Stage 1 pool-multiplier pilot and a three-condition paper-scale mutation pilot completed sequentially with no invariant failures. Pool multipliers 0.1, 0.5, 2, and 16 produced overall blocked-write rates of 30.79%, 14.95%, 3.05%, and 0.12%, respectively. Pool totals remained fixed, demonstrating that the relevant failure mode is selective symbol depletion rather than total-pool exhaustion. Blocking remained episodic: even multiplier 16 had a one-tick blocked fraction above 84% despite a near-zero average, consistent with individual long loops repeatedly requesting a scarce symbol.

At paper scale for seed 0, the reference mutation rate 1/4,096 reproduced the epoch-2,433 transition and finished at 6.026 bits/byte high-order entropy. Zero mutation reached 0.658 at most without transition, while mutation 1/128 remained near random at 0.013. This supports a within-seed mutation Goldilocks zone but does not establish rates across seeds. Full methods, caveats, follow-ups, and literature are in `reports/pilot_experiments_2026-08-09.md`.

## 2026-08-12 — Phase 1 path tracing and substrate-independence gate

Nine token-audited BFF runs (multipliers 0.5, 2, and 16; three seeds each; 20,000 epochs) reconstructed explicit return→pool→reacquisition paths without altering byte trajectories. Every condition had cross-tape transfer and cyclic flow with zero byte/token conservation errors. The most blocked 1% of epochs at multipliers 0.5 and 2 were dominated by one full-budget interaction and one requested symbol, confirming the long-loop burst mechanism. Aggregate donor→receiver graphs were nearly complete, so the result demonstrates well-mixed matter circulation—not a sparse organism-like metabolism.

A fixed-tape prefix SKI substrate then completed nine 5,000-tick conservation runs through the unchanged flat world, scheduler, invariant checker, and logging modules. All expression snapshots remained valid, all residuals were zero, and duplicate short runs produced byte-identical six-table Parquet output with digest `c56352a9ce4b425692156556c9625be51f837c4e614a5e49da1c0411a958d5c8`. Atomic multi-slot writes were the only required conservation-boundary extension. SKI scarcity was unexpectedly non-monotonic: blocked-slot fractions averaged 76.82%, 89.29%, and 0.55% at multipliers 0.5, 2, and 16 because the intermediate pool supported longer expressions that then demanded scarce symbols.

The two previously open Phase 1 mechanical criteria—explicit matter paths and a second substrate through the same pipeline—are now closed. Persistent metabolic organization remains unobserved. Full results are in `reports/phase1_metabolic_trace_report.md`, `reports/phase1_ski_validation_report.md`, and `reports/phase1_final_report_2026-08-12.md`.


## 2026-08-16 — Phase 1 new-experiment batches 1 and 2 (auto-loop)

Preregistered batches targeting the final report's top open questions. Preregistration: `reports/phase1_newexperiments_preregistration.md` and `reports/phase1_batch2_preregistration.md`; interpretation in `reports/phase1_newexperiments_findings.md`; notebooks in `notebooks/`.

Three new logging-only probe capabilities, covered by tests: `--initial-soup`/`--epoch-offset` checkpoint continuation (`paper_probe`, `phase1_probe`) and `--flow-window` cumulative-matrix windowing (`metabolic_trace_probe`). All conserved runs kept zero per-symbol conservation residual.

Results:

1. **Long-window emergence (A; 4,096 tapes x 100,000 epochs, 15 conserved + 5 control):** control emergence 1/5 (A1 supported at criterion); m2 vs control 1/5 vs 1/5, Fisher p = 0.78 — no detectable conservation effect on emergence onset (A2 not supported). Blocked-write scarcity curve reproduced (rho = -0.945, p < 1e-4; A4). Exploratory: 5/20 runs crossed the entropy threshold in *every* arm, but only m16 seed 0 held takeover to the end — at 4,096 tapes emergence is usually a transient excursion, with or without conservation.
2. **Shadowing (A/D2):** m16 conserved runs byte-shadow the no-conservation control until the first scarcity-blocked write (three seeds share max-entropy values with controls to six decimals). Time-to-first-block scales with multiplier: medians ~155 (m0.5), ~577 (m2), ~4,749 epochs (m16); Spearman rho = 0.869, p < 1e-4. Conservation enters dynamics discontinuously.
3. **Windowed flow organization (C/D3; 9 trace runs, 2,000-epoch windows):** the well-mixed null is rejected — consecutive-window edge-weight correlation 0.19 vs permuted null 0.011, paired permutation p = 0.0025, robust to excluding self-flow. Mean persistence decreases monotonically with lag (lag-1 0.19, lag-2 0.063, lag-4 0.024), but the exact four-point Spearman test is not conventionally significant (rho = -1.0, p = 0.0833); treat drifting 2-4K-epoch roles as a descriptive pattern, not a confirmed trend. No scarcity modulation was detected (C2 rho = -0.16, exact p = 0.729).
4. **Natural-checkpoint continuation (B, partial):** the Phase 0 seed-0 epoch-2,433 checkpoint continues stably in the replicator-dominated regime for 8,000 epochs (entropy 5.6-6.1) as a diverse quasispecies (distinct tapes 37,503 -> 81,736). The preregistered single-hash dominance criterion was wrong for this substrate and is reported as failed honestly; entropy-based viability holds. Conserved continuations m0.5 complete, m2/m16 still running.
5. **Batch-2 D1 (16,384-tape control + m16 x 5 seeds) launched** to test whether takeover persistence improves with population scale.

Statistical tooling: numpy-only exact Fisher, Mann-Whitney U (validated against textbook values), Spearman with tie-corrected ranks, moving-block bootstrap, paired permutation tests (`experiments/analyze_phase1_newexperiments.py`), plus two executed Jupyter notebooks.
### Batch-1/2 addendum (final): continuation economics

Experiment B completed all arms. The m16 conserved continuation is byte-identical to the no-conservation control (zero blocked writes in 8,000 epochs); m2 sustains the replicator regime with blocked fraction 2.6e-7; m0.5 sustains with 5.8e-6 — all against a random-soup baseline of 7.6e-3. Preregistered B2 (disruption at intermediate scarcity) is decisively not supported: scarcity binds during emergence from random soups, not in established ecologies, because a replicator quasispecies' byte demand equals its own content histogram (a matter-closed economy). Batch-2 D1: 16,384-tape control remains marginal (1/5, D1a not supported); m16 seed 3 held takeover to the end while emergent controls decayed (exploratory persistence signal, E1b in batch 3 tests it at 32,768 tapes); D1c not supported (first-block epoch scale-invariant).
### Batch-3 E1 final (32,768-tape scale test)

Control emergence 3/5 within 100K epochs (E1a supported): emergence probability climbs with population (1/5 at 4,096; 1/5 at 16,384; 3/5 at 32,768). E1b: held-to-end among crossings m16 2/2 vs control 2/3, Fisher p=1.00 — the batch-2 hint that conservation stabilizes takeover weakens; at 32,768 control crossings hold too (3/5 structural takeovers with 22-82% diversity collapse). E1c: m16 first-block epoch scale-invariant (median 5,829 vs 5,296, MW-U p=0.22). Consolidated headline of the auto-loop campaign: population scale governs emergence probability and takeover persistence; conservation governs the resource economy (binding during emergence from random soups, neutrally closed once a replicator ecology is established). The two factors are separable.

## 2026-08-19 — Batches 4–7: mismatched, exclusion, and origin-filter economies (auto-loop campaign 2)

Four preregistered batches (`reports/phase1_batch4_preregistration.md` … `phase1_batch7_preregistration.md`; reports `phase1_batch4_report.md` … `phase1_batch7_report.md`) probing whether the conserved symbol pool can act as a *selective* force. 34 new headless runs (all conserved runs at zero conservation residual; 66 tests passing). New probe capabilities: uniform/exclusion pool modes (`--pool-mode uniform|excluded_top|excluded_list`), final-soup checkpoints, soup-vs-pool JSD metrics.

### Batch 4 — mismatched (uniform) pools

Continuing the natural epoch-2,433 checkpoint under uniform pools (U0.5/U2/U16): **neither adaptation nor disruption** — all arms viable (entropy 5.6–6.1 for 8,000 epochs); JSD(soup,pool) rose 0.090→0.13–0.14, the same drift magnitude as matched controls' endogenous drift (which itself falsifies perfect "neutral closure": matched-pool JSD(soup,pool) drifts 0→0.046–0.107). Exploratory: under U2, symbol-0 content fell 36% while viability held — weak directional content pressure absorbed as friction. Emergence at 32,768: uniform m16 2/3 vs matched 1/3 paired seeds (Fisher p=1.0).

### Batch 5 — exclusion pools on an established ecology

Zero pool supply of the ecology's six most-enriched symbols (null byte + `< [ , } ]`, 20.3% of content): viable for all 8,000 epochs; excluded-symbol share fell only 1.1% (top-6) / 17.8% (symbol 0 only, a slow ratchet). Blocked writes were 98.6% concentrated on excluded symbols (mechanism as designed) — **absorbed as friction, never as selection**. Tiny uniform pools (m0.05/m0.1) also viable (min entropy 5.13). Batch-4's emergence hint did not replicate (uniform 2/5 = matched 2/5). **Established ecologies are matter-economically homeostatic.**

### Batch 6 — exclusion at origin: suppression

Excluding the natural six during emergence (32,768 tapes, 100K epochs, m2): **0/5 emergence** vs 3/5 control (one-sided Fisher p=0.083); excluding only byte 0: **0/3**. Suppressed runs never crossed entropy 1.0 (Hmax 0.63–0.94).

### Batch 7 — specificity control

Excluding six arbitrary non-structural symbols (200–205) under the identical protocol produced **3/5 emergence**, the same observed count as control (Fisher p=1.0), with takeovers held to end in 2/5. The control's 1.6e8–8.8e8 blocked writes were lower than the natural-six arm's roughly 2.5e9–3.4e9, so it supports symbol specificity without perfectly matching friction. Mechanism (I3): suppressed runs never grow structural-symbol content (0.023→0.021); even *failed* natural runs grow it to ~0.11 and emergent ones to 0.15–0.20; symbol-0-only exclusion lets the five opcodes double (0.023→0.05) yet still blocks emergence — loops need the falsy byte.

### Consolidated conclusion

**The conserved matter economy is a candidate class-specific origin filter and an ecology-level homeostat.** Zero supply of the known replicator class's structural symbols was associated with 0/5 emergence versus 3/5 control (one-sided Fisher p=0.083), while the same constraint applied to an established ecology was absorbed as friction and non-structural exclusion allowed 3/5 emergence. The specificity control had a lower blocked-write volume, so the strongest defensible claim is that conservation's origin-filter mechanism is supported but still needs more seeds and a matched-friction control.

## 2026-08-23 — Phase 1 closeout and Phase 2 readiness scaffold

Phase 1 was frozen as `phase0-phase1-closeout-v1`: 3,199 raw artifact files (about 10.7 GB) are indexed by SHA-256 in `reports/phase0_phase1_artifact_index.csv`, with compact provenance in `reports/phase0_phase1_freeze_manifest.json`. Multi-gigabyte runs remain outside Git. Historical manifests point to the original base commit because Phase 1 had been developed in an uncommitted worktree; the closeout version captures the final source, configs, analysis, and reports.

The custom Spearman helper was corrected. Its incomplete-beta symmetry exponents were reversed, and tiny perfect correlations incorrectly received asymptotic p=0. Exact permutation is now used for n<=9. Corrected decisions: A3 p=0.273 (unsupported), A4 p=1.13e-7 (supported), C2 exact p=0.729 (unsupported), and D3 exact p=0.0833 (lag decay is descriptive, not significant).

Phase 2 semantics are preregistered in `reports/phase2_preregistration.md`. The scaffold now has a toroidal sparse lattice, local pairing, neutral dissolution, atomically pool-funded random placement, occupancy/conservation invariants, lifecycle logging, a Stage 2 report, neighbor-identity permutation analysis, and block beta diversity. Starvation dissolution is disabled until Stage 3 energy exists, and the anti-clogging gate now also requires liveness so extinction cannot pass.

The 500,000-tick benchmark projects 17.61 hours for 32x32 and 64.12 hours for 64x64 under aggregate logging; all measured cases had zero invariant failures. These are projections, not completed acceptance runs. Full details: `reports/phase1_closeout_and_phase2_handoff.md` and `reports/stage2_benchmark.md`. organism-sim transfer guidance is in `organism-sim/PHASE1_FINDINGS_TRANSFER.md`.
