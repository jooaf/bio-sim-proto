from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pytest

from experiments.stringmol.analyze_lineage import EVENT_COLUMNS, SNAPSHOT_COLUMNS, analyze_run, integer, sequence
from experiments.stringmol.configure_control import HOST, StringmolControlConfig, render_config
from experiments.stringmol.lineage_workflow import ENV, LOGS, execute, expected_initial, inventory, parity, record, seal


def write_csv(path: Path, columns: list[str], data: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)


def fixture_run(path: Path, end_tick: int = 5000, end_population: int = 142, births: bool = True) -> None:
    path.mkdir(exist_ok=True)
    initial = expected_initial("host")
    events: list[dict[str, Any]] = []
    for item in initial:
        row: dict[str, Any] = dict.fromkeys(EVENT_COLUMNS, -1)
        row.update(event="INIT", timestep=0, x=item["x"], y=item["y"], active_sequence_hex="", passive_sequence_hex="")
        row.update({"child_" + k: item[k] for k in ("id", "species", "label", "sequence_hex")})
        events.append(row)
    if births:
        for idx, active, passive, tick in ((142, 0, 1, 1), (145, 142, 0, 101)):
            row = dict.fromkeys(EVENT_COLUMNS, -1)
            row.update(event="BIRTH", timestep=tick, child_id=idx, active_id=active, passive_id=passive, child_species=1, active_species=1, passive_species=1, child_label=81, active_label=81, passive_label=81, x=idx - 142, y=0, child_sequence_hex=HOST.encode().hex().upper(), active_sequence_hex="42", passive_sequence_hex=HOST.encode().hex().upper())
            events.append(row)
    row = dict.fromkeys(EVENT_COLUMNS, -1)
    row.update(event="END", timestep=end_tick, population=end_population, child_sequence_hex="", active_sequence_hex="", passive_sequence_hex="")
    events.append(row)
    write_csv(path / "lineage_events001.csv", EVENT_COLUMNS, events)
    snapshots: list[dict[str, Any]] = []
    populations = []
    for tick in range(0, end_tick, 100):
        items = initial.copy()
        if births:
            for idx, born in ((142, 1), (145, 101)):
                if tick > born:
                    items.append({**initial[0], "id": idx, "x": idx - 142, "y": 0})
        snapshots.extend({"tick": tick, **item} for item in items)
        populations.append(f"{tick},1,{len(items)}\n")
    write_csv(path / "lineage_snapshots001.csv", SNAPSHOT_COLUMNS, snapshots)
    (path / "popdy001.dat").write_text("".join(populations))
    (path / "stdout.txt").write_text("FINISHED smspatial\n")
    (path / "stderr.txt").write_text("")


def edit_csv(path: Path, columns: list[str], index: int, key: str, value: str) -> None:
    with path.open(newline="") as f:
        data: list[dict[str, Any]] = list(csv.DictReader(f))
    data[index][key] = value
    write_csv(path, columns, data)


def test_inert_changes_only_sequence_and_label(tmp_path: Path) -> None:
    host = render_config(StringmolControlConfig("host-only", 202620000, 0, 0), tmp_path / "ALXII.mtx")
    inert = render_config(StringmolControlConfig("inert", 202620000, 0, 0), tmp_path / "ALXII.mtx")
    assert host.replace(f"AGENT {HOST} 1 Q", "AGENT B 1 B") == inert
    assert inert.count("AGENT B 1 B") == 140


def test_two_parent_and_passive_depth_are_distinct(tmp_path: Path) -> None:
    fixture_run(tmp_path)
    result = analyze_run(tmp_path, expected_initial("host"))
    assert result["successful_births"] == 2
    assert result["max_two_parent_depth"] == 2
    assert result["max_passive_depth"] == 1
    assert result["final_noninitial_descendants"] == 2
    assert result["passive_sequence_match_fraction"] == 1
    assert result["sequence_comparisons"][0]["child_sha256"] == "94f8c51cef8ef18d4246fb1fc6030b20f887bb0e265be59b3949be2bb69b89c5"


