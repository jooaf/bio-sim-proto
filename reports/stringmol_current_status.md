# Current Stringmol program status

## SM-B002: complete, verified, not a strong-dependence result

Authoritative completed attempt: SM-B002-R2, source
`f2eda7ed620aa2e6afc5c89b51b583e758a4f4f7`.

- All 80 executions succeeded; longest execution-plus-inventory time 29.92 seconds.
- All 42 previously completed R1 outputs matched R2 byte-for-byte.
- Independent ordered replay passed; repeat analysis was byte-identical.
- All outcomes retained; portable control export checksum-verified.
- Closure: 2026-11-06 05:31:03 -06:00.
- Decision: branch 8, **Intermediate response**, integrity true, no analysis failures.

| Schedule | RETAIN continuity | RETIRE continuity | RETIRE exposure |
|---|---:|---:|---:|
| Immediate | 18/20 | 5/20 | 20/20 |
| Delay 500 | 18/20 | 8/20 | 20/20 |

These are frozen threshold classifications and descriptive paired outcomes, not a
formal interaction test or a binary necessity claim. R1 remains preserved as an
unevaluable operational attempt; it is not pooled into R2. No R3 was needed or run.

Raw data, full/repeat analyses, decisions and source bundle:
`/run/media/jojo/Elements/bio-sim-results/sm-b002-r2/`.

## SM-B003: design and mechanical selector qualification only

The user requested autonomous continuation. B002 permits separate admission-stage
design, not automatic admission execution. The candidate protocol is in
`sm_b003_admission_replacement_design.md`; native integration findings and the
probe receipt are in `sm_b003_admission_native_integration_notes.md`.

The six proposed arms cross both schedules with native vacancy, stratified reject,
and stratified replace; source RETAIN is fixed. A prospective half-occupied/half-
vacant challenge avoids pretending that a vacancy-first fallback establishes
replacement exposure. Replacement-only ancestry excludes all vacancy/relocation
paths and is reported separately from population expansion and all-admission renewal.

Completed: 234 focused tests, strict typing, 1,536 independent Python/C++ selector
comparisons and 192 complete native RNG reference-state checks. There have been
**zero SM-B003 population assays**. The native atomic replacement adapter,
independent ordered admission replay, fault/adversarial gates, development
opportunity qualification, final preregistration and held-out execution audit are
still required. Candidate seed reservations are not certified unseen.

The next engineering work is native adapter/replay implementation and qualification,
not rerunning B002, changing its interpretation, or launching an unqualified matrix.
Ordinary raw data stays on Elements; immutable controls use its POSIX image.
Historical BFF acceptance/program documents are not current launch instructions:
**BFF remains closed as NO-GO.**
