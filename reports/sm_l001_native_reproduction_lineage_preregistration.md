# SM-L001 native Stringmol reproduction and lineage-identity gate

**Frozen before lineage-observer patching:** 2026-09-18

## Motivation and boundary

FR-P001 closed further BFF lineage/persistence work. The pivot target is pinned
Spatial Stringmol because it has explicit successful cleavage into a newly
allocated molecule, monotonically assigned individual IDs, mutation during copy,
and previously validated seeded host/parasite ecology. Before adding conservation
or energy, SM-L001 must establish that native birth and individual lineage can be
observed prospectively without changing Stringmol trajectories.

This gate validates seeded native reproduction and individual identity. It does
not test spontaneous origin, conservation, energetic closure, heredity fidelity,
adaptation, self-maintenance, ecology, or organisms. Earlier Stringmol species-
level ancestry remains external evidence and is not reused as confirmation.

## Pinned substrate

- upstream repository: `https://github.com/uoy-research/stringmol.git`;
- commit: `15dad84da126a4f887ba945c23a13e89e827f067`;
- canonical ALXII matrix;
- existing reviewed locality patch
  `0001-fix-neighbor-selection-and-add-locality-controls.patch`;
- canonical 64-symbol host replicase
  `WWGEWLHHHRLUEUWJJJRJXUUUDYGRHJLRWWRE$BLUBO^B>C$=?>$$BLUBO%}OYHOB`,
  SHA-256 `94f8c51cef8ef18d4246fb1fc6030b20f887bb0e265be59b3949be2bb69b89c5`;
- one-symbol source-grounded inert control `B`;
- upstream binding, opcode execution, mutation, decay, copy, cleavage, placement,
  and RNG semantics unchanged.

The new patch may add append-only observation and an environment-variable switch.
It must not add an RNG draw, alter control flow, agent state, species accounting,
placement, timing, or configuration semantics.

## Frozen observer semantics

When `STRINGMOL_LINEAGE_LOG=1`, write two append-only CSV files for run number 1.
Logging is disabled when the variable is absent or not exactly `1`.

### Individual event log

After configuration and placement, emit one `INIT` row for every initial agent.
After and only after a cleaved child is successfully placed on the grid, emit one
`BIRTH` row. Canonical columns are:

`event,timestep,population,child_id,active_id,passive_id,child_species,active_species,passive_species,child_label,active_label,passive_label,x,y,child_sequence_hex,active_sequence_hex,passive_sequence_hex`

INIT and BIRTH rows use population `-1`; initial rows also use `-1` parent
IDs/species/labels and empty parent-sequence fields. Birth values are captured
after successful placement but before parent healing or
destruction; parent sequences are therefore the pre-healing event-time strings.
The event species values are current upstream species assignments and may lag a
bound molecule's modified bytes. Sequence is uppercase two-digit hex per raw byte
with no separators. Failed/zero-length cleavage and failed placement are not
births. File order is execution order.

At normal loop exit emit one `END` row with exact exit timestep and remaining
population in the declared population column, every identity/species/label/
position field `-1`, and all sequence fields empty. The logger emits no other
event types.

### Individual snapshots

At every existing population-report checkpoint, before that tick's spatial
increment, write every extant agent ordered by ascending individual ID with:

`tick,id,species,label,x,y,sequence_hex`.

Logging does not define survival between checkpoints. The final endpoint is
population at tick 4,900: use the tick-4,900 snapshot whenever it exists, even if
extinction occurs afterward. Only when no tick-4,900 snapshot exists and the
`END` row proves population zero at timestep at most 4,900 are tick-4,900
population, non-initial descendant count, and descendant fraction defined as
zero; no fabricated snapshot is written. Missing snapshots without that verified
early-extinction condition are an observer defect.

### Identity and ancestry

- Individual identity is `(condition, seed, s_ag.idx)`, never sequence. `agct`
  allocates IDs monotonically within one uninterrupted process; allocation gaps
  from unsuccessful children are allowed. Restarts/checkpoint continuation are
  prohibited, and any negative ID, ID above `2^31-1`, reuse, or ordering wrap is
  an identity-integrity failure.
- Every successful child has two causal parent edges, active and passive.
- Passive-parent lineage is reported separately because upstream assigns the
  child's label from the passive parent.
- Lineage depth is the longest path from any initial individual in the two-parent
  birth DAG; passive depth uses only passive-parent edges.
- Passive-sequence match means child bytes equal the passive parent's pre-healing
  event-time bytes. Mismatch is descriptive and is not called mutation because
  cleavage may target either parent and copying context can also differ. Canonical
  hashes and equality outcomes are reported.

## Observation-isolation gate

Before unseen-seed execution, generate one absolute-path host-only config for seed
`202619999`, 500 steps, global interaction/placement, mutation 0.0002, decay
0.0005, report interval 100, and image interval 1,000,000. Run command
`stringmol 30 <absolute-config>` in three independently empty directories with a
sanitized environment: locality-only baseline binary with no lineage variable;
observer-patched binary with the variable absent; and observer-patched binary
with `STRINGMOL_LINEAGE_LOG=1`. Build both binaries from fresh pinned checkouts;
the baseline applies patch 0001 only and the observer build applies patches 0001
and 0002.