@pytest.mark.parametrize(("tick", "population", "expected_population"), [(4900, 0, 0), (4901, 0, 142), (5000, 0, 142), (5000, 142, 142)])
def test_endpoint_extinction_rules(tmp_path: Path, tick: int, population: int, expected_population: int) -> None:
    fixture_run(tmp_path, tick, population)
    result = analyze_run(tmp_path, expected_initial("host"))
    assert result["final_population"] == expected_population
    assert result["final_noninitial_descendants"] == (2 if expected_population else 0)
    assert result["final_descendant_fraction"] == (2 / 142 if expected_population else 0)


def test_zero_birth_match_fraction_null(tmp_path: Path) -> None:
    fixture_run(tmp_path, 1, 0, births=False)
    result = analyze_run(tmp_path, expected_initial("host"))
    assert result["passive_sequence_match_fraction"] is None
    assert result["max_two_parent_depth"] == 0


@pytest.mark.parametrize(("index", "key", "value"), [
    (140, "child_id", "0"), (140, "child_id", "-1"), (140, "child_id", "2147483648"),
    (141, "child_id", "141"), (140, "active_id", "141"), (140, "active_id", "142"),
    (140, "child_label", "66"), (140, "child_species", "-1"), (140, "x", "40"),
    (140, "child_sequence_hex", "ff"), (140, "active_sequence_hex", "0"),
    (140, "population", "1"), (140, "event", "DEATH"), (141, "timestep", "0"),
    (0, "active_id", "0"), (0, "child_sequence_hex", "42"), (0, "event", "END"),
    (-1, "child_id", "0"), (-1, "child_sequence_hex", "42"), (-1, "population", "-1"),
    (-1, "timestep", "4999"), (-1, "event", "INIT"),
])
def test_bad_event_fails_integrity(tmp_path: Path, index: int, key: str, value: str) -> None:
    fixture_run(tmp_path)
    edit_csv(tmp_path / "lineage_events001.csv", EVENT_COLUMNS, index, key, value)
    with pytest.raises(ValueError):
        analyze_run(tmp_path, expected_initial("host"))


@pytest.mark.parametrize(("index", "key", "value"), [(0, "id", "142"), (1, "id", "0"), (1, "x", "12"), (140, "tick", "1"), (-1, "id", "999"), (-1, "species", "2"), (-1, "y", "-1")])
def test_bad_snapshot_fails_integrity(tmp_path: Path, index: int, key: str, value: str) -> None:
    fixture_run(tmp_path)
    edit_csv(tmp_path / "lineage_snapshots001.csv", SNAPSHOT_COLUMNS, index, key, value)
    with pytest.raises(ValueError):
        analyze_run(tmp_path, expected_initial("host"))


def test_missing_endpoint_not_fabricated(tmp_path: Path) -> None:
    fixture_run(tmp_path)
    p = tmp_path / "lineage_snapshots001.csv"
    p.write_text("\n".join(line for line in p.read_text().splitlines() if not line.startswith("4900,")) + "\n")
    with pytest.raises(ValueError, match="checkpoint"):
        analyze_run(tmp_path, expected_initial("host"))


@pytest.mark.parametrize("warning", ["Number of agents not specified", "reproducible method", "repclicable method", "loader fallback"])
def test_loader_warning_rejected(tmp_path: Path, warning: str) -> None:
    fixture_run(tmp_path)
    (tmp_path / "stderr.txt").write_text(warning)
    with pytest.raises(ValueError, match="loader"):
        analyze_run(tmp_path, expected_initial("host"))


def test_process_failure_is_integrity_failure(tmp_path: Path) -> None:
    fixture_run(tmp_path)
    with pytest.raises(ValueError, match="exit"):
        analyze_run(tmp_path, expected_initial("host"), exit_status=1)


def test_population_species_checked(tmp_path: Path) -> None:
    fixture_run(tmp_path)
    p = tmp_path / "popdy001.dat"
    p.write_text(p.read_text().replace("100,1,141", "100,2,141"))
    with pytest.raises(ValueError, match="species mismatch"):
        analyze_run(tmp_path, expected_initial("host"))


