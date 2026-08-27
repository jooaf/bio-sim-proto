# Python Reference-Engine Optimization Notes

## Scope

This pass optimized only the existing Python reference engine and benchmark notes. It did not edit `rust/**`, `pyproject.toml`, `src/organism_sim/{cli,app,recording}.py`, or their behavior.

Reference inputs:

- `bench/results/profile_before/`
- `bench/results/baseline/metrics.json`
- `bench/results/regress_baseline.json`
- `bench/regress_check.py`

## Hot-path changes

The final working tree contains these semantics-preserving changes:

- Skip primary-production work in `_upkeep` when its configured target is zero.
- Return immediately from `World.remove_heat` for non-positive requests.
- Make `World.heat_at` a read-only lookup: missing chunks return zero rather than generating terrain. The final implementation performs the chunk dictionary lookup directly, avoiding a second method call on this multi-million-call path.
- Scan deposit inventories directly for decomposition and production. Production caches local methods/data, skips cold/full deposits, uses a single-batch fast path for the overwhelmingly common inventory shape, and retains the original multi-batch distribution order and arithmetic.
- Add a single-cell `remove_heat` path used by deposit production and heat absorption. It preserves the generic path's floating-point operation order while avoiding temporary chunk lists, `ensure_positions`, and generator-based summation.
- Replace hottest-cell `max(..., key=...)` work with a single ordered scan using strict `>` comparison. This preserves first-max tie behavior.
- Build nearby/contact occupancy sets with ordered cell scans and no temporary per-cell empty sets. Organism filtering does not draw randomness, and the prey/mate routines retain their original iteration and RNG order.
- Cache immutable or position/body-derived values on organisms: footprint cells, nearby cells by radius, structural mass, energy capacity, body signature, food chemistry, policy vectors, maturity values, and position-relative distances. Mutation paths invalidate body-derived caches.
- Reduce `can_place` allocation by scanning cached footprint offsets directly and materializing only touched chunk keys, while still generating every touched chunk before checking occupancy.

## Profile evidence

The original 1200-founder, 110-tick cProfile run reported:

- `_decide_and_act`: 16.609 s cumulative
- built-in `max`: 4.634 s cumulative across 5,008,462 calls
- `_upkeep`: 2.253 s cumulative
- `remove_heat`: 2.546 s cumulative across 712,116 calls

The intermediate post-optimization profile in `bench/results/pyopt_profile_after/` reported the same deterministic 110-tick trajectory with:

- `_decide_and_act`: 14.387 s cumulative
- built-in `max`: 0.577 s cumulative
- `_upkeep`: 0.596 s cumulative
- `remove_heat`: 1.733 s cumulative across 588,557 calls

The final direct heat lookup and single-cell removal path were added after that profile and verified by the strict regression fingerprint.

## Exact regression checks

Command:

```text
uv run python bench/regress_check.py
```

The stored 600-founder, seed-7, 1500-tick fingerprint matched before finishing the pass and after every additional cluster:

| checkpoint | result | throughput |
|---|---|---:|
| existing optimized tree | exact match | 26.7 ticks/s |
| single-batch deposit production | exact match | 26.9 ticks/s |
| `can_place` allocation reduction | exact match | 27.0 ticks/s |
| direct read-only heat lookup | exact match | 27.4 ticks/s |
| single-cell heat removal | exact match | 30.3 ticks/s |

Final fingerprint highlights:

- population: 914
- births/deaths: 1973 / 1659
- organism digest: `c729610d65ed1037f46fed2a9d22758963cc48f46cae8a2f1c5a3fbfa444d750`
- deposit digest: `b3859c394ae2ccfe9efa5bb4ac60bef0e2e81c0c769d322c7550f67cd0f0fdad`
- dynamic energy error: `-0x1.2800000000000p-29`

No divergent cluster was retained.

## Final benchmark

Command:

```text
uv run python bench/perf.py --scales 300,600,1200 --ticks 300 --warmup 50 --label pyopt_final
```

Results are in `bench/results/pyopt_final/`.

| founders | supplied baseline ticks/s | final ticks/s | speedup | change |
|---:|---:|---:|---:|---:|
| 300 | 35.6 | 48.4 | 1.36x | +35.6% |
| 600 | 24.5 | 33.2 | 1.36x | +35.6% |
| 1200 | 5.6 | 19.7 | 3.49x | +249.1% |

The stored baseline measured 400 ticks while the requested final run measured 300 ticks; both use seed 7, audit disabled, and a 50-tick warmup. Population and world growth make cross-duration rates trajectory-dependent, so the table is the requested practical comparison rather than a controlled microbenchmark.

## Validation

The optimization agent initially validated 62 tests and the engine-specific Ruff scope. During final integration, the benchmark lint findings were cleaned up and Rust CLI tests were added. Final repository validation is:

- `uv run --extra dev pytest -q`: **64 passed**.
- `uvx ruff check src tests bench`: **passed**.
- `uv run python bench/regress_check.py`: exact fingerprint match.
