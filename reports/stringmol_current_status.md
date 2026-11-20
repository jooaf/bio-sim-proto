# Current Stringmol program status

Updated 2026-11-20 after the read-only XL role/opportunity measurement. SM-B002 and SM-B003 are closed.
XP and the complete XL technical recovery are closed as bounded descriptive
explorations. Original failures remain preserved. No experiment is currently running.

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

- **SM-XP001 partner/frequency context:** 12/12 populations and 48 directed
  assays retained. Descriptive archive only: the one-byte background is not
  binding-matched inert, and canonical HOST declined in all eight primary runs.
  See [`sm_xp001_results.md`](sm_xp001_results.md).
- **SM-XL001 separated interaction/placement locality:** the original attempt
  remains **BLOCKED** because all four nominal off conditions omitted the default-on
  conservation logger flag. A separately authorized complete12-run recovery now
  passes all full-off/repeat checks and16independent replays, with the original
  eight observed/repeat outputs unchanged byte-for-byte. GG positive control passed.
  Final populations GG/LG/GL/LL:347/230/157/187; births:664/539/339/413. Local-placement
  cells had1027/1556failed placements; global-placement cells had zero. This is
  one development realization per cell, not confirmatory evidence. See
  [`sm_xl001_recovery_closeout.md`](sm_xl001_recovery_closeout.md) and the unchanged
  [`original blocked closeout`](sm_xl001_closeout.md).
- Independent review and controller hardening are complete. XP `d0e3034` and
  XL `fe3bf8c` are integrated through `61de654`, with the documented limited scope
  in [`stringmol_exploration_code_review_closeout.md`](stringmol_exploration_code_review_closeout.md).
  Combined parent validation: 102 tests passed normally and 102 under `-O`, one
  directed-native-fixture skip each, strict typing clean across 20 owned files.
  This is not full historical/native regression qualification.
- Recovery source `2532726` was qualified, independently reviewed, frozen and
  published before execution. All12native runs and16replays succeeded;2297portable
  files were checksum-verified and independently rehashed by the parent. Original
  seed, biological settings, horizon and endpoints were unchanged. The original
  blocked attempt is immutable and unpooled. The recovery budget is now exhausted;
  no additional population attempts are authorized.

- **Existing-data renewal synthesis:** independent parent review accepted the
  post hoc reduction (`f9ba2d6`), with zero new simulations or full replays. Local
  placement accompanies fewer distinct renewers (GL12 vs GG25; LL39 vs LG47) and
  late-born renewers (2vs6;12vs21). Per-admitted-child renewal fractions change in
  opposite directions across interaction contexts, while exact HOST declines in
  every cell. This motivated the role/opportunity measurement below,
  rather than another population campaign. See
  [`sm_xl001_renewal_analysis.md`](sm_xl001_renewal_analysis.md).

- **Role/opportunity measurement complete:** independent scheduling-log reduction
  and parent audit show every qualifying source action was also executed actively
  by that molecule, with its own instruction-head genome. First renewer counts
  remain25/47/12/39. Passive-source attribution does not explain those successes.
  Death/no-event and end-censoring are separately recorded; observed opportunities
  and follow-up differ. This resolves role attribution in these histories, not
  intrinsic or standardized competence. Further claims require a separately
  authorized design, not more reinterpretation of the same observations. No new
  simulations or assays ran. See [`sm_xl001_role_analysis.md`](sm_xl001_role_analysis.md).

These are bounded development explorations, not confirmatory unseen-seed results.
Retain negatives and every attempt. Do not reopen SM-H003's failed panel-level
catalyst/template confirmation or reuse SM-B003 seeds as unseen confirmation.

Ordinary raw data stays on Elements; POSIX controls remain in its mounted image.
Historical comparative/BFF documents are not launch instructions:
**BFF remains closed as NO-GO.**
