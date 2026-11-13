"""Controller guards; fake process results are never biological qualification."""
from pathlib import Path
import sys
import subprocess

import pytest

from experiments.stringmol import admission_workflow as w, admission_design as d
from experiments.stringmol import conservation_workflow as c
from experiments.stringmol.configure_control import HOST


def test_fixed_development_inputs() -> None:
    initial, coords = w.expected_initial()
    assert len(coords) == len(set(coords.values())) == len(initial['buffers']) == 140
    assert initial['pool'] == [0]*33 and initial['molecular'] == initial['total']
    assert all(bytes.fromhex(value).split(b'\0', 1)[0] == HOST.encode() for value in initial['buffers'].values())
    assert w.DEV_SEED not in d.SEEDS and w.WORKERS == 6
    assert len(w.ARMS) == 6 and w.NATIVE_TIMEOUT == 600 and w.ANALYSIS_TIMEOUT == 1800


@pytest.mark.parametrize('schedule', list(d.Schedule))
@pytest.mark.parametrize('policy', list(d.Admission))
def test_environment_is_explicit_and_observer_only(schedule: d.Schedule, policy: d.Admission) -> None:
    observed = w.environment(schedule, policy, 'observed')
    off = w.environment(schedule, policy, 'off')
    assert observed | {'STRINGMOL_ADMISSION_LOG': '0'} == off
    assert w.environment(schedule, policy, 'repeat') == observed
    assert observed['STRINGMOL_SOURCE_DISPOSITION'] == 'RETAIN'
    assert observed['STRINGMOL_POOL_AMOUNT'] == '0'
    if policy is d.Admission.NATIVE:
        baseline = w.environment(schedule, policy, 'baseline')
        assert baseline == off | {'STRINGMOL_ADMISSION': '0'}
    else:
        with pytest.raises(ValueError): w.environment(schedule, policy, 'baseline')


@pytest.mark.parametrize('mode', ['success', 'stderr', 'failure', 'timeout', 'missing', 'existing'])
def test_execution_attempt_receipts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    monkeypatch.setattr(w, 'storage', lambda *args, **kwargs: None)
    control, raw = tmp_path/'controls', tmp_path/'raw'
    control.mkdir(); raw.mkdir()
    directory = raw/'attempt'
    script = "print('FINISHED smspatial')"
    if mode == 'stderr': script += "; import sys; print('bad', file=sys.stderr)"
    if mode == 'failure': script += '; raise SystemExit(7)'
    if mode == 'timeout':
        monkeypatch.setattr(w, 'NATIVE_TIMEOUT', .05)
        script = 'import time; time.sleep(1)'
    if mode == 'existing':
        directory.mkdir(); (directory/'preserved.txt').write_text('untouched')
    command = [sys.executable, '-c', script] if mode != 'missing' else [str(tmp_path/'absent-binary')]
    job = {'key': mode, 'directory': str(directory), 'config': 'fixture\n', 'command': command, 'environment': c.ENV}
    result = w.execute_one(job, control, raw)
    assert result['success'] is (mode == 'success')
    assert c.read(control/'executions'/f'{mode}.json') == result
    assert result['execution_inventory_seconds'] >= result['native_seconds'] >= 0
    if mode == 'existing':
        assert (directory/'preserved.txt').read_text() == 'untouched'
        assert result['files'] == {} and 'FileExistsError' in result['error']
    else:
        assert result['files'] == c.inventory(directory)
    if mode == 'timeout': assert result['error'] == 'native timeout' and result['exit_status'] is None


def test_scientific_parity_exclusions_are_exact(tmp_path: Path) -> None:
    names = ['material_events002.csv', *w.NEW_LOGS, 'final_rng.txt']
    for name in names: (tmp_path/name).write_text('test\n')
    assert set(w.scientific_files(tmp_path, observer=True)) == set(names)
    assert set(w.scientific_files(tmp_path, observer=False)) == {'material_events002.csv', 'final_rng.txt'}


def test_failed_execution_cannot_be_replayed_as_success(tmp_path: Path) -> None:
    output = tmp_path/'result.json'
    with pytest.raises(ValueError, match='failed native execution'):
        w.analyze_job({}, tmp_path/'matrix', output, {}, 1)
    assert not output.exists()


def test_storage_does_not_allow_internal_fallback(tmp_path: Path) -> None:
    with pytest.raises(ValueError): w.storage(tmp_path/'controls', tmp_path/'raw')


@pytest.mark.parametrize('suffix', ['json', 'stdout', 'stderr'])
def test_command_evidence_never_overwrites_or_launches(tmp_path: Path, suffix: str) -> None:
    existing = tmp_path/f'step.{suffix}'
    existing.write_bytes(b'preserve exactly\n'); existing.chmod(0o444)
    marker = tmp_path/'launched'
    with pytest.raises(FileExistsError):
        w.checked([sys.executable, '-c', f'from pathlib import Path; Path({str(marker)!r}).touch()'], tmp_path, 'step')
    assert existing.read_bytes() == b'preserve exactly\n' and not marker.exists()


def test_command_receipt_and_analysis_are_separate(tmp_path: Path) -> None:
    output = tmp_path/'analysis.json'
    script = f'from pathlib import Path; Path({str(output)!r}).open("x").write(\'{{"integrity": true}}\')'
    w.checked([sys.executable, '-c', script], tmp_path, 'analysis-process')
    assert c.read(output) == {'integrity': True}
    assert c.read(tmp_path/'analysis-process.json')['exit_code'] == 0


def test_child_cannot_publish_over_reserved_command_receipt(tmp_path: Path) -> None:
    script = 'from pathlib import Path; Path("collision.json").open("x").write("scientific result")'
    with pytest.raises(RuntimeError, match='FileExistsError'):
        w.checked([sys.executable, '-c', script], tmp_path, 'collision')
    assert c.read(tmp_path/'collision.json')['exit_code'] != 0


def test_command_timeout_keeps_partial_logs_and_receipt(tmp_path: Path) -> None:
    script = 'import time; print("before timeout", flush=True); time.sleep(3)'
    with pytest.raises(subprocess.TimeoutExpired):
        w.checked([sys.executable, '-c', script], tmp_path, 'timeout', timeout=1)
    assert (tmp_path/'timeout.stdout').read_text() == 'before timeout\n'
    receipt = c.read(tmp_path/'timeout.json')
    assert receipt['timed_out'] is True and receipt['exit_code'] is None
