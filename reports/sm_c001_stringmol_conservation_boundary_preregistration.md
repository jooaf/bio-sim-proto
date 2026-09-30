# SM-C001 Stringmol exact symbol-conservation boundary

**Frozen before conservation patching:** 2026-09-18

## Purpose and boundary

SM-L001 validated native successful cleavage birth and persistent individual
lineage identity in pinned Spatial Stringmol. SM-C001 asks whether exact
per-symbol matter conservation can be added at the native copy/decay boundary
without changing unconserved trajectories and while retaining the seeded lineage
positive control.

This is a mechanics and liveness gate. It does not establish spontaneous origin,
energetic closure, heredity fidelity, adaptation, self-maintenance, ecology, or
organisms. It does not reinterpret BFF failures.

## Pinned substrate and patch order

- upstream commit `15dad84da126a4f887ba945c23a13e89e827f067`;
- canonical ALXII 33-symbol alphabet and matrix;
- patch 0001 locality controls;
- patch 0002 individual lineage observation;
- new patch 0003 exact conservation, applied last;
- canonical host, positions, grid, mutation, decay, and execution settings from
  SM-L001.

Existing upstream `comass` code is not reused as the scientific boundary. It is
aspatial, changes unavailable-symbol copy behavior, does not transactionally
account for the two-write insertion branch, and is not integrated with spatial
placement/decay. Patch 0003 must implement separately reviewed spatial semantics.

## Frozen conservation unit and pool

The conserved material unit is one non-NUL byte from the ALXII alphabet anywhere
in an agent's full allocated `maxl0` sequence buffer, including bytes beyond the
first C-string NUL. This avoids creating or destroying matter when a write head
crosses a terminator and hidden bytes later become visible. For each symbol `s`,
require at every reported checkpoint and final state:

`full_buffer_count[s] + free_pool[s] = initial_total[s]`, where
`initial_total = initial_full_buffer_count + initial_free_pool`.

NUL bytes, agent structures, grid cells, labels, IDs, and energy are not matter.
Every allocation must zero its complete buffer before sequence copy. Pool counts
are signed 64-bit storage but must remain nonnegative and within range. A non-NUL
byte outside the pinned alphabet is an integrity failure. Decay/free accounting
scans the full buffer rather than `strlen`.

Conservation is enabled only when all of these environment variables are present:

- `STRINGMOL_CONSERVATION=1`;
- `STRINGMOL_POOL_MODE=histogram` or `uniform`;
- `STRINGMOL_POOL_AMOUNT=<nonnegative integer>`.

Absent or non-`1` `STRINGMOL_CONSERVATION` disables all conservation code and
outputs even when pool variables are present. If conservation equals `1`, missing
or malformed mode/amount, an unknown mode, overflow, duplicate initialization,
or any invalid initial byte causes nonzero exit before the first timestep. Parse
canonical unsigned decimal only and use checked 64-bit multiplication/addition.
Initialize exactly once after validated loading and placement. Scientific
histogram mode sets `free_pool[s] = initial_full_buffer_count[s] * amount`.
Uniform mode sets the same stated amount for every alphabet symbol and is used
only for no-scarcity parity.

The ALXII key is `ABC$DEF%GH^IJK?LMN}OPQ>RST=UVWXYZ`. The canonical host lacks
`AFIKMNPQSTVZ`; histogram mode therefore assigns those symbols zero total
inventory forever, even at m16. This is a frozen compositional restriction, not
merely low abundance. Agent label `Q` is metadata and contributes no matter.
Environment values, initial molecular/free counts, and totals are frozen in every
manifest.

## Frozen write semantics

For valid in-bounds native states, patch 0003 preserves every native RNG draw and
branch choice before testing availability. Even mutation-disabled safe copy takes
the native mutation draw. It plans the complete ordered byte-change list for one
`=` opcode, including active/passive destination selection, aliasing, and the
native two-write insertion branch, without modifying buffers or pool.

For the opcode transaction:

