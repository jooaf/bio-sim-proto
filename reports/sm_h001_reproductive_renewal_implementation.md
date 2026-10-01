# SM-H001 reproductive-renewal implementation

**Prepared:** 2026-09-30  
**Preregistration commit:** `6d69824`  
**Status:** mechanics/analysis gates passed; 30 unseen inputs sealed; launch pending commit/push

## Implementation

SM-H001 changes no simulator source or chemistry. It adds:

- `experiments/stringmol/analyze_renewal.py`: independent stable-cleavage source
  inference, ordered suffix validation, productive population-increasing birth,
  qualifying/orphan source lineage, renewal/depth, late-window, and positional
  inherited-byte retention analysis;
- `experiments/stringmol/renewal_workflow.py`: fresh inherited build/gate
  verification, 20-host/10-inert input preparation, six-worker no-resume runner,
  direct `origin/main` launch verification, and launch-time held-out seed audit;
- `tests/test_stringmol_renewal.py`: synthetic/adversarial source, transfer,
  lifecycle, depth, retention, extinction, decision, artifact, and launch tests.

The analyzer starts from tick-0 full buffers and independently replays the complete
version-2 material journal. Active/passive lineage labels do not determine source.
Whole-parent transfers and their descendants remain valid native IDs but outside
the qualifying source lineage unless a later productive edge has an initial or
already qualifying source.

## Frozen evidence

Canonical artifacts:

- build: `runs/sm_h001_revision/builds/build.json`;
- gates: `runs/sm_h001_revision/gates/gates.json`;
- sealed inputs: `runs/sm_h001_work/prepared/preparation.json`.

Final validation passed:

- both fresh upstream suites and all inherited lineage/conservation/decay gates;
- exact development-output parity with the inherited SM-C002 workflow;
- complete development replay: 592 productive births, 21 renewing descendants,
  101 serial source births, depth 3, 11 retained late renewals;
- 318 focused Python tests;
- strict scoped mypy across 13 files;
- synthetic active/passive source, suffix, whole-transfer, orphan, retention,
  lifecycle, and decision fixtures;
- 17 native-lifecycle adversarial cases, while the superseded replay behavior
  failed nine of them as expected;
- fresh scan of 17,319 historical files with no held-out seed match.

Independent review found one prelaunch defect: the first analyzer removed every
empty-visible cleavage participant, while native `AgentCheckZeroLengthString`
removes the active participant first and returns, leaving an empty passive partner
when both are empty. Replay now exactly follows native active-first single-parent
cleanup and preserves hidden tails. Fresh gates/preparation were regenerated, and
final review found no remaining blocker.

## Sealed boundary

The preparation contains 20 canonical host configs for seeds
`202623000`–`202623019` and ten one-symbol-B inert controls for seeds
`202623000`–`202623009`. All 30 output directories and launch/campaign receipts
were absent. Inputs are read-only and all artifact records verify.

Scientific launch remains prohibited until these implementation bytes are
committed, pushed, and directly observed on `origin/main` by the launch seal.
