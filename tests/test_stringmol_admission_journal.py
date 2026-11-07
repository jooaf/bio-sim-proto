"""SM-B003 synthetic wire/selection checks; no native population or held-out run."""
from dataclasses import replace
from pathlib import Path
import math
import struct

import pytest

from experiments.stringmol import admission_design as a, admission_journal as j
from experiments.stringmol.analyze_conservation import MAXL0


def buf(prefix: bytes) -> bytes:
    return prefix + bytes(MAXL0 - len(prefix))


def wire_vector(values: tuple[int, ...]) -> str:
    return ';'.join(map(str, values))


def counters(proposals: int = 0, evictions: int = 0, partial: int = 0, commits: int = 0,
             returns: tuple[int, ...] = j.ZERO) -> dict[str, str]:
    return dict(zip(j.COUNTERS, (str(proposals), str(evictions), str(partial), str(commits), wire_vector(returns)), strict=True))


def changed(row: j.Row, **fields: str) -> j.Row:
    values = list(row.values)
    for key, value in fields.items():
        values[j.COLUMN_INDEX[key]] = value
    return j.Row(tuple(values))


def fixture(mode: a.Admission = a.Admission.REPLACE, schedule: a.Schedule = a.Schedule.IMMEDIATE,
            *, vacant: bool = False, offset: int = 1) -> tuple[j.Header, tuple[j.Row, ...], j.SelectionState]:
    header = j.Header(mode, schedule, 50, 3, 2)
    slots = (a.Slot(0, 0, a.Actor(0, buf(b'%ABC'), a.Role.ACTIVE, 1)),
             a.Slot(0, 1, a.Actor(1, buf(b'DEF'), a.Role.PASSIVE, 0)),
             a.Slot(1, 0, a.Actor(2, buf(b'A\0BB'), eligible_tick=500)),
             a.Slot(1, 1), a.Slot(2, 0), a.Slot(2, 1))
    state = j.SelectionState(slots, (2,), (), 0, 1, 0, offset, 3, 3, 5, 10)
    channel_value = None if mode is a.Admission.NATIVE else (0.75 if vacant else 0.25)
    plan = a.plan(mode, slots, 3, 2, (0, 1), channel_draw=channel_value, rank_draw=0.0)
    occupied = plan.channel is a.Channel.OCCUPIED
    replacing = plan.disposition is a.Disposition.REPLACEMENT
    admitted = plan.disposition in (a.Disposition.REPLACEMENT, a.Disposition.VACANCY)
    partial = occupied and offset > 0
    alive = offset > 0
    assert plan.target is not None
    begin = j.Row.make(header, j.Event.BEGIN, 10, 2, 1, {
        'material_index': '3', 'boundary_index': '5', 'now_ids': '2', 'next_ids': '', 'population': '3',
        'active': '0', 'passive': '1', 'source': '0', 'offset': str(offset), 'child': '3',
        'channel': plan.channel.value, 'channel_bits': '' if channel_value is None else j.uniform_bits(channel_value),
        'rank_bits': j.uniform_bits(0.0), 'vacant_count': '3', 'occupied_count': '1',
        'target_x': str(plan.target[0]), 'target_y': str(plan.target[1]),
        'victim': '2' if occupied else '', 'victim_eligible_tick': '500' if occupied else '',
        'victim_owner': 'NOW' if occupied else '', 'victim_buffer': buf(b'A\0BB').hex().upper() if occupied else '',
        'source_buffer': buf(b'%ABC').hex().upper(), 'child_buffer': buf(b'%ABC'[offset:]).hex().upper(),
        'partial_opportunity': str(int(partial))})
    now = '' if replacing else '2'
    next_ids = ';'.join(str(i) for i in ([3] if admitted else []) + ([0] if alive else []) + [1])
    population = 3 + int(admitted) - int(replacing) - int(not alive)
    final_counters = counters(1, int(replacing), int(partial), int(partial and replacing), plan.refund)
    resolve = j.Row.make(header, j.Event.RESOLVE, 10, 3, 1, {
        'material_index': '5' if replacing else '4', 'boundary_index': '8',
        'now_ids': now, 'next_ids': next_ids, 'population': str(population),
        'disposition': plan.disposition.value, 'eviction_material_index': '4' if replacing else '',
        'cleave_material_index': '5' if replacing else '4', 'death_index': '6' if replacing else '',
        'birth_index': '7' if admitted else '', 'child_eligible_tick': str(11 + (500 if schedule is a.Schedule.DELAY500 else 0)) if admitted else '',
        'source_alive': str(int(alive)), **final_counters})
    start = j.Row.make(header, j.Event.START, 0, 1, 0, {'material_index': '0', 'boundary_index': '1',
                       'now_ids': '0;1;2', 'next_ids': '', 'population': '3', **counters()})
    end = j.Row.make(header, j.Event.END, 50, 4, 0, {'material_index': '10', 'boundary_index': '12',
                     'now_ids': ';'.join(x for x in (now, next_ids) if x), 'next_ids': '', 'population': str(population), **final_counters})
    return header, (start, begin, resolve, end), state