1. resolve repeated destinations in native write order to obtain final proposed
   bytes;
2. classify no-op only when every final destination byte equals its initial byte;
   zero net composition alone is not a no-op;
3. each changed old non-NUL byte is a gross return and each changed new non-NUL
   byte is a gross withdrawal;
4. succeed only if current pool plus this transaction's gross returns funds every
   withdrawal;
5. on success, atomically apply final bytes and gross pool exchange;
6. on scarcity, apply no byte or pool change and record one blocked transaction
   plus each symbol's missing-unit count after transaction returns;
7. on both success and scarcity, preserve the selected native branch's read,
   write, and instruction-pointer movement, global/per-agent biomass, execution
   count, energy, unbinding/species effects, and instruction completion; recompute
   both agent lengths from the actual committed buffers, never from hypothetical
   blocked bytes; and
8. never substitute an adjacent or alternative symbol when unavailable.

Deletion mutation and read-at-NUL are no-write branch outcomes, not no-op byte
transactions. Freeze their native RNG consumption, conditional pointer movement,
double versus single instruction-pointer increments, length/biomass effects, and completion. Blocked append and blocked hidden-gap
fixtures explicitly require lengths equal `strlen` of unchanged committed buffers.
Normal substitution, ordinary copy, and insertion are classified by
proposed final bytes. Accepted positive-growth is the subset with increased total
non-NUL buffer bytes.

Native bounds handling has unsafe/ambiguous paths. Freeze allocated offsets
`0..maxl0-1`, with `maxl = maxl0-1`; offset `maxl` is the reserved NUL terminator
and valid data read/write offsets are exactly `0 <= offset < maxl`. Conservation-
enabled code verifies the reserved byte is NUL before every copy; a non-NUL
terminator is an immediate integrity failure with no repair or state mutation.

Initial read/write offset validation occurs at the native precheck before any
mutation RNG draw. Invalid initial offsets are `boundary_error`: emit the native
error text and preserve its instruction advance and unbinding/species completion,
but perform no buffer/pool write and no terminator repair. For an insertion, take
only the native draws needed to select indel and insert-versus-delete, then validate
both ordered destinations before drawing the inserted symbol. An invalid second
destination is boundary_error; do not draw the inserted symbol or write bytes,
but apply the already selected insertion branch's pointer/completion effects and
recompute lengths from unchanged buffers. Fixtures freeze exact RNG state.
Scientific runs require zero boundary errors, so this compatibility exception
cannot support a pass. Disabled mode remains byte-identical to native behavior.

Cumulative copy attempts partition exactly into `boundary_error`, `read_null`,
`deletion_no_write`, `final_byte_noop`, `accepted_changed`, and
`scarcity_blocked`. `accepted_positive_growth` is a subset of accepted_changed.
Per-symbol gross copy withdrawals/returns and missing blocked units are separate
arrays. The exact identity is
`attempts = sum(partition categories)`.

## Cleavage, failed placement, and decay

The accounting boundary for cleavage is stable state immediately before the
opcode versus stable state after placement/failure, parent healing, pointer
rewinding, and any zero-length parent destruction. Temporary child/parent suffix
duplication before healing is not a withdrawal and freeing that temporary child
is not independently credited. Compute the net full-buffer histogram across the
active parent, passive parent, and any successfully placed child:

- successful placed cleavage transfers the suffix and must have zero net pool
  exchange unless bytes are actually discarded by parent destruction;
- failed placement followed by parent healing returns the net removed bytes to
  the pool exactly once;
- full-parent suffix cleavage, active-target and passive-target cleavage, pointer
  rewinding, and each zero-length-parent destruction path are explicit fixtures;
- zero-length/invalid cleavage with no stable molecular change exchanges nothing;
  and
- any unexpected stable molecular gain is an integrity failure, not a pool
  withdrawal invented after cleavage.

