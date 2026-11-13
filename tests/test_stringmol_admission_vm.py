"""Head-state branch tests independent of native snapshots."""
from pathlib import Path

import pytest

from experiments.stringmol.admission_numeric import Alignment, Matrix, MT
from experiments.stringmol.admission_vm import VM
from experiments.stringmol.analyze_conservation import ALPHABET, MAXL0


@pytest.fixture
def matrix(tmp_path: Path) -> Matrix:
    rows = [' '.join(str(1 if i == j else -1) for j in range(33)) for i in range(34)]
    adjacency = [' '.join(str(int(i == j)) for j in range(33)) for i in range(33)]
    path = tmp_path / 'toy.mtx'
    path.write_text('\n'.join([ALPHABET, *rows, *adjacency])+'\n')
    return Matrix(path)


def buffers(active: bytes, passive: bytes) -> dict[int, bytes]:
    return {0: active.ljust(MAXL0, b'\0'), 1: passive.ljust(MAXL0, b'\0')}


def vm() -> VM:
    return VM(0, 1, Alignment(0, 0, 0, 0, 0, 0))


@pytest.mark.parametrize('outcome', ['ACCEPTED', 'BLOCKED', 'NOOP', 'READ_NULL', 'BOUNDARY'])
def test_zero_mutation_copy_heads_and_draws(matrix: Matrix, outcome: str) -> None:
    machine = vm(); machine.toggles['r'] = 0; machine.heads['w'][1] = 1
    before = buffers(b'=B' if outcome == 'NOOP' else b'=A', b'' if outcome == 'READ_NULL' else b'B')
    if outcome == 'BOUNDARY': machine.heads['w'][1] = MAXL0-1
    pool = [0] * 33
    pool[ALPHABET.index('B')] = int(outcome == 'ACCEPTED')
    rng = MT(2)
    result = machine.instruction(before, pool, rng, matrix)
    assert result.copy_outcome == outcome
    assert rng.draws == int(outcome in ('ACCEPTED', 'BLOCKED', 'NOOP'))
    assert result.unbind is (outcome == 'BOUNDARY')
    assert result.buffers[0][1] == (ord('B') if outcome in ('ACCEPTED', 'NOOP') else ord('A'))
    if outcome not in ('READ_NULL', 'BOUNDARY'):
        assert machine.address('r') == (1, 1) and machine.address('w') == (0, 2)
    if outcome != 'BOUNDARY': assert machine.address('i') == (0, 1)


@pytest.mark.parametrize('offset,proposal', [(0, True), (1, True), (4, False), (2000, False)])
def test_flow_is_derived_before_increment(matrix: Matrix, offset: int, proposal: bool) -> None:
    machine = vm(); machine.toggles['f'] = 0; machine.heads['f'][0] = offset
    result = machine.instruction(buffers(b'%', b'ABCD'), [0]*33, MT(2), matrix)
    assert result.flow == (1, offset) and result.proposal is proposal
    assert machine.address('i') == (0, 1)


def test_move_and_toggle_change_target_then_increment(matrix: Matrix) -> None:
    machine = vm(); machine.toggles['f'] = 0; machine.heads['f'][0] = 3
    machine.instruction(buffers(b'>A', b'ABC^A'), [0]*33, MT(2), matrix)
    assert machine.address('i') == (1, 4)
    machine.heads['i'][0] = 3
    machine.instruction(buffers(b'>A', b'ABC^A'), [0]*33, MT(2), matrix)
    assert machine.address('i') == (0, 1)


def test_conditional_read_near_reserved_terminator_is_padded(matrix: Matrix) -> None:
    machine = vm(); machine.toggles['r'] = 0; machine.heads['r'][0] = MAXL0-2
    other = bytearray(MAXL0); other[-2] = ord('N')
    rng = MT(2)
    machine.instruction({0: b'?AAAAA'.ljust(MAXL0, b'\0'), 1: bytes(other)}, [0]*33, rng, matrix)
    assert rng.draws == 1
    assert machine.address('i')[1] in (6, 7)


def test_empty_alignment_is_not_invented(matrix: Matrix) -> None:
    machine = vm(); machine.toggles['r'] = 0
    with pytest.raises(ValueError, match='empty/nonvisible'):
        machine.instruction(buffers(b'?ABC', b''), [0]*33, MT(2), matrix)
