# Phase 0–1 findings, contribution assessment, and Phase 2 readiness

## Executive decision

**Recommendation: conditional GO for Phase 2.**

Phase 0 and Phase 1 have produced enough useful evidence to stop broad Phase 1 exploration and begin a short Phase 2 design/scaffold step. The Phase 1 mechanical gate is complete: conservation is exact, the scarcity mechanism is active, explicit matter paths were traced, and a second substrate ran through the shared pipeline.

However, the project is **not ready to launch the long Phase 2 experiments yet**. Before that, it should:

1. freeze and version the Phase 0/1 code, reports, configurations, and essential manifests;
2. correct a statistical p-value helper and regenerate the affected statistical statements;
3. resolve several Phase 2 semantics, especially how empty cells are repopulated and how a run avoids passing the anti-clogging gate merely by dying out;
4. add the missing spatial analyses and benchmark a feasible 500,000-tick protocol.

The strongest candidate new scientific result is:

> A conserved symbol economy appears to act differently before and after replication emerges. It can filter the origin of a known replicator class when that class's structural symbols have zero free supply, while an already established replicator ecology absorbs the same shortage mostly as friction.

This is promising but should currently be described as **suggestive, specific to this simulator and protocol, and not yet a general theorem or fully powered result**.

---

## 1. Scope and evidence reviewed

This assessment uses the repository's Phase 0/1 code, preregistrations, generated reports, and statistical tables, especially:

- `FINDINGS.md`
- `convserved-prompt.md`
- `design-brief.md`
- `literature-review.md`
- `experiments/PHASE1_RESEARCH.md`
- `reports/stage0_batch_report.md`
- `reports/p0_7_time_to_emergence_replicates.md`
- `reports/pilot_experiments_2026-08-09.md`
- `reports/phase1_hypothesis_results.md`
- `reports/phase1_final_report_2026-08-12.md`
- `reports/phase1_metabolic_trace_report.md`
- `reports/phase1_ski_validation_report.md`
- `reports/phase1_newexperiments_findings.md`
- `reports/phase1_batch2_report.md`
- `reports/phase1_batch4_report.md` through `reports/phase1_batch7_report.md`
- `reports/phase1_campaign2_consolidated_report.md`
- the associated CSV result tables and analysis scripts.

The current software state was also checked directly:

- `uv run pytest`: **66 passed**;
- `uv run mypy --strict soup analysis`: **passed with no issues in 30 source files**;
- `git diff --check`: **passed**.

### Important novelty limitation

This is a **repository-based contribution assessment**, not a completed systematic literature review. The statements below mean “apparently new relative to the literature reviewed in this project.” Before publication, the novelty claims should be checked with a broader and current search, including citation chaining and searches for conserved instruction-tape chemistries, resource-limited digital evolution, and origin-versus-establishment interventions.

---

## 2. What Phase 0 established

### 2.1 Simulator and data foundation

Phase 0 built a deterministic BFF program soup with:

- fixed-length self-modifying byte tapes;
- paper-style shuffled, disjoint ordered pairs;
- configurable BFF semantics;
- background mutation;
- one seeded random-number stream;
- raw Parquet logging, manifests, invariant logs, and offline reports;
- exact-copy inference outside the simulator;
- diversity and high-order-entropy analysis;
- a bounded, accelerated paper-scale probe.

This is important engineering work because later claims depend on reproducible trajectories and auditable raw data. It is not, by itself, a new scientific result.

### 2.2 The initial 256-tape failure was a protocol/scale diagnosis

The first acceptance campaign used 20 seeds, 256 tapes, and 20,000 epochs. It found exact copying in only **1/20 runs (5%)**, with maximum abundance 2, and essentially no diversity collapse. The original threshold was at least 30% emergence.

That failure should not be interpreted as a failed reproduction of the cited BFF paper because the computational opportunities were radically different:

- local run: roughly 5.12 million interactions per run;
- paper-scale run: roughly 1.05 billion interactions per run.

The pairing and mutation protocols were also corrected after source-level comparison. This was a useful negative result: it showed that “same instruction set” is not enough for a quantitative comparison when population size, pairing, mutation, and interaction count differ.

### 2.3 Paper-scale emergence was independently reproduced

