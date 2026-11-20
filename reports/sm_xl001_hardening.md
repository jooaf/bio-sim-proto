# SM-XL001 engineering hardening (not scientific recovery)

Source baseline: `a394accb6de446ef067d5a736ab7d33bdb376c79`.
Branch/worktree: `harden/sm-xl001`, `/tmp/sm/xlr`.
Evidence: `/tmp/sm/xlr-e`; portable evidence:
`Elements/bio-sim-results/verification/sm-exploration-hardening-v1/xl`.

## Review findings addressed

1. Corrected logger settings now have directed native qualification. The fixture
   calls actual conservation, scheduling, retirement, lineage and terminal observer
   hooks against two fixed agents. Seven valid configurations check all nine
   observer files for actual presence/absence, nonempty enabled files, unchanged
   agent/head/species/grid/material-ledger state and complete MT state, plus exact
   ordinary state/RNG/stdout/stderr byte parity between configurations. Five invalid
   conservation/scheduling/retirement configurations fail with retained stderr and
   receipts. Source-retention qualification here opens its real journal; it does
   not establish full source-transaction or population trajectory isolation.
   There is **no population loop**. These mechanical qualifications do not repair
   the historical four off runs or authorize treatment interpretation.
2. All production `assert` guards in owned locality modules are unconditional
   `require`/exception checks. Required operations are not assertion expressions.
   Subprocess tests explicitly exercise mount, seal and interpretation parity
   failures in ordinary and optimized Python, and reject unwanted native calls.
5. Native, replay and diagnostic wrappers use one exclusive receipt reservation
   before launch. Final receipts retain exact argv, complete supplied environment,
   cwd, timeout, wall start/end/duration, exit or exception type/message/repr and
   available file hashes. stdout/stderr remain separate files. Spawn errors and
   timeouts are retained, never retried. Native failure stops the attempt before
   another native job or completion marker. Replay diagnostics retain all attempted
   inputs without granting interpretation. Adversarial tests exercise all three
   wrappers for missing executable, permission failure and timeout, plus exit codes,
   exclusive reservations and incomplete pending dispatch.
6. Typed preparation/job/file/process/diagnostic/summary/replay records replace
   heterogeneous inferred dictionaries. Frozen pending dispatch is a dataclass;
   optional pending/flow/target states are explicitly narrowed or rejected.
   `Any` is limited to the existing inherited material-initialization interface;
   inherited modules were not changed. Strict mypy passes all eleven owned Python
   files, without blanket ignores or strict-mode changes. Malformed/redirected
   preparation identities, paths, commands and logger settings fail closed.

## Native patch hygiene and binding

The stored patch now uses minimal zero-context hunks. Apply **only to the pinned
baseline** with `git apply --unidiff-zero --check PATCH` and then
`git apply --unidiff-zero PATCH`. Do not strip unified-diff context markers.
Baseline `src/sm_spatial.cpp` SHA256:
`e2c7ffd76d76fc32ff3453c42fb8c8bda26328477d74acecd57009cd279c53e3`.
The final patched source inventory exactly matches the source inventory sealed in
historical `preparation.json` (including the unchanged terminal observer header).
`native-source-binding.json` records the comparison. A fresh copied baseline was
built with forced `make -B -j2`; original/shared native trees were never built or
modified. The logger fixture links those fresh objects, excluding the native CLI
and spatial object (the latter implementation is included to reach private lineage
hooks). It never calls native `Run()`.

## Validation and limits

Latest scope: three owned pytest modules, **33 passed**, no skips. Strict mypy:
**11 source files clean**. Final optimized validation and checksums are recorded in
`HANDOFF.md` and execution receipts in the external evidence root. Diff checks run
against both the assigned source tip and common base. Earlier failed validation
attempts and successful superseded attempts remain in fresh evidence paths.

No full historical replay, broad inherited suite, sanitizer campaign or population
experiment was run. Historical skipped native tests are not passes. The existing
canonical radii0/1 and tick-zero `G_NEXT` semantics are preserved, not generalized
to other inocula/radii. Hard-coded historical CLI roots remain non-reusable for a
new protocol; no old CLI stage was executed against them. A new whole-matrix
recovery still requires separate protocol/budget authorization and new paths.

**Historical decision remains BLOCKED. ZERO new native populations.** No BFF,
B002/B003, or gated H003 reopening. Parent review remains pending; this report is
not an independent approval, merge authorization or future recovery claim.
