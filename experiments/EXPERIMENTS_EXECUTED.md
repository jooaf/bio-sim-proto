# Executed experiments registry

This append-only registry summarizes experiments that reached a decision. It is
not a replacement for preregistrations, manifests, raw artifacts, or full
reports. Pending work belongs in [`EXPERIMENTAL_IDEAS.md`](EXPERIMENTAL_IDEAS.md).

For every new entry include: frozen hypothesis, test and primary endpoint,
result with uncertainty/test statistic, decision, why that decision follows,
limitations, artifact links, and follow-up idea IDs. Negative and invalidated
results stay in the registry. A consolidated index of failed and mixed gates is
maintained at [`reports/failed_experiments_registry.md`](../reports/failed_experiments_registry.md).

---

## Stage 0 — Bare soup and reference replication

### S0-E001 — Initial tractable 256-tape acceptance

- **Hypothesis:** Bare BFF soup would show replication in at least 30% of 20
  seeds and clear exact-hash diversity collapse under the initial protocol.
- **Test:** 20 seeds, 20,000 ticks, 256 tapes, with-replacement interactions.
- **Result:** Replication appeared in 1/20 runs (5%); the sole inferred replicator
  reached abundance 2. Final distinct hashes averaged 255.75 and maximum
  transient collapse was 7.0%. Deterministic replay and unattended reporting
  passed with zero invariant violations.
- **Decision:** **FAIL as an emergence test; mechanics PASS.**
- **Why:** Both biological thresholds failed, and the protocol supplied orders
  of magnitude fewer interactions than the reference paper.
- **Follow-up:** Protocol correction and paper-scale reproduction, S0-E002.
- **Evidence:** `FINDINGS.md` (2026-08-06), `reports/stage0_batch_report.md`.

### S0-E002 — Corrected paper-scale replication reproduction

- **Hypothesis:** Matching released BFF semantics, mutation, shuffled disjoint
  pairing, population, and horizon reproduces the published transition.
- **Test:** Seed 0; 131,072 tapes; 16,000 epochs; mutation `1/4096`; bounded-log
  Numba probe validated byte-for-byte at short horizon against the reference.
- **Result:** High-order entropy first crossed 1 bit/byte at epoch 2,433 and
  finished at 6.025684. At transition, 106/1,024 abundant sampled tapes passed
  the functional-copy threshold; 1,023/1,024 passed at completion. Maximum
  matched-epoch discrepancy from the independent upstream run was
  `1.234e-6` bits/byte.
- **Decision:** **PASS. Stage 0 emergence concern closed for the paper protocol.**
- **Why:** Transition timing, trajectory, and functional-copy evidence agree
  with the reference at the correct scale.
- **Follow-up:** Stage 1 conserved symbol economy; no mutation retuning.
- **Evidence:** `FINDINGS.md` (2026-08-07), `reports/paper_probe_seed0.csv`.

## Stage 1 — Conserved symbol economy

### S1-E001 — Exact symbol conservation and scarcity mechanics

- **Hypothesis:** A global symbol pool can mediate every tape write while exactly
  conserving all 256 byte totals and producing measurable scarcity.
- **Test:** 256 tapes for 20,000 ticks at pool multiplier 2, plus multiplier
  pilots at 0.1, 0.5, 2, and 16.
- **Result:** All 200 reconstructed snapshots had zero per-symbol residual. The
  primary run recorded 7,453,461 accepted and 236,511 blocked writes. Pilot
  blocked-write rates were 30.79%, 14.95%, 3.05%, and 0.12% as multiplier rose.
- **Decision:** **PASS.**
- **Why:** Conservation was exact and scarcity changed dynamics through selective
  symbol depletion rather than total-pool exhaustion.
- **Follow-up:** Explicit matter paths and substrate-independence, S1-E002.
- **Evidence:** `FINDINGS.md` (2026-08-08 through 2026-08-09).

### S1-E002 — Matter-path tracing and SKI substrate validation

- **Hypothesis:** Conserved symbols circulate across tapes through explicit
  return/reacquisition paths, and the conservation boundary generalizes beyond
  BFF.
- **Test:** Nine token-audited BFF runs and nine fixed-tape prefix-SKI runs.
- **Result:** Every BFF arm showed cross-tape transfer and cycles with zero
  token/byte residual. All SKI snapshots remained valid; duplicate runs were
  byte-identical with digest
  `c56352a9ce4b425692156556c9625be51f837c4e614a5e49da1c0411a958d5c8`.
- **Decision:** **PASS mechanically; no persistent metabolism claim.**
- **Why:** Paths and a second substrate were demonstrated, but aggregate flow was
  nearly complete/well mixed rather than sparse and organism-like.
- **Follow-up:** Windowed organization and emergence/economy interventions,
  S1-E003 and S1-E004.
- **Evidence:** `reports/phase1_metabolic_trace_report.md`,
  `reports/phase1_ski_validation_report.md`.

### S1-E003 — Long-window emergence and temporal flow organization

- **Hypotheses:** Conservation changes emergence onset; multiplier predicts
  scarcity; adjacent flow windows retain organization above a permutation null.
