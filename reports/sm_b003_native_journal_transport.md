# SM-B003 native journal transport checkpoint

This records the initial native **transport**, not atomic victim replacement.
Subsequent sanitizer recovery and the prospective v2 cleanup correction are in
`sm_b003_sanitizer_recovery.md`; the former tooling blocker is now resolved. The
simulator, archived patch-0006 trees and R2 data have not been modified.

Files:
- `experiments/stringmol/native/admission_journal.h`: C++11 writer, initially for
  `SM-B003-ADMISSION-1` (now prospectively revised to v2), typed field/event/policy names, exclusive creation,
  bounded rows, exact MT-uniform bit encoding and ordered transaction framing.
- `tests/stringmol_admission_journal.cpp`: synthetic transport fixture, not a
  native population simulation.
- `tests/test_stringmol_native_admission_journal.py`: independently reads native
  output with the Python contract and exercises injected I/O failures.

## Checks completed

105 combined design/journal/transport tests passed; strict typing passed for the
three journal modules/tests. The complete committed-source regression at `3d03256`
also passed: **1,769 tests**, two existing warnings, 843.61 seconds. Its evidence is
`Elements/bio-sim-results/verification/sm-b003-journal-3d03256-full2/`, including
source checksums and 28 checksum-verified ordinary-file CSV exports. The earlier
180-second regression attempt was incomplete and is retained separately, not
counted as a pass. Native compilation uses C++11, `-Wall -Wextra -Werror`.
A synthetic complete replacement-shaped record, including hidden victim bytes,
round-trips through Python framing. This does **not** prove actual replacement.

Tests cover exclusive creation, duplicate/missing markers, unresolved transactions,
oversized records, IEEE uniform encoding, header/flush/short-write failures and
close failure. A writer poisoned by an attempted write cannot subsequently retry,
even if the original I/O failure disappears. A complete END prefix followed by a
fatal process status remains invalid: file framing alone is not run integrity.

UBSan trap-mode compilation and the synthetic complete-proposal fixture passed.
ASan linking did **not** pass: the installed compiler references missing
`/usr/lib64/libasan.so.8.0.0`; static sanitizer runtimes and clang are also absent.
This initial failure remains retained, not silently counted as a gate; the separate
recovery receipt documents its subsequent repair and actual sanitizer passes.
The GNU linker `--wrap` fault fixture is Linux-specific and needs an equivalent
fault-injection mechanism when rebuilt on macOS; CSV evidence is ordinary ASCII.

Development evidence is on Elements under
`verification/sm-b003-journal-20261107-*`; externally backed binaries and fixture
outputs are under `/tmp/sm/sm-b003-journal-20261107-*`. Earlier development attempts
remain retained. None used a held-out assay seed or ran a population assay.

## Still required

The adapter must enforce fatal failure after **any stream's** irreversible admission
publication, not decide rollback from this writer's `failed()` flag alone. That flag
only describes this transport's I/O. Before publication it must restore the entire
post-proposal baseline, and after completion it must verify real grid/list ownership.

Next: isolated patch-0007 simulator integration, distinct eviction accounting,
actual native directed/rollback/sanitizer/RNG tests, independent full joined replay,
development-only exposure qualification, and final prospective launch eligibility.
No native replacement or population-integrity qualification is claimed here.
