# Parent scientific/provenance review: SM-XP001 and SM-XL001

## Scope and disposition

Reviewed branch tips:
- XP: `229f8bc80b8f7d2f66dcf14fd5fe217a3cd769bc`, `/tmp/sm/xp`.
- XL: `a394accb6de446ef067d5a736ab7d33bdb376c79`, `/tmp/sm/xl`.
- Common base: `08cd1cec0b724c2042bfa6e4a8fcfa6914102d2b`.

**XP: accept the bounded descriptive closeout, not a causal or confirmatory finding.**
**XL: retain the interpretation block; no valid population locality conclusion.**
Neither branch is approved for merge or further population execution by this review.
The independent Herdr-based pre-merge quality gate could not run because Herdr
tools are unavailable. No substitute reviewer approval is claimed. No staging,
merge, push, agent-source edits or new native population executions occurred.

## What the parent independently checked

Read frozen plans, amendments, launch documents, controllers, relevant verifiers,
terminal observer, tests, handoffs and export manifests. Both branches contain
only new track-specific files; inherited modules were not edited.

Read-only audit in `/tmp/sm/parent-exploration-review-v1/`:
- XP: frozen manifest/launch binding, binary/config hashes, every native file
  against its retained inventory, twelve successful native receipts with empty
  stderr/completion markers, twenty successful replay receipts, identical analysis
  repeats, native technical repeats, and exact declared on/off filename/hash parity.
  All seven declared observation files are absent in both population off runs.
- XL: preparation seal, configs, all twelve native inventories and successful
  receipts, actual launched environments, eight successful diagnostic replay
  receipts and paired result equality. Confirmed that all four off runs retain
  conservation/material files and that the final decision denies interpretation.
- Rehashed both original and portable controls, raw exports, manifest seals and
  source archives: XP 7,755 control and 2,420 raw files; XL 449 control and 1,968
  raw files. All checks passed. This validates the existing evidence, not its
  sufficiency for every possible claim.
- Reran owned non-population tests: XP `tests/test_sm_xp001.py`: **11 passed**;
  XL `tests/test_stringmol_locality.py`: **8 passed**. Fresh external basetemps and
  caches were used. No full VM histories or full inherited regression were rerun
  by the parent, and the agents' skipped tests are not counted as passes.

Audit v1 incorrectly assumed the XL flag was explicitly `1` and stopped with
KeyError. Retained that diagnostic. Native `sm_conservation.h:100–102` establishes
that an omitted flag defaults to enabled; audit-v2 checks omission and the actual
files and passed. This was a parent audit assumption correction, not a native or
scientific-data repair. Both script versions and receipts remain preserved.

## Findings and boundaries

### 1. XL — blocker: missing frozen fully-disabled observer condition

`locality_pilot.py` originally inherited an environment helper that disabled
scheduling/source logging but omitted `STRINGMOL_CONSERVATION_LOG`. Native
conservation logging defaults to on. The original preparations and all four
actual off receipts confirm omission, while conservation002.csv,
conservation_buffers002.csv and material_events002.csv are present.

The six genuinely disabled streams have useful parity evidence; they do not
certify the other three. The corrected `locality_environment()` and its Python
unit test are prospective fixes, not evidence that the missing native condition
was executed. Eight correct geometry/VM/material/RNG reconstructions cannot waive
the frozen observer gate. Keep the full matrix interpretation blocked.

### 2. XP — interpretation limitation, not an undisclosed control failure

The B background is one byte and binding-excluded for the tested pair. It is not
a binding-, length-, composition- or material-matched inert partner. Changing its
fraction changes several mechanisms simultaneously. Two reused development seeds
and technical repeats do not establish robust causal partner-frequency effects.
The reports disclose these limits, and parent checks confirm the stated population
observer-off comparisons passed; do not transfer XL's observer failure to XP.

