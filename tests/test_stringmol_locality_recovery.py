"""Qualification uses fake native/replay processes only; no population loop."""
import json
import io
from pathlib import Path
import subprocess
import shutil
from unittest.mock import Mock

import pytest
from experiments.stringmol import locality_recovery as r
from experiments.stringmol import locality_pilot as p
from experiments.stringmol.locality_process import FileRecord


def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> r.Proposal:
    for name in ('CONTROL', 'RAW', 'EXPORT', 'OLD_RAW', 'ORIGIN', 'WORKTREE', 'APPROVAL'):
        monkeypatch.setattr(r, name, tmp_path/name)
    r.OLD_RAW.mkdir()
    monkeypatch.setattr(r, 'storage', Mock())
    digest: FileRecord = {'sha256':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'bytes':0}
    jobs: list[r.Job] = []
    names: dict[str, list[str]] = {}
    for arm in p.ARMS:
        for kind in r.KINDS:
            identity = f'{arm}-{kind}'
            expected = ['state.bin'] + (sorted(p.OBS) if kind != 'off' else [])
            names[identity] = sorted(expected)
            jobs.append(dict(arm=arm, kind=kind, command=['fake-native', arm, kind],
                             environment=p.locality_environment(kind != 'off'), directory=str(r.RAW/identity)))
            inventory = {name:digest for name in expected}
            inventory.update({name:digest for name in r.LOGS})
            (r.OLD_RAW/f'{identity}.receipt.json').write_text(json.dumps(dict(inventory=inventory)))
    return dict(schema=1, scope='test-complete', roots=[], policy={}, jobs=jobs, bindings={},
                native_files=names, observers=sorted(p.OBS), endpoints=digest)


