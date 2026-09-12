# Experimental ideas registry

This is the shared queue for experiments that have **not** reached a final
decision. It is organized by research stage so the Mac and remote machine can
work without duplicating campaigns. Completed or terminated entries move to
[`EXPERIMENTS_EXECUTED.md`](EXPERIMENTS_EXECUTED.md); any resulting follow-up is
added here with a new ID.

## Coordination protocol

1. Start from a clean checkout and run `just pull`.
2. Add an idea as `Proposed`; include why it matters and its predecessor.
3. Before implementation or execution, change it to `Claimed`, fill in owner,
   machine, UTC claim time, and preregistration path, then commit and push that
   claim immediately.
4. Use only these states: `Proposed`, `Claimed`, `Running`, `Blocked`,
   `Complete`, or `Abandoned`. Only one owner may hold `Claimed`/`Running`.
5. Before launching, pull again and confirm no other row claims the same
   question, seeds, or treatment block.
6. Never edit thresholds after execution starts. Record deviations in the final
   report rather than silently changing the preregistration.
7. When finished, append the hypothesis test, result, decision, rationale, and
   artifact links to `EXPERIMENTS_EXECUTED.md`; mark this row `Complete`; add
   each justified follow-up below as a new idea; commit and push promptly.
8. Generated runs go to central result storage, not Git. Commit configurations,
   preregistrations, analysis code, compact tables, and narrative reports.

A claim coordinates work; it is not approval of a scientific protocol. If two
machines race to claim the same entry, the first claim on `origin/main` wins.
The other machine must reset its claim and choose different work.

## Entry template

```markdown
### S<stage>-I<sequence> — Short title

- **Status:** Proposed
- **Owner / machine:** Unclaimed
- **Claimed at:** —
- **Depends on:** experiment ID or report
- **Why:** uncertainty this resolves and why it is worth the cost
- **Hypothesis:** directional, falsifiable statement
- **Test:** treatments, controls, seeds, primary endpoint, and stopping rule
- **Preregistration:** pending
- **Estimated cost:** runtime and storage
- **On success:** next decision
- **On failure:** next decision or stop rule
```

---

## Stage 0 — Bare soup and reference replication

No active experiments. The reference paper-scale emergence question is closed
for the implemented BFF semantics. Do not repeat the underpowered 256-tape
acceptance runs or tune mutation around the successful seed-0 trajectory.

## Stage 1 — Conserved symbol economy

### S1-I001 — Matched-friction origin-filter confirmation

- **Status:** Proposed
- **Owner / machine:** Unclaimed
- **Claimed at:** —
- **Depends on:** Stage 1 batches 6–7; `reports/phase1_campaign2_consolidated_report.md`
- **Why:** Natural structural-symbol exclusion suppressed origin in 0/5 runs
  versus 3/5 controls, but the one-sided Fisher result was `p=0.083` and the
  arbitrary-symbol control had lower blocked-write volume. Matching total
  friction is required before claiming class-specific selection.
- **Hypothesis:** Excluding the natural structural set suppresses emergence more
  than a preregistered non-structural exclusion set matched for blocked-write
  load.
- **Test:** Freeze a matching rule using pilot-independent data, then compare
  new matched seeds with emergence and held-to-end takeover as primary outcomes.
  Do not choose control symbols after seeing emergence results.
- **Preregistration:** pending
- **Estimated cost:** high; paper-like long-window runs
- **On success:** strengthen the origin-filter claim and test generality on an
  independently found replicator class.
- **On failure:** retain conservation as generic friction/homeostasis and stop
  class-specific origin-filter claims.

### S1-I002 — Same-checkpoint origin-versus-established intervention in organism-sim

- **Status:** Proposed
- **Owner / machine:** Unclaimed
- **Claimed at:** —
- **Depends on:** `organism-sim/PHASE1_FINDINGS_TRANSFER.md`
- **Why:** The BFF results suggest the same shortage can filter origin while an
  established ecology buffers it. The organism model needs a checkpoint-matched
  test rather than comparisons of unrelated initial conditions.
- **Hypothesis:** Removing target resources suppresses de-novo establishment more
  strongly than it disrupts a checkpointed established ecology, relative to an
  irrelevant-resource and matched-friction control.
- **Test:** First implement deterministic checkpoint/resume and corrected
  late-window reporting; freeze one checkpoint and crossed intervention/control
  conditions before execution.
- **Preregistration:** pending; blocked on checkpoint/resume
- **Estimated cost:** medium to high
- **On success:** motivate a general origin-versus-maintenance study across
  substrates.
