# SM-C002 decay-recycling implementation

**Prepared:** 2026-09-30  
**Preregistration commit:** `5cce74b`  
**Status:** mechanics gates passed; 40 unseen scientific inputs prepared; launch seal pending implementation commit/push

## Implementation

- Added `experiments/stringmol/patches/0004-add-decay-routing-and-material-journal.patch` after patches 0001–0003.
- Added exact per-symbol inaccessible waste accounting and decay-only routing to
  accessible pool or waste. Copy, failed-placement, and cleavage-discard returns
  retain their frozen accessible-pool route.
- Added versioned `conservation002.csv`, `conservation_buffers002.csv`, and
  `material_events002.csv` observation under explicit routing. Missing routing
  remains on the byte-exact patch-0003 path.
- Added ordered material-event replay, exact pool/waste reconciliation, checkpoint
  and END full-buffer validation, late growth-byte/birth endpoints, funding lower
  bounds, and the frozen full/partial decision predicates.
- Added a six-worker runner with no-resume enforcement and a separate launch seal.
  Launch re-audits held-out seeds, verifies committed implementation bytes, and
  queries the configured `origin/main` remote directly before any scientific
  process starts.

Primary files:

- `experiments/stringmol/decay_workflow.py`
- `experiments/stringmol/analyze_decay.py`
- `tests/stringmol_decay_directed.cpp`
- `tests/test_stringmol_decay.py`

## Mechanics and isolation evidence

Fresh canonical artifacts are under `runs/sm_c002_work/`:

- build: `review-fixes-builds/build.json`;
- lineage build/isolation: `review-fixes-lineage-builds/build.json` and
  `review-fixes-lineage-isolation/isolation.json`;
- mechanics gates: `review-fixes-gates/gates.json`;
- sealed preparation: `prepared/preparation.json`.

The final gates passed:

- both fresh upstream suites: 79 assertions in 15 cases each;
- 231 focused Python tests;
- scoped mypy clean across ten files;
- directed C++ routing/replay mechanics;
- absent and disabled patch-0003 parity;
- explicit recycle projection parity;
- no-decay recycle/sequester equivalence;
- observer isolation and deterministic repeats;
- exact event replay, nonnegative pool/waste, and zero residual;
- release-object and directed-linkage provenance.

Repository-wide `just test` separately passed 849 main tests and 105 organism-sim
tests.

## Review repairs before launch

Independent review found and closed three launch/replay gaps:

1. held-out seed freshness was initially checked only during preparation;
2. push verification initially relied on local upstream refs rather than direct
   remote confirmation; and
3. accepted-copy replay separately capped withdrawals/returns but did not cap the
   union of changed positions at the native maximum of two.

Launch now repeats and seals the seed audit, directly verifies the intended remote
URL/ref/revision, and fails closed. Replay counts distinct changed positions, with
an adversarial regression fixture. Final review approved the implementation for
precommit.

## Prepared execution boundary

The canonical preparation contains exactly 40 read-only configs for paired seeds
`202622000`–`202622019`; all 40 output directories were absent. A fresh scan of
10,934 historical files found no prior seed use. All 948 artifact-record checks
matched. No launch, campaign, or outcome receipt exists.

Per the preregistration, scientific execution remains prohibited until this
implementation is committed and pushed and the launch-time remote/seed seal
passes.
