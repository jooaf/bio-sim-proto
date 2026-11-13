# SM-B003 interpreter integration — work in progress

User instruction: “continue until integration and independent replay pass. once
done run experiments.” This authorizes proceeding after the gates, not bypassing
mechanics, replay, development qualification, final preregistration or seed audit.
B002 remains closed; BFF remains NO-GO. No SM-B003 population assay has run.

## Current candidate

`experiments/stringmol/native/admission_adapter.h` and
`experiments/stringmol/native/admission_integration.patch` wire admission into the
actual interpreter in `/tmp/sm/a7-dev`. The patch includes the eviction ledger;
do not also apply `eviction_ledger.patch`. Copy the three admission headers into
`src/` when applying to a fresh patches-0001–0006 baseline. `/tmp/sm/a7` remains
unchanged. This is development source, not a sealed launch revision.

The adapter samples the two categories, flushes BEGIN, stages replacement, emits
EVICT/material/death/lineage before releasing the victim, delegates source healing
to the inherited opcode, and emits RESOLVE only after scheduling COMPLETE. Failed
placement still uses inherited native healing. Proposal allocations and detached
victims have explicit temporary owners; transfer/free clears ownership. Fatal
prefixes remain owned rather than orphaning allocations or rewinding IDs/RNG.

## Findings from actual integration

- Native bound dispatch may append to NEXT while retaining grid flag G_NOW.
  Grid flags are not list ownership; validate actual lists and preserve flags.
- Native AgentMake leaves `set` indeterminate before placement. Initialize it for
  the new proposal path before saving a rollback baseline.
- Dormant unbound/passive VM head slots can be indeterminate. Only active VM heads
  are meaningful inbound references; do not inspect dormant storage as pointers.
- ASan identified the `%2000s` matrix-label destination as 2000 rather than 2001
  bytes. The candidate provides the terminating-byte capacity.
- The default-table helper omitted freeing its final allocated scratch row.
  The base bucket destructor also omitted its table header and two owned arrays.
  Candidate repairs are teardown/storage-only and still need disabled/native
  parity qualification. No sanitizer suppression has been added.
- Copying object directories can make object timestamps newer than edited source.
  Build-v3 did **not** rebuild and is not qualification. Subsequent builds use fresh
  output directories and forced `make -B`. All attempts remain retained.

## Completed development checks

`verification/sm-b003-interpreter-suite-v2/` on Elements records **1,358 passing
ASan/UBSan tests**: 206 component cases plus 1,152 actual
`ReactionExecuteOpcode_Spatial` cases. These cover three policies, two schedules,
both sources, zero/partial/end cuts, hidden material, NOW/NEXT incumbents, sparse,
full and protected grids, and two synthetic RNG fixtures. Full final native MT
states match an independent straight-line draw consumer. Real native source
healing, material reconciliation, scheduling joins and admission framing pass.

`verification/sm-b003-native-witness-v1/` records **56 passing native fault cases**.
Link-time witnesses observe state at the throw, before stack unwinding, and again
at fatal exit. Five mutation checkpoints restore the captured post-proposal state
without rewinding RNG or IDs. Nine publication/completion boundaries preserve
irreversible state and enforce exactly-once victim freeing. Incomplete journals
are rejected, even when RESOLVE was emitted but END was not.

These directed fixtures are not complete population histories. Initial synthetic
late-eligibility victims are deliberately injected after scheduling initialization.
No biological endpoint or exposure denominator may be computed from them.

## Configuration-loader repair and complete-loop qualification

The complete simulator exposed another `%2000s`/2000-byte destination mismatch
in `stringPM::load_table`. The candidate removes two unused label scans, gives
the token buffer terminator capacity, rejects missing filenames and filenames
that cannot fit `swt_fn`, and checks the MIS alphabet scan. Boundary tests cover
missing, 80-byte and 2000-byte filenames for both directives, plus a valid
79-byte filename.

Further sanitizer runs identified overwritten, unowned initial parent records
and alignment-cache nodes allocated into a pass-by-value local head. The
candidate avoids both allocations; it does not enable previously ineffective
alignment caching or change RNG consumption. Full-loop tests also corrected the
fixture's lineage environment name to `STRINGMOL_LINEAGE_LOG`.

`verification/sm-b003-full-plumbing-v4/` records 13 passing loader/full-loop
checks. `verification/sm-b003-loader-regression-v1/` records **1,963 passing
ASan/UBSan tests** in 226.02 seconds and strict typing across four Python files.
This includes 216 directed observer/disabled parity cases and six complete-loop
policy/schedule cases. Native-policy scientific CSVs and full final RNG state
match the unmodified patches-0001–0006 reference (ordinary build); other policies
match with observation on/off. The full-loop fixture is three synthetic agents
for three ticks, not a population assay. Failed v1–v3 plumbing attempts remain
retained. The pinned baseline was not modified.

## Independent material and transaction replay hardening

`admission_material.Replay` now validates its initial buffer size, identity map,
per-symbol vectors and total conservation independently, and copies the initial
state so callers cannot change its reference accounting. A rejected material
row or checkpoint makes that replay permanently unusable. Dedicated eviction
returns and counts are bounded independently of decay and source retirement.

`check_transaction` joins BEGIN/RESOLVE to the independently supplied pre-opcode
state and ordered material events. It reconstructs source healing, the exact
child sequence, active-first cleanup, victim removal, complete post-operation
buffers and NOW/NEXT queue order. It also reconciles material indices and the
separate eviction ledger. Checks run on a trial copy; failed joins never publish
partial state to the caller.