- **Test:** 20 long 4,096-tape runs plus nine 2,000-epoch-window trace runs.
- **Result:** Emergence was 1/5 for multiplier 2 and 1/5 for controls (Fisher
  `p=0.78`), so no onset effect was detected. Multiplier versus blocked rate was
  strongly monotone (`rho=-0.945`, corrected `p=1.13e-7`). Adjacent-window edge
  persistence was 0.19 versus null 0.011 (paired permutation `p=0.0025`), but
  four-lag decay was only descriptive (`p=0.0833`) and scarcity modulation was
  unsupported (`p=0.729`).
- **Decision:** **Mixed:** onset hypothesis FAIL; scarcity and adjacent-window
  persistence PASS; long-lag/scarcity modulation unsupported.
- **Why:** Frozen tests separate clear resource-economy effects from weaker
  temporal-organization claims.
- **Follow-up:** Established-ecology and origin filters, S1-E004.
- **Evidence:** `reports/phase1_newexperiments_findings.md`, `FINDINGS.md`.

### S1-E004 — Established ecology versus origin filtering

- **Hypothesis:** Conserved resource composition can filter replicator origin
  while an established replicator ecology buffers the same shortage.
- **Test:** Checkpoint continuations; uniform and tiny pools; natural structural-
  symbol exclusion at maintenance and origin; arbitrary-symbol specificity
  control.
- **Result:** Established ecologies remained viable under all tested shortages;
  blocked writes concentrated on excluded symbols but acted as friction. At
  origin, natural-six exclusion yielded 0/5 emergence versus 3/5 control
  (one-sided Fisher `p=0.083`); byte-0-only exclusion yielded 0/3. Arbitrary
  symbols 200–205 yielded 3/5, equal to control (`p=1.0`), but with lower total
  blocked-write volume.
- **Decision:** **Suggestive origin-filter support; homeostasis supported; strong
  class-specific claim NOT established.**
- **Why:** Direction and specificity are consistent with an origin filter, but
  seed count and unmatched friction leave an alternative explanation.
- **Follow-up:** S1-I001 matched-friction confirmation and S1-I002 cross-model
  same-checkpoint intervention.
- **Evidence:** `reports/phase1_campaign2_consolidated_report.md`, `FINDINGS.md`.

### S1-E005 — Phase 1 closeout

- **Hypothesis:** Phase 1 has enough mechanical and scientific evidence to stop
  conservation-only batches and proceed to spatial mechanics.
- **Test:** Reproducibility freeze, artifact checksums, statistical audit, and
  explicit claim review.
- **Result:** 3,199 raw files (~10.7 GB) indexed; retained conserved runs had zero
  symbol residual; corrected small-sample statistics were propagated.
- **Decision:** **CLOSE Stage 1; proceed to Stage 2.**
- **Why:** Conservation, circulation, scarcity, and bounded temporal roles were
  established, while persistent organism-like metabolism remained unsupported.
- **Follow-up:** Stage 2 spatial locality; S1-I001 only if a stronger origin-filter
  claim becomes necessary.
- **Evidence:** `reports/phase1_closeout_and_phase2_handoff.md`.

## Stage 2 — Spatial locality

### S2-E001 — Spatial liveness operating point

- **Hypothesis:** Dissolution/reseed rates can maintain a live, partially empty,
  exactly conserved 32×32 lattice.
- **Test:** 27-run 8×8 grid followed by three 32×32, 5,000-tick confirmations.
- **Result:** Rates `1e-5/1e-5` were selected. Confirmation passed 3/3; median
  late occupancy 0.767, minimum population 780/1,024, zero invariant failures,
  and exact conservation.
- **Decision:** **PASS and freeze operating point.**
- **Why:** All mechanical liveness and conservation criteria passed at scale.
- **Follow-up:** Locality campaign, S2-E002.
- **Evidence:** `reports/phase2_acceptance_readiness_decision.md`.

### S2-E002 — Radius effect on spatial sequence similarity

- **Hypothesis:** Local interaction creates greater positional byte similarity
  than wide interaction.
- **Test:** Radii 1, 2, 4, and 8; five seeds each; 999 label permutations.
- **Result:** Byte-identity excess was positive in 20/20 runs; radius 1 exceeded
  radius 8 in 5/5 pairs, mean difference `+0.004050`, exact one-sided
  `p=0.03125`. Radius 2 was strongest, so the response was nonmonotonic. The
  categorical opcode-signature contrast was unsupported (`p=0.125`).
- **Decision:** **PASS for a narrow radius effect; categorical Phase 2 gate not
  passed.**
- **Why:** The continuous positional endpoint detected reproducible locality,
  while the frozen categorical endpoint did not.
- **Follow-up:** Graded opcode metric/temporal replication, S2-E004.
- **Evidence:** `reports/phase2_radius_pilot_report.md`,
  `reports/phase2_acceptance_readiness_decision.md`.

### S2-E003 — Parasite positive-control viability

- **Hypothesis:** The selected BFF copier invades under the large-radius treatment
  strongly enough to support a containment comparison.
- **Test:** Strict mutation-free mechanics, five mutating content-family runs,
  and five separately preregistered neutral-ancestry diagnostics.
