from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path
from typing import Any, Callable, cast

import numpy as np
import pytest

from experiments import analyze_ac_p003_functional_origin_convergence as source
from experiments import phase1_probe as probe
from experiments import run_ac_p006_transplant as transplant
from experiments.paper_probe import initialize_soup, shuffle_indices
from experiments.run_phase2_parasite_control import parasite_tape


def test_frozen_shuffle_composition_score_and_determinism() -> None:
    witness = parasite_tape()
    original = witness.copy()
    for index in range(10):
        control = transplant.shuffled_control(witness, index)
        assert np.array_equal(control, transplant.shuffled_control(witness, index))
        assert np.array_equal(np.sort(control), np.sort(witness))
        assert not np.array_equal(control, witness)
        assert transplant.validate_control(witness, control) < 64
    assert np.array_equal(witness, original)
    # Independent uint64 implementation of the frozen draw, not RNG state.
    from experiments.paper_probe import splitmix64
    expected = np.arange(64, dtype=np.uint8)
    for i in range(63, 0, -1):
        draw = int(splitmix64(np.uint64(0xAC006) ^ splitmix64(np.uint64(3 * 64 + i))))
        j = draw % (i + 1)
        expected[i], expected[j] = expected[j], expected[i]
    assert np.array_equal(transplant.shuffled_control(np.arange(64, dtype=np.uint8), 3), expected)


def test_invalid_controls_stop_without_alternatives(monkeypatch: pytest.MonkeyPatch) -> None:
    witness = parasite_tape()
    with pytest.raises(ValueError, match="unchanged"):
        transplant.validate_control(witness, witness.copy())
    with pytest.raises(ValueError, match="composition"):
        transplant.validate_control(witness, np.zeros(64, dtype=np.uint8))
    calls = []
    def score(tapes: Any, seed: int) -> Any:
        calls.append(seed)
        return np.asarray([64], dtype=np.int64)
    monkeypatch.setattr(transplant, "score_selfrep_candidates", score)
    with pytest.raises(ValueError, match="below 64"):
        transplant.validate_control(witness, transplant.shuffled_control(witness, 0))
    assert calls == [0]


def test_paired_initial_histograms_pools_and_replacements() -> None:
    witness = parasite_tape()
    control = transplant.shuffled_control(witness, 2)
    left, right, indices = transplant.paired_inocula(witness, control, 2)
    background = cast(Callable[[int, int], transplant.U8], initialize_soup)(32768, 202616002)
    order = np.arange(32768, dtype=np.uint32)
    cast(Callable[[Any, int, int], None], shuffle_indices)(order, 202616002, 0xAC006 + 2)
    assert np.array_equal(indices, order[:32])
    assert len(np.unique(indices)) == 32
    keep = np.ones(32768, dtype=bool)
    keep[indices] = False
    assert np.array_equal(left[keep], background[keep])
    assert np.array_equal(right[keep], background[keep])
    assert np.all(left[indices] == witness)
    assert np.all(right[indices] == control)
    a = np.bincount(left.ravel(), minlength=256)
    b = np.bincount(right.ravel(), minlength=256)
    assert a.tobytes() == b.tobytes()
    assert (a * 16).tobytes() == (b * 16).tobytes()
    assert probe.exact_tape_count(left, witness.tobytes()) >= 32
    assert probe.exact_tape_count(right, control.tobytes()) >= 32


