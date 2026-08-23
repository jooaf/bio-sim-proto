# Architecture: Data Extraction, Logging, and Experiment Framework

## 1. Overview

This document defines the architecture for the data extraction, logging, and experiment framework of the conserved program-soup evolution simulator. It supersedes the ad-hoc split between the detailed `RunWriter` (Parquet) and the bounded `paper_probe.py` (CSV) with a unified design that works at all scales, from 256-tape detailed runs to 131K-tape paper-protocol probes.

The architecture is designed so that the on-disk format (Parquet), the in-memory protocol (Apache Arrow), and the structural boundaries can be ported to Rust or Odin without a redesign.

### 1.1 Design Principles

1. **Log raw, compute offline.** The simulator writes facts. It never writes conclusions. Diversity indices, complexity measures, and open-endedness metrics are computed by a separate analysis package reading the logs.

2. **Protocol boundary.** The simulation engine communicates with the logging/extraction layer through a well-defined message-passing interface. The two can be ported, optimized, or replaced independently.

3. **Unified tiers.** One logging pipeline serves all scales. The difference between a 256-tape detailed run and a 131K-tape paper-scale probe is a configuration knob (sampling rate), not a separate code path.

4. **Arrow-native.** The protocol uses Apache Arrow RecordBatches. The on-disk format is Apache Parquet. Both are language-agnostic standards with mature Rust, C, C++, and Python implementations.

5. **Polars over pandas.** The analysis package uses Polars — Arrow-native, lazy-evaluation-capable, and sharing a Rust core with the eventual port.

---

## 2. System Boundary: FactEmitter Protocol

### 2.1 The Core Insight

The current code has no boundary between simulation and logging. The `Scheduler` calls `self.writer.append(...)` directly, passing Python dicts. The `paper_probe.py` bypasses the writer entirely and emits CSV. This is expedient but fragile:

- The simulation must know about table names, schemas, and buffering.
- Changing the logging backend requires changing the simulation.
- The paper probe cannot be compared apples-to-apples with detailed runs because they use different schemas.
- A Rust port would need to reimplement the entire Python logging stack.

### 2.2 The FactEmitter Interface

Every piece of information that leaves the simulation engine passes through a `FactEmitter` — a Protocol (structural interface) that the logging layer implements and the simulation calls.

```python
from typing import Protocol
import pyarrow as pa

class FactEmitter(Protocol):
    """Protocol boundary between simulation engine and logging/extraction layer.

    All methods accept Arrow RecordBatches matching the canonical schemas
    defined in soup/logging/schemas.py. This interface is designed so that
    it can be replaced with an Arrow Flight or Arrow IPC stream transport
    in a compiled-language port.
    """

    def emit_ticks(self, batch: pa.RecordBatch) -> None: ...
    def emit_interactions(self, batch: pa.RecordBatch) -> None: ...
    def emit_tapes(self, batch: pa.RecordBatch) -> None: ...
    def emit_lineage(self, batch: pa.RecordBatch) -> None: ...
    def emit_population(self, batch: pa.RecordBatch) -> None: ...
    def emit_events(self, batch: pa.RecordBatch) -> None: ...
    def flush(self) -> None: ...
    def close(self, exit_status: str) -> None: ...
```

### 2.3 Why Arrow RecordBatches

| Criterion | Arrow RecordBatches | Python dicts | Protobuf |
|-----------|--------------------|-------------|----------|
| Schema enforcement at boundary | Yes — schemas are explicit and validated | No — dicts are untyped | Yes — `.proto` compilation |
| Zero-copy between processes | Yes (Arrow IPC, Plasma) | No (pickle serialization) | No |
| Rust support | `arrow-rs` (mature) | Not practical | `prost` / `tonic` |
| Odin support | C FFI via Arrow C Data Interface | No | C FFI via `protobuf-c` |
| Columnar (batch-friendly) | Yes | No | No |
| Already required for Parquet | Yes — Parquet is Arrow | No | No |
| No schema compilation step | Yes | Yes | No — requires `protoc` |

**Decision:** Arrow RecordBatches. They are already required for Parquet output, so they introduce zero new dependencies. The schemas defined in `soup/logging/schemas.py` become the contract between simulation and logging — the single source of truth for the shape of every fact.

### 2.4 What the Simulation Sees

