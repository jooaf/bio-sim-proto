# Pinned Spatial Stringmol control

This directory builds an external, independently published artificial chemistry for the retained Phase 2 parasite gate. It is an ecological control, not part of the conserved BFF simulator.

## Build

```nu
nu experiments/stringmol/bootstrap.nu --test
```

The bootstrap script:

1. clones `source.lock.json`'s exact upstream commit into ignored `vendor/stringmol/`;
2. applies the reviewed patch series from `patches/`;
3. builds the release binary;
4. optionally runs the upstream Catch test suite and requires its pass marker.

The upstream checkout and generated runs are intentionally not committed.

## Patch policy

Patches may repair reproducibility defects and expose locality controls. They must not change Stringmol binding scores, opcodes, mutation, decay, copy, or cleavage chemistry.

The current patch:

- fixes an upstream missing-braces/counter defect that returned the first eligible spatial neighbor instead of the randomly drawn neighbor;
- adds `INTERACTION_RADIUS` and `PLACEMENT_RADIUS` configuration fields;
- preserves radius 1 as the upstream default;
- uses radius 0 as an explicit global/well-mixed control;
- writes both fields into checkpoint configurations.

## Scientific order

1. Validate a fixed source-grounded parasite candidate in parasite-alone and host-plus-parasite global controls.
2. Freeze the candidate and inoculum before comparing locality.
3. Require the large-radius/global positive control to pass before interpreting a local treatment.
4. Keep all failures and exact source/config/output hashes.

See `reports/phase2_replacement_host_parasite_audit.md` for the audit and limitations.

## SM-L001 individual lineage workflow

`reports/sm_l001_native_reproduction_lineage_preregistration.md` is the frozen
protocol. `lineage_workflow.py` provides separate build, isolation, preparation,
and execution commands; preparation does not launch any matrix process.

```sh
uv run python -m experiments.stringmol.lineage_workflow build --root runs/sm-l001/builds
uv run python -m experiments.stringmol.lineage_workflow isolation --build runs/sm-l001/builds/build.json --root runs/sm-l001/isolation
uv run python -m experiments.stringmol.lineage_workflow prepare --build runs/sm-l001/builds/build.json --isolation runs/sm-l001/isolation/isolation.json --root runs/sm-l001/prepared
```

The build command creates two fresh detached clones of the pinned local upstream
repository, applies patch 0001 to baseline and patches 0001/0002 to observer, runs
the upstream Catch suite for each, and rebuilds release binaries after the suite's
clean/debug build. It saves compiler versions, explicit release flags, source
commit/tree/diff and tracked-file hashes, patch bytes/order, test/build logs, and
binary/matrix hashes. It never edits the existing vendor checkout.

Isolation runs only seed 202619999 using one absolute config and four new
working directories. Every regular output file, including stdout and stderr,
participates in exact filename-set and SHA-256/size parity. The only permitted
extras are `lineage_events001.csv` and `lineage_snapshots001.csv`; the repeated
enabled run must match everything. A failed gate stops before preparation.

Preparation writes all 20 configs and a read-only, exclusively created
`preparation.json` plus its hash receipt. It records exact config bytes, commands,
allowlisted environment, implementation hashes, source state, both builds,
isolation provenance, and expected IDs/cells. Every input is verified before
execution. Only the following separate command launches the frozen matrix:

```sh
uv run python -m experiments.stringmol.lineage_workflow run --manifest runs/sm-l001/prepared/preparation.json
uv run python -m experiments.stringmol.analyze_lineage runs/sm-l001/prepared/preparation.json
```

The runner uses six workers, refuses any existing campaign/run tree, and does not
resume or selectively retry. Failed exits and timeouts retain stdout/stderr and
all outputs. Each complete regular-file inventory and exit status is stored in a
sibling `SEED.inventory.json`, outside its inventoried directory to avoid a
self-hash exclusion. The campaign retains all 20 entries. An interrupted campaign
is unevaluable and requires an entirely fresh preparation and complete matrix.
The analyzer verifies provenance/inventories before evaluating the individual
DAG, per-species populations, checkpoints, END, and the joint host thresholds.

