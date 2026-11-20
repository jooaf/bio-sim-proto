"""Final XL guard regression; every attempted native launch is mocked."""
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
from experiments.stringmol import locality_pilot as pilot
from experiments.stringmol.locality_process import FileRecord, InventoryError, execute


@pytest.mark.parametrize('outcome', [0, FileNotFoundError('spawn'), subprocess.TimeoutExpired(['fake'], 2)])
@pytest.mark.parametrize('collection_error', [PermissionError('inventory denied'), OSError('inventory IO')])
def test_collection_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                            outcome: int | OSError | subprocess.TimeoutExpired,
                            collection_error: OSError) -> None:
    receipt = tmp_path/'receipt.json'
    native = Mock(return_value=subprocess.CompletedProcess(['fake'], outcome) if isinstance(outcome, int) else None,
                  side_effect=None if isinstance(outcome, int) else outcome)
    monkeypatch.setattr(subprocess, 'run', native)
    original_record = pilot.record

    def failing_record(path: str | Path) -> FileRecord:
        # The authoritative process result is already durable before hashing.
        saved = json.loads(receipt.read_text())
        assert saved['exit_code'] == (outcome if isinstance(outcome, int) else
                                     'TIMEOUT' if isinstance(outcome, subprocess.TimeoutExpired) else 'OSERROR')
        assert saved['collection_complete'] is False
        if Path(path).name == 'z-unreadable':
            raise collection_error
        return original_record(path)

    (tmp_path/'a-available').write_bytes(b'keep')
    (tmp_path/'z-unreadable').write_bytes(b'unreadable')
    monkeypatch.setattr(pilot, 'record', failing_record)
    with pytest.raises(InventoryError) as caught:
        execute(['fake', 'literal argument'], cwd=tmp_path, environment={'EXACT':'yes'},
                receipt=receipt, stdout=tmp_path/'out', stderr=tmp_path/'err', timeout=2, output_root=tmp_path)
    assert caught.value.__cause__ is collection_error
    saved = json.loads(receipt.read_text())
    assert saved['collection_complete'] is False
    assert saved['inventory_error'] == dict(type=type(collection_error).__name__,
                                          message=str(collection_error), repr=repr(collection_error))
    assert saved['exception'] == (None if isinstance(outcome, int) else
                                 dict(type=type(outcome).__name__, message=str(outcome), repr=repr(outcome)))
    assert saved['command'] == ['fake', 'literal argument'] and saved['environment'] == {'EXACT':'yes'}
    assert saved['cwd'] == str(tmp_path) and saved['timeout'] == 2
    assert saved['finished'] >= saved['started'] and saved['seconds'] >= 0
    assert saved['inventory']['a-available'] == original_record(tmp_path/'a-available')
    assert 'receipt.json' not in saved['inventory']
    before = receipt.read_bytes()
    with pytest.raises(FileExistsError):
        execute(['fake'], cwd=tmp_path, environment={}, receipt=receipt,
                stdout=tmp_path/'out', stderr=tmp_path/'err', timeout=2, output_root=tmp_path)
    assert native.call_count == 1 and receipt.read_bytes() == before


@pytest.mark.parametrize('consumer', ['analyze', 'diagnose'])
def test_incomplete_receipt_consumers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, consumer: str) -> None:
    from experiments.stringmol import locality_diagnose as diagnose
    control = tmp_path/'control'; control.mkdir()
    raw = tmp_path/'raw'; raw.mkdir()
    for module in (pilot, diagnose):
        monkeypatch.setattr(module, 'CONTROL', control)
        monkeypatch.setattr(module, 'RAW', raw)
    for kind in ('observed', 'repeat', 'off'):
        (raw/f'GG-{kind}.receipt.json').write_text(json.dumps(
            dict(exit_code=0, inventory={}, collection_complete=False)))
    native = Mock(); monkeypatch.setattr(subprocess, 'run', native)
    with pytest.raises(ValueError, match='incomplete native evidence'):
        if consumer == 'analyze': pilot.analyze()
        else: diagnose.main()
    assert native.call_count == 0
    assert not (control/'results.json').exists()
    assert not (control/'diagnostic-v3/diagnostics.json').exists()


@pytest.mark.parametrize('optimized', [False, True])
def test_storage_admission(tmp_path: Path, optimized: bool) -> None:
    # Run explicit checks, not Python assertions, in both interpreter modes.
    script = r'''
from pathlib import Path
from unittest.mock import Mock, patch
from types import SimpleNamespace
import sys
from experiments.stringmol import locality_pilot as p
root=Path(sys.argv[1]); posix=root/'posix'; elements=root/'elements'; outside=root/'outside'
for folder in (posix,elements,outside): folder.mkdir()
p.POSIX_STORAGE=posix; p.ELEMENTS_STORAGE=elements
p.CONTROL=posix/'control'; p.RAW=elements/'raw'
p.CONTROL.mkdir(); p.RAW.mkdir()
mounts=' /tmp/sm /run/media/jojo/Elements/bio-sim-results/stringmol-posix.ext4 /run/media/jojo/Elements '
def check_rejected():
    try: p.preflight()
    except ValueError: return
    raise RuntimeError('unsafe admission')
with patch.object(Path,'read_text',return_value=mounts), patch.object(p.shutil,'disk_usage',return_value=SimpleNamespace(free=100*1024**3)), patch.object(p.subprocess,'run') as native:
    p.preflight()
    for name in ('CONTROL','RAW'):
        original=getattr(p,name)
        original.rmdir(); original.symlink_to(outside, target_is_directory=True)
        check_rejected()
        # run() must check before reading a preparation or reserving launch.
        try: p.run()
        except ValueError: pass
        else: raise RuntimeError('run admitted redirected root')
        if (outside/'launch.json').exists() or list(outside.iterdir()): raise RuntimeError('output created')
        original.unlink(); original.mkdir()
        ancestor=original.parent/'redirect'; ancestor.symlink_to(outside,target_is_directory=True)
        setattr(p,name,ancestor/'absent-child')
        check_rejected()
        setattr(p,name,outside/'absent-child'); check_rejected()
        setattr(p,name,original)
    # Mock size accounting; no large evidence files are created.
    original_stat=Path.stat
    for folder,limit in ((p.CONTROL,4),(p.RAW,25)):
        quota=folder/'quota'; quota.touch()
        def quota_stat(path, *args, **kwargs):
            actual=original_stat(path,*args,**kwargs)
            if path == quota: return SimpleNamespace(st_mode=actual.st_mode, st_size=limit*1024**3)
            return actual
        with patch.object(Path,'stat',quota_stat): check_rejected()
        quota.unlink()
    for free in (0, 6*1024**3):
        with patch.object(p.shutil,'disk_usage',return_value=SimpleNamespace(free=free)): check_rejected()
    p.preflight()
    if native.call_count: raise RuntimeError('unexpected process launch')
'''
    result = subprocess.run([sys.executable, *(['-O'] if optimized else []), '-c', script, str(tmp_path)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
