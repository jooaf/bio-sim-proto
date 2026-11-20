"""Adversarial engineering tests; native population entry points are never called."""
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
from experiments.stringmol import locality_pilot as pilot
from experiments.stringmol.locality_process import execute, FileRecord
from experiments.stringmol.locality_pilot import Job


@pytest.mark.parametrize('failure', [FileNotFoundError('missing'), PermissionError('denied'),
                                     subprocess.TimeoutExpired(['fake'], 2)])
def test_failure_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                         failure: OSError | subprocess.TimeoutExpired) -> None:
    receipt = tmp_path/'attempt.json'
    def spawn(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        assert json.loads(receipt.read_text())['state'] == 'reserved'
        (tmp_path/'partial').write_bytes(b'preserved')
        raise failure
    native = Mock(side_effect=spawn)
    monkeypatch.setattr(subprocess, 'run', native)
    result = execute(['fake', 'literal argument'], cwd=tmp_path, environment={'EXACT':'yes'},
        receipt=receipt, stdout=tmp_path/'out', stderr=tmp_path/'err', timeout=2, output_root=tmp_path)
    assert result == json.loads(receipt.read_text())
    assert result['exception'] is not None and result['exception']['type'] == type(failure).__name__
    assert result['command'] == ['fake', 'literal argument'] and result['environment'] == {'EXACT':'yes'}
    assert result['cwd'] == str(tmp_path) and result['seconds'] >= 0
    assert result['finished'] >= result['started']
    assert set(result['inventory']) == {'out', 'err', 'partial'}
    assert native.call_count == 1
    with pytest.raises(FileExistsError):
        execute(['fake'], cwd=tmp_path, environment={}, receipt=receipt, stdout=tmp_path/'out',
                stderr=tmp_path/'err', timeout=2, output_root=tmp_path)
    assert native.call_count == 1


@pytest.mark.parametrize('code', [0, 7, -9])
def test_exit_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int) -> None:
    native = Mock(return_value=subprocess.CompletedProcess(['fake'], code))
    monkeypatch.setattr(subprocess, 'run', native)
    result = execute(['fake'], cwd=tmp_path, environment={}, receipt=tmp_path/'receipt',
                     stdout=tmp_path/'out', stderr=tmp_path/'err', timeout=2, output_root=tmp_path)
    assert result['exit_code'] == code and result['exception'] is None
    assert native.call_count == 1


@pytest.mark.parametrize('optimized', [False, True])
def test_guards_survive_optimization(tmp_path: Path, optimized: bool) -> None:
    script = '''
from pathlib import Path
from unittest.mock import patch
from experiments.stringmol import locality_pilot as p
from experiments.stringmol import locality_finish as f
import json
import sys
root=Path(sys.argv[1]); p.CONTROL=root; p.RAW=root/'raw'; f.CONTROL=root
with patch.object(Path,'read_text',return_value=''), patch.object(p.subprocess,'run') as native:
    try: p.preflight()
    except ValueError: pass
    else: raise RuntimeError('mount guard bypassed')
    if native.call_count: raise RuntimeError('unexpected launch')
with patch.object(p,'validate_preparation'), patch.object(p.subprocess,'run') as native:
    (root/'preparation.json').write_text('{}')
    (root/'preparation.sha256.json').write_text('{}')
    try: p.run()
    except ValueError: pass
    else: raise RuntimeError('provenance guard bypassed')
    if native.call_count: raise RuntimeError('unexpected launch')
try: p.validate_preparation({'jobs':[]})
except ValueError: pass
else: raise RuntimeError('matrix guard bypassed')
(root/'diagnostic-v3').mkdir()
arm={'native_exit_codes':{'observed':0,'repeat':0,'off':0},'exact_repeat':True,
     'common_file_parity':True,'full_observer_off':False,'replays':[{'exit_code':0},{'exit_code':0}]}
(root/'diagnostic-v3/diagnostics.json').write_text(json.dumps({'arms':dict.fromkeys(p.ARMS,arm)}))
(root/'diagnostic-v3/GG-observed.json').write_text('one')
(root/'diagnostic-v3/GG-repeat.json').write_text('two')
try: f.main()
except ValueError: pass
else: raise RuntimeError('parity guard bypassed')
if (root/'decision.json').exists(): raise RuntimeError('false decision emitted')
'''
    command = [sys.executable, *(['-O'] if optimized else []), '-c', script, str(tmp_path)]
    result = subprocess.run(command, capture_output=True, text=True, env=dict(os.environ), check=False)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('bad', [None, [], {}, {'jobs':[]}, {'jobs':[{}]*12}])
def test_malformed_preparation(bad: object) -> None:
    with pytest.raises(ValueError):
        pilot.validate_preparation(bad)


def test_provenance_mismatch_never_launches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Seal mismatch must reject before native invocation, also tested in -O suite.
    monkeypatch.setattr(pilot, 'CONTROL', tmp_path)
    monkeypatch.setattr(pilot, 'validate_preparation', lambda data: None)
    (tmp_path/'preparation.json').write_text('{}')
    (tmp_path/'preparation.sha256.json').write_text('{}')
    native = Mock()
    monkeypatch.setattr(subprocess, 'run', native)
    with pytest.raises(ValueError): pilot.run()
    assert native.call_count == 0


@pytest.mark.parametrize('failure', [FileNotFoundError('missing'), PermissionError('denied'),
                                     subprocess.TimeoutExpired(['fake'], 2)])