### Patch 0002 observation review

Patch 0002 adds code only to `src/sm_spatial.cpp`. Its four call sites are after
configuration/placement (INIT), at the existing population-report checkpoint
(snapshot), inside the successful cleavage-placement branch before append and
parent healing (BIRTH), and after normal loop exit using the existing `timestep`
and `ct` values (END). Failed placement and zero-length cleavage cannot reach the
birth hook. Species fields read the current upstream assignments; sequences read
the event-time C strings, including modified parent bytes before healing.

The helpers use const agent pointers and a separate sorted pointer vector for
snapshots. They do not call the RNG, update agent/grid/species state, or change
existing branches, timing counters, placement, or configuration. Only an exact
`STRINGMOL_LINEAGE_LOG=1` enables append-mode CSV files. Labels are decimal byte
values, sequences are uppercase two-digit hex per byte, and absent identities
use the frozen `-1` sentinels. Missing/truncated observation is an integrity
failure. The END population comes directly from the simulator's exit-loop count;
the tick-4900 snapshot remains authoritative after later extinction.

The committed SM-L001 preregistration is independently pinned at revision
`46c13846558a64fe61a6cae75945d0cd9994751b`, SHA-256
`cf093cb2ad26fecea39fea925da2944c6e6e1d4adc30b2ceaa72b6779a3e64b1`.
Build and preparation manifests include its committed bytes, hash, and revision;
verification checks the Git object and working file against that pin separately
from repository state. Parent event labels and snapshot labels must match each
identity's introduction label. END population cannot exceed either the number
of introduced identities or the last snapshot's population plus births at or
after that snapshot's tick, since snapshots precede tick execution. These bounds
do not replace the authoritative tick-4900
endpoint or change the later-extinction rule.

## SM-C001 conservation preparation

`patches/0003-add-exact-spatial-symbol-conservation.patch` applies after 0001 and
0002. It adds spatial full-buffer symbol accounting, atomic copy transactions,
stable-state cleavage differences, and full-buffer decay returns. Conservation
is enabled only by `STRINGMOL_CONSERVATION=1`, with canonical
`STRINGMOL_POOL_MODE` and `STRINGMOL_POOL_AMOUNT`. The original disabled copy path
remains available for byte-for-byte compatibility checks. Enabled substitution
rejects native draw-zero invalid indexing as an integrity failure. Dispatch and
cleavage validate allocated pointer bounds before access; deletion retains native
completion effects before rejecting an unsafe resulting instruction pointer.
These faults exit nonzero. Upper-endpoint insertion still selects native NUL and
may contract a buffer; the analyzer imposes no positive-net-growth assumption.

The two additional files are `conservation001.csv` and
`conservation_buffers001.csv`. Their schema uses ALXII order, hex-encoded symbol
column suffixes, canonical decimal integers, ASCII LF lines, and uppercase
`2 * maxl0` buffer hex. Checksums cover exact raw file bytes. The independent
analyzer reconstructs every checkpoint and END histogram, validates lineage
identity/prefix evidence, reconciles gross pool exchanges, rejects boundary
errors, and checks reported all-time minima against initial/observed pools and
interval withdrawals. Directed source fixtures verify minima updates between
observations, native branch/RNG parity, and scarcity rollback.

Build, gate, prepare, and execute are separate actions. Example preparation
(the directories must be new):

```bash
python -m experiments.stringmol.lineage_workflow build --root runs/smc/lineage-builds
python -m experiments.stringmol.lineage_workflow isolation \
  --build runs/smc/lineage-builds/build.json --root runs/smc/lineage-isolation
python -m experiments.stringmol.conservation_workflow build --root runs/smc/builds
python -m experiments.stringmol.conservation_workflow gates \
  --build runs/smc/builds/build.json --root runs/smc/gates \
  --lineage-build runs/smc/lineage-builds/build.json \
  --lineage-gate runs/smc/lineage-isolation/isolation.json
python -m experiments.stringmol.conservation_workflow prepare \
  --build runs/smc/builds/build.json --gates runs/smc/gates/gates.json \
  --root runs/smc/prepared
```

