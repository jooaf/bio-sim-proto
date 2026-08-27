from __future__ import annotations

import json

from organism_sim.config import SimulationConfig
from organism_sim.gui_backend import WorkerStatus
from organism_sim.native_recording import NativeGuiRecorder


def test_native_gui_recorder_writes_compact_metrics_and_audit(tmp_path) -> None:
    recorder = NativeGuiRecorder(
        SimulationConfig(founder_count=10),
        runs_root=tmp_path,
    )
    snapshot = {
        "tick": 5,
        "population": 9,
        "species": {"population": [5, 4, 0]},
        "stats": {
            "births": 1,
            "deaths": 2,
            "audit_error": 1e-12,
            "v2_intent_counts": [0, 3, 1],
        },
        "season": {
            "enabled": True,
            "events": [
                {
                    "schema_version": 1,
                    "index": 0,
                    "started_tick": 0,
                    "transition_end_tick": 0,
                    "next_season_tick": 500,
                    "from": {
                        "resource_charge_multiplier": 1.0,
                        "decomposition_multiplier": 1.0,
                        "molecule_charge_affinities": [1.0],
                    },
                    "target": {
                        "resource_charge_multiplier": 0.8,
                        "decomposition_multiplier": 1.2,
                        "molecule_charge_affinities": [0.7],
                    },
                }
            ],
        },
    }
    recorder.record(snapshot, 123.0)
    recorder.record(snapshot, 123.0)
    recorder.record_config_update(5, {"mutation_multiplier": 2.0})
    recorder.close(
        WorkerStatus(
            tick=5,
            ticks_per_second=123.0,
            final_audit={"elements_ok": True, "energy_ok": True},
        )
    )

    rows = (recorder.run_dir / "metrics.jsonl").read_text().splitlines()
    config_events = (recorder.run_dir / "config_events.jsonl").read_text().splitlines()
    season_events = (recorder.run_dir / "season_events.jsonl").read_text().splitlines()
    manifest = json.loads((recorder.run_dir / "manifest.json").read_text())
    audit = json.loads((recorder.run_dir / "audit.json").read_text())
    assert len(rows) == 1
    recorded = json.loads(rows[0])
    assert recorded["living_species"] == 2
    assert recorded["dominant_species_population"] == 5
    assert recorded["dominant_species_share"] == 5 / 9
    assert recorded["v2_intent_counts"] == [0, 3, 1]
    assert json.loads(config_events[0]) == {
        "changes": {"mutation_multiplier": 2.0},
        "revision": 1,
        "tick": 5,
    }
    assert len(season_events) == 1
    assert json.loads(season_events[0])["target"]["resource_charge_multiplier"] == 0.8
    assert manifest["schema_version"] == 4
    assert len(manifest["config_sha256"]) == 64
    assert manifest["build"]["kernel_version"] == "0.1.0"
    assert len(manifest["build"]["kernel_binary_sha256"]) == 64
    assert manifest["execution"]["scheduler"] == "serial-v2"
    assert manifest["execution"]["scheduler_schema_version"] == 2
    assert manifest["config_events"] == "config_events.jsonl"
    assert manifest["season_events"] == "season_events.jsonl"
    assert manifest["final_tick"] == 5
    assert manifest["energy_ok"] is True
    assert audit["elements_ok"] is True
