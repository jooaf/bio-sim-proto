# Autonomous scientific workflow

The user explicitly requests continued autonomous operational recovery, not a stop
whenever a batch fails. A fail-closed experiment gate stops that attempt; it does
not stop the engineering work.

- After timeouts or infrastructure faults, retain all evidence, diagnose the cause,
  benchmark repairs on development inputs, and continue with a prospectively
  documented whole-matrix recovery when justified.
- Never selectively retry failed scientific runs, discard outcomes, tune until
  significance, or silently change biological horizons or decision criteria.
- Distinguish operational resource failures from valid negative scientific results.
  Respect preregistered stopping rules for valid results.
- Connect successful validation to execution, independent replay, repeat analysis,
  and export rather than requiring another user message between stages.
- A background process or completion monitor is not an autonomous reasoning loop.
  Do not claim ongoing recovery when the process has stopped and no repair is active.
- Interrupt the user only for a genuine critical blocker or required authorization.
  Status requests should report actual live progress and failures candidly.
- Stringmol is the active track. BFF remains closed as NO-GO.
- Write results to Elements. Preserve the POSIX seals in its filesystem image and
  export ordinary Mac-readable files with verified checksums. Never silently fall
  back to storing experimental results on the internal disk.