- **Result:** Strict mechanics grew exact copies from 16 to maximum 32. Under
  treatment, content family increased in 3/5 but reached 50% in 1/5; ancestry
  increased in 1/5 and reached 50% in 0/5 (maximum 0.099).
- **Decision:** **NO-GO; candidate rejected and integrated Phase 2 acceptance
  blocked.**
- **Why:** A containment effect is unidentified when the large-radius positive
  control does not invade.
- **Follow-up:** S2-I001 protocol decision. Do not tune this candidate.
- **Evidence:** `reports/phase2_acceptance_readiness_decision.md`.

### S2-E004 — 50,000-tick opcode-composition locality

- **Hypothesis:** Radius-1 interaction produces greater graded opcode-composition
  similarity than radius 8 through 50,000 ticks.
- **Test:** Ten new matched seeds; pooled final-window Jensen–Shannon excess.
- **Result:** Mean paired effect `+0.005324`, 95% bootstrap interval
  `[+0.003924,+0.007259]`, exact `p=0.000977`, positive 10/10. Combined 5k and
  50k campaigns were positive in 20/20 pairs. Runtime was 12h43m48s.
- **Decision:** **PASS; no nearby repeat or sweep.**
- **Why:** Direction and magnitude replicated across a tenfold horizon increase.
- **Follow-up:** Functional meaning and distance decay, S2-E005; 500k deferred as
  S2-I002.
- **Evidence:** `reports/phase2_opcode_js_temporal_decision.md`.

### S2-E005 — Functional prediction and spatial distance decay

- **Hypotheses:** Opcode composition predicts standardized execution behavior;
  composition similarity decays more strongly with distance at radius 1.
- **Test:** Ten matched seed averages, Mantel/permutation analysis, paired tests,
  and Holm correction across the two hypotheses.
- **Result:** Functional correlation mean `0.284521`, interval
  `[0.259729,0.309913]`, `p=0.000977`, positive 10/10. Radius-1 minus radius-8
  decay-strength effect `+0.00013480`, interval
  `[+0.00010728,+0.00016145]`, `p=0.000977`, positive 10/10. Both survived Holm.
- **Decision:** **PASS both; proceed to explicit-reproduction model development.**
- **Why:** Spatial composition is not merely categorical proximity—it predicts a
  controlled execution assay and exhibits reproducible distance structure.
- **Follow-up:** Stage 3R reproduction controls; no immediate 500k run.
- **Evidence:** `reports/phase2_functional_distance_decision.md`.

## Stage 3R — Scheduled reproduction mechanism control

### S3R-E001 — Scheduled reproduction liveness

- **Hypothesis:** A scheduled, pool-funded copy-birth rate exists that creates
  lineage depth without extinction, clogging, or conservation failure.
- **Test:** Four rates from `5e-6` to `5e-5`, three runs each; mechanics only.
- **Result:** Rate `2e-5` passed 3/3 with median 71 births, occupancy 0.835, zero
  pool blocks, and lineage depth 2. Other rates passed at most 2/3.
- **Decision:** **Select `2e-5` for the neutral mechanism control.**
- **Why:** It was the only candidate satisfying all frozen feasibility criteria.
- **Follow-up:** Lineage patch test, S3R-E002.
- **Evidence:** `reports/stage3r_reproduction_liveness_report.md`.

### S3R-E002 — Local-placement lineage patch

- **Hypothesis:** Local offspring placement increases neutral-family neighbor
  association relative to wide placement.
- **Test:** Ten matched radius-1/radius-8 seed pairs.
- **Result:** Mean paired effect `+0.032600`, bootstrap interval
  `[+0.031180,+0.033990]`, exact `p=0.000977`, positive 10/10. All runs conserved
  matter. Radius 1 had 448 no-space blocks and fewer births, revealing a vacancy
  opportunity confound.
- **Decision:** **PASS for the complete local-placement mechanism, not a pure
  displacement effect.**
- **Why:** Strong clustering persisted despite fewer descendants, but unequal
  vacancy access required a controlled confirmation.
- **Follow-up:** Vacancy-first control, S3-E001.
- **Evidence:** `reports/stage3r_lineage_patch_decision.md`.

## Stage 3 — Causal reproduction and energy

### S3-E001 — Vacancy-first opportunity control

- **Hypothesis:** Local lineage clustering remains when vacancy opportunity and
  successful births are matched across radii.
- **Test:** Mechanics pilot followed by ten matched radius-1/radius-8 pairs with
  uniformly preselected vacancies.
- **Result:** Pilot median births were 78 at both radii with zero no-parent/pool
  blocks. Confirmation mean family-neighbor effect was `+0.045032`, interval
  `[+0.041877,+0.047977]`, `p=0.000977`, positive 10/10; each pair had exactly
  matched births and all 20 runs were conserved/invariant-clean.
- **Decision:** **PASS.**
- **Why:** The spatial lineage effect remains after removing the measured
  opportunity and birth-count confounds.
- **Follow-up:** Persistence and organization tests; do not tune placement radii.
- **Evidence:** `reports/stage3_causal_reproduction_pilots_decision.md`,
  `reports/stage3_vacancy_lineage_decision.md`.