The accelerated probe matched the released implementation's initialization and first-epoch behavior. At 131,072 tapes and 16,000 epochs:

- seed 0 crossed the high-order-entropy threshold at epoch **2,433** and finished at **6.026 bits/byte**;
- seed 2 crossed at the first sampled callback near epoch **11,777** and finished at **5.649 bits/byte**;
- seeds 1 and 3 did not cross;
- the available paper-scale result is therefore **2/4 transitions**, descriptive rather than a precise rate estimate.

For seed 0, functional scoring strengthened the entropy result: 106 of the 1,024 most abundant tapes passed the functional threshold at the first transition, and 1,023 of 1,024 passed by the end.

This is primarily an **independent reproduction and validation result**, not a new phenomenon. Its value is that Phase 1 starts from a verified baseline rather than an unverified imitation.

### 2.4 Mutation showed a within-seed Goldilocks pattern

For seed 0 at paper scale:

| Mutation condition | Maximum entropy | Final entropy | Transition |
|---|---:|---:|---|
| 0 | 0.658 | 0.482 | No |
| 1/4,096 | 6.055 | 6.026 | Yes, epoch 2,433 |
| 1/128 | 0.0127 | 0.0105 | No |

This is strong **within-seed** evidence that too much mutation destroys heritable structure and that the reference mutation opened this seed's emergence path. It is not evidence for a universal optimal mutation rate because only one seed received the full three-rate intervention.

### 2.5 Population size is a major emergence variable

Later controls reported:

| Population | Horizon | Control transitions |
|---:|---:|---:|
| 4,096 | 100,000 epochs | 1/5 |
| 16,384 | 50,000 epochs | 1/5 |
| 32,768 | 100,000 epochs | 3/5 |
| 131,072 | 16,000 epochs | 2/4 |

The 4,096-versus-32,768 comparison uses the same 100,000-epoch horizon and supports a scale effect. The full table is not a clean dose-response experiment because horizons differ and each cell has few seeds. “Population scale strongly influences emergence” is justified; a precise emergence curve is not.

---

## 3. What Phase 1 added

### 3.1 Exact symbol conservation

Phase 1 introduced a global `SymbolPool`. Every changed write must:

1. withdraw the requested new byte value from the pool;
2. return the overwritten byte value;
3. block atomically if the requested value is unavailable.

This applies to BFF execution and mutation. The invariant is a 256-component equality:

`tape histogram + pool histogram = initial conserved totals`.

Evidence includes:

- a 100,000-epoch BFF validation with residual 0 at every independent check;
- all replicated BFF mechanism campaigns with maximum residual 0;
- all token-audited BFF runs with byte and token conservation;
- all SKI runs with residual 0;
- all later exclusion and mismatch interventions with residual 0.

This establishes that the resource effects are not caused by matter leakage.

### 3.2 Scarcity is selective and tunable

At 256 tapes, five multipliers and five seeds per condition produced:

| Pool multiplier | Mean blocked fraction [95% bootstrap CI] | Mean peak high-order entropy | Transitions |
|---:|---:|---:|---:|
| 0.1 | 0.3030 [0.2556, 0.3630] | 0.116 | 0/5 |
| 0.5 | 0.1486 [0.0945, 0.1939] | 0.362 | 0/5 |
| 2 | 0.0308 [0.0178, 0.0475] | 0.614 | 0/5 |
| 16 | 0.0014 [0.0004, 0.0024] | 0.476 | 0/5 |
| 256 | 0 | 0.476 | 0/5 |

The pool's total size never falls during ordinary replacement; only its composition changes. Therefore the relevant mechanism is **specific-symbol depletion**, not total-pool exhaustion.

The scarcity curve was reproduced in the longer 4,096-tape campaign: multiplier versus blocked fraction had Spearman rho **-0.945**. An independent exact label-permutation check gives two-sided **p ≈ 2.64 × 10^-6**.

### 3.3 Scarcity has two temporal regimes

Tight pools produce broad, nearly continuous blocking. Moderate or loose pools are usually permissive but occasionally produce sharp bursts focused on one symbol.

Examples from the five-seed mechanism sweep:

