# SM-C001 exact Stringmol conservation implementation

**Prepared:** 2026-09-29  
**Preregistration commit:** `9cc31a3`  
**Status:** mechanics gates passed; 20 unseen scientific inputs sealed but not executed

## Implementation

- Added `experiments/stringmol/patches/0003-add-exact-spatial-symbol-conservation.patch` after patches 0001 and 0002.
- Conserved inventory is every non-NUL ALXII byte in each complete `maxl0` agent buffer plus the free per-symbol pool.
- Copy is planned as one ordered transaction. It preserves native branch/RNG behavior on valid paths, commits all byte/pool changes atomically, and rolls all bytes back under scarcity while retaining frozen completion effects.
- Stable-state cleavage accounting distinguishes failed-placement and successful-cleavage discard returns. Spatial decay returns every full-buffer byte exactly once.
- Enabled safety checks fail closed on invalid substitution rank, reserved-terminator corruption, unsafe instruction/read/write positions, and invalid cleavage pointers. Scientific runs require zero such errors. Disabled execution remains on the unmodified native path.
- Added append-only `conservation001.csv` and `conservation_buffers001.csv` observations, independent reconstruction, pool/counter reconciliation, and lineage cross-checks.

Primary files:

- `experiments/stringmol/conservation_workflow.py`
- `experiments/stringmol/analyze_conservation.py`
- `tests/stringmol_conservation_directed.cpp`
- `tests/test_stringmol_conservation.py`

## Frozen mechanics evidence

Fresh artifacts are under `runs/sm_c001_work/`:

- build manifest: `final-builds/build.json`;
- lineage isolation: `final-lineage-isolation/isolation.json`;
- conservation gates: `final-gates/gates.json`;
- sealed preparation: `prepared/preparation.json`.

The final gate passed all frozen checks:

- both fresh upstream builds: 79 assertions in 15 cases each;
- focused Python validation: 150 tests passed;
- scoped mypy: seven files clean;
- directed C++ mechanics fixture passed;
- disabled absent-variable, explicit-zero, deterministic-repeat, and lineage-isolation parity passed;
- enabled uniform no-scarcity, deterministic-repeat, and lineage-isolation parity passed;
- zero blocked and boundary-error transactions in the no-scarcity parity run;
- exact reconstruction and zero residual at every checkpoint and END;
- all 18 release objects per build are hashed, and the directed receipt binds the exact 17 linked objects.

A separate repository-wide `just test` passed 768 main tests and 105 organism-sim tests.

## Review repairs before freezing

Independent source review identified and closed four pre-execution gaps:

1. native `OpcodeAdjacent` could index before the ALXII key for a zero endpoint draw;
2. deletion completion and cleavage pointer subtraction had reachable pointer hazards;
3. the analyzer incorrectly assumed every accepted change withdrew matter and net copy growth could not be negative, rejecting valid native NUL insertion contraction; and
4. directed-test object files were not initially bound to the verified build.

Endpoint, pointer, contraction, tampering, and linkage fixtures now cover these cases. A final read-only review found no remaining pre-execution blockers.

## Sealed execution boundary

`prepared/preparation.json` pins the committed protocol, inherited SM-L001 definitions, source and patch bytes, runner/analyzer/tests, fresh binaries and release objects, gate artifacts, environments, commands, configs, initial full buffers, pools, and per-symbol totals.

It contains exactly 20 read-only inputs for paired seeds `202621000`–`202621009` in m16 and m0 arms. All 20 run directories were absent when sealed. No scientific campaign or outcome analysis had been executed at preparation time.