Whenever spatial decay frees one unbound molecule or both members of a bound pair,
every non-NUL full-buffer byte in each freed molecule is returned exactly once
before memory release. Track gross `decay_returns`,
`failed_placement_returns`, and `cleavage_discard_returns` separately from copy
returns. The last category covers nontransferred bytes, including hidden tail,
discarded when a parent is destroyed after successful child placement.

`AgentMake` allocation failure exits upstream; unchecked child-buffer allocation
failure or any allocation anomaly is a process/integrity failure. Patch 0003 adds
no recovery semantics. Directed fixtures cover placement failure, not simulated
allocator recovery. Conservation accounting cannot depend on lineage logging.

## Conservation observation

Conservation adds exactly two files when enabled:

1. `conservation001.csv`: one aggregate `CHECKPOINT` row at every existing
   pre-increment report tick and one post-loop `END` row before cleanup. Records
   contain tick/event, ALXII-ordered full-buffer molecule/free/initial totals,
   maximum residual, all partition counters, gross copy withdrawals/returns,
   decay returns, failed-placement returns, cleavage-discard returns, missing
   blocked units, current total molecular/free bytes, and all-time per-symbol
   pool minimum after every pool
   transaction/release (not merely checkpoint minima).
2. `conservation_buffers001.csv`: at every same checkpoint and END, every extant
   agent ordered by ID as `tick,event,id,full_buffer_hex`, where hex has exactly
   `2 * maxl0` uppercase digits and includes NUL/hidden bytes.

CHECKPOINT rows align with SM-L001's pre-increment lineage snapshots. END rows
represent post-loop state before cleanup and remain separate from the tick-4,900
lineage endpoint, including later extinction. Canonical CSV serialization and
checksum rules are frozen in tests before scientific execution.

The analyzer reconstructs full-buffer histograms from the buffer file and verifies
aggregate rows, pool nonnegativity, all-time minima, zero residual, counter
partition, and the reconciliation equation for every symbol:

`pool = initial_pool - copy_withdrawals + copy_returns + decay_returns + failed_placement_returns + cleavage_discard_returns`.

It cross-checks buffer IDs and visible prefixes against patch-0002 lineage
snapshots at CHECKPOINT and against patch-0002 END population at END. Thus no END
conservation claim relies on an unverifiable aggregate.

## Mechanics gates before unseen runs

### Disabled compatibility

Generate one absolute-path canonical host config/matrix for seed `202620998`, 500
steps, and use independently empty directories plus a sanitized environment.
Enable identical lineage logging in every run. Compare patch-0002 with patch-0003
under (a) all conservation variables absent and (b)
`STRINGMOL_CONSERVATION=0` with valid pool variables present. Require successful
identical exit status, stdout/stderr, exact filename set, and every output byte.
Repeat patch-0003 absent-variable execution and require exact determinism. Also run
patch-0003 absent-variable with lineage logging disabled and require native shared
outputs to match its lineage-enabled counterpart after removing only the two
lineage files.

### No-scarcity compatibility

For one shared absolute config/matrix at canonical host seed `202620999`, 500
steps, compare successful patch-0002 unconserved against patch-0003 with lineage
logging enabled and uniform pool amount `1000000`, under the same sanitized
environment in empty directories. Require zero blocked and boundary-error
transactions and identical shared native outputs byte-for-byte; only the two
declared conservation files may be extra. Independently verify every checkpoint
and END full-buffer/pool reconstruction. Repeat enabled execution byte-for-byte.
Also execute conservation enabled with lineage disabled: after removing only the
two lineage files, native plus conservation outputs must match lineage-enabled.

### Directed mechanics

Add branch-directed source-level tests comparing complete state and RNG state for
normal copy into NUL, overwrite, same-symbol no-op, substitution mutation, atomic
two-write insertion, deletion mutation, read-at-NUL, scarcity rollback, repeated
destination resolution, active/passive destinations, pointer aliasing, and native
pointer/completion behavior on block. Freeze expected lengths, both biomasses,
global biomass, execution count, energy, instruction/read/write pointers,
unbinding/species effects, and every RNG draw.

