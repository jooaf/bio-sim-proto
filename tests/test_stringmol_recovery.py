"""Infrastructure recovery must not alter biology, drop outcomes, or resume assays."""
from __future__ import annotations

from copy import deepcopy
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from experiments.stringmol import (
    recover_retirement as r, retirement_workflow as w,
    analyze_retirement as ar, conservation_workflow as c,
)


def test_original_gate_and_matrix_unchanged() -> None:
    assert w.protocol_pin()['sha256'] == w.PROTOCOL_SHA256
    assert len(ar.MATRIX) == len(set(ar.MATRIX)) == 80
    assert r.WORKERS == 6
    assert ar.SEEDS == list(range(202628000, 202628020))
    assert ar.outcomes([], [])['branch'] == 1
    assert ar.outcomes([], [])['run_denominator'] == 80


def inputs(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    new = w.run_input(tmp_path / 'native', tmp_path / 'run', ar.SEEDS[0], ar.ARMS[0])
    raw = w.custom_config(new, tmp_path / 'native')
    old = deepcopy(new)
    old['bytes_hex'] = raw.replace(str(tmp_path / 'native'), '/old/source').encode().hex()
    return old, new, raw


def test_only_submat_path_may_change(tmp_path: Path) -> None:
    old, new, raw = inputs(tmp_path)
    r.compare_inputs(old, new, raw)
    for before, after in [('MUTATE 0\n', 'MUTATE 0.1\n'), ('5000', '5001'), ('202628000', '202628001')]:
        assert before in raw
        with pytest.raises(ValueError, match='config'):
            r.compare_inputs(old, new, raw.replace(before, after))


@pytest.mark.parametrize('key', ['condition', 'seed', 'expected_initial', 'initial_material', 'environment', 'route'])
def test_changed_scientific_input_rejected(tmp_path: Path, key: str) -> None:
    old, new, raw = inputs(tmp_path)
    changed = deepcopy(new)
    changed[key] = 'tampered'
    with pytest.raises(ValueError, match='scientific input'):
        r.compare_inputs(old, changed, raw)


@pytest.mark.parametrize('raw', ['', 'SUBMAT a\nSUBMAT b\n', ' SUBMAT a\n'])
def test_submat_requires_exactly_one_field(raw: str) -> None:
    with pytest.raises(ValueError, match='exactly one'):
        r.normalized_config(raw)


def test_snapshot_tampering_and_symlinks(tmp_path: Path) -> None:
    path = tmp_path / 'evidence.json'
    path.write_text('{}')
    saved = r.snapshot([tmp_path])
    r.check_records(saved)
    path.write_text('{"changed": true}')
    with pytest.raises(ValueError, match='evidence changed'):
        r.check_records(saved)
    (tmp_path / 'alias').symlink_to(path)
    with pytest.raises(ValueError, match='symlink'):
        r.snapshot([tmp_path])


def test_pin_rejects_changed_original(tmp_path: Path) -> None:
    path = tmp_path / 'old.json'
    path.write_text('{}')
    with pytest.raises(ValueError, match='pin mismatch'):
        r.pinned(path, r.OLD_PREPARATION)


def setup_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, list[tuple[str, int]]]:
    manifest = tmp_path / 'preparation.json'
    manifest.write_text('{}')
    data = {'runs': [{'condition': arm, 'seed': seed} for arm, seed in ar.MATRIX],
            'source': {'commit': 'a' * 40}, 'recovery_kind': 'artifact failure, whole matrix'}
    monkeypatch.setattr(r, 'verify_preparation', lambda _: data)
    monkeypatch.setattr(w, 'remote_target', lambda: {})
    monkeypatch.setattr(w, 'observe_remote', lambda *_: {'observed_revision': 'a' * 40})
    monkeypatch.setattr(shutil, 'disk_usage', lambda _: SimpleNamespace(free=r.MIN_FREE + 1))
    calls: list[tuple[str, int]] = []

    def execute(entry: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
        calls.append((entry['condition'], entry['seed']))
        return {**entry, 'exit_status': 0, 'files': {}, 'input_manifest': record}

    monkeypatch.setattr(r, 'execute_one', execute)
    return manifest, calls


def test_whole_matrix_once_and_no_resume(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest, calls = setup_matrix(tmp_path, monkeypatch)
    r.run_matrix(manifest)
    assert sorted(calls) == sorted(ar.MATRIX)
    receipts = c.read(tmp_path / 'campaign-results.json')
    assert [(item['condition'], item['seed']) for item in receipts] == ar.MATRIX
    assert len(receipts) == 80
    with pytest.raises(ValueError, match='no resume'):
        r.run_matrix(manifest)
    assert len(calls) == 80


def test_resource_failure_prevents_any_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest, calls = setup_matrix(tmp_path, monkeypatch)
    monkeypatch.setattr(shutil, 'disk_usage', lambda _: SimpleNamespace(free=r.MIN_FREE - 1))
    with pytest.raises(ValueError, match='headroom'):
        r.run_matrix(manifest)
    assert calls == []
    assert not (tmp_path / 'launch.json').exists()


def test_execution_error_is_retained_not_retried(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / 'runs' / 'IMMEDIATE_RETAIN' / '202628000'
    entry = {'condition': 'IMMEDIATE_RETAIN', 'seed': 202628000, 'directory': str(directory),
             'command': ['binary'], 'config': 'config', 'environment': {}}
    calls = []
    monkeypatch.setattr(shutil, 'disk_usage', lambda _: SimpleNamespace(free=r.MIN_FREE + 1))

    def fail(*args: Any) -> None:
        calls.append(args)
        raise OSError('disk failure')

    monkeypatch.setattr(c, 'execute', fail)
    result = r.execute_one(entry, {'sha256': 'manifest'})
    assert len(calls) == 1
    assert 'disk failure' in result['exit_status']
    assert result == c.read(directory.with_suffix('.inventory.json'))
    assert result['seed'] == entry['seed']


def test_receipt_identity_and_raw_corruption(tmp_path: Path) -> None:
    directory = tmp_path / '123'
    directory.mkdir()
    raw = directory / 'events.csv'
    raw.write_text('original')
    entry = {'condition': 'arm', 'seed': 123}
    receipt = {**entry, 'input_manifest': {'sha256': 'm'}, 'files': c.inventory(directory)}
    c.seal(directory.with_suffix('.inventory.json'), receipt)
    r.verify_receipt(entry, receipt, directory, {'sha256': 'm'})
    with pytest.raises(ValueError, match='identity'):
        r.verify_receipt({**entry, 'seed': 124}, receipt, directory, {'sha256': 'm'})
    raw.write_text('changed')
    with pytest.raises(ValueError, match='inventory'):
        r.verify_receipt(entry, receipt, directory, {'sha256': 'm'})


def test_analysis_retains_failed_run_in_denominator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_path / 'preparation.json'
    manifest.write_text('{}')
    commit = 'a' * 40
    source = {'commit': commit}
    entries = [{'condition': arm, 'seed': seed, 'directory': str(tmp_path / arm / str(seed)),
                'expected_initial': []} for arm, seed in ar.MATRIX]
    monkeypatch.setattr(r, 'verify_preparation', lambda _: {'source': source, 'runs': entries})
    target = {'remote': 'origin', 'url': 'example', 'ref': 'refs/heads/main'}
    monkeypatch.setattr(w, 'remote_target', lambda: target)
    raw = f'{commit}\trefs/heads/main\n'.encode()
    remote = {**target, 'observed_revision': commit, 'stdout_hex': raw.hex(), 'stdout_sha256': c.digest(raw),
              'command': ['git', 'ls-remote', '--exit-code', '--refs', 'example', 'refs/heads/main'], 'environment': c.ENV}
    c.seal(tmp_path / 'launch.json', {'protocol': r.PROTOCOL, 'input_manifest': c.record(manifest),
                                     'source': source, 'workers': 6, 'remote': remote})
    c.seal(tmp_path / 'campaign-results.json', [dict(exit_status=0, files={}) for _ in entries])
    calls = []

    def receipt(entry: dict[str, Any], *_: Any) -> None:
        calls.append((entry['condition'], entry['seed']))
        if (entry['condition'], entry['seed']) == ar.MATRIX[0]:
            raise ValueError('synthetic corrupt raw artifact')

    monkeypatch.setattr(r, 'verify_receipt', receipt)
    monkeypatch.setattr(ar, 'output_names', lambda _: set())
    summary = {**dict(zip(ar.ENDPOINTS, ar.THRESHOLDS, strict=True)), 'boundary_errors': 0,
               'fatal_enforcement_errors': 0, 'zero_residual': True, 'end_timestep': 5000,
               'end_arrays': {'pool': [0] * 33, 'waste': [0] * 33}, 'retirements': 100, 'retirement_eligible': 100}
    monkeypatch.setattr(ar, 'analyze_run', lambda *args, **kwargs: summary)
    result = r.analyze(manifest)
    assert calls == ar.MATRIX
    assert len(result['runs']) == 79 and len(result['failures']) == 1
    assert result['run_denominator'] == 80 and result['branch'] == 1
    assert not result['integrity']
