"""Material-derived replacement ancestry, isolated from VM/scheduling proof."""
import pytest

from experiments.stringmol import analyze_conservation as c
from experiments.stringmol.admission_source import SourceReplay
from experiments.stringmol.analyze_lineage import require


def source() -> SourceReplay:
    return SourceReplay(c.initial_material([
        {'id': 0, 'sequence_hex': b'%'.hex()},
        {'id': 1, 'sequence_hex': (b'A' * 64).hex()},
        {'id': 2, 'sequence_hex': b'E'.hex()},
    ], 'uniform', 128, c.MAXL0))


def emit(replay: SourceReplay, tick: int, event: str, before: dict[int, bytes], after: dict[int, bytes]) -> None:
    changes: list[str] = []
    for idx in sorted(before.keys() | after.keys()):
        old, new = before.get(idx, bytes(c.MAXL0)), after.get(idx, bytes(c.MAXL0))
        changes.extend(f'{idx}:{pos}:{a:02X}:{b:02X}' for pos, (a, b) in enumerate(zip(old, new, strict=True)) if a != b)
    replay.step(dict(tick=str(tick), index=str(replay.material.nums['event_count']+1), event=event,
                     outcome='PLACED' if event == 'CLEAVE' else 'REMOVED' if event == 'EVICT' else 'ACCEPTED',
                     before_ids=';'.join(map(str, sorted(before))), after_ids=';'.join(map(str, sorted(after))),
                     changes=';'.join(changes), proposal=''))


def birth(replay: SourceReplay, tick: int, parent: int, offset: int, victim: int | None = None) -> int:
    if victim is not None:
        emit(replay, tick, 'EVICT', {victim: replay.material.buffers[victim]}, {})
    before = {i: replay.material.buffers[i] for i in (0, parent)}
    child = max(replay.material.seen)+1
    visible = before[parent].split(b'\0', 1)[0]
    require(0 < offset < len(visible), 'fixture partial transfer')
    after = before | {parent: visible[:offset].ljust(c.MAXL0, b'\0'), child: visible[offset:].ljust(c.MAXL0, b'\0')}
    emit(replay, tick, 'CLEAVE', before, after)
    return child


def test_vacancy_descendant_cannot_reconnect_by_later_replacement() -> None:
    replay = source()
    first = birth(replay, 2500, 1, 32, 2)
    vacancy_child = birth(replay, 2501, first, 1)
    attempted_reconnection = birth(replay, 2502, vacancy_child, 1, 1)
    assert replay.replacement_depth[first] == 1
    assert replay.replacement_depth[vacancy_child] is None
    assert replay.replacement_depth[attempted_reconnection] is None
    assert replay.transfer_depth[attempted_reconnection] == 3
    summary = replay.replacement_summary()
    assert summary['qualifying_transfers'] == 1 and summary['orphan_transfers'] == 1
    assert summary['transfer_renewing_descendants'] == 0


def test_replacement_retention_uses_first_source_across_all_channels() -> None:
    replay = source()
    first = birth(replay, 2500, 1, 32, 2)
    vacancy_child = birth(replay, 2501, first, 1)
    frozen = replay.transfer_renewals[first].copy()
    assert frozen['retention'] == 1 and frozen['retained_late']
    # Change/grow the remnant into a different 32-byte genome. Each accepted
    # material COPY changes one position; the synthetic pool supplies B units.
    for pos in range(32):
        before = {i: replay.material.buffers[i] for i in (0, first)}
        changed = bytearray(before[first]); changed[pos] = ord('B')
        emit(replay, 2502, 'COPY', before, before | {first: bytes(changed)})
    second = birth(replay, 2503, first, 1, vacancy_child)
    assert replay.replacement_depth[second] == 2
    assert replay.replacement_renewals[first] == frozen
    summary = replay.replacement_summary()
    assert summary['qualifying_transfers'] == 2 and summary['serial_transfers'] == 1
    assert summary['retained_late_transfer_renewals'] == 1


def test_eviction_without_admission_poisoned() -> None:
    replay = source()
    emit(replay, 0, 'EVICT', {2: replay.material.buffers[2]}, {})
    with pytest.raises(ValueError, match='unfinished'):
        replay.replacement_summary()
    before = {i: replay.material.buffers[i] for i in (0, 1)}
    with pytest.raises(ValueError, match='immediately admitted'):
        emit(replay, 0, 'COPY', before, before)
    assert replay.invalid
    with pytest.raises(ValueError, match='already failed'):
        birth(replay, 0, 1, 32)


def test_no_replacement_credit_for_vacancy_only() -> None:
    replay = source()
    child = birth(replay, 0, 1, 32)
    descendant = birth(replay, 1, child, 1)
    assert replay.replacement_depth[child] is replay.replacement_depth[descendant] is None
    assert replay.replacement_summary()['qualifying_transfers'] == 0
    assert replay.transfer_summary()['qualifying_transfers'] == 2
