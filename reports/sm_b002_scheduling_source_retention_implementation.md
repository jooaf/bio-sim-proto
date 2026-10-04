# SM-B002 scheduling × source-retention implementation

**Prepared:** 2026-10-04  
**Preregistration commit:** `0e0d0a9`  
**Status:** mechanics/configuration gates passed; 80 unseen assays sealed

Added environment-gated patch
`experiments/stringmol/patches/0006-add-source-remnant-retirement.patch`, exact
retirement material accounting, rooted transfer-lineage analysis, a four-arm
workflow, and directed/adversarial fixtures. No unseen assay seed was executed.

RETIRE operates after stable native child placement/healing/cleanup and before
generic completion. It owns completion, removes only the verified extant material
source, returns all full-buffer matter to the accessible pool once, preserves and
schedules any extant nonsource survivor exactly once, and emits linked boundary
and material records. RETAIN/disabled paths preserve patch-0005 bytes and RNG.

Validation passed:

- full inherited upstream, conservation, recycling, renewal, perturbation,
  replicated, mutation, and scheduling suites;
- 1,016 focused tests and strict mypy;
- active/passive source, cleanup, hidden-tail, list/grid, survivor, orphan,
  relocation, exposure, and decision fixtures;
- exact RETAIN shared-output/final-RNG parity and deterministic repeats;
- independent boundary, material, pool, source, scheduling, and rooted transfer
  replay; and
- 114 real-phase fault cases: 48 rollback, 30 publication/free, and 36 journal-
  write failures, proving no accepted partial retirement or RETAIN fallback.

An initial validation attempt hit a disposable `/tmp` pytest quota; no scientific
input executed. After cleanup, all validation was rerun, corrected fault coverage
was independently audited, builds/gates were regenerated, and the full 80-input
preparation was resealed. Superseded development artifacts are retained under the
ignored `logs/sm_b002_revision_archive/`.

Canonical evidence:

- `reports/sm_b002_implementation_evidence.json`;
- `runs/sm_b002_work/prepared/preparation.json`; and
- build/gate records referenced by that preparation.

Independent review found no residual prelaunch blocker and confirmed zero unseen
execution. Launch remains prohibited until committed bytes are pushed and directly
observed on `origin/main`, followed by the mandatory fresh seed audit.