The `Scheduler` holds a reference to a `FactEmitter`:

```python
class Scheduler:
    def __init__(self, ..., emitter: FactEmitter):
        self.emitter = emitter

    def step(self, tick: int) -> None:
        # Run interactions, get facts
        # Convert to RecordBatch, emit
        self.emitter.emit_interactions(interaction_batch)
        # ...
```

The simulation does not know whether the emitter writes to Parquet, streams over a socket, or discards the data. It only knows the Arrow schemas.

### 2.5 Default Implementation: BufferedParquetEmitter

For the Python prototype, we provide a single implementation that buffers RecordBatches and flushes them as Parquet row groups:

```
Simulation ──► FactEmitter (Protocol)
                    │
                    ▼
           BufferedParquetEmitter
                    │
           ┌────────┼────────┐
           ▼        ▼        ▼
      ticks     interactions  tapes
      .parquet  .parquet     .parquet
```

In a Rust port, `FactEmitter` becomes a Rust trait, and `BufferedParquetEmitter` becomes a struct that writes Parquet via `arrow-rs` + `parquet` crates. The Arrow schemas (defined in a shared location) are the language-independent contract.

### 2.6 Alternative Emitters (Future)

Because the interface is a Protocol, alternative emitters can be plugged in without changing the simulation:

- **ArrowFlightEmitter** — streams RecordBatches over gRPC to a remote logging service
- **MetricsOnlyEmitter** — computes and prints epoch summaries to stdout, discards detail (Tier 0 equivalent)
- **MultiEmitter** — fans out to multiple emitters (e.g., Parquet + real-time metrics)
- **NullEmitter** — discards everything (for pure-throughput benchmarking)

---

## 3. Unified Tiered Logging

### 3.1 The Problem

The current system has two completely separate code paths:

| Path | Used for | Output | Schemas |
|------|----------|--------|---------|
| `RunWriter` | 256-tape detailed runs | Parquet (6 tables) | Arrow schemas in `schemas.py` |
| `paper_probe.py` | 131K-tape paper probes | CSV (6 columns) | Inline Python dicts |

These paths share no code, no schemas, and no analysis tooling. A finding from a paper probe (e.g., "entropy transition at epoch 2,433") cannot be correlated with a detailed run's interaction-level data because they come from different pipelines.

### 3.2 Unified Tiers

All runs go through the same `FactEmitter` → `BufferedParquetEmitter` pipeline. The difference between scales is a **tier configuration** that controls sampling rates:

| Tier | Interactions | Tape census | Full bytes | Ticks table | Population table | Use case |
|------|-------------|-------------|------------|-------------|-----------------|----------|
| 0 (Aggregate) | None | None | None | Tick-level only | Epoch summaries | Paper-scale 131K-tape, 16K-epoch probes |
| 1 (Sampled) | `interaction_log_rate` (e.g., 0.01 = 1%) | Every N epochs | Every M ticks (can be 0) | Per-tick | Per-epoch | Medium-scale sweeps |
| 2 (Full) | 100% | Every epoch | Every M ticks | Per-tick | Per-epoch | Small-scale detailed runs (256-tape) |

All tiers produce the **same Parquet tables with the same schemas**. The analysis code works identically on all three. The only difference is the volume of data.

### 3.3 Tier Configuration

```python
@dataclass(slots=True)
class LoggingTier:
    """Controls how much raw data is emitted.

    All tiers produce the same schemas; only sampling rates differ.
    """
    interaction_log_rate: float = 1.0       # 0.0 = none, 1.0 = all
    tape_snapshot_interval: int = 1         # epochs between tape census (0 = never)
    full_tape_snapshot_interval: int = 0    # ticks between full-byte snapshots (0 = never)
    tick_table_enabled: bool = True
    population_table_enabled: bool = True

    @classmethod
    def aggregate(cls) -> LoggingTier:
        """Paper-scale: only epoch summaries, no detail."""
        return cls(
            interaction_log_rate=0.0,
            tape_snapshot_interval=0,
            full_tape_snapshot_interval=0,
            tick_table_enabled=True,
            population_table_enabled=True,
        )

    @classmethod
    def sampled(cls, interaction_rate: float = 0.01) -> LoggingTier:
        """Medium-scale: sampled interactions, periodic census."""
        return cls(
            interaction_log_rate=interaction_rate,
            tape_snapshot_interval=100,
            full_tape_snapshot_interval=1000,
        )

    @classmethod
    def full(cls) -> LoggingTier:
        """Small-scale: every interaction, full tape snapshots."""
        return cls(
            interaction_log_rate=1.0,
            tape_snapshot_interval=1,
            full_tape_snapshot_interval=100,
        )
```