### S3-E002 — Execution-gated exact-copy birth availability

- **Hypothesis:** Ordinary BFF interactions produce source-preserving complete
  copy events that can trigger conserved birth.
- **Test:** Three frozen 10,000-tick runs with full-tape equality criterion.
- **Result:** Exact-copy triggers: 0/3 runs; trigger-gated births: 0.
- **Decision:** **NO-GO.**
- **Why:** The mechanism was absent under the frozen conditions. Criteria were
  not weakened and parameters were not tuned.
- **Follow-up:** S3-I004 independently viable substrate. Scheduled birth remains
  explicitly exogenous.
- **Evidence:** `reports/stage3_causal_reproduction_pilots_decision.md`.

### S3-E003 — Explicit energy-ledger liveness

- **Hypothesis:** One tested influx supports active dynamics while closing the
  explicit energy ledger within relative error `1e-9`.
- **Test:** Influxes 64, 256, and 1,024; three runs each.
- **Result:** Influx 1,024 passed 3/3 with maximum relative error `1.721e-11`,
  active-interaction fraction 1.0, occupancy 0.771, and no starvation deaths.
  Lower influxes failed only the frozen dissipated-fraction ceiling.
- **Decision:** **GO at influx 1,024; reject lower candidates.**
- **Why:** It was the only operating point satisfying every preregistered
  accounting and liveness criterion.
- **Follow-up:** Energy-funded birth, S3-E004; differentiated access S3-I005.
- **Evidence:** `reports/stage3_energy_liveness_decision.md`.

### S3-E004 — Energy-funded scheduled birth

- **Hypothesis:** Parent-held cost 5 reduces successful scheduled births relative
  to cost 0 while retaining viable birth and exact ledgers.
- **Test:** Ten matched pairs at the selected energy operating point.
- **Result:** Cost-0 minus cost-5 mean effect 43.9 births, interval
  `[38.598,48.900]`, exact `p=0.000977`, positive 10/10. Cost-5 median was 38
  versus 84; all 20 runs were matter/energy clean, maximum energy error
  `1.945e-11`.
- **Decision:** **PASS.**
- **Why:** The atomic energy requirement causally constrained otherwise matched
  birth attempts without breaking liveness or conservation.
- **Follow-up:** S3-I005; do not interpret uniform absorption as trophic ecology.
- **Evidence:** `reports/stage3_energy_birth_decision.md`.

### S3-E005 — Lineage switch-off persistence

- **Hypothesis:** Local lineage association persists after scheduled birth stops,
  while the continued-birth arm remains a feasible positive control.
- **Test:** Ten stopped and ten continued runs through tick 19,900; stop at
  10,000; frozen occupancy ceiling 0.95.
- **Result:** Stopped runs retained mean excess `+0.045945`, interval
  `[+0.042071,+0.049567]`, `p=0.000977`, median retention 0.999, positive 10/10.
  Continued runs reached median occupancy 0.971; only 1/10 met the ceiling.
- **Decision:** **Integrated NO-GO; narrow persistence observation retained.**
- **Why:** Slow turnover preserved lineage labels, but the required continued
  positive control clogged. Persistent labels are not self-maintenance.
- **Follow-up:** S3-I003 population regulation; do not lower the ceiling or tune
  the completed campaign.
- **Evidence:** `reports/stage3_lineage_persistence_decision.md`.

### S3-E006 — Empirical organization identifiability diagnostic

- **Hypothesis:** The exact eleven-component composition representation is
  identifiable in at least 12/15 windows, and closed, exactly balanced active
  candidates exceed a product-permutation null with candidates in at least 8/15
  windows.
- **Test:** Three frozen seeds (`202609170`–`202609172`), 5,000 ticks, 1%
  deterministic reaction sampling, five 1,000-tick windows per seed, and 199
  aligned product permutations.
- **Result:** Identifiability passed in 15/15 windows. Accepted candidates occurred
  in 5/15 windows, below the frozen 8/15 prevalence requirement. The observed
  mean was 0.4 candidates versus a null 95th percentile of 0.0 (Monte Carlo
  `p=0.005`). All 3 runs succeeded and conserved matter, with zero invariant
  failures and maximum relative energy error `1.831e-11`.
- **Decision:** **Representation PASS; empirical organization excess NOT
  SUPPORTED.**
- **Why:** Although the observed mean exceeded the permutation null, the
  preregistered prevalence criterion failed. The conjunction required every
  criterion, so the positive null contrast cannot override that failure.
- **Limitations:** The result is specific to exact composition species and frozen
  1,000-tick windows; it neither establishes organism identity nor licenses
  post-hoc clustering or representation changes.
- **Follow-up:** S3-I002 abandoned under its stopping rule. Retain the five
  candidate-bearing windows as descriptive evidence only.
- **Evidence:** `reports/stage3_organization_report.md`,
  `reports/stage3_organization_windows.csv`; raw campaign:
  `/home/jojo/bio-sim-results/bazzite/stage3_organization_diagnostic`.

### S3-E007 — Density-independent population regulation

- **Hypothesis:** Increasing neutral spontaneous dissolution without reducing the
  frozen scheduled-birth rate maintains a partially empty lattice and preserves
  a valid lineage-clustering positive control.
