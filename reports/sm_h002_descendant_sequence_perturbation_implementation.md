# SM-H002 descendant sequence perturbation implementation

**Prepared:** 2026-10-01  
**Preregistration commit:** `f80cce7`  
**Status:** mechanics/source/configuration gates passed; 60 unseen assays sealed; launch pending commit/push

## Implementation

No simulator mechanics changed. Added:

- `experiments/stringmol/perturbation_panel.py` for independent SM-H001 source
  verification, candidate selection/deduplication, deterministic SHA-256 shuffles,
  and sealed panel construction;
- `experiments/stringmol/analyze_perturbation.py` for candidate/support
  material-source cohort propagation, qualifying renewal metrics, paired
  exact/shuffle specificity, and frozen context decisions;
- `experiments/stringmol/perturbation_workflow.py` for custom exact/shuffle ×
  self/support configs, fresh inherited gates, six-worker no-resume execution,
  direct remote launch verification, and launch-time seed audit;
- `tests/test_stringmol_perturbation.py` and the pinned source-candidate fixture
  `tests/fixtures/sm_h002_source_candidates.json`.

The implementation independently reproduced the 20 H001 selected-source records,
deduplicated them into the frozen 15-genotype panel, and generated 15 distinct
composition-preserving shuffles. The panel contains one canonical and 14
noncanonical genotypes with 20 retained source provenances.

## Frozen evidence

Canonical artifacts:

- build: `runs/sm_h002_revision/builds/build.json`;
- gates: `runs/sm_h002_revision/gates/gates.json`;
- preparation: `runs/sm_h002_work/prepared/preparation.json`;
- summary: `runs/sm_h002_work/evidence.json`.

Validation passed:

- six fresh upstream suites plus inherited lineage, conservation, decay-routing,
  renewal, isolation, and deterministic gates;
- 418 focused Python tests;
- strict scoped mypy across 17 files;
- byte-exact canonical custom-config/output parity;
- independent H001 source analysis hash reproduction;
- panel selection, deduplication, shuffle encoding, config load order, positions,
  cohort ID ranges, and exact/shuffle histogram/material equality;
- synthetic whole-transfer, cohort/source-lineage separation, cross-cohort,
  unknown/conflict, extinction, threshold, ratio, and decision fixtures;
- build/object/config/artifact hash verification.

A seed audit scanned 22,521 files and found no prior assay-seed use. One historical
CSV counter equaled `202624012`; its file, manifest, config, run seed, field,
offset, and hashes are pinned as a non-seed numeric coincidence. Adversarial tests
reject changed content, column, offset, multiplicity, or location rather than
silently exempting the file.

Independent review reproduced panel/shuffle/config/material properties, verified
the documented counter coincidence, checked the full source/build/gate/
preparation chain, and found no prelaunch blocker.

## Sealed boundary

The preparation contains 15 genotype blocks and 60 read-only assay configs:
EXACT_SELF, SHUFFLE_SELF, EXACT_SUPPORT, and SHUFFLE_SUPPORT on paired unseen
seeds `202624000`–`202624014`. All output directories and launch/campaign receipts
were absent. Scientific launch remains prohibited until implementation bytes are
committed, pushed, and directly observed on `origin/main`.
