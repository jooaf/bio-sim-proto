# FR-I002 conserved-kernel provenance parity preregistration

**Frozen before implementation:** 2026-09-18

## Purpose and boundary

FR-I001 validated an operational functional-descendant candidate in the
unconserved paper assay: paper score 64 plus at least 0.75 value-change
provenance detected 65/65 held-out witness trials and 0/130 controls. FR-I002 is
an implementation mechanics gate for carrying exactly those labels through the
exact conserved BFF kernel without changing simulation dynamics.

This gate does not test descendant persistence and cannot reclassify AC-P006.
Any mechanics mismatch stops before new transplantation.

## Frozen label semantics

Maintain a separate `uint8` label for every soup byte, restricted to `{0,1}`.
Labels never enter instruction dispatch, heads, loops, pool accounting, friction,
mutation draws, pairing, or scheduling.

For each attempted write:

- equal-value no-op: retain the destination label, regardless of source label;
- successful `.` or `,` changing copy: destination receives source label;
- successful `+` or `-` changing arithmetic: retain destination label;
- successful changing mutation: destination label becomes 0;
- scarcity- or friction-blocked write: retain destination label; and
- pool withdrawals/returns carry no labels.

Initial-label patterns in this mechanics gate are deterministic test patterns,
not biological ancestry.

## Separate implementation rule

Implement separate instrumented conserved-write, BFF-interaction, and epoch
functions. Do not modify the production kernel's behavior or route ordinary runs
through provenance code. Instrumented functions must return the same mechanics
metrics as production plus updated labels. The production mechanics reference is
`experiments/phase1_probe.py` Git blob
`3805a0d4987f2c24ba70fe25e9b688a9f40cb137`; any reference change requires a
new preregistration.

## Frozen parity matrix

### Directed write and interaction fixtures

Create explicit fixture records for every Cartesian combination of operation
`{., ,, +, -}`, changed/equal value, binary source/destination labels, and outcome
`{success, scarcity, friction}` where meaningful. Each record freezes initial
joint bytes/heads, pool target count, friction threshold/seed, counter start,
expected destination byte/label, pool exchange, counter delta, and returned
metrics. Add concrete head-wrap, same-half/cross-half, nested/unmatched loop,
self-modification, arithmetic-wrap (`255 -> 0`, `0 -> 255`), and budgets
`1, 2, 16, 128, 1024, 8192` records.

Explicitly require full mechanics and label parity for these rules: no-ops skip
the changing counter but count as execution/mutation success; every changing
attempt increments it; friction is checked before scarcity; rate-1 friction wins
when both friction and scarcity apply; blocked writes retain labels; and cross-
success excludes no-ops. Verify expected labels and mechanics independently, not
only by comparing the two kernels.

Add forced mutation fixtures for successful changing (label resets to 0),
equal-value no-op (label retained), scarcity block, friction block, and mutation
followed by a provenance-carrying copy. Add a nonidentity pair order
`[2,0,3,1]` fixture with independently expected gather/scatter labels.

### Randomized interaction parity

For case `c` and byte `b`, set joint byte to
`splitmix64(0xAC008100 XOR splitmix64(c * 128 + b)) & 0xff` and label to
`splitmix64(0xAC008101 XOR splitmix64(c * 128 + b)) & 1`.
Use mixed-radix parameter indices:

- friction rate index `c mod 4` over
  `{0, 0.1, 0.27555027572734614, 1}`;
- pool regime index `floor(c/4) mod 3`;
- counter index `floor(c/12) mod 4` over
  `{0, 1, 2^16 - 1, 2^31 - 1}`; and
- budget index `floor(c/48) mod 6` over
  `{1, 2, 16, 128, 1024, 8192}`.

Convert friction rates with `round(rate * 2^30)` and use friction seed
`202618000 + c`. Initialize all ledger/cross arrays to zero. Pool regimes are:
all-available = 4,096 of every symbol; one-count = one of every symbol; sparse =
zero for symbol `s` when
`splitmix64(0xAC008102 XOR splitmix64(c * 256 + s)) & 3 == 0`, otherwise 4,096.

Run production and instrumented interactions from independent copies. Require
exact equality of final joint bytes, pool, withdrawals, returns, blocked-symbol
arrays, friction-blocked array, cross-direction arrays, changing counter, step
count, and every returned write/block/cross metric.

### Multi-epoch parity

For seeds `202618000`–`202618004`, initialize 32 tapes with the pinned production
`initialize_soup(32, seed)`. Label tape `t`, byte `b` as
`splitmix64(0xAC008200 XOR splitmix64(seed * 2048 + t * 64 + b)) & 1`.
Initialize histogram-matched pools as exact initial tape counts times multiplier,
all ledger/cross arrays to zero, changing counter to zero, and order to
`arange(32, uint32)`. Run absolute epochs `0..99`; before each epoch call pinned
`shuffle_indices(order, seed, epoch)`. Use max steps 8,192, mutation threshold
`round(rate * 2^30)`, friction threshold `round(rate * 2^30)`, and friction seed
`seed`; carry pool, labels, ledgers, and changing counter across epochs.

Run production and instrumented epoch paths under the Cartesian matrix:

- mutation rates `{0, 1/4096}`;
- friction rates `{0, 0.27555027572734614}`; and
- histogram-matched pool multipliers `{2, 16}`.

After every epoch require exact equality of soup bytes, pair order, pool, all
ledger/cross arrays, changing counter, interval metrics, and conservation
residual. In addition to binary range and deterministic-repeat equality, require
the forced mutation and nonidentity gather/scatter fixtures above to establish
independently expected epoch-label behavior.

## Acceptance gate

FR-I002 passes only if:

1. every directed fixture has the independently specified label outcome;
2. all 1,000 randomized interactions match every production mechanics field;
3. all 40 multi-epoch configurations match after every one of 100 epochs;
4. every instrumented trajectory is deterministic across two complete runs;
5. labels never affect bytes, pools, ordering, RNG/friction streams, or counters;
   and
6. the full existing test suite remains green.

Any mismatch is an implementation defect. Repair only mechanics/provenance code
and rerun this frozen matrix; do not weaken parity fields or remove failing cases.

## Decision ladder

- **Pass:** preregister new held-out composition-preserving transplantation runs
  using the frozen 0.75 descendant threshold and prospective descendant counts.
- **Fail:** stop BFF lineage/persistence/ecology work and pivot to a substrate
  with explicit atomic reproduction and lineage identity.

A pass validates observational instrumentation only. It does not establish
biological ancestry, persistence, heredity, organisms, adaptation, ecology, or
organization.