@pytest.mark.parametrize('mode', list(a.Admission))
@pytest.mark.parametrize('schedule', list(a.Schedule))
@pytest.mark.parametrize('vacant', [False, True])
def test_all_policy_schedules_and_channels_roundtrip(tmp_path: Path, mode: a.Admission, schedule: a.Schedule, vacant: bool) -> None:
    header, rows, state = fixture(mode, schedule, vacant=vacant)
    path = tmp_path / j.NAME
    path.write_text(','.join(j.COLUMNS) + '\n' + ''.join(row.encode() for row in rows), encoding='ascii')
    decoded = tuple(j.read(path))
    assert decoded == rows
    expected = j.check_selection(rows[1], header, state)
    result = j.audit_structure(decoded, header)
    assert result.proposals == 1 and result.evictions == int(expected.disposition is a.Disposition.REPLACEMENT)
    assert result.eviction_returns == expected.refund
    assert 'independent linked-state replay still required' in result.scope


def test_hidden_refund_and_future_eligibility_are_preserved() -> None:
    header, rows, state = fixture()
    assert j.check_selection(rows[1], header, state).incumbent == 2
    result = j.audit_structure(rows, header)
    assert sum(result.eviction_returns) == 3  # visible A plus hidden BB
    assert result.partial_opportunities == result.partial_commits == 1
    corrupted = (rows[0], rows[1], changed(rows[2], eviction_returns=wire_vector(a.histogram(buf(b'A')))), rows[3])
    with pytest.raises(ValueError, match='full-buffer'):
        j.audit_structure(corrupted, header)


def test_whole_transfer_is_not_partial_exposure() -> None:
    header, rows, state = fixture(offset=0)
    j.check_selection(rows[1], header, state)
    result = j.audit_structure(rows, header)
    assert result.evictions == 1 and result.partial_opportunities == result.partial_commits == 0
    assert rows[2]['population'] == '2' and rows[2]['source_alive'] == '0'


def cleanup_case(source: int, empty_partner: bool, offset: int) -> tuple[j.Header, tuple[j.Row, ...], j.SelectionState]:
    header, rows, state = fixture(offset=offset)
    slots = list(state.slots)
    for identity in (0, 1):
        actor = slots[identity].actor
        assert actor is not None
        content = b'%ABC' if identity == source else (b'' if empty_partner else b'DEF')
        slots[identity] = replace(slots[identity], actor=replace(actor, buffer=buf(content)))
    state = replace(state, slots=tuple(slots), source=source)
    empty = {identity for identity in (0, 1) if (identity == source and offset == 0) or (identity != source and empty_partner)}
    removed = next((identity for identity in (0, 1) if identity in empty), None)
    survivors = [identity for identity in (0, 1) if identity != removed]
    next_ids = ';'.join(map(str, [3, *survivors]))
    population = str(1 + len(survivors))
    begin = changed(rows[1], source=str(source))
    resolved = changed(rows[2], next_ids=next_ids, population=population, source_alive=str(int(source != removed)))
    end = changed(rows[3], now_ids=next_ids, population=population)
    return header, (rows[0], begin, resolved, end), state