- multiplier 0.1: about 178 effective blocked symbols and almost no zero-block epochs;
- multiplier 2: about 17 effective blocked symbols and 67.4% zero-block epochs;
- multiplier 16: 96.2% zero-block epochs, but rare large spikes.

Token-audited runs showed that the most blocked 1% of epochs at multipliers 0.5 and 2 were dominated by one full-budget interaction and almost one requested symbol. Thus the bursts are usually caused by a long loop repeatedly asking for a depleted byte, not by a synchronized global shortage.

No narrow periodic oscillator was established.

### 3.4 Matter was explicitly traced between tapes

Nine token-audited runs reconstructed valid return-to-pool and later reacquisition paths without altering byte trajectories.

Every condition showed:

- returned tokens later withdrawn again;
- movement from one persistent tape ID to another;
- reciprocal edges and cycles;
- zero token-placement and conservation failures.

The whole-run donor-to-receiver graphs were nearly complete. This proves **matter circulation**, but not organism-like metabolism. Complete mixing can generate abundant cycles without a bounded, self-maintaining metabolic organization.

### 3.5 Windowing revealed temporary roles hidden by aggregation

The same flow was reanalyzed in 2,000-epoch windows:

- consecutive-window edge-weight correlation: **0.193**;
- permuted-label null: **0.011**;
- mean gap: **+0.182**;
- paired permutation **p = 0.0025**, robust when self-flow was removed.

This supports persistent producer/consumer-like roles over adjacent windows. Persistence then decayed with lag:

- lag 1: 0.193;
- lag 2: 0.063;
- lag 3: 0.030;
- lag 4: 0.024.

The original report gives Spearman rho -1 and p reported as 0. An exact rank permutation over the four lag points gives **p = 0.0833**, not p = 0. The monotonic decay is a real descriptive pattern, but its significance was overstated. The safest conclusion is: **roles drift rather than remaining fixed, and stronger replication is required before calling them metabolic organizations**.

### 3.6 Conservation begins to matter at the first blocked write

Loose-pool conserved runs can exactly shadow their no-conservation controls until scarcity first blocks a write. Time to first block rose with multiplier; the reported Spearman rho was **0.869** across 15 runs.

This is mechanistically useful because it separates two periods:

1. before the first block, the conserved and unconserved worlds can be byte-identical;
2. after the first block, the resource economy changes the trajectory.

This supports analyzing conservation as an intervention event, not only as an average blocked-write rate.

### 3.7 Established replicator ecologies are unusually resource-closed

A naturally emerged seed-0 checkpoint was continued for 8,000 epochs.

- no-conservation control: entropy remained in the replicator-dominated regime;
- multiplier 16: byte-identical to control, with zero blocked writes;
- multiplier 2: viable, blocked fraction about **2.6 × 10^-7**;
- multiplier 0.5: viable, blocked fraction about **5.8 × 10^-6**;
- random-soup multiplier-2 baseline: first-window blocked fraction about **7.6 × 10^-3**.

The ecology was not one dominant exact tape; it was a diverse quasispecies. Its byte demand was close to its own composition, so recycling supplied what it already used. This is evidence for **matter-economic closure at the ecology level**.

Uniform pools, tiny pools, and zero initial free supply of the established ecology's enriched symbols did not destroy it over the 8,000-epoch continuation window. Even the strongest exclusion was mostly absorbed as blocked-write friction.

This does not prove indefinite stability: all continuations used one natural checkpoint and a bounded horizon.

### 3.8 Conservation may filter replication at origin

The most important campaign compared random-soup emergence under different excluded-symbol pools at 32,768 tapes and 100,000 epochs.

#### Natural structural-symbol exclusion

The pool had zero initial free supply of six symbols enriched in the known replicator class: null byte plus `<`, `[`, `,`, `}`, and `]`.

- natural-six exclusion: **0/5** transitions;
- no-conservation control: **3/5** transitions;
- one-sided Fisher exact **p = 0.0833**;
- all excluded runs stayed below entropy 1.0;
- the combined structural-symbol share stayed near or below its random-soup baseline instead of growing to the 11–20% observed in comparison runs.

Null-byte-only exclusion also produced 0/3 transitions, but that cell is too small for a strong standalone claim.

