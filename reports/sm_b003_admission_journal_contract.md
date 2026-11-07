# SM-B003 admission journal v1 and publication contract

**Wire version:** `SM-B003-ADMISSION-1`

**File:** `admission_events007.csv`

**Status:** frozen implementation contract before native adapter implementation;
not a final assay preregistration or launch certificate.

Authoritative column order is `admission_journal.COLUMNS`. Values are ASCII tokens,
comma-separated, no quoting/embedded separators, LF including the final LF. Blank
means absent, never zero or -1. Integers are canonical nonnegative decimals; actor
IDs are signed-int-range nonnegative values; counters are at most 2^63-1. Full
buffers are uppercase hex of exactly 2,001 bytes, including hidden tails and the
reserved trailing NUL. Vectors contain 33 semicolon-separated counts in ALXII order.
Queue IDs are semicolon-separated in **actual queue order**, never sorted.
Rows are bounded to 65,536 bytes, enough for the complete 40×40 queue population
and the three full buffers. Unknown columns, extra payload, noncanonical text,
truncation, and oversized records are fatal.

## Common metadata and event sequence

Every row repeats version, policy, schedule, fixed horizon, dimensions, buffer size
and `source_disposition=RETAIN`. Compare these to an independently sealed input,
not metadata inferred from the same journal. Row indices start at one and are
contiguous. Ticks are nondecreasing. The only valid sequence is:

`START, (BEGIN, RESOLVE)*, END`

Transactions start at one and are contiguous. START/END use transaction zero.
There is at most one pending transaction. A dangling BEGIN, absent END, extra row
after END, duplicate resolution, or nonzero process exit makes the run unevaluable.
An early END is valid only for extinction, and must match all inherited END states.
Do not extend an extinct run artificially to manufacture a 5,000-tick endpoint.

`material_index`, `boundary_index`, `now_ids`, `next_ids`, and `population` describe
state at that event. The boundary index joins the existing scheduling journal:
START -> scheduling START; BEGIN -> DISPATCH of `%`; RESOLVE -> COMPLETE;
END -> scheduling END. Those records must match tick, participants and material
index. BEGIN/RESOLVE indices are not arbitrary monotonic labels.

## BEGIN: committed proposal prefix, before victim mutation

A BEGIN exists exactly for each staged nonempty child proposal, whether admission
will succeed or fail. Independent VM and full-buffer replay must enumerate these
proposals, including FAILED placements; matching only the entries that happened
to be logged is insufficient. No-change/empty-cleavage dispatches have no BEGIN
and must independently be shown to have no nonempty proposal.

The existing native child allocation, ID consumption, species bookkeeping and
executor-biomass reset occur before placement. Sampler draws then occur. These and
the flushed BEGIN are a committed **proposal prefix**, not rollback state to erase.
Rollback begins after that prefix and before victim/list/grid/pool mutation. A
prepublication injected failure restores that post-proposal baseline and terminates
fatally. It does not rewind RNG, reuse the child ID, unpublish species, retry a
victim, or continue as a rejected placement.

BEGIN records:

- active/passive/source IDs, flow offset and proposed child ID;
- full source and staged child buffers (child is the visible suffix, zero-padded;
  hidden source bytes are not copied into it);
- both candidate-set counts and selected channel;
- the channel/rank uniforms as **16 uppercase hex digits of IEEE binary64 bits**,
  not rounded decimal strings; empty means that draw was not consumed;
- selected coordinate and, for an occupied selection, incumbent ID, full buffer,
  eligibility tick and NOW/NEXT ownership;
- the pre-intervention partial-opportunity flag, plus pre-admission queues and
  population.

MT uniforms must be canonical values k/2^32 in [0,1), including positive zero only.
NATIVE has no channel draw. Stratified modes always have one channel draw; a rank
draw occurs exactly when the selected candidate set is nonempty, even for REJECT.
The occupied channel is [0,1/2), the vacant channel [1/2,1). No resampling/fallback.
Candidate coordinates are enumerated x-major/y-minor. The source and partner cannot
be victims; a delayed but unbound, visibly nonempty child is not protected.

