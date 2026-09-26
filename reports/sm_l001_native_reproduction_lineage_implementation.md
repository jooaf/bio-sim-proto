# SM-L001 native reproduction/lineage implementation readiness

**Status:** Prepared; unseen 20-run matrix not executed.

Implemented:

- environment-gated append-only individual INIT/BIRTH/END events;
- report-aligned extant individual snapshots;
- pre-healing active/passive sequences and immutable labels on birth events;
- inert `B` condition using the same 140 positions as the host;
- fresh baseline and observer builds from the pinned upstream commit;
- complete output-set/byte isolation checks and deterministic observer repeat;
- immutable build/isolation/config preparation manifests;
- fail-closed six-worker execution and complete post-run inventories; and
- independent individual-DAG, snapshot, extinction, population/species, and
  acceptance analysis.

Validation:

- both fresh upstream builds passed 79 assertions in 15 test cases;
- observation isolation passed against the patch-0001-only baseline;
- enabled observation added only the two declared CSV files;
- the enabled repeat was byte-identical;
- 81 focused tests passed, including label, END-bound, protocol-pin, malformed
  artifact, extinction, concurrency, and acceptance-boundary cases;
- scoped mypy and `git diff --check` passed;
- 20 unseen configs were generated and verified without creating a campaign run
  tree.

Frozen preparation:

`runs/sm_l001_review_fixes/prepared_end_bound/preparation.json`

The preparation independently pins the committed preregistration at revision
`46c13846558a64fe61a6cae75945d0cd9994751b`, both patch byte streams, source,
compiler/build records, observer implementation, isolation evidence, environment,
matrix, commands, and every generated config.

No unseen seed was executed and no scientific outcome was inspected before the
implementation commit.