Require baseline and patched-disabled exit status, stdout, stderr, exact output
filename set, and every output byte to match, including `popdy001.dat`, all
`splist*.dat`, `out1_*.conf`, `reload_*.conf`, `RNGstate_*.txt`, and images.
The enabled run must differ only by the two declared lineage CSV files; after
removing those, its filename set and every byte, stdout, stderr, and exit status
must match baseline. Repeat enabled execution in a fourth empty directory and
require all outputs, including lineage files, byte-identical. No run may contain
`Number of agents not specified`, `reproducible method`, `repclicable method`, or
any loader-fallback warning.

Any mismatch stops implementation. Repair observation only and repeat; do not
inspect unseen seeds.

## Frozen paired matrix

Seeds: `202620000`–`202620009`. For every seed run:

1. **host:** 140 canonical host molecules in the existing fixed 140 host cells;
2. **inert:** 140 one-symbol `B` molecules in exactly the same cells.

Both conditions use:

- 40×40 toroidal grid;
- 5,000 steps;
- global interaction radius 0 and global placement radius 0;
- mutation 0.0002 and decay 0.0005;
- report interval 100;
- identical ALXII matrix, loader, positions, build, and observer; and
- six concurrent processes maximum.

Host labels are `Q`; inert labels are `B`; this sequence/label pair is the only
condition difference. Before launch, write an immutable preparation manifest with
source commit/tree status, both patch bytes/hashes/order, compiler and flags,
baseline and observer binary hashes, matrix hash, exact environment allowlist,
generated config bytes/hashes, commands, seeds, conditions, and expected initial
IDs/positions. After each run, write a complete regular-file inventory with size
and SHA-256 plus exit status. Save stdout/stderr and all raw outputs. The runner
must reject preexisting incomplete/mismatched directories and must not resume a
Stringmol process from checkpoints. Failed or extinct runs remain in the
denominator.

## Integrity criteria

Every run must satisfy all of the following:

1. exactly one valid `END` row exists; process success and its timestep/population
   agree with the simulator exit;
2. initial event IDs exactly equal unique tick-0 snapshot IDs and the 140-agent
   expected inoculum;
3. every birth child ID is unique, nonnegative, at most `2^31-1`, greater than
   both parent IDs, and absent from initial IDs and earlier births;
4. every parent ID was previously introduced by INIT or BIRTH;
5. the two-parent and passive-parent graphs are acyclic;
6. every non-initial snapshot ID has `birth_tick < snapshot_tick`; INIT IDs alone
   may appear at tick 0;
7. event species, labels, positions, and sequences parse losslessly, and every
   child label equals the explicitly logged passive-parent event-time label;
8. every logged successful child is assigned a species and in-bounds grid
   position;
9. every snapshot has unique IDs, unique occupied cells, in-bounds positions, and
   exactly the complete expected tick set `0,100,...` strictly before verified
   extinction, or `0..4900` for a nonextinct run;
10. population counts reconstructed from snapshots equal `popdy001.dat` both in
    total and per species at every expected snapshot tick; and
11. source, patch, binary, matrix, config, seed, input-manifest, and post-run
    inventory hashes verify exactly.

Any integrity failure makes the campaign unevaluable, not negative.

## Frozen outcomes and acceptance

Roots have depth 0. Descendants are strictly non-initial IDs reachable through a
birth edge. Final descendant fraction is non-initial descendant count divided by tick-4,900
population. A present tick-4,900 snapshot is authoritative even if later
extinction occurs; only verified extinction by timestep 4,900 defines both count
and fraction as zero.
For a zero-birth run, passive-sequence match fraction is reported as null.

For each run report successful birth count, unique active/passive parents,
passive-sequence match and mismatch counts/fraction, maximum two-parent and
passive depths, analytical final population, final strict non-initial descendants,
and final descendant fraction.

SM-L001 passes only if:

1. observation isolation and deterministic repeat pass;
2. all 20 runs pass integrity;
3. the same at least 8/10 host seeds jointly record at least 100 successful
   births, reach two-parent depth at least 2, and have at least 100 strict
   non-initial descendants with final fraction at least 0.5 at tick 4,900;
4. all 10 inert runs record exactly zero successful births; and
5. no inert run reaches lineage depth 2.

Thresholds establish a live multigenerational positive control and a noncopying
negative control; they do not compare host and inert fitness statistically.

## Decision ladder

- **Pass:** native cleavage birth and individual lineage identity are validated.
  Preregister a separate Stringmol conservation-boundary design; do not add
  conservation retrospectively to these runs.
- **Fail with valid integrity:** biological gate failure; do not integrate
  conservation. Audit whether the pinned host/config or inert control lacks the
  required native positive/negative behavior, then choose a new substrate or
  separately preregistered baseline.
- **Unevaluable:** any process, build, observer, integrity, or artifact failure.
  Repair only that defect and rerun the complete 20-run matrix with unchanged
  inputs, seeds, and thresholds. No selective retry, replacement seed, or reuse of
  partial runs is permitted.