The original zero-pool HH reaction negative remains valid. Histogram16 support is
a separately documented changed experimental condition, not an operational fix
that turns the zero-pool outcome into a pass. Supported sequence output does not
establish zero-pool competence, serial offspring competence or heredity. The later
population minimal canonical reference passed, but is not a historical robust
renewal/maintenance gate. Exact HOST declined in every primary population run;
total population growth and births cannot replace that endpoint.

### 3. Verifier coverage differs materially

XP `xp001_population.analyze()` reconstructs supplied-inoculum material, scheduling
lifecycle, checkpoints, birth sequences and source transactions. It does **not**
independently reconstruct all opcode choices, full RNG or terminal VM heads.
Accept only the declared material/boundary/source descriptive scope. XL has a
separate canonical radii0/1 geometry/VM/RNG verifier and qualified tick-zero
G_NEXT correction; this is not evidence for other radii or inocula. Neither branch
should be presented as a general replacement for the frozen SM-B003 verifier.

### 4. Controller hardening is required before reuse/integration

- Both pilots rely heavily on Python `assert` for launch/provenance/integrity
  guards. Replace production safety guards with non-optional checks, or explicitly
  reject optimized execution and test it. No optimized invocation was introduced
  in this parent review; this is a reuse risk, not evidence of changed outcomes.
- XP `xp001_finish.finish()` reports `interpretation_integrity` from output parity
  separately from `canonical_reference_gate`. Provide an explicit interpretation
  authorization conjunction and a negative-control unit test so downstream readers
  cannot treat integrity alone as a passed biological control. Current canonical
  gate is true; this concern does not fabricate a failed current control.
- Do not reuse hard-coded original output paths or mutate sealed preparations to
  perform recovery. A new controller must reserve fresh controls/logs before work,
  bind code/config/binary/gate evidence, enforce the entire matrix and budget,
  retain every failed phase, and keep output/result receipts disjoint.
- Complete applicable static/build/regression validation and the independent
  quality gate before integration. XP's missing historical-CSV regression and
  XL's explicit native skips are still limitations, not full-suite successes.

## Decision on further work

No extra native runs are authorized by the parent-review request. Both original
12-execution budgets remain exhausted.

A justified **XL operational recovery proposal**, if approved separately, would:
1. Preserve all original native data, failed observer decision, diagnostic
   analyses and exports; use a new recovery ID and new output roots.
2. Freeze the same four cells, development seed, 5,000-tick horizon, inoculum,
   occupancy, endpoints and native semantics. The change is explicit log control,
   not biological tuning. This is technical recovery, not new independent seeds.
3. Qualify every logger's actual native enable/disable behavior with directed
   fixtures before population launch, including observer failures and file absence.
4. Budget a complete 4×3 observed/repeat/fully-off matrix: **12 additional native
   executions**, not four selective off reruns. Require original observed/repeat
   bytes to remain unchanged where the only difference is an equivalent explicit
   logging setting; any unexpected drift fails closed.
5. Require complete native repeats, full observer isolation, independent replay,
   positive-control gate, provenance checks and checksum exports before drawing
   the original bounded descriptive locality conclusions.

XP can close as descriptive exploration. A stronger partner-frequency question
requires its own prospectively matched-background design and competence/control
qualification, not selective continuation of these eight primary runs. No new
confirmatory claim or BFF/SM-H003/SM-B003 reopening is licensed.

## Evidence and remaining gate

Parent receipts: `audit-process.nuon` (retained assumption error),
`audit-v2-process.nuon`, `evidence-audit.json`, `xp-tests.nuon`, `xl-tests.nuon`
under `/tmp/sm/parent-exploration-review-v1/` (Elements POSIX image).
Portable parent review and supplemental branch-history bundles are intended under
Elements `verification/sm-parallel-parent-review-v1/`; its completion receipt,
not this path declaration, establishes successful export.

Independent merge-review verdict: **NOT RUN — Herdr tools unavailable**.
Restore Herdr tools to run the required reviewer/validation workflow. Do not merge
on the strength of this narrower parent evidence review alone.