- **On failure:** treat the BFF asymmetry as substrate-specific.

## Stage 2 — Spatial locality

### S2-I001 — Resolve the parasite-gate protocol

- **Status:** Blocked
- **Owner / machine:** Unclaimed
- **Claimed at:** —
- **Depends on:** `reports/phase2_acceptance_readiness_decision.md`
- **Why:** The selected parasite failed its required large-radius positive
  control, so containment cannot be inferred. More runs with that candidate
  would not repair identification.
- **Hypothesis:** Pending one of two explicit paths: (a) an independently
  validated host/parasite pair invades at large radius and is contained locally,
  or (b) parasite containment is removed from Stage 2 and deferred to a later
  ecology stage.
- **Test:** Choose and preregister one path before implementation. Do not broaden
  family definitions, seed more copies, lower mutation, or tune on radius data.
- **Preregistration:** pending protocol decision
- **Estimated cost:** unknown; potentially high
- **On success:** run only the newly valid confirmatory gate.
- **On failure:** close parasite containment for this substrate/configuration.

### S2-I002 — Conditional 500,000-tick locality confirmation

- **Status:** Proposed
- **Owner / machine:** Unclaimed
- **Claimed at:** —
- **Depends on:** S2-I001 and the 5k/50k locality campaigns
- **Why:** A very-long run is useful only if a future gate specifically requires
  500k-tick persistence. Existing continuous locality effects already replicated
  in 20/20 matched pairs through 50k ticks.
- **Hypothesis:** The frozen radius-1 versus radius-8 opcode-composition locality
  contrast remains positive through 500,000 ticks.
- **Test:** Use the already frozen endpoint/configuration and a resource budget;
  no nearby radius or mutation sweep.
- **Preregistration:** existing protocol requires an explicit authorization
- **Estimated cost:** at least overnight; measured 50k campaign took 12h44m
- **On success:** establish very-long persistence only.
- **On failure:** bound the lifetime of the locality effect without retuning.

## Stage 3 — Reproduction, energy, persistence, and organization

### S3-I001 — Empirical organization identifiability and permutation test

- **Status:** Complete
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-07T05:23:17Z (transferred from Mac claim)
- **Depends on:** completed Stage 3 energy gate; `reports/stage3_causal_phase_synthesis.md`
- **Why:** Neutral lineage patches and energy-constrained scheduled birth are
  mechanism controls, not evidence of self-maintaining organization. The next
  question is whether reaction organization is even identifiable under a frozen,
  threshold-free composition representation.
- **Hypothesis:** At least 12/15 windows pass recurrence/support criteria and the
  observed mean count of closed, exactly balanced active candidates exceeds the
  product-permutation null (`p <= 0.05`), with candidates in at least 8/15
  windows.
- **Test:** Three seeds (`202609170`–`202609172`), 5,000 ticks, 1% deterministic
  interaction sampling, five frozen windows, exact eleven-component composition
  species, 199 aligned permutations. Stop before organization inference if the
  identifiability gate fails.
- **Preregistration:** `reports/stage3_organization_diagnostic_preregistration.md`
- **Estimated cost:** bounded; three 5k runs plus offline permutations
- **On success:** add S3-I002 for an intervention that removes external species
  inflow and measures recovery; do not claim organism identity.
- **On failure:** record non-identifiability and do not introduce post-hoc
  clustering or revert to sparse exact hashes.

### S3-I002 — Organizational recovery intervention

- **Status:** Abandoned
- **Owner / machine:** Unclaimed
- **Claimed at:** —
- **Depends on:** S3-I001
- **Why:** Observed closure and balanced flux can be window/representation
  artifacts. A perturbation is needed to test active rebuilding.
- **Hypothesis:** A preregistered candidate recovers its composition/flux after
  external member inflow is removed or a member is depleted, beyond matched
  null candidates.
- **Test:** Define only after S3-I001 identifies a candidate; use held-out seeds
  and freeze perturbation magnitude, recovery endpoint, controls, and horizon.
- **Preregistration:** not opened; S3-I001 missed its frozen prevalence gate
- **Estimated cost:** unknown
- **On success:** support bounded empirical self-maintenance and replicate on a
  second representation/substrate.
- **On failure:** retain descriptive organization only.

### S3-I003 — Population regulation for a non-clogging birth control

- **Status:** Complete
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-07T06:05:00Z
- **Depends on:** Stage 3 lineage switch-off NO-GO
- **Why:** Continued scheduled birth reached median occupancy 0.971 and failed
  the frozen occupancy ceiling in 9/10 runs. Long-run controls require a
  motivated regulation mechanism, not post-hoc reduction of birth rate.