The gate action runs focused pytest/mypy, the C++ mechanics fixtures, and all
500-step compatibility variants. Preparation verifies committed SM-C001 and
inherited SM-L001 pins, source/build/patch/test inventories, every release object,
the exact directed-test linkage receipt, gate artifacts,
configs, sanitized environments, commands, and initial buffers/pools/totals.
It creates twenty read-only input configs and a sealed preparation manifest;
it launches no scientific simulation. The separately invoked `run` action uses
six workers, preserves failed processes in the denominator, and rejects resume
or selective retry. `analyze_conservation` validates completed inventories and
reports the frozen paired outcomes with ties retained in the ten-pair denominator.

## SM-C002 decay routing (preparation only)

The committed protocol is `reports/sm_c002_decay_recycling_preregistration.md`.
Apply `0004-add-decay-routing-and-material-journal.patch` after unchanged patches
0001–0003. `STRINGMOL_DECAY_DESTINATION=recycle|sequester` is effective only with
`STRINGMOL_CONSERVATION=1`. Missing routing retains conservation-v1 outputs;
disabled conservation ignores routing. Invalid enabled routing/configuration
fails before simulation. Only native decay enters waste; copy, failed placement,
and cleavage discard still return to the accessible pool.

Explicit routing emits exactly `conservation002.csv`,
`conservation_buffers002.csv`, and `material_events002.csv`. The v2 aggregate
retains the v1 columns as its prefix; `decay_returns` in that prefix is the total
removed histogram, identical to `decay_removed`, while `decay_to_pool` and
`decay_to_waste` give its destination. Waste, per-symbol zero residuals, growth
and contraction **byte** totals, and event count follow the v1 prefix. There is
no route metadata in these files, so the no-decay serializer fixture requires
all output bytes to match. `STRINGMOL_CONSERVATION_LOG=0` suppresses all three
files while retaining conservation checks and native/lineage behavior.

The journal begins from the canonical tick-zero full buffers. Each row contains
sorted before/after participating IDs, sparse `ID:offset:old:new` byte changes
(including `00`), and an uncommitted proposal for scarcity-blocked copies.
Removed IDs are zeroed; new IDs start from an all-zero allocated buffer.
`CLEAVE/PLACED`, `CLEAVE/FAILED`, and `CLEAVE/NO_CHANGE` describe stable outcomes;
the difference between their full-buffer histograms records every actual
cleavage-discard or failed-placement return. Transient child duplication is
excluded. Each decay member has a separate ordered removal. All copy completion
categories are recorded, so replay derives the entire counter partition as well
as exchanges, growth, contraction, lifecycle, and both material ledgers.

Use `python -m experiments.stringmol.decay_workflow` with separate `build`,
`gates`, and `prepare` actions. Gates require fresh SM-L001 build/isolation
manifests via `--lineage-build` and `--lineage-gate`. Preparation verifies the
committed protocol, all build inputs and release objects, development gates,
schemas, and prior seed use, then seals forty read-only configurations for paired
seeds 202622000–202622019. It never executes them. The separate `run` action
pins the intended `origin` URL and `refs/heads/main` at preparation, then requires
HEAD to equal a direct `git ls-remote` observation of that remote/ref at launch.
A stale local tracking ref cannot authorize execution; missing, ambiguous,
unreachable, changed-URL, or mismatched remote observations fail closed.
Immediately before the final `launch.json` seal, it repeats the held-out freshness
audit, excluding only the verified manifest, digest, and forty config files.
Other artifacts inside that directory remain in scope. The launch seal binds
full audit evidence and its canonical hash, remote URL/ref/observed revision and
raw query response, and the exact committed input bytes. Verification checks
these bindings and historical audit input hashes without treating later
scientific outputs as earlier seed use. The runner refuses
resume/selective retry, and limits concurrency to six. Analyze a completed
campaign with `python -m experiments.stringmol.analyze_decay MANIFEST`.
