# SM-B001 offspring scheduling-delay ablation

**Frozen before implementation:** 2026-10-04

## Question and scope

Does canonical Stringmol reproductive renewal require offspring to become
independently reaction-eligible immediately after physical cleavage and vacancy
admission, or does renewal remain robust after a fixed 500-tick delay?

This is the first staged birth-boundary intervention authorized by SM-M001. It
isolates **reaction scheduling latency** while retaining a separate child buffer,
identity, spatial cell, native source healing, and vacancy admission. It does not
test a product retained inside its parent, exact pre-cut parent preservation,
replacement admission, adaptation, or the closed H003 panel-heredity claim.

A permanently locked arm is a directed mechanics/upper-bound control: its lack of
descendant participation is imposed and is not evidence that its products lack
latent reproductive competence.

## Why not a nominal 2×2×2

Separation, parent preservation, and admission are not mechanically orthogonal
under exact conservation. A nonseparate product has no independent admission;
preserving pre-cut source bytes while also creating the child requires an
explicit material debit; replacement changes occupancy and population-growth
semantics. SM-B001 therefore freezes the smallest interpretable contrast first.
Parent disposition and admission require separately gated experiments and a new
boundary journal extension.

## Pinned baseline

- upstream `15dad84da126a4f887ba945c23a13e89e827f067`;
- unchanged patches 0001–0004 plus one environment-gated patch 0005;
- 140 canonical 64-byte hosts at frozen positions;
- 40×40 grid, global interaction and vacancy placement;
- exact molecular + accessible-pool + waste conservation;
- free-pool multiplier 0, recycle decay 0.0005;
- `MUTATE 0`, validated viable by SM-M001;
- 5,000 steps, report interval 100; and
- lineage, material, and boundary-scheduling observation enabled.

## Intervention semantics

Patch 0005 adds an `eligible_tick` to every molecule and changes no byte-transfer,
cleavage, healing, placement, decay, or material-routing operation.

At every successfully placed cleavage child:

- preserve fresh child ID, complete `maxl0` buffer, spatial cell, unbound status,
  next-list insertion, and native birth/material events;
- set `eligible_tick = birth_tick + 1 + D` with checked integer arithmetic;
- initial molecules have `eligible_tick = 0`;
- the policy applies recursively to every later child.

Arms:

1. **IMMEDIATE:** `D=0`; native next-tick eligibility.
2. **DELAY500:** `D=500`.
3. **LOCKED:** no eligibility before END, represented by a checked sentinel above
   5,000 rather than overflow arithmetic.

A molecule before `eligible_tick`:

- remains in normal population, occupancy, identity, snapshot, material, and
  native unbound-decay accounting;
- remains in ordinary top-level random molecule selection;
- receives its native decay attempt first and, if it survives, is appended to the
  next list exactly once without seeking a partner;
- cannot seek a reaction partner or be selected as one; and
- receives no material refund, extra energy, extra execution, rebinding, or
  release bonus.

Partner candidates are filtered for eligibility **before** counting and the one
native partner-selection draw; eligible candidates retain native list order and
uniform selection semantics. There is no reject/redraw loop. At tick start,
`timestep >= eligible_tick` makes the child eligible before its processing and
decay. It then follows the unchanged native reaction path. No explicit release RNG
draw occurs. A delayed child that decays first never releases, and a child cannot
be bound before eligibility.

The intervention preserves the native decay routine, not matched realized decay
exposure: native selected partners do not receive a separate decay trial that
tick, so preventing binding can change later decay opportunities. Mortality,
encounter, and occupancy changes are included in the total scheduling-policy
effect.
When the patch is absent, policy is disabled, or `D=0`, all preexisting output
files and final RNG state must be byte-identical to patch-0004 native output. The
new boundary journal is observation-only and may be enabled for all three arms.

## Boundary journal

Add an append-only ordered journal for every policy-born child's scheduling
lifecycle. It records:

- birth: child ID, birth tick, eligible tick, policy, source/active/passive IDs,
  and successful-placement transaction index;
