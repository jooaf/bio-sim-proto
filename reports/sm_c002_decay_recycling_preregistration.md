# SM-C002 causal decay-recycling gate

**Frozen before patching:** 2026-09-30

## Question and bounded claim

SM-C001 established exact per-symbol conservation, persistent seeded native
lineage, and an initial free-pool abundance effect. Its m0 arm nevertheless
accepted 10,537–14,112 positive-growth copy transactions and produced 519–972
births while receiving 14,347–18,534 bytes from decay. SM-C002 asks:

**Does access to material released by native decay sustain late copying and
cleavage-lineage production under exact conservation?**

A pass supports causal decay-fed material throughput and reproduction under these
conditions. It does not establish regulated recycling, metabolism, energetic
closure, functional heredity, self-maintenance, ecology, or organisms.

## Pinned substrate and inherited semantics

- upstream commit `15dad84da126a4f887ba945c23a13e89e827f067`;
- patches 0001, 0002, and 0003 unchanged and applied in order;
- new environment-gated patch 0004 applied last;
- canonical 140-host inoculum, positions, 40×40 grid, global interaction and
  placement, mutation 0.0002, decay 0.0005, 5,000 steps, report interval 100;
- SM-C001 copy transactions, reserved terminator, full-buffer inventory,
  cleavage, decay, bounds, lineage, and artifact semantics remain frozen.

SM-C002 changes only the destination of matter removed by native decay. It does
not change whether decay occurs, which unbound molecule or bound pair is selected,
RNG draws, freeing, vacancy creation, list/grid operations, or native completion.

## Conserved state and intervention

For every ALXII symbol `s` and every completed operation/checkpoint/END:

`molecular[s] + accessible_pool[s] + waste[s] = initial_total[s]`.

`molecular` counts each non-NUL byte in every complete allocated `maxl0` buffer,
including hidden bytes. `waste` is an inaccessible per-symbol ledger: it occupies
no grid cell, cannot bind, execute, mutate, diffuse, decay, or fund a copy, and
causes no RNG draw. All counts are checked nonnegative 64-bit integers. Initial
pool and waste are zero; initial total is the 8,960-byte host inoculum histogram.
Symbols absent from that histogram remain impossible.

Set `STRINGMOL_DECAY_DESTINATION` only when conservation is enabled:

- **recycle:** each full-buffer symbol removed by unbound or bound-pair decay is
  returned exactly once to the accessible pool;
- **sequester:** the identical removed histogram is added exactly once to waste.

Missing routing preserves patch-0003 behavior byte-for-byte. With conservation
disabled, any routing variable has no effect. Unknown values or a routing value
with malformed conservation configuration fail before the first timestep.

Copy returns, failed-placement returns, and successful-cleavage discard returns
remain routed to the accessible pool in both arms. Do not modify the generic
release path to implement decay routing. Temporary cleavage duplication is still
outside stable-state accounting.

## Versioned observation and independent replay

When routing is explicitly enabled, suppress patch-0003's two conservation-v1
files and add exactly three version-2 files; native and lineage files are unchanged:

1. `conservation002.csv`: CHECKPOINT at every scheduled report tick strictly
   before the actual END (ticks 0–4,900 only for a full-horizon run) and one
   post-loop END at the native exit tick, with ALXII-ordered
   molecular/pool/waste/initial inventories, exact residuals,
   copy partitions and per-symbol exchanges/blocks, decay removed/to-pool/to-
   waste, failed-placement and cleavage-discard returns, molecular/pool/waste
   bytes, pool minima, and cumulative positive-growth/contraction byte totals.
2. `conservation_buffers002.csv`: every extant ID and uppercase full-buffer hex at
   each matching checkpoint and END, ordered exactly as SM-C001.
3. `material_events002.csv`: an ordered operation journal with tick, global event
   index, event/outcome, participating IDs, buffer/offset byte changes including
   NUL, and stable material effects. Record every accepted changing or scarcity-
   blocked copy, every decay member (including both members of a bound-pair
   event), every cleavage stable transition/placement outcome, and every actual
   failed-placement or cleavage-discard return.

The journal begins from the tick-0 full-buffer state. Its sparse ordered byte
changes and lifecycle events must replay the complete agent-buffer map and the
accessible/waste ledgers at every checkpoint and END. The analyzer independently
checks:

`pool = initial_pool - copy_withdrawals + copy_returns + decay_to_pool + failed_placement_returns + cleavage_discard_returns`

`waste = initial_waste + decay_to_waste`

`decay_removed = decay_to_pool + decay_to_waste`.

It cross-checks version-2 buffers, aggregate counters, native lineage identities
and checkpoint visible prefixes, END identity history/population, exact output
inventories, and conservation. Event-level replay defines positive-growth and
contraction bytes; aggregate counters alone are insufficient.

## Frozen mechanics gates

All gates use fresh directories, sanitized environments, successful exits, exact
inventories/checksums, and development seeds only.

1. **Absent compatibility:** patch 0003 versus patch 0004 with routing absent;
   lineage on; canonical host seed `202620998`, 500 steps. Require exact filename
   set, stdout/stderr, RNG states, and every output byte.
2. **Explicit recycle parity:** patch 0003 default versus patch 0004 recycle;
   canonical host seed `202620999`, 500 steps, histogram amount 0. Native and
   lineage outputs must be byte-exact; version-2 rows projected onto v1 fields
   must match every v1 buffer/inventory/counter value exactly, with waste and
   decay-to-waste zero.
3. **Disabled isolation:** patch 0004 with conservation disabled and routing
   absent/recycle/sequester must be byte-exact.
