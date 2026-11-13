# SM-B003 development-only qualification plan

Prospective fixed engineering panel, before any reserved seed is executed.
B002 remains closed; no BFF continuation. Reserved 202629000–202629019 remain
unavailable until final preregistration, execution-aware audit and eligibility.

## Fixed inputs

Use development seed **202620999**, already used in earlier development work.
Use the unchanged 140-host inoculum, global interaction/placement, zero mutation,
recycle routing, zero histogram pool, RETAIN, 40x40 grid, **5,000 ticks**, report
interval 100. Cross IMMEDIATE/DELAY500 with all three admission policies.

For every arm execute observer-on, observer-off, and an exact observer-on repeat.
Additionally execute the unmodified patch-0006 reference for both NATIVE arms.
This is exactly **20 native executions**, not a seed search. Preserve every
attempt and failure; changing code requires a separately named development
qualification attempt, never overwriting or selectively replacing evidence.

## Mechanical/resource gates

- Fresh baseline and candidate builds from the pinned upstream plus immutable
  patches 0001–0006; candidate adds the recorded integration patch and headers.
  Capture the full final RNG through the already qualified renamed-main wrapper.
- At most six concurrent native processes, fixed 600-second native timeout.
  Qualify execution plus inventory elapsed time as well as native runtime.
- All 20 exits successful; no stderr, missing terminal witness, partial journal,
  inventory drift or input mismatch. Observer-off excludes only the two new
  observer logs; inherited scientific CSVs and full final RNG must match.
- Candidate NATIVE outputs must match the patch-0006 reference. Exact repeats
  must match all scientific CSVs and final RNG.
- Independently reconstruct all six observed histories, then repeat analysis in
  separate processes and compare deterministic results. Initial analysis limit:
  1,800 seconds per run, one process at a time. Record wall time, output sizes,
  peak resident memory and all failures. Any justified resource adjustment must
  be documented prospectively and must not alter biological inputs or endpoints.
- Report all exposure/continuity outcomes without selection. Population-level
  opportunity qualification requires at least 100 independently verified occupied
  partial opportunities/commits in **each** REPLACE development arm. A failure is
  retained and is not a license to choose a luckier seed or change victim rules.

## Storage and launch boundary

Raw runs/logs go directly to Elements; controls, build objects and immutable
receipts go in its mounted POSIX image. Preflight floors: 100 GiB raw and 10 GiB
POSIX free. Emergency floors: 2 GiB raw and 1 GiB POSIX free. No fallback to
internal storage. Export portable evidence with verified checksums.

This panel does not authorize or constitute the frozen 120-run matrix. Launch
still requires complete regression, finalized committed preregistration/source,
verified publication, final resource limits, a fresh execution-aware unseen-seed
audit, and a sealed explicit eligibility receipt. The user's conditional launch
authorization applies only after these prerequisites succeed.
