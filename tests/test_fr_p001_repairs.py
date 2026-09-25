"""Repair policy, semantic tampering, process admission, and destination gates."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import multiprocessing as mp
from pathlib import Path
import queue
import shutil
import sqlite3
from typing import Any

import numpy as np
import pytest

from experiments import fr_p001 as f
from experiments import run_fr_p001 as run
from experiments import analyze_fr_p001 as analysis
from experiments.fr_i002_gate import State


def synthetic_prepared(output: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Entirely synthetic complete inventory; no campaign source/input reads."""
    output.mkdir()
    monkeypatch.setattr(f, 'POPULATION', 4)
    monkeypatch.setattr(f, 'EPOCHS', (1,))
    monkeypatch.setattr(f, 'FINAL', (1,))
    def paired(w: f.U8, c: f.U8, index: int) -> tuple[f.U8, f.U8, Any, f.U8]:
        return np.tile(w, (4, 1)), np.tile(c, (4, 1)), np.arange(4, dtype=np.uint32), np.ones((4, 64), dtype=np.uint8)
    monkeypatch.setattr(run, 'paired', paired)
    version: dict[str, Any] = {'artifact_version': f.ARTIFACT_VERSION, 'output_version': 'synthetic-v2',
               'repair_policy': f.REPAIR_POLICY, 'run_pins': f.run_pins()}
    f.save_sources(output, version['run_pins'])
    f.atomic_json(output / 'version.json', version)
    pairs = []
    for index, seed in enumerate(f.SEEDS):
        w = np.arange(64, dtype=np.uint8)
        c = run.control(w, index)
        left, right, indices, labels = paired(w, c, index)
        p: dict[str, Any] = {'index': index, 'source_seed': seed, 'recipient_seed': 202619000 + index,
                             'witness_score': 64, 'shuffle_score': 0, 'arms': {}}
        for arm, data, target in (('witness', left, w), ('shuffle', right, c)):
            path = output / f'input_{index:02d}_{arm}.npz'
            pool = np.bincount(data.ravel(), minlength=256).astype(np.int64) * 16
            arrays = {'soup': data, 'labels': labels, 'indices': indices, 'pool': pool}
            np.savez_compressed(path, **arrays)
            p['arms'][arm] = {'path': path.name, 'sha256': f.sha(path), 'target_hex': target.tobytes().hex(),
                             **{k + '_sha256': f.digest(v.tobytes()) for k, v in arrays.items()}}
        pairs.append(p)
    prepared = {'campaign': 'FR-P001', **version, 'epochs': [1], 'workers': 6, 'numba_num_threads': 1,
                'preflight': {'passed': True, 'run_pins': version['run_pins']}, 'pairs': pairs}
    f.atomic_json(output / 'preparation.json', prepared)
    (output / 'preparation.sha256').write_text(f.sha(output / 'preparation.json') + '\n')
    f.atomic_json(output / 'isolation.json', {'passed': True, 'run_pins': version['run_pins']})
    for index, p in enumerate(pairs):
        for arm in ('witness', 'shuffle'):
            directory = output / 'runs' / f'{index:02d}_{arm}'
            directory.mkdir(parents=True)
            item = p['arms'][arm]
            with np.load(output / item['path'], allow_pickle=False) as initial:
                state = State.create(initial['soup'], initial['labels'], initial['pool'])
                pool = initial['pool']
                totals = pool + np.bincount(initial['soup'].ravel(), minlength=256)
            db = f.database(directory / 'run.sqlite')
            record = f.observe(db, directory, state, 1, np.zeros(9, dtype=np.int64), bytes.fromhex(item['target_hex']), pool, totals)
            db.close()
            binding = {'preparation_sha256': f.sha(output / 'preparation.json'), 'index': index, 'arm': arm}
            f.atomic_json(directory / 'binding.json', binding)
            f.atomic_json(directory / 'complete.json', {**binding, 'epochs': [1],
                'database_sha256': f.sha(directory / 'run.sqlite'),
                'soup_sha256': record['soup_sha256'], 'labels_sha256': record['labels_sha256']})
    return prepared


