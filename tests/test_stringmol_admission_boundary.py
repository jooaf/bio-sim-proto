"""Boundary-layer histories; VM/RNG provenance is a separate mandatory gate."""
from copy import deepcopy
from typing import Any

import pytest

from experiments.stringmol import analyze_conservation as c
from experiments.stringmol.admission_boundary import BoundaryReplay
from experiments.stringmol.analyze_scheduling import DEFAULTS


def fixture(policy: str = 'DELAY500', next_victim: bool = False) -> tuple[BoundaryReplay, list[dict[str, str]]]:
    initial = c.initial_material([{'id': 0, 'sequence_hex': b'%%A'.hex()},
                                  {'id': 1, 'sequence_hex': b'CD'.hex()},
                                  {'id': 2, 'sequence_hex': b'E'.hex()}], 'histogram', 0, c.MAXL0)
    material = [
        dict(tick='1', index='1', event='EVICT', outcome='REMOVED', before_ids='2', after_ids='', changes='2:0:45:00', proposal=''),
        dict(tick='1', index='2', event='CLEAVE', outcome='PLACED', before_ids='0;1', after_ids='0;1;3', changes='1:1:44:00;3:0:00:44', proposal=''),
        dict(tick='2', index='3', event='EVICT', outcome='REMOVED', before_ids='3', after_ids='', changes='3:0:44:00', proposal=''),
        dict(tick='2', index='4', event='CLEAVE', outcome='PLACED', before_ids='0;1', after_ids='0;4', changes='1:0:43:00;4:0:00:43', proposal=''),
    ]
    rows: list[dict[str, str]] = []
    delay = 500 if policy == 'DELAY500' else 0
    def emit(event: str, tick: int, **kw: Any) -> None:
        rows.append({**DEFAULTS, 'event': event, 'tick': str(tick), 'index': str(len(rows)+1),
                     'policy': policy, **{k: str(v) for k, v in kw.items()}})
    def idle(tick: int, idx: int, eligible: int = 0) -> None:
        emit('SELECT', tick, id=idx, count=int(tick >= eligible), eligible_tick=eligible, outcome='UNBOUND')
        emit('SURVIVE', tick, id=idx)
        if tick >= eligible:
            emit('SEARCH', tick, id=idx, count=0, outcome='EMPTY')
    emit('START', 0, eligible_tick=3, ids='0;1;2')
    emit('TICK', 0, ids='0;1;2')
    emit('SELECT', 0, id=0, count=1, outcome='UNBOUND'); emit('SURVIVE', 0, id=0)
    emit('SEARCH', 0, id=0, other=1, count=2, selected=0, outcome='SELECTED')
    emit('ENCOUNTER', 0, id=0, other=1, active=0, passive=1, count=2, selected=0, outcome='BOUND')
    idle(0, 2)
    emit('TICK', 1, ids='0;1;2')
    if next_victim:
        idle(1, 2)
    emit('SELECT', 1, id=0, other=1, count=1, outcome='ACTIVE'); emit('SURVIVE', 1, id=0, other=1)
    emit('DISPATCH', 1, active=0, passive=1, opcode=37, owner=0, offset=0)
    emit('DEATH', 1, id=2, outcome='EVICT', material_index=1)
    emit('BIRTH', 1, id=3, active=0, passive=1, source=1, eligible_tick=2+delay, material_index=2)
    emit('COMPLETE', 1, active=0, passive=1, material_index=2)
    emit('TICK', 2, ids='3;0;1')
    if not delay:
        emit('RELEASE', 2, id=3, eligible_tick=2)
    idle(2, 3, 2+delay)
    emit('SELECT', 2, id=0, other=1, count=1, outcome='ACTIVE'); emit('SURVIVE', 2, id=0, other=1)
    emit('DISPATCH', 2, active=0, passive=1, opcode=37, owner=0, offset=1, material_index=2)
    emit('DEATH', 2, id=3, eligible_tick=2+delay, outcome='EVICT', material_index=3)
    emit('DEATH', 2, id=1, outcome='CLEAVE', material_index=4)
    emit('BIRTH', 2, id=4, active=0, passive=1, source=1, eligible_tick=3+delay, material_index=4)
    emit('COMPLETE', 2, active=0, passive=1, material_index=4)
    emit('CENSOR', 3, id=4, eligible_tick=3+delay)
    emit('END', 3, ids='4;0', material_index=4)
    return BoundaryReplay(initial, material, policy, 3), rows


@pytest.mark.parametrize('policy', ['IMMEDIATE', 'DELAY500'])
@pytest.mark.parametrize('next_victim', [False, True])
def test_ordered_eviction_lifecycle(policy: str, next_victim: bool) -> None:
    replay, rows = fixture(policy, next_victim)
    for row in rows:
        replay.step(row)
    summary = replay.summary(3)
    assert summary['evicted_before_eligibility'] == int(policy == 'DELAY500')
    assert summary['decayed_before_eligibility'] == 0
    assert replay.source.material.evictions == 2 and not replay.pairs
    assert replay.source.replacement_depth == {0: 0, 1: 0, 2: 0, 3: 1, 4: None}
    assert replay.source.replacement_summary()['qualifying_transfers'] == 1
    assert replay.source.material.buffers.keys() == {0, 4}


@pytest.mark.parametrize('kind', ['missing-death', 'wrong-cause', 'wrong-victim', 'early-release', 'wrong-eligibility',
                                  'duplicate-death', 'wrong-material', 'wrong-order', 'wrong-end', 'spurious-retirement'])
def test_boundary_corruption_is_terminal(kind: str) -> None:
    replay, rows = fixture()
    death = next(i for i, row in enumerate(rows) if row['event'] == 'DEATH')
    if kind == 'missing-death':
        rows.pop(death)
    elif kind == 'wrong-cause':
        rows[death]['outcome'] = 'DECAY'
    elif kind == 'wrong-victim':
        rows[death]['id'] = '0'
    elif kind == 'early-release':
        row = deepcopy(rows[death]); row.update(event='RELEASE', id='3', eligible_tick='502')
        rows.insert(death, row)
    elif kind == 'wrong-eligibility':
        rows[death]['eligible_tick'] = '1'
    elif kind == 'duplicate-death':
        rows.insert(death, rows[death].copy())
    elif kind == 'wrong-material':
        rows[death]['material_index'] = '2'
    elif kind == 'wrong-order':
        rows[death], rows[death+1] = rows[death+1], rows[death]
    elif kind == 'wrong-end':
        rows[-1]['ids'] = '0;4'
    else:
        replay.material[0]['event'] = 'RETIRE'
    for index, row in enumerate(rows, 1):
        row['index'] = str(index)
    with pytest.raises(ValueError):
        for row in rows:
            replay.step(row)
    assert replay.failed
    with pytest.raises(ValueError, match='already failed'):
        replay.step(rows[0])
    with pytest.raises(ValueError):
        replay.summary(3)
