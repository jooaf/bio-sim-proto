# Stage 4 signal-write reachability positive control

## Decision

Fully connected partner-cell signal writing supported: **False**.

- Write-enabled changed-write range: 14–15 (frozen requirement: 16)
- Complete write-enabled fields: 0/5

| arm | runs | interactions | reads | dispatches | changed writes | complete fields |
|---|---:|---:|---:|---:|---:|---:|
| mismatched | 5 | 4000 | 4000 | 0 | 0 | 0 |
| write_disabled | 5 | 4000 | 4000 | 4000 | 0 | 0 |
| write_enabled | 5 | 4000 | 4000 | 597 | 71 | 0 |

The positive control failed: writers whose own tags were replaced stopped dispatching before every cell changed. Per the frozen rule, writable-signal and inter-tape-response work stops here.
