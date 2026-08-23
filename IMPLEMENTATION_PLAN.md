# Implementation Plan: Data Extraction, Logging, and Experiment Framework

**Target audience:** A coding agent that needs to implement this from scratch. Read this entire document before writing any code.

---

## 0. Project Context

This is a research simulator for self-modifying program-soup evolution (think: Brainfuck-variant programs that interact, copy, and mutate inside a flat population). The simulator (`soup/`) is already built through Stage 1. The analysis package (`analysis/`) and experiment runner (`experiments/runner.py`) already work using pandas and a direct-coupling logging approach.

**What we're doing here:** Refactoring the data extraction, logging, and experiment framework with four goals:
1. Replace pandas with Polars (lazy evaluation) throughout analysis and experiments
2. Introduce a `FactEmitter` Protocol boundary between simulation and logging (for future Rust/Odin portability)
3. Unify the logging pipeline with config-driven tiers (so paper-scale and detail-scale runs use the same code path)
4. Add an experiment registry (SQLite) and analysis caching (content-hash-based)

**Key constraint:** This is a prototype. Do not over-engineer. The Numba paper-probe kernel stays as a separate CLI — do NOT try to unify it into the FactEmitter pipeline. It will be replaced by the Rust/Odin port.

---

## 1. Design Decisions (Pre-Settled — Do Not Reopen)

| Decision | Answer |
|----------|--------|
| Message-passing boundary | `FactEmitter` Protocol accepting Arrow RecordBatches |
| On-disk format | Parquet (zstd compression, same schemas as today) |
| Analysis library | Polars with **lazy evaluation** as primary API (`pl.LazyFrame`) |
| Logging tiers | Unified pipeline, 3 tiers (Aggregate / Sampled / Full), same schemas |
| Numba paper probe | **Leave alone.** Do not unify. Separate CLI stays as-is. |
| Experiment registry | SQLite at project root: `registry.db` |
| Analysis caching | Content-hash-based manifest in `analysis/.cache_manifest.json` |
| Run directory layout | Add `analysis/` subdirectory for computed metrics; otherwise unchanged |

---

## 2. Files to Create

### 2.1 `soup/logging/emitter.py` — FactEmitter Protocol

```python
"""Protocol boundary between simulation engine and logging/extraction layer.

All methods accept Arrow RecordBatches matching the canonical schemas defined
in soup/logging/schemas.py. The simulation never knows what happens to the data
after emission.
"""

from typing import Protocol
import pyarrow as pa


class FactEmitter(Protocol):
    """Sink for simulation facts. All methods accept Arrow RecordBatches."""

    def emit_ticks(self, batch: pa.RecordBatch) -> None: ...
    def emit_interactions(self, batch: pa.RecordBatch) -> None: ...
    def emit_tapes(self, batch: pa.RecordBatch) -> None: ...
    def emit_lineage(self, batch: pa.RecordBatch) -> None: ...
    def emit_population(self, batch: pa.RecordBatch) -> None: ...
    def emit_events(self, batch: pa.RecordBatch) -> None: ...
    def flush(self) -> None: ...
    def close(self, exit_status: str) -> None: ...


class NullEmitter:
    """Discards all facts. Used for pure-throughput benchmarking."""

    def emit_ticks(self, batch: pa.RecordBatch) -> None: pass
    def emit_interactions(self, batch: pa.RecordBatch) -> None: pass
    def emit_tapes(self, batch: pa.RecordBatch) -> None: pass
    def emit_lineage(self, batch: pa.RecordBatch) -> None: pass
    def emit_population(self, batch: pa.RecordBatch) -> None: pass
    def emit_events(self, batch: pa.RecordBatch) -> None: pass
    def flush(self) -> None: pass
    def close(self, exit_status: str) -> None: pass
```

**Requirements:**
- `FactEmitter` is a `typing.Protocol` — structural subtyping, no inheritance needed.
- `NullEmitter` provides a no-op implementation for benchmarking.
- The Protocol exists so that later, a Rust process can implement the same interface over Arrow IPC.

### 2.2 `soup/logging/tiered_writer.py` — BufferedParquetEmitter

This replaces the current `soup/logging/writer.py` `RunWriter`. It implements `FactEmitter` and writes Parquet files.

