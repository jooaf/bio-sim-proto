# XP prospective controller hardening

Engineering only, based on XP `229f8bc80b8f7d2f66dcf14fd5fe217a3cd769bc`.
No new native population, reaction, replay executable, build or seed search was
run. All launch/build tests mock subprocesses. Original preparations, raw data,
exports and conclusions are unchanged. This is not independent review approval.

## Review mapping

- **Finding 2:** XP production assertions replaced by explicit `require()` checks.
  Build, link and repeat-analysis calls execute unconditionally and their return
  codes are checked. `AssertionError` remains the backward-compatible exception
  interface, not an `assert` statement. Native failure retains the execution and
  inventory receipts, consumes the launch reservation and stops further calls.
- **Finding 3:** future preparations add exclusive, versioned `bindings-v1.json`.
  It binds complete preparation bytes (all per-case settings and founders), the
  actual absolute `SUBMAT` paths, build/input/gate receipts, native source inputs,
  qualified reaction binary, plans and Python source snapshots. Verification runs
  before launch reservation and again before every native execution. Config and
  population binary hashes remain enforced. Historical preparations remain
  readable for analysis but cannot launch without a prospective binding receipt.
  Historical enforcement is **not** claimed to have existed.
- **Finding 4:** preflight independently checks mount/headroom and cumulative
  4 GiB POSIX / 25 GiB raw pilot usage. Accounting uses the larger of logical and
  allocated size per node, counts hard links conservatively and does not traverse
  symlinks. Symlink budget roots are rejected. Checks recur before new executions,
  reaction assays, link work and repeated analyses.
- **Finding 6:** typed founder/case/snapshot/reaction/process/export records and
  narrow nullable process return codes replace unparameterized dictionaries.
  JSON preparation boundaries validate types, counts and identifiers. Strict
  mypy passes on all eight owned Python files, with no blanket ignores/Any model.
- **Authorization interface:** `interpretation_authorized` is explicitly integrity
  AND canonical biological positive control. Integrity includes successful native
  and repeated analysis prerequisites, replay integrity and output isolation.
  No-reference control sets fail closed. Negative descriptive tables are retained.
  Existing historical positive/negative claims are not rewritten.
- **Reservations:** receipt files are exclusively reserved before spawn or log
  creation, spawn/timeout/log-conflict failures retain structured receipts, and
  failed attempts cannot reuse labels or launch reservations.

## Validation

Retained under `/tmp/sm/xpr-e/validation-01` through `validation-04`.
Final scoped pytest: **60 passed**, both normal Python and `python -O`.
Optimized pytest emits its expected warning about assertions outside rewritten
modules; owned production code no longer contains assertion statements. Tests
exercise actual production functions under optimization, including exact build,
link and repeat call counts, mount/headroom/hash/parity/process failures,
malformed and legacy preparations, input drift between executions, quota failures
with ample free space, receipt/output exclusivity and authorization negatives.
The original 11 reaction/input tests pass using read-only frozen reaction data.
Strict mypy: **success, eight files**. Diff whitespace check: passed.

Earlier failed validations are retained, not overwritten: validation-01 found
seven typing issues; validation-02 found twelve test typing issues and one test
fixture mistake (raw and POSIX headroom paths were accidentally identical).
Validation-03 passed 48 tests before the last twelve adverse cases were added.
These were engineering/test iterations, not scientific retries.

## Limits

No native source changed and no directed native fixture was necessary for these
Python-only repairs. No fresh C++ build or broad historical/native regression was
performed; unavailable historical-CSV coverage remains unresolved, not passed or
skipped-as-passed. The inherited replay modules remain unchanged and this work
adds no opcode/RNG/head reconstruction claim. The immutable old pilot remains
12/12 exhausted and its bounded descriptive closeout remains accepted as before.

Quota admission checks stop subsequent work at the cumulative cap; they are not
an OS-enforced in-flight write limit and cannot predict one process's output.
Dependency verification detects drift before calls, not hostile concurrent
mutation after verification. Bindings are local evidence, not signed attestations.
Historical hard-coded CLI defaults remain; do not invoke them against originals.
Future scientific execution requires separate authorization, fresh roots and a
fresh budget; no such authorization is supplied by this engineering change.
