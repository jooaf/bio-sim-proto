# SM-B002 timeout diagnosis (development inputs only)

R1 retained all 80 attempts. Thirty-eight RETAIN processes hit the fixed 600-second
wall-time limit; 42 processes and independent replays succeeded. This is an
operationally unevaluable matrix, not a biological non-pass. R1 is not overwritten.

## Frozen diagnostic screen

Use only existing development seed 202620999, the already validated
IMMEDIATE_RETAIN environment, exact existing development config and pinned native
binary. Keep 5,000 ticks, every scientific parameter, and full logging unchanged.
Compare these profiles in this fixed order:

1. POSIX-image storage, one worker;
2. ordinary Elements exFAT storage, one worker;
3. ordinary Elements exFAT storage, six workers;
4. POSIX-image storage, six workers.

Each worker is an independent exact repeat of the same development input. These
are engineering probes, not independent biological replicates. Preserve them all.
The diagnostic wall-time ceiling is 1,200 seconds per process, with whole-process-
group termination on timeout. Record elapsed and native CPU times, maximum RSS,
I/O counters, process exits and final output hashes. Progress and resource samples
are recorded separately from native output files. Require completed outputs to
match the existing frozen development output byte-for-byte; never accept a faster
but scientifically different result.

This fixed-order screen is descriptive: cache/order effects are not randomized.
If the six-worker direct-exFAT profile completes with exact parity and its slowest
worker takes at most 300 seconds, qualify six workers. Otherwise qualify two only
after a new two-worker direct-exFAT development profile completes with exact parity.
If even that fails, continue engineering diagnosis rather than launching assays.
Any successful process with changed output bytes is an integrity blocker.

## Intended operational repair (to be frozen before R2)

Separate immutable POSIX control/provenance files from raw native output. Raw
journals need no POSIX permission bits and can be written directly to ordinary
exFAT directories, avoiding the filesystem-image/FUSE write path and making them
Mac-readable immediately. Store hash-sealed receipts/manifests in the POSIX image.
A prospective R2 addendum must specify the qualified worker count and one fixed
wall-time ceiling for **all** 80 runs. Biological duration remains 5,000 ticks.
Any enlarged engineering deadline must not be described as extending biological
duration or as a scientific rescue. A whole-matrix retry follows only validated
operational repair; no resume or replacement of just R1's failures.

The controller must continue from qualified infrastructure to the full matrix,
independent replay, repeat analysis and verified export. Stopping an invalid
attempt must not silently stop engineering recovery.
