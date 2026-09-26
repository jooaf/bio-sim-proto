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
