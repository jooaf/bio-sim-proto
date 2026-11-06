# SM-B003 — prospective admission-replacement design

**Status: candidate design and executable reference specification, not launch authorization.**
No SM-B003 held-out assays have been executed. Native patch, ordered-journal replay,
exposure qualification, and final preregistration remain required. SM-B002 permits
this separate design; it does not authorize an admission experiment automatically.

## Evidence and scope

SM-B002-R2, source `f2eda7ed620aa2e6afc5c89b51b583e758a4f4f7`, completed all 80
runs and both independently checked analysis passes. Branch 8: intermediate
response. Continuity was 18/20 for each RETAIN schedule, 5/20 IMMEDIATE_RETIRE,
and 8/20 DELAY500_RETIRE; both retirement exposure gates passed. This is not a
binary necessity claim, a formal interaction result, or permission to rerun B002.
Artifacts remain in `Elements/bio-sim-results/sm-b002-r2/`.

The next question is whether rooted multigenerational transfer can pass through
**actual occupied-cell replacement**, rather than counting vacant-cell expansion
as evidence of replacement transmission. BFF remains closed; no BFF experiment,
ecological generalization, adaptation claim, or organism claim is proposed.

## Native audit and rejected shortcut

Pinned upstream remains `15dad84da126a4f887ba945c23a13e89e827f067`, patches 0001–0006.
In `sm_spatial.cpp`, `AgentPlaceInMooreNeighbourhood` with global placement scans
vacancies in x-major/y-minor order, draws once if any exist, and otherwise fails.
`OpcodeCleaveSpatial` subsequently heals the source even on failed placement;
conservation reconciles the discarded child suffix. Placement failure is not a
no-op. SM-B002 retirement occurs **after** admission and cannot establish occupied-
cell replacement opportunity. Native MT uniforms are in [0,1), scaled by 2^-32.

A vacancy-first, replacement-only-when-full adapter is rejected for this design:
140 initial hosts on 1,600 cells do not establish adequate full-grid opportunity.
Uniform sampling of every cell also leaves exposure hostage to occupancy and
binding state. Neither alternative has been tested as an admission assay here.
Instead, the candidate below deliberately supplies a fixed occupied-channel
challenge. This is a **stratified admission stress test**, not natural crowding.
The 1/2 probability is a prospective symmetric design choice, not a fitted value.
Do not tune it, density, horizon, or thresholds after held-out outcomes.

## Proposed factors and fixed background

Six arms: IMMEDIATE / DELAY500 crossed with:

1. NATIVE_VACANCY: unchanged native vacancy placement, concurrent positive reference.
2. STRATIFIED_REJECT: common target sampler below; reject an occupied target.
3. STRATIFIED_REPLACE: identical sampler; replace the eligible occupied target.

Keep source RETAIN in every arm. Do not carry the intermediate RETIRE response into
another factorial or claim preservation of an unchanged pre-cut parent. Preserve
canonical 140-host placement, 40×40 grid, global interaction/placement, mutation 0,
initial accessible pool 0, recycle decay 0.0005, 5,000 ticks, report interval 100,
exact symbol conservation and existing eligibility timing. Capacity is fixed;
occupancy is **not** clamped and vacancies are not filled artificially.

Provisional reservation: 20 matched seeds `202629000`–`202629019`, 120 runs. These
numbers are not certified unseen: an execution-aware archive/config audit and
final immutable manifest must precede launch. Documentation mentions are not
execution evidence. Development uses only existing seed 202620999 and synthetic
mechanical fixtures, never the reserved population matrix. At most six native
workers; direct Elements exFAT raw I/O and POSIX-image control seals as in R2.
Operational deadlines and complete-matrix artifact-recovery policy must be frozen
in the final preregistration after development performance qualification.

## Common target sampler (before source healing)

For each staged **nonempty** child proposal, reconstruct the pre-admission grid,
full buffers, binding relations, current/next lists and active/passive participants.
Enumerate two candidate sets in x-major/y-minor order:

- VACANT: currently empty cells;
- OCCUPIED: cells containing an unbound, visibly nonempty molecule, excluding both
  current participants. A bound molecule, including a delayed child's later bound
  state, is not eligible. An unbound delayed child **is** eligible regardless of
  eligibility tick. No infant protection is added. Empty-visible/hidden-only live
  molecules are excluded as victims, not treated as vacant cells.

STRATIFIED modes draw one native uniform: [0,1/2) selects OCCUPIED; [1/2,1) selects
VACANT. If that set is empty, placement fails: consume no rank draw, do not search
another set, and do not resample. Otherwise consume one more native uniform and
select `floor(u * candidate_count)`. REJECT consumes that rank draw even when it
will reject an occupied target. Only disposition of the selected incumbent differs
between REJECT and REPLACE. There is no random tie-breaking or retirement RNG.

NATIVE_VACANCY consumes only its original rank draw when a vacancy exists, and no
draw if none exists. It is a reference for concurrent native viability, not a
same-RNG-stream control for stratified sampling. Matched seeds do not imply coupled
trajectories after treatment divergence. Disabled/NATIVE mode must reproduce all
old native outputs and final RNG; an enabled observer may add only its new journal.

## Transaction, ownership, and material contract

Replacement is not a call to native decay (which can also kill a bound partner),
and must not use the SM-B002 post-admission RETIRE adapter as a substitute.

Native child allocation/species bookkeeping and sampler draws form an already
committed proposal prefix. The new rollback baseline is **after** that prefix,
before victim/list/grid/pool mutation; no failure is described as erasing the
proposal or rewinding its RNG. Before new irreversible admission publication,
stage the existing child bytes/ID, selected victim, all affected list/grid nodes,
source healing/cleanup effects, full victim
histogram, pool/counter additions and overflow checks. The victim must be extant,
unbound, distinct from both participants, uniquely owned by its grid cell and
exactly one current/next list, and have no inbound binding pointer. Reject stale,
ambiguous, duplicated, or inconsistent ownership as integrity failures.

Detach that victim once; return every non-NUL allocated-buffer byte, including
hidden tails, to the accessible pool exactly once; increment a distinct eviction
counter and return ledger, not decay/RETIRE/waste counters. Install the already
staged child in the same cell with its fresh ID and original scheduling semantics.
Never overwrite or reuse the victim ID or register victim ancestry. Victim material
cannot pay for creation/copying of this same child: those operations precede refund.
Complete the native source-healing/zero-length cleanup and completion contract once.

The composite journal must expose a causally linked replacement transaction,
eviction material/death, successful child admission, source healing/cleanup and
completion. Independent replay must reconstruct both before/after grid states and
all intermediate ledger effects, not trust a REPLACED label. A birth plus one
victim eviction has zero occupancy delta; native participant cleanup may make the
composite delta negative. No qualified replacement transaction may increase live
population. Ordinary vacancy births and native deaths remain separate.

Before new admission publication: injected failures restore the post-proposal
baseline, then terminate the run; never fall back to vacancy placement or retry a different victim. After any
journal/species publication: failure is fatal, with its prefix retained. No rollback
of published prefixes, double refund, silent rejection, or resumed transaction.
This contract still requires a native implementation and a fully specified journal
schema; the Python planner is not a proof of C++ atomicity.

## Opportunity, transfer, and endpoints

An admission opportunity is assessed from pre-intervention state: a nonempty child,
OCCUPIED channel, and eligible incumbent. A **partial opportunity** additionally has
a known source, positive cut offset, and an independently projected nonempty native
post-cut source remnant. Projection must use the VM/full-buffer state, not successful
admission or a logger flag. It is defined for REJECT too. Unknown source on an
apparent partial proposal is fatal, not an exclusion. In REPLACE every such eligible
opportunity must commit once; none may commit in REJECT or NATIVE.

A REPLACE run is exposed when partial opportunities and their verified commitments
are each >=100; an arm is exposed at >=16/20. Report opportunity and failure reasons
for **every** arm, including empty category, protected occupants, victim age/status,
and unchosen candidate-set sizes. Counts are recursively treatment-dependent;
conditional success rates are diagnostics, not unbiased causal effects.

