from __future__ import annotations

import json

from organism_sim.native_report import print_native_report
from organism_sim.report import _resolve_recording, latest_recording


def _write_json(path, value) -> None:
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def test_native_report_surfaces_growth_bottlenecks_and_config_provenance(
    tmp_path, capsys
) -> None:
    run_dir = tmp_path / "native-run"
    run_dir.mkdir()
    manifest = {
        "schema_version": 2,
        "run_id": "native-run",
        "source": "gui",
        "recording_format": "native-gui-jsonl",
        "metrics": "metrics.jsonl",
        "config_events": "config_events.jsonl",
        "season_events": "season_events.jsonl",
        "audit": "audit.json",
    }
    _write_json(run_dir / "manifest.json", manifest)
    rows = [
        {
            "tick": 0,
            "population": 10,
            "living_species": 2,
            "dominant_species_population": 5,
            "dominant_species_share": 0.5,
            "actual_ticks_per_second": 100.0,
            "generated_chunks": 4,
            "deposit_positions": 100,
            "births": 0,
            "deaths": 0,
        },
        {
            "tick": 800,
            "population": 20,
            "living_species": 1,
            "dominant_species_population": 20,
            "dominant_species_share": 1.0,
            "actual_ticks_per_second": 40.0,
            "generated_chunks": 8,
            "deposit_positions": 200,
            "births": 15,
            "deaths": 5,
            "reproduction_attempts": 100,
            "successful_reproductions": 15,
            "reproduction_probability_failures": 70,
            "reproduction_resource_blocks": 15,
        },
        {
            "tick": 1000,
            "population": 30,
            "living_species": 1,
            "dominant_species_population": 30,
            "dominant_species_share": 1.0,
            "actual_ticks_per_second": 30.0,
            "generated_chunks": 10,
            "deposit_positions": 250,
            "births": 30,
            "deaths": 10,
            "reproduction_attempts": 200,
            "successful_reproductions": 30,
            "reproduction_probability_failures": 140,
            "reproduction_resource_blocks": 30,
        },
    ]
    (run_dir / "metrics.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    _write_json(
        run_dir / "config_events.jsonl",
        {"tick": 400, "revision": 1, "changes": {"mutation_multiplier": 2.0}},
    )
    _write_json(
        run_dir / "season_events.jsonl",
        {
            "enabled": True,
            "target": {
                "resource_charge_multiplier": 0.7,
                "decomposition_multiplier": 1.2,
            },
        },
    )
    _write_json(
        run_dir / "audit.json",
        {
            "elements_ok": True,
            "energy_ok": True,
            "energy_error": 1e-9,
            "initial_energy": 0.5,
            "generated_energy": 0.5,
        },
    )

    print_native_report(run_dir / "manifest.json")

    output = capsys.readouterr().out
    assert "final_population=30" in output
    assert "probability=140 (70.0%)" in output
    assert "dominant_species_share=1.0000" in output
    assert "population_per_generated_chunk=3.00" in output
    assert "relative_error=1.000e-09" in output
    assert "tick=400 revision=1 mutation_multiplier=2.0" in output
    assert "random environment seasons" in output
    assert "resource_multiplier=[0.700,0.700]" in output
    assert "founder diversity collapsed" in output


def test_native_report_uses_first_zero_population_as_extinction_tick(
    tmp_path, capsys
) -> None:
    run_dir = tmp_path / "extinct-run"
    run_dir.mkdir()
    _write_json(
        run_dir / "manifest.json",
        {"run_id": "extinct-run", "metrics": "metrics.jsonl"},
    )
    rows = [
        {"tick": 0, "population": 10, "living_species": 2},
        {"tick": 50, "population": 12, "living_species": 2},
        {"tick": 100, "population": 0, "living_species": 0},
        {"tick": 150, "population": 0, "living_species": 0},
    ]
    (run_dir / "metrics.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )

    print_native_report(run_dir / "manifest.json")

    output = capsys.readouterr().out
    assert "peak_population=12 peak_tick=50" in output
    assert "extinction_tick=100" in output


def test_latest_recording_and_directory_resolution(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest = run_dir / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")

    assert latest_recording(tmp_path) == manifest
    assert _resolve_recording(run_dir) == manifest

    database = run_dir / "run.sqlite"
    database.touch()
    assert _resolve_recording(run_dir) == database
    assert _resolve_recording(manifest) == database
