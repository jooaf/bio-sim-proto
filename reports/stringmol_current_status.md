# Current Stringmol program status

Updated 2026-11-16. SM-B002 and SM-B003 are closed. No campaign is currently running.

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

## SM-B003: complete, integrity-valid non-pass

Final decision: **Robust replacement-only continuity not established**.
Recovery source: `15b4bb18d50bd09568a2cdd16f8644734ff2b278`.

| Schedule | Admission | All-admission continuity | Replacement-only continuity |
|---|---|---:|---:|
| IMMEDIATE | NATIVE_VACANCY | 16/20 | 0/20 |
| IMMEDIATE | STRATIFIED_REJECT | 13/20 | 0/20 |
| IMMEDIATE | STRATIFIED_REPLACE | 12/20 | 3/20 |
| DELAY500 | NATIVE_VACANCY | 20/20 | 0/20 |
| DELAY500 | STRATIFIED_REJECT | 16/20 | 0/20 |
| DELAY500 | STRATIFIED_REPLACE | 18/20 | 4/20 |

Native controls passed, and all 40 REPLACE runs had ≥100 partial replacement
commits. Neither replacement-only arm reached the frozen 16/20 robustness gate.
The result is not rescued by all-admission continuity, nor does it establish
that replacement continuity or Stringmol renewal is generally impossible.

All 120 native executions succeeded. The original two-pass analysis rejected 22
inputs due to an independent VM omission of inherited dangling-head cleanup; its
Unevaluable integrity decision remains preserved. Qualified analysis-only recovery
passed all 240 checks, with the original 98 valid results unchanged byte-for-byte.
No native runs, horizons, thresholds, or criteria were changed or selectively retried.

Final decision: 2026-11-15T23:47:29Z. Portable export: 2026-11-16T00:16:04Z,
69,516 checksum-verified regular files across nine evidence roots. Original
POSIX controls and failed attempts remain intact.

Full report: [`sm_b003_admission_replacement_closeout.md`](sm_b003_admission_replacement_closeout.md).
Raw: `/run/media/jojo/Elements/bio-sim-results/sm-b003-v1/`.
Portable controls/source bundle:
`/run/media/jojo/Elements/bio-sim-results/verification/sm-b003-analysis-recovery-c3a2/`.

## Next work: distinct exploratory questions, not SM-B003 retries

The user requested two independent exploratory agents. The existing roadmap is
[`stringmol_bff_comparative_deep_dive_program.md`](stringmol_bff_comparative_deep_dive_program.md).
Two candidate tracks are partner/frequency context (module 1) and separated
interaction/placement locality (module 4). These are proposals, not launched
experiments or approved confirmatory protocols. Agent launch and per-track scope
remain to be established; no new results are claimed.

Each track needs a distinct ID, bounded design, qualified positive control,
separate code/output ownership and explicit resource budget. Retain every pilot,
label exploration honestly, and use a separate prospective unseen-seed design
for any later confirmation. Do not reopen SM-H003's failed panel-level catalyst/
template confirmation or reuse SM-B003 seeds as unseen confirmation.

Ordinary raw data stays on Elements; POSIX controls remain in its mounted image.
Historical comparative/BFF documents are not launch instructions:
**BFF remains closed as NO-GO.**
