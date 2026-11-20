"""Owned development input/replay gates; no population launches."""
from pathlib import Path
import shutil
import pytest
from experiments.stringmol import xp001 as x, xp001_population as p
from experiments.stringmol.configure_control import HOST
from experiments.stringmol.analyze_retirement import BoundaryReplay
from experiments.stringmol.analyze_conservation import initial_material

@pytest.mark.parametrize('count,mixed',[(70,False),(70,True),(140,False),(140,True)])
def test_changed_inoculum(count: int,mixed: bool) -> None:
    founders=p.expected(count,mixed)
    assert len(founders)==count
    assert len({(r['x'],r['y']) for r in founders})==count
    initial=initial_material([dict(f) for f in founders],'histogram',0)
    boundary=BoundaryReplay(initial,[],'IMMEDIATE',5000,[r['id'] for r in founders],'RETAIN')
    assert set(boundary.source.material.buffers)==set(range(count))
    visible=[b.split(b'\0',1)[0] for b in boundary.source.material.buffers.values()]
    assert visible.count(HOST.encode())==(count//2 if mixed else count)
    assert visible.count(b'B')==(count//2 if mixed else 0)
    assert sum(initial['molecular'])==sum(map(len,visible))
    assert initial['total']==initial['molecular']

@pytest.mark.parametrize('pair',['HH','HB','BH','BB'])
def test_real_native_replay(pair: str) -> None:
    directory=x.RAW/f'reactions-v2/{pair}-s1-r0-o1'
    assert directory.is_dir(), 'qualify frozen native reaction inputs first'
    result=x.replay(directory,[HOST if c=='H' else 'B' for c in pair],16)
    assert result['conserved']
    assert result['exact_host_children']==int(pair=='HH')

def test_wrong_initial_support_fails() -> None:
    with pytest.raises(ValueError):
        x.replay(x.RAW/'reactions-v2/HH-s1-r0-o1',[HOST,HOST],0)

def test_wrong_partner_fails() -> None:
    with pytest.raises(ValueError):
        x.replay(x.RAW/'reactions-v2/HB-s1-r0-o1',[HOST,HOST],16)

def test_terminal_buffer_tamper(tmp_path: Path) -> None:
    source=x.RAW/'reactions-v2/HH-s1-r0-o1'
    target=tmp_path/'tampered'; shutil.copytree(source,target)
    path=target/'summary.json'
    raw=path.read_text(); assert '5757' in raw
    path.write_text(raw.replace('5757','4257',1))
    with pytest.raises(AssertionError):
        x.replay(target,[HOST,HOST],16)
