# SM-B003 native-integration audit and qualification receipt

## Completed work

Design/source commit: `16f553c` (full revision in the retained probe plan).

- Candidate six-arm admission design and Python selection/lineage/decision oracle.
- 234 focused tests passed, including 24 new synthetic admission-design tests;
  strict typing passed for the new Python modules/tests.
- 1,536 C++/Python selector comparisons passed across eight synthetic grids,
  three policies and 64 synthetic RNG seeds (1–64).
- 192 independent straight-line native RNG reference states were checked against
  the complete 624-word state plus cursor, not merely claimed draw counts.
- All four selection outcomes were exercised. Pinned native MT object/header and
  the compiled native uniform wrapper were checked against preserved R1 hashes.
- Probe outputs and checksum-verified plan/report copies are ordinary files in
  `Elements/bio-sim-results/verification/sm-b003-selection-v1/`; POSIX controls and
  the fixture binary are in the externally backed `/tmp/sm/sm-b003-selection-v1/`.

These are selector/RNG mechanics checks, **not population assays**, eviction
atomicity tests, admission exposure qualification, or an implemented native
adapter. SM-B003 launch remains false. The inherited simulator has not been edited.

## Integration findings that must constrain the adapter

The next change cannot be a generic replacement of `AgentPlaceOnGrid` alone.
Inspection of pinned `sm_spatial.cpp`, `sm_conservation.h` and the directed
retirement fixture establishes these requirements:

1. **Native proposal publication already exists.** `OpcodeCleaveSpatial` allocates
   the child ID, copies its suffix, updates species bookkeeping and resets executor
   biomass before placement. A placement hook therefore cannot honestly claim to
   roll the whole cleavage proposal back. Define the new rollback baseline after
   this existing proposal prefix and after the sampler's RNG draws, before any
   victim/list/grid/pool mutation. Preserve the proposal prefix on fatal failure;
   never rewind it or describe it as an unattempted birth. If implementation instead
   moves species publication, that is a separately reviewed semantic change and
   needs amended parity/reference requirements, not a silent refactor.
2. **All reconciliation sites need a distinct ledger.** Both `material()` and
   `observe()` reconstruct pool balance from named ledgers. Add eviction returns
   to both wide-intermediate equations; never charge them to `retirement_returns`,
   failed placement, decay or waste. A separate admission journal can carry the new
   ledger without changing legacy CSV bytes in disabled/NATIVE parity runs.
3. **A staged child is not yet committed molecular inventory.** Native placement
   installs the child before source healing; the material journal commits the
   conserved `CLEAVE` state only afterward. Publish victim removal as its own exact
   material transition, followed by the inherited cleavage transition and linked
   scheduling birth. Do not count the staged child in both source and live material,
   or use its victim's refund to fund prior child copying.
4. **Distinguish stream order from call order.** Native lineage BIRTH publication
   occurs earlier than scheduling BIRTH. Specify a joined causal schema using
   material indices and admission transaction IDs; physical CSV file interleaving
   is not a causal clock. Replay must prove EVICT -> CLEAVE -> scheduling BIRTH ->
   boundary completion, plus actual same-cell ownership transfer. Validate the
   earlier lineage event against that composite, not as an independent admission.
5. **Snapshot all state actually mutated.** Before the irreversible boundary,
   rollback must restore list heads and neighboring links, victim ownership, child
   coordinates/status, grid status, accessible pool/minimum, eviction counters,
   and every other changed field. The child proposal's preexisting ID and species
   prefix are outside that rollback baseline. Preserve the victim allocation until
   publication; free exactly once afterward. Published-prefix failure is fatal.
6. **Do not substitute decay or source retirement.** Decay may delete a bound
   partner; source retirement acts after admission on a participating source.
   Neither implements an unrelated unbound victim's same-cell displacement.
7. **Independent replay must distinguish removals.** Frozen B002 material replay
   recognizes RETIRE but not EVICT. A future admission replay must reject a RETIRE
   label masquerading as eviction, verify its distinct return ledger, and join
   victim death to the selected cell and child admission. Reusing a validated
   full-buffer-removal arithmetic primitive is permissible; conflating public
   counters, journal labels, or biological roles is not.

## Concrete next implementation order

1. Freeze the versioned admission journal and explicit post-proposal rollback
   boundary; specify what every column proves and its independent derivation.
2. Build an isolated patch-0007 checkout, never modify the archived patch-0006
   execution tree or R2 artifacts. Add environment-gated admission selection,
   distinct eviction accounting and staged ownership transitions.
3. Extend real native directed fixtures, including both list states, hidden tails,
   delayed unbound victims, source cleanup and every fault boundary. Include ASan/
   UBSan and actual native final-RNG comparisons; the standalone selector does not
   satisfy these gates.
4. Implement independent admission/material/ownership replay and adversarial
   corruption tests. Enforce replacement-only ancestry without reconnection.
5. Run all six arms on development inputs only; qualify opportunity, observer
   isolation and resource budgets. Preserve all failures and amendments.
6. Only then finalize the prospective protocol, audit reserved-seed execution
   history, publish a clean complete implementation and seal launch eligibility.

No further biological question is answered by these mechanical checks. B002's
intermediate classification is unchanged; no BFF continuation is included.
