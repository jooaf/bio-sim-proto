# SM-B003 native replacement transaction component

## Scope

`native/admission_transaction.h` now implements reversible victim unlinking,
same-cell child staging and full-buffer refund against the real native `s_ag`,
`smsprun`, list operations and conservation types. It is **not yet wired into the
interpreter**, and is not a population experiment, complete adapter or launch gate.
The component ledger patch is `native/eviction_ledger.patch`, not a completed
canonical patch 0007. Paths above are relative to `experiments/stringmol/`.

The baseline `/tmp/sm/a7` and archived execution trees remain unchanged. A separate
candidate tree `/tmp/sm/a7-dev` has the same pinned upstream and patches 0001–0006,
plus the three-line ledger extension. Tests independently apply that extension to
a private copy of the baseline header rather than modifying either baseline.

## Implemented mechanics

- Validate grid/list bijections, queue backlinks, participant/victim/child identity,
  nonempty unbound victim, fresh non-live child ID, staging status, distinct buffers,
  and absence of incoming binding/head references to the victim.
- Accept unbound delayed children as victims regardless of their eligibility tick.
- Preflight all refund/ledger additions against overflow before mutation.
- Unlink from NOW or NEXT, install the staged child in exactly the selected cell,
  and credit all victim bytes, including hidden tails, to a distinct eviction ledger.
- Include this ledger in **both** native `material()` and `observe()` reconciliation.
  No debit/refund is charged to retirement, decay, failed placement or waste.
- Restore the captured post-proposal ownership/grid/pool/minimum/ledger state on
  every injected prepublication fault. An aborted transaction cannot be retried.
- Mark publication before invoking its callback. Callback failure permanently
  forbids rollback, restaging and freeing through this transaction; the caller must
  terminate the run, even if no bytes reached storage.
- Keep the victim allocation through successful publication, then free exactly once.
  The primitive neither rewinds RNG nor owns the earlier ID/species proposal prefix.

The staged child is not yet committed molecular inventory: after EVICT, the caller
still must execute inherited source healing, CLEAVE, scheduling birth and completion.
The publisher callback must also supply the joined scheduling/lineage death events.
These responsibilities are explicit remaining integration work, not implied by the
primitive's successful material transition.

## Native directed checks

168 component cases passed under ASan/UBSan with leak detection:

- 12 successful cases covering both queue owners, head/middle/tail unlinking and
  visible-only/hidden-tail refunds; real native EVICT/CLEAVE accounting and both
  reconciliation sites pass.
- 60 injected failures across five reversible checkpoints, all queue positions,
  both owners and both buffer shapes; captured native state is restored and retry
  refused. Snapshots include actor buffers/fields, heads/links, grid/status,
  material counters/ledgers and journal handles.
- 24 failures before/after material publication preserve irreversible state and
  return a fatal fixture status, with the published EVICT prefix retained when present.
- 36 abandonment/free-order checks and 36 invalid-state/preflight checks, including
  duplicate/cyclic ownership, aliases, protected/empty/bound victims, incoming
  references, ID reuse, invalid minimum/pool and refund/ledger overflow.

The same 168 cases passed without instrumentation. All **48** resulting native CSV
files, including partial fatal prefixes, matched byte-for-byte with equal file sets.
The combined design/journal/sanitizer/native-component suite passed **286 tests**;
strict typing passed. These are mechanical tests, not biological replicates.

Successful component fixtures explicitly supply known source healing to exercise
native conservation; they do not pretend to execute the whole opcode. Future full
interpreter and independent replay tests must verify that healing themselves.

An initial strict build stopped on an unchanged inherited-header indentation warning.
That attempt is retained. Legacy headers are treated as system headers; new fixture
and component code still compile with `-Wall -Wextra -Werror`. No native semantics
were edited to silence the warning.

Evidence on Elements:
- `verification/sm-b003-transaction-v1/` — initial compiler failure.
- `verification/sm-b003-transaction-v2/` — initial 142-case component qualification.
- `verification/sm-b003-transaction-v3/` — expanded 286-test combined qualification.
- `verification/sm-b003-transaction-normal-v1/` — 168 ordinary cases and 48-file parity.

## Next required work

Wire the existing selector, proposal journal and transaction into an isolated native
opcode adapter, enforcing source RETAIN and global interaction. Publish exact EVICT,
CLEAVE, birth and completion joins, then test complete native operations, all failure
boundaries, disabled/NATIVE observer parity and full final RNG states. Implement the
independent ordered material/grid/list/VM/ancestry replay before six-arm development
population qualification. The held-out matrix is still unlaunched.