The proposed child ID must be fresh and monotonic across all proposals, including
failed ones; gaps from other native allocations are allowed. ID exhaustion must
be checked before native signed-counter increment, not after an overflow.

Partial opportunity means selected eligible occupied incumbent plus positive cut
offset leaving a nonempty source. Validate the flow head/source and full buffers
against independent VM state. Do not infer them from the BEGIN's own flags.

## RESOLVE: after inherited completion

RESOLVE is emitted **after the existing scheduling COMPLETE**, not merely at return
from `OpcodeCleaveSpatial`: generic completion can still append participants and
update counters after that return. The adapter must hold a pending transaction
across this boundary using saved IDs/data, never freed participant pointers.

RESOLVE includes disposition, cross-stream indices, child eligibility and source
survival; its state/queues/population are the completed transaction state.

- A replacement has one EVICT material event at BEGIN.material_index + 1, then the
  native CLEAVE event at +2. Other dispositions have CLEAVE at +1 and no EVICT.
- EVICT has one independent full-buffer victim removal and exact accessible-pool
  refund in a distinct eviction ledger; it is neither DECAY nor RETIRE.
- The linked scheduling DEATH must identify that victim, carry cause EVICT and
  reference its EVICT material index. Native participant-cleanup deaths are separate
  CLEAVE deaths linked to the CLEAVE material index; they are not victim deaths.
- Successful placement has one scheduling BIRTH after material CLEAVE, before
  COMPLETE, with the proposed child ID, source/participant IDs, same selected cell,
  and eligibility `tick + 1 + delay`. Rejections have no birth/eligibility fields.
- The earlier native **lineage** BIRTH publication must match this composite; it
  cannot be treated as a separate admission. CSV interleaving is not a causal clock.
- Actual child/victim/grid/list bijections and all untouched occupants must be
  reconstructed independently. Replacement adds one child and removes one victim;
  only native participant cleanup can reduce its composite population further.
  A replacement transaction cannot increase population.

Cumulative fields at START (zero), each RESOLVE, and END are: nonempty proposals,
evictions, partial opportunities, partial commitments, and per-symbol eviction
returns. BEGIN has no cumulative payload. Every eligible partial REPLACE opportunity
commits exactly once; none commits in REJECT/NATIVE. Whole-source transfers may
replace a victim but receive no partial-opportunity/continuity credit. Refund totals
include every eviction, not just qualifying/partial/rooted ones.

The irreversible admission boundary starts with attempted publication of victim
material/death or child-admission state, whichever is first. Any failure thereafter
is fatal, with all published prefixes retained and no rollback/resume. Even a failure
inside a journal function before its first successful write is fatal once that
publication call has begun; do not guess which prefix reached storage.

## Independent checks and explicit limits

`audit_structure()` checks framing, internal suffix/draw claims, causal-index shape,
queue/counter consistency and cumulative hidden-tail refunds. It deliberately
returns a **Structure**, not a scientific integrity pass. A self-consistent false
cell can pass framing: the adversarial tests demonstrate that fact.

`check_selection()` compares a BEGIN to externally reconstructed VM, grid and
current/next state and recomputes the target using the independent Python oracle.
That state must not be manufactured from the same admission row.

Full admission replay still must implement:

1. A bijection between independently reconstructed nonempty VM proposals and
   BEGIN/RESOLVE pairs; every material EVICT and scheduling EVICT death is used once.
2. Exact joined event contents, pool/eviction-ledger updates, full-buffer source
   healing/native cleanup and child creation, including every event outside the
   admission journal and all raw snapshot/END checks.
3. Post-completion grid/list ownership, unchanged unrelated agents, actual RNG
   consumption/isolation, and source/replacement-only ancestry with no reconnection.
4. Native prepublication rollback and postpublication fatal-prefix tests.

Neither framing nor selector conformance discharges these remaining obligations.
Native population execution stays locked until they and all inherited gates pass.
