# SM-B003: frozen admission-replacement assay protocol

This protocol becomes executable only after committed publication, verified
qualification, a fresh execution-aware unseen-seed audit, and an immutable
preparation/eligibility receipt. Preparing inputs is not launching them.
The existing user authorization is conditional on all these gates succeeding.

## Scientific identity

The design and ordered classifier in `experiments/stringmol/admission_design.py`
are unchanged. Native integration and complete independent replay were qualified
and published at **a663885635ee79d03d1db8655e5cef2a64a02114**. The development report
`sm_b003_development_qualification.md` retains every development arm, including
both negative replacement-only continuity outcomes. No threshold is adjusted
in response to those outcomes. B002 is closed; BFF remains NO-GO.

Exactly 120 inputs: seeds **202629000 through 202629019**, crossed with
IMMEDIATE/DELAY500 and NATIVE_VACANCY/STRATIFIED_REJECT/STRATIFIED_REPLACE.
Those seeds are reserved, not presumed unseen; the audit must certify them
before launch. Every arm uses the unchanged canonical 140-host inoculum,
40x40 grid, global interaction and placement, zero mutation, zero histogram pool,
recycle routing, RETAIN, 5,000 ticks, and reporting every 100 ticks. Configurations
must equal the canonical renderer byte-for-byte, with the qualified matrix file.

Stratified admission draws vacant versus eligible-occupied categories with
probability one half, then uniformly within the chosen category; no fallback.
Eligible victims are visibly nonempty unbound nonparticipants, including delayed
children. The current linked-list owner determines removal, not a guessed grid
status. NATIVE remains the inherited vacancy-only control. A committed eviction
returns the victim's full physical buffer only to the dedicated eviction ledger.
Post-proposal rollback does not rewind RNG, reuse IDs or undo allocation-prefix
species history. Publication is irreversible; failures invalidate execution.
Native source cleanup remains active-first and removes at most one participant.

## Fixed endpoints and decision ordering

Maintain all-admission and replacement-only ancestry separately. Replacement-only
ancestry cannot reconnect through a vacancy/relocation descendant. Empty survivors
receive no partial/continuity credit. Retention is evaluated at the first source
event across all channels, using the inherited physical-buffer retention rule.

Each continuity tuple must reach all six thresholds:

1. at least 100 qualifying transfers;
2. at least 10 renewing descendants;
3. at least 50 serial transfers;
4. maximum nonrelocation depth at least 2;
5. at least 5 renewing descendants born at or after tick 2500;
6. at least 5 such late renewals with birth length at least 32 and retention at
   least 0.90.

Report all per-run tuples, exposures, admissions, evictions and integrity failures.
Do not drop a failed input from the intended denominator of 120, the arm
denominator of 20, or paired seed accounting. Use `admission_design.decide` in
its existing order:

- Any missing/duplicate input, execution/replay/repeat failure or invalid outcome:
  **Unevaluable integrity**.
- Either NATIVE schedule has fewer than 16/20 all-admission continuity passes:
  **Valid native-control failure**.
- Either REPLACE schedule has fewer than 16/20 runs with at least 100 verified
  occupied partial commits: **Inadequate replacement exposure**.
- Otherwise classify replacement-only continuity at 16/20 separately for the two
  schedules: both, immediate only, delayed only, or neither.

REJECT is fully reported, not excluded or substituted into a favorable decision.
These are transmission/continuity claims, not evidence of novel function, strong
necessity, or a formal interaction test. Valid negative results stop the campaign;
no tuning, selective retry or search for a better seed is authorized.

## Operational constraints and evidence

Use the qualified ordinary baseline/candidate build and renamed-main RNG wrapper;
verify every source, matrix, object and executable digest before use. Final
orchestration must be separately tested and committed. Verify the actual remote
branch, not only a cached tracking ref. Preserve a portable Git source bundle.

At most **six native processes**, with **600 seconds per native execution**.
Execution plus complete inventory must also remain below 600 seconds. Analyze
serially with **1,800 seconds per process**, and analyze each successful input a
second time in a separate process. Require exact deterministic result agreement.
Analysis must validate native success, input identity and full output inventory,
then independently reconstruct VM/RNG, queues, grid, material/eviction accounting,
source/species/lineage joins, checkpoints, terminal heads and complete final RNG.
Framing or conservation-only checks are not a substitute.

Raw data stays directly on Elements; immutable controls stay in its mounted POSIX
image. Preflight free-space floors: 100 GiB raw and 10 GiB POSIX. Emergency floors:
2 GiB raw and 1 GiB POSIX. No internal-storage fallback. All output creation is
exclusive; retain failures, stderr, timeouts, incomplete prefixes and denominators.
Do not automatically rerun a failed scientific input. Any later operational
whole-matrix recovery requires a prospective documented engineering amendment,
unchanged biological inputs/criteria, and renewed qualification before execution.

The freshness audit covers project historical runs/sweeps, the Elements results
root and its POSIX image contents, including archived execution/input metadata.
Recognize seed-bearing configuration fields, JSON/structured records, command
arguments/logs, CSV seed columns and key/value parameter tables. CSVs without
seed-bearing fields receive explicit header/schema records, not invented full-file
checksums. Full campaign artifact checksums remain a separate integrity gate.
Numeric RNG words/counters and source-code or preregistration references are not
execution evidence. Follow coverage through project Git/runtime directory aliases;
record binary runtime links without treating executables as seed-input metadata.
Only exact hash-verified current preparation files may be excluded from inspection,
never an entire directory subtree. A known synthetic negative-test artifact may
be classified as nonexecution only with exact artifact, generator-source and
successful-test-receipt hashes, all retained in the audit. This applies to the
single retained archive-alias fixture from audit-unit-v5, not to a path pattern.
Unexpected or ambiguous evidence blocks launch; missing scope is not a pass.
Recheck the audit immediately before claiming launch eligibility.

Publish all attempts, the fixed decision, both analyses, complete checksums and
Mac-readable data/source exports. Included Linux binaries require rebuilding and
requalification before execution on macOS. No publication may label a development
fixture or an incomplete campaign as a completed confirmatory assay.
