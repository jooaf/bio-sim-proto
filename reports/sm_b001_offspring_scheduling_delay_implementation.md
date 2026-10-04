# SM-B001 offspring scheduling-delay implementation

**Prepared:** 2026-10-04  
**Preregistration commit:** `a1debdc`  
**Status:** mechanics/configuration gates passed; 60 unseen assays sealed

Added environment-gated patch
`experiments/stringmol/patches/0005-add-offspring-scheduling-delay.patch`, an
independent analyzer/workflow, directed C++ fixtures, and Python decision/
integrity tests. No unseen assay seed was executed.

The patch adds checked offspring eligibility ticks while preserving physical
cleavage, source healing, identity, placement, material routing, occupancy, and
native decay. Before eligibility a policy child receives its normal top-level
decay attempt but cannot seek or be selected as a partner. Eligible partner sets
are filtered before the one native selection draw. The ordered scheduling journal
records policy-child processing, searches, encounters, binding, dispatch,
lifecycle, and END censoring without RNG draws.

Validation passed:

- exact absent/disabled/IMMEDIATE shared-output and final-RNG parity against fresh
  patch-0004 builds;
- deterministic repeats for all three policies;
- directed active/passive source, delay boundary, pre-eligibility exclusion,
  decay, recursive child, hidden-tail, and transfer-lineage fixtures;
- fresh inherited upstream, lineage, conservation, recycling, renewal,
  perturbation, replicated, and mutation gates;
- 813 focused Python tests and strict mypy across 26 files;
- independent material, source-lineage, scheduling-lifecycle, END-state, and
  policy-decision replay with zero boundary errors; and
- exact parse/hash/material checks for 20 matched IMMEDIATE, DELAY500, and LOCKED
  blocks.

A seed audit scanned 51,594 historical files and found no held-out seed use. One
hash-pinned historical CSV counter numerically equaled `202627000`; it is recorded
as a non-seed field coincidence and guarded adversarially. Full preparation and
audit evidence are outside Git in `runs/sm_b001_work/prelaunch/`.

The sealed preparation is
`runs/sm_b001_work/prepared/preparation.json`: 60 configs plus manifest and digest,
all read-only, with no output directories or launch/campaign receipts. Independent
read-only review found no prelaunch blocker. Launch remains prohibited until the
implementation is committed, pushed, directly observed on `origin/main`, and a
fresh launch-time seed audit passes.