- **Hypothesis:** A preregistered density-independent or resource-mediated death/
  birth mechanism maintains a partially empty lattice while preserving enough
  births for a lineage-persistence positive control.
- **Test:** First justify the mechanism; select liveness using mechanics only,
  without inspecting lineage endpoints; then run held-out confirmation.
- **Preregistration:** `reports/stage3_population_regulation_preregistration.md`
- **Estimated cost:** medium
- **On success:** create a new lineage-persistence experiment rather than
  reopening the failed gate.
- **On failure:** stop long-run scheduled-birth persistence work.

### S3-I004 — Independently viable endogenous copy substrate

- **Status:** Proposed
- **Owner / machine:** Unclaimed
- **Claimed at:** —
- **Depends on:** Stage 3 exact-copy-trigger NO-GO
- **Why:** The frozen BFF interaction criterion produced zero triggers in 3/3
  runs. Scheduled cloning cannot answer endogenous reproduction questions.
- **Hypothesis:** A substrate with independently demonstrated source-preserving
  exact-copy events yields nonzero preregistered triggers before simulator-funded
  allocation.
- **Test:** Validate copy events outside the spatial treatment first; then freeze
  trigger semantics and run a bounded availability pilot. Do not tune BFF seeds
  or weaken the failed criterion.
- **Preregistration:** pending
- **Estimated cost:** high/model-development
- **On success:** test interaction-gated conserved birth as a new stage.
- **On failure:** retain scheduled birth solely as a mechanism control.

### S3-I005 — Differentiated energy-access pilot

- **Status:** Blocked
- **Owner / machine:** Unclaimed
- **Claimed at:** —
- **Depends on:** completed energy accounting and S3-I001
- **Why:** Uniform passive absorption proves accounting and energetic constraint
  but cannot produce trophic roles or differentiated resource conversion.
- **Hypothesis:** A preregistered heterogeneous energy field creates persistent,
  measurable access/transfer differences without violating the energy ledger.
- **Test:** Separate mechanics/liveness selection from ecological endpoints;
  retain exact matter conservation and relative energy error `<=1e-9`.
- **Preregistration:** pending
- **Estimated cost:** medium
- **On success:** design a causal resource-flow experiment.
- **On failure:** keep the energy ledger as an accounting mechanism only.

### S3-I006 — Regulated lineage switch-off persistence

- **Status:** Complete
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-07T21:14:16Z
- **Depends on:** completed S3-I003 regulated positive-control confirmation
- **Why:** Density-independent turnover now prevents the continued-birth control
  from clogging. A new experiment can ask whether neutral lineage patches persist
  after birth stops under materially stronger turnover, without reopening or
  reinterpreting the failed original gate.
- **Hypothesis:** With spontaneous dissolution fixed at `2e-5`, local lineage
  association remains positive after scheduled birth stops and differs from a
  valid continued-birth positive control.
- **Test:** Preregister new held-out matched seeds, a fixed switch tick and
  horizon, the unchanged modulo-16 family endpoint, and retention criteria. Keep
  the selected birth and dissolution rates frozen.
- **Preregistration:** `reports/stage3_regulated_lineage_persistence_preregistration.md`
- **Estimated cost:** high; 20 matched 20,000-tick runs
- **On success:** support turnover-resistant neutral patch persistence only.
- **On failure:** conclude the earlier persistence was specific to slow turnover
  and stop neutral lineage-persistence work.

## Stage 4 — Behaviorally accessible energy and ecology

### S4-I001 — Active energy-uptake positive control

- **Status:** Complete
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-08T00:45:00Z
- **Depends on:** completed Stage 3 energy ledger
- **Why:** Passive absorption makes energy explicit but gives every occupied tape
  equal access. A mechanics-positive control must show that executed behavior can
  control local energy transfer before ecological differentiation is tested.
- **Hypothesis:** Executing a reserved uptake opcode transfers bounded local field
  energy into the active tape and closes the energy ledger, while the byte-exact
  disabled control records no uptake.
- **Test:** Five matched mutation-free 100-tick seeded assay pairs, active uptake
  enabled versus disabled, zero passive absorption, exact energy accounting, and
  frozen positive-control tape bytes.
- **Preregistration:** `reports/stage4_active_uptake_preregistration.md`
- **Estimated cost:** low; ten small mechanics runs
- **On success:** add a held-out differentiated-access or structured-field idea;
  do not claim ecology from the mechanics assay.
- **On failure:** stop Stage 4 ecological campaigns and repair only the explicit
  ledger or execution defect.