### 3.4 Sampling Strategy

Interaction sampling uses a **deterministic hash-based filter** (already implemented in `should_log_interaction`):

```python
def should_log(seed: int, tick: int, round_index: int, rate: float) -> bool:
    if rate >= 1.0:
        return True
    payload = struct.pack("<qqq", seed, tick, round_index)
    draw = int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "little")
    return draw < int(rate * 2**64)
```

This is deterministic (same seed → same sampled interactions) and does not consume simulation RNG state.

### 3.5 What Happens to paper_probe.py?

The `paper_probe.py` Numba kernel stays as-is for now — it's a separate accelerated path for paper-scale (131K-tape) runs that produces a lightweight CSV. We deliberately do **not** add a `NumbaProbeEmitter` wrapping it in the FactEmitter interface. This is a prototype; the complexity of unifying the Numba path isn't worth it when the Numba kernel will be replaced entirely by the Rust/Odin port.

**The Python `Simulation` + `BufferedParquetEmitter` path handles all Tier 0, 1, and 2 runs.** For paper-scale Tier 0 runs, the emitter skips RecordBatch construction entirely when `interaction_log_rate == 0.0`, avoiding the Python interpreter overhead per interaction. The paper probe remains available as a separate CLI (`soup-paper-probe`) for when maximum throughput is needed, but it is not part of the unified pipeline.

### 3.6 Pros and Cons of Unified Tiers

**Pros:**
- One code path to test, debug, and optimize.
- Same schemas, same analysis code at all scales.
- Config-driven; no code changes to switch between paper-scale and detailed runs.
- The `population` table (epoch summaries) is always present, so diversity metrics always work.
- Deterministic sampling ensures reproducibility.

**Cons / Risks:**
- Tier 0 through the Python pipeline will be slower than the dedicated Numba kernel because it enters the Python interpreter for each interaction, even if it discards the data.
- **Mitigation:** For Tier 0, the simulation can skip building interaction RecordBatches entirely when `interaction_log_rate == 0.0`. The `FactEmitter.emit_interactions()` simply returns immediately. A `should_emit_interactions` flag on the emitter lets the simulation skip the conversion work.
- The transition from the current dual-path system requires touching both `Scheduler` and `paper_probe.py`, which carries regression risk.
- **Mitigation:** The existing golden-run Parquet digest tests catch regressions. The transition can be done incrementally — first refactor `RunWriter` into `BufferedParquetEmitter`, then adapt `paper_probe.py`, then merge.

---

## 4. Run Directory Layout

### 4.1 Current Layout (for reference)

```
runs/<timestamp>_<config_hash>_<seed>/
├── config.toml
├── manifest.json
├── invariant_log.jsonl
├── ticks.parquet
├── interactions.parquet
├── tapes.parquet
├── lineage.parquet
├── population.parquet
├── events.parquet
└── invariant_failure_tick_*.npz   (only on violation)
```

### 4.2 Proposed Layout

```
runs/<run_id>/
├── manifest.json
├── config.toml
├── ticks.parquet
├── interactions.parquet
├── tapes.parquet
├── lineage.parquet
├── population.parquet
├── events.parquet
├── invariant_log.jsonl
├── invariant_failure_tick_*.npz        (only on violation)
└── analysis/                            (post-run, written by analysis package)
    ├── hill_numbers.parquet
    ├── high_order_entropy.parquet
    ├── conservation.parquet             (Stage 1+)
    └── stage<N>_report.md
```

**Run ID format:** `{YYYYMMDD}T{HHMMSS}.{microseconds}Z_{config_hash[:12]}_{seed}` (unchanged from current).

### 4.3 What Changed

- Added `analysis/` subdirectory for post-run computed metrics. This separates raw facts (the simulator's output) from derived conclusions (the analysis package's output).
- The raw Parquet tables are the irreplaceable artifacts. Analysis outputs can always be recomputed from them.

### 4.4 Pros and Cons