def test_exact_file_set_and_bytes_parity() -> None:
    base: dict[str, Any] = {"exit_status": 0, "files": {"popdy001.dat": {"size": 3, "sha256": "a"}}}
    parity(base, base, False)
    enabled = {"exit_status": 0, "files": {**base["files"], **dict.fromkeys(LOGS, {})}}
    parity(base, enabled, True)
    for bad in (
        {"exit_status": 1, "files": base["files"]},
        {"exit_status": 0, "files": {}},
        {"exit_status": 0, "files": {**base["files"], "extra": {}}},
        {"exit_status": 0, "files": {"popdy001.dat": {"size": 3, "sha256": "b"}}},
    ):
        with pytest.raises(ValueError):
            parity(base, bad, False)
    with pytest.raises(ValueError):
        parity(base, base, True)


def test_output_inventory_is_complete_and_rejects_symlinks(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested/raw").write_bytes(b"\0\xff")
    assert inventory(tmp_path) == {"nested/raw": record(tmp_path / "nested/raw")}
    (tmp_path / "link").symlink_to(tmp_path / "nested/raw")
    with pytest.raises(ValueError, match="nonregular"):
        inventory(tmp_path)


def test_execute_rejects_existing_directory_before_launch(tmp_path: Path) -> None:
    with pytest.raises(FileExistsError):
        execute(Path("/nonexistent"), Path("/config"), tmp_path, True)


def test_execute_sanitizes_environment_and_preserves_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRINGMOL_LINEAGE_LOG", "1")
    monkeypatch.setenv("UNWANTED", "secret")
    binary = tmp_path / "fake"
    binary.write_text('#!/bin/sh\n/usr/bin/env\necho failure >&2\nexit 7\n')
    binary.chmod(0o755)
    result = execute(binary, tmp_path / "config", tmp_path / "out", False)
    output = (tmp_path / "out/stdout.txt").read_text()
    assert "UNWANTED" not in output and "STRINGMOL_LINEAGE_LOG" not in output
    assert f"LC_ALL={ENV['LC_ALL']}" in output
    assert result["exit_status"] == 7
    assert set(result["files"]) == {"stdout.txt", "stderr.txt"}


def test_seal_is_exclusive_and_readonly(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    seal(path, {"input": "frozen"})
    assert path.stat().st_mode & 0o222 == 0
    with pytest.raises(FileExistsError):
        seal(path, {"input": "new"})


@pytest.mark.parametrize("value", ["00", "+1", " 1", "-0", "2147483648", "-1"])
def test_identity_lossless_parsing(value: str) -> None:
    with pytest.raises(ValueError):
        integer(value)


def test_raw_sequence_bytes_roundtrip() -> None:
    assert sequence("FF2C0A22") == b'\xff,\n"'
    with pytest.raises(ValueError):
        sequence("410042")


def mock_preparation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from experiments.stringmol import lineage_workflow as workflow
    build_file = tmp_path / "build.json"
    gate_file = tmp_path / "isolation.json"
    seal(build_file, {})
    seal(gate_file, {})
    data = {"builds": {"observer": {"source": str(tmp_path / "source")}}}
    monkeypatch.setattr(workflow, "verify_build", lambda _: data)
    monkeypatch.setattr(workflow, "verify_gate", lambda *_: None)
    monkeypatch.setattr(workflow, "source_state", lambda _: {"commit": "test"})
    return workflow.prepare(build_file, gate_file, tmp_path / "prepared")


def test_preparation_is_frozen_without_running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from experiments.stringmol import lineage_workflow as workflow
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("preparation launched a simulator")
    monkeypatch.setattr(workflow, "execute", forbidden)
    manifest = mock_preparation(tmp_path, monkeypatch)
    data = workflow.verify_preparation(manifest)
    assert len(data["runs"]) == 20
    assert len(list(manifest.parent.glob("*.conf"))) == 20
    assert not (manifest.parent / "runs").exists()
    assert data["workers"] == 6
    assert data["environment"]["STRINGMOL_LINEAGE_LOG"] == "1"
    config = Path(data["runs"][0]["config"])
    config.chmod(0o644)
    config.write_text(config.read_text() + "NSTEPS 1\n")
    with pytest.raises(ValueError, match="config"):
        workflow.verify_preparation(manifest)


def test_manifest_tampering_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from experiments.stringmol import lineage_workflow as workflow
    manifest = mock_preparation(tmp_path, monkeypatch)
    manifest.chmod(0o644)
    manifest.write_text(manifest.read_text().replace('"workers": 6', '"workers": 7'))
    manifest.chmod(0o444)
    with pytest.raises(ValueError, match="immutable"):
        workflow.verify_preparation(manifest)


def test_six_workers_preserve_failed_runs_and_inventory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import threading
    from experiments.stringmol import lineage_workflow as workflow
    manifest = mock_preparation(tmp_path, monkeypatch)
    lock = threading.Lock()
    six_started = threading.Event()
    active = maximum = calls = 0

    def fake_execute(binary: Path, config: Path, directory: Path, enabled: bool) -> dict[str, Any]:
        nonlocal active, maximum, calls
        assert enabled
        with lock:
            active += 1
            calls += 1
            maximum = max(maximum, active)
            if active == 6:
                six_started.set()
        assert six_started.wait(10)
        directory.mkdir(parents=True, exist_ok=False)
        (directory / "stdout.txt").write_text("failed synthetic process")
        result = {"exit_status": 1, "files": inventory(directory)}
        with lock:
            active -= 1
        return result

    monkeypatch.setattr(workflow, "execute", fake_execute)
    workflow.run_matrix(manifest)
    assert maximum == 6 and calls == 20
    results = workflow.read(manifest.parent / "campaign-results.json")
    assert len(results) == 20 and all(r["exit_status"] == 1 for r in results)
    for run in workflow.read(manifest)["runs"]:
        directory = Path(run["directory"])
        receipt = workflow.read(directory.with_suffix(".inventory.json"))
        assert receipt["files"] == inventory(directory)
        assert receipt["input_manifest"] == record(manifest)
    with pytest.raises(FileExistsError):
        workflow.run_matrix(manifest)
    assert calls == 20


def test_preexisting_campaign_directory_blocks_every_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from experiments.stringmol import lineage_workflow as workflow
    manifest = mock_preparation(tmp_path, monkeypatch)
    (manifest.parent / "runs").mkdir()
    with pytest.raises(FileExistsError):
        workflow.run_matrix(manifest)
    assert not (manifest.parent / "campaign.json").exists()


def test_malformed_observation_makes_campaign_unevaluable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from experiments.stringmol import analyze_lineage, lineage_workflow as workflow
    manifest = mock_preparation(tmp_path, monkeypatch)
    data = workflow.read(manifest)
    receipts = []
    for r in data["runs"]:
        directory = Path(r["directory"])
        directory.mkdir(parents=True)
        (directory / "stdout.txt").write_text("FINISHED smspatial\n")
        (directory / "stderr.txt").write_text("")
        (directory / "lineage_events001.csv").write_text(",".join(EVENT_COLUMNS) + '\n"unterminated')
        receipt = {"exit_status": 0, "files": inventory(directory), "input_manifest": record(manifest), "condition": r["condition"], "seed": r["seed"]}
        workflow.seal(directory.with_suffix(".inventory.json"), receipt)
        receipts.append(receipt)
    workflow.seal(manifest.parent / "campaign.json", {"input_manifest": record(manifest), "workers": 6})
    workflow.seal(manifest.parent / "campaign-results.json", receipts)
    result = analyze_lineage.analyze_campaign(manifest)
    assert result["decision"] == "unevaluable"
    assert result["denominator"] == len(result["failures"]) == 20


@pytest.mark.parametrize(("index", "role"), [(140, "active"), (140, "passive"), (141, "active"), (141, "passive")])
def test_event_labels_bound_to_introduction(tmp_path: Path, index: int, role: str) -> None:
    fixture_run(tmp_path)
    path = tmp_path / "lineage_events001.csv"
    edit_csv(path, EVENT_COLUMNS, index, role + "_label", "66")
    if role == "passive":
        # A forged parent/child pair must not evade the immutable identity check.
        edit_csv(path, EVENT_COLUMNS, index, "child_label", "66")
    with pytest.raises(ValueError, match="parent label differs from introduction"):
        analyze_run(tmp_path, expected_initial("host"))


@pytest.mark.parametrize("index", [140, -1])
def test_snapshot_labels_bound_to_initial_and_birth_introductions(tmp_path: Path, index: int) -> None:
    fixture_run(tmp_path)
    edit_csv(tmp_path / "lineage_snapshots001.csv", SNAPSHOT_COLUMNS, index, "label", "66")
    with pytest.raises(ValueError, match="snapshot label differs from introduction"):
        analyze_run(tmp_path, expected_initial("host"))


def test_end_cannot_exceed_introduced_identities(tmp_path: Path) -> None:
    fixture_run(tmp_path, end_population=143)
    with pytest.raises(ValueError, match="total introduced identities"):
        analyze_run(tmp_path, expected_initial("host"))


@pytest.mark.parametrize(("birth_tick", "end_population", "valid"), [(101, 142, False), (4900, 142, True), (4901, 142, True), (4901, 141, True)])
def test_end_bound_from_last_snapshot(tmp_path: Path, birth_tick: int, end_population: int, valid: bool) -> None:
    fixture_run(tmp_path, end_population=end_population)
    edit_csv(tmp_path / "lineage_events001.csv", EVENT_COLUMNS, 141, "timestep", str(birth_tick))
    path = tmp_path / "lineage_snapshots001.csv"
    with path.open(newline="") as f:
        data: list[dict[str, Any]] = list(csv.DictReader(f))
    # The last introduced identity is absent at 4900; for late births it is
    # absent from all preceding snapshots too. Keep population evidence exact.
    data = [r for r in data if not (r["id"] == "145" and (birth_tick >= 4900 or r["tick"] == "4900"))]
    write_csv(path, SNAPSHOT_COLUMNS, data)
    from collections import Counter
    totals = Counter(int(r["tick"]) for r in data)
    (tmp_path / "popdy001.dat").write_text("".join(f"{tick},1,{count}\n" for tick, count in sorted(totals.items())))
    if valid:
        result = analyze_run(tmp_path, expected_initial("host"))
        assert result["final_population"] == 141
        assert result["end_population"] == end_population
    else:
        with pytest.raises(ValueError, match="last snapshot plus subsequent births"):
            analyze_run(tmp_path, expected_initial("host"))


@pytest.mark.parametrize("field", ["revision", "sha256", "bytes_hex"])
def test_preparation_protocol_pin_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    import json
    from experiments.stringmol import lineage_workflow as workflow
    manifest = mock_preparation(tmp_path, monkeypatch)
    data = workflow.read(manifest)
    data["protocol_pin"][field] = "bad pin"
    manifest.chmod(0o644)
    manifest.write_text(json.dumps(data))
    manifest.chmod(0o444)
    receipt = manifest.with_name("preparation.sha256.json")
    receipt.chmod(0o644)
    receipt.write_text(json.dumps(record(manifest)))
    receipt.chmod(0o444)
    with pytest.raises(ValueError, match="prepared protocol pin mismatch"):
        workflow.verify_preparation(manifest)


@pytest.mark.parametrize("change_committed", [False, True])
def test_protocol_checks_committed_and_working_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change_committed: bool) -> None:
    from experiments.stringmol import lineage_workflow as workflow
    manifest = mock_preparation(tmp_path, monkeypatch)
    pin = workflow.protocol_pin()
    committed = bytes.fromhex(pin["bytes_hex"])
    protocol = tmp_path / workflow.PROTOCOL_PATH
    protocol.parent.mkdir()
    protocol.write_bytes(committed if change_committed else committed + b"\nchanged\n")
    monkeypatch.setattr(workflow, "ROOT", tmp_path)
    monkeypatch.setattr(workflow, "command", lambda *_: committed + b"changed" if change_committed else committed)
    with pytest.raises(ValueError, match="protocol"):
        workflow.verify_preparation(manifest)