Evidence on Elements:
- `verification/sm-b003-material-joined-v1/`: 1,479 passing tests, including all
  1,440 real-opcode fixture cases under ASan/UBSan, 31 material tests and eight
  selected native fault tests. A subsequent typing-only narrowing was required.
- `verification/sm-b003-material-adversarial-v2/`: 40 passing tests and strict
  typing over three files. Nine native-journal corruptions include an incorrect
  child sequence with unchanged histogram: accounting alone accepts it, while
  the joined reconstruction rejects it. Other corruptions alter victims, time,
  queue order, ledgers, event multiplicity, indices and source identity.

These are transaction-local checks against independently constructed fixture
state. They do **not** reconstruct that state across a whole population history,
prove all VM/RNG transitions, or certify lifecycle/ancestry joins. Task 17 and
population launch remain open; no criteria or scientific outcomes were changed.

## Whole-history reconstruction now under qualification

New independent modules: `admission_numeric.py` (pinned 69069-seeded MT and
binary32/tie-exact alignment), `admission_vm.py` (head-state/opcode interpreter),
`admission_boundary.py` (ordered scheduling/lifecycle reconstruction),
`admission_source.py` (replacement-only ancestry), and `admission_replay.py`
(the complete joined verifier). None modifies frozen B002 analysis.

VM heads initialize from independently computed binding alignment, not claimed
DISPATCH or BEGIN fields. The verifier derives initial queue permutation,
selections, decay, partner ranks, binding, opcode effects, proposal bijections,
admission draws/targets, child allocation IDs, source healing, full buffers,
grid/list ownership, species/lineage events, source transactions, checkpoints and
full final MT state. An observer-only terminal VM witness closes the last-head
observation gap; see `sm_b003_terminal_vm_witness_addendum.md`.

- `verification/sm-b003-boundary-v1/`: 20 scheduling/native-plumbing checks passed;
  a type annotation was subsequently corrected.
- `verification/sm-b003-ancestry-v1/`: 18 boundary/ancestry checks passed, including
  delayed-child eviction, both victim queues, no reconnection through a vacancy
  edge, and retention frozen at the first source event across all channels.
- `verification/sm-b003-vm-replay-v2/`: 30 checks passed: full 624-word MT states
  across two twist boundaries/four seeds, 133 native alignment comparisons, and
  six tiny full-loop joined replays.
- `verification/sm-b003-vm-program-v1/`: six 600-tick mechanical runs passed full
  independent replay and observer/native parity. Each had two nonempty proposals;
  both replacement arms had one verified occupied-cell partial replacement.
  These fixtures use three initial agents, a 3x3 grid and a 128-unit uniform pool,
  deliberately **not** the frozen zero-pool population assay.
- `verification/sm-b003-whole-adversarial-v3/`: 26 checks passed (14 whole-history
  corruptions and 12 tiny/program full-loop cases), including terminal-head/grid
  checks. A same-byte wrong instruction head passes the simpler boundary replay
  but fails independent VM reconstruction. Coherent-looking missing proposals
  and one-bit draw changes pass framing but fail the joined verifier.

`verification/sm-b003-integrated-replay-v4/` passed **2,116 sanitizer tests**,
including the expanded second-seed, decay/early-extinction and terminal-witness
I/O cases. `sm-b003-replay-unit-v1/` passed 61 focused tests after removing an
overstrict conditional-read span check: native `strncpy` stops at the reserved
NUL and pads even if its requested length extends past the remaining source
allocation. Full inherited regression and canonical-population qualification
remain open. Task 17 is not yet closed. Development-only population exposure/resources, final preregistration,
unseen-seed audit and sealed launch eligibility remain mandatory. No SM-B003
frozen population matrix has launched.

Failed builds/runs are retained under `verification/sm-b003-integration-build-*`,
`sm-b003-interpreter-*`, and `sm-b003-native-fault-*` on Elements; corresponding
native artifacts remain in fresh `/tmp/sm/` paths inside its external POSIX image.

## Development controller artifact failure and repair

The prospective panel is fixed in `sm_b003_development_qualification_plan.md`:
seed 202620999, six arms, 5,000 ticks, zero pool/mutation, 140 hosts; 20 native
executions including observer-off, exact repeats and two patch-0006 references.

Attempt v1 (`/tmp/sm/b3q1`, Elements `sm-b003-development-v1/`) completed all
20 native executions successfully. Maximum execution-plus-inventory time was
approximately 17.89 seconds. All observer/repeat/native scientific CSV and full
RNG comparisons passed before analysis. Its first two complete-history replay
processes exited zero, but their scientific JSON outputs were accidentally
replaced by the command logger's JSON receipts. The apparent repeat disagreement
was between command paths, **not evidence of a biological or replay mismatch**.
The overwritten scientific reports cannot count as retained qualification.
Keep the entire attempt, including raw data, resource logs and failed receipt.
The first analysis took about 270 seconds and peaked near 3.71 GiB resident RAM.

Repair: reserve command stdout/stderr/JSON with exclusive opens **before launch**,
use distinct `-process` names for command receipts, and retain partial logs and
structured receipts on timeout. Read-only permissions are not a substitute for
exclusive creation, particularly on this fakeroot mount. Controller v2 tests:
**22 passed**, typing clean across three files. Regression tests explicitly cover
pre-existing evidence, child/parent filename collisions, distinct scientific
outputs and timeout retention.

Use a separately named complete development attempt with the same fixed inputs;
no selective biological retry, seed search, or reserved-seed execution. Full
regression, development opportunity/replay, publication and final launch gates
remain open.
