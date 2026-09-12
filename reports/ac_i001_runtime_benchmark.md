# AC-I001 full-scale runtime benchmark

- Commit: `a15e07876ebfa7631ea44ee8e5ed0fd092072785`
- Excluded seed: `202610099`
- Configuration: histogram-matched control, 32,768 tapes, 100,000 epochs,
  callback interval 100, functional observation enabled.
- Wall time: 4,808.6 seconds (1.336 hours).
- Stored size: approximately 25 MB.
- Conservation residual: zero; manifest artifact checks passed.
- Standalone 1,024-candidate assay with one Numba thread: 4.59 seconds including
  compilation/startup.

A status query inadvertently displayed the benchmark's final entropy and that it
had zero eligible scoring callbacks. This seed is excluded from confirmation,
and those observations did not alter any endpoint, seed, threshold, or treatment.
Only runtime/storage measurements set the seven-process execution limit.
