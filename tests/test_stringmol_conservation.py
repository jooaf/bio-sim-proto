from __future__ import annotations

import csv
from pathlib import Path
import threading
from typing import Any

import pytest

from experiments.stringmol import conservation_workflow as workflow
from experiments.stringmol.analyze_conservation import (
    ALPHABET, BUFFER_COLUMNS, COLUMNS, MAXL0, analyze_run,
    canonical_rows, fields, full_buffer, initial_material, outcomes,
)
from experiments.stringmol.analyze_lineage import EVENT_COLUMNS, SNAPSHOT_COLUMNS
from experiments.stringmol.lineage_workflow import PROTOCOL_SHA256, expected_initial, inventory, read, record, seal


def write(path: Path, columns: list[str], data: list[dict[str, Any]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(data)


def fixture(path: Path, end_tick: int = 500, extinct: bool = False) -> None:
    initial = expected_initial("host")
    events: list[dict[str, Any]] = []
    for item in initial:
        row: dict[str, Any] = dict.fromkeys(EVENT_COLUMNS, -1)
        row.update(event="INIT", timestep=0, x=item["x"], y=item["y"], active_sequence_hex="", passive_sequence_hex="")
        row.update({"child_" + k: item[k] for k in ("id", "species", "label", "sequence_hex")})
        events.append(row)
    row = dict.fromkeys(EVENT_COLUMNS, -1)
    row.update(event="END", timestep=end_tick, population=0 if extinct else 140, child_sequence_hex="", active_sequence_hex="", passive_sequence_hex="")
    events.append(row)
    write(path / "lineage_events001.csv", EVENT_COLUMNS, events)
    write(path / "lineage_snapshots001.csv", SNAPSHOT_COLUMNS, [{"tick": t, **a} for t in range(0, end_tick, 100) for a in initial])
    (path / "popdy001.dat").write_text("".join(f"{t},1,140\n" for t in range(0, end_tick, 100)))
    (path / "stdout.txt").write_text("FINISHED smspatial\n")
    (path / "stderr.txt").write_text("")
    material = initial_material(initial, "histogram", 16)
    aggregate = []
    buffers: list[dict[str, Any]] = []
    for tick, event in [(t, "CHECKPOINT") for t in range(0, end_tick, 100)] + [(end_tick, "END")]:
        dead = extinct and event == "END"
        row = dict.fromkeys(COLUMNS, 0)
        row.update(tick=tick, event=event)
        for s in range(33):
            row[fields("molecular")[s]] = 0 if dead else material["molecular"][s]
            row[fields("pool")[s]] = material["total"][s] if dead else material["pool"][s]
            row[fields("initial")[s]] = material["total"][s]
            row[fields("pool_minimum")[s]] = material["pool"][s]
            row[fields("decay_returns")[s]] = material["molecular"][s] if dead else 0
        row["molecular_bytes"] = 0 if dead else sum(material["molecular"])
        row["free_bytes"] = sum(material["total"] if dead else material["pool"])
        aggregate.append(row)
        if not dead:
            buffers.extend({"tick": tick, "event": event, "id": i, "full_buffer_hex": value} for i, value in material["buffers"].items())
    write(path / "conservation001.csv", COLUMNS, aggregate)
    write(path / "conservation_buffers001.csv", BUFFER_COLUMNS, buffers)


def edit(path: Path, columns: list[str], index: int, key: str, value: Any) -> None:
    data: list[dict[str, Any]] = list(canonical_rows(path, columns))
    data[index][key] = value
    write(path, columns, data)


def test_full_buffer_not_c_string() -> None:
    raw = b"A\0B\0"
    assert full_buffer(raw.hex().upper(), 4) == raw
    with pytest.raises(ValueError, match="terminator"):
        full_buffer("41004243", 4)
    for value in ("41002100", "4100", "4100420a", "4100420A"):
        with pytest.raises(ValueError):
            full_buffer(value, 4)


def test_frozen_initial_inventory() -> None:
    m = initial_material(expected_initial("host"), "histogram", 16)
    assert len(m["buffers"]) == 140 and all(len(v) == 2 * MAXL0 for v in m["buffers"].values())
    assert "".join(s for s, n in zip(ALPHABET, m["total"], strict=True) if n == 0) == "AFIKMNPQSTVZ"
    assert all(p == 16 * n and t == 17 * n for n, p, t in zip(m["molecular"], m["pool"], m["total"], strict=True))
    uniform = initial_material(expected_initial("host"), "uniform", 1000000)
    assert uniform["pool"] == [1000000] * 33


@pytest.mark.parametrize(("tick", "extinct", "final"), [(500, False, 140), (401, True, 140), (400, True, 0), (1, True, 0)])
def test_reconstruction_and_distinct_end(tmp_path: Path, tick: int, extinct: bool, final: int) -> None:
    fixture(tmp_path, tick, extinct)
    result = analyze_run(tmp_path, expected_initial("host"), "histogram", 16, nsteps=500)
    assert result["zero_residual"] and result["final_population"] == final
    assert result["end_conservation"]["population"] == (0 if extinct else 140)


@pytest.mark.parametrize(("key", "value"), [
    ("max_residual", 1), ("boundary_error", 1), ("attempts", 1), ("accepted_positive_growth", 1),
    ("scarcity_blocked", 1), ("molecular_bytes", 1), ("free_bytes", 0), ("pool_42", -1),
    ("pool_minimum_42", 999999), ("initial_42", 1), ("copy_returns_42", 1),
    ("molecular_42", 0), ("tick", 501), ("event", "CHECKPOINT"), ("attempts", "01"),
])
def test_corrupt_aggregate_rejected(tmp_path: Path, key: str, value: Any) -> None:
    fixture(tmp_path)
    edit(tmp_path / "conservation001.csv", COLUMNS, -1, key, value)
    with pytest.raises(ValueError):
        analyze_run(tmp_path, expected_initial("host"), "histogram", 16, nsteps=500)


@pytest.mark.parametrize("kind", ["hidden", "visible", "missing-end", "unknown-id", "duplicate", "terminator", "bad-symbol", "lowercase", "missing-checkpoint"])
def test_corrupt_buffers_rejected(tmp_path: Path, kind: str) -> None:
    fixture(tmp_path)
    path = tmp_path / "conservation_buffers001.csv"
    data: list[dict[str, Any]] = list(canonical_rows(path, BUFFER_COLUMNS))
    if kind == "missing-end":
        data = [r for r in data if r["event"] != "END"]
    elif kind == "missing-checkpoint":
        data = [r for r in data if r["tick"] != "100"]
    elif kind == "unknown-id":
        data[-1]["id"] = "999"
    elif kind == "duplicate":
        data[-1]["id"] = data[-2]["id"]
    else:
        value = data[0]["full_buffer_hex"]
        if kind == "hidden":
            value = value[:-6] + "410000"
        elif kind == "visible":
            value = "41" + value[2:]
        elif kind == "terminator":
            value = value[:-2] + "41"
        elif kind == "bad-symbol":
            value = value[:-4] + "FF00"
        elif kind == "lowercase":
            value = value.lower()
        data[0]["full_buffer_hex"] = value
    write(path, BUFFER_COLUMNS, data)
    with pytest.raises(ValueError):
        analyze_run(tmp_path, expected_initial("host"), "histogram", 16, nsteps=500)


def test_canonical_serialization_checksum(tmp_path: Path) -> None:
    path = tmp_path / "buffers.csv"
    write(path, BUFFER_COLUMNS, [{"tick": 0, "event": "END", "id": 7, "full_buffer_hex": "41004200"}])
    assert path.read_bytes() == b"tick,event,id,full_buffer_hex\n0,END,7,41004200\n"
    assert record(path)["sha256"] == "e684e39ef27d43885b6f2f8f5ea4870f9e962f57575924c0416b83b20fdf5fdc"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    with pytest.raises(ValueError, match="canonical"):
        canonical_rows(path, BUFFER_COLUMNS)


def test_partition_and_reconciliation_even_with_zero_residual(tmp_path: Path) -> None:
    fixture(tmp_path)
    # Aggregate molecular+pool is untouched, but inventing gross releases fails.
    edit(tmp_path / "conservation001.csv", COLUMNS, -1, "decay_returns_42", 1)
    with pytest.raises(ValueError, match="reconciliation"):
        analyze_run(tmp_path, expected_initial("host"), "histogram", 16, nsteps=500)


def mock_preparation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    build_file, gate_file = tmp_path / "build.json", tmp_path / "gates.json"
    seal(build_file, {}); seal(gate_file, {})
    data = {"builds": {"observer": {"source": str(tmp_path / "source")}}}
    monkeypatch.setattr(workflow, "verify_build", lambda _: data)
    monkeypatch.setattr(workflow, "verify_gate", lambda *_: None)
    monkeypatch.setattr(workflow, "source_state", lambda _: {"commit": "test"})
    return workflow.prepare(build_file, gate_file, tmp_path / "prepared")


def test_prepare_only_and_inventory_freeze(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("preparation launched unseen simulator")
    monkeypatch.setattr(workflow, "execute", forbidden)
    path = mock_preparation(tmp_path, monkeypatch)
    data = workflow.verify_preparation(path)
    assert len(data["runs"]) == 20 and data["workers"] == 6
    assert not (path.parent / "runs").exists()
    assert data["protocol_pin"]["inherited"]["sha256"] == PROTOCOL_SHA256
    for r in data["runs"]:
        assert r["initial_material"] == initial_material(expected_initial("host"), "histogram", r["amount"])
        assert r["environment"] == workflow.environment("histogram", r["amount"])
    config = Path(data["runs"][0]["config"])
    config.chmod(0o644)
    with pytest.raises(ValueError, match="config"):
        workflow.verify_preparation(path)


@pytest.mark.parametrize("target", ["workers", "environment", "initial_material", "protocol_pin", "seed", "amount"])
def test_resealed_manifest_tampering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    import json
    path = mock_preparation(tmp_path, monkeypatch)
    data = read(path)
    if target == "workers":
        data[target] = 7
    elif target == "protocol_pin":
        data[target]["sha256"] = "forged"
    else:
        data["runs"][0][target] = "forged"
    path.chmod(0o644); path.write_text(json.dumps(data)); path.chmod(0o444)
    receipt = path.with_name("preparation.sha256.json")
    receipt.chmod(0o644); receipt.write_text(json.dumps(record(path))); receipt.chmod(0o444)
    with pytest.raises((ValueError, TypeError)):
        workflow.verify_preparation(path)


def test_six_workers_failed_denominator_no_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = mock_preparation(tmp_path, monkeypatch)
    lock, six = threading.Lock(), threading.Event()
    active = maximum = calls = 0
    def fake(binary: Path, config: Path, directory: Path, env: dict[str, str]) -> dict[str, Any]:
        nonlocal active, maximum, calls
        assert env["STRINGMOL_CONSERVATION"] == "1"
        with lock:
            active += 1; calls += 1; maximum = max(maximum, active)
            if active == 6:
                six.set()
        assert six.wait(10)
        directory.mkdir(parents=True)
        (directory / "stdout.txt").write_text("synthetic failure")
        with lock:
            active -= 1
        return {"exit_status": 7, "files": inventory(directory)}
    monkeypatch.setattr(workflow, "execute", fake)
    workflow.run_matrix(path)
    assert maximum == 6 and calls == 20
    results = read(path.parent / "campaign-results.json")
    assert len(results) == 20 and all(r["exit_status"] == 7 for r in results)
    for r in read(path)["runs"]:
        directory = Path(r["directory"])
        assert read(directory.with_suffix(".inventory.json"))["files"] == inventory(directory)
    with pytest.raises(ValueError, match="no resume"):
        workflow.run_matrix(path)
    assert calls == 20


def test_preexisting_directory_prevents_all_launches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = mock_preparation(tmp_path, monkeypatch)
    (path.parent / "runs").mkdir()
    with pytest.raises(ValueError):
        workflow.run_matrix(path)
    assert not (path.parent / "campaign.json").exists()


def test_fixed_n_ties_and_joint_seed_gate() -> None:
    results = []
    for i in range(10):
        for condition in ("m16", "m0"):
            results.append({"seed": 202621000+i, "condition": condition,
                            "successful_births": 100 if condition == "m16" or i >= 8 else 99,
                            "max_two_parent_depth": 2, "final_noninitial_descendants": 100,
                            "final_descendant_fraction": .5,
                            "end_conservation": {"scarcity_blocked": 1 if condition == "m16" or i >= 8 else 2}})
    result = outcomes(results, [])
    assert result["decision"] == "pass"
    assert result["birth_wins"] == result["scarcity_wins"] == 8
    assert result["birth_coin_tail"] == result["scarcity_coin_tail"] == 56 / 1024
    assert outcomes(results[:-1], [{"error": "missing"}])["decision"] == "unevaluable"


def test_parity_exact_extra_files() -> None:
    base: dict[str, Any] = {"exit_status": 0, "files": {"stdout.txt": "hash"}}
    other = {"exit_status": 0, "files": {**base["files"], **dict.fromkeys(workflow.CONSERVATION_LOGS)}}
    workflow.parity(base, other, workflow.CONSERVATION_LOGS)
    for extra in ({}, {"unexpected": "x"}):
        with pytest.raises(ValueError):
            workflow.parity(base, {"exit_status": 0, "files": {**base["files"], **extra}}, workflow.CONSERVATION_LOGS)


def test_sanitized_execute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_UNWANTED", "do not inherit")
    binary = tmp_path / "fake"
    binary.write_text("#!/bin/sh\n/usr/bin/env\nexit 3\n"); binary.chmod(0o755)
    result = workflow.execute(binary, tmp_path / "cfg", tmp_path / "out", workflow.environment("histogram", 0))
    text = (tmp_path / "out/stdout.txt").read_text()
    assert "SECRET_UNWANTED" not in text and "STRINGMOL_POOL_AMOUNT=0" in text
    assert result["exit_status"] == 3


def test_minima_cannot_drop_without_withdrawal(tmp_path: Path) -> None:
    fixture(tmp_path)
    path = tmp_path / "conservation001.csv"
    rows_ = canonical_rows(path, COLUMNS)
    value = int(rows_[1]["pool_minimum_42"])
    edit(path, COLUMNS, 1, "pool_minimum_42", value - 1)
    with pytest.raises(ValueError, match="minimum"):
        analyze_run(tmp_path, expected_initial("host"), "histogram", 16, nsteps=500)


def test_initial_and_gross_counters_not_just_residual(tmp_path: Path) -> None:
    fixture(tmp_path)
    path = tmp_path / "conservation001.csv"
    edit(path, COLUMNS, 0, "attempts", 1)
    edit(path, COLUMNS, 0, "final_byte_noop", 1)
    with pytest.raises(ValueError, match="initial counters"):
        analyze_run(tmp_path, expected_initial("host"), "histogram", 16, nsteps=500)


def test_end_ids_cannot_resurrect(tmp_path: Path) -> None:
    fixture(tmp_path)
    # Reuse a never-introduced ID at END without changing population/histogram.
    path = tmp_path / "conservation_buffers001.csv"
    edit(path, BUFFER_COLUMNS, -1, "id", 1000)
    with pytest.raises(ValueError, match="introduction"):
        analyze_run(tmp_path, expected_initial("host"), "histogram", 16, nsteps=500)


def test_build_pins_untracked_new_header(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "src").mkdir()
    header = tmp_path / "src/sm_conservation.h"
    header.write_text("original")
    def command(args: list[str], cwd: Path) -> bytes:
        if "ls-files" in args:
            return b""
        return b"fixture"
    monkeypatch.setattr(workflow, "command", command)
    before = workflow.source_state(tmp_path)
    header.write_text("changed")
    assert before["source_files"] != workflow.source_state(tmp_path)["source_files"]


@pytest.mark.parametrize("changed_committed", [False, True])
def test_committed_protocol_bytes_are_independently_pinned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed_committed: bool) -> None:
    pin = workflow.protocol_pin()
    committed = bytes.fromhex(pin["bytes_hex"])
    path = tmp_path / workflow.PROTOCOL_PATH
    path.parent.mkdir()
    path.write_bytes(committed if changed_committed else committed + b"change")
    monkeypatch.setattr(workflow, "ROOT", tmp_path)
    monkeypatch.setattr(workflow, "command", lambda *_: committed + b"change" if changed_committed else committed)
    with pytest.raises(ValueError, match="protocol"):
        workflow.protocol_pin()


@pytest.mark.parametrize("growth,contractions", [(0, 1), (1, 1), (1, 2)])
def test_native_nul_insertion_reconstruction(tmp_path: Path, growth: int, contractions: int) -> None:
    """Upper float endpoint selects native key[N]=NUL; retain hidden material.

    The C++ controlled-MT fixture verifies native execution. Here the independent
    analyzer sees only serialized buffers and ledgers, including contraction
    without withdrawals and positive-growth history with nonpositive net growth.
    """
    fixture(tmp_path)
    material = initial_material(expected_initial("host"), "histogram", 16)
    raw = bytearray(bytes.fromhex(material["buffers"]["0"]))
    assert raw[:4] == b"WWGE"
    if growth:
        # A prior hidden-tail append, separated from the visible string by NUL.
        raw[len(bytes.fromhex(expected_initial("host")[0]["sequence_hex"])) + 1] = ord("W")
    # First ordered destination already equals the read symbol. The inserted
    # NUL overwrites the second destination: gross return only, not a no-op.
    raw[1] = 0
    returns = {"W": 1}
    if contractions == 2:
        raw[3] = 0
        returns["E"] = 1
    buffer_path = tmp_path / "conservation_buffers001.csv"
    buffers: list[dict[str, Any]] = list(canonical_rows(buffer_path, BUFFER_COLUMNS))
    for row in buffers:
        if row["tick"] != "0" and row["id"] == "0":
            row["full_buffer_hex"] = raw.hex().upper()
    write(buffer_path, BUFFER_COLUMNS, buffers)
    snapshot_path = tmp_path / "lineage_snapshots001.csv"
    with snapshot_path.open(newline="") as f:
        snapshots: list[dict[str, Any]] = list(csv.DictReader(f))
    for row in snapshots:
        if row["tick"] != "0" and row["id"] == "0":
            row["sequence_hex"] = "57"  # W; all following non-NUL bytes are hidden.
    write(snapshot_path, SNAPSHOT_COLUMNS, snapshots)
    aggregate_path = tmp_path / "conservation001.csv"
    aggregate: list[dict[str, Any]] = list(canonical_rows(aggregate_path, COLUMNS))
    for row in aggregate[1:]:
        row.update(attempts=growth + contractions, accepted_changed=growth + contractions, accepted_positive_growth=growth)
        for s in ("W", "E"):
            index = ALPHABET.index(s)
            withdraw = growth if s == "W" else 0
            returned = returns.get(s, 0)
            row[fields("molecular")[index]] = material["molecular"][index] + withdraw - returned
            row[fields("pool")[index]] = material["pool"][index] - withdraw + returned
            row[fields("copy_withdrawals")[index]] = withdraw
            row[fields("copy_returns")[index]] = returned
            row[fields("pool_minimum")[index]] = material["pool"][index] - withdraw
        row["molecular_bytes"] = int(row["molecular_bytes"]) + growth - contractions
        row["free_bytes"] = int(row["free_bytes"]) - growth + contractions
    write(aggregate_path, COLUMNS, aggregate)
    result = analyze_run(tmp_path, expected_initial("host"), "histogram", 16, nsteps=500)
    end = result["end_conservation"]
    assert result["zero_residual"] and end["accepted_changed"] == growth + contractions
    assert end["accepted_positive_growth"] == growth
    assert sum(end["copy_withdrawals"]) == growth
    assert sum(end["copy_returns"]) == contractions
    assert end["molecular_bytes"] == sum(material["molecular"]) + growth - contractions


def mock_object_build(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Fake compiler products; keep real object inventory and link verification."""
    monkeypatch.setattr(workflow, "protocol_pin", lambda: {"test": "protocol"})
    monkeypatch.setattr(workflow, "source_state", lambda _: {"commit": workflow.PIN})
    builds = {}
    for name in ("baseline", "observer"):
        source = tmp_path / name
        (source / "release").mkdir(parents=True)
        (source / "config").mkdir()
        for obj in workflow.RELEASE_OBJECTS:
            (source / "release" / f"{obj}.o").write_bytes(obj.encode())
        (source / "release/stringmol").write_bytes(b"unchanged simulator")
        (source / "config/ALXII.mtx").write_bytes(b"matrix")
        builds[name] = {"source": str(source), "state": {"commit": workflow.PIN},
                        "binary": record(source / "release/stringmol"), "matrix": record(source / "config/ALXII.mtx"),
                        "release_objects": workflow.release_objects(source),
                        "patch_order": [str(p) for p in (workflow.PATCHES[:2] if name == "baseline" else workflow.PATCHES)]}
    path = tmp_path / "build.json"
    seal(path, {"protocol_pin": workflow.protocol_pin(), "implementation": {str(p): record(p) for p in workflow.IMPLEMENTATION},
                "environment": workflow.ENV, "flags": workflow.FLAGS, "builds": builds,
                "patches": [{"path": str(p), **record(p), "bytes_hex": p.read_bytes().hex()} for p in workflow.PATCHES], "logs": {}})
    workflow.verify_build(path)
    return path


@pytest.mark.parametrize("variant", ["baseline", "observer"])
@pytest.mark.parametrize("change", ["replace", "remove", "extra", "symlink", "main"])
def test_release_object_tampering_rejected_before_directed_link(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str, change: str) -> None:
    build = mock_object_build(tmp_path, monkeypatch)
    obj = tmp_path / variant / "release/agent.o"
    if change == "replace":
        obj.write_bytes(b"tampered but simulator unchanged")
    elif change == "remove":
        obj.unlink()
    elif change == "extra":
        obj.with_name("extra.o").write_bytes(b"unexpected linkage")
    elif change == "main":
        obj.with_name("stringmol.o").write_bytes(b"main also pinned")
    else:
        obj.unlink()
        obj.symlink_to(obj.with_name("alignment.o"))
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("compiler/linker must not run on changed object inputs")
    monkeypatch.setattr(workflow, "command", forbidden)
    with pytest.raises(ValueError, match="release object|regular file"):
        workflow.directed(build, tmp_path)


@pytest.mark.parametrize("field", ["objects", "command", "build_record", "fixture", "environment"])
def test_directed_receipt_binds_exact_linkage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    build = mock_object_build(tmp_path, monkeypatch)
    linkage = workflow.directed_linkage(build, workflow.verify_build(build), tmp_path)
    assert len(linkage["objects"]) == len(workflow.RELEASE_OBJECTS) - 1
    assert all(not p.endswith("/stringmol.o") for p in linkage["objects"])
    receipt = {"linkage": linkage, "exit_status": 0}
    for key, name in (("binary", "directed-test"), ("stdout", "directed.stdout"), ("stderr", "directed.stderr")):
        path = tmp_path / name
        path.write_text("synthetic directed artifact")
        receipt[key] = record(path)
    workflow.verify_directed(receipt, build, tmp_path)
    linkage[field] = "forged"
    with pytest.raises(ValueError, match="linkage receipt"):
        workflow.verify_directed(receipt, build, tmp_path)


def test_integrity_exit_cannot_pass_scientific_analysis(tmp_path: Path) -> None:
    fixture(tmp_path)
    with pytest.raises(ValueError, match="exit"):
        analyze_run(tmp_path, expected_initial("host"), "histogram", 16, nsteps=500, exit_status=1)
