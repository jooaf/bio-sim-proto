"""Load a complete run directory into typed pandas tables."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from soup.config import Config


TABLE_NAMES = ("ticks", "interactions", "tapes", "lineage", "population", "events")


@dataclass(frozen=True, slots=True)
class RunData:
    run_dir: Path
    config: Config
    manifest: dict[str, Any]
    tables: dict[str, pd.DataFrame]

    def table(self, name: str) -> pd.DataFrame:
        """Return one required raw table."""

        try:
            return self.tables[name]
        except KeyError as error:
            raise KeyError(f"run has no table {name!r}") from error


def load_run(run_dir: str | Path) -> RunData:
    """Load config, manifest, and every Stage 0 Parquet table without intervention."""

    path = Path(run_dir)
    if not path.is_dir():
        raise FileNotFoundError(f"run directory does not exist: {path}")
    config = Config.load(path / "config.toml")
    manifest_raw = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest_raw, dict):
        raise ValueError("manifest.json must contain an object")
    tables: dict[str, pd.DataFrame] = {}
    for name in TABLE_NAMES:
        parquet_path = path / f"{name}.parquet"
        if not parquet_path.exists():
            raise FileNotFoundError(f"missing required table: {parquet_path}")
        tables[name] = pd.read_parquet(parquet_path)
    return RunData(path, config, manifest_raw, tables)
