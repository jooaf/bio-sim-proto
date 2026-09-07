# Executed experiments registry

This append-only registry summarizes experiments that reached a decision. It is
not a replacement for preregistrations, manifests, raw artifacts, or full
reports. Pending work belongs in [`EXPERIMENTAL_IDEAS.md`](EXPERIMENTAL_IDEAS.md).

For every new entry include: frozen hypothesis, test and primary endpoint,
result with uncertainty/test statistic, decision, why that decision follows,
limitations, artifact links, and follow-up idea IDs. Negative and invalidated
results stay in the registry.

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

## Current frontier

Stage 3 supports causal neutral lineage clustering, exact matter/energy
accounting, energy-constrained scheduled birth, an identifiable exact
composition representation, and a non-clogging neutral turnover control. It does
**not** support endogenous reproduction, trophic organization, prevalent
empirical organization, self-maintenance, or organism identity. No experiment is
currently claimed or running in `EXPERIMENTAL_IDEAS.md`; S3-I006 is the next
proposed lineage-persistence test.
