"""SM-B003 candidate design oracle, NOT a native adapter or assay launcher.

Pure pre-admission selection, full-buffer refund projection, lineage isolation,
and fixed-denominator decision rules. Native transaction/replay gates are absent.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import math

from experiments.stringmol.analyze_conservation import ALPHABET, LIMIT, MAXL0
from experiments.stringmol.analyze_lineage import require


class Admission(str, Enum):
    NATIVE = 'NATIVE_VACANCY'
    REJECT = 'STRATIFIED_REJECT'
    REPLACE = 'STRATIFIED_REPLACE'


class Schedule(str, Enum):
    IMMEDIATE = 'IMMEDIATE'
    DELAY500 = 'DELAY500'


class Role(str, Enum):
    UNBOUND = 'UNBOUND'
    ACTIVE = 'ACTIVE'
    PASSIVE = 'PASSIVE'


class Channel(str, Enum):
    VACANT = 'VACANT'
    OCCUPIED = 'OCCUPIED'


class Disposition(str, Enum):
    VACANCY = 'ADMIT_VACANCY'
    REPLACEMENT = 'ADMIT_REPLACEMENT'
    REJECT = 'REJECT_OCCUPIED'
    UNAVAILABLE = 'NO_CANDIDATE'


# Reservations only. No claim of unseen execution history or launch eligibility.
SEEDS = tuple(range(202629000, 202629020))
MATRIX = tuple((schedule, admission, seed) for seed in SEEDS
               for schedule in Schedule for admission in Admission)
SYMBOLS = tuple(ALPHABET.encode('ascii'))


@dataclass(frozen=True)
class Actor:
    identity: int
    buffer: bytes
    role: Role = Role.UNBOUND
    partner: int | None = None
    eligible_tick: int = 0


@dataclass(frozen=True)
class Slot:
    x: int
    y: int
    actor: Actor | None = None


@dataclass(frozen=True)
class Plan:
    channel: Channel
    disposition: Disposition
    draws: int
    candidates: tuple[tuple[int, int], ...]
    target: tuple[int, int] | None
    incumbent: int | None
    refund: tuple[int, ...]


def histogram(buffer: bytes) -> tuple[int, ...]:
    require(len(buffer) == MAXL0 and buffer[-1] == 0, 'full allocated buffer and reserved terminator required')
    require(all(value == 0 or value in SYMBOLS for value in buffer), 'invalid buffer symbol')
    counts = Counter(buffer)
    return tuple(counts[symbol] for symbol in SYMBOLS)


def projected_pool(pool: tuple[int, ...], refund: tuple[int, ...]) -> tuple[int, ...]:
    require(len(pool) == len(refund) == len(SYMBOLS), 'pool alphabet dimension')
    require(all(type(value) is int and 0 <= value <= LIMIT for value in (*pool, *refund)), 'pool integer bounds')
    result = tuple(left + right for left, right in zip(pool, refund, strict=True))
    require(all(value <= LIMIT for value in result), 'pool refund overflow')
    return result


def validate_grid(slots: tuple[Slot, ...], width: int, height: int,
                  participants: tuple[int, int]) -> None:
    require(type(width) is int and type(height) is int and width > 0 and height > 0, 'grid dimensions')
    require(tuple((slot.x, slot.y) for slot in slots) == tuple((x, y) for x in range(width) for y in range(height)), 'complete x-major grid')
    require(all(type(slot.x) is int and type(slot.y) is int for slot in slots), 'integer grid coordinates')
    actors = {slot.actor.identity: slot.actor for slot in slots if slot.actor is not None}
    require(len(actors) == sum(slot.actor is not None for slot in slots), 'duplicate grid identity')
    for actor in actors.values():
        require(type(actor.identity) is int and actor.identity >= 0 and isinstance(actor.role, Role), 'actor identity/role')
        require(type(actor.eligible_tick) is int and 0 <= actor.eligible_tick <= 2**64 - 1, 'eligibility tick bounds')
        histogram(actor.buffer)
        if actor.role is Role.UNBOUND:
            require(actor.partner is None, 'unbound actor has partner')
        else:
            require(type(actor.partner) is int and actor.partner >= 0, 'bound partner identity')
            partner = actors.get(actor.partner) if actor.partner is not None else None
            other_role = Role.PASSIVE if actor.role is Role.ACTIVE else Role.ACTIVE
            require(partner is not None and partner.partner == actor.identity and partner.role is other_role, 'reciprocal binding required')
    require(len(participants) == 2 and participants[0] != participants[1] and all(type(identity) is int and identity in actors for identity in participants), 'two extant participants')
    active, passive = (actors[identity] for identity in participants)
    require(active.role is Role.ACTIVE and passive.role is Role.PASSIVE and active.partner == passive.identity, 'current bound pair')


def uniform(value: float | None) -> float:
    require(value is not None and not isinstance(value, bool) and math.isfinite(value) and 0 <= value < 1, 'uniform must be finite in [0,1)')
    assert value is not None
    return value


def plan(admission: Admission, slots: tuple[Slot, ...], width: int, height: int,
         participants: tuple[int, int], *, channel_draw: float | None = None,
         rank_draw: float | None = None) -> Plan:
    """Plan one already-staged nonempty child; never mutate grid, buffers or RNG.

    Native fixtures must supply and independently validate actual MT draw values.
    This oracle checks draw demand/selection, not the engine's RNG implementation.
    """
    require(isinstance(admission, Admission), 'unknown admission mode')
    validate_grid(slots, width, height, participants)
    if admission is Admission.NATIVE:
        require(channel_draw is None, 'native mode must not draw a channel')
        channel, draws = Channel.VACANT, 0
    else:
        channel = Channel.OCCUPIED if uniform(channel_draw) < 0.5 else Channel.VACANT
        draws = 1
    candidates = tuple(slot for slot in slots if
                       (slot.actor is None if channel is Channel.VACANT else
                        slot.actor is not None and slot.actor.identity not in participants and
                        slot.actor.role is Role.UNBOUND and slot.actor.buffer[0] != 0))
    coordinates = tuple((slot.x, slot.y) for slot in candidates)
    zero = (0,) * len(SYMBOLS)
    if not candidates:
        require(rank_draw is None, 'empty candidate set must not consume rank draw')
        return Plan(channel, Disposition.UNAVAILABLE, draws, coordinates, None, None, zero)
    selected = candidates[math.floor(uniform(rank_draw) * len(candidates))]
    target = (selected.x, selected.y)
    if selected.actor is None:
        return Plan(channel, Disposition.VACANCY, draws + 1, coordinates, target, None, zero)
    replace = admission is Admission.REPLACE
    return Plan(channel, Disposition.REPLACEMENT if replace else Disposition.REJECT, draws + 1,
                coordinates, target, selected.actor.identity, histogram(selected.actor.buffer) if replace else zero)


@dataclass(frozen=True)
class Transfer:
    source: int | None
    child: int
    qualifying_partial: bool
    replaced: bool


def replacement_depths(initial: tuple[int, ...], births: tuple[Transfer, ...]) -> dict[int, int | None]:
    """All births in causal order; qualifying_partial must come from VM replay.

    A vacancy/relocation/orphan path never reconnects to the replacement-only DAG.
    Victim identity deliberately is not an ancestry input.
    """
    require(len(initial) == len(set(initial)) and all(type(i) is int and i >= 0 for i in initial), 'unique initial identities')
    depths: dict[int, int | None] = dict.fromkeys(initial, 0)
    for birth in births:
        require(type(birth.child) is int and birth.child >= 0 and birth.child not in depths, 'fresh child identity')
        require(type(birth.qualifying_partial) is bool and type(birth.replaced) is bool, 'verified boolean edge labels')
        require(birth.source is None or (type(birth.source) is int and birth.source in depths), 'source must precede child')
        require(not birth.qualifying_partial or birth.source is not None, 'unknown partial source')
        parent = depths[birth.source] if birth.source is not None else None
        depths[birth.child] = parent + 1 if parent is not None and birth.qualifying_partial and birth.replaced else None
    return depths


@dataclass(frozen=True)
class Continuity:
    transfers: int = 0
    renewing: int = 0
    serial: int = 0
    depth: int = 0
    late: int = 0
    retained_late: int = 0

    @property
    def values(self) -> tuple[int, ...]:
        return (self.transfers, self.renewing, self.serial, self.depth, self.late, self.retained_late)

    @property
    def valid(self) -> bool:
        return (all(type(value) is int and value >= 0 for value in self.values) and
                self.retained_late <= self.late <= self.renewing <= self.serial <= self.transfers and
                self.depth <= self.transfers and (self.depth > 0) == (self.transfers > 0) and
                (self.serial == 0 or self.depth >= 2))

    @property
    def passed(self) -> bool:
        return self.valid and all(value >= threshold for value, threshold in zip(self.values, (100, 10, 50, 2, 5, 5), strict=True))


@dataclass(frozen=True)
class Outcome:
    schedule: Schedule
    admission: Admission
    seed: int
    integrity: bool
    all_edges: Continuity = Continuity()
    replacement_edges: Continuity = Continuity()
    partial_opportunities: int = 0
    partial_commits: int = 0

    @property
    def valid(self) -> bool:
        if not isinstance(self.schedule, Schedule) or not isinstance(self.admission, Admission) or self.integrity is not True or not self.all_edges.valid or not self.replacement_edges.valid:
            return False
        if not all(type(value) is int and value >= 0 for value in (self.partial_opportunities, self.partial_commits)):
            return False
        if any(replacement > total for replacement, total in zip(self.replacement_edges.values, self.all_edges.values, strict=True)):
            return False
        if self.admission is Admission.REPLACE:
            return self.partial_commits == self.partial_opportunities and self.replacement_edges.transfers <= self.partial_commits
        return (self.partial_commits == 0 and self.replacement_edges == Continuity() and
                (self.admission is not Admission.NATIVE or self.partial_opportunities == 0))


class Decision(str, Enum):
    INTEGRITY = 'Unevaluable integrity'
    CONTROL = 'Valid native-control failure'
    EXPOSURE = 'Inadequate replacement exposure'
    BOTH = 'Robust replacement-only transmission across schedules'
    IMMEDIATE = 'Robust replacement-only transmission under immediate scheduling only'
    DELAYED = 'Robust replacement-only transmission under delayed scheduling only'
    NEITHER = 'Robust replacement-only continuity not established'


def decide(outcomes: tuple[Outcome, ...]) -> Decision:
    """Synthetic design classifier only: not an authority to launch native assays."""
    by = {(row.schedule, row.admission, row.seed): row for row in outcomes}
    if len(outcomes) != len(by) or set(by) != set(MATRIX) or not all(row.valid for row in outcomes):
        return Decision.INTEGRITY
    def count(schedule: Schedule, admission: Admission, replacement: bool = False) -> int:
        return sum((by[schedule, admission, seed].replacement_edges if replacement else
                    by[schedule, admission, seed].all_edges).passed for seed in SEEDS)
    if any(count(schedule, Admission.NATIVE) < 16 for schedule in Schedule):
        return Decision.CONTROL
    if any(sum(by[schedule, Admission.REPLACE, seed].partial_commits >= 100 for seed in SEEDS) < 16 for schedule in Schedule):
        return Decision.EXPOSURE
    immediate = count(Schedule.IMMEDIATE, Admission.REPLACE, True) >= 16
    delayed = count(Schedule.DELAY500, Admission.REPLACE, True) >= 16
    if immediate and delayed:
        return Decision.BOTH
    if immediate:
        return Decision.IMMEDIATE
    return Decision.DELAYED if delayed else Decision.NEITHER