#### Non-structural specificity control

Excluding six arbitrary non-opcode bytes produced:

- **3/5** transitions;
- 2/5 held to the end;
- the same transition count as the no-conservation control.

This makes a purely generic “any exclusion suppresses emergence” explanation less plausible.

#### Why this remains suggestive rather than decisive

Three cautions matter:

1. The natural-six contrast does not reach a conventional 0.05 significance threshold: p = 0.0833.
2. “3/5 versus 3/5, p = 1” does not prove equivalence. It only says this small experiment did not detect a difference.
3. The direct specificity control had substantially fewer blocked writes (about 1.6 × 10^8 to 8.8 × 10^8) than the natural-six excluded runs (reported around 2.5 × 10^9 to 3.4 × 10^9). Therefore symbol identity and total friction were not perfectly matched.

The strongest defensible wording is:

> In this protocol, zero free supply of the known class's structural symbols was associated with suppression of that class's origin, while exclusion of arbitrary non-structural symbols still allowed emergence. The combined trajectory and symbol-content evidence supports a class-specific origin-filter hypothesis, but more matched-friction replicates are needed for a strong general claim.

### 3.9 Intermediate scarcity did not show a reliable organization optimum

Multiplier 2 had the largest mean peak entropy in the initial five-seed sweep, but its matched-seed advantage had a 95% bootstrap interval crossing zero. In the longer campaign, multiplier versus maximum entropy had rho -0.302.

The earlier generated report incorrectly gave p = 1.000. The corrected analyzer gives the asymptotic p = **0.273**, while an independent exact label-permutation check gives **p ≈ 0.284**. Both are non-significant, so the decision remains **unresolved/not supported**, not established.

### 3.10 The SKI test validated portability, not a new SKI chemistry

Nine 5,000-tick SKI runs used the same world, scheduler, invariants, logging tables, and report pipeline. All expression snapshots remained valid, all conservation residuals were zero, and duplicate runs produced byte-identical Parquet output.

The unexpected result was non-monotonic scarcity:

- multiplier 0.5: 76.82% blocked slots;
- multiplier 2: 89.29%;
- multiplier 16: 0.55%.

The intermediate pool supported longer expressions, which then requested more scarce combinator/application symbols. This is a useful substrate-dependence warning. The minimal SKI implementation is explicitly not a reproduction of Combinatory Chemistry or chemSKI, so it should be treated as an engineering portability fixture.

---

## 4. What is actually new work?

“New work” has several meanings. Separating them prevents overclaiming.

### 4.1 Reproduction work: valuable but not scientifically novel by itself

These are strong project contributions, but mostly reproduce or validate known behavior:

- implementing the BFF substrate;
- matching released BFF protocol details;
- reproducing paper-scale entropy transitions and functional replication;
- implementing standard diversity and exact-conservation checks;
- reproducing deterministic runs and byte-identical outputs.

Their contribution is reliability and a trusted baseline.

### 4.2 New engineering and experimental methodology

Relative to the reviewed literature, the following combination appears new or at least uncommon:

1. **Every self-modifying BFF write mediated by an exactly conserved, symbol-specific pool**, including background mutation.
2. **Trajectory-preserving token audits** that reconstruct one valid token history while preserving the byte-level dynamics.
3. **Natural-checkpoint interventions** that compare random-soup origin with an already emerged ecology rather than seeding a designed replicator.
4. **Composition-controlled pool interventions**, including histogram-matched, uniform, and zero-supply exclusion pools.
5. **Windowed donor-to-receiver flow tests against a shuffled-label null**.
6. **The same conservation boundary applied to both BFF single-slot writes and atomic SKI multi-slot rewrites**.

Even if a headline biological interpretation weakens, these methods remain reusable contributions.

### 4.3 Candidate new empirical findings

#### High confidence within this simulator

- Symbol scarcity is selective, tunable, and nonuniform rather than simple loss of total matter.
- Tight scarcity is broad and continuous; loose scarcity is rare, bursty, and often generated by one long loop requesting one symbol.
- Conservation can be causally localized to the first blocked write because trajectories shadow controls before that event.
- Established replicator ecologies use the conserved pool far more efficiently than random soups.
- Whole-run aggregation hides short-lived flow roles that become detectable in time windows.
- Scarcity response depends on substrate; SKI need not preserve the BFF multiplier ordering.