Maintain the unchanged B002 all-admission, rooted nonrelocation transfer endpoint.
Separately reconstruct a **replacement-only** rooted DAG:

- Initial molecules have depth zero.
- Only a verified qualifying partial transfer admitted through actual replacement
  can extend a defined replacement-only depth.
- A vacancy-born child, whole-parent relocation, nonqualifying transfer, or child
  of an undefined-depth source has undefined replacement-only depth forever.
- Include all births; descendants cannot reconnect through a later replacement.
- The displaced incumbent is never the source or ancestor merely by displacement.

Apply the same six numerical continuity requirements, separately to each DAG:
>=100 qualifying transfers, >=10 renewing descendants, >=50 serial transfers,
depth >=2, >=5 late renewing descendants (born >=2500), and >=5 retained late
renewals (inherited >=0.90 positional retention and birth length >=32). Do not mix
all-admission depth/late counts into replacement-only continuity. Freeze first-source
retention at the first qualifying source event across **all** admission channels,
not a later favorable replacement event. Thus replacement-only retained renewals
remain a subset of the unchanged all-admission endpoint. Report births,
evictions, native cleanup/deaths, occupancy, population change, extinction,
material routing and all ties independently of both endpoints.

A replacement-only path excludes expansion on its **own admission edges**. It does
not prove a globally growth-free ecology: other vacancy lineages, recycling and
population changes may support it. No mortality-only or pure admission-information
claim is permitted; eviction, recycling and competitive removal form a total policy.

## Proposed decision precedence

Every run remains in its fixed 20-per-arm denominator; population runs, not births,
are experimental units. Preserve matched REJECT/REPLACE magnitudes and discordant
pairs for both schedules; no formal interaction test or necessity claim is proposed.

1. Any process/artifact/replay/ownership/material/identity/schema failure or missing/
   duplicate input: unevaluable integrity; do not evaluate biological categories.
2. Either concurrent NATIVE reference below 16/20 all-admission continuity: valid
   native-control failure, terminal for this assay; no rerun to improve controls.
3. Either REPLACE arm below 16 exposed runs: inadequate replacement exposure. Retain
   total-policy outcomes; do not claim a calibrated replacement-transmission test.
4. Both REPLACE arms achieve >=16/20 replacement-only continuity: robust replacement-
   only transmission under both tested schedules and the declared stress policy.
5. Only IMMEDIATE meets 16/20: robust under the immediate schedule only.
6. Only DELAY500 meets 16/20: robust under the delayed schedule only.
7. Neither meets 16/20: robust replacement-only continuity not established.

Categories 5–7 are not statements of universal necessity or equivalence. All valid
categories are retained; none permits selective reruns, endpoint relaxation, tuning
until success, or reopening BFF. Additional questions require separate prospective
design. No category grants automatic downstream experimental authorization.

Native integration details and completed selector/RNG qualification are recorded
in `reports/sm_b003_admission_native_integration_notes.md`. The selector corpus
validates neither eviction atomicity nor population-level exposure.

## Launch prerequisites still outstanding

- New environment-gated native adapter and versioned journal schema, separately
  reviewed for staged versus irreversible publication and full-buffer reconciliation.
- Directed active/passive source, vacancy/full/protected grids, both list states,
  hidden-tail victim, zero/whole/partial cut, source cleanup, delayed child victim,
  empty candidate sets, exact channel/rank boundaries, ID exhaustion and pool overflow.
- Fault injection at every mutation/publication boundary; no use-after-free,
  dangling pointer, duplicate list entry, duplicate death or refund.
- Independent ordered admission/material/source replay plus adversarial altered
  target/RNG/candidate counts, wrong victim, false eligibility, wrong pool recipient,
  deletion of eviction evidence, and false replacement-only reconnection tests.
- Native exact parity and deterministic repeats; observer isolation for every arm;
  verify native RNG consumption with actual pinned generator state, not just counts.
- Development-only opportunity/performance qualification. Report failures honestly;
  do not silently fill cells or change victim rules to create exposure.
- Full inherited regression, complete-matrix config identity and held-out execution
  audit, frozen final preregistration and source publication, disk headroom checks,
  independent repeat analysis/export and explicit final launch eligibility.
