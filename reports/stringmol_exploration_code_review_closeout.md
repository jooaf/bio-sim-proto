# Exploratory code review closeout

## Disposition

- **XP `d0e30340e38ac0a0a6bf2e8a54cee93c52055ca3`: approved for scoped code
  integration** by the independent Rex re-review.
- **XL `fe3bf8c2ed616902e94ecf4b58bd3bffa38cacc3`: the two remaining controller
  findings are closed by independent parent inspection and focused reruns.**
  The parent did not implement these fixes; the worker did. No third reviewer-agent
  approval is claimed. Acceptance is limited to the reviewed exploratory code and
  controller hardening, not a general scientific qualification or authorization
  to execute hard-coded historical CLI paths.

No branches have been merged or pushed as part of this review. Original scientific
outcomes, data and exports are unchanged. Zero new population runs occurred.

## Review chain

1. Initial independent reviewer: `verification/sm-rex-parent-review-v1/reviewer.stdout`.
2. Hardening re-review: `verification/sm-rex-parent-review-v2/review.stdout`.
   XP approved; XL had two remaining findings.
3. XL worker final repair from `fa5f8fc` to `fe3bf8c`: handoff
   `/tmp/sm/xlf-e/HANDOFF.md`; export
   `verification/sm-xl-final-hardening-v1/export/VERIFIED.nuon` is verified=true.
4. Parent directly inspected `locality_process.execute`, storage preflight,
   incremental inventory collection and regression tests at the final tip.

Verification directories above are relative to
`/run/media/jojo/Elements/bio-sim-results/`.

## Final XL findings closed

**Process outcome persistence:** the process outcome is flushed/fsynced before
inventory collection. An inventory exception is recorded separately, preserves
partial collected hashes and original process exception/code/timing, marks
collection incomplete, and raises `InventoryError` after persisting the receipt.
Duplicate reservation still refuses. Native receipt consumers explicitly reject
incomplete collection, even with exit0; legacy receipt reading remains supported.

**Storage-root containment:** preflight rejects symlink roots and resolved paths
outside literal intended external-storage anchors. This also rejects ancestor
redirection. `run()` now preflights before launch reservation. Mount, quota and
free-space checks remain distinct. This is admission-time enforcement, not a
claim of protection against hostile concurrent filesystem changes.

Parent evidence: `/tmp/sm/xlf-parent-check-v1/` on the Elements POSIX image.
- `tests/test_stringmol_locality_final.py`: **10 passed** normally.
- Same tests under `python -O`: **10 passed**, one expected pytest assertion warning.
- Strict mypy on the three affected production modules and final test: **4 files
  clean**.
- `git diff --check fa5f8fc HEAD`: passed; final worktree clean.
- These tests mock native process launches. No native population/build/replay was
  invoked by the parent. They include success/spawn-error/timeout followed by
  inventory failure, partial receipts, no duplicate attempt, both receipt consumers,
  redirected/valid storage, quota and headroom checks in normal/optimized modes.

Worker final scoped results were **42 passed, 1 skipped** in each interpreter
mode, strict **12 files** clean. The skipped directed logger fixture is not a pass
or a new population observer-control result. Its earlier directed qualification
and limits remain as documented in the hardening review.

## Scientific and execution boundary

XP remains a descriptive exploration with unmatched one-byte background confounds
and material/boundary/source—not complete opcode/RNG—reconstruction. XL's original
population interpretation stays **BLOCKED** because the fully-off population
condition was never executed. Engineering approval cannot retroactively pass it.

Both original 12-run budgets remain exhausted. Any XL recovery still requires a
separately authorized fresh complete 12-run matrix, new roots and protocol, with
unchanged biological settings and full observer/replay gates. Neither integration
nor further experiments are performed by this closeout.

Broad historical regression, unavailable historical CSV coverage, fresh full VM
replay and additional sanitizer coverage remain deferred and are not claimed as
passes. The user's Herdr-specific workflow waiver does not waive these documented
limits or scientific safeguards. All created completed Rex panes have closed;
this code-review sequence has no active worker.
