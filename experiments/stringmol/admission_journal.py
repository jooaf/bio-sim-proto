"""SM-B003 admission wire contract and structural checks, not full VM replay.

A well-framed transcript is NOT a scientific integrity pass. Independent material,
scheduling, grid/list, VM, source and lineage replay must supply the linked states.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
import re
import struct
from typing import Iterable, Iterator, Mapping

from experiments.stringmol import admission_design as design
from experiments.stringmol.analyze_conservation import ALPHABET, LIMIT, MAXL0
from experiments.stringmol.analyze_lineage import require

VERSION = 'SM-B003-ADMISSION-2'
NAME = 'admission_events007.csv'
MAX_LINE = 65536
COMMON = ('version', 'event', 'tick', 'index', 'transaction', 'policy', 'schedule', 'horizon', 'width', 'height', 'buffer_size', 'source_disposition')
STATE = ('material_index', 'boundary_index', 'now_ids', 'next_ids', 'population')
COUNTERS = ('proposal_total', 'eviction_total', 'partial_total', 'partial_commit_total', 'eviction_returns')
PROPOSAL = ('active', 'passive', 'source', 'offset', 'child', 'channel', 'channel_bits', 'rank_bits',
            'vacant_count', 'occupied_count', 'target_x', 'target_y', 'victim', 'victim_eligible_tick', 'victim_owner',
            'source_buffer', 'child_buffer', 'victim_buffer', 'partial_opportunity')
RESOLUTION = ('disposition', 'eviction_material_index', 'cleave_material_index', 'death_index', 'birth_index',
              'child_eligible_tick', 'source_alive')
COLUMNS = (*COMMON, *STATE, *COUNTERS, *PROPOSAL, *RESOLUTION)
COLUMN_INDEX = {name: index for index, name in enumerate(COLUMNS)}
ID_MAX = 2**31 - 1
ZERO = (0,) * len(ALPHABET)


class Event(str, Enum):
    START = 'START'
    BEGIN = 'BEGIN'
    RESOLVE = 'RESOLVE'
    END = 'END'


@dataclass(frozen=True)
class Header:
    policy: design.Admission
    schedule: design.Schedule
    horizon: int = 5000
    width: int = 40
    height: int = 40

    def __post_init__(self) -> None:
        require(isinstance(self.policy, design.Admission) and isinstance(self.schedule, design.Schedule), 'typed admission/schedule policy')
        require(type(self.horizon) is int and 1 <= self.horizon < 2**32, 'horizon bounds')
        require(all(type(n) is int and 1 <= n <= 40 for n in (self.width, self.height)), 'bounded grid dimensions')

    @property
    def fields(self) -> dict[str, str]:
        return {'version': VERSION, 'policy': self.policy.value, 'schedule': self.schedule.value,
                'horizon': str(self.horizon), 'width': str(self.width), 'height': str(self.height),
                'buffer_size': str(MAXL0), 'source_disposition': 'RETAIN'}


def number(raw: str, maximum: int = LIMIT) -> int:
    require(re.fullmatch(r'0|[1-9][0-9]*', raw) is not None, 'canonical nonnegative integer')
    value = int(raw)
    require(value <= maximum, 'integer overflow')
    return value


def identity(raw: str) -> int:
    return number(raw, ID_MAX)


def optional_number(raw: str, maximum: int = LIMIT) -> int | None:
    return None if raw == '' else number(raw, maximum)


def ids(raw: str) -> tuple[int, ...]:
    values = tuple(identity(value) for value in raw.split(';')) if raw else ()
    require(len(values) == len(set(values)), 'duplicate list identity')
    return values  # queue order is significant; do NOT sort


def vector(raw: str) -> tuple[int, ...]:
    values = tuple(number(value) for value in raw.split(';'))
    require(len(values) == len(ALPHABET), 'ALXII vector dimension')
    return values


def full_buffer(raw: str) -> bytes:
    require(len(raw) == 2 * MAXL0 and re.fullmatch(r'[0-9A-F]+', raw) is not None, 'canonical full-buffer hex')
    value = bytes.fromhex(raw)
    design.histogram(value)
    return value


def uniform_bits(value: float) -> str:
    require(math.isfinite(value) and 0 <= value < 1 and math.ldexp(value, 32).is_integer(), 'native MT uniform lattice')
    bits = struct.pack('>d', value).hex().upper()
    require(bits == struct.pack('>d', int(math.ldexp(value, 32)) * 2**-32).hex().upper(), 'canonical MT zero')
    return bits


def uniform(raw: str) -> float | None:
    if not raw:
        return None
    require(re.fullmatch(r'[0-9A-F]{16}', raw) is not None, 'canonical IEEE binary64 hex')
    value = float(struct.unpack('>d', bytes.fromhex(raw))[0])
    require(uniform_bits(value) == raw, 'canonical MT uniform')
    return value


@dataclass(frozen=True)
class Row:
    values: tuple[str, ...]

    def __post_init__(self) -> None:
        require(len(self.values) == len(COLUMNS), 'admission column count')
        require(sum(map(len, self.values)) + len(self.values) <= MAX_LINE, 'admission row size limit')
        require(all(value.isascii() and not any(c in value for c in ',\r\n"') for value in self.values), 'admission ASCII/no quoting')

    def __getitem__(self, name: str) -> str:
        return self.values[COLUMN_INDEX[name]]

    @property
    def event(self) -> Event:
        return Event(self['event'])

    def encode(self) -> str:
        return ','.join(self.values) + '\n'

    @classmethod
    def make(cls, header: Header, event: Event, tick: int, index: int, transaction: int,
             fields: Mapping[str, str]) -> Row:
        require(set(fields) <= set(COLUMNS) - set(COMMON), 'unexpected/reserved admission field')
        data = {**header.fields, 'event': event.value, 'tick': str(tick), 'index': str(index), 'transaction': str(transaction), **fields}
        return cls(tuple(data.get(name, '') for name in COLUMNS))


def read(path: Path) -> Iterator[Row]:
    with path.open(encoding='ascii', newline='') as stream:
        require(stream.readline() == ','.join(COLUMNS) + '\n', 'canonical admission header')
        while line := stream.readline(MAX_LINE + 1):
            require(len(line) <= MAX_LINE, 'admission row size limit')
            require(line.endswith('\n') and '\r' not in line, 'canonical admission LF')
            yield Row(tuple(line[:-1].split(',')))


def queues(row: Row, population: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    now, next_ids = ids(row['now_ids']), ids(row['next_ids'])
    require(not set(now) & set(next_ids), 'duplicate cross-list identity')
    require(len(now) + len(next_ids) <= population, 'list exceeds population')
    return now, next_ids


def proposal(row: Row, header: Header) -> design.Disposition:
    """Validate internal claims only. Real VM/grid state is checked separately."""
    active, passive, source, child = (identity(row[name]) for name in ('active', 'passive', 'source', 'child'))
    require(active != passive and source in (active, passive) and child not in (active, passive), 'proposal identities')
    raw_source, raw_child = full_buffer(row['source_buffer']), full_buffer(row['child_buffer'])
    offset = number(row['offset'], MAXL0 - 2)
    visible = raw_source.split(b'\0', 1)[0]
    require(offset < len(visible), 'nonempty staged proposal required')
    suffix = visible[offset:]
    require(raw_child == suffix + bytes(MAXL0 - len(suffix)), 'exact staged visible suffix')
    channel = design.Channel(row['channel'])
    channel_value, rank = uniform(row['channel_bits']), uniform(row['rank_bits'])
    if header.policy is design.Admission.NATIVE:
        require(channel_value is None and channel is design.Channel.VACANT, 'native channel/RNG parity')
    else:
        if channel_value is None:
            raise ValueError('missing channel draw')
        require(channel is (design.Channel.OCCUPIED if channel_value < 0.5 else design.Channel.VACANT), 'channel threshold')
    population = number(row['population'], header.width * header.height)
    require(population >= 2 and child not in (*ids(row['now_ids']), *ids(row['next_ids'])), 'staged child/participant population')
    vacancy, occupied = (number(row[name], header.width * header.height) for name in ('vacant_count', 'occupied_count'))
    require(vacancy + population == header.width * header.height and occupied <= max(0, population - 2), 'candidate/population counts')
    count = vacancy if channel is design.Channel.VACANT else occupied
    victim = optional_number(row['victim'], ID_MAX)
    x, y = optional_number(row['target_x'], header.width - 1), optional_number(row['target_y'], header.height - 1)
    require(number(row['partial_opportunity'], 1) == int(channel is design.Channel.OCCUPIED and count > 0 and offset > 0), 'pre-intervention partial opportunity')
    if count == 0:
        require(rank is None and x is None and y is None and victim is None, 'empty category must not resample')
        disposition = design.Disposition.UNAVAILABLE
    else:
        require(rank is not None and x is not None and y is not None, 'selected candidate/rank required')
        if channel is design.Channel.OCCUPIED:
            require(victim is not None and victim not in (active, passive, child), 'unrelated incumbent required')
            raw_victim = full_buffer(row['victim_buffer'])
            require(raw_victim[0] != 0, 'visibly nonempty incumbent required')
            number(row['victim_eligible_tick'], 2**64 - 1)  # future eligibility is NOT protection
            require(row['victim_owner'] in ('NOW', 'NEXT'), 'victim must have one list owner')
            owner_ids = ids(row['now_ids'] if row['victim_owner'] == 'NOW' else row['next_ids'])
            require(victim in owner_ids, 'claimed victim list owner')
            disposition = design.Disposition.REPLACEMENT if header.policy is design.Admission.REPLACE else design.Disposition.REJECT
        else:
            require(victim is None, 'vacancy cannot evict')
            disposition = design.Disposition.VACANCY
    if victim is None:
        require(all(row[name] == '' for name in ('victim_eligible_tick', 'victim_owner', 'victim_buffer')), 'spurious victim payload')
    return disposition


@dataclass(frozen=True)
class SelectionState:
    """Must be reconstructed by independent VM/scheduling replay, not this CSV."""
    slots: tuple[design.Slot, ...]
    now: tuple[int, ...]
    next_ids: tuple[int, ...]
    active: int
    passive: int
    source: int
    offset: int
    child: int
    material_index: int
    dispatch_index: int
    tick: int


def check_selection(row: Row, header: Header, state: SelectionState) -> design.Plan:
    require(row.event is Event.BEGIN, 'selection requires BEGIN')
    require(all(row[key] == value for key, value in header.fields.items()), 'selection header drift')
    expected = {'active': state.active, 'passive': state.passive, 'source': state.source, 'offset': state.offset, 'child': state.child,
                'material_index': state.material_index, 'boundary_index': state.dispatch_index, 'tick': state.tick}
    require(all(number(row[name]) == value for name, value in expected.items()), 'VM/dispatch linkage differs')
    require(ids(row['now_ids']) == state.now and ids(row['next_ids']) == state.next_ids, 'pre-admission queue order differs')
    actors = {slot.actor.identity: slot.actor for slot in state.slots if slot.actor is not None}
    listed = (*state.now, *state.next_ids)
    require(len(listed) == len(set(listed)) and set(listed) <= set(actors), 'independent list/grid ownership')
    require(set(actors) - {state.active, state.passive} <= set(listed), 'missing nonparticipant list owner')
    require(state.source in actors and state.active in actors and state.passive in actors, 'missing participant')
    require(actors[state.active].eligible_tick <= state.tick and actors[state.passive].eligible_tick <= state.tick, 'early dispatch')
    require(full_buffer(row['source_buffer']) == actors[state.source].buffer and number(row['population']) == len(actors), 'source/population differs')
    require(identity(row['child']) not in actors, 'child reuses live identity')
    expected_plan = design.plan(header.policy, state.slots, header.width, header.height, (state.active, state.passive),
                                channel_draw=uniform(row['channel_bits']), rank_draw=uniform(row['rank_bits']))
    vacancy = sum(slot.actor is None for slot in state.slots)
    occupied = sum(actor.role is design.Role.UNBOUND and actor.identity not in (state.active, state.passive) and actor.buffer[0] != 0 for actor in actors.values())
    require(number(row['vacant_count']) == vacancy and number(row['occupied_count']) == occupied, 'reconstructed candidate counts differ')
    target = None if row['target_x'] == '' else (number(row['target_x']), number(row['target_y']))
    require(expected_plan.target == target and expected_plan.incumbent == optional_number(row['victim']), 'reconstructed target differs')
    if expected_plan.incumbent is not None:
        victim = actors[expected_plan.incumbent]
        require(full_buffer(row['victim_buffer']) == victim.buffer and number(row['victim_eligible_tick']) == victim.eligible_tick, 'incumbent state differs')
        require(row['victim_owner'] == ('NOW' if victim.identity in state.now else 'NEXT'), 'incumbent queue differs')
    require(proposal(row, header) is expected_plan.disposition, 'proposal disposition differs')
    return expected_plan


def check_native_cleanup(begin: Row, resolved: Row, state: SelectionState) -> None:
    """Check native active-first cleanup against independent pre-dispatch buffers.

    This is a local check, not a replacement for full material/ownership replay.
    Native cleanup removes at most one participant, even if both become empty.
    """
    require(begin.event is Event.BEGIN and resolved.event is Event.RESOLVE, 'cleanup event pair')
    require(begin['transaction'] == resolved['transaction'] and begin['tick'] == resolved['tick'], 'cleanup transaction linkage')
    expected = {'active': state.active, 'passive': state.passive, 'source': state.source, 'offset': state.offset}
    require(all(number(begin[name]) == value for name, value in expected.items()), 'cleanup VM linkage')
    buffers = {slot.actor.identity: slot.actor.buffer for slot in state.slots if slot.actor is not None}
    require(state.active in buffers and state.passive in buffers and state.source in (state.active, state.passive), 'cleanup participants')
    source = full_buffer(begin['source_buffer'])
    require(source == buffers[state.source], 'cleanup source buffer differs')
    visible = len(source.split(b'\0', 1)[0])
    require(0 <= state.offset < visible, 'cleanup nonempty proposal')
    buffers[state.source] = source[:state.offset] + bytes(visible - state.offset) + source[visible:]
    removed = next((actor for actor in (state.active, state.passive) if buffers[actor][0] == 0), None)
    listed = (*ids(resolved['now_ids']), *ids(resolved['next_ids']))
    for actor in (state.active, state.passive):
        require((actor in listed) == (actor != removed), 'native active-first cleanup differs')
    require(number(resolved['source_alive'], 1) == int(state.source != removed), 'native source survival differs')


@dataclass(frozen=True)
class Structure:
    rows: int
    proposals: int
    evictions: int
    partial_opportunities: int
    partial_commits: int
    eviction_returns: tuple[int, ...]
    # Explicitly not a population integrity or launch certificate.
    scope: str = 'framing/counter checks only; independent linked-state replay still required'


def audit_structure(rows: Iterable[Row], header: Header) -> Structure:
    pending: Row | None = None
    disposition: design.Disposition | None = None
    count = tick = proposals = evictions = partials = commits = 0
    returns = ZERO
    started = ended = False
    last_child = -1
    last_material = last_boundary = -1
    for row in rows:
        require(not ended and number(row['index']) == count + 1, 'row ordering or data after END')
        require(all(row[key] == value for key, value in header.fields.items()), 'admission header drift')
        current_tick = number(row['tick'], header.horizon)
        require(current_tick >= tick, 'tick regression')
        tick = current_tick
        event = row.event
        transaction = number(row['transaction'])
        material, boundary = number(row['material_index']), number(row['boundary_index'])
        require(material >= last_material and boundary > last_boundary, 'cross-stream ordering')
        last_material, last_boundary = material, boundary
        population = number(row['population'], header.width * header.height)
        now, next_ids = queues(row, population)
        allowed = set(COMMON) | set(STATE)
        if event is Event.BEGIN:
            allowed |= set(PROPOSAL)
        else:
            allowed |= set(COUNTERS)
            if event is Event.RESOLVE:
                allowed |= set(RESOLUTION)
        require(all(row[name] == '' for name in set(COLUMNS) - allowed), 'nonempty unused field')
        if event is Event.START:
            require(not started and count == 0 and tick == transaction == material == 0 and boundary == 1, 'START identity')
            require(not next_ids and len(now) == population, 'START ownership')
            started = True
            last_child = max(now, default=-1)
        else:
            require(started, 'missing START')
        if event is Event.BEGIN:
            require(pending is None and transaction == proposals + 1 and tick < header.horizon, 'BEGIN transaction/order')
            disposition = proposal(row, header)
            child = identity(row['child'])
            require(child > last_child, 'proposal child ID reuse/regression')
            last_child = child
            pending = row
        elif event is Event.RESOLVE:
            if pending is None:
                raise ValueError('unmatched RESOLVE')
            require(transaction == proposals + 1 and tick == number(pending['tick']), 'unmatched RESOLVE')
            require(design.Disposition(row['disposition']) is disposition, 'resolution changed planned disposition')
            admitted = disposition in (design.Disposition.VACANCY, design.Disposition.REPLACEMENT)
            replaced = disposition is design.Disposition.REPLACEMENT
            before_material = number(pending['material_index'])
            require(number(row['cleave_material_index']) == material == before_material + 1 + int(replaced), 'EVICT/CLEAVE material order')
            eviction = optional_number(row['eviction_material_index'])
            death, birth = optional_number(row['death_index']), optional_number(row['birth_index'])
            if replaced:
                require(eviction == before_material + 1 and death is not None and birth is not None and
                        number(pending['boundary_index']) < death < birth < boundary, 'eviction/death/birth/completion order')
                returns = design.projected_pool(returns, design.histogram(full_buffer(pending['victim_buffer'])))
                require(identity(pending['victim']) not in (*now, *next_ids), 'victim remains scheduled')
            else:
                require(eviction is None and death is None, 'spurious eviction linkage')
            child = identity(pending['child'])
            if admitted:
                require(birth is not None and number(pending['boundary_index']) < birth < boundary, 'birth/completion link')
                require(number(row['child_eligible_tick']) == tick + 1 + (500 if header.schedule is design.Schedule.DELAY500 else 0), 'child eligibility changed')
                require(child in next_ids and child not in now, 'child schedule ownership')
            else:
                require(birth is None and row['child_eligible_tick'] == '' and child not in (*now, *next_ids), 'rejected child admitted')
            source_alive = number(row['source_alive'], 1)
            offset = number(pending['offset'])
            if offset > 0:
                require(source_alive == 1, 'nonempty source remnant removed')
            elif pending['source'] == pending['active']:
                require(source_alive == 0, 'empty active source not removed')
            require((identity(pending['source']) in (*now, *next_ids)) == bool(source_alive), 'source survival/list mismatch')
            cleanup = number(pending['population']) + int(admitted) - int(replaced) - population
            removed_participants = sum(identity(pending[name]) not in (*now, *next_ids) for name in ('active', 'passive'))
            require(cleanup in (0, 1) and cleanup == removed_participants and (offset > 0 or cleanup == 1),
                    'population accounting/active-first participant cleanup')
            require(len(now) + len(next_ids) == population, 'completed list ownership')
            proposals += 1
            evictions += replaced
            partials += number(pending['partial_opportunity'], 1)
            commits += replaced and bool(number(pending['partial_opportunity'], 1))
            pending = None
        elif event is Event.END:
            require(pending is None and transaction == 0 and not next_ids and len(now) == population, 'END/pending ownership')
            require(tick == header.horizon or population == 0, 'early nonextinct END')
            ended = True
        if event is not Event.BEGIN:
            require(tuple(number(row[name]) for name in COUNTERS[:-1]) == (proposals, evictions, partials, commits), 'cumulative admission counters')
            require(vector(row['eviction_returns']) == returns, 'distinct full-buffer eviction returns')
        count += 1
    require(started and ended and pending is None, 'incomplete admission transcript')
    return Structure(count, proposals, evictions, partials, commits, returns)