**Pros of analysis subdirectory:**
- Clear separation between raw data and computed metrics.
- Re-running analysis with updated algorithms doesn't touch the raw data.
- A Rust/Odin port of the simulator only needs to produce the raw tables; the analysis can stay in Python or move independently.

**Cons:**
- Adds a directory level. Tools that glob for `*.parquet` at the run root won't find analysis outputs.
- **Mitigation:** Analysis outputs use an `analysis_` prefix in their filenames, so they're easy to identify regardless of location.

---

## 5. Polars Migration

### 5.1 Current State

The analysis package uses `pandas` throughout:

| Module | pandas usage |
|--------|-------------|
| `analysis/load.py` | `pd.read_parquet`, `pd.DataFrame` |
| `analysis/report.py` | `df.loc[...]`, `df.groupby(...).nunique()`, `df.itertuples()` |
| `analysis/diversity.py` | `df.groupby("epoch")` |
| `analysis/complexity.py` | `df.groupby("tick")`, `df.sort_values()` |
| `experiments/runner.py` | `pd.DataFrame(...).to_parquet()` |

### 5.2 Target State

Replace all pandas usage with Polars, using **lazy evaluation as the primary API**. The primary motivations:

1. **Arrow-native.** Polars uses Arrow as its in-memory format. Zero-copy from Parquet → Polars → Arrow export. No pandas → Arrow conversion step.
2. **Lazy evaluation by default.** `pl.scan_parquet().filter(...).group_by(...).collect()` pushes predicates to the Parquet reader, reducing I/O for selective queries. `analysis/load.py` returns `pl.LazyFrame` from all public functions; callers `.collect()` when they need eager data.
3. **Expression-based API.** Avoids the `SettingWithCopyWarning` and chained-indexing pitfalls of pandas.
4. **Rust core.** Polars is written in Rust. When the simulator ports to Rust, the analysis can use `polars-rs` directly.
5. **Better performance.** Columnar, vectorized, and multi-threaded by default.

### 5.3 Migration Map

| pandas | polars |
|--------|--------|
| `pd.read_parquet(path)` | `pl.read_parquet(path)` |
| `df[df["col"] == value]` | `df.filter(pl.col("col") == value)` |
| `df.groupby("epoch")["hash"].nunique()` | `df.group_by("epoch").agg(pl.col("hash").n_unique())` |
| `df.sort_values(["a", "b"])` | `df.sort(["a", "b"])` |
| `df.iloc[0]` | `df.row(0)` or `df.head(1)` |
| `df.itertuples()` | `df.iter_rows(named=True)` |
| `pd.DataFrame(rows, columns=cols)` | `pl.DataFrame(rows, schema=cols)` |
| `df.to_parquet(path)` | `df.write_parquet(path)` |
| `int(df["col"].max())` | `df["col"].max()` (already typed) |

### 5.4 Example: Before and After

**Before (pandas), from `analysis/report.py`:**

```python
def detect_replications(interactions: pd.DataFrame) -> pd.DataFrame:
    columns = ["tick", "round_index", "direction", "source_id", "target_id", "source_hash"]
    if interactions.empty:
        return pd.DataFrame(columns=columns)
    a_into_b = (
        (interactions["a_hash_after"] == interactions["a_hash_before"])
        & (interactions["b_hash_after"] == interactions["a_hash_before"])
        & (interactions["b_hash_before"] != interactions["a_hash_before"])
        & (interactions["b_bytes_changed"] > 0)
    )
    # ... builds rows list, returns pd.DataFrame(rows)
```

**After (polars):**

```python
def detect_replications(interactions: pl.DataFrame) -> pl.DataFrame:
    schema = {"tick": pl.Int64, "round_index": pl.Int64, "direction": pl.String,
              "source_id": pl.Int64, "target_id": pl.Int64, "source_hash": pl.String}
    if interactions.is_empty():
        return pl.DataFrame(schema=schema)

    a_into_b = interactions.filter(
        (pl.col("a_hash_after") == pl.col("a_hash_before"))
        & (pl.col("b_hash_after") == pl.col("a_hash_before"))
        & (pl.col("b_hash_before") != pl.col("a_hash_before"))
        & (pl.col("b_bytes_changed") > 0)
    ).select([
        pl.col("tick"), pl.col("round_index"),
        pl.lit("a_into_b").alias("direction"),
        pl.col("a_id").alias("source_id"),
        pl.col("b_id").alias("target_id"),
        pl.col("a_hash_before").alias("source_hash"),
    ])
    # Same for b_into_a, then pl.concat([a_into_b, b_into_a]).sort(["tick", "round_index"])
```

