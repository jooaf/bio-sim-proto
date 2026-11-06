"""Synthetic design checks only; no SM-B003 reserved seed is executed."""
from dataclasses import replace
from itertools import product
import math

import pytest

from experiments.stringmol import admission_design as a
from experiments.stringmol.analyze_conservation import ALPHABET, LIMIT, MAXL0


def buffer(prefix: bytes = b'A') -> bytes:
    return prefix + bytes(MAXL0 - len(prefix))


def grid(*, full: bool = False, victims: bool = True) -> tuple[a.Slot, ...]:
    actors = [a.Actor(0, buffer(), a.Role.ACTIVE, 1),
              a.Actor(1, buffer(), a.Role.PASSIVE, 0),
              a.Actor(2, buffer(b'A\0BB')) if victims else None,
              a.Actor(3, buffer(b'B'), eligible_tick=5000) if victims else None,
              a.Actor(4, buffer(), a.Role.ACTIVE, 5) if full else None,
              a.Actor(5, buffer(), a.Role.PASSIVE, 4) if full else None]
    return tuple(a.Slot(x, y, actor) for (x, y), actor in zip(product(range(3), range(2)), actors, strict=True))


def test_same_sampler_distinct_disposition_and_hidden_refund() -> None:
    slots = grid()
    reject = a.plan(a.Admission.REJECT, slots, 3, 2, (0, 1), channel_draw=0.0, rank_draw=0.0)
    replacement = a.plan(a.Admission.REPLACE, slots, 3, 2, (0, 1), channel_draw=0.0, rank_draw=0.0)
    assert reject.target == replacement.target == (1, 0)
    assert reject.candidates == replacement.candidates == ((1, 0), (1, 1))
    assert reject.incumbent == replacement.incumbent == 2
    assert reject.draws == replacement.draws == 2
    assert reject.disposition is a.Disposition.REJECT
    assert replacement.disposition is a.Disposition.REPLACEMENT
    assert sum(reject.refund) == 0 and sum(replacement.refund) == 3
    assert replacement.refund[ALPHABET.index('A')] == 1
    assert replacement.refund[ALPHABET.index('B')] == 2
    assert a.projected_pool(reject.refund, replacement.refund) == replacement.refund
    assert slots == grid()  # planning never mutates any source/victim state


@pytest.mark.parametrize('mode', list(a.Admission))
def test_vacancy_choice_and_native_draw_contract(mode: a.Admission) -> None:
    result = a.plan(mode, grid(), 3, 2, (0, 1), channel_draw=None if mode is a.Admission.NATIVE else 0.5, rank_draw=0.999)
    assert result.target == (2, 1) and result.incumbent is None
    assert result.disposition is a.Disposition.VACANCY and sum(result.refund) == 0
    assert result.draws == (1 if mode is a.Admission.NATIVE else 2)


def test_delayed_unbound_child_is_not_protected() -> None:
    result = a.plan(a.Admission.REPLACE, grid(), 3, 2, (0, 1), channel_draw=math.nextafter(0.5, 0), rank_draw=math.nextafter(1.0, 0))
    assert result.channel is a.Channel.OCCUPIED and result.incumbent == 3
    assert result.candidates == ((1, 0), (1, 1))


def test_no_resampling_empty_category_and_full_native_grid() -> None:
    full = grid(full=True)
    native = a.plan(a.Admission.NATIVE, full, 3, 2, (0, 1))
    assert native.disposition is a.Disposition.UNAVAILABLE and native.draws == 0
    vacancy = a.plan(a.Admission.REPLACE, full, 3, 2, (0, 1), channel_draw=0.8)
    assert vacancy.disposition is a.Disposition.UNAVAILABLE and vacancy.draws == 1
    occupied = a.plan(a.Admission.REPLACE, grid(victims=False), 3, 2, (0, 1), channel_draw=0.1)
    assert occupied.disposition is a.Disposition.UNAVAILABLE and occupied.draws == 1
    with pytest.raises(ValueError, match='rank draw'):
        a.plan(a.Admission.REPLACE, full, 3, 2, (0, 1), channel_draw=0.8, rank_draw=0.0)
    with pytest.raises(ValueError, match='channel'):
        a.plan(a.Admission.NATIVE, grid(), 3, 2, (0, 1), channel_draw=0.0, rank_draw=0.0)


@pytest.mark.parametrize('draw', [-0.01, 1.0, math.inf, math.nan])
def test_invalid_uniforms_are_integrity_errors(draw: float) -> None:
    with pytest.raises(ValueError, match='uniform'):
        a.plan(a.Admission.REPLACE, grid(), 3, 2, (0, 1), channel_draw=draw)
    with pytest.raises(ValueError, match='uniform'):
        a.plan(a.Admission.REPLACE, grid(), 3, 2, (0, 1), channel_draw=0.0, rank_draw=draw)


