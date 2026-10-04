# SM-B002 scheduling × source-remnant-retention factorial

**Frozen before implementation:** 2026-10-04

## Question and boundary

After a successful partial cleavage transfer, is continued survival of the
material-source remnant required for multigenerational material-transfer renewal,
and does that dependence change when offspring reaction eligibility is delayed by
500 ticks?

SM-B002 is the prospectively authorized second birth-boundary stage. It crosses:

- offspring scheduling: IMMEDIATE versus DELAY500; and
- source disposition: native RETAIN versus intervention RETIRE.

RETIRE tests source-remnant retirement with exact recycling, not protection of an
unchanged pre-cut parent. The policy removes source activity, releases its
remaining material, interrupts its partner, opens space after admission, and
changes population accounting. Those are inseparable parts of this declared total
intervention. No pure informational-preservation, adaptation, replacement-
admission, BFF rescue, ecology, or organism claim is allowed.

## Pinned baseline

- upstream `15dad84da126a4f887ba945c23a13e89e827f067`;
- unchanged patches 0001–0005 plus environment-gated patch 0006;
- canonical 140-host frozen placement, 40×40 grid;
- global interaction and native vacancy admission;
- exact molecule + accessible-pool + waste conservation;
- initial free-pool multiplier 0, recycle decay 0.0005;
- `MUTATE 0`, 5,000 ticks, report interval 100; and
- lineage, material, scheduling, and boundary-transaction observation.

## Factor semantics

### Scheduling

Use unchanged SM-B001 `eligible_tick` mechanics:

- IMMEDIATE: `D=0`;
- DELAY500: `D=500`.

No LOCKED arm is included. Both scheduling levels were renewal viable and fully
exposed in SM-B001, but all SM-B002 controls are concurrent on new seeds.

### Source disposition

A **retirement-eligible transaction** is determined before intervention from a
native cleavage proposal and must satisfy all:

1. the child is nonempty and successfully placed using native vacancy admission;
2. the inferred material source and transferred suffix are independently verified;
3. cut offset is strictly positive;
4. native healing leaves that source with a nonempty full-buffer remnant; and
5. the source has not already been removed by native zero-length cleanup.

Admission is completed before retirement; the new retirement vacancy cannot fund
that same child's placement.

- **RETAIN:** unchanged native post-cleavage source and partner handling.
- **RETIRE:** after child placement, native healing, and native zero-length
  cleanup reach their stable state—but before `OpcodeCleaveSpatial` returns to
  generic opcode completion—atomically retire the extant material-source remnant.

The retirement adapter owns completion for that event and returns
`safe_append=false`, so generic completion never dereferences or appends a retired
source. It removes the source from whichever current/next list and grid currently
owns it, returns every non-NUL full-buffer byte (including hidden tails) to the
accessible pool exactly once, and marks intervention retirement rather than
native decay. Any extant nonsource partner is unbound and appended to `nexthead`
exactly once after the already placed child, in native survivor state. If that
survivor is the active executor, increment its completed-execution counter exactly
once before unbinding; if native cleanup already removed the nonsource partner,
there is no survivor to preserve or append. No freed pointer is subsequently read.

Whole-parent transfers, failed placements, zero-offset cuts, empty/source-removed
outcomes, and unknown-source events are never eligible. Unknown or ambiguous source
attribution on a successfully placed apparent partial transfer is an integrity
failure, not a diagnostic exclusion. Retirement uses no RNG. It never reuses an
ID, changes child ID/buffer/cell/eligibility, or retroactively changes admission.
Disabled/RETAIN patch-0006 output and final RNG must be byte-exact with patch 0005
for corresponding scheduling arms.

## Journals and replay

Extend the ordered boundary transaction with proposal, admission, stable suffix
transfer, source inference, source-remnant bytes, retention/retirement decision,
partner unbinding, retirement material return, list/grid transition, and child
eligibility. Extend the material journal with a distinct `RETIRE` event and
counter; do not increment native decay or waste-routing counters.

Independent replay must prove:

- exact source/suffix/remnant attribution from full buffers;
- child placement precedes retirement;
- full retirement return reaches the accessible pool once;
- nonsource partner survives/unbinds/schedules once;
- child identity and scheduling policy are unchanged;
- no dangling bound pointer, duplicate list entry, omitted hidden byte, double
  refund, source retirement on an ineligible edge, or admission from the new
  vacancy;
- an independently reconstructed bijection: every eligible RETIRE transaction
  commits exactly once and every ineligible transaction commits zero times; and
- per-symbol molecule + pool + waste residual remains exactly zero.

Once native cleavage has committed, any eligible retirement failure, incomplete
journal, or partial intervention commit is fatal and makes the run unevaluable;
there is no RETAIN fallback.

Preserve and link the ordered `CLEAVE -> BIRTH -> RETIRE/death -> COMPLETE`
projection and the intermediate full-buffer state used for suffix inference. The
historical H001 analyzer may assign event-local **pre-retirement H001 diagnostic
credit** before the linked retirement; report it under that explicit name only.
Do not describe it as source-surviving RETIRE reproduction or use it for RETIRE
viability. The composite transfer endpoint below is authoritative, and retirement
has a separate exact per-symbol pool reconciliation.

## Transfer lineage

Freeze a separate **qualifying nonrelocation transfer edge** when a successfully
placed child received a nonempty suffix at positive cut offset from a known source,
the source had a nonempty native post-cut remnant immediately before any RETIRE
intervention, and the edge is not a whole-parent transfer. RETAIN and RETIRE use
the same pre-intervention qualification.

Initial molecules have nonrelocation transfer depth zero. A rooted qualifying
child receives `source_nonrelocation_depth + 1` only when its source has defined
nonrelocation depth. An otherwise eligible edge from an undefined-depth source is
an orphan edge: its child has undefined nonrelocation depth and it contributes to
no qualifying-transfer, renewal, serial, late, retained-late, or depth endpoint.

Whole-parent transfers are tagged relocation edges and may propagate a separate
relocation depth, but never assign nonrelocation depth. Any later partial transfer
from a relocation/orphan descendant remains orphaned rather than reconnecting to
the rooted lineage.

A **transfer-renewing descendant** is a rooted qualifying noninitial child with
positive defined depth that later serves as source of another rooted qualifying
edge. A **serial transfer** is a rooted qualifying edge whose source has defined
positive depth. A **late transfer-renewing descendant** is rooted, was born at
tick ≥2,500, and later sources a rooted qualifying edge. First-source positional
retention and retained-late rules remain H001's ≥0.90 and birth length ≥32.

A run has **transfer renewal with continuity** when all hold:

1. qualifying nonrelocation transfers ≥100;
2. transfer-renewing descendants ≥10;
3. serial transfers ≥50;
4. maximum nonrelocation transfer depth ≥2;
5. late transfer-renewing descendants ≥5; and
6. retained late transfer renewals ≥5.

An arm is **transfer viable** when at least 16/20 runs satisfy that conjunction.
Population increase and source survival are reported separately and are not
smuggled into this transfer endpoint.

## Matrix

Run 20 matched unseen seeds `202628000`–`202628019` in four arms:

1. IMMEDIATE_RETAIN;
2. DELAY500_RETAIN;
3. IMMEDIATE_RETIRE; and
4. DELAY500_RETIRE.

There are 80 runs. Use at most six workers and `NUMBA_NUM_THREADS=1`; retain every
run. No resume, replacement, selective retry, horizon extension, or policy change.

A RETIRE run has **application exposure** when at least 100 retirement-eligible
transactions occur and at least 100 are atomically retired. A retirement arm is
exposure-valid when at least 16/20 runs meet this rule. Eligibility is defined
before intervention, but recursive transaction count remains treatment-dependent.
Exposure failure does not erase valid total-policy outcomes.

## Endpoints

Report per run and matched pair:

- all H001 and SM-B001 native metrics;
- retirement proposals, eligibility, commitments, fatal enforcement errors, source role,
  remnant length/histogram, and returned material;
- qualifying transfers, transfer-renewing descendants, serial transfers,
  nonrelocation and relocation depths, late/retained renewal;
- source survival, repeat production, child participation and subsequent source
  activity;