**Key design points:**
- Buffers RecordBatches per table name, flushes whole row groups to Parquet.
- Uses the schemas from `soup/logging/schemas.py` (already exist).
- Configurable tier via a `LoggingTier` dataclass (see below).
- Interaction sampling uses the existing deterministic hash-based filter (from `RunWriter.should_log_interaction` — move it here).
- Emits empty Parquet files for all tables on `close()`, even if no rows were buffered (so analysis always sees all tables).
- Writes `manifest.json` with git commit, package versions, wall time, exit status (same fields as current `RunWriter`).
- Creates the run directory with `config.toml` and `invariant_log.jsonl` (same layout as today).

```python
from dataclasses import dataclass


@dataclass(slots=True)
class LoggingTier:
    """Controls how much raw data is emitted. All tiers produce the same schemas."""
    interaction_log_rate: float = 1.0       # 0.0 = none, 1.0 = all
    tape_snapshot_interval: int = 1         # epochs between tape census (0 = never)
    full_tape_snapshot_interval: int = 0    # ticks between full-byte snapshots (0 = never)
    tick_table_enabled: bool = True
    population_table_enabled: bool = True

    @classmethod
    def aggregate(cls) -> "LoggingTier":
        """Paper-scale: only epoch summaries, no per-interaction detail."""
        return cls(interaction_log_rate=0.0, tape_snapshot_interval=0,
                   full_tape_snapshot_interval=0)

    @classmethod
    def sampled(cls, interaction_rate: float = 0.01) -> "LoggingTier":
        """Medium-scale: sampled interactions, periodic census."""
        return cls(interaction_log_rate=interaction_rate,
                   tape_snapshot_interval=100, full_tape_snapshot_interval=1000)

    @classmethod
    def full(cls) -> "LoggingTier":
        """Small-scale: every interaction, full tape snapshots."""
        return cls(interaction_log_rate=1.0, tape_snapshot_interval=1,
                   full_tape_snapshot_interval=100)
```

**Implementation notes:**
- The `BufferedParquetEmitter.__init__` takes `(config: Config, run_dir: Path | None, tier: LoggingTier)`.
- It is a drop-in replacement for `RunWriter` with the same constructor signature plus `tier`.
- Move `hash_tape` and `should_log_interaction` static methods from `RunWriter` to this class.
- The `first_seen` dict (tracking content hash first appearance) moves here too.
- `flush()` writes each nonempty buffer as one Parquet row group, then clears buffers.
- `close(exit_status)` calls `flush()`, ensures all table files exist (empty if needed), closes Parquet writers, writes manifest.

### 2.3 `experiments/registry.py` — SQLite Experiment Registry

SQLite database at project root (`registry.db`). The filesystem is the source of truth; the registry is a rebuildable cache.

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS runs (
    run_id          TEXT PRIMARY KEY,
    config_hash     TEXT NOT NULL,
    seed            INTEGER NOT NULL,
    stage           INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'running',
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    wall_time_s     REAL,
    exit_status     TEXT,
    run_dir         TEXT NOT NULL UNIQUE,
    sweep_id        TEXT,
    parameter_json  TEXT
);