The Polars version is more verbose for boolean-mask construction but avoids the mutable-rows-list pattern entirely, which is a correctness improvement.

### 5.5 Pros and Cons

**Pros:**
- Arrow-native (zero-copy from Parquet).
- Expression API is composable and less error-prone than pandas boolean indexing.
- Lazy evaluation can dramatically reduce I/O for large interaction tables.
- Rust core aligns with the eventual port target.
- Actively maintained; faster release cadence than pandas.

**Cons:**
- Polars is less widely known than pandas. The team needs to learn its API.
- Some pandas idioms (like `df.iloc` for positional indexing) don't have direct equivalents.
- **Mitigation:** Polars documentation is excellent, and the migration affects ~500 lines of analysis code, not the simulation core.
- The `pandas-stubs` type-checking story is more mature than Polars' type hints.
- **Mitigation:** Polars types are simpler (fewer generic parameters), so `mypy` checks most usage without stubs.

---

## 6. Experiment Framework

### 6.1 Current State

`experiments/runner.py` provides three CLI commands:

- `soup-run run <config.toml>` — single run
- `soup-run replicates <config.toml> --n-seeds N` — N seeded replicates
- `soup-run sweep <spec.toml>` — Cartesian grid sweep with index.parquet

It has no experiment registry, no lifecycle management, and no cross-experiment queryability.

### 6.2 Experiment Registry

A lightweight SQLite database at the project root (`registry.db`) tracks all runs:

```sql
CREATE TABLE runs (
    run_id          TEXT PRIMARY KEY,
    config_hash     TEXT NOT NULL,
    seed            INTEGER NOT NULL,
    stage           INTEGER NOT NULL,
    status          TEXT NOT NULL,  -- 'running', 'success', 'failed'
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    wall_time_s     REAL,
    exit_status     TEXT,
    run_dir         TEXT NOT NULL UNIQUE,
    sweep_id        TEXT REFERENCES sweeps(sweep_id),
    parameter_json  TEXT             -- sweep parameter values, if part of a sweep
);

CREATE TABLE sweeps (
    sweep_id    TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    spec_path   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_runs_sweep ON runs(sweep_id);
CREATE INDEX idx_runs_config_hash ON runs(config_hash);
```

### 6.3 Analysis Caching

Computed metrics (Hill numbers, high-order entropy, conservation snapshots) are cached in the run's `analysis/` subdirectory alongside a **content hash of the source tables** they were computed from:

```
analysis/
├── hill_numbers.parquet
├── high_order_entropy.parquet
├── conservation.parquet
└── .cache_manifest.json    # {filename: source_tables_hash}
```

Before computing a metric, the analysis package hashes the relevant source tables (e.g., `population.parquet` for Hill numbers). If the hash matches the cached manifest, computation is skipped. This avoids recomputing expensive metrics (e.g., Brotli entropy over full tape snapshots) when re-running reports on the same data.

**Cache invalidation:** The cache is keyed on the SHA-256 digest of the source tables' Parquet bytes. Any change to the raw data (including a re-run with the same seed that produces different results — which shouldn't happen but is detectable) invalidates the cache automatically.

### 6.4 Registry Semantics

- The filesystem is the **source of truth**. The registry is a **cache**.
- A run is registered when it starts (`status='running'`). It is updated when it finishes.
- A `soup-registry rebuild` command scans `runs/` directories and rebuilds the registry from `manifest.json` files.
- The registry can be queried with SQL, Polars (`pl.read_database`), or DuckDB.

### 6.5 Why SQLite

| Criterion | SQLite | Parquet index | No registry (filesystem-only) |
|-----------|--------|---------------|-------------------------------|
| Cross-run queries | SQL | Scan all index files | Glob + read manifests |
| Concurrent writes | Yes (WAL mode) | No (not designed for writes) | N/A |
| Atomic updates | Transactions | Rewrite entire file | N/A |
| Rust portability | `rusqlite` (mature) | `parquet` crate | FS operations |
| Odin portability | C FFI (sqlite3.h) | C FFI (Apache Parquet C++) | FS operations |
| Query "all failed runs in sweep X" | `SELECT ... WHERE status='failed' AND sweep_id=?` | Scan all index files | Not feasible |

