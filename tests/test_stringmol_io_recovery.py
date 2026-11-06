"""Direct raw storage and bounded fallback cannot select or omit scientific runs."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from experiments.stringmol import (recover_retirement_io as m, conservation_workflow as c,
                                  analyze_retirement as ar, diagnose_retirement_runtime as d)


def profile_report() -> dict[str, Any]:
    return {'qualified_workers': 6, 'profiles': {
        name: [{'index': index, 'exit_status': 0, 'parity': True, 'wall_seconds': 18} for index in range(workers)]
        for name, workers, _ in d.PROFILES}}


def test_qualified_worker_rule_and_complete_development_denominator() -> None:
    report = profile_report()
    assert m.qualified_workers(report) == 6
    report['profiles']['exfat-six'].pop()
    with pytest.raises(ValueError, match='worker set'):
        m.qualified_workers(report)
    report = profile_report()
    report['profiles']['exfat-six'][0]['wall_seconds'] = 301
    with pytest.raises(ValueError, match='two-worker'):
        m.qualified_workers(report)
    report['profiles']['exfat-two'] = deepcopy(report['profiles']['exfat-six'][:2])
    report['qualified_workers'] = 2
    assert m.qualified_workers(report) == 2
    report['profiles']['posix-serial'][0]['parity'] = False
    with pytest.raises(ValueError, match='changed successful'):
        m.qualified_workers(report)


def test_operational_ladder_is_fixed_and_bounded() -> None:
    assert m.policy(2, 6) == (6, 600)
    assert m.policy(2, 2) == (2, 600)
    assert m.policy(3, 6) == m.policy(3, 2) == (1, 3600)
    for attempt, workers in [(1, 6), (4, 6), (2, 5), (3, 0)]:
        with pytest.raises(ValueError):
            m.policy(attempt, workers)
    layout = m.Layout.create(2)
    assert layout.raw('IMMEDIATE_RETAIN', 202628000).is_relative_to(m.STORE)
    assert layout.receipt('IMMEDIATE_RETAIN', 202628000).is_relative_to(m.IMAGE)
    assert not layout.receipt('IMMEDIATE_RETAIN', 202628000).is_relative_to(layout.portable)


def timeout_result() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    failed = ar.MATRIX[0]
    receipts = [{'condition': arm, 'seed': seed, 'exit_status': 'timeout' if (arm, seed) == failed else 0} for arm, seed in ar.MATRIX]
    result = {'branch': 1, 'integrity': False,
              'failures': [{'condition': failed[0], 'seed': failed[1], 'category': m.Failure.TIMEOUT.value}],
              'verified_ids': [f'{arm}:{seed}' for arm, seed in ar.MATRIX if (arm, seed) != failed]}
    return result, receipts


def test_only_complete_timeout_failure_authorizes_full_serial_recovery() -> None:
    result, receipts = timeout_result()
    assert m.timeout_only(result, receipts)
    assert not m.timeout_only(result, receipts[:-1])
    assert not m.timeout_only({**result, 'branch': 2, 'integrity': True}, receipts)
    assert not m.timeout_only({**result, 'verified_ids': []}, receipts)
    assert not m.timeout_only({**result, 'verified_ids': result['verified_ids'] * 2}, receipts)
    result['failures'][0]['category'] = m.Failure.INTEGRITY.value
    assert not m.timeout_only(result, receipts)
    result, receipts = timeout_result()
    receipts[1]['exit_status'] = 'launch failure'
    assert not m.timeout_only(result, receipts)


def native_fixture(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any], Path, dict[str, Any]]:
    raw = tmp_path / 'raw'; raw.mkdir()
    (raw / 'events.csv').write_text('fixed native bytes')
    entry = {'condition': ar.ARMS[0], 'seed': ar.SEEDS[0], 'directory': str(raw), 'expected_initial': []}
    record = {'sha256': 'manifest'}
    receipt = {'condition': entry['condition'], 'seed': entry['seed'], 'input_manifest': record, 'exit_status': 0, 'files': c.inventory(raw)}
    receipt_path = tmp_path / 'receipt.json'
    return entry, receipt, receipt_path, record


def test_timeout_is_classified_only_after_raw_receipt_verification(tmp_path: Path) -> None:
    entry, receipt, path, record = native_fixture(tmp_path)
    receipt['exit_status'] = 'timeout'
    c.seal(path, receipt)
    result, failure = m.analyze_one((entry, receipt, str(path), record, None))
    assert result is None and failure is not None and failure['category'] == m.Failure.TIMEOUT.value
    (Path(entry['directory']) / 'events.csv').write_text('corrupt')
    _, failure = m.analyze_one((entry, receipt, str(path), record, None))
    assert failure is not None and failure['category'] == m.Failure.INTEGRITY.value


def test_completed_output_drift_blocks_recovery_inference(tmp_path: Path) -> None:
    entry, receipt, path, record = native_fixture(tmp_path)
    c.seal(path, receipt)
    _, failure = m.analyze_one((entry, receipt, str(path), record, {}))
    assert failure is not None and failure['category'] == m.Failure.INTEGRITY.value
    assert 'across operational recovery' in failure['error']


def test_native_execution_records_timeout_without_replacement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(m, 'mounts', lambda: None)
    monkeypatch.setattr(shutil, 'disk_usage', lambda _: SimpleNamespace(free=1000 * 1024**3))
    entry = {'directory': str(tmp_path / 'raw'), 'command': [sys.executable, '-c', 'import time; time.sleep(60)'], 'environment': c.ENV}
    result = m.execute_native(entry, 0)
    assert result['exit_status'] == 'timeout' and result['timeout_seconds'] == 0
    assert set(result['files']) == {'stdout.txt', 'stderr.txt'}
    with pytest.raises(FileExistsError):
        m.execute_native(entry, 0)


def test_exported_layout_never_falls_back_to_internal_raw_storage() -> None:
    for attempt in (2, 3):
        layout = m.Layout.create(attempt)
        assert str(layout.portable).startswith('/run/media/jojo/Elements/')
        assert layout.raw('IMMEDIATE_RETAIN', 202628000).parent.parent == layout.portable / 'runs'
