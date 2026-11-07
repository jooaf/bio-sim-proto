# SM-B003 sanitizer recovery and native cleanup correction

## Tooling repair — no system installation

GCC is `gcc-16.2.1-2.fc44.x86_64`, but its runtime RPMs were absent. Its linker
scripts named nonexistent `/usr/lib64/libasan.so.8.0.0` and the analogous UBSan
library. The exact matching x86_64 Fedora updates-archive packages were downloaded
to Elements and verified with `rpmkeys --checksig --verbose`: both signatures and
header/payload digests passed against the already installed Fedora key fingerprint
`36f612dcf27f7d1a48a835e4dbfcf71c6d9f90a6`.

Packages:

| RPM | SHA-256 |
|---|---|
| libasan-16.2.1-2.fc44.x86_64.rpm | 7a537e0276154d7c92976790657337ef5d543b8401ce6dd278498403cfc36328 |
| libubsan-16.2.1-2.fc44.x86_64.rpm | 2677b173bcb7e5f26204f8880a4d1ea16567803a778b66955468eb37c0913ab6 |

They were extracted, not installed, under
`/tmp/sm/toolchains/gcc-16.2.1-2-sanitizers-v1/usr/lib64` on the external POSIX image.
Local `libasan.so`/`libubsan.so` links plus explicit link-search/RPATH arguments
avoid modifying `/usr`, the archived simulator, or global loader configuration.
RPMs, signatures and library/source hashes are retained in
`Elements/bio-sim-results/verification/sm-b003-sanitizer-runtime-v1/`.

The test harness now supports explicit instrumentation with
`SM_ADMISSION_SANITIZERS=1` and an optional `SM_ADMISSION_SANITIZER_LIBDIR` override.
It rejects invalid mode values, verifies actual runtime linkage, uses nonrecovering
ASan/UBSan, enables leak detection, and replaces inherited sanitizer suppressions.
Dedicated controls must detect **heap-use-after-free** and **signed integer overflow**;
a successful nominal fixture alone is not proof of active instrumentation.

Example after runtime verification/extraction, with a fresh external output path:

```nu
with-env {
    SM_ADMISSION_SANITIZERS: '1'
    SM_ADMISSION_SANITIZER_LIBDIR: '/tmp/sm/toolchains/gcc-16.2.1-2-sanitizers-v1/usr/lib64'
    SM_ADMISSION_NATIVE_SOURCE: '/tmp/sm/a7/src'
} {
    .venv/bin/python -m pytest tests/test_stringmol_admission_design.py tests/test_stringmol_admission_journal.py tests/test_stringmol_native_admission_journal.py --basetemp /tmp/sm/NEW-UNUSED-SANITIZER-OUTPUT -q
}
```

Do not reuse a pytest basetemp containing evidence: pytest clears it. These are
Linux/GCC qualification tools, not portable macOS executables.

## Native behavior finding — change the oracle, not the simulator

An isolated checkout at `/tmp/sm/a7` was cloned without hardlinks from the archived
source, checked out at `15dad84da126a4f887ba945c23a13e89e827f067`, and given the
unchanged patches 0001–0006. No adapter changes have yet been applied there.

Inspection and a sanitizer-instrumented probe of the **real `agent.cpp` function**
confirmed that `AgentCheckZeroLengthString` returns immediately for an empty active
participant, otherwise checks the passive participant. Both empty means action 1,
not removal of both. The probe covered all eight empty/nonempty × hidden-tail
combinations, returned zero, and produced no sanitizer diagnostics. It checks the
native branch selector, not an entire cleavage, grid mutation or replacement.

The v1 journal framer incorrectly assumed source survival iff cut offset > 0 and
allowed up to two cleanup deaths. A whole-source passive transfer with an already
empty active partner instead removes that active partner and retains the empty
passive source, including hidden material. V2 corrects physical survival/cleanup
checks and uses independent pre-dispatch buffers to check the active-first rule.
Both native/Python wire tags advance to `SM-B003-ADMISSION-2`; v1 artifacts remain
unchanged at their recorded revisions. The partial-remnant endpoint, candidate
selection, denominators and continuity criteria do not change; empty survivors
receive no partial/continuity credit. Existing B002 reference code already uses
active-first cleanup; the mistake was confined to the new admission journal checker.

## Validation and remaining work

- 118 focused tests passed with ASan/UBSan enabled, including both deliberate-fault
  controls, ten new cleanup edge/adversarial checks, and the real native branch
  probe integrated into the test harness; strict typing passed.
- Native branch probe: eight cases, all assertions passed under ASan/UBSan.
- Evidence: `verification/sm-b003-asan-v1/`, `verification/sm-b003-asan-v2/`,
  `verification/sm-b003-asan-v3/`, and `verification/sm-b003-native-cleanup-v1/`
  on Elements. The v3 native test records its compiler command and hashes all
  native local headers plus the pinned function, struct and fixture sources.
- Earlier failed linker evidence remains retained; it is superseded, not erased.

Sanitizer availability is repaired. Native atomic replacement, rollback/publication
fault tests, full material/ownership/lineage replay and population qualification
remain outstanding. No population assay or held-out seed was used for this repair.