- births, retirements, native decays, occupancy, final population, extinction,
  pool/waste routing, scarcity blocks, and net population change; and
- sequence/length diversity and first-source retention.

The population run is the unit. Report all ties and extinctions. Conditional
per-transfer rates are diagnostics; primary conclusions use arm-level 16/20 gates
and paired run-level outcomes.

## Prelaunch gates

1. fresh-build patches 0001–0006 and pass all inherited upstream, conservation,
   decay, renewal, perturbation, replicated, mutation, and scheduling suites;
2. byte-exact disabled/RETAIN output and final-RNG parity for both schedules;
3. directed active/passive source, partial/zero/whole cut, hidden-tail, failed
   placement, source-already-empty, both list states, and partner-preservation tests;
4. atomic fault-injection tests at every retirement step with no partial commit;
5. exact material/source/boundary/transfer replay and adversarial wrong-source,
   double-refund, admission-order, ID-reuse, dangling-pointer, and counter tests;
6. deterministic repeats and observer isolation in all four arms;
7. prove all 80 configs differ only by frozen schedule/disposition factors and
   have identical initial bytes, matter, positions, chemistry, and horizon;
8. synthetic exposure, transfer-lineage, relocation exclusion, retention, 16/20,
   4/20, interaction, and all decision boundaries; and
9. commit/push implementation, directly verify exact bytes on `origin/main`,
   repeat held-out seed audit, and prohibit resume artifacts.

## Integrity and concurrent controls

All 80 runs must pass process, artifact, exact ordered journal replay, per-symbol
conservation, nonnegative ledgers, identity/source/transfer DAGs, boundary/list/
grid transitions, scheduling, snapshot, counter, schema, alphabet, bounds, and
END-state checks with zero boundary errors.

Both concurrent RETAIN controls must reproduce viability:

- IMMEDIATE_RETAIN transfer viable ≥16/20;
- DELAY500_RETAIN transfer viable ≥16/20.

A valid RETAIN control failure is terminal and is not repairable by rerunning.
Integrity defects alone permit repair and unchanged full-matrix rerun.

## Frozen decision ladder

Apply strict precedence: integrity -> concurrent RETAIN controls -> both RETIRE
exposure gates -> response classification.

1. **Unevaluable integrity:** repair only demonstrated implementation/artifact
   defects and rerun the unchanged complete matrix.
2. **Valid concurrent-control failure:** either RETAIN control is nonviable. Stop
   without interpreting RETIRE biologically or rerunning.
3. **Inadequate retirement exposure:** either RETIRE arm has fewer than 16 exposed
   runs. Retain total-policy outcomes but make no calibrated retention response or
   admission-stage continuation.
4. **Retention not required across schedules:** both RETIRE arms transfer viable
   (≥16/20). Source-remnant survival is not required for robust transfer renewal
   under either tested schedule. Not equivalence.
5. **Immediate-only retention dependence:** IMMEDIATE_RETIRE passes at most 4/20,
   DELAY500_RETIRE is viable, and the same at least 16 immediate pairs pass RETAIN
   but not RETIRE. Report a schedule-dependent retention effect; do not infer a
   statistical interaction from thresholds alone.
6. **Delayed-only retention dependence:** symmetric rule: DELAY500_RETIRE ≤4/20,
   IMMEDIATE_RETIRE viable, and the same ≥16 delayed pairs pass RETAIN only.
7. **Strong retention dependence across schedules:** both RETIRE arms ≤4/20 and
   each schedule has the same ≥16/20 pairs passing RETAIN but not RETIRE. Source
   remnant retention is required for robust fixed-horizon transfer renewal under
   both tested schedules and declared recycling policy.
8. **Intermediate response:** exposure-valid RETIRE results not matching branches
   4–7. Report arm and paired magnitudes without binary necessity/generalization.

Branches 4–8 complete the source-disposition response classification. They
authorize separate prospective design—not execution—of admission replacement only
because integrity, both RETAIN controls, and both RETIRE exposure gates have
already passed by precedence. Threshold categories are not a formal statistical
interaction test. Any later admission experiment must validate actual replacement
opportunity and distinguish transmission from population expansion.
