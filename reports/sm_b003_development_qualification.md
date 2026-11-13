# SM-B003 development qualification: fixed panel v2

**Integration, independent replay, and development opportunity gates pass.**
This is development evidence, not the frozen 120-input assay or its decision.
B002 remains closed; BFF remains NO-GO. Reserved seeds were not executed.

## Evidence and provenance

- Prospective plan: `sm_b003_development_qualification_plan.md`.
- Builds: `/tmp/sm/b3d2/build.json`; inputs and exact compiler/object/native-source
  records are retained alongside it inside the external POSIX image.
- Controls: `/tmp/sm/b3q2/`; completion receipt `development.json`.
- Raw data: Elements `bio-sim-results/sm-b003-development-v2/`.
- Completion: **2026-11-12T23:37:10.093620+00:00**.
- Full regression: `verification/sm-b003-full-regression-v1/result.nuon`:
  **3,917 passed**, two non-failing warnings, 1,145.02 seconds. The admission
  native cases used ASan/UBSan with leak checks, no suppressions and fresh builds.
- Controller repair tests: `verification/sm-b003-controller-unit-v2/`: 22 passed,
  typing clean across three files.
- Portable export: `verification/sm-b003-development-qualified-v2/portable/`:
  **56,690 regular files** copied and SHA256-verified, covering both development
  controls/builds, the full regression and repaired-controller tests. Per-root
  checksum inventories and `COMPLETE.nuon` are retained. Symlinks and special
  filesystem objects are excluded; all original POSIX artifacts remain intact.

All 20 native executions succeeded. All six observer-on/off comparisons, six
exact repeats, and both patch-0006 NATIVE reference comparisons agreed on
scientific CSV bytes and complete final RNG state. All six observer-on histories
passed independent VM/RNG/grid/list/material/source/species/lineage reconstruction;
each was analyzed again in a separate process, with identical retained results.
Inputs and complete output inventories were verified again after analysis.

Maximum native execution-plus-inventory time: **92.27 seconds**, below the fixed
600-second limit. Total raw bytes: **4,535,625,883**. Analysis remained serial,
with the fixed 1,800-second per-run limit. Per-process elapsed-time and peak-memory
receipts remain in the control directory. These resource limits are not permission
to weaken mechanics or retry biological failures.

## All development outcomes (no selection)

Every row uses the same previously used seed **202620999**, 140 hosts, zero
mutation/pool, recycle routing, global interaction/placement and 5,000 ticks.
Tuple order: qualifying transfers, renewing descendants, serial transfers,
maximum nonrelocation depth, late renewing descendants, retained late renewals.
Unchanged continuity thresholds: **(100, 10, 50, 2, 5, 5)**.

| Schedule / admission | Partial opportunities / commits | All-admission tuple | Replacement-only tuple |
|---|---:|---|---|
| IMMEDIATE / NATIVE_VACANCY | 0 / 0 | (664,25,140,3,6,6) | (0,0,0,0,0,0) |
| IMMEDIATE / STRATIFIED_REJECT | 569 / 0 | (562,18,88,3,4,4) | (0,0,0,0,0,0) |
| IMMEDIATE / STRATIFIED_REPLACE | 531 / 531 | (1059,15,228,3,2,2) | (453,6,36,2,1,1) |
| DELAY500 / NATIVE_VACANCY | 0 / 0 | (613,41,189,3,15,15) | (0,0,0,0,0,0) |
| DELAY500 / STRATIFIED_REJECT | 587 / 0 | (574,44,229,3,6,6) | (0,0,0,0,0,0) |
| DELAY500 / STRATIFIED_REPLACE | 531 / 531 | (1058,37,381,4,16,16) | (423,15,87,2,3,3) |

Both REPLACE arms exceed the predeclared development opportunity floor of 100
verified partial commits. **Neither replacement-only continuity tuple passes all
six thresholds.** Those valid negative development outcomes are retained; they
are not a reason to tune criteria, choose another seed, or rerun selectively.
Replacement ancestry excludes reconnection through vacancy descendants, hence
its qualifying-transfer denominator differs from all occupied partial commits.

## Failed attempt and remaining boundary

Keep v1 raw data (`sm-b003-development-v1/`), controls `/tmp/sm/b3q1/`, and all
build/analysis/error receipts. All its 20 native executions and parity comparisons
passed, but the command logger overwrote scientific analysis outputs with command
receipts. V1 therefore supplies no retained repeat-analysis qualification.
Exclusive pre-launch receipt reservation and distinct `-process` filenames fix
that artifact failure. V2 repeats the **entire unchanged fixed panel**, not a
selected arm or a more favorable seed.

`population_launch_eligible` remains **false**. Remaining gates: source publication,
finalized preregistration/launch controls, fresh
execution-aware unseen-seed audit, and a sealed explicit eligibility receipt.
No frozen SM-B003 matrix has launched. Portable evidence is data/source: Linux
binaries must be rebuilt and requalified before execution on macOS.