- **Test:** A mechanics-only pilot crossed dissolution rates `2e-5`, `3e-5`,
  `5e-5`, and `1e-4` over three 20,000-tick seeds each. The frozen selected rate
  was then tested on ten held-out 20,000-tick seeds with 499-permutation final
  family-neighbor tests.
- **Result:** Rate `2e-5` was the sole eligible pilot treatment (3/3 feasible),
  with median occupancy 0.812 and median absolute 10k-to-19.9k occupancy change
  0.012. Held-out confirmation was feasible in 10/10 runs; median late occupancy
  was 0.838 and median births were 340. Final family-neighbor excess averaged
  `+0.088461`, bootstrap interval `[+0.084802,+0.091852]`, exact one-sided
  `p=0.000977`, positive and individually significant in 10/10 runs.
- **Decision:** **PASS for a non-clogging neutral lineage positive control.**
- **Why:** Every frozen mechanics, liveness, conservation, and lineage-control
  criterion passed on held-out seeds without changing the selected birth rate.
- **Limitations:** Spontaneous dissolution is exogenous density-independent
  mortality and scheduled cloning remains exogenous. This result does not show
  endogenous reproduction, adaptation, or self-maintenance.
- **Follow-up:** S3-I006, a newly preregistered regulated switch-off experiment;
  do not reinterpret the failed original switch-off gate.
- **Evidence:** `reports/stage3_population_regulation_pilot_report.md`,
  `reports/stage3_population_regulation_confirmation_report.md`; raw campaigns:
  `/home/jojo/bio-sim-results/bazzite/stage3_population_regulation_pilot` and
  `/home/jojo/bio-sim-results/bazzite/stage3_population_regulation_confirmation`.

### S3-E008 — Regulated lineage switch-off persistence

- **Hypothesis:** Under the selected `2e-5` spontaneous dissolution rate, neutral
  lineage association remains positive after scheduled birth stops, while the
  continued-birth arm retains a stronger valid positive control.
- **Test:** Ten new matched seeds (`202609193`–`202609202`), 20,000 ticks,
  continued versus stop-before-10,000 birth, four frozen checkpoints, 499
  fixed-occupancy family-label permutations, and Holm correction across stopped
  persistence and continued-minus-stopped co-primary endpoints.
- **Result:** Stopped final family excess averaged `+0.043097`, interval
  `[+0.040045,+0.046359]`; continued-minus-stopped averaged `+0.045861`, interval
  `[+0.040967,+0.050633]`. Both exact one-sided tests had raw `p=0.000977` and
  Holm `p=0.001953`. Both arms were positive and individually significant in
  10/10 runs. Median stopped retention was 0.881; stopped/continued mechanical
  feasibility was 8/10 and 10/10. All 20 runs succeeded, conserved matter, and
  had zero invariant failures.
- **Decision:** **PASS for turnover-resistant neutral lineage-patch persistence.**
- **Why:** Every frozen integrated criterion passed, including both corrected
  co-primary tests and the minimum mechanical-feasibility counts.
- **Limitations:** Population declined after birth removal, as expected, and two
  stopped runs missed the lineage-depth feasibility threshold. The pattern is a
  neutral label association under exogenous death and scheduled cloning, not
  endogenous reproduction or self-maintenance.
- **Follow-up:** No additional neutral lineage-persistence campaign is justified.
  Proceed to a preregistered Stage 4 active resource-access mechanism before
  making ecological claims.
- **Evidence:** `reports/stage3_regulated_lineage_persistence_report.md`,
  `reports/stage3_regulated_lineage_persistence_endpoints.csv`; raw campaign:
  `/home/jojo/bio-sim-results/bazzite/stage3_regulated_lineage_persistence`.

## Stage 4 — Behaviorally accessible energy and ecology

### S4-E001 — Active energy-uptake mechanics positive control

- **Hypothesis:** Execution of reserved BFF byte `0x3a` transfers bounded local
  field energy into the active tape and preserves exact accounting, while the
  byte-identical feature-disabled control records no uptake.
- **Test:** Five matched seeds (`202609210`–`202609214`), 100 ticks, eight seeded
  tapes on a 4×4 lattice, enabled versus disabled active uptake, zero passive
  absorption, mutation, dissolution, reseeding, and reproduction.
- **Result:** Enabled runs each recorded 1,600 reached uptake instructions,
  206.72 gross energy transfer, 78.72 final tape energy, and 12,800 executed
  steps. Disabled runs recorded exactly zero uptake, zero tape energy, and zero
  funded steps. All 5/5 matched pairs favored enabled uptake. All 10 runs
  succeeded with fixed occupancy, zero invariant failures, and maximum relative
  energy error `3.553e-15`.
- **Decision:** **PASS for execution-mediated active uptake mechanics.**
- **Why:** Every frozen positive-control, disabled-control, transfer, occupancy,
  and ledger criterion passed on all seeds.
- **Limitations:** Every tape in the enabled arm carried the uptake opcode. This
  does not yet show differentiated access among coexisting types, fitness,
  adaptation, trophic ecology, or organism identity.
