"""Buffered deterministic Parquet writer for raw simulation facts."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import socket
import struct
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from numpy.typing import NDArray

from soup.config import Config
from soup.logging.schemas import table_schemas


class RunWriter:
    """Own one run directory and append rows in deterministic row groups."""

    def __init__(self, config: Config, run_dir: Path | None = None) -> None:
        self.config = config
        config_bytes = self._config_bytes(config)
        self.config_hash = hashlib.sha256(config_bytes).hexdigest()[:12]
        if run_dir is None:
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
            run_dir = Path(config.run.output_dir) / f"{timestamp}_{self.config_hash}_{config.run.seed}"
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=False)
        (self.run_dir / "config.toml").write_bytes(config_bytes)
        (self.run_dir / "invariant_log.jsonl").write_text("", encoding="utf-8")

        self.schemas = table_schemas()
        self.buffers: dict[str, list[dict[str, Any]]] = {name: [] for name in self.schemas}
        self.writers: dict[str, pq.ParquetWriter] = {}
        self.started_at = datetime.now(UTC)
        self.started_clock = time.perf_counter()
        self.first_seen: dict[str, int] = {}
        self._manifest = self._base_manifest()
        self._write_manifest(exit_status="running", wall_time_seconds=0.0)

    @staticmethod
    def _config_bytes(config: Config) -> bytes:
        import tomli_w

        return tomli_w.dumps(config.to_dict()).encode("utf-8")

    @staticmethod
    def hash_tape(tape: NDArray[np.uint8]) -> str:
        """Return a stable 128-bit content hash for one fixed-length tape."""

        return hashlib.blake2b(tape.tobytes(), digest_size=16).hexdigest()

    def should_log_interaction(self, tick: int, round_index: int) -> bool:
        """Sample logs deterministically without consuming simulation RNG state."""

        rate = self.config.logging.interaction_log_rate
        if rate <= 0.0:
            return False
        if rate >= 1.0:
            return True
        payload = struct.pack("<qqq", self.config.run.seed, tick, round_index)
        draw = int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "little")
        return draw < int(rate * 2**64)

    def append(self, table: str, row: dict[str, Any]) -> None:
        """Buffer one raw fact; no analysis is performed here."""

        if table not in self.buffers:
            raise KeyError(f"unknown log table {table!r}")
        self.buffers[table].append(row)

    def append_event(
        self,
        *,
        tick: int,
        event_type: str,
        tape_id: int | None = None,
        content_hash: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        """Append a rare factual event with canonical JSON details."""

        self.append(
            "events",
            {
                "tick": tick,
                "event_type": event_type,
                "tape_id": tape_id,
                "content_hash": content_hash,
                "details_json": json.dumps(details or {}, sort_keys=True, separators=(",", ":")),
            },
        )

    def flush(self) -> None:
        """Write each nonempty buffer as one deterministic Parquet row group."""

        codec = None if self.config.logging.compression == "none" else self.config.logging.compression
        for table_name, schema in self.schemas.items():
            rows = self.buffers[table_name]
            if not rows:
                continue
            arrow_table = pa.Table.from_pylist(rows, schema=schema)
            parquet_writer = self.writers.get(table_name)
            if parquet_writer is None:
                parquet_writer = pq.ParquetWriter(
                    self.run_dir / f"{table_name}.parquet",
                    schema,
                    compression=codec,
                    use_dictionary=False,
                    write_statistics=True,
                    version="2.6",
                )
                self.writers[table_name] = parquet_writer
            parquet_writer.write_table(arrow_table, row_group_size=len(rows))
            rows.clear()

    def close(self, exit_status: str = "success") -> None:
        """Flush, ensure all table files exist, close footers, and finalize manifest."""

        self.flush()
        codec = None if self.config.logging.compression == "none" else self.config.logging.compression
        for table_name, schema in self.schemas.items():
            if table_name not in self.writers:
                empty = pa.Table.from_pylist([], schema=schema)
                pq.write_table(
                    empty,
                    self.run_dir / f"{table_name}.parquet",
                    compression=codec,
                    use_dictionary=False,
                    write_statistics=True,
                    version="2.6",
                )
        for writer in self.writers.values():
            writer.close()
        self.writers.clear()
        elapsed = time.perf_counter() - self.started_clock
        self._write_manifest(exit_status=exit_status, wall_time_seconds=elapsed)

    def _base_manifest(self) -> dict[str, object]:
        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            commit = None
        versions: dict[str, str] = {}
        for package in ("numpy", "pandas", "pyarrow", "tomli-w"):
            try:
                versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                versions[package] = "unavailable"
        return {
            "config_hash": self.config_hash,
            "seed": self.config.run.seed,
            "stage": self.config.run.stage,
            "git_commit": commit,
            "python": platform.python_version(),
            "packages": versions,
            "hostname": socket.gethostname(),
            "started_at_utc": self.started_at.isoformat(),
        }

    def _write_manifest(self, *, exit_status: str, wall_time_seconds: float) -> None:
        manifest = dict(self._manifest)
        manifest["exit_status"] = exit_status
        manifest["wall_time_seconds"] = wall_time_seconds
        if exit_status != "running":
            manifest["finished_at_utc"] = datetime.now(UTC).isoformat()
        (self.run_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