def rows(path: Path) -> list[dict[str, str]]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def test_tracker_truthfulness_isolation_and_conservation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    soup = np.tile(parasite_tape(), (16, 1))
    soup[1, -1] ^= 1  # near match must not count
    target = soup[0].tobytes()
    initial = tmp_path / "initial.npy"
    np.save(initial, soup)
    observed: list[int] = []
    original = probe.mutate_and_execute_conserved_epoch
    def capture(*args: Any, **kwargs: Any) -> Any:
        result = original(*args, **kwargs)
        observed.append(sum(row.tobytes() == target for row in args[0]))
        return result
    monkeypatch.setattr(probe, "mutate_and_execute_conserved_epoch", capture)
    common: dict[str, Any] = dict(population_size=16, epochs=5, seed=71,
        mutation_rate=1 / 64, pool_multiplier=16, callback_interval=2,
        max_steps=128, initial_soup=initial)
    disabled = probe.run_probe(**common, output_dir=tmp_path / "off", final_soup=tmp_path / "off.npy")
    observed.clear()
    enabled = probe.run_probe(**common, tracked_tape=target, output_dir=tmp_path / "on", final_soup=tmp_path / "on.npy")
    assert (tmp_path / "off.npy").read_bytes() == (tmp_path / "on.npy").read_bytes()
    for name in ("writes.csv", "symbols.csv"):
        assert (disabled / name).read_bytes() == (enabled / name).read_bytes()
    tracking = rows(enabled / "tracked_tape.csv")
    assert [int(r["epoch"]) for r in tracking] == [0, 1, 3, 5]
    assert [int(r["exact_target_count"]) for r in tracking] == [15, *observed[::2]]
    off, on = rows(disabled / "aggregate.csv"), rows(enabled / "aggregate.csv")
    for i, (a, b) in enumerate(zip(off, on, strict=True), start=1):
        assert int(b.pop("exact_target_count")) == int(tracking[i]["exact_target_count"])
        a.pop("elapsed_seconds")
        b.pop("elapsed_seconds")
        assert a == b
        assert a["max_conservation_residual"] == "0"
    manifest = json.loads((enabled / "manifest.json").read_text())
    assert manifest["initial_exact_target_count"] == 15
    assert "tracked_tape.csv" in manifest["artifact_checksums"]
    assert manifest["config"]["exact_tape_tracker"]["target_hex"] == target.hex()
    assert "exact_tape_tracker" not in json.loads((disabled / "config.json").read_text())
    assert not (disabled / "tracked_tape.csv").exists()
    assert disabled.name == "p1_m16_n16_s71_cont"
    # Changing target/version must create isolated run IDs.
    other = probe.run_probe(**common, tracked_tape=bytes(64), output_dir=tmp_path / "on")
    monkeypatch.setattr(probe, "EXACT_TAPE_TRACKER_VERSION", "test-version")
    version = probe.run_probe(**common, tracked_tape=target, output_dir=tmp_path / "on")
    assert len({enabled.name, other.name, version.name}) == 3
    (enabled / "tracked_tape.csv").write_text("corrupt")
    monkeypatch.setattr(probe, "EXACT_TAPE_TRACKER_VERSION", "exact-tape-v1")
    with pytest.raises(RuntimeError, match="corrupt"):
        probe.run_probe(**common, tracked_tape=target, output_dir=tmp_path / "on", final_soup=tmp_path / "on.npy")


def test_tracker_rejects_bad_target_before_writing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="64 bytes"):
        probe.run_probe(population_size=16, epochs=1, seed=1, mutation_rate=0,
            pool_multiplier=16, callback_interval=1, output_dir=tmp_path / "run", tracked_tape=b"short")
    assert not (tmp_path / "run").exists()


def test_preparation_validates_all_sources_before_soup_building(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded: list[int] = []
    def checkpoint(root: Path, run: Any) -> Any:
        loaded.append(run.seed)
        if len(loaded) == 10:
            raise ValueError("synthetic invalid source")
        from types import SimpleNamespace
        return SimpleNamespace(witness=parasite_tape())
    def forbidden(*args: Any) -> Any:
        pytest.fail("recipient construction or launch before all sources validated")
    monkeypatch.setattr(source, "load_checkpoint", checkpoint)
    monkeypatch.setattr(transplant, "paired_inocula", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(ValueError, match="invalid source"):
        transplant.prepare(tmp_path / "sources", tmp_path / "output")
    assert loaded == list(transplant.SOURCE_SEEDS)
    assert not (tmp_path / "output").exists()


def test_runner_uses_six_workers_and_one_numba_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    def run(command: list[str], **kwargs: Any) -> None:
        calls.append((command, kwargs))
    class Executor:
        def __init__(self, max_workers: int) -> None:
            assert max_workers == 6
        def __enter__(self) -> Executor:
            return self
        def __exit__(self, *args: Any) -> None:
            pass
        def map(self, function: Any, commands: Any) -> Any:
            return map(function, commands)
    monkeypatch.setattr(transplant, "ThreadPoolExecutor", Executor)
    monkeypatch.setattr(subprocess, "run", run)
    transplant.execute([["synthetic", "command"]] * 20)
    assert len(calls) == 20
    assert all(call[1]["env"]["NUMBA_NUM_THREADS"] == "1" and call[1]["check"] for call in calls)
