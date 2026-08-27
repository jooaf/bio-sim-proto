# Parallel engine design

## Implementation status

The first opt-in `parallel-v3` engine is now implemented for the linear and recurrent V2 intent controllers. `serial-v2` remains the default and its fixed legacy digest is unchanged.

Implemented boundaries:

- cellular regulation and contested primary-production heat reservations remain canonical; organism-local upkeep, senescence, toxin handling, and digestion mutate dense organism slots in parallel and emit canonical heat/deposit/death transactions;
- due-agent caches and generated world chunks are prepared before parallel work;
- Rayon generates every due agent's complete observation, bounded candidate set, neural scores, and selected intent through an immutable kernel borrow;
- proposal randomness is derived from `(seed, RNG version, tick, organism ID, decision ordinal)` and is independent of worker scheduling;
- typed organism, occupancy, deposit, heat, alliance, lifecycle, effect, and reproduction keys are unioned into deterministic conflict components;
- singleton components containing wait, repair, or detox intents commit directly to disjoint organism slots in parallel; complex components retain canonical serial validation/commit;
- manifests and snapshots record scheduler, configured/effective workers, partition strategy, RNG version, and resolver version;
- 1-, 2-, 4-, 8-, and auto-worker tests produce the same digest and pass matter/energy conservation.

Resolver V2 performs bounded concurrent resolution only where ownership is mechanically disjoint. Movement, ingestion, heat absorption, combat, magic, reproduction, and alliance components remain serial because they mutate shared world maps, global IDs, or multi-organism state. Parallelizing those components requires partitioned world/resource transaction buffers rather than locks. `parallel-v3` currently rejects the legacy macro controller and coordinated cellular-component actions rather than silently changing either law.

A release recurrent-V2 gate over a wide 1,024×1,024 founder region measured:

| initial founders | final population | 1 worker | 4 workers | 8 workers | 4-worker speedup | 8-worker speedup |
|---:|---:|---:|---:|---:|---:|---:|
| 10,000 | 9,973 | 36.4 ticks/s | 66.9 ticks/s | 64.7 ticks/s | 1.84x | 1.78x |
| 30,000 | 29,662 | 10.8 ticks/s | 21.6 ticks/s | 24.4 ticks/s | 2.00x | 2.26x |

These are short 10-tick scaling gates, not sustained ecological outcome runs. Compared with resolver V1 on the same fixture, the 8-worker 30k result rose from 13.1 to 24.4 ticks/s (1.86x). An 8-worker 30k phase profile measured 0.42 s total: 0.02 s parallel maintenance, 0.08 s prepare, 0.11 s intent generation, 0.06 s conflict grouping, 0.11 s resolution, and 0.03 s heat diffusion. The benchmark artifacts are under `bench/results/parallel-v3-wide-workers{1,4,8}/`. A separate 100-tick recurrent fixture measured about 2.0x versus `serial-v2`, but scheduler versions are different simulation laws and should not be mixed in one experimental block. Sustained 100k–300k throughput and ecological-law comparisons remain required before replacing the default.

## Decision

Do not place Rayon around the current organism loop. The serial scheduler deliberately shuffles living IDs and commits every organism's upkeep, digestion, observation, action, death, movement, combat, and reproduction before the next ID observes the world. Parallel mutation would be racy; locking it would largely serialize execution and make lock acquisition order part of the scientific model.

Retain the current scheduler as `serial-v2`. A future multicore scheduler must be a separately selected and recorded `parallel-v3` simulation law.

## Profiling basis

The representative 14,116-organism profile (`bench/results/dense-occupancy-seed11-profile.json`) measured 25 ticks:

| phase | seconds | share of total |
|---|---:|---:|
| decision/perception | 0.830 | 66.7% |
| upkeep | 0.184 | 14.8% |
| deposit production | 0.117 | 9.4% |
| decomposition | 0.038 | 3.1% |
| heat diffusion | 0.026 | 2.1% |
| all other work | 0.049 | 3.9% |

The 10,000-founder synthetic profile attributed 82.6% of total time to decisions. Therefore:

- infinitely fast normal-workload heat diffusion would improve the representative run by only about 2%;
- snapshot parallelism cannot materially accelerate headless runs and the current asynchronous GUI already retained 99.5–99.8% of headless throughput;
- adding Rayon, synchronization, and another dependency to these minor phases is not justified;
- the dominant decision/perception phase is the required parallel boundary.

Field-heavy workloads remain a separate case. The existing 1,024-chunk synthetic fixture spends about 24% in heat diffusion and 67% in deposit production/decomposition. If that becomes a production workload, benchmark a deterministic chunk-result buffer and canonical serial commit before enabling Rayon.