def test_corrupt_grid_binding_or_buffer_cannot_be_a_valid_rejection() -> None:
    slots = grid()
    with pytest.raises(ValueError, match='grid identity'):
        a.plan(a.Admission.REPLACE, (*slots[:3], replace(slots[3], actor=slots[2].actor), *slots[4:]), 3, 2, (0, 1))
    with pytest.raises(ValueError, match='x-major'):
        a.plan(a.Admission.NATIVE, tuple(reversed(slots)), 3, 2, (0, 1))
    with pytest.raises(ValueError, match='reciprocal'):
        a.plan(a.Admission.NATIVE, (replace(slots[0], actor=a.Actor(0, buffer(), a.Role.ACTIVE, 3)), *slots[1:]), 3, 2, (0, 1))
    with pytest.raises(ValueError, match='reserved terminator'):
        a.histogram(b'A' * MAXL0)
    with pytest.raises(ValueError, match='symbol'):
        a.histogram(buffer(b'@'))
    with pytest.raises(ValueError, match='overflow'):
        a.projected_pool((LIMIT,) * len(ALPHABET), (1,) * len(ALPHABET))
    with pytest.raises(ValueError, match='integer bounds'):
        a.projected_pool((-1,) * len(ALPHABET), (0,) * len(ALPHABET))


def test_hidden_only_occupant_is_not_vacant_or_eligible() -> None:
    slots = grid(victims=False)
    slots = (*slots[:2], replace(slots[2], actor=a.Actor(2, buffer(b'\0A'))), *slots[3:])
    occupied = a.plan(a.Admission.REPLACE, slots, 3, 2, (0, 1), channel_draw=0.0)
    assert occupied.disposition is a.Disposition.UNAVAILABLE
    native = a.plan(a.Admission.NATIVE, slots, 3, 2, (0, 1), rank_draw=0.0)
    assert native.target == (1, 1)


def test_replacement_paths_cannot_reconnect_after_vacancy_or_relocation() -> None:
    edges = (a.Transfer(0, 2, True, True), a.Transfer(2, 3, True, True),
             a.Transfer(0, 4, True, False), a.Transfer(4, 5, True, True),
             a.Transfer(0, 6, False, True), a.Transfer(6, 7, True, True),
             a.Transfer(None, 8, False, True), a.Transfer(8, 9, True, True))
    assert a.replacement_depths((0, 1), edges) == {0: 0, 1: 0, 2: 1, 3: 2, 4: None, 5: None, 6: None, 7: None, 8: None, 9: None}
    for edge in (a.Transfer(0, 0, True, True), a.Transfer(4, 2, True, True), a.Transfer(None, 2, True, True)):
        with pytest.raises(ValueError):
            a.replacement_depths((0, 1), (edge,))


GOOD = a.Continuity(100, 10, 50, 2, 5, 5)


def outcomes() -> tuple[a.Outcome, ...]:
    return tuple(a.Outcome(schedule, mode, seed, True, GOOD,
                           GOOD if mode is a.Admission.REPLACE else a.Continuity(),
                           0 if mode is a.Admission.NATIVE else 100,
                           100 if mode is a.Admission.REPLACE else 0)
                 for schedule, mode, seed in a.MATRIX)


def test_all_six_continuity_thresholds_remain_conjunctive() -> None:
    assert GOOD.passed and not a.Continuity().passed
    for field, threshold in zip(('transfers', 'renewing', 'serial', 'depth', 'late', 'retained_late'), GOOD.values, strict=True):
        assert not replace(GOOD, **{field: threshold - 1}).passed


def test_matrix_integrity_precedes_control_and_exposure() -> None:
    rows = outcomes()
    assert len(rows) == 120 and a.decide(rows) is a.Decision.BOTH
    assert a.decide(rows[:-1]) is a.Decision.INTEGRITY
    assert a.decide((*rows[:-1], rows[0])) is a.Decision.INTEGRITY
    assert a.decide((replace(rows[0], integrity=False), *rows[1:])) is a.Decision.INTEGRITY
    damaged = tuple(replace(row, partial_commits=99) if row.admission is a.Admission.REPLACE else row for row in rows)
    assert a.decide(damaged) is a.Decision.INTEGRITY  # missing commit is not inadequate exposure
    damaged = tuple(replace(row, replacement_edges=GOOD) if row.admission is a.Admission.REJECT else row for row in rows)
    assert a.decide(damaged) is a.Decision.INTEGRITY


@pytest.mark.parametrize('failing', [4, 5])
def test_native_control_quorum_boundary(failing: int) -> None:
    rows = tuple(replace(row, all_edges=a.Continuity()) if row.admission is a.Admission.NATIVE and row.seed in a.SEEDS[:failing] else row for row in outcomes())
    assert a.decide(rows) is (a.Decision.BOTH if failing == 4 else a.Decision.CONTROL)


@pytest.mark.parametrize('failing', [4, 5])
def test_exposure_quorum_boundary(failing: int) -> None:
    rows = tuple(replace(row, partial_opportunities=99, partial_commits=99, replacement_edges=a.Continuity())
                 if row.admission is a.Admission.REPLACE and row.seed in a.SEEDS[:failing] else row for row in outcomes())
    assert a.decide(rows) is (a.Decision.BOTH if failing == 4 else a.Decision.EXPOSURE)


@pytest.mark.parametrize('immediate,delayed,expected', [
    (16, 16, a.Decision.BOTH), (16, 15, a.Decision.IMMEDIATE),
    (15, 16, a.Decision.DELAYED), (15, 15, a.Decision.NEITHER), (0, 0, a.Decision.NEITHER)])
def test_response_categories_do_not_borrow_all_admission_renewal(immediate: int, delayed: int, expected: a.Decision) -> None:
    rows = tuple(replace(row, replacement_edges=a.Continuity()) if row.admission is a.Admission.REPLACE and
                 row.seed not in a.SEEDS[:immediate if row.schedule is a.Schedule.IMMEDIATE else delayed]
                 else row for row in outcomes())
    assert all(row.all_edges.passed for row in rows)
    assert a.decide(rows) is expected