def shadow_sources(directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in f.run_pins() | f.analysis_pins():
        dest = directory / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((f.ROOT / name).read_bytes())
    (directory / '.git').symlink_to(f.ROOT / '.git', target_is_directory=True)
    monkeypatch.setattr(f, 'ROOT', directory)


def test_analyzer_only_repair_preserves_preparation_and_completed_analysis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / 'prepared'
    synthetic_prepared(output, monkeypatch)
    before = f.sha(output / 'preparation.json')
    run_identity = f.run_pins()
    first = analysis.analyze(output, tmp_path / 'analysis-v1')
    assert first['gates']['integrity'], first
    shadow_sources(tmp_path / 'sources', monkeypatch)
    path = f.ROOT / 'experiments/analyze_fr_p001.py'
    path.write_bytes(path.read_bytes() + b'\n# analyzer-only repair identity fixture\n')
    assert f.run_pins() == run_identity
    assert run.validate_preparation(output)['run_pins'] == run_identity
    second = analysis.analyze(output, tmp_path / 'analysis-v2')
    assert second['gates']['integrity'], second
    assert first['analysis_provenance']['analyzer_pins'] != second['analysis_provenance']['analyzer_pins']
    assert second['analysis_provenance']['validation'] == 'passed'
    assert f.sha(output / 'preparation.json') == before
    with pytest.raises(ValueError, match='fresh report'):
        analysis.analyze(output, tmp_path / 'analysis-v1')


@pytest.mark.parametrize('changed', ('experiments/fr_p001.py', 'experiments/run_fr_p001.py', 'experiments/fr_i002_gate.py'))
def test_run_repair_rejects_preparation_and_resume(changed: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / 'prepared'
    synthetic_prepared(output, monkeypatch)
    shadow_sources(tmp_path / 'sources', monkeypatch)
    path = f.ROOT / changed
    path.write_bytes(path.read_bytes() + b'\n# changed run implementation\n')
    monkeypatch.setenv('NUMBA_NUM_THREADS', '1')
    with pytest.raises(ValueError, match='fresh output version'):
        run.validate_preparation(output)
    with pytest.raises(ValueError, match='fresh output version'):
        run.run_one(output, 0, 'witness')


def test_frozen_source_copy_tampering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / 'prepared'
    synthetic_prepared(output, monkeypatch)
    path = output / 'frozen_sources/experiments/fr_p001.py'
    path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='frozen source copy mismatch'):
        run.validate_preparation(output)


def forge_record(directory: Path, damage: str) -> None:
    db = sqlite3.connect(directory / 'run.sqlite')
    record = json.loads(db.execute('SELECT manifest FROM callbacks WHERE epoch=1').fetchone()[0])
    path = directory / record['snapshot']
    with np.load(path, allow_pickle=False) as saved:
        arrays = {k: saved[k] for k in saved.files}
    if damage == 'scarcity':
        arrays['metrics'][2] = 1
    elif damage == 'friction':
        arrays['metrics'][3] = 1
    elif damage == 'cross_total':
        arrays['metrics'][7] = 1
    elif damage == 'cross_blocked':
        arrays['metrics'][8] = 1
    elif damage == 'successful_writes':
        arrays['withdrawals'][0] = arrays['returns'][0] = arrays['counter'][0] = 1
    elif damage == 'cross_symbol':
        arrays['withdrawals'][0] = arrays['returns'][0] = arrays['counter'][0] = 1
        arrays['cross_a_to_b'][1] = 1
        arrays['metrics'][0] = arrays['metrics'][1] = arrays['metrics'][7] = 1
    elif damage == 'steps':
        arrays['metrics'][1] = 1
    else:
        raise AssertionError(damage)
    np.savez_compressed(path, **arrays)
    record['snapshot_sha256'] = f.sha(path)
    record['metrics'] = dict(zip(f.METRICS, map(int, arrays['metrics'])))
    record['ledgers'] = {k: arrays[k].tolist() for k in record['ledgers']}
    db.execute('UPDATE callbacks SET manifest=? WHERE epoch=1', (json.dumps(record),))
    db.commit()
    db.close()
    complete = json.loads((directory / 'complete.json').read_text())
    complete['database_sha256'] = f.sha(directory / 'run.sqlite')
    f.atomic_json(directory / 'complete.json', complete)


@pytest.mark.parametrize('damage', ('scarcity', 'friction', 'cross_total', 'cross_blocked', 'successful_writes', 'cross_symbol', 'steps'))
def test_recomputed_checksums_cannot_hide_bad_mechanics(damage: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / 'prepared'
    prepared = synthetic_prepared(output, monkeypatch)
    directory = output / 'runs/00_witness'
    forge_record(directory, damage)
    db = sqlite3.connect(directory / 'run.sqlite')
    record = json.loads(db.execute('SELECT manifest FROM callbacks').fetchone()[0])
    item = prepared['pairs'][0]['arms']['witness']
    with np.load(output / item['path'], allow_pickle=False) as initial:
        pool = initial['pool']
        totals = pool + np.bincount(initial['soup'].ravel(), minlength=256)
    with pytest.raises(ValueError, match='mechanics'):
        f.verify_callback(db, directory, record, bytes.fromhex(item['target_hex']), pool, totals)
    state, metrics = f.load_snapshot(directory / record['snapshot'])
    with pytest.raises(ValueError, match='mechanics'):
        f.observe(db, directory, state, 2, metrics, bytes.fromhex(item['target_hex']), pool, totals)
    db.close()
    monkeypatch.setenv('NUMBA_NUM_THREADS', '1')
    monkeypatch.setattr(run, 'check_launch_resources', lambda *args: {})
    with pytest.raises(ValueError, match='mechanics'):
        run.run_one(output, 0, 'witness')
    result = analysis.analyze(output, tmp_path / 'report')
    assert result['status'] == 'unevaluable' and 'mechanics' in result['error']


def process_worker(output: str, entered: Any, release: Any, active: Any, peak: Any, guard: Any, attempted: Any) -> None:
    def admitted(output: Path, index: int, arm: str) -> None:
        with guard:
            active.value += 1
            peak.value = max(peak.value, active.value)
        entered.put('standalone')
        try:
            if not release.wait(30):
                raise RuntimeError('test timed out')
        finally:
            with guard:
                active.value -= 1
    run._run_one_admitted = admitted
    attempted.set()
    run.run_one(Path(output), 8, 'shuffle')


def test_shared_admission_across_launcher_and_standalone_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = mp.get_context('spawn')
    entered, release, attempted = ctx.Queue(), ctx.Event(), ctx.Event()
    active, peak, guard = ctx.Value('i', 0), ctx.Value('i', 0), ctx.Lock()
    monkeypatch.setattr(run, 'validate_preparation', lambda _: {})
    monkeypatch.setattr(run, 'check_launch_resources', lambda *args: {})
    monkeypatch.setattr(run, 'publish_isolation', lambda _: {})
    def admitted(output: Path, index: int, arm: str) -> None:
        with guard:
            active.value += 1
            peak.value = max(peak.value, active.value)
        entered.put('launcher')
        try:
            assert release.wait(30)
        finally:
            with guard:
                active.value -= 1
    monkeypatch.setattr(run, '_run_one_admitted', admitted)
    def child(command: list[str], **kwargs: Any) -> None:
        run.run_one(tmp_path, int(command[command.index('--pair') + 1]), command[-1])
    monkeypatch.setattr('experiments.run_fr_p001.subprocess.run', child)
    standalone = ctx.Process(target=process_worker, args=(str(tmp_path), entered, release, active, peak, guard, attempted))
    with ThreadPoolExecutor(max_workers=1) as outer:
        launched = outer.submit(run.launch, tmp_path)
        try:
            assert [entered.get(timeout=20) for _ in range(6)] == ['launcher'] * 6
            standalone.start()
            assert attempted.wait(20)
            with pytest.raises(queue.Empty):
                entered.get(timeout=2)
            assert active.value == peak.value == 6
            # A competing launcher cannot even validate or republish isolation.
            with pytest.raises(BlockingIOError):
                run.launch(tmp_path)
        finally:
            release.set()
        launched.result(timeout=30)
        standalone.join(timeout=30)
    assert standalone.exitcode == 0 and peak.value == 6 and active.value == 0
    entered.close()


def test_coordination_precedes_validation_and_isolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('publication/validation reached while workers active')
    monkeypatch.setattr(run, 'validate_preparation', forbidden)
    with f.lock(tmp_path / '.campaign.lock', shared=True):
        with pytest.raises(BlockingIOError):
            run.launch(tmp_path)
        with pytest.raises(BlockingIOError):
            run.validate_isolation(tmp_path)
    assert not (tmp_path / 'isolation.json').exists()


@pytest.mark.parametrize('entry', ('launch', 'run-one'))
@pytest.mark.parametrize('resource', ('disk', 'ram'))
def test_destination_resource_gate_before_simulation(entry: str, resource: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output, preflight = tmp_path / 'campaign', tmp_path / 'different-device/preflight.json'
    output.mkdir()
    evidence = {'elapsed_seconds': 1.0, 'max_rss_bytes': 1000}
    prepared = {'preflight_path': str(preflight), 'preflight': evidence}
    monkeypatch.setattr(run, 'validate_preparation', lambda _: prepared)
    monkeypatch.setattr(run, 'validate_preflight', lambda _: evidence)
    paths = []
    def usage(path: Path) -> Any:
        paths.append(path)
        assert path == output.resolve()
        return type('Usage', (), {'free': 0 if resource == 'disk' else f.DISK_REQUIRED})()
    monkeypatch.setattr('experiments.fr_p001.shutil.disk_usage', usage)
    monkeypatch.setattr(f, 'available_ram', lambda: 0 if resource == 'ram' else 64 * 2**30)
    monkeypatch.setenv('NUMBA_NUM_THREADS', '1')
    with pytest.raises(ValueError, match='campaign output resources'):
        if entry == 'launch':
            run.launch(output)
        else:
            run.run_one(output, 0, 'witness')
    assert paths == [output.resolve()]
    assert not (output / 'runs').exists() and not (output / 'isolation.json').exists()


def test_new_version_cannot_reuse_completed_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / 'old'
    prepared = synthetic_prepared(output, monkeypatch)
    fresh = tmp_path / 'fresh'
    shutil.copytree(output, fresh)
    prepared['output_version'] = 'repair-v3'
    version = {k: prepared[k] for k in ('artifact_version', 'output_version', 'repair_policy', 'run_pins')}
    f.atomic_json(fresh / 'version.json', version)
    f.atomic_json(fresh / 'preparation.json', prepared)
    (fresh / 'preparation.sha256').write_text(f.sha(fresh / 'preparation.json'))
    monkeypatch.setenv('NUMBA_NUM_THREADS', '1')
    monkeypatch.setattr(run, 'check_launch_resources', lambda *args: {})
    with pytest.raises(ValueError, match='run input binding mismatch'):
        run.run_one(fresh, 0, 'witness')


def test_prepare_cannot_repair_existing_version_in_place(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / 'prepared'
    synthetic_prepared(output, monkeypatch)
    monkeypatch.setattr(run, 'validate_preflight', lambda _: {'elapsed_seconds': 1, 'max_rss_bytes': 1000})
    monkeypatch.setattr(f, 'resources', lambda *args: {'passed': True})
    before = f.sha(output / 'preparation.json')
    with pytest.raises(ValueError, match='fresh output version'):
        run.prepare(output, tmp_path, tmp_path, tmp_path / 'unused', output_version='different-version')
    assert f.sha(output / 'preparation.json') == before