@pytest.mark.parametrize('source', [0, 1])
@pytest.mark.parametrize('empty_partner', [False, True])
@pytest.mark.parametrize('offset', [0, 1])
def test_native_cleanup_is_active_first_and_removes_at_most_one(source: int, empty_partner: bool, offset: int) -> None:
    header, rows, state = cleanup_case(source, empty_partner, offset)
    j.check_selection(rows[1], header, state)
    j.check_native_cleanup(rows[1], rows[2], state)
    summary = j.audit_structure(rows, header)
    assert summary.partial_commits == int(offset > 0)
    if source == 1 and empty_partner and offset == 0:
        assert rows[2]['source_alive'] == '1' and rows[2]['next_ids'] == '3;1'


def test_wrong_empty_participant_death_needs_independent_cleanup_check() -> None:
    header, rows, state = cleanup_case(1, True, 0)
    forged = changed(rows[2], next_ids='3;0', source_alive='0')
    j.audit_structure((rows[0], rows[1], forged, changed(rows[3], now_ids='3;0')), header)
    with pytest.raises(ValueError, match='active-first'):
        j.check_native_cleanup(rows[1], forged, state)


def test_native_cleanup_cannot_delete_both_empty_participants() -> None:
    header, rows, state = cleanup_case(0, True, 0)
    forged = changed(rows[2], next_ids='3', population='1')
    with pytest.raises(ValueError, match='active-first'):
        j.audit_structure((rows[0], rows[1], forged, rows[3]), header)
    with pytest.raises(ValueError, match='active-first'):
        j.check_native_cleanup(rows[1], forged, state)


@pytest.mark.parametrize('bits', ['8000000000000000', '7FF0000000000000', '7FF8000000000000', '3FF0000000000000', '3fb999999999999a', '0'])
def test_noncanonical_or_nonuniform_bits_rejected(bits: str) -> None:
    with pytest.raises(ValueError):
        j.uniform(bits)


def test_native_mt_lattice_and_absent_draw_are_distinct() -> None:
    assert j.uniform('') is None
    for value in (0.0, 0.5, (2**32 - 1) * 2**-32):
        assert j.uniform(j.uniform_bits(value)) == value
    for value in (0.1, math.nextafter(1.0, 0), -0.0):
        with pytest.raises(ValueError):
            j.uniform_bits(value)
    with pytest.raises(ValueError):
        j.uniform(struct.pack('>d', 0.1).hex().upper())


@pytest.mark.parametrize('event_index,fields', [
    (0, {'source_disposition': 'RETIRE'}), (0, {'transaction': '1'}),
    (1, {'source': '2'}), (1, {'offset': '4'}), (1, {'partial_opportunity': '0'}),
    (1, {'victim': '0'}), (1, {'victim_owner': 'NEXT'}), (1, {'rank_bits': ''}),
    (1, {'active': '00'}), (1, {'child': '2'}), (1, {'victim_buffer': ''}),
    (2, {'eviction_material_index': '3'}), (2, {'cleave_material_index': '4'}),
    (2, {'death_index': '8'}), (2, {'birth_index': ''}), (2, {'child_eligible_tick': '10'}),
    (2, {'disposition': 'ADMIT_VACANCY'}), (2, {'eviction_total': '2'}),
    (2, {'next_ids': '3;0;1;2', 'population': '4'}), (2, {'source_alive': '0'}),
    (2, {'partial_commit_total': '0'}), (2, {'victim_buffer': '00'}),
    (3, {'tick': '49'}), (3, {'boundary_index': '8'}), (3, {'partial_total': '2'})])
def test_corrupt_framing_counters_and_links_are_fatal(event_index: int, fields: dict[str, str]) -> None:
    header, rows, _ = fixture()
    corrupted = list(rows)
    corrupted[event_index] = changed(corrupted[event_index], **fields)
    with pytest.raises(ValueError):
        j.audit_structure(corrupted, header)


@pytest.mark.parametrize('indices', [(1, 2, 3), (0, 1), (0, 2, 3), (0, 1, 1, 2, 3), (0, 1, 2), (0, 1, 2, 3, 3)])
def test_missing_duplicate_or_unclosed_transactions(indices: tuple[int, ...]) -> None:
    header, rows, _ = fixture()
    with pytest.raises(ValueError):
        j.audit_structure(tuple(rows[i] for i in indices), header)


def test_internally_consistent_wrong_target_needs_real_selection_replay() -> None:
    header, rows, state = fixture(a.Admission.NATIVE)
    forged = changed(rows[1], target_x='2', target_y='1')
    # Framing alone cannot prove a claimed selected cell. Do not mistake it for integrity.
    j.audit_structure((rows[0], forged, rows[2], rows[3]), header)
    with pytest.raises(ValueError, match='target differs'):
        j.check_selection(forged, header, state)


