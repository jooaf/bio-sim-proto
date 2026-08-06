from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from soup.substrate.base import ExecutionBudget, HaltReason
from soup.substrate.bff import BFFSubstrate


def execute(values: list[int], *, steps: int = 32, head_wrap: bool = True, pc_wrap: bool = False) -> tuple[NDArray[np.uint8], object]:
    if len(values) != 8:
        raise ValueError("test joint must contain eight bytes")
    tape = np.asarray(values, dtype=np.uint8)
    substrate = BFFSubstrate(tape_length=4, head_wrap=head_wrap, pc_wrap=pc_wrap)
    result = substrate.execute(tape, None, ExecutionBudget(max_steps=steps), None)
    return tape, result


def test_increment_head0_then_increment_value() -> None:
    tape, result = execute([ord(">"), ord("+"), 0, 0, 0, 0, 0, 0])
    assert tape[1] == ord(",")
    assert result.writes_success == 1


def test_decrement_head0_wraps_to_joint_end() -> None:
    tape, _ = execute([ord("<"), ord("+"), 0, 0, 0, 0, 0, 9])
    assert tape[7] == 10


def test_decrement_head0_clamp_variant_halts() -> None:
    tape, result = execute([ord("<"), ord("+"), 0, 0, 0, 0, 0, 9], head_wrap=False)
    assert tape[7] == 9
    assert result.halt_reason is HaltReason.PC_OVERRUN
    assert result.steps_executed == 1


def test_increment_head1_then_copy_0_to_1() -> None:
    tape, _ = execute([ord("}"), ord("."), 0, 0, 0, 0, 0, 0])
    assert tape[:2].tolist() == [ord("}"), ord("}")]


def test_decrement_head1_wraps_then_copy_0_to_1() -> None:
    tape, _ = execute([ord("{"), ord("."), 0, 0, 0, 0, 0, 9])
    assert tape[7] == ord("{")


def test_increment_byte_wraps_uint8() -> None:
    tape, _ = execute([ord(">"), 255, ord("+"), 0, 0, 0, 0, 0])
    assert tape[1] == 0


def test_decrement_byte_wraps_uint8() -> None:
    tape, _ = execute([ord(">"), 0, ord("-"), 0, 0, 0, 0, 0])
    assert tape[1] == 255


def test_copy_head0_into_head1() -> None:
    tape, _ = execute([ord("}"), ord("."), 0, 0, 0, 0, 0, 0])
    assert tape[1] == ord("}")


def test_copy_head1_into_head0() -> None:
    tape, _ = execute([ord("}"), ord(","), 0, 0, 0, 0, 0, 0])
    assert tape[0] == ord(",")


def test_loop_start_skips_nested_body_when_head_value_is_zero() -> None:
    values = [ord(">"), 0, ord("["), ord("["), ord("+"), ord("]"), ord("]"), 0]
    tape, result = execute(values)
    assert tape[1] == 0
    assert result.steps_executed == 4
    assert result.halt_reason is HaltReason.PC_OVERRUN


def test_loop_end_jumps_back_while_head_value_is_nonzero() -> None:
    values = [ord(">"), 1, ord("["), 2, ord("]"), 0, 0, 0]
    _, result = execute(values, steps=10)
    assert result.steps_executed == 10
    assert result.halt_reason is HaltReason.BUDGET_EXHAUSTED


def test_bracket_matching_uses_current_modified_tape() -> None:
    values = [ord(">"), 0, ord("{"), ord("."), ord("["), 2, 3, ord("]")]
    tape, result = execute(values)
    assert tape[7] == 0
    assert result.halt_reason is HaltReason.PC_OVERRUN
    assert result.steps_executed == 5


def test_other_bytes_are_noops_and_pc_wrap_is_configurable() -> None:
    tape, result = execute([1, 2, 3, 4, 5, 6, 7, 8], steps=10, pc_wrap=True)
    assert tape.tolist() == [1, 2, 3, 4, 5, 6, 7, 8]
    assert result.steps_executed == 10
    assert result.halt_reason is HaltReason.BUDGET_EXHAUSTED


def test_random_tape_is_seed_deterministic() -> None:
    first_rng = np.random.Generator(np.random.PCG64(42))
    second_rng = np.random.Generator(np.random.PCG64(42))
    substrate = BFFSubstrate()
    assert np.array_equal(substrate.random_tape(first_rng), substrate.random_tape(second_rng))


@pytest.mark.parametrize("invalid", [np.zeros(7, dtype=np.uint8), np.zeros(8, dtype=np.int64)])
def test_rejects_invalid_joint(invalid: NDArray[np.generic]) -> None:
    substrate = BFFSubstrate(tape_length=4)
    with pytest.raises(ValueError):
        substrate.execute(invalid, None, ExecutionBudget(max_steps=1), None)  # type: ignore[arg-type]