- each top-level processing selection, eligibility state, and decay/survival
  outcome;
- each seeker search and its no-candidate or selected-candidate outcome;
- each encounter with both IDs, roles, candidate-set size, selected index, and
  binding outcome;
- each bound-pair dispatch with active/passive IDs and opcode/material-event link;
- death, deterministic eligibility transition, and END censoring.

A **reaction participation** is a selected two-molecule encounter in either seeker
or selected-partner role, regardless of binding success. Seeker searches with no
candidate are opportunities but not participation; successful binding and opcode
dispatch are reported separately. First participation is derived from this stream,
not directly logged as a summary. Any pre-eligibility encounter, binding, or
dispatch involving a policy-born child is both a runtime-fatal boundary error and
an independent replay failure.

Final states are: decayed before eligibility; alive but not yet eligible at END;
eligible but never encountered; encountered but never bound; bound but never
dispatched; or dispatched. ZERO participation in LOCKED applies only to
policy-born children, not initial molecules.

Observation adds no RNG draws and does not alter labels or mechanics. Cross-check
child births against native lineage and material journals, identities, snapshots,
and decay events. The journal does not redefine historical `BIRTH`.

## Matrix

Use 20 matched unseen seeds `202627000`–`202627019` in all three arms: 60 runs.
Use at most six workers and `NUMBA_NUM_THREADS=1`. All runs remain in the
denominator. No resume, replacement, selective retry, horizon extension, or delay
change is permitted.

The 500-tick delay is frozen as 10% of the horizon. With ticks ending at 4,999,
a child born at the existing late boundary 2,500 becomes eligible at 3,001 and
has at most 1,999 eligible processing ticks. No pilot on these seeds or adaptive
delay selection is allowed.

## Endpoints

Retain all native birth, H001 productive-source, source-lineage, renewal,
retention, conservation, and SM-M001 sequence endpoints unchanged.

Additionally report per run:

- policy births and successful physical child placements;
- children surviving to eligibility;
- children decaying before eligibility;
- eligible children with and without later participation;
- first-participation latency and role;
- released children that later become verified productive material sources;
- material-transfer lineage: every verified placed suffix transfer gives the
  child transfer depth `source_depth + 1` from initial depth zero; whole-parent
  transfers are tagged relocation edges and may propagate transfer depth but are
  excluded from nonrelocation serial-transfer and renewal counts; unknown-source
  children remain orphaned and cannot seed qualifying depth;
- nonrelocation serial transfers, transfer depth, relocation-chain depth, and
  source-remnant survival, all separately from unchanged H001 productive lineage;
- child/source survival, whole transfers, placement failures, occupancy, decay,
  and full-buffer material routing.

A DELAY500 run has **policy application exposure** when at least 100 successfully
placed delayed children have `eligible_tick < 5000`, regardless of later survival
or participation. The treatment is application-exposed when at least 16/20 runs
meet this criterion. This verifies repeated policy application using the nominal
horizon without conditioning on each child's later survival or participation;
recursive birth count remains a treatment-dependent exposure classification.

Separately, a run has **adequate post-release response exposure** when at least 100
children survive to eligibility and at least 50 distinct released children later
participate in an encounter. Report the number of runs meeting it. It gates only
post-release competence language and later-factorial design, never the total
fixed-horizon treatment effect.

LOCKED must record zero encounters, bindings, and dispatches involving policy-born
children. Its count of physical placements is a diagnostic biological output, not
an integrity or positive-control threshold.
Use unchanged H001 renewal core and continuity criteria. An arm is **renewal
viable** when at least 16/20 runs pass renewal with continuity.

For each matched seed report IMMEDIATE-minus-DELAY500 differences in productive
source births, renewing descendants, serial source births, depth, late renewal,
retained late renewal, survival, and sequence endpoints. Do not treat children or
births as experimental units.

## Prelaunch gates

