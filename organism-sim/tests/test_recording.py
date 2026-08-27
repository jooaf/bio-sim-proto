import json
import sqlite3
from pathlib import Path

from organism_sim import Simulation, SimulationConfig
from organism_sim.recording import SCHEMA_VERSION, RunRecorder


def test_run_recorder_captures_analysis_state(tmp_path: Path) -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=97,
            width=16,
            height=16,
            founder_count=5,
            element_count=4,
            molecule_count=12,
            initial_deposits=30,
            audit_every=0,
            recording_metrics_interval=1,
            recording_detail_interval=1,
            recording_snapshot_interval=20,
            recording_commit_interval=2,
        )
    )
    recorder = RunRecorder(simulation, source="test", runs_root=tmp_path)
    for _ in range(3):
        simulation.step()
        recorder.record_tick(simulation)
    recorder.record_config(simulation.tick, simulation.config, reason="test_change")
    recorder.close(simulation)

    manifest = json.loads((recorder.run_dir / "manifest.json").read_text())
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["final_tick"] == 3
    assert manifest["source"] == "test"

    with sqlite3.connect(recorder.database_path) as database:
        assert database.execute("SELECT COUNT(*) FROM tick_metrics").fetchone()[0] == 4
        tick_columns = {
            row[1] for row in database.execute("PRAGMA table_info(tick_metrics)").fetchall()
        }
        assert {
            "reproduction_attempts",
            "reproduction_resource_blocks",
            "reproduction_mate_readiness_blocks",
            "reproduction_energy_blocks",
            "reproduction_body_matter_blocks",
            "reproduction_probability_failures",
            "reproduction_placement_failures",
        } <= tick_columns
        assert database.execute("SELECT MIN(tick), MAX(tick) FROM tick_metrics").fetchone() == (0, 3)
        assert database.execute("SELECT COUNT(*) FROM elements").fetchone()[0] == 4
        assert database.execute("SELECT COUNT(*) FROM molecules").fetchone()[0] == 12
        assert database.execute("SELECT COUNT(*) FROM organisms").fetchone()[0] >= 5
        assert database.execute("SELECT COUNT(*) FROM genomes").fetchone()[0] >= 5
        assert database.execute("SELECT COUNT(*) FROM detail_ticks").fetchone()[0] == 4
        assert database.execute("SELECT COUNT(*) FROM organism_states").fetchone()[0] >= 20
        assert database.execute("SELECT COUNT(*) FROM organism_inventories").fetchone()[0] > 0
        assert database.execute("SELECT COUNT(*) FROM molecule_states").fetchone()[0] == 4 * 12
        assert database.execute("SELECT COUNT(*) FROM element_states").fetchone()[0] == 4 * 4
        assert database.execute("SELECT COUNT(*) FROM species_states").fetchone()[0] > 0
        assert database.execute("SELECT DISTINCT origin FROM species_states").fetchall() == [("founder",)]
        species_columns = {
            row[1] for row in database.execute("PRAGMA table_info(species_states)").fetchall()
        }
        assert {"origin", "created_tick", "parent_species_ids_json", "founder_organism_id"} <= species_columns
        assert database.execute("SELECT COUNT(*) FROM world_snapshots").fetchone()[0] == 2
        assert database.execute("SELECT COUNT(*) FROM config_events").fetchone()[0] == 2
        tables = {
            row[0]
            for row in database.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert {
            "sexual_parents",
            "corpse_states",
            "magic_effect_states",
            "colony_states",
            "alliances",
            "alliance_states",
        } <= tables
        assert database.execute("SELECT COUNT(*) FROM events WHERE event_type='founder'").fetchone()[0] >= 5
        max_error = database.execute("SELECT MAX(ABS(energy_error)) FROM tick_metrics").fetchone()[0]
        assert max_error < 1e-7


def test_default_recording_keeps_every_metric_and_samples_large_state(tmp_path: Path) -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=107,
            width=16,
            height=16,
            founder_count=4,
            founder_archetype_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            audit_every=0,
        )
    )
    recorder = RunRecorder(simulation, source="test", runs_root=tmp_path)
    for _ in range(7):
        simulation.step()
        recorder.record_tick(simulation)
    recorder.close(simulation)

    with sqlite3.connect(recorder.database_path) as database:
        assert database.execute("SELECT tick FROM tick_metrics ORDER BY tick").fetchall() == [
            (0,),
            (5,),
            (7,),
        ]
        assert database.execute("SELECT tick FROM detail_ticks ORDER BY tick").fetchall() == [
            (0,),
            (7,),
        ]
        assert database.execute("SELECT tick FROM world_snapshots ORDER BY tick").fetchall() == [
            (0,),
            (7,),
        ]


def test_reset_recording_is_a_distinct_linked_run(tmp_path: Path) -> None:
    config = SimulationConfig(
        seed=113,
        width=16,
        height=16,
        founder_count=4,
        founder_archetype_count=2,
        element_count=4,
        molecule_count=12,
        initial_deposits=20,
        audit_every=0,
    )
    first_simulation = Simulation(config)
    first_recorder = RunRecorder(first_simulation, source="gui", runs_root=tmp_path)
    first_simulation.step()
    first_recorder.record_tick(first_simulation)

    reset_simulation = Simulation(config)
    reset_recorder = RunRecorder(
        reset_simulation,
        source="gui_reset",
        runs_root=tmp_path,
        previous_run_id=first_recorder.run_id,
    )
    first_recorder.close(first_simulation)
    reset_recorder.close(reset_simulation)

    run_directories = sorted(path for path in tmp_path.iterdir() if path.is_dir())
    assert len(run_directories) == 2
    first_manifest = json.loads((first_recorder.run_dir / "manifest.json").read_text())
    reset_manifest = json.loads((reset_recorder.run_dir / "manifest.json").read_text())
    assert first_manifest["final_tick"] == 1
    assert reset_manifest["source"] == "gui_reset"
    assert reset_manifest["previous_run_id"] == first_recorder.run_id
    assert reset_manifest["final_tick"] == 0
    with sqlite3.connect(reset_recorder.database_path) as database:
        previous = database.execute(
            "SELECT value_json FROM run_metadata WHERE key='previous_run_id'"
        ).fetchone()[0]
        assert json.loads(previous) == first_recorder.run_id
        assert database.execute("SELECT COUNT(*) FROM tick_metrics").fetchone()[0] == 1


def test_alliances_are_recorded_once_instead_of_repeated_in_snapshots(tmp_path: Path) -> None:
    simulation = Simulation(
        SimulationConfig(
            seed=127,
            width=16,
            height=16,
            founder_count=4,
            founder_archetype_count=2,
            element_count=4,
            molecule_count=12,
            initial_deposits=20,
            audit_every=0,
            recording_detail_interval=1,
        )
    )
    recorder = RunRecorder(simulation, source="test", runs_root=tmp_path)
    left_id, right_id = sorted(simulation.living_ids)[:2]
    simulation.alliances.add(frozenset((left_id, right_id)))
    simulation.alliance_events.append((simulation.tick, left_id, right_id))
    for _ in range(3):
        simulation.step()
        recorder.record_tick(simulation)
    recorder.close(simulation)

    with sqlite3.connect(recorder.database_path) as database:
        assert database.execute("SELECT COUNT(*) FROM alliances").fetchone()[0] == 1
        assert database.execute("SELECT COUNT(*) FROM alliance_states").fetchone()[0] == 0
        assert database.execute(
            "SELECT COUNT(*) FROM events WHERE event_type='alliance_created'"
        ).fetchone()[0] == 1
