"""Future-controller adversarial tests. Every native command is mocked."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest

from experiments.stringmol import xp001 as x, xp001_population as p, xp001_finish as f
from experiments.stringmol import xp001_provenance as provenance
from experiments.stringmol.xp001_safety import allocated, authorization, object_from

REAL_PREFLIGHT = x.preflight


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    evidence = tmp_path / 'e'; evidence.mkdir()
    raw = tmp_path / 'raw'; raw.mkdir()
    source = tmp_path / 'source'; source.mkdir()
    reports = source / 'reports'; reports.mkdir()
    for name in ('development_plan', 'reaction_recovery_plan', 'population_launch'):
        (reports / f'sm_xp001_{name}.md').write_text(name)
    modules = source / 'experiments/stringmol'; modules.mkdir(parents=True)
    (modules / 'source.py').write_text('source snapshot')
    native = evidence / 'native-v2'; native.mkdir()
    (native / 'objects').mkdir()
    (native / 'objects/stringmol').write_text('MOCK binary; not executable')
    (native / 'reaction').write_text('MOCK reaction; not executable')
    (native / 'ALXII.mtx').write_text('qualified matrix')
    (native / 'fixture.cpp').write_text('fixture source')
    inputs = {'fixture.cpp': x.digest(native / 'fixture.cpp'), 'ALXII.mtx': x.digest(native / 'ALXII.mtx')}
    x.save(native / 'inputs.json', inputs)
    x.save(native / 'build.json', {'inputs': inputs, 'binary': x.digest(native / 'reaction'), 'matrix': x.digest(native / 'ALXII.mtx')})
    reactions = raw / 'reactions-v2'; reactions.mkdir()
    x.save(reactions / 'gate.json', {k: True for k in ('valid', 'deterministic', 'observation_isolation',
           'canonical_positive', 'candidate_nonproductive', 'population_authorized_by_reaction_gate')})
    monkeypatch.setattr(x, 'EVIDENCE', evidence)
    monkeypatch.setattr(x, 'RAW', raw)
    monkeypatch.setattr(x, 'ROOT', source)
    monkeypatch.setattr(p, 'CONTROL', evidence / 'p001')
    monkeypatch.setattr(p, 'POP', raw / 'population-v1')
    monkeypatch.setattr(x, 'preflight', lambda: None)
    monkeypatch.setattr(subprocess, 'check_output', Mock(return_value='mock-source-commit'))
    # Fail the test if an unmocked process would escape.
    monkeypatch.setattr(subprocess, 'run', Mock(side_effect=AssertionError('unwanted subprocess')))
    return tmp_path


@pytest.mark.parametrize('target', ['matrix', 'build', 'gate', 'plan', 'source', 'config', 'binary', 'settings', 'founders'])
def test_drift_prevents_any_invocation(sandbox: Path, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    p.freeze()
    paths = {
        'matrix': x.EVIDENCE / 'native-v2/ALXII.mtx',
        'build': x.EVIDENCE / 'native-v2/build.json',
        'gate': x.RAW / 'reactions-v2/gate.json',
        'plan': x.ROOT / 'reports/sm_xp001_development_plan.md',
        'source': x.ROOT / 'experiments/stringmol/source.py',
        'config': p.CONTROL / '00.conf',
        'binary': x.EVIDENCE / 'native-v2/objects/stringmol',
        'settings': p.CONTROL / 'freeze.json',
        'founders': p.CONTROL / 'freeze.json',
    }
    path = paths[target]; path.chmod(0o644)
    if target in ('settings', 'founders'):
        value = json.loads(path.read_text())
        if target == 'settings':
            value['matrix'][0]['environment']['STRINGMOL_POOL_AMOUNT'] = '16'
        else:
            value['matrix'][0]['founders'][0]['sequence_hex'] = '42'
        path.write_text(json.dumps(value))
    else:
        path.write_text(path.read_text() + '\ndrift')
    invoke = Mock(return_value=0); monkeypatch.setattr(x, 'command', invoke)
    with pytest.raises(AssertionError, match='drift'):
        p.run()
    invoke.assert_not_called()
    assert not (p.CONTROL / 'launch.json').exists()


def test_legacy_readable_but_not_launchable(sandbox: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p.freeze()
    (p.CONTROL / 'bindings-v1.json').unlink()
    assert len(provenance.cases_from(object_from(p.CONTROL / 'freeze.json'))) == 12
    invoke = Mock(); monkeypatch.setattr(x, 'command', invoke)
    with pytest.raises(FileNotFoundError):
        p.run()
    invoke.assert_not_called()


@pytest.mark.parametrize('bad', [None, [], {'matrix': []}, {'matrix': [None] * 12}])
def test_malformed_preparation(tmp_path: Path, bad: object) -> None:
    path = tmp_path / 'bad.json'; path.write_text(json.dumps(bad))
    with pytest.raises((ValueError, KeyError)):
        provenance.cases_from(object_from(path))


def test_failed_reaction_gate_not_authorized(sandbox: Path) -> None:
    path = x.RAW / 'reactions-v2/gate.json'
    value = json.loads(path.read_text()); value['canonical_positive'] = False
    path.write_text(json.dumps(value))
    with pytest.raises(AssertionError, match='reaction gate'):
        p.freeze()
    assert not (p.CONTROL / 'bindings-v1.json').exists()


def test_each_execution_rechecks_and_launch_is_once_only(sandbox: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p.freeze()
    invoke = Mock(return_value=0)
    def drift(*args: object, **kwargs: object) -> int:
        invoke(*args, **kwargs)
        (x.EVIDENCE / 'native-v2/ALXII.mtx').write_text('drift after first invocation')
        return 0
    monkeypatch.setattr(x, 'command', drift)
    with pytest.raises(AssertionError, match='drift'):
        p.run()
    assert invoke.call_count == 1
    assert (p.CONTROL / 'execution-00.json').exists()
    assert (p.CONTROL / 'launch.json').exists()
    # Restoring an input never clears the consumed launch reservation.
    (x.EVIDENCE / 'native-v2/ALXII.mtx').write_text('qualified matrix')
    with pytest.raises(AssertionError, match='already reserved'):
        p.run()
    assert invoke.call_count == 1


@pytest.mark.parametrize('failure', [FileNotFoundError('missing'), PermissionError('denied'), subprocess.TimeoutExpired(['mock'], 1)])
def test_command_failure_receipt_and_exclusive_reservation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception) -> None:
    invoke = Mock(side_effect=failure); monkeypatch.setattr(subprocess, 'run', invoke)
    assert x.command(['mock'], tmp_path, 'native', overrides={'STRINGMOL_POOL_AMOUNT': '0'}) is None
    receipt = object_from(tmp_path / 'native.receipt.json')
    assert receipt['returncode'] is None and receipt['error']
    assert receipt['environment_overrides'] == {'STRINGMOL_POOL_AMOUNT': '0'}
    assert receipt['timeout'] == isinstance(failure, subprocess.TimeoutExpired)
    with pytest.raises(FileExistsError):
        x.command(['mock'], tmp_path, 'native')
    assert invoke.call_count == 1


def test_log_conflict_receipt_no_spawn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / 'native.stdout').write_text('preserved')
    invoke = Mock(); monkeypatch.setattr(subprocess, 'run', invoke)
    assert x.command(['mock'], tmp_path, 'native') is None
    assert object_from(tmp_path / 'native.receipt.json')['error']
    assert (tmp_path / 'native.stdout').read_text() == 'preserved'
    invoke.assert_not_called()


@pytest.mark.parametrize('posix,raw', [(4 * 1024**3, 1), (1, 25 * 1024**3)])
def test_quota_independent_of_headroom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, posix: int, raw: int) -> None:
    monkeypatch.setattr(x, 'EVIDENCE', tmp_path)
    monkeypatch.setattr(x, 'RAW', tmp_path / 'raw'); (tmp_path / 'raw').mkdir()
    monkeypatch.setattr(subprocess, 'check_output', Mock(return_value='/run/media/jojo/Elements /dev/sdc1 exfat\n/tmp/sm /run/media/jojo/Elements/bio-sim-results/stringmol-posix.ext4 fuse.ext4'))
    monkeypatch.setattr(shutil, 'disk_usage', Mock(return_value=shutil._ntuple_diskusage(100 * 1024**3, 0, 100 * 1024**3)))
    monkeypatch.setattr(x, 'allocated', lambda path: posix if path == tmp_path else raw)
    with pytest.raises(AssertionError, match='quota exhausted'):
        x.preflight()


def test_accounting_does_not_follow_links(tmp_path: Path) -> None:
    root = tmp_path / 'budget'; root.mkdir()
    outside = tmp_path / 'outside'; outside.mkdir()
    (outside / 'large').write_bytes(b'x' * 100000)
    (root / 'escape').symlink_to(outside, target_is_directory=True)
    (root / 'cycle').symlink_to(root, target_is_directory=True)
    assert 0 < allocated(root) < 100000


@pytest.mark.parametrize('kind', ['mount', 'posix', 'raw'])
def test_preflight_bad_mount_or_headroom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    monkeypatch.setattr(x, 'EVIDENCE', tmp_path)
    monkeypatch.setattr(x, 'RAW', tmp_path / 'raw-parent/raw')
    mounts = '/run/media/jojo/Elements /dev/sdc1 exfat\n/tmp/sm /run/media/jojo/Elements/bio-sim-results/stringmol-posix.ext4 fuse.ext4'
    monkeypatch.setattr(subprocess, 'check_output', Mock(return_value='' if kind == 'mount' else mounts))
    monkeypatch.setattr(shutil, 'disk_usage', lambda path: shutil._ntuple_diskusage(100 * 1024**3, 0, (0 if (path == tmp_path) == (kind == 'posix') else 100 * 1024**3)))
    with pytest.raises(AssertionError):
        x.preflight()


@pytest.mark.parametrize('integrity,canonical,expected', [(True, True, True), (True, False, False), (False, True, False), (False, False, False)])
def test_authorization(integrity: bool, canonical: bool, expected: bool) -> None:
    assert authorization(integrity, canonical) is expected


def setup_finish(canonical: bool) -> None:
    p.CONTROL.mkdir(); p.POP.mkdir()
    observations = ['lineage_events001.csv', 'lineage_snapshots001.csv', 'conservation002.csv',
                    'conservation_buffers002.csv', 'material_events002.csv', 'scheduling_events001.csv', 'source_events006.csv']
    executions = []
    for index in range(12):
        case = {'index': index, 'count': 140, 'mixed': False, 'seed': 1, 'observed': int(index < 10)}
        executions.append({'case': case, 'returncode': 0, 'analysis_returncode': 0})
        x.save(p.POP / f'{index:02}.inventory.json', {'native.receipt.json': 'unique', 'ordinary': 'same',
               **({name: 'observation' for name in observations} if index < 10 else {})})
        if index < 10:
            summary = {k: 1 for k in ('integrity', 'end_tick', 'final_population', 'final_host', 'late_min_host',
                'encounters', 'bound_encounters', 'dispatches', 'successful_cleavages', 'exact_host_children')}
            summary['integrity'] = True
            summary['exact_host_children'] = int(canonical)
            x.save(p.CONTROL / f'summary-{index:02}.json', {**summary, 'transfer': {k: 0 for k in
                ('qualifying_transfers', 'serial_transfers', 'transfer_renewing_descendants', 'max_nonrelocation_depth')}})
    x.save(p.CONTROL / 'completed.json', executions)


@pytest.mark.parametrize('canonical', [True, False])
def test_finish_executes_repeat_and_separates_control(sandbox: Path, monkeypatch: pytest.MonkeyPatch, canonical: bool) -> None:
    setup_finish(canonical)
    def repeat(args: list[str], *rest: object, **kwargs: object) -> int:
        index = int(args[-1])
        (p.CONTROL / f'repeat-{index:02}.json').write_bytes((p.CONTROL / f'summary-{index:02}.json').read_bytes())
        return 0
    invoke = Mock(side_effect=repeat); monkeypatch.setattr(x, 'command', invoke)
    f.finish()
    assert invoke.call_count == 10
    result = object_from(p.CONTROL / 'final-audit.json')
    assert result['interpretation_integrity'] is True
    assert result['canonical_reference_gate'] is canonical
    assert result['interpretation_authorized'] is canonical
    summaries = result['summaries']
    assert isinstance(summaries, list) and len(summaries) == 8


@pytest.mark.parametrize('failure', ['process', 'parity'])
def test_finish_failure_no_authorization(sandbox: Path, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    setup_finish(True)
    def repeat(args: list[str], *rest: object, **kwargs: object) -> int:
        index = int(args[-1])
        (p.CONTROL / f'repeat-{index:02}.json').write_text('different')
        return 1 if failure == 'process' else 0
    invoke = Mock(side_effect=repeat); monkeypatch.setattr(x, 'command', invoke)
    with pytest.raises(AssertionError):
        f.finish()
    assert invoke.call_count == 1
    assert not (p.CONTROL / 'final-audit.json').exists()


@pytest.mark.parametrize('fail_phase', ['', 'build', 'link'])
def test_build_and_link_unconditional(sandbox: Path, monkeypatch: pytest.MonkeyPatch, fail_phase: str) -> None:
    # Stub only filesystem copies and process execution, never invoke a compiler.
    shutil.rmtree(x.EVIDENCE / 'native-v2')
    def copytree(source: object, target: Path) -> None:
        target.mkdir(); (target / 'source.cpp').write_text('mock')
    def copyfile(source: object, target: Path) -> None:
        target.write_text('mock')
    monkeypatch.setattr(shutil, 'copytree', copytree)
    monkeypatch.setattr(shutil, 'copyfile', copyfile)
    def command(args: list[str], cwd: Path, label: str) -> int:
        if label == 'link' and fail_phase != 'link':
            (cwd / 'reaction').write_text('mock binary')
        return 1 if label == fail_phase else 0
    invoke = Mock(side_effect=command); monkeypatch.setattr(x, 'command', invoke)
    if fail_phase:
        with pytest.raises(AssertionError, match=f'{fail_phase} failed'):
            x.build()
        assert not (x.EVIDENCE / 'native-v2/build.json').exists()
    else:
        x.build()
        assert (x.EVIDENCE / 'native-v2/build.json').exists()
    assert [call.args[2] for call in invoke.call_args_list] == (['build'] if fail_phase == 'build' else ['build', 'link'])


@pytest.mark.parametrize('returncode', [1, None])
def test_native_failure_consumes_launch_and_stops(sandbox: Path, monkeypatch: pytest.MonkeyPatch, returncode: int | None) -> None:
    p.freeze()
    invoke = Mock(return_value=returncode); monkeypatch.setattr(x, 'command', invoke)
    with pytest.raises(AssertionError, match='launch remains consumed'):
        p.run()
    assert invoke.call_count == 1
    assert object_from(p.CONTROL / 'execution-00.json')['returncode'] == returncode
    assert (p.POP / '00.inventory.json').exists()
    with pytest.raises(AssertionError, match='already reserved'):
        p.run()
    assert invoke.call_count == 1


def test_output_reservation_never_reused(sandbox: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p.freeze()
    directory = p.POP / '00'; directory.mkdir()
    (directory / 'preserved').write_text('old attempt')
    invoke = Mock(); monkeypatch.setattr(x, 'command', invoke)
    with pytest.raises(FileExistsError):
        p.run()
    invoke.assert_not_called()
    assert (directory / 'preserved').read_text() == 'old attempt'
    assert (p.CONTROL / 'launch.json').exists()


@pytest.mark.parametrize('budget', ['posix', 'raw'])
def test_over_quota_prevents_launch_with_ample_free(sandbox: Path, monkeypatch: pytest.MonkeyPatch, budget: str) -> None:
    p.freeze()
    monkeypatch.setattr(x, 'preflight', REAL_PREFLIGHT)
    monkeypatch.setattr(subprocess, 'check_output', Mock(return_value='/run/media/jojo/Elements /dev/sdc1 exfat\n/tmp/sm /run/media/jojo/Elements/bio-sim-results/stringmol-posix.ext4 fuse.ext4'))
    monkeypatch.setattr(shutil, 'disk_usage', Mock(return_value=shutil._ntuple_diskusage(100 * 1024**3, 0, 100 * 1024**3)))
    def usage(path: Path) -> int:
        return (4 if budget == 'posix' else 25) * 1024**3 if path == (x.EVIDENCE if budget == 'posix' else x.RAW) else 1
    monkeypatch.setattr(x, 'allocated', usage)
    invoke = Mock(); monkeypatch.setattr(x, 'command', invoke)
    with pytest.raises(AssertionError, match='quota exhausted'):
        p.run()
    invoke.assert_not_called()
    assert not (p.CONTROL / 'launch.json').exists()


@pytest.mark.parametrize('negative', ['replay', 'isolation', 'no-reference'])
def test_descriptive_negative_cannot_authorize(sandbox: Path, monkeypatch: pytest.MonkeyPatch, negative: str) -> None:
    setup_finish(True)
    if negative == 'replay':
        path = p.CONTROL / 'summary-00.json'
        value = json.loads(path.read_text()); value['integrity'] = False
    elif negative == 'isolation':
        path = p.POP / '10.inventory.json'
        value = json.loads(path.read_text()); value['ordinary'] = 'changed'
    else:
        path = p.CONTROL / 'completed.json'
        value = json.loads(path.read_text())
        for item in value:
            item['case']['mixed'] = True
    path.write_text(json.dumps(value))
    def repeat(args: list[str], *rest: object, **kwargs: object) -> int:
        index = int(args[-1])
        (p.CONTROL / f'repeat-{index:02}.json').write_bytes((p.CONTROL / f'summary-{index:02}.json').read_bytes())
        return 0
    monkeypatch.setattr(x, 'command', Mock(side_effect=repeat))
    f.finish()
    result = object_from(p.CONTROL / 'final-audit.json')
    assert result['interpretation_authorized'] is False
    assert result['canonical_reference_gate'] is (negative != 'no-reference')
    assert result['interpretation_integrity'] is (negative == 'no-reference')
    assert (p.CONTROL / 'population-summary.csv').exists()


@pytest.mark.parametrize('malformed', ['missing-returncode', 'missing-analysis', 'duplicate-index', 'null-analysis'])
def test_incomplete_process_receipts_do_not_execute(sandbox: Path, monkeypatch: pytest.MonkeyPatch, malformed: str) -> None:
    setup_finish(True)
    path = p.CONTROL / 'completed.json'; values = json.loads(path.read_text())
    if malformed == 'missing-returncode':
        del values[0]['returncode']
    elif malformed == 'missing-analysis':
        del values[0]['analysis_returncode']
    elif malformed == 'duplicate-index':
        values[0]['case']['index'] = 1
    else:
        values[0]['analysis_returncode'] = None
    path.write_text(json.dumps(values))
    invoke = Mock(); monkeypatch.setattr(x, 'command', invoke)
    with pytest.raises((AssertionError, KeyError)):
        f.finish()
    invoke.assert_not_called()
    assert not (p.CONTROL / 'final-audit.json').exists()