#### Moderate/suggestive confidence

- Population size influences both the probability and persistence of BFF emergence.
- A known replicator ecology behaves as a matter-economically closed quasispecies over the tested continuation window.
- Structural-symbol availability acts as an origin filter for the known BFF replicator class.

#### Not established

- a universal mutation optimum;
- a universal intermediate-scarcity optimum;
- persistent organism-like metabolism;
- general equivalence between non-structural exclusion and no conservation;
- a universal law that conservation acts only at origin;
- open-ended evolution, increasing complexity, trophic structure, or multicellularity.

### 4.4 The strongest paper-sized contribution

A defensible paper framing would be:

> **Conserved instruction matter separates origin constraints from ecological maintenance in an emergent program soup.**

The paper would combine:

1. exact resource accounting;
2. the scarcity-regime curve;
3. first-block shadowing;
4. random-soup versus natural-checkpoint interventions;
5. structural versus non-structural exclusion;
6. windowed flow persistence;
7. negative results showing that established ecologies resist even severe pool mismatch.

Before using this as a final title or abstract claim, replicate the origin-filter contrast with better friction matching and more seeds.

---

## 5. Statistical audit notes

### 5.1 Results that are well supported

- Conservation residuals are exactly zero across all reported conserved campaigns.
- The blocked-rate response to multiplier is large and consistent.
- Windowed flow correlations exceed the permutation null with p = 0.0025.
- The continuation differences in blocked rate are orders of magnitude, not marginal effects.
- Functional scoring confirms that the Phase 0 seed-0 entropy transition corresponds to replicator-rich behavior.

### 5.2 Small-sample and interpretation limits

- Most emergence cells have only 3–5 seeds.
- Several continuation experiments use only one natural checkpoint.
- Entropy is a structural transition metric, not a direct functional replication assay.
- “Failed to reject” is not evidence of equivalence.
- Different population cells sometimes use different horizons.
- The excluded-symbol specificity comparison did not perfectly match total blocked-write load.

### 5.3 Statistical implementation defect found and corrected

The custom regularized incomplete-beta symmetry branch in `experiments/analyze_phase1_newexperiments.py` had its exponents reversed, causing some moderate-correlation Spearman p-values to approach 1 incorrectly. The implementation now uses the corrected beta expression for larger samples and exact label permutation for samples of at most nine observations. Regression tests cover the beta identity, the n=4 perfect-correlation case, and the Phase 1 moderate-correlation case.

Corrected and independently checked values are:

| Test | Earlier report | Corrected result | Decision effect |
|---|---:|---:|---|
| A3 multiplier vs maximum entropy | rho -0.302, p 1.000 | asymptotic p = 0.273; exact grouped-label p ≈ 0.284 | None; still unsupported |
| A4 multiplier vs blocked fraction | rho -0.945, p < 0.0001 | asymptotic p = 1.13×10⁻⁷; exact grouped-label p ≈ 2.64×10⁻⁶ | None; still strongly supported |
| C2 multiplier vs role-persistence gap | rho -0.158, p 1.000 | exact p ≈ 0.729 | None; still unsupported |
| D3 lag vs mean role persistence, n=4 | rho -1, p reported 0 | exact p = 0.0833 | Yes; monotonic decay remains descriptive, not conventionally significant |

The machine-generated reports and narrative findings were regenerated or corrected with these values.

---

## 6. Gate review

### 6.1 Phase 0 gate

| Original criterion | Assessment |
|---|---|
| At least 30% of 20 runs emerge within 20,000 epochs | **Not met literally.** The original 256-tape campaign had 1/20; the corrected paper-scale evidence has only 4 seeds, with 2 transitions. |
| Clear diversity collapse during takeover | **Supported in corrected larger runs, not in the original 20-run small campaign.** Later 32,768-tape controls showed 22–82% collapse in structural takeovers. |
| Logs load and report without repair | **Pass.** |
| Same seed/config gives byte-identical Parquet | **Pass.** |