**Decision:** SQLite. It adds zero operational overhead (single file, no server) and enables queries that are otherwise impractical.

### 6.6 Sweep Improvements

The current sweep mechanism produces an `index.parquet` mapping config_hash → parameters → run_dir. This is good but can be improved:

1. **Resume on interruption.** The sweep runner checks the registry for existing successful runs with matching config_hash and seed before launching a new one.
2. **Automatic analysis.** After all runs in a sweep complete, the sweep runner can optionally trigger `write_batch_stage0_report` automatically.
3. **Parameter annotations.** The sweep spec can include metadata about each parameter (description, units, expected effect) that flows into the index.

### 6.7 Experiment Lifecycle

```
                    ┌──────────┐
                    │  queued  │
                    └────┬─────┘
                         │ start
                         ▼
                    ┌──────────┐
              ┌─────│ running  │─────┐
              │     └────┬─────┘     │
              │          │           │
          exception   success    invariant
              │          │       violation
              ▼          ▼           ▼
         ┌────────┐ ┌────────┐  ┌────────┐
         │ failed │ │success │  │ failed │
         └────────┘ └────────┘  └────────┘
```

Each transition is recorded in the registry with a timestamp.

### 6.8 CLI Surface

```sh
# Single run
soup-run run <config.toml> [--report]

# Replicates
soup-run replicates <config.toml> --n-seeds 20 [--start-seed 0] [--processes 8] [--report]

# Sweep
soup-run sweep <spec.toml>

# Registry
soup-run registry list [--status failed] [--sweep <name>]
soup-run registry rebuild
soup-run registry report <run_id>
```

### 6.9 Pros and Cons

**Pros:**
- Cross-experiment queries become possible ("show me all failed seeds across all sweeps", "what's the emergence rate per population_size?").
- Resume-on-interruption saves compute for long sweeps.
- The registry is rebuildable from run directories — no single point of failure.
- SQLite is zero-config and well-supported in Rust/Odin.

**Cons:**
- Adds a new dependency (but Python includes `sqlite3` in stdlib).
- Registry and filesystem can diverge if runs are moved or deleted manually.
- **Mitigation:** `soup-run registry rebuild` reconciles them.
- The registry is not a substitute for the filesystem — it's an index. Users who prefer filesystem-only workflows can ignore it.

---

## 7. Portability to Rust / Odin

### 7.1 Design-for-Porting Principles

Every architectural decision in this document was made with the eventual compiled-language port in mind. Here is the mapping:

| Python Component | Rust Equivalent | Odin Equivalent |
|-----------------|-----------------|-----------------|
| `FactEmitter` (Protocol) | `trait FactEmitter` | `FactEmitter :: struct { vtable: ... }` (manual vtable) |
| Arrow RecordBatches | `arrow-rs` (`arrow::record_batch::RecordBatch`) | C FFI to Arrow C Data Interface |
| Parquet files | `parquet` crate + `arrow-rs` | Apache Parquet C++ via C FFI |
| `BufferedParquetEmitter` | Struct implementing `FactEmitter` trait | Same pattern |
| SQLite registry | `rusqlite` crate | `sqlite3.h` via `foreign import` |
| Polars analysis | `polars-rs` crate | Can stay in Python or use C FFI |
| NumPy arrays (sim state) | `ndarray` crate | Raw slices + manual indexing |
| Configuration (TOML) | `toml` crate | TOML parser in Odin or C FFI |

### 7.2 Arrow C Data Interface

The Arrow C Data Interface (ABI-stable, no linking required) allows two libraries to exchange Arrow arrays and schemas through C structs. This is the most portable way to cross the language boundary:

- Python's `pyarrow` exports the C Data Interface.
- Rust's `arrow-rs` imports/exports it via the `arrow` crate's `ffi` module.
- Odin can call the C Data Interface directly via `foreign import`.

This means the FactEmitter boundary can literally be a function call that passes Arrow C Data structs across a language boundary, with zero serialization overhead.

### 7.3 What Stays in Python (Initially)

