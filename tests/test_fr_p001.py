"""Focused FR-P001 observation, independent reconstruction, integrity and resume tests."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import struct
from typing import Any

import numpy as np
import pytest

from experiments import fr_p001 as f
from experiments import analyze_ac_p003_functional_origin_convergence as source
from experiments import run_fr_p001 as run
from experiments import analyze_fr_p001 as analysis
from experiments.fr_i002_gate import State


def fixture() -> tuple[State, f.I64, f.I64]:
    data = np.full((4, 64), 65, dtype=np.uint8)
    data[2:, 0] = 66
    labels = np.zeros_like(data)
    labels[0, :47] = 1
    labels[1, :48] = 1
    labels[2, :48] = 1
    labels[3, :] = 1
    pool = np.bincount(data.ravel(), minlength=256).astype(np.int64) * 16
    return State.create(data, labels, pool), pool, pool + np.bincount(data.ravel(), minlength=256)


def test_frozen_shuffle_and_pair() -> None:
    witness = np.arange(64, dtype=np.uint8)
    shuffled = run.control(witness, 8)
    assert shuffled.tolist()[:8] == [57, 6, 59, 52, 51, 33, 44, 15]
    left, right, indices, labels = run.paired(witness, shuffled, 8)
    assert len(set(indices.tolist())) == 32
    assert labels.sum() == 32 * 64
    assert np.array_equal(left[indices], np.tile(witness, (32, 1)))
    assert np.array_equal(right[indices], np.tile(shuffled, (32, 1)))
    assert np.array_equal(np.bincount(left.ravel(), minlength=256), np.bincount(right.ravel(), minlength=256))


def test_canonical_occurrences_and_independent_reconstruction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, pool, totals = fixture()
    monkeypatch.setattr(f, 'score', lambda tape: 64)
    monkeypatch.setattr(f.paper, 'score_selfrep_candidates', lambda tapes, seed: np.array([64], dtype=np.int64))
    db = f.database(tmp_path / 'run.sqlite')
    record = f.observe(db, tmp_path, state, 1, np.zeros(9, dtype=np.int64), state.data[1].tobytes(), pool, totals)
    expected = (b'A' * 64 + struct.pack('<BQ', 48, 1)
                + b'B' + b'A' * 63 + struct.pack('<BQ', 48, 1)
                + b'B' + b'A' * 63 + struct.pack('<BQ', 64, 1))
    assert record['canonical_sha256'] == f.digest(expected)
    assert record['candidate_abundance'] == 3 and record['candidate_distinct'] == 2
    assert record['nonexact_abundance'] == 2 and record['nonexact_distinct'] == 1
    assert record['exact_target'] == 2 and record['evaluated_tapes'] == 3
    assert record['qualifying_label_histogram_48_64'] == [2] + [0] * 15 + [1]
    independent = sqlite3.connect(':memory:')
    independent.execute('CREATE TABLE independent (tape BLOB PRIMARY KEY, score INTEGER)')
    canonical, rows, values = analysis.reconstruct(state.data, state.labels, state.data[1].tobytes(), independent)
    assert canonical == expected and len(rows) == 3
    assert all(record[k] == v for k, v in values.items())
    f.verify_callback(db, tmp_path, record, state.data[1].tobytes(), pool, totals)
    db.close()
    independent.close()


def test_single_seed_zero_cache_and_chunking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    def evaluator(tapes: f.U8, seed: int) -> f.I64:
        assert tapes.shape == (1, 64) and seed == 0
        calls.append(tapes.tobytes())
        return np.array([int(tapes[0, 0]) % 65], dtype=np.int64)
    monkeypatch.setattr(f.paper, 'score_selfrep_candidates', evaluator)
    sequences = [i.to_bytes(2, 'little') + bytes(62) for i in range(4100)]
    db = f.database(tmp_path / 'cache.sqlite')
    with db:
        first = f.fill_scores(db, sequences)
        assert f.fill_scores(db, sequences) == first
    assert len(calls) == 4100
    assert db.execute('SELECT count(*) FROM scores').fetchone() == (4100,)
    db.close()


@pytest.mark.parametrize('damage', ('labels', 'pool', 'ledger'))
def test_fail_closed_state(damage: str, tmp_path: Path) -> None:
    state, pool, totals = fixture()
    if damage == 'labels':
        state.labels[0, 0] = 2
    elif damage == 'pool':
        state.arrays['pool'][65] += 1
    else:
        state.arrays['withdrawals'][65] += 1
    db = f.database(tmp_path / 'cache.sqlite')
    with pytest.raises(ValueError):
        f.observe(db, tmp_path, state, 1, np.zeros(9, dtype=np.int64), bytes(64), pool, totals)
    assert db.execute('SELECT count(*) FROM callbacks').fetchone() == (0,)
    db.close()


def test_artifact_and_sql_tampering(tmp_path: Path) -> None:
    state, pool, totals = fixture()
    target = state.data[0].tobytes()
    db = f.database(tmp_path / 'cache.sqlite')
    record = f.observe(db, tmp_path, state, 1, np.zeros(9, dtype=np.int64), target, pool, totals)
    db.execute('UPDATE audit SET abundance=2')
    with pytest.raises(ValueError, match='SQLite audit'):
        f.verify_callback(db, tmp_path, record, target, pool, totals)
    db.rollback()
    path = tmp_path / record['snapshot']
    path.write_bytes(path.read_bytes() + b'corrupt')
    with pytest.raises(ValueError, match='snapshot checksum'):
        f.verify_callback(db, tmp_path, record, target, pool, totals)
    db.close()


def test_failed_callback_rolls_back_and_can_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state, pool, totals = fixture()
    db = f.database(tmp_path / 'cache.sqlite')
    original = np.savez_compressed
    monkeypatch.setattr(np, 'savez_compressed', lambda *a, **k: (_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError, match='disk full'):
        f.observe(db, tmp_path, state, 1, np.zeros(9, dtype=np.int64), bytes(64), pool, totals)
    assert db.execute('SELECT count(*) FROM callbacks').fetchone() == (0,)
    assert db.execute('SELECT count(*) FROM scores').fetchone() == (0,)
    monkeypatch.setattr(np, 'savez_compressed', original)
    f.observe(db, tmp_path, state, 1, np.zeros(9, dtype=np.int64), bytes(64), pool, totals)
    assert db.execute('SELECT count(*) FROM callbacks').fetchone() == (1,)
    db.close()


def test_isolation_real_observer(tmp_path: Path) -> None:
    assert run.isolation(tmp_path)['passed']


def test_endpoint_windows_and_control_exact_does_not_shield() -> None:
    trajectory = [{'epoch': epoch, 'nonexact_abundance': 1, 'exact_target': 0} for epoch in f.EPOCHS]
    assert analysis.endpoint(trajectory, 'witness')['post_transient_load'] == 91
    assert analysis.endpoint(trajectory, 'witness')['sustained']
    trajectory[-10]['exact_target'] = 1
    assert not analysis.endpoint(trajectory, 'witness')['sustained']
    assert analysis.endpoint(trajectory, 'shuffle')['sustained']
    trajectory[-10]['nonexact_abundance'] = 0
    assert not analysis.endpoint(trajectory, 'shuffle')['sustained']


def test_acceptance_ties_and_sign_tail() -> None:
    pairs = [{'witness': {'sustained': i < 7, 'post_transient_load': 2 if i < 8 else 1},
              'shuffle': {'sustained': i == 0, 'post_transient_load': 1}} for i in range(9)]
    result = analysis.decision(pairs)
    assert result['status'] == 'pass' and result['one_sided_fair_sign_tail'] == 10 / 512
    pairs[7]['witness']['post_transient_load'] = 1
    assert not analysis.decision(pairs)['gates']['paired_load']


def test_no_preflight_no_source_reads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('source accessed before resource gate')
    monkeypatch.setattr(source, 'load_checkpoint', forbidden)
    with pytest.raises(FileNotFoundError):
        run.prepare(tmp_path / 'out', tmp_path, tmp_path, tmp_path / 'missing.json', output_version='test-v2')


def test_incomplete_analysis_is_unevaluable(tmp_path: Path) -> None:
    result = analysis.analyze(tmp_path / 'missing', tmp_path / 'report')
    assert result['status'] == 'unevaluable' and not result['gates']['integrity']
    assert json.loads((tmp_path / 'report' / 'analysis.json').read_text()) == result


def test_resource_boundaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f, 'available_ram', lambda: 64 * 2**30)
    assert not f.resources(tmp_path, 1200.01, 1000)['passed']
    assert not f.resources(tmp_path, 1, 8 * 2**30)['passed']
    assert not f.resources(tmp_path, 900, 1000)['passed']  # projection exceeds 72h
    assert f.RAW_BOUND == 7625244672


def test_run_resume_restores_order_counters_and_absolute_epoch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('NUMBA_NUM_THREADS', '1')
    monkeypatch.setattr(f, 'EPOCHS', (1, 3))
    monkeypatch.setattr(f, 'POPULATION', 4)
    state, pool, totals = fixture()
    path = tmp_path / 'input.npz'
    np.savez_compressed(path, soup=state.data, labels=state.labels, pool=pool)
    (tmp_path / 'preparation.json').write_text('{}')
    (tmp_path / 'isolation.json').write_text(json.dumps({'passed': True, 'run_pins': f.run_pins()}))
    item = {'path': path.name, 'target_hex': state.data[0].tobytes().hex()}
    monkeypatch.setattr(run, 'validate_preparation', lambda path: {'pairs': [{'arms': {'witness': item}}]})
    monkeypatch.setattr(run, 'check_launch_resources', lambda *args: {})
    original = f.observe
    def interrupted(*args: Any, **kwargs: Any) -> Any:
        if args[3] == 3:
            raise RuntimeError('simulated interruption')
        return original(*args, **kwargs)
    monkeypatch.setattr(f, 'observe', interrupted)
    with pytest.raises(RuntimeError, match='interruption'):
        run.run_one(tmp_path, 0, 'witness')
    monkeypatch.setattr(f, 'observe', original)
    run.run_one(tmp_path, 0, 'witness')
    final, metrics = f.load_snapshot(tmp_path / 'runs/00_witness/epoch_00003.npz')
    expected_metrics = np.zeros(9, dtype=np.int64)
    shuffle: Any = f.paper.shuffle_indices
    for epoch in range(3):
        shuffle(state.order, 202619000, epoch)
        expected_metrics += state.epoch(True, 202619000, epoch, (1 << 30) // 4096, 0)
    assert final.digest(tuple(metrics)) == state.digest(tuple(expected_metrics))
    before = (tmp_path / 'runs/00_witness/complete.json').read_bytes()
    run.run_one(tmp_path, 0, 'witness')
    assert (tmp_path / 'runs/00_witness/complete.json').read_bytes() == before


def test_independent_analyzer_full_synthetic_inventory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f, 'EPOCHS', (1,))
    monkeypatch.setattr(f, 'FINAL', (1,))
    monkeypatch.setattr(f, 'POPULATION', 4)
    (tmp_path / 'preparation.json').write_text('{}')
    (tmp_path / 'isolation.json').write_text(json.dumps({'passed': True, 'run_pins': f.run_pins()}))
    state, pool, totals = fixture()
    np.savez_compressed(tmp_path / 'input.npz', soup=state.data, labels=state.labels, pool=pool)
    item = {'path': 'input.npz', 'target_hex': state.data[0].tobytes().hex()}
    prepared = {'pairs': [{'arms': {'witness': item, 'shuffle': item}} for _ in range(9)]}
    monkeypatch.setattr(analysis, 'validate_preparation', lambda _: prepared)
    for index in range(9):
        for arm in ('witness', 'shuffle'):
            directory = tmp_path / 'runs' / f'{index:02d}_{arm}'
            directory.mkdir(parents=True)
            db = f.database(directory / 'run.sqlite')
            record = f.observe(db, directory, state, 1, np.zeros(9, dtype=np.int64),
                               state.data[0].tobytes(), pool, totals)
            db.close()
            binding = {'preparation_sha256': f.sha(tmp_path / 'preparation.json'), 'index': index, 'arm': arm}
            f.atomic_json(directory / 'binding.json', binding)
            f.atomic_json(directory / 'complete.json', {**binding, 'epochs': [1],
                'database_sha256': f.sha(directory / 'run.sqlite'),
                'soup_sha256': record['soup_sha256'], 'labels_sha256': record['labels_sha256']})
    result = analysis.analyze(tmp_path, tmp_path / 'report')
    assert result['status'] == 'fail_with_valid_integrity', result
    assert len(result['trajectories']) == 18
    # Forge runner cache AND all its aggregate/checksum assertions consistently.
    # Fresh independent seed-zero rescoring must still reject the fabrication.
    directory = tmp_path / 'runs/00_witness'
    db = sqlite3.connect(directory / 'run.sqlite')
    db.execute('UPDATE scores SET score=64')
    manifest = json.loads(db.execute('SELECT manifest FROM callbacks').fetchone()[0])
    rows = f.audit_table(state.data, state.labels)
    manifest.update(f.aggregate(rows, {r['tape'].tobytes(): 64 for r in rows}, state.data, state.data[0].tobytes()))
    manifest['scores_sha256'] = f.score_digest(db)
    db.execute('UPDATE callbacks SET manifest=?', (json.dumps(manifest),))
    db.commit()
    db.close()
    complete = json.loads((directory / 'complete.json').read_text())
    complete['database_sha256'] = f.sha(directory / 'run.sqlite')
    f.atomic_json(directory / 'complete.json', complete)
    result = analysis.analyze(tmp_path, tmp_path / 'report2')
    assert result['status'] == 'unevaluable' and 'independent rescore mismatch' in result['error']


def test_launcher_exactly_six_workers_single_numba_thread(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, 'validate_preparation', lambda _: {'preflight_path': 'unused'})
    monkeypatch.setattr(run, 'check_launch_resources', lambda *args: {})
    monkeypatch.setattr(run, 'isolation', lambda _: {'passed': True})
    calls = []
    def child(command: list[str], **kwargs: Any) -> None:
        assert kwargs['env']['NUMBA_NUM_THREADS'] == '1'
        assert kwargs['check'] is True
        calls.append(command)
    monkeypatch.setattr('experiments.run_fr_p001.subprocess.run', child)
    original = ThreadPoolExecutor
    def executor(*, max_workers: int) -> Any:
        assert max_workers == 6
        return original(max_workers=max_workers)
    monkeypatch.setattr(run, 'ThreadPoolExecutor', executor)
    run.launch(tmp_path)
    assert len(calls) == 18
    assert {(int(c[c.index('--pair') + 1]), c[c.index('--arm') + 1]) for c in calls} == {
        (i, arm) for i in range(9) for arm in ('witness', 'shuffle')}
