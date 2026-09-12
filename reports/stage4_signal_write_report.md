# Stage 4 local signal-write mechanics

## Decision

Local partner-cell signal writing supported: **False**.

- Write-enabled changed-write range: 5–6 (frozen requirement: exactly 8)
- Write-enabled runs with all occupied tags changed: 0/5

| arm | runs | interactions | reads | dispatches | changed writes | runs with written occupied field |
|---|---:|---:|---:|---:|---:|---:|
| mismatched | 5 | 4000 | 4000 | 0 | 0 | 0 |
| write_disabled | 5 | 4000 | 4000 | 4000 | 0 | 0 |
| write_enabled | 5 | 4000 | 4000 | 1318 | 27 | 0 |

The frozen mechanics gate failed because isolated occupied cells were not reachable as interaction partners. Observed writes are descriptive only; the stop rule prohibits the planned inter-tape response test and writable-signal claims.