@pytest.mark.parametrize('change', ['flow', 'child', 'material', 'queue', 'source', 'victim', 'early', 'missing_owner'])
def test_independent_selection_state_must_match(change: str) -> None:
    header, rows, state = fixture()
    if change == 'flow':
        state = replace(state, offset=2)
    elif change == 'child':
        state = replace(state, child=4)
    elif change == 'material':
        state = replace(state, material_index=2)
    elif change == 'queue':
        state = replace(state, now=(), next_ids=(2,))
    elif change == 'missing_owner':
        state = replace(state, now=())
    else:
        slots = list(state.slots)
        index = 2 if change == 'victim' else 0
        actor = slots[index].actor
        assert actor is not None
        actor = replace(actor, eligible_tick=11) if change == 'early' else replace(actor, buffer=buf(b'A'))
        slots[index] = replace(slots[index], actor=actor)
        state = replace(state, slots=tuple(slots))
    with pytest.raises(ValueError):
        j.check_selection(rows[1], header, state)


@pytest.mark.parametrize('mode', [a.Admission.REJECT, a.Admission.REPLACE])
def test_empty_selected_category_never_falls_back_to_available_vacancy(mode: a.Admission) -> None:
    header, original, state = fixture(mode)
    start, begin, resolve, end = original
    slots = list(state.slots)
    slots[2] = replace(slots[2], actor=None)
    state = replace(state, slots=tuple(slots), now=())
    start = changed(start, now_ids='0;1', population='2')
    begin = changed(begin, population='2', now_ids='', occupied_count='0', vacant_count='4',
                    rank_bits='', target_x='', target_y='', victim='', victim_eligible_tick='',
                    victim_owner='', victim_buffer='', partial_opportunity='0')
    resolve = changed(resolve, disposition=a.Disposition.UNAVAILABLE.value, population='2',
                      now_ids='', next_ids='0;1', material_index='4', cleave_material_index='4',
                      eviction_material_index='', death_index='', birth_index='', child_eligible_tick='',
                      **counters(proposals=1))
    end = changed(end, now_ids='0;1', population='2', **counters(proposals=1))
    assert j.check_selection(begin, header, state).disposition is a.Disposition.UNAVAILABLE
    assert j.audit_structure((start, begin, resolve, end), header).evictions == 0
    with pytest.raises(ValueError, match='resample'):
        j.audit_structure((start, changed(begin, rank_bits=j.uniform_bits(0.0)), resolve, end), header)


def test_empty_and_early_extinct_run_are_valid_framing_not_a_pass() -> None:
    header = j.Header(a.Admission.NATIVE, a.Schedule.IMMEDIATE, 50, 3, 2)
    fields = {'material_index': '0', 'boundary_index': '1', 'now_ids': '', 'next_ids': '', 'population': '0', **counters()}
    start = j.Row.make(header, j.Event.START, 0, 1, 0, fields)
    end = j.Row.make(header, j.Event.END, 0, 2, 0, {**fields, 'boundary_index': '2'})
    assert j.audit_structure((start, end), header).proposals == 0
    with pytest.raises(ValueError, match='incomplete'):
        j.audit_structure((), header)


@pytest.mark.parametrize('mutation', ['crlf', 'no_lf', 'header', 'extra', 'large'])
def test_wire_noncanonical_or_oversized_file_rejected(tmp_path: Path, mutation: str) -> None:
    _, rows, _ = fixture()
    raw = ','.join(j.COLUMNS) + '\n' + ''.join(row.encode() for row in rows)
    if mutation == 'crlf':
        raw = raw.replace('\n', '\r\n')
    elif mutation == 'no_lf':
        raw = raw[:-1]
    elif mutation == 'header':
        raw = raw.replace('version,event', 'event,version', 1)
    elif mutation == 'extra':
        raw += '\n'
    else:
        raw = ','.join(j.COLUMNS) + '\n' + 'X' * (j.MAX_LINE + 1) + '\n'
    path = tmp_path / j.NAME
    path.write_bytes(raw.encode('ascii'))
    with pytest.raises(ValueError):
        tuple(j.read(path))