def fake_process(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
    cwd = Path(str(kwargs['cwd']))
    if command[0] == 'git':
        stream = kwargs.get('stdout')
        if isinstance(stream, io.BufferedWriter):
            stream.write(b'mock source archive')
        else:
            Path(command[3]).write_bytes(b'mock git bundle')
    elif command[0] == 'fake-native':
        (cwd/'state.bin').write_bytes(b'')
        if command[2] != 'off':
            for name in p.OBS:
                (cwd/name).write_bytes(b'')
    else:
        # The isolated replay command embeds its exclusive result path.
        code = command[-1]
        output = Path(code.split('Path(')[1].split('))')[0].strip("'"))
        value = dict(end_tick=5000, end_population=1, rng_draws=1, searches=1,
                     empty_searches=0, encounters=1, bindings=1, proposals=100, placed=100,
                     failed_placement=0, vacancy_sum=1,
                     checkpoints=[dict(tick=4900, event='CHECKPOINT', population=1,
                                       occupied_neighbor_slots=0, neighbor_slots=8)],
                     renewal=dict(transfer_edges=[]))
        output.write_text(json.dumps(value))
    return subprocess.CompletedProcess(command, 0)


def exported() -> None:
    r.EXPORT.mkdir()
    p.save(r.EXPORT/'VERIFIED.json', dict(verified=True))


def test_complete_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = setup(tmp_path, monkeypatch)
    native = Mock(side_effect=fake_process)
    monkeypatch.setattr(subprocess, 'run', native)
    r.workflow(data)
    assert native.call_count == 30
    assert (r.EXPORT/'checksums.json').exists()
    assert json.loads((r.EXPORT/'VERIFIED.json').read_text())['verified'] is True
    assert json.loads((r.CONTROL/'complete.json').read_text())['replay'] == 16
    assert json.loads((r.CONTROL/'decision.json').read_text())['positive_control'] is True
    before = (r.CONTROL/'launch.json').read_bytes()
    with pytest.raises(FileExistsError):
        r.workflow(data)
    assert native.call_count == 30 and (r.CONTROL/'launch.json').read_bytes() == before
    assert not r.ORIGIN.exists()


@pytest.mark.parametrize('failure', ['spawn', 'timeout', 'nonzero', 'inventory', 'missing',
                                     'repeat', 'off', 'replay', 'false-complete', 'analysis', 'outcome', 'export'])
def test_workflow_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    data = setup(tmp_path, monkeypatch)
    calls = 0

    def process(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal calls
        calls += 1
        if failure == 'spawn':
            raise FileNotFoundError('mock spawn')
        if failure == 'timeout':
            raise subprocess.TimeoutExpired(command, 600)
        result = fake_process(command, **kwargs)
        cwd = Path(str(kwargs['cwd']))
        if failure == 'nonzero':
            return subprocess.CompletedProcess(command, 7)
        if failure == 'inventory':
            (cwd/'redirect').symlink_to(tmp_path)
        if failure == 'missing' and calls == 1:
            (cwd/'state.bin').unlink()
        if failure == 'repeat' and calls == 2:
            (cwd/'state.bin').write_bytes(b'drift')
        if failure == 'off' and calls == 3:
            (cwd/next(iter(p.OBS))).write_bytes(b'')
        if calls > 12:
            path = Path(command[-1].split('Path(')[1].split('))')[0].strip("'"))
            if failure == 'replay':
                return subprocess.CompletedProcess(command, 8)
            if failure == 'false-complete':
                path.unlink()
            if failure == 'outcome':
                value = json.loads(path.read_text()); value['end_tick'] = 42
                path.write_text(json.dumps(value))
            if failure == 'analysis' and calls == 14:
                value = json.loads(path.read_text()); value['placed'] = 101
                path.write_text(json.dumps(value))
        return result

    monkeypatch.setattr(subprocess, 'run', Mock(side_effect=process))
    monkeypatch.setattr(r, 'portable', Mock(side_effect=OSError('export failure')) if failure == 'export' else exported)
    with pytest.raises((ValueError, OSError)):
        r.workflow(data)
    assert not (r.CONTROL/'complete.json').exists()
    assert (r.CONTROL/'blocked.json').exists()
    if failure in ('spawn', 'timeout', 'nonzero', 'inventory', 'missing'):
        assert calls == 1
        assert (r.CONTROL/'GG-observed.process.json').exists()
    if failure == 'repeat': assert calls == 2
    if failure == 'off': assert calls == 3
    if failure in ('replay', 'false-complete', 'outcome'): assert calls == 13
    if failure == 'analysis': assert calls == 16
    if failure == 'export': assert calls == 28
    with pytest.raises(FileExistsError):
        r.workflow(data)
    assert not r.ORIGIN.exists()


@pytest.mark.parametrize('change', ['matrix', 'flags', 'input', 'roots', 'binding'])
def test_canonical_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    data = setup(tmp_path, monkeypatch)
    path = tmp_path/'proposal.json'
    monkeypatch.setattr(r, 'proposal', lambda: data)
    r.freeze(path)
    value = json.loads(path.read_text())
    if change == 'matrix': value['jobs'].pop()
    if change == 'flags': value['jobs'][2]['environment']['STRINGMOL_CONSERVATION_LOG'] = '1'
    if change == 'input': value['jobs'][0]['command'] = ['wrong']
    if change == 'roots': value['roots'] = ['/tmp/sm/xl-e']
    if change == 'binding': value['bindings'] = {}
    # A removed required binding is not allowed even with a freshly claimed hash.
    if change == 'binding': value['bindings']['ambient'] = {'sha256':'x', 'bytes':1}
    path.write_bytes(r.encode(value))
    native = Mock(); monkeypatch.setattr(subprocess, 'run', native)
    with pytest.raises(ValueError): r.validate(path, p.record(path)['sha256'])
    assert native.call_count == 0 and not r.CONTROL.exists()


def test_approval_and_reuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(r, 'validate', lambda path, digest: data)
    native = Mock(); monkeypatch.setattr(r, 'workflow', native)
    with pytest.raises(ValueError): r.launch(tmp_path/'proposal', 'x')
    r.APPROVAL.write_bytes(r.encode(dict(scope=data['scope'], proposal_sha256='x', roots=data['roots'],
                                         independent_parent_review='PASS', native_budget=12)))
    r.CONTROL.mkdir()
    with pytest.raises(ValueError, match='reuse'): r.launch(tmp_path/'proposal', 'x')
    assert native.call_count == 0


def test_paths_and_export_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    setup(tmp_path, monkeypatch)
    redirected = tmp_path/'redirect'; redirected.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError): r.clean_path(redirected/'child')
    r.CONTROL.mkdir(); (r.CONTROL/'file').write_bytes(b'evidence')
    r.RAW.mkdir(); (r.RAW/'file').write_bytes(b'raw')
    monkeypatch.setattr(shutil, 'copyfileobj', Mock(side_effect=OSError('copy denied')))
    with pytest.raises(OSError): r.portable()
    assert not (r.EXPORT/'VERIFIED.json').exists()


@pytest.mark.parametrize('free', [0, 6*r.GIB])
def test_headroom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, free: int) -> None:
    from types import SimpleNamespace
    # Keep literal external roots; mock only mounts/disk status, no outputs.
    mounts = ('/run/media/jojo/Elements/bio-sim-results/stringmol-posix.ext4 /tmp/sm fuse.ext4 rw 0 0\n'
              '/dev/mock /run/media/jojo/Elements exfat rw 0 0\n')
    monkeypatch.setattr(Path, 'read_text', Mock(return_value=mounts))
    monkeypatch.setattr(shutil, 'disk_usage', Mock(return_value=SimpleNamespace(free=free)))
    with pytest.raises(ValueError, match='headroom'): r.storage()


def test_quota(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace
    control = tmp_path/'control'; control.mkdir(); (control/'file').touch()
    monkeypatch.setattr(r, 'CONTROL', control)
    monkeypatch.setattr(p, 'POSIX_STORAGE', tmp_path)
    mounts = ('/run/media/jojo/Elements/bio-sim-results/stringmol-posix.ext4 /tmp/sm fuse.ext4 rw 0 0\n'
              '/dev/mock /run/media/jojo/Elements exfat rw 0 0\n')
    monkeypatch.setattr(Path, 'read_text', Mock(return_value=mounts))
    monkeypatch.setattr(shutil, 'disk_usage', Mock(return_value=SimpleNamespace(free=100*r.GIB)))
    monkeypatch.setattr(r, 'files', Mock(return_value={'file':dict(bytes=4*r.GIB, sha256='x')}))
    with pytest.raises(ValueError, match='budget'): r.storage()
