# SM-M001 mutation baseline implementation

Prepared against committed preregistration `c3030c1a36f6c5e9de99e2cbf5f3d9bab22e062a`.
No preregistration, registry, upstream source, patches, or simulator mechanics were
edited during preparation. The implementation was subsequently committed and
pushed as `7539813`; the sealed campaign then executed once. See
`reports/sm_m001_mutation_baseline_report.md` for the outcome.

`experiments/stringmol/mutation_workflow.py` adds the exact 20-pair NATIVE/ZERO
matrix, strict rendered-config equality and independent loader parsing, complete
initial per-symbol comparisons, both-arm development repeatability, static RNG
semantics verification, inherited fresh gates, immutable preparation, and the
H003 launch protections. Launch requires clean committed bytes, a direct
`origin/main` observation, a repeated held-out seed audit, and absence of every
execution/resume marker before any launch seal is written. Execution is capped
at six workers with `NUMBA_NUM_THREADS=1`.

`experiments/stringmol/analyze_mutation.py` calls H001's independent replay
unchanged. It adds complete visible birth-sequence identities keyed by bytes and
length, abundance-weighted Hill q=1, exact/noncanonical counts and fractions,
q=0/unique sequences, length distributions, renewing-descendant birth filtering,
first-source retention summaries, and the frozen decision ladder. H001's renewal
counters retain their original definitions; primary sequence endpoints separately
exclude whole-parent transfers, orphan-source births, and other nonproductive
births. Excluded edges remain individually reportable.

All scalar sequence endpoints receive paired signed differences, direction
counts, and median differences. Distribution endpoints additionally receive
pointwise abundance comparisons over their observed support. Missing retention
medians/minima remain JSON null, distinct from ties; empty distributions stay
empty. Every aggregate retains the 20-pair denominator and reports the number of
observed differences. The fair-coin tail is descriptive, not a p-value for the
composite gate. Neither diversity nor operational viability is an adaptation,
variant-fitness, or equivalent-performance claim.

`tests/test_stringmol_mutation.py` covers sequence/length identity, abundance,
renewal filtering, empty sets, retention, every renewal boundary, the same-pair
16/20 conjunction, discordance, every decision branch, strict config settings,
resealed input tampering, seed audits, direct remote observations, no-resume
markers, six-worker receipts with a mocked executor, and static RNG semantics.

## Loader path constraint found during validation

The first development-only inherited gate stopped with an incomplete snapshot
checkpoint set. The pinned loader uses `strcpy` into `char swt_fn[80]`; the
112-byte nested SUBMAT path overwrote the reporting interval. Its native output
recorded `REPORTEVERY 1229543500` instead of 100. The failed evidence is preserved
under `runs/sm_m001_work/gates/`, with its initial builds under
`runs/sm_m001_work/builds/` and `runs/sm_m001_work/lineage-build/`.

The workflow now rejects every prospective build matrix path of 80 or more
bytes, including the supplied lineage package, before building. Fixtures cover
both 79-byte acceptance and 80-byte rejection. Fresh builds use `/tmp/smm1l` and
`/tmp/smm1b`; this corrects an artifact-layout defect without changing simulator
code or scientific settings. These build roots must remain available for seal
verification. The failed long-path artifacts are not authorized assay inputs.

## Validation and sealed evidence

The combined focused suite passed **647 tests** in 221.48 seconds; strict mypy
passed across **23 files**. Logs and exact commands are recorded in
`runs/sm_m001_work/gates-short/pytest.txt`, `mypy.txt`, and the gate manifest.
The six accepted fresh upstream suites each passed 79 assertions in 15 cases.

All inherited gates, both-arm repeatability, independent development replay,
static RNG semantics, and preparation verification passed. Both development arms
reached step 5,000 with exit status 0 and exact within-arm repeat-output equality.
No cross-arm output equality is asserted.

The sealed preparation contains exactly 40 configs plus its manifest and digest:
42 read-only files, with no assay output directories, receipts, launch seal, or
campaign files. A post-preparation audit checked 41,774 files,
exempted only those 42 authorized inputs, and found no held-out seed matches.
No existing tracked file was changed. No unseen seeds were executed, and no
commit or push was performed.

Evidence:

- Fresh lineage build: `/tmp/smm1l/build.json`.
- Fresh inherited builds: `/tmp/smm1b/build.json`.
- Gates: `runs/sm_m001_work/gates-short/gates.json`.
- Sealed inputs: `runs/sm_m001_work/prepared/preparation.json`.
- Compact evidence receipt: `runs/sm_m001_work/evidence.json`.

Preparation SHA-256:
`492d38345f1d51d7835ac54a71f1168d0ac883cfca5a002818408474f97b04b1`.

Launch remains prohibited until the implementation is committed and pushed,
committed bytes are directly verified on `origin/main`, and the launch-time
held-out audit passes. Those actions were not performed.