- **Follow-up:** S4-I002 mixed-population differentiated-access assay.
- **Evidence:** `reports/stage4_active_uptake_report.md`,
  `reports/stage4_active_uptake_runs.csv`; raw campaign:
  `/home/jojo/bio-sim-results/bazzite/stage4_active_uptake`.

### S4-E002 — Mixed-population differentiated energy access

- **Hypothesis:** Uptake-capable tapes acquire and retain more energy than
  one-byte matched controls while both coexist in the same uniform field, with
  passive absorption disabled and exact ledger closure.
- **Test:** Five matched seeds (`202609220`–`202609224`), 200 ticks, four uptake
  and four control tapes in alternating seed-crossed positions, globally enabled
  versus disabled uptake arms, immutable tape types, and no demographic dynamics.
- **Result:** In every enabled run, uptake tapes finished at mean energy 9.84
  while coexisting controls remained exactly zero; all five within-run
  differences were positive (exact one-sided sign `p=0.03125`). Energy-area
  differences were positive in 5/5, uptake tapes funded 12,320–12,720 steps,
  and controls funded zero. Both types had zero energy and steps in all disabled
  runs. All 10 runs succeeded with fixed type counts, zero invariant failures,
  and maximum relative energy error `5.713e-15`.
- **Decision:** **PASS for coexisting type-specific energy access.**
- **Why:** Every frozen differentiation, disabled-control, immutability, and
  accounting criterion passed.
- **Limitations:** The types were deliberately seeded and immutable, and energy
  access had no survival or reproduction consequence. This is differentiated
  mechanics, not ecological selection.
- **Follow-up:** S4-I003 structured energy-field scale.
- **Evidence:** `reports/stage4_mixed_energy_access_report.md`,
  `reports/stage4_mixed_energy_access_runs.csv`; raw campaign:
  `/home/jojo/bio-sim-results/bazzite/stage4_mixed_energy_access`.

### S4-E003 — Structured energy-field scale

- **Hypothesis:** Fixed-total static patch influx produces stronger spatial
  structure and inequality in execution-mediated uptake than uniform influx.
- **Test:** Uniform plus patch correlation lengths 0.5, 2, and 8 cells; five
  matched seeds (`202609230`–`202609234`), 1,000 ticks, fixed occupancy, and
  mechanics-only uptake, tape-energy, profile, and ledger endpoints.
- **Result:** Mean-patch uptake Moran effects were positive in 5/5 seeds (exact
  one-sided sign `p=0.03125`); uptake-CV and tape-energy Moran effects were also
  positive in 5/5. Median uptake Moran's I was 0.576, 0.840, and 0.887 across
  increasing patch scales versus 0.360 under uniform influx. All patch profiles
  were positive and normalized. All 20 runs succeeded with unchanged tapes,
  zero invariant failures, and maximum relative energy error `3.786e-13`.
- **Decision:** **PASS for structured local energy-access niches.**
- **Why:** Every frozen spatial, inequality, profile-integrity, activity, and
  accounting criterion passed without selecting a favored scale.
- **Limitations:** Occupancy and tape type were fixed; no survival, reproduction,
  fitness, lineage, or organization endpoint was tested.
- **Follow-up:** S4-I004 active-uptake survival consequence, using the
  near-interaction scale fixed independently rather than selected from outcomes.
- **Evidence:** `reports/stage4_structured_field_report.md`,
  `reports/stage4_structured_field_effects.csv`; raw campaign:
  `/home/jojo/bio-sim-results/bazzite/stage4_structured_field`.

### S4-E004 — Active-uptake survival consequence

- **Hypothesis:** In a mixed immutable population under a static patch field,
  active uptake preserves uptake-capable tapes through starvation while matched
  controls and the globally feature-disabled population are removed.
- **Test:** Ten held-out seeds (`202609240`–`202609249`), matched uptake-enabled
  and disabled arms, alternating 64/64 uptake and control tapes, correlation
  length 2, 500 ticks, and the existing 50-tick starvation rule. Reproduction,
  mutation, writes, passive absorption, and reseeding were disabled.
- **Result:** Enabled uptake-tape survival was 0.969–1.000 while enabled control
  survival was zero. The primary difference was positive in 10/10 seeds (exact
  one-sided sign `p=0.00097656`). Both types reached zero survival in all disabled
  arms. All 20 runs succeeded; every death was attributed to starvation, tape
  types remained consistent, invariant failures were zero, and maximum relative
  energy error was `2.309e-13`.
- **Decision:** **PASS for a causal starvation-survival consequence.**
- **Why:** Uptake capability was the only within-population type difference, and
  the globally disabled arm removed survival for both opcode labels.
- **Limitations:** This is survival under a deliberately configured starvation
  regime, not evolved fitness, competition, adaptation, reproduction,
  organization, self-maintenance, or organism identity.
- **Follow-up:** A separately preregistered resource-coupled birth or frequency
  experiment is now justified but is not required to establish this bounded
  survival result.
- **Evidence:** `reports/stage4_uptake_survival_report.md`,
  `reports/stage4_uptake_survival_effects.csv`; raw campaign:
  `/home/jojo/bio-sim-results/bazzite/stage4_uptake_survival`.

### S4-E005 — Resource-coupled birth and frequency change