Add fixtures for read/write bounds, insertion first/second destination boundaries,
invalid offsets, blocked append followed by hidden-tail write and gap filling, full
buffer visibility changes, histogram/uniform/invalid/overflow initialization,
successful full/partial active/passive cleavage, pointer rewinding, each destroyed-
parent case, successful full-parent cleavage containing hidden tail material,
failed-placement return, unbound decay, bound-pair decay, and zero-length handling. Require upstream plus all existing lineage/isolation tests green.

Any mechanics mismatch stops before unseen seeds. Repair mechanics only and rerun
the frozen gates.

## Frozen scientific matrix

Seeds `202621000`–`202621009`, paired by seed:

1. **m16:** canonical 140-host inoculum; histogram pool amount 16;
2. **m0 scarcity:** identical inoculum; histogram pool amount 0.

All runs use 40×40 grid, 5,000 steps, global interaction and placement, mutation
0.0002, decay 0.0005, report interval 100, lineage and conservation logging on,
and six concurrent processes maximum. Before launch independently pin committed
SM-C001 protocol bytes/revision and inherited SM-L001 definition hashes; checksum
fresh patch-0002 and patch-0003 builds, patch order/bytes, runner, analyzer, tests,
configs, sanitized environments, commands, initial buffers, pools, and per-symbol
totals. After execution retain complete output inventories. Failed, extinct, or
blocked runs remain in the denominator. No process resume or selective retry.

## Integrity and outcomes

All 20 runs must pass source/build/input/output inventory, process, loader,
lineage-DAG, snapshot/species, and conservation reconstruction checks. Report:

- zero-residual status and pool minima;
- all copy transaction counters and per-symbol exchanges/blocks;
- successful cleavage births, two-parent/passive depths, tick-4,900 strict
  descendants and fraction;
- population and total molecular/free bytes; and
- paired m16-minus-m0 birth and final-descendant differences as descriptive
  scarcity effects.

Roots, descendants, final-window semantics, and extinction handling are exactly
SM-L001's frozen definitions.

## Acceptance gate

SM-C001 passes only if:

1. disabled, no-scarcity, deterministic, directed, upstream, lineage, and
   observation gates all pass;
2. all 20 scientific runs pass integrity with zero per-symbol residual at every
   checkpoint and END, zero boundary errors, and no out-of-alphabet bytes;
3. the same at least 8/10 m16 seeds jointly record at least 100 successful births,
   two-parent depth at least 2, at least 100 strict final descendants, and final
   descendant fraction at least 0.5;
4. every m0 run records at least one scarcity-blocked changing copy transaction;
5. m0 scarcity-blocked transaction count is strictly greater than paired m16 in
   at least 8/10 seeds; and
6. m16 successful birth count is strictly greater than paired m0 in at least 8/10
   seeds.

Matter released by decay or failed placement may legitimately fund later m0
growth; zero m0 positive growth is therefore not an acceptance criterion. A
no-recycling directed fixture separately proves that an empty pool blocks net
molecular growth. For each directional paired gate, use all ten pairs: ties count
as non-wins rather than being dropped. Report the fixed-n fair-coin tail; 8/10 is
`56/1024 = 0.0546875`, descriptive and not standalone significance.

## Decision ladder

- **Pass:** exact conserved native Stringmol reproduction/lineage is validated;
  preregister a separate resource-regulation or energetic-boundary experiment.
- **Fail with valid integrity:** do not add energy or ecology. Report separately
  whether conservation mechanics, m16 reproduction liveness, or scarcity contrast
  failed; retain exact negative results.
- **Unevaluable:** repair only build, observer, or artifact-integrity defects and
  rerun the complete unchanged matrix. A change to write, bounds, cleavage,
  decay, pool, or counter semantics is a new experiment ID, not a repair. Do not
  alter pool amounts, seeds, liveness thresholds, or chemistry after outcomes.