4. **No-decay equivalence:** recycle and sequester with decay probability zero
   must have byte-exact native, lineage, and replayed molecular trajectories;
   decay/waste counters are zero. Route metadata and declared zero-valued route
   columns may differ only as frozen by serializer fixtures.
5. **Observer isolation and determinism:** logging on/off leaves native and lineage
   trajectories exact; repeated logging-on runs reproduce every byte.
6. **Directed mechanics:** unbound decay, active-selected and passive-selected
   bound-pair decay, hidden tails, exact once-only routing, inaccessible waste,
   malformed/overflow configuration, pool/waste reconciliation, and a downstream
   copy that succeeds after decay in recycle but remains blocked in sequester.
   Preserve RNG, pointers, biomass, energy, lengths, species/unbinding, and
   completion effects. Retain all patch-0003 copy/cleavage/bounds fixtures.
7. **Upstream and focused validation:** both fresh upstream suites, lineage
   isolation, scoped mypy, and focused Python/C++ tests must pass.

Any mismatch stops before unseen seeds. Mechanics may be repaired without changing
this protocol; changing routing chemistry, endpoints, thresholds, or scientific
matrix requires a new experiment ID.

## Frozen scientific matrix

Use unseen paired seeds `202622000`–`202622019`, after verifying no prior use:

- **R (recycle):** histogram amount 0; decay routes to accessible pool;
- **S (sequester):** identical start; decay routes to inaccessible waste.

There are 40 runs. Use at most six concurrent processes and no resume, selective
retry, pair removal, or outcome-based extension. Extinct and failed runs remain in
the denominator. Before launch, commit and push the protocol and implementation,
then seal protocol/source/patch/build/test/analyzer/config/schema/environment/
command hashes, all initial buffers and totals, and every read-only input.

## Frozen endpoints

The late window is `2500 <= timestep < 5000`. Native execution stops immediately
at population zero. Extinct runs retain their actual early END and only scheduled
checkpoints before it; no later snapshots are fabricated. Their unexecuted
remaining-window event contributions are zero. Tick-4,900 lineage outcomes use
the inherited SM-C001 early-extinction rule.

- `G_late`: sum over accepted copy events of `max(0, committed non-NUL bytes after
  - before)` in the late window. This is a byte count, not transaction count.
- `B_late`: successful placed cleavage births in the late window.
- total successful births, two-parent/passive depths, and SM-C001 strict
  descendants/fraction at tick 4,900.
- conservative whole-run decay-funding lower bound:

`L = sum_s max(0, copy_withdrawals[s] - copy_returns[s] - failed_placement_returns[s] - cleavage_discard_returns[s] - initial_pool[s])`.

Diagnostics include early/late contractions, copy attempts/blocks and blocked
fractions, decay exposure, molecular/pool/waste bytes, population, full/visible
length distributions, descendant material, extinction time, placement outcomes,
and every source-specific exchange. Raw blocked counts have no required direction
because an inactive arm may make fewer attempts.

## Integrity and exposure

Every run must pass process, build/input/output inventory, exact replay,
per-symbol conservation, pool/waste nonnegativity, loader, lineage-DAG,
snapshot/species, identity-history, counter, schema, and bounds checks. Every run
must record zero boundary errors and no out-of-alphabet bytes.

For a scientific pass, every run must also experience at least one native decay
with nonzero removed matter. A zero-exposure pair remains in the denominator and
is a valid exposure/liveness failure, not an integrity failure.

## Acceptance gate

SM-C002 passes only if all mechanics/integrity/exposure gates pass and the **same
at least 16 of 20 pairs** satisfy all four requirements:

1. **Late material effect:** `G_late(R) - G_late(S) >= 896` bytes and
   `G_late(R) >= 2 * G_late(S)`;
2. **Late birth effect:** `B_late(R) >= 50` and
   `B_late(R) - B_late(S) >= 25`;
3. **Recycle lineage liveness:** R has at least 100 total births, two-parent depth
   at least 2, at least 100 strict tick-4,900 descendants, and descendant fraction
   at least 0.5; and
4. **Demonstrable decay funding:** `L(R) >= 896` bytes.

The 896-byte margin is 10% of initial material. Ties and inadequate effects are
non-passes; all 20 pairs remain in the fixed denominator. Report every component
and pair. For a simple directional 16/20 count, the frozen fair-coin upper tail is
`6196/1048576 = 0.005908966064453125`; this is descriptive and is not a p-value
for the composite gate.

## Decision ladder

Any scientific full or partial claim requires all mechanics, integrity, and
40-run exposure gates. Define prospectively:

- `material_support`: at least 16/20 pairs each satisfy requirements 1 and 4;
- `birth_support`: at least 16/20 pairs each satisfy requirements 2 and 3;
- `full_support`: the same at least 16/20 pairs each satisfy all four requirements.

Apply this ladder:

- **Full pass (`full_support`):** access to decay-released matter causally supports
  late material throughput and cleavage-lineage production under the frozen
  conditions. A separately preregistered functional-descendant or energetic
  boundary is eligible.
- **Material support only (`material_support` true, `full_support` false):** report
  decay-supported copying only. Even if `birth_support` is separately true, do not
  combine effects occurring in different pairs into a reproduction claim. Stop
  before energy/ecology.
- **Birth without material support (`birth_support` true, `material_support`
  false):** fragmentation/redistribution remains unresolved; do not call recycling
  causal and stop before energy/ecology.
- **Valid failure (neither support predicate):** retain exact results and identify
  exposure, recycle liveness, material, birth, lineage, or funding component
  failure without relaxing gates.
- **Unevaluable:** repair only process/observer/artifact defects and repeat the
  complete unchanged matrix. Chemistry or semantic changes require a new ID.