- **Hypothesis:** Energy acquired by active uptake funds scheduled exact-copy
  births and increases uptake-type frequency across low, equal, and high initial
  frequencies.
- **Test:** Ten held-out seeds (`202609250`–`202609259`), initial uptake counts 8,
  32, and 56 of 64 tapes, matched uptake-enabled and disabled arms, 500 ticks,
  static correlation-length-2 influx, and energy-costly vacancy-first cloning.
  Mortality, mutation, passive absorption, writes, and reseeding were disabled.
- **Result:** Frequency change and enabled-minus-disabled differences were
  positive in all 30 matched cases (exact sign `p=9.313e-10`), every successful
  enabled birth had an uptake parent, and disabled arms had zero births. Median
  frequency increases were 0.441, 0.261, and 0.054. However, two low-frequency
  enabled runs fell below the frozen minimum of 16 births, with the overall
  minimum only 3. All 60 runs succeeded with zero invariant failures and maximum
  relative energy error `3.809e-13`.
- **Decision:** **FAIL the frozen confirmatory gate.**
- **Why:** The mandatory per-run birth-liveness criterion failed in 2/30 enabled
  runs despite uniformly positive directional effects.
- **Limitations:** Directional frequency shifts are descriptive evidence only.
  The preregistered stop rule forbids parameter tuning or a confirmatory claim
  that uptake drives reproduction.
- **Follow-up:** Stop the energy-coupled reproduction branch. Retain the completed
  differentiated-access, spatial-niche, and starvation-survival results; return
  to the roadmap's structured-signal/event-driven-genome work.
- **Evidence:** `reports/stage4_resource_birth_report.md`,
  `reports/stage4_resource_birth_effects.csv`; raw campaign:
  `/home/jojo/bio-sim-results/bazzite/stage4_resource_birth`.

### S4S-E001 — Exact-tag signal dispatch mechanics

- **Hypothesis:** A local environmental byte tag can select an exact-matching
  active-tape handler while mismatched and disabled controls retain PC-zero
  execution.
- **Test:** Five held-out seeds (`202609260`–`202609264`), matched, mismatched,
  and globally disabled arms, 100 ticks, one instruction per interaction, and an
  immutable tagged uptake-handler tape.
- **Result:** Matched arms recorded exactly 4,000 reads, 4,000 dispatches, and
  4,000 uptake executions. Mismatched arms recorded 4,000 reads but zero
  dispatches and uptake; disabled arms recorded zero reads, dispatches, and
  uptake. Matched final mean tape energy was 9.99 versus zero in both controls.
  All 15 runs succeeded with unchanged tapes, zero invariant failures, and
  maximum relative energy error `2.297e-15`.
- **Decision:** **PASS for exact local signal dispatch mechanics.**
- **Why:** Every interaction-level dispatch, mismatch, disabled-feature,
  immutability, activity, and accounting criterion passed.
- **Limitations:** Signals are read-only, uniform, and exactly matched. No
  writing, approximate tag matching, coordination, fitness, adaptation, or
  organization endpoint was tested.
- **Follow-up:** S4S-I002 local signal-write mechanics.
- **Evidence:** `reports/stage4_signal_dispatch_report.md`,
  `reports/stage4_signal_dispatch_runs.csv`; raw campaign:
  `/home/jojo/bio-sim-results/bazzite/stage4_signal_dispatch`.

### S4S-E002 — Local signal-write mechanics

- **Hypothesis:** A tagged writer can atomically replace every occupied
  interaction-partner cell's signal tag while disabled and mismatched controls
  leave the field unchanged.
- **Test:** Five held-out seeds (`202609270`–`202609274`), write-enabled,
  write-disabled, and dispatch-mismatched arms, 100 ticks, and immutable tagged
  writer tapes on eight of sixteen cells.
- **Result:** Write-enabled runs recorded 5–6 changed tags rather than the frozen
  requirement of exactly eight, and no run changed all occupied tags. The random
  half-occupied lattice contained isolated tapes that could not be selected as
  local interaction partners. Write-disabled arms recorded 4,000 dispatches and
  zero writes; mismatched arms recorded zero dispatches and writes. Empty cells
  and all tapes remained unchanged, and all 15 runs succeeded with zero invariant
  failures.
- **Decision:** **FAIL the frozen writable-signal mechanics gate.**
- **Why:** The mandatory complete occupied-field transition failed in 5/5 seeds,
  even though reachable partner-cell writes behaved as implemented.
- **Limitations:** The outcome identifies a topology/reachability mismatch in the
  assay; observed writes are descriptive only. The preregistered stop rule does
  not permit changing occupancy or neighborhood after seeing the result.
- **Follow-up:** Do not run the planned causal inter-tape response campaign.
  Retain read-only exact dispatch and stop writable-signal/niche-construction
  claims under this branch.
- **Evidence:** `reports/stage4_signal_write_report.md`,
  `reports/stage4_signal_write_runs.csv`; raw campaign:
  `/home/jojo/bio-sim-results/bazzite/stage4_signal_write`.

### S4S-R001 — Signal-write reachability positive control

- **Hypothesis:** Full occupancy removes unreachable interaction partners and
  permits unchanged writers to replace every signal tag.