## `parallel-v3` tick law

### 1. Freeze tick-start read state

Create immutable, dense views for:

- living physical and physiological fields;
- occupancy and local neighbor indices;
- deposits, corpses, and heat;
- alliances, colonies, species metadata, and active effects;
- controller policy and recurrent state.

No pointer into mutable authoritative storage may escape this phase.

### 2. Apply mandatory maintenance

Initially keep upkeep, digestion, expirations, and environmental field updates serial in canonical ID/chunk order. These are only promoted to parallel prepare/commit phases after independent profiling and conservation tests.

### 3. Generate intents in parallel

For every due organism, generate bounded observations, candidates, controller scores, and one proposal using Rayon over dense due-agent indices. Each worker writes only to its assigned intent slot and scratch arena.

Randomness must not depend on worker count or steal order. Derive a local stream from:

```text
run_seed, scheduler_version, tick, organism_id, decision_ordinal, subsystem_tag
```

A counter-based generator is preferred. SplitMix-derived xoshiro streams are acceptable if every proposal has a fixed derivation and draw contract.

### 4. Build deterministic conflict components

Each intent declares sorted read/write keys such as:

```text
organism(id)
occupancy(cell)
deposit(cell, molecule)
heat(cell)
alliance(pair)
colony(id)
species(id)
```

Bucket intents by spatial cell and non-spatial entity keys, then union overlapping buckets into conflict components. Sort component members by a canonical priority tuple independent of thread count:

```text
(resolution_class, target_key, actor_priority, actor_id, intent_index)
```

Any stochastic priority is generated in phase 3 and stored in the intent.

### 5. Resolve reservations

Within each conflict component, validate against tick-start versions and reserve finite resources:

- destination footprint cells;
- target survival/integrity budget;
- deposits and chemical inventory;
- reproduction matter and placement;
- heat and mana;
- alliance/colony membership changes.

Components with disjoint complete write sets may resolve concurrently. The first implementation should resolve serially after parallel intent generation; this isolates the main speedup while keeping conflict logic auditable.

### 6. Commit canonically

Apply accepted transactions in canonical component/member order. Failed intents do not redraw randomness. Emit deterministic event records, repair dense indices, then run matter/energy audits.

## Data contracts

```rust
struct IntentEnvelope {
    actor_id: u32,
    decision_ordinal: u32,
    priority: u64,
    intent: ActionIntent,
    reads: KeyRange,
    writes: KeyRange,
    reservation: ResourceDelta,
}

struct Resolution {
    intent_index: u32,
    accepted: bool,
    failure: FailureCode,
    committed_delta: ResourceDelta,
}
```

Use typed enums/indices rather than strings. Store keys and deltas in retained per-thread arenas and flatten once per phase.

## Scientific compatibility

`parallel-v3` is deterministic within its own declared law but is not bitwise or causally equivalent to `serial-v2`. Every manifest must record:

- scheduler name and schema version;
- worker count and partition strategy;
- RNG derivation version;
- conflict resolver version;
- SIMD/scalar neural mode;
- complete build identifier.

Worker count should not affect results. If it does, the implementation fails acceptance.

## Acceptance gates

1. Same seed/config/scheduler produces the same digest at 1, 2, 4, 8, and auto thread counts.
2. Exact integer matter conservation and existing floating energy tolerance pass.
3. Every accepted transaction has complete declared write keys; a debug shadow executor detects undeclared mutation.
4. No deadlock, lock-order dependence, or unbounded intent queue exists.
5. Benchmarks report prepare, intent, grouping, resolution, and commit separately at 1.2k, 10k, and synthetic 100k populations.
6. Parallel speedup is at least 2x at 10k on four performance cores before making the mode generally available.
7. Preregistered multi-seed ecological comparisons characterize the changed scheduling law; engine modes are not mixed inside one experimental block.

## Implementation sequence

1. Add read-only observation tests and explicit read/write-key extraction to existing intents.
2. Introduce counter-derived decision RNG while retaining serial execution and verify a new versioned digest.
3. Split `decide_and_act` into `observe_and_propose` and `validate_and_commit` without parallelism.
4. Add a serial `parallel-v3` reference resolver and conservation/property tests.
5. Parallelize only `observe_and_propose` with Rayon.
6. Profile conflict grouping; parallelize disjoint component resolution only if it remains material.

This sequence avoids simultaneously changing ownership, randomness, scheduling, and concurrency, which would make failures scientifically and mechanically uninterpretable.