1. fresh-build patches 0001–0005 and pass upstream, isolation, lineage,
   conservation, recycling, renewal, perturbation, replicated, and mutation suites;
2. directed active-source, passive-source, partial-cut, whole-transfer,
   failed-placement, hidden-tail, child-decay, exact eligibility boundary, both
   partner-selection directions, and recursive-child fixtures;
3. exact disabled/zero-delay shared-output and final-RNG parity against patch0004;
4. deterministic repeats for all policies;
5. independent boundary-lifecycle plus material replay, including adversarial
   early participation, missing child, duplicate release/participation, ID reuse,
   and plausible-but-wrong source attribution;
6. prove all 60 configs differ only by policy/delay and have identical initial
   matter, positions, hosts, mutation, decay, horizon, and environment otherwise;
7. synthetic 16/20 viability/exposure and 4/20 sensitivity boundaries plus all
   decision branches;
8. commit/push implementation, directly observe exact bytes on `origin/main`,
   repeat held-out seed audit, and prohibit resume artifacts.

Any mismatch stops before assays. Mechanics, delay, thresholds, endpoints, and
seeds are frozen under this ID.

## Integrity and controls

All 60 runs must pass process, inventory, complete ordered material replay, exact
per-symbol conservation, nonnegative ledgers, identity/source DAGs, boundary
scheduling replay, suffix transfer, snapshot, counter, schema, alphabet, bounds,
and END-state checks with zero boundary errors.

IMMEDIATE is the concurrent biological positive control. LOCKED zero policy-child
encounters/bindings/dispatches is an enforcement/integrity requirement; its
physical-placement count is diagnostic only. DELAY500 application exposure and
post-release response exposure are classified by the decision ladder rather than
silently excluding runs.

## Frozen decision ladder

After integrity and controls:

1. **Unevaluable integrity:** process, replay, conservation, or enforcement
   failure. Repair only demonstrated implementation/artifact defects, retain the
   failed record, and rerun the unchanged complete matrix.
2. **Valid positive-control failure:** integrity passes but IMMEDIATE is not
   renewal viable. Stop; do not rerun or interpret DELAY500 biologically.
3. **Delay-robust renewal:** IMMEDIATE passes, DELAY500 is application-exposed and
   renewal viable (≥16/20). Immediate scheduling within 500 ticks is not required
   for robust renewal under this condition. This is not equivalence.
4. **Strong fixed-horizon delay sensitivity:** IMMEDIATE passes, DELAY500 is
   application-exposed, DELAY500 passes continuity in at most 4/20, and the same
   at least 16/20 pairs pass IMMEDIATE but not DELAY500. The total 500-tick
   scheduling policy—including downstream mortality, encounter, and occupancy
   changes—causally disrupts fixed-horizon renewal. Do not claim unrestricted
   necessity of immediate scheduling.
5. **Intermediate delay response:** IMMEDIATE passes, DELAY500 is application-
   exposed with 5–15 continuity passes or without the strong paired conjunction.
   Report magnitude and ties; make neither robustness nor strong-sensitivity
   claim.
6. **Inadequate application exposure:** IMMEDIATE passes but fewer than 16/20
   DELAY500 runs have at least 100 applied children with `eligible_tick < 5000`.
   Retain the valid total policy outcomes but make no calibrated delay-response or
   continuation claim.

LOCKED enforcement is an integrity requirement; low LOCKED birth/placement count
is reported without changing these branches. Adequate post-release response
exposure controls only claims about behavior after release.

Branches 3–5, and only those branches, authorize **separate preregistration** of a
scheduling × source-remnant-retention experiment when all integrity/LOCKED gates
pass. Both scheduling levels need not be renewal viable. If DELAY500 has a floor
response or inadequate post-release response exposure, the new preregistration
must address that floor prospectively and may not interpret a missing interaction
as source-retention irrelevance. Replacement admission remains later and requires
prospective exposure validation. No result alone explains the Stringmol–BFF
contrast; that requires a BFF-derived rescue under matched declared mechanics.
