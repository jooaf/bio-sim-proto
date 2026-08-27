from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import SimulationConfig
from .gui_backend import WorkerStatus
from .rust_kernel import config_sha256, rust_build_metadata, scheduler_metadata


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _metric_value(value: Any) -> int | float | list[int | float]:
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_metric_scalar(item) for item in value]
    raise TypeError(f"unsupported native metric value: {type(value).__name__}")


def _metric_scalar(value: Any) -> int | float:
    if isinstance(value, int):
        return int(value)
    return float(value)


class NativeGuiRecorder:
    """Low-frequency JSONL recorder that never enters the simulation hot path."""

    def __init__(
        self,
        config: SimulationConfig,
        *,
        runs_root: Path | None = None,
        previous_run_id: str | None = None,
    ) -> None:
        root = runs_root or Path(__file__).resolve().parents[2] / "runs"
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        self.run_id = f"{timestamp}-seed{config.seed}-rust-gui-{uuid4().hex[:8]}"
        self.run_dir = root / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=False)
        self._manifest_path = self.run_dir / "manifest.json"
        self._metrics_file = (self.run_dir / "metrics.jsonl").open(
            "w", encoding="utf-8", buffering=1
        )
        self._config_events_file = (self.run_dir / "config_events.jsonl").open(
            "w", encoding="utf-8", buffering=1
        )
        self._season_events_file = (self.run_dir / "season_events.jsonl").open(
            "w", encoding="utf-8", buffering=1
        )
        self._last_tick = -1
        self._config_revision = 0
        self._closed = False
        self._manifest: dict[str, Any] = {
            "schema_version": 4,
            "run_id": self.run_id,
            "previous_run_id": previous_run_id,
            "kernel": "rust",
            "source": "gui",
            "recording_format": "native-gui-jsonl",
            "seed": config.seed,
            "started_utc": datetime.now(UTC).isoformat(),
            "build": rust_build_metadata(),
            "execution": scheduler_metadata(config),
            "config": asdict(config),
            "config_sha256": config_sha256(config),
            "metrics": "metrics.jsonl",
            "config_events": "config_events.jsonl",
            "season_events": "season_events.jsonl",
            "audit": "audit.json",
        }
        self._write_manifest()

    def _write_manifest(self) -> None:
        self._manifest_path.write_text(_json(self._manifest) + "\n", encoding="utf-8")

    def record(self, snapshot: dict[str, Any], actual_ticks_per_second: float) -> None:
        tick = int(snapshot["tick"])
        if self._closed or tick == self._last_tick:
            return
        stats = snapshot["stats"]
        species_populations = [
            int(population)
            for population in snapshot["species"]["population"]
            if int(population) > 0
        ]
        population = int(snapshot["population"])
        dominant_species_population = max(species_populations, default=0)
        season = snapshot.get("season")
        row = {
            "tick": tick,
            "population": population,
            "living_species": len(species_populations),
            "dominant_species_population": dominant_species_population,
            "dominant_species_share": (
                dominant_species_population / population if population else 0.0
            ),
            "actual_ticks_per_second": actual_ticks_per_second,
            **{name: _metric_value(value) for name, value in stats.items()},
        }
        self._metrics_file.write(_json(row) + "\n")
        if season is not None:
            events = season["events"]
            for event in events:
                self._season_events_file.write(
                    _json({"enabled": bool(season["enabled"]), **event}) + "\n"
                )
        self._last_tick = tick

    def record_config_update(self, tick: int, changes: dict[str, object]) -> None:
        """Record a kernel-applied live update at its authoritative tick."""

        if self._closed or not changes:
            return
        self._config_revision += 1
        self._config_events_file.write(
            _json(
                {
                    "tick": int(tick),
                    "revision": self._config_revision,
                    "changes": changes,
                }
            )
            + "\n"
        )

    def close(self, status: WorkerStatus) -> None:
        if self._closed:
            return
        self._closed = True
        self._metrics_file.close()
        self._config_events_file.close()
        self._season_events_file.close()
        audit = status.final_audit or {}
        (self.run_dir / "audit.json").write_text(
            json.dumps(audit, indent=2), encoding="utf-8"
        )
        self._manifest.update(
            {
                "ended_utc": datetime.now(UTC).isoformat(),
                "final_tick": status.tick,
                "average_ticks_per_second": status.ticks_per_second,
                "error": status.error or None,
                "elements_ok": audit.get("elements_ok"),
                "energy_ok": audit.get("energy_ok"),
            }
        )
        self._write_manifest()


__all__ = ["NativeGuiRecorder"]