**Interpretation:** Phase 0's original statistical gate was never passed exactly as written. It was scientifically replaced after discovering that the 256-tape protocol was not comparable to the paper. The revised evidence is adequate to show that the substrate supports spontaneous functional replication, but it is not a 20-seed paper-scale rate estimate.

### 6.2 Phase 1 gate

| Original criterion | Assessment |
|---|---|
| Exact symbol conservation for 100,000 ticks | **Pass.** |
| Population growth saturates with blocking | **Not measurable as written** because tape count is fixed; replaced by content-turnover/scarcity saturation, which passed. |
| At least five pool multipliers | **Pass.** |
| Acquire/decompose pattern | **Pass mechanically** through explicit return, reacquisition, cross-tape flow, and cycles; no claim of organized metabolism. |
| SKI through the same world/scheduler/logging pipeline | **Pass.** |

**Interpretation:** the Phase 1 engineering/mechanism gate is complete under the documented semantic correction. Its stronger ecological aspiration—persistent metabolic organization—remains unresolved.

---

## 7. Phase 2 readiness assessment

### 7.1 What is ready

- The substrate supports spontaneous replication at appropriate scales.
- The symbol pool is exact and robust under multiple interventions.
- `is_inert` exists for BFF and SKI.
- spatial coordinates, free-cell counts, dissolutions, and lineage fields already exist in logging schemas as placeholders;
- the configuration tree already contains lattice, interaction-radius, initial-fill, reseed, and dissolution fields;
- current tests and strict typing pass;
- the original pre-Phase-2 instruction-step benchmark exceeded its required threshold.

### 7.2 What is not implemented

The current `Simulation` explicitly rejects stages other than 0 and 1. The current world and scheduler remain flat and nonspatial. Missing Phase 2 components include:

- occupancy lattice and free-cell ledger;
- local-neighborhood pairing;
- dissolution timers and matter return;
- placement/reseeding;
- Stage 2 invariants;
- spatial autocorrelation analysis;
- block beta-diversity analysis;
- Phase 2 report generation;
- Phase 2 configuration and visualization behavior.

This is expected: readiness to start Phase 2 does not mean Phase 2 already exists.

### 7.3 Must-resolve design questions

#### A. Empty-cell reproduction and liveness

The written specification only fills empty cells through optional random reseeding, whose default is zero. Existing BFF replication overwrites an occupied interaction partner; it does not naturally place an offspring into an empty cell.

Without a neighbor-to-empty placement path, dissolution makes occupancy monotonically decrease. A run could “avoid clogging” simply by becoming empty. Before implementation, choose one explicit model:

1. allow a successful copier to place offspring into a neighboring empty cell, with conserved bytes and lineage attribution; or
2. retain random reseeding only, but admit that Stage 2 measures spatial turnover rather than biological birth and add a nontrivial occupancy/liveness criterion.

#### B. Anti-clogging must not reward extinction

The current criterion only forbids free-cell count remaining zero. It also needs lower liveness bounds, such as:

- occupied fraction remains above a preregistered minimum;
- interactions and successful writes remain nonzero in late windows;
- both dissolutions and placements occur;
- the pool continues cycling rather than all matter ending free.

#### C. Starvation dissolution must be disabled before energy exists

Stage 2 has no energy ledger, so every tape currently has zero energy. If `starved_ticks` is applied literally, all tapes will dissolve. Starvation-based dissolution should activate only when Stage 3 energy is enabled.

#### D. Inertness semantics need an activity timer

BFF currently calls a tape inert when it contains no write opcode. That is a structural proxy, not a history of whether it has recently changed or contributed as a template. Define exactly when the inert timer increments and resets, and test that useful passive templates are not accidentally removed by an interpretation change.

#### E. Initial fill and conserved totals

For a partially occupied lattice, specify whether the free pool is generated from:

- occupied initial tapes only;
- the matter required for a fully occupied lattice; or
- a separately specified environmental composition.

The choice changes both conservation totals and vacancy-filling capacity.

#### F. Feasible experiment scale

A 500,000-tick lattice run can require roughly a billion interactions even at 4,096 cells. The current paper-scale Numba probe is specialized to a dense flat soup and cannot simply be reused for dynamic occupancy and local neighborhoods.