- **Test:** The same write-enabled, write-disabled, and mismatched mechanics arms
  on a fully occupied 4×4 torus with five new seeds (`202609280`–`202609284`).
- **Result:** Write-enabled runs changed 14–15 of 16 tags, and no run completed
  the field. Once a writer's own tag was replaced, exact dispatch stopped that
  writer; this dynamic deactivation stranded remaining initial tags. Controls
  behaved exactly as expected, and all 15 runs succeeded with zero invariant
  failures.
- **Decision:** **FAIL the reachability positive control.**
- **Why:** Full static connectivity did not satisfy the frozen 16-tag transition
  because writing changed future writer eligibility.
- **Limitations:** This does not alter either prior failure and does not license a
  different writer tape or dispatch rule.
- **Follow-up:** Stop writable-signal and causal inter-tape-response work. A new
  independent branch may still test read-only structured environmental response.
- **Evidence:** `reports/stage4_signal_write_reachability_report.md`,
  `reports/stage4_signal_write_reachability_runs.csv`; raw campaign:
  `/home/jojo/bio-sim-results/bazzite/stage4_signal_write_reachability`.

### S4S-E003 — Structured read-only environmental response

- **Hypothesis:** One immutable dual-handler tape expresses uptake only in the
  spatial region carrying its uptake-handler tag.
- **Test:** Five held-out seeds (`202609290`–`202609294`), fully occupied 4×4
  torus, deterministic left/right tags, uniform-primary positive controls, and
  globally disabled controls. Every tape and all dynamics were otherwise
  identical.
- **Result:** Split arms read and dispatched all 8,000 interactions; all 4,035
  uptake executions occurred in the left half, every left cell had uptake, and
  every right cell had zero. Final tape energy was 9.99 left and zero right.
  Uniform arms executed uptake in all 8,000 interactions and ended at 9.99 in
  both halves; disabled arms had zero reads, dispatches, uptake, and tape energy.
  All 15 runs succeeded with unchanged tapes, zero invariant failures, and
  maximum relative energy error `3.268e-15`.
- **Decision:** **PASS for spatially conditional behavior under read-only
  environmental signals.**
- **Why:** Every frozen cell-level response, uniform-control, disabled-control,
  immutability, and accounting criterion passed.
- **Limitations:** The field and tapes were deliberately constructed and static.
  This is not communication, coordination, fitness, adaptation, or organization.
- **Follow-up:** S4S-I004 task-relevant signal modulation may test whether correct
  response changes interaction opportunity without direct fitness assignment.
- **Evidence:** `reports/stage4_structured_signal_response_report.md`,
  `reports/stage4_structured_signal_response_runs.csv`; raw campaign:
  `/home/jojo/bio-sim-results/bazzite/stage4_structured_signal_response`.

### S4S-E004 — Task-relevant signal modulation

- **Hypothesis:** Correct local signal response increases future interaction
  opportunity without assigning births, survival, or direct fitness.
- **Test:** Ten held-out seeds (`202609300`–`202609309`), matched task-enabled and
  disabled arms, eight correct and eight incorrect immutable dual-handler tapes,
  a fixed split signal field, 200 ticks, and one-tick-delayed score weighting with
  bonus 3.
- **Result:** Correct-type selection fraction was 0.794–0.804 with task weighting
  versus 0.491–0.508 under uniform disabled-task selection. Paired effects were
  positive in 10/10 seeds (exact one-sided sign `p=0.00097656`). Every response
  and final task score matched the declared task. All 20 runs succeeded with two
  immutable types, zero invariant failures, and maximum relative energy error
  `1.748e-14`.
- **Decision:** **PASS for task-relevant modulation of interaction opportunity.**
- **Why:** Every frozen paired-selection, disabled-control, score, behavior,
  immutability, and accounting criterion passed.
- **Limitations:** Opportunity weighting is simulator-mediated and caused no
  demographic outcome. This is not fitness, adaptation, communication,
  coordination, or organization.
- **Follow-up:** Close the minimum viable read-only structured-signal phase. A
  demographic test is deferred until a non-artificial coupling from interaction
  opportunity to endogenous birth or persistence exists.
- **Evidence:** `reports/stage4_task_modulation_report.md`,
  `reports/stage4_task_modulation_effects.csv`; raw campaign:
  `/home/jojo/bio-sim-results/bazzite/stage4_task_modulation`.

## Current frontier

The minimum viable structured-signal phase is complete: exact event dispatch,
spatially conditional behavior by one fixed tape, and task-relevant interaction
modulation all passed held-out controls. Stage 4 also retains differentiated
energy access, static energy niches, and causal starvation survival. Failed
energy-coupled reproduction and writable/inter-tape signaling remain stopped.
The project still does **not** support endogenous reproduction, evolved
adaptation, communication, coordination, niche construction, competition,
trophic ecology, prevalent empirical organization, self-maintenance, or organism
identity. No experiment is currently claimed or running. The next proposed work
is AC-I001 from `reports/conserved_bff_discovery_phase_design.md`: a
blocked-load-matched test of whether conserved resource composition selectively
filters functional BFF replicator origin.
