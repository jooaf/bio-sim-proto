# SM-B002-R1 — prospective artifact-failure recovery

## Scope and authority

The user directed continued autonomous Stringmol work, not BFF, and explicitly
requested proceeding with SM-B002 after its infrastructure failures. This addendum
is frozen before any R1 experimental input executes. It implements the original
protocol's permission to repair an artifact/integrity failure and rerun the
**unchanged complete matrix**. It does not authorize selective retries, new seeds,
changed horizons, changed thresholds, or rerunning valid scientific non-passes.

The original launch at commit `4dba5fecf3c4a1975223782a16aab9b30fe2e6f5`
failed with ENOSPC during inventory sealing. Its retained preparation, launch,
and cleanup records remain evidence. Partial raw outputs were removed by the
historical cleanup, not this recovery. Consequently the seeds are previously
attempted, not unseen. R1 must retain all 80 outcomes, including failures.

## Infrastructure-only change to prelaunch verification

The old full-gate chain reconstructs historical H001/H002/H003 development builds
using absolute paths to now-deleted files. This is not recoverable by copying raw
results alone. R1 explicitly replaces that historical-build reconstruction
requirement; it does **not** claim those deleted files have been recovered.

Required before R1 launch:

1. Verify the fresh pinned SM-B002 build, inherited upstream suites, the complete
   SM-B001 gate, and the complete focused SM-B002 gate. These include all inherited
   Python suites, strict typing, directed native tests, 114 fault cases, byte/RNG
   parity, and independent material/source/scheduling/retirement replay.
2. Replay **all 30** archived H001 runs, checking every raw inventory and receipt,
   canonical initial states and configs, archived launch/manifest records against
   the retained original B002 audit, and original source bytes against the pinned
   H001 commit. Recreate the exact committed H001 analysis SHA-256. This verifies
   historical empirical evidence without depending on deleted build directories.
   No historical genotype/outcome selects or filters a B002 input: all inputs are
   the already frozen canonical host population.
3. Exercise the fresh patch-0004 canonical mutation baseline in NATIVE and ZERO
   on development seed 202620999, twice each; require deterministic byte parity,
   full independent conservation/renewal/sequence replay, expected file sets and
   unchanged RNG semantics. The inherited H002/H003 test suites remain mandatory;
   their old selected-panel build-directory reconstruction is not an R1 gate.
4. Snapshot the verified build and live-gate artifacts and recheck their hashes
   before launch and analysis. Preserve all failed recovery attempts separately.
5. Require clean committed R1 driver/tests/addendum and original scientific code,
   direct observation of that commit on origin/main, and exact unchanged original
   protocol/patch pins. Preserve the source commit and every input's checksum.

This is a transparent prospective portability amendment, not a claim that the
old full-gate command passed. Lost historical prelaunch-artifact reproducibility
remains a limitation; newly rebuilt live mechanics and archived raw empirical
replay must both pass. A failed replacement gate blocks execution.

## Unchanged experiment and decision

Exactly the original 20 seeds 202628000–202628019, four arms, 5,000 ticks,
report interval 100, zero mutation, canonical 140 hosts, global interaction,
recycle decay 0.0005 and zero initial free-pool multiplier. Use the original
`run_input`, config renderer, environments, simulator binary, ordered replay,
output schema, thresholds and eight-branch decision ladder. Compare every R1
input with its original sealed input; only storage/executable paths may differ.
Only the single SUBMAT pathname may differ in config text.

At most six workers, exactly one execution attempt per matrix entry in R1,
unchanged 600-second per-run execution timeout. Resource/process/artifact failures
remain in the fixed denominator of 80 and make integrity unevaluable. No resume
or selective replacement is allowed. Disk preflight requires at least 30 GiB
free within the external POSIX volume before launch. All data remains on Elements.

The recovery driver automatically proceeds from successful gates to immutable
preparation, launch, all 80 executions, independent ordered replay and a repeat
analysis. Repeated analysis must agree byte-for-byte; this checks reproducibility,
not independent implementations. The original Python journal replay is independent
of the native simulator. Both concurrent controls and both exposure gates precede
any biological response classification. A valid negative classification ends R1;
no tuning or admission-stage execution follows automatically.

## Storage and audit

The POSIX image on Elements retains read-only seals. Export completed raw results,
configs, reports, source provenance and analysis as ordinary exFAT files for macOS,
with a recursive full-content checksum comparison. The image's POSIX metadata is
not supplied by exFAT exports; the sealed image remains the executable audit copy.
All historical failure records, failed validation logs, all R1 run receipts and
both analysis results remain available. Completion means verified classification,
not necessarily a positive scientific result.