CREATE TABLE IF NOT EXISTS sweeps (
    sweep_id    TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    spec_path   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_sweep ON runs(sweep_id);
CREATE INDEX IF NOT EXISTS idx_runs_config_hash ON runs(config_hash);
```

**API:**

```python
def init_db(db_path: str | Path = "registry.db") -> None:
    """Create tables and indexes if they don't exist."""

def register_run(db_path: str | Path, run_id: str, config_hash: str,
                 seed: int, stage: int, run_dir: str | Path,
                 sweep_id: str | None = None,
                 parameter_json: str | None = None) -> None:
    """Record a run as 'running'."""

def update_run_status(db_path: str | Path, run_id: str, status: str,
                      exit_status: str | None = None,
                      wall_time_s: float | None = None) -> None:
    """Update status to 'success' or 'failed', optionally setting finish fields."""

def register_sweep(db_path: str | Path, sweep_id: str, name: str,
                   spec_path: str | Path) -> None:
    """Record a new sweep."""

def rebuild(db_path: str | Path, runs_root: str | Path = "runs") -> int:
    """Scan runs/ directories, read manifest.json, rebuild registry. Returns count."""

def list_runs(db_path: str | Path, status: str | None = None,
              sweep_id: str | None = None) -> list[dict]:
    """Query runs with optional filters."""
```

**Implementation notes:**
- Use Python stdlib `sqlite3` module (no new dependency).
- Use WAL mode for concurrent read/write: `PRAGMA journal_mode=WAL;`
- `rebuild()` clears the runs table and re-scans. It does NOT touch sweeps.
- `run_id` is the run directory name (e.g., `20260808T034006.807001Z_5eef6826453d_18`).
- All DB functions take `db_path` as first argument so they work on any path.

### 2.4 `analysis/cache.py` — Content-Hash-Based Analysis Cache

Avoids recomputing expensive metrics when source tables haven't changed.

```python
def source_hash(run_dir: Path, table_names: list[str]) -> str:
    """SHA-256 of the named Parquet files' bytes in sorted order."""

def is_cached(run_dir: Path, metric_name: str, table_names: list[str]) -> bool:
    """True if the metric's cache manifest matches current source hashes."""

def write_cache_manifest(run_dir: Path, metrics: dict[str, list[str]]) -> None:
    """Write .cache_manifest.json: {metric_filename: sha256_of_sources}."""

def invalidate(run_dir: Path, metric_name: str | None = None) -> None:
    """Remove cached metric file(s). If metric_name is None, clear all."""
```

**Cache manifest format** (`analysis/.cache_manifest.json`):

```json
{
  "hill_numbers.parquet": "abc123def456...",
  "high_order_entropy.parquet": "789ghi012jkl..."
}
```

**Implementation notes:**
- `source_hash` reads the named Parquet files in sorted order and hashes their concatenated bytes with SHA-256.
- `is_cached` checks: (a) the metric file exists, (b) the manifest has an entry for it, (c) the entry matches the current source hash.
- `write_cache_manifest` reads existing manifest (if any), updates the given entries, writes back.
- This is simple enough to not need a separate file — the functions can go in `analysis/load.py` or a small `analysis/cache.py`.

---

## 3. Files to Modify

### 3.1 `pyproject.toml` — Add Polars, Remove Pandas

- Add `polars>=1.0` to `dependencies`.
- Remove `pandas>=2.2` and `pandas-stubs>=2.2` from dependencies and dev dependencies.
- Remove `pyarrow>=17` from explicit dependencies (Polars depends on it transitively, but we still use `pyarrow` directly for schemas, so keep it listed).
- Keep `pyarrow` — we use `pyarrow.Schema`, `pyarrow.RecordBatch`, and `pyarrow.parquet` in the emitter.

### 3.2 `analysis/load.py` — Pandas → Polars (Lazy)

Rewrite to use Polars lazy frames:

```python
import polars as pl
from pathlib import Path
from dataclasses import dataclass
from typing import Any

TABLE_NAMES = ("ticks", "interactions", "tapes", "lineage", "population", "events")


@dataclass(frozen=True, slots=True)
class RunData:
    run_dir: Path
    config: "Config"
    manifest: dict[str, Any]
    tables: dict[str, pl.LazyFrame]
    _eager_cache: dict[str, pl.DataFrame]  # lazily filled

    def table(self, name: str) -> pl.DataFrame:
        """Return one required table as an eager DataFrame (cached)."""
        if name not in self._eager_cache:
            self._eager_cache[name] = self.tables[name].collect()
        return self._eager_cache[name]

    def lazy_table(self, name: str) -> pl.LazyFrame:
        """Return one required table as a lazy frame (no I/O yet)."""
        return self.tables[name]


def load_run(run_dir: str | Path) -> RunData:
    """Load config, manifest, and every Stage 0 Parquet table."""
    path = Path(run_dir)
    if not path.is_dir():
        raise FileNotFoundError(f"run directory does not exist: {path}")
    # ... config loading unchanged ...
    tables: dict[str, pl.LazyFrame] = {}
    for name in TABLE_NAMES:
        parquet_path = path / f"{name}.parquet"
        if not parquet_path.exists():
            raise FileNotFoundError(f"missing required table: {parquet_path}")
        tables[name] = pl.scan_parquet(parquet_path)
    return RunData(path, config, manifest_raw, tables, {})
```

**Requirements:**
- Public API returns `pl.LazyFrame` by default via `.lazy_table()`.
- `.table()` returns eager `pl.DataFrame` with caching.
- `load_run()` uses `pl.scan_parquet()` (lazy). The actual Parquet I/O is deferred until `.collect()` is called.
- Keep `TABLE_NAMES` and `RunData` structure as close to the existing code as possible.

### 3.3 `analysis/report.py` — Pandas → Polars

Replace all pandas operations with Polars equivalents. Key changes:

| Current (pandas) | Replacement (polars) |
|---|---|
| `df.loc[condition]` | `df.filter(condition)` |
| `df.groupby("epoch")["hash"].nunique()` | `df.group_by("epoch").agg(pl.col("hash").n_unique())` |
| `df.sort_values(["a", "b"])` | `df.sort(["a", "b"])` |
| `df.itertuples(index=False)` | `df.iter_rows(named=True)` |
| `df.iloc[0]` | `df.row(0)` or `df.head(1).row(0)` |
| `df.empty` | `df.is_empty()` |
| `pd.DataFrame(rows, columns=cols)` | `pl.DataFrame(rows, schema=cols, orient="row")` |
| `df.to_parquet(path, index=False)` | `df.write_parquet(path)` |
| Boolean mask via `df["col"] == value` | `pl.col("col") == value` |

**Specific function rewrites:**

- `detect_replications()` — Use `filter()` with Polars expressions instead of boolean mask indexing. Build a→b and b→a frames with `.select()`, then `pl.concat([a_into_b, b_into_a]).sort(["tick", "round_index"])`.
- `summarize_stage0()` — Use `.group_by()` instead of `.groupby()`. Use `.n_unique()` instead of `.nunique()`. Use `.max()` (returns typed value, no cast needed).
- `write_stage0_report()` — Same pattern. The complexity and diversity calls pass DataFrames; adapt to Polars.
- `write_batch_stage0_report()` — Build rows as a list of dicts, create `pl.DataFrame` at the end if needed, or just format strings directly (the output is markdown).
- `parquet_digest()` — Unchanged (reads raw bytes, not using pandas).

**Important:** All functions that accept DataFrames should accept `pl.DataFrame` (eager). Use `.collect()` on lazy frames before passing to these functions, or make them accept lazy frames and collect internally.

### 3.4 `analysis/diversity.py` — Pandas → Polars

- `hill_number()` — Already uses NumPy, no change needed.
- `epoch_hill_numbers()` — Replace `df.groupby("epoch")` with `df.group_by("epoch")`. Build result as `pl.DataFrame` instead of `pd.DataFrame`.
- `spatial_beta_diversity()` — Already returns empty DataFrame. Update to Polars schema.

### 3.5 `analysis/complexity.py` — Pandas → Polars

- `soup_high_order_entropy()` — Replace `tapes[tapes["full_bytes"].notna()]` with `tapes.filter(pl.col("full_bytes").is_not_null())`. Replace `groupby("tick")` with `group_by("tick")`. Build result as `pl.DataFrame`.

### 3.6 `analysis/modes.py`, `analysis/organizations.py`, `analysis/trophic.py` — Update Return Types

These are placeholders returning empty DataFrames. Update them to return `pl.DataFrame` with Polars schemas.

### 3.7 `experiments/runner.py` — Pandas → Polars + Registry Integration

- Replace `pd.DataFrame(...).to_parquet(...)` with `pl.DataFrame(...).write_parquet(...)`.
- Replace `pd.read_parquet(...)` with `pl.read_parquet(...)`.
- Integrate with registry: call `register_run()` before starting a run, `update_run_status()` after completion.
- Integrate with analysis cache: before running analysis, check cache; after running, write cache manifest.
- The sweep index (`index.parquet`) switches from `pd.DataFrame.to_parquet` to `pl.DataFrame.write_parquet`.

### 3.8 `soup/simulation.py` — Use BufferedParquetEmitter

- Replace `from soup.logging.writer import RunWriter` with `from soup.logging.tiered_writer import BufferedParquetEmitter, LoggingTier`.
- `self.writer = BufferedParquetEmitter(config, run_dir=run_dir, tier=LoggingTier.full())`.
- Rename `self.writer` to `self.emitter` throughout.

### 3.9 `soup/scheduler.py` — Wire to FactEmitter

- Accept `emitter: FactEmitter` instead of `writer: RunWriter`.
- Currently calls `self.writer.append("interactions", {...})`, `self.writer.append("ticks", {...})`, etc.
- **Phase 1 approach:** For now, keep the dict-based append pattern but route it through the emitter. The `BufferedParquetEmitter` can accept dicts and convert to RecordBatches internally. (A cleaner Arrow-native approach can come later.)
- **OR** add an `append(table_name, row_dict)` method to `FactEmitter` for a smoother transition. This is fine for a prototype.
- Update `self.writer.hash_tape` → `self.emitter.hash_tape`.
- Update `self.writer.first_seen` → `self.emitter.first_seen`.
- Update `self.writer.should_log_interaction(...)` → `self.emitter.should_log_interaction(...)`.
- Update `self.writer.flush()` → `self.emitter.flush()`.
- In `advance()`, the invariant violation dump still writes to `self.emitter.run_dir`.

### 3.10 `soup/logging/writer.py` — Deprecate

After `BufferedParquetEmitter` is working, remove `RunWriter` or leave a re-export for backward compatibility:

```python
# soup/logging/writer.py
from soup.logging.tiered_writer import BufferedParquetEmitter as RunWriter  # backward compat
```

**Decision:** Keep a backward-compat re-export initially. Remove the original implementation only after all tests pass.

---

## 4. CLI Changes

### 4.1 New `soup-run registry` subcommands

Add to `experiments/runner.py`:

```sh
soup-run registry list [--status failed|running|success] [--sweep <name>]
soup-run registry rebuild [--runs-root runs]
```

### 4.2 Update Existing Commands

- `soup-run run` — registers the run before starting, updates on completion/failure.
- `soup-run replicates` — registers each replicate.
- `soup-run sweep` — registers the sweep and each member run.
- `soup-report` — uses analysis cache; add `--no-cache` flag to force recomputation.

---

## 5. Implementation Order

### Step 1: Polars migration (foundation)

**Files:** `pyproject.toml`, `analysis/load.py`, `analysis/report.py`, `analysis/diversity.py`, `analysis/complexity.py`, `analysis/modes.py`, `analysis/organizations.py`, `analysis/trophic.py`, `experiments/runner.py`

**Validation:** `uv run pytest` passes all existing tests. `uv run mypy --strict soup analysis` passes. Golden-run Parquet digest unchanged (because Parquet format is the same).

### Step 2: FactEmitter Protocol + BufferedParquetEmitter

**Files (new):** `soup/logging/emitter.py`, `soup/logging/tiered_writer.py`

**Files (modify):** `soup/logging/writer.py` (add re-export)

**Validation:** Unit test: create a `BufferedParquetEmitter`, emit ticks/interactions/tapes/population/events, close, verify all Parquet files exist and load correctly with Polars.

### Step 3: Wire Scheduler and Simulation

**Files (modify):** `soup/scheduler.py`, `soup/simulation.py`

**Validation:** Golden-run Parquet digest test. A short run with the same seed/config produces byte-identical Parquet to the pre-refactor output. (This is the critical regression test.)

### Step 4: Analysis cache

**Files (new):** `analysis/cache.py`

**Files (modify):** `analysis/report.py` (integrate cache)

**Validation:** Run report twice on same run directory — second run is instant (cache hit). Modify a source table — cache invalidates, report recomputes.

### Step 5: Experiment registry

**Files (new):** `experiments/registry.py`

**Files (modify):** `experiments/runner.py` (integrate registry + new CLI subcommands)

**Validation:** `soup-run registry rebuild` populates registry from existing runs. `soup-run registry list` shows runs. Run a single config → registry updated.

### Step 6: Cleanup and docs

- Remove pandas/pandas-stubs from `pyproject.toml`.
- Remove `RunWriter` original implementation (keep re-export only if needed by viz).
- Update `README.md` and `FINDINGS.md` to reflect the new architecture.
- Run full test suite one final time.

---

## 6. What NOT to do

- Do NOT touch `paper_probe.py`. It stays as-is.
- Do NOT touch `soup/viz/`. The visualizer uses the same Parquet files; it should continue working.
- Do NOT change the Parquet schemas. The existing schemas in `soup/logging/schemas.py` are the contract.
- Do NOT change the run directory naming format.
- Do NOT change `soup/config.py` except to add `LoggingTier` fields if needed (but prefer keeping the tier in the emitter, not the config, for now).
- Do NOT add new dependencies beyond `polars`. Use stdlib `sqlite3`.
- Do NOT over-engineer. The `FactEmitter` Protocol exists for future Rust portability. For now, dict-based `append()` on the emitter is fine.

---

## 7. Success Criteria

1. `uv run pytest` — all existing tests pass.
2. `uv run mypy --strict soup analysis` — zero errors.
3. Golden-run test: same seed + config produces byte-identical Parquet digest as before the refactor.
4. `uv run soup-report runs/<any-existing-run>` — produces the same report as before (same numbers, same structure).
5. `uv run soup-run registry rebuild && uv run soup-run registry list` — works.
6. Analysis cache: second report run is faster than first (cache hit).
7. The `experiments/EXPERIMENT_IDEAS.md` experiments can be expressed as sweep specs using the refactored runner.
