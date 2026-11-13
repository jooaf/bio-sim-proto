# SM-B003 final launch controls

The separate `experiments.admission_campaign` entry point leaves all 67 qualified
native/replay implementation records byte-identical to a663885. It provides
prepare, eligible, once-only run, and serial independent/repeat analysis phases.
Preparing inputs cannot launch a native process. A raw directory or launch marker
prevents a second native attempt; failed inputs remain in the 120-input denominator.

Scientific settings, seeds, ancestry definitions, continuity thresholds and ordered
decisions are unchanged; see `sm_b003_admission_replacement_preregistration.md`.
No campaign input was executed during controller tests: their seed set is fake.

## Validation

- `verification/sm-b003-campaign-controls-v1/`: 36 tests passed; two typing-only
  annotations were then corrected, with clean typing in controls-v2.
- `verification/sm-b003-full-regression-v2/`: **3,953 passed**, two non-failing
  warnings, 1,164.80 seconds, including instrumented native admission cases.
- `experiments/sm_b003_qualification.json` binds the existing build, development
  plan/results/executions and the complete new regression receipt by SHA256.
- Guards cover changed/resealed configurations, policy/timeout/denominator drift,
  source drift, stale eligibility, repeat-launch attempts, failed audits, exact
  negative endpoint mapping, and process-group termination on analysis timeout.
- Both analysis passes use the qualified replay CLI. Process receipts, outputs,
  resource records and partial logs have separate, exclusive paths. Timeout kills
  the owned process group, including the time wrapper and its Python child.

## Freshness audit development and retained failures

The audit covers historical runs/sweeps, Elements results, the external POSIX image
and project Git/runtime metadata targets. It checks archives without extraction,
seed-bearing JSON/text/CSV fields and key/value parameter tables. It does not
confuse data counters, source references or ordinary complete MT state words with
seed declarations. No directory subtree is exempt.

Diagnostic-v1 and v2 did not produce completion receipts. V2 retained streamed
progress through at least 70,001 payloads. One-run profiling showed 45.48 seconds,
44.81 in disk reads. Schema-aware inspection reduced the same 110-file audit to
0.023 seconds: non-seed CSV schemas now have explicit header-only records, not
false full-content checksums. Full campaign artifact checksums remain independent.

Diagnostic-v3 completed with unresolved Git/runtime aliases. V4 expanded coverage
but encountered a large audit receipt and a retained synthetic archive-alias test.
The JSON review bound is now 512 MiB; larger matching metadata remains fail-closed.
The single unit-v5 alias artifact is classified only with exact artifact,
generator-source and successful-test-receipt hashes. It contains no simulation
execution; all witnesses remain retained. Future alias fault tests operate in
memory rather than adding unknown external references to the historical corpus.
This classification is not an arbitrary filename or subtree exemption.

`verification/sm-b003-seed-audit-diagnostic-v5/audit.json` completed with
**372,813 metadata records and zero prior-use matches**. This diagnostic is not a
substitute for launch eligibility: after immutable preparation, the controller
must run a new audit excluding only the exact verified preparation files.
Eligibility binds that audit, preparation and published source, and expires after
180 seconds. The audit's own completion timestamp must also remain fresh.

## Launch boundary

Commit and observe actual origin/main before preparing inputs. Execute from a
separate clean checkout, leaving unrelated migration changes untouched. Preserve
portable source/provenance receipts on Elements. Only a successful new preparation
and fresh eligibility gate may transition task21 into native execution.
