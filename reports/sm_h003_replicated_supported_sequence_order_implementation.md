# SM-H003 replicated supported sequence-order implementation

**Prepared:** 2026-10-02  
**Preregistration commit:** `10ae455`  
**Status:** 90 unseen assays sealed; launch pending committed implementation

No simulator mechanics changed. Added:

- `experiments/stringmol/analyze_replicated.py` for three-pair genotype
  aggregation, same-pair specificity, all-three directional checks, canonical
  exclusion, and whole-population positive control;
- `experiments/stringmol/replicated_workflow.py` for the exact 90-run matrix,
  fresh inherited gates, immutable preparation, direct remote launch seal,
  no-resume six-worker execution, and repeated seed audit; and
- `tests/test_stringmol_replicated.py` for matrix, thresholds, aggregation,
  control, integrity, configuration, audit, and decision boundaries.

Fresh validation passed six upstream/inherited suites, 550 focused tests, strict
mypy across 20 files, source/panel/shuffle reproduction, canonical exact parity,
whole-population development replay, cohort/source replay, exact material/config
comparisons, and adversarial launch/audit fixtures. A fresh audit scanned 30,228
files and found no prior use of seeds `202625000`–`202625044` outside the 92
authorized sealed input files.

Independent read-only review verified the complete gate/preparation chain, exact
matrix and scientific rules, and confirmed no output directories, inventory
receipts, or launch/campaign files. Canonical evidence is in:

- `runs/sm_h003_work/builds/build.json`;
- `runs/sm_h003_work/gates/gates.json`;
- `runs/sm_h003_work/prepared/preparation.json`; and
- `runs/sm_h003_work/evidence.json`.

Launch remains prohibited until these implementation bytes are committed, pushed,
directly observed on `origin/main`, and followed by the mandatory launch-time
seed audit.