- **Analysis package.** Polars has a Python frontend and a Rust core. The analysis can stay in Python even after the simulator ports to Rust, since it reads Parquet files — no language coupling.
- **Visualization.** Pygame is Python-only. The visualization reads Parquet files and can run against a completed run directory regardless of what produced it.
- **Experiment orchestration.** The runner, sweep engine, and registry can stay in Python initially. They spawn simulation processes and read their output.

### 7.4 Incremental Porting Path

1. Port the simulation engine (world, substrate, scheduler, interactions) to Rust/Odin.
2. Implement `FactEmitter` as a Rust trait / Odin interface that writes Parquet.
3. Keep the Python analysis, viz, and orchestration reading the same Parquet files.
4. Optionally port analysis to Rust using `polars-rs` for end-to-end native execution.

---

## 8. What We Are NOT Building (Yet)

These are capabilities the architecture supports but are not in scope for the current implementation:

| Capability | Why not now | How the architecture enables it later |
|-----------|-------------|--------------------------------------|
| Real-time metrics streaming (WebSocket / Prometheus) | No immediate use case; all analysis is offline | `FactEmitter` can be backed by a streaming transport |
| Distributed execution (multiple machines) | Single-machine runs meet current scale needs | Arrow Flight emitter replaces `BufferedParquetEmitter` |
| Interactive experiment dashboard | `soup-viz` handles live viewing | Analysis outputs are Parquet; any dashboard can read them |
| Automatic experiment scheduling (queue, priority) | Manual CLI is sufficient for now | Registry tracks status; a scheduler can read/write it |
| Incremental analysis (process data as it arrives) | Post-run analysis works for current run lengths | The Parquet files are appendable; a streaming reader could tail them |

---

## 9. Implementation Order

### Phase A: Foundation (no functional changes to simulation)

1. **Polars migration.** Replace pandas with polars in `analysis/` and `experiments/runner.py`. Add `polars` to dependencies. Keep existing tests passing.
2. **FactEmitter Protocol.** Define the `FactEmitter` Protocol and Arrow schemas in `soup/logging/emitter.py`. This is a pure interface; no implementation changes yet.
3. **BufferedParquetEmitter.** Implement `BufferedParquetEmitter` as a drop-in replacement for the current `RunWriter`. Validate with existing golden-run digest tests.

### Phase B: Unified logging

4. **Tier configuration.** Add `[logging.tier]` to `Config` with the tier parameters. Implement sampling logic in `BufferedParquetEmitter`.
5. **Wire Scheduler to FactEmitter.** Replace direct `self.writer.append(...)` calls with `self.emitter.emit_*()` calls. The `Scheduler` no longer knows about table names.
6. **Retire RunWriter.** Remove `RunWriter`; all logging goes through `BufferedParquetEmitter`.

### Phase C: Experiment framework

7. **Registry.** Implement `registry.py` at project root with SQLite schema and CLI commands (`soup-run registry ...`).
8. **Sweep improvements.** Add resume-on-interruption and automatic analysis triggering.
9. **Analysis caching.** Implement content-hash-based caching for computed metrics in `analysis/.cache_manifest.json`.

### Phase D: Cleanup

10. **Update documentation.** README, FINDINGS, and this architecture document.
11. **Remove pandas dependency.** Drop `pandas` and `pandas-stubs` from `pyproject.toml`.

---

## 10. Resolved Design Decisions

These were open questions in the initial draft, now settled:

| Question | Decision | Rationale |
|----------|----------|----------|
| Numba kernel for Tier 0? | **No.** Keep paper_probe.py as a separate CLI. | This is a prototype; unifying the Numba path adds complexity that will be thrown away in the Rust port. |
| Polars lazy vs eager? | **Lazy (`pl.LazyFrame`) as the primary API.** | Predicate pushdown to Parquet reader reduces I/O; callers `.collect()` when they need eager data. |
| Registry location? | **Project root: `registry.db`.** | Maximum discoverability. |
| Analysis caching? | **Yes, with content-hash-based invalidation.** | Avoids recomputing expensive metrics (Brotli entropy, Hill numbers) on repeated report runs. |
| Arrow schemas as canonical source? | **Yes.** The schemas in `soup/logging/schemas.py` are the single source of truth for table shapes. `Config.logging.tick_tables` names must match schema keys; validation enforces this. |