def test_native_controller_failure_stops_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                              failure: OSError | subprocess.TimeoutExpired) -> None:
    control=tmp_path/'control'; control.mkdir(); raw=tmp_path/'raw'; raw.mkdir()
    source=control/'n'
    monkeypatch.setattr(pilot, 'CONTROL', control)
    monkeypatch.setattr(pilot, 'RAW', raw)
    monkeypatch.setattr(pilot, 'SOURCE', source)
    monkeypatch.setattr(pilot, 'preflight', Mock())
    digest: FileRecord={'sha256':'f'*64, 'bytes':1}
    jobs: list[Job]=[]
    for arm, (interaction, placement) in pilot.ARMS.items():
        for kind in ('observed','repeat','off'):
            jobs.append(dict(arm=arm,kind=kind,interaction=interaction,placement=placement,
                config=str(control/f'{arm}.conf'),config_record=digest,directory=str(raw/f'{arm}-{kind}'),
                environment=pilot.locality_environment(kind!='off'),
                command=[str(source/'release/stringmol'),'30',str(control/f'{arm}.conf')]))
    data=dict(jobs=jobs,binary=digest,matrix=digest,source={},implementation={},gates={})
    (control/'preparation.json').write_text(json.dumps(data))
    (control/'preparation.sha256.json').write_text(json.dumps(digest))
    monkeypatch.setattr(pilot, 'record', Mock(return_value=digest))
    monkeypatch.setattr(pilot, 'inventory', Mock(return_value={}))
    native=Mock(side_effect=failure); monkeypatch.setattr(subprocess,'run',native)
    with pytest.raises(ValueError, match='native failure'): pilot.run()
    assert native.call_count==1
    receipts=list(raw.glob('*.receipt.json'))
    assert len(receipts)==1
    assert json.loads(receipts[0].read_text())['exception']['type']==type(failure).__name__
    assert not (control/'native-complete.json').exists()


@pytest.mark.parametrize('failure', [FileNotFoundError('missing'), PermissionError('denied'),
                                     subprocess.TimeoutExpired(['fake'], 2)])
def test_diagnostic_wrapper_failure_receipts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                             failure: OSError | subprocess.TimeoutExpired) -> None:
    from experiments.stringmol import locality_diagnose as diagnose
    control=tmp_path/'control'; control.mkdir(); raw=tmp_path/'raw'; raw.mkdir()
    monkeypatch.setattr(diagnose,'CONTROL',control); monkeypatch.setattr(diagnose,'RAW',raw)
    for arm in pilot.ARMS:
        for kind in ('observed','repeat','off'):
            (raw/f'{arm}-{kind}').mkdir()
            (raw/f'{arm}-{kind}.receipt.json').write_text(json.dumps({'exit_code':0,'inventory':{}}))
    native=Mock(side_effect=failure); monkeypatch.setattr(subprocess,'run',native)
    diagnose.main()
    receipts=list((control/'diagnostic-v3').glob('*.process.json'))
    assert len(receipts)==8 and native.call_count==8
    assert all(json.loads(p.read_text())['exception']['type']==type(failure).__name__ for p in receipts)
    assert json.loads((control/'diagnostic-v3/diagnostics.json').read_text())['population_interpretation_authorized'] is False


@pytest.mark.parametrize('failure', [FileNotFoundError('missing'), PermissionError('denied'),
                                     subprocess.TimeoutExpired(['fake'], 2)])
def test_analysis_wrapper_failure_receipts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                           failure: OSError | subprocess.TimeoutExpired) -> None:
    control=tmp_path/'control'; control.mkdir(); raw=tmp_path/'raw'; raw.mkdir()
    monkeypatch.setattr(pilot,'CONTROL',control); monkeypatch.setattr(pilot,'RAW',raw)
    for arm in pilot.ARMS:
        for kind in ('observed','repeat','off'):
            directory=raw/f'{arm}-{kind}'; directory.mkdir()
            if kind != 'off':
                for name in pilot.OBS: (directory/name).write_bytes(b'fixture')
            (raw/f'{arm}-{kind}.receipt.json').write_text(json.dumps({'exit_code':0,'inventory':pilot.inventory(directory)}))
    native=Mock(side_effect=failure); monkeypatch.setattr(subprocess,'run',native)
    with pytest.raises(ValueError, match='replay failure'): pilot.analyze()
    receipts=list(control.glob('*.process.json'))
    assert len(receipts)==8 and native.call_count==8
    assert all(json.loads(p.read_text())['exception']['type']==type(failure).__name__ for p in receipts)
    assert not (control/'results.json').exists()


def test_complete_without_pending_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from experiments.stringmol import locality_replay as replay_module
    from experiments.stringmol.configure_control import HOST
    from experiments.stringmol.analyze_conservation import initial_material
    from experiments.stringmol import analyze_conservation
    from experiments.stringmol.locality_geometry import Boundary
    initial = initial_material([{'id':0,'sequence_hex':HOST.encode().hex()}], 'histogram', 0)
    initial['waste'] = [0]*33
    monkeypatch.setattr(replay_module, 'Matrix', Mock())
    monkeypatch.setattr(analyze_conservation, 'canonical_rows', Mock(return_value=[]))
    monkeypatch.setattr(replay_module, 'canonical_stream', Mock(return_value=iter([{'event':'COMPLETE','tick':'0'}])))
    monkeypatch.setattr(Boundary, 'step', Mock())
    with pytest.raises(ValueError, match='missing dispatch'):
        replay_module.replay(tmp_path, initial, {0:(0,0)}, 42, tmp_path/'matrix', 0, 0)
