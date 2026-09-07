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

- **Status:** Proposed
- **Owner / machine:** Unclaimed
- **Claimed at:** —
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
- **Preregistration:** pending
- **Estimated cost:** high; 20 matched 20,000-tick runs
- **On success:** support turnover-resistant neutral patch persistence only.
- **On failure:** conclude the earlier persistence was specific to slow turnover
  and stop neutral lineage-persistence work.