### S4-I002 — Mixed-population differentiated energy access

- **Status:** Complete
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-09T22:50:16Z
- **Depends on:** completed S4-I001 uptake mechanics positive control
- **Why:** The seeded all-uptake assay proves execution-mediated transfer but not
  differentiation between tape types sharing one environment. A mixed assay is
  required before introducing structured resource fields or ecological claims.
- **Hypothesis:** In a shared uniform field with passive absorption disabled,
  uptake-capable seeded tapes acquire and retain more energy than byte-matched
  uptake-disabled controls while the exact energy ledger remains closed.
- **Test:** Freeze mixed placement, immutable type labels, held-out seeds, a
  mutation-free horizon, energy-access endpoints, and disabled-feature controls.
  Do not use reproduction, mortality, or fitness endpoints in the first test.
- **Preregistration:** `reports/stage4_mixed_energy_access_preregistration.md`
- **Estimated cost:** low to medium
- **On success:** proceed to a preregistered structured-field scale campaign.
- **On failure:** retain active uptake as an isolated mechanics affordance and
  stop ecological interpretation.

### S4-I003 — Structured energy-field scale

- **Status:** Complete
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-10T06:05:56Z
- **Depends on:** completed S4-I002 mixed-population access gate
- **Why:** Uptake-capable and control tapes now show differentiated access in a
  shared uniform field. The next uncertainty is whether spatially structured
  influx produces persistent local energy niches at scales around the radius-1
  interaction neighborhood.
- **Hypothesis:** With total influx fixed, a preregistered static patch field
  produces stronger spatial autocorrelation and distance decay in uptake events
  and tape energy than a uniform field.
- **Test:** First validate normalized static fields mechanically; then freeze a
  small set of correlation lengths below, near, and above interaction scale.
  Select no field using lineage, organization, reproduction, or survival.
- **Preregistration:** `reports/stage4_structured_field_preregistration.md`
- **Estimated cost:** medium
- **On success:** test a causal ecological consequence with held-out seeds.
- **On failure:** retain differentiated uptake under uniform supply and stop
  spatial-niche claims.

### S4-I004 — Active-uptake survival consequence

- **Status:** Complete
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-11T21:36:08Z
- **Depends on:** completed S4-I003 structured-field mechanics gate
- **Why:** Structured fields create local access niches, but no Stage 4 campaign
  has shown a demographic consequence. Starvation mortality provides an existing
  resource-coupled outcome without introducing a new fitness mechanism.
- **Hypothesis:** In a mixed immutable population under a frozen patch field,
  active uptake preserves uptake-capable tapes through starvation while matched
  controls and the feature-disabled population are removed.
- **Test:** Freeze patch scale independently of outcomes, mixed placement,
  starvation horizon, held-out seeds, survival endpoints, and enabled/disabled
  feature arms. Keep reproduction, mutation, and reseeding off.
- **Preregistration:** `reports/stage4_uptake_survival_preregistration.md`
- **Estimated cost:** low to medium
- **On success:** support a bounded causal survival consequence and design a
  resource-coupled birth or competition experiment.
- **On failure:** retain spatial uptake as mechanics only and stop demographic
  interpretation.

### S4-I005 — Resource-coupled birth and frequency change

- **Status:** Complete
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-11T23:40:32Z
- **Depends on:** completed S4-I004 causal starvation-survival gate
- **Why:** Uptake now has a survival consequence, but Stage 4 has not shown that
  acquired energy can fund births and alter type frequency.
- **Hypothesis:** Under structured influx, scheduled energy-costly birth increases
  uptake-type frequency across low, equal, and high initial frequencies, while a
  globally disabled uptake arm produces no births.
- **Test:** Freeze three initial frequencies, deterministic spatial assignment,
  held-out seeds, energy-funded vacancy-first birth, enabled/disabled arms, and
  exact lineage/type/accounting endpoints. Disable mortality and mutation to
  isolate reproduction.
- **Preregistration:** `reports/stage4_resource_birth_preregistration.md`
- **Estimated cost:** medium; 60 matched 500-tick runs
- **On success:** close the energy-access Stage 4 subphase with a bounded causal
  synthesis and return to structured signals/event-driven genomes.
- **On failure:** retain uptake-mediated survival but stop reproduction and
  frequency-change claims.

### S4S-I001 — Exact-tag signal dispatch mechanics

- **Status:** Complete
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-11T23:51:41Z
- **Depends on:** completed Stage 4 energy-access subphase
- **Why:** The original roadmap's structured-signal/event-driven-genome branch
  has typed configuration but no operational signal field or dispatch semantics.
