# SM-B003 — admission-replacement closeout

Closed 2026-11-16 UTC. **Robust replacement-only continuity not established.**
Integrity passed; this is a valid non-pass, not a continuing verifier failure.

## Frozen design and results

Twenty paired seeds (202629000–202629019), six arms: IMMEDIATE/DELAY500 crossed
with NATIVE_VACANCY/STRATIFIED_REJECT/STRATIFIED_REPLACE. Source RETAIN, 140 hosts,
40×40 grid, global interaction/placement, zero mutation/free pool, recycling and
5,000 ticks stayed fixed. Each arm's denominator is 20.

| Schedule | Admission | All-admission continuity | Replacement-only continuity | Runs with ≥100 partial replacement commits |
|---|---|---:|---:|---:|
| IMMEDIATE | NATIVE_VACANCY | 16/20 | 0/20 | 0/20 |
| IMMEDIATE | STRATIFIED_REJECT | 13/20 | 0/20 | 0/20 |
| IMMEDIATE | STRATIFIED_REPLACE | 12/20 | 3/20 | 20/20 |
| DELAY500 | NATIVE_VACANCY | 20/20 | 0/20 | 0/20 |
| DELAY500 | STRATIFIED_REJECT | 16/20 | 0/20 | 0/20 |
| DELAY500 | STRATIFIED_REPLACE | 18/20 | 4/20 | 20/20 |

Continuity is the unchanged conjunction of at least (100 transfers, 10 renewing,
50 serial, depth2, 5 late, 5 retained-late); robustness requires 16/20 runs.
Replacement ancestry excludes vacancy/relocation paths. Zeros in nonreplacement
arms reflect that exclusion, not an additional biological failure.

Both native-control gates passed; replacement exposure passed in all 40 REPLACE
runs. Neither replacement-only schedule passed robustness. All-admission renewal
cannot substitute for the failed replacement-only endpoint. Differences between
arms are descriptive here, not a new interaction or significance claim.

## Preserved operational history

- Frozen native source/controller: `525a745524d0a655695248017799c2e4febf10f8`.
  All 120 native executions succeeded.
- Original two-pass replay: 98 inputs passed; 22 failed terminal VM/grid equality
  in both passes. Original decision **Unevaluable integrity** remains preserved.
- Diagnosis: replay omitted inherited `AgentRewindDanglingPtrs` after nonempty
  cleavage. Native mechanics clamp all heads to visible participant ends before
  cleanup/instruction advancement. No native code or terminal equality was weakened.
- Repair/recovery source: `15b4bb18d50bd09568a2cdd16f8644734ff2b278`.
  Qualification: 66 focused sanitizer tests; 4,007 full runtime tests; 12/12
  retained development replays with exact original agreement; 35 controller tests.
- Prospective analysis-only recovery rechecked **all 120 inputs twice**:
  **240/240 successful processes**, no timeouts, all 120 integrity-valid. The 98
  previously valid outputs matched their originals byte-for-byte. No native
  population was rerun and no scientific thresholds or horizons changed.
- Final decision: 2026-11-15T23:47:29.476106+00:00. Portable export completed
  2026-11-16T00:16:04.177161+00:00; 69,516 regular files checksum-verified across
  nine evidence roots. Fixture links/special nodes are explicitly recorded as
  metadata, not followed or represented as regular-file contents.

## Evidence

- Raw: `/run/media/jojo/Elements/bio-sim-results/sm-b003-v1/`.
- Original controls: `/tmp/sm/c3/`; recovery controls: `/tmp/sm/c3a2/`.
  Both reside in the Elements POSIX image.
- Portable export and source bundle:
  `/run/media/jojo/Elements/bio-sim-results/verification/sm-b003-analysis-recovery-c3a2/`.
  Portable decision: `portable/c3a2/files/decision.json`.
- Decision SHA-256:
  `1242fead76f03c57747d65df36211eef89cceb026247737249496537223620c7`
  (61,358 bytes).
- Design: `sm_b003_admission_replacement_preregistration.md`.
- Recovery: `sm_b003_analysis_recovery_plan.md`; pinned qualification:
  `../experiments/sm_b003_analysis_recovery_qualification.json`.

## Inference and next-work boundary

This does not show that Stringmol renewal is absent, replacement-only continuity
is impossible, or all birth-boundary explanations are false. It does not establish
robust replacement-only continuity under these frozen conditions. SM-B003 is
closed: no selective retries, threshold changes or nearby parameter search may be
reported as a successful continuation of this experiment.

New independent exploratory questions can come from the existing comparative
program (partner/frequency context or interaction/placement locality, for example).
Give each a distinct ID and bounded plan, retain every outcome, and keep discovery
separate from any later unseen-seed confirmation. SM-H003's gated catalyst/template
confirmation remains unsupported; BFF remains NO-GO. Neither branch is reopened
by this result or by the request for additional exploratory work.