Benchmark the spatial kernel before committing to the final gate matrix. A staged protocol should use:

1. tiny invariant and determinism tests;
2. short 32×32 or 64×64 spatial pilots;
3. a bounded radius sweep;
4. only then the 500,000-tick acceptance run.

#### G. Baseline comparison

Compare Stage 2 with a matched nonspatial or large-radius control using the same population capacity, horizon, mutation, and logging cadence. Otherwise a diversity difference can be caused by scale or observation time instead of locality.

### 7.4 Reproducibility blocker

At review time, most Phase 1 scripts, reports, and run summaries are untracked, while many core files are modified relative to `main`. The experiment data directory is also very large.

Before Phase 2:

- commit or tag the Phase 0/1 source, configs, preregistrations, analysis scripts, final reports, and compact summary tables;
- keep multi-gigabyte raw runs outside Git if necessary, but preserve manifests, checksums, and a storage-location index;
- record the exact commit used for every retained result;
- remove or archive stale PID files and document incomplete runs, if any.

Without this freeze, future Phase 2 changes can make it difficult to reconstruct which code generated Phase 1's results.

### 7.5 Readiness verdict by category

| Category | Status | Reason |
|---|---|---|
| Scientific reason to proceed | **Ready** | Phase 1 has answered its mechanism questions well enough; further broad sweeps have diminishing value. |
| Phase 0 substrate baseline | **Conditionally ready** | Functional emergence reproduced, but original 20-run gate was not literally repeated at paper scale. |
| Phase 1 mechanical gate | **Ready** | Exact conservation, tracing, and SKI portability passed. |
| Current code quality | **Ready** | 66 tests and strict typing pass. |
| Statistical freeze | **Ready after final validation** | The Spearman helper and affected wording have been corrected and regression-tested. |
| Provenance/versioning | **Not ready** | Phase 1 work is largely untracked/unfrozen. |
| Phase 2 semantics | **Not ready** | Placement, liveness, starvation gating, and initial matter need explicit decisions. |
| Long-run feasibility | **Not ready** | Spatial 500,000-tick performance has not been benchmarked. |

#### Final answer

**Move to Phase 2 as a short design-and-scaffold phase, after freezing Phase 0/1 and resolving the listed semantics. Do not start the full Phase 2 acceptance campaign yet.**

---

## 8. Recommended immediate plan

1. **Freeze Phase 0/1.** Commit compact evidence and write checksums/locations for raw runs.
2. **Preserve the statistical correction.** Keep the new Spearman regression tests and the descriptive D3 lag-decay wording in the frozen Phase 1 version.
3. **Write a Phase 2 preregistration.** Preserve all five original criteria, add liveness/anti-extinction criteria, matched controls, null models, seed counts, effect sizes, and stopping rules.
4. **Resolve placement.** Decide whether replication can occupy empty neighboring cells.
5. **Design the lattice state and invariants.** Occupancy, IDs, ages, inert timers, pool totals, and lineage must remain atomic.
6. **Implement a tiny deterministic scaffold.** Test locality, dissolution return, blocked placement, IDs, and byte-identical replay.
7. **Implement spatial analysis before long runs.** Moran-like content autocorrelation or an explicitly defined hash-similarity statistic, block beta diversity, and well-mixed permutation nulls.
8. **Benchmark before scaling.** Choose the largest feasible lattice and horizon without silently weakening the acceptance test.
9. **Run preregistered Phase 2 pilots.** Only after the small invariant and performance gates pass.

---

## 9. Bottom line

Phase 0 proved that the BFF substrate can spontaneously produce functional replicator ecologies when the protocol provides enough opportunities. Phase 1 proved that exact symbol conservation creates a real, symbol-specific resource economy rather than a uniform slowdown.

The new scientific direction is the separation between **origin** and **maintenance**:

- random soups need to assemble scarce structural symbols and are vulnerable to their absence;
- established replicator quasispecies recycle a composition close to their own demand and are much harder to disrupt.

That is meaningful new work relative to the project's reviewed literature, but its strongest “class-specific origin filter” wording still needs more power and better friction-matched controls. The project has enough evidence to proceed, provided Phase 2 begins with a careful design freeze rather than immediately launching long spatial experiments.