- **Hypothesis:** A local exact-match signal tag deterministically dispatches an
  active BFF tape to its tagged handler, while mismatched and globally disabled
  controls retain legacy PC-zero execution.
- **Test:** Implement a deterministic uniform byte-tag field and exact active-tape
  block scan, then run matched, mismatched, and disabled mechanics arms with a
  one-step uptake-handler assay. Defer signal writes and ecological endpoints.
- **Preregistration:** `reports/stage4_signal_dispatch_preregistration.md`
- **Estimated cost:** low; 15 small mechanics runs
- **On success:** preregister local signal-write mechanics before any coordination
  or niche-construction test.
- **On failure:** stop the signal branch and repair only the dispatch defect.

### S4S-I002 — Local signal-write mechanics

- **Status:** Complete
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-12T00:40:14Z
- **Depends on:** completed S4S-I001 exact-tag dispatch gate
- **Why:** Exact environmental dispatch now works, but tapes cannot alter their
  local signal environment; writable signals are required before testing niche
  construction or coordination.
- **Hypothesis:** A reserved BFF signal-write opcode deterministically replaces
  the active cell's tag from declared tape bytes, affects subsequent dispatch,
  and leaves matter and energy accounting unchanged.
- **Test:** Freeze atomic write semantics and a two-step writer/responder assay
  with disabled-opcode and mismatched-tag controls. Measure writes and subsequent
  dispatch only; defer ecological endpoints.
- **Preregistration:** `reports/stage4_signal_write_preregistration.md`
- **Estimated cost:** low
- **On success:** test whether written local signals causally alter another tape's
  behavior before any coordination claim.
- **On failure:** retain read-only exact dispatch and stop niche-construction
  interpretation.

### S4S-R001 — Signal-write reachability positive control

- **Status:** Complete
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-12T01:02:15Z
- **Depends on:** failed S4S-I002 topology diagnosis
- **Why:** S4S-I002 mixed opcode semantics with an unreachable-cell requirement.
  A fully connected positive control can isolate implementation correctness
  without changing or overturning that failed result.
- **Hypothesis:** With full occupancy, unchanged partner-cell write semantics
  replace all signal tags, while disabled and mismatched controls remain static.
- **Test:** Repeat the byte-exact mechanics arms at full 4×4 occupancy with new
  seeds and a separate fixed gate. Make no niche-construction claim.
- **Preregistration:** `reports/stage4_signal_write_reachability_preregistration.md`
- **Estimated cost:** low; 15 small runs
- **On success:** permit a separately preregistered fully connected inter-tape
  response positive control.
- **On failure:** stop writable-signal work completely.

### S4S-I003 — Structured read-only environmental response

- **Status:** Complete
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-12T01:07:26Z
- **Depends on:** completed S4S-I001 read-only dispatch; independent of failed
  writable-signal gates
- **Why:** Exact uniform dispatch works even though writable signaling failed. A
  deterministic two-region field can test whether one immutable tape expresses
  spatially conditional behavior without communication.
- **Hypothesis:** One dual-handler tape executes uptake only in the half-field
  carrying its uptake tag, while uniform and globally disabled controls establish
  full and absent response.
- **Test:** Add deterministic `split_x` two-tag initialization and run identical
  tapes under split, uniform, and disabled fields with per-cell response logging.
- **Preregistration:** `reports/stage4_structured_signal_response_preregistration.md`
- **Estimated cost:** low; 15 small runs
- **On success:** permit a task-relevant signal-to-interaction experiment, but no
  communication or coordination claim.
- **On failure:** stop structured read-only signal-response work.

### S4S-I004 — Task-relevant signal modulation

- **Status:** Claimed
- **Owner / machine:** Linux remote (`bazzite`)
- **Claimed at:** 2026-09-12T01:37:29Z
- **Depends on:** completed S4S-I003 spatial response gate
- **Why:** One fixed tape now changes behavior by environmental region, but that
  response has not affected interaction opportunity under a declared task.
- **Hypothesis:** Correct local signal-handler response can modulate interaction
  probability without direct fitness assignment or signal writing.
- **Test:** First specify a deterministic task score and scheduler weighting with
  disabled-task and shuffled-signal controls; freeze mechanics endpoints before
  any demographic consequence.
- **Preregistration:** `reports/stage4_task_modulation_preregistration.md`
- **Estimated cost:** medium
- **On success:** test a bounded demographic consequence with held-out seeds.
- **On failure:** retain spatial conditional behavior only.
