from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from soup.substrate.base import ExecutionBudget, HaltReason
from soup.substrate.bff import BFFSubstrate, OP_ENERGY_UPTAKE, OP_SIGNAL_WRITE


def execute(values: list[int], *, steps: int = 32, head_wrap: bool = True, pc_wrap: bool = False) -> tuple[NDArray[np.uint8], object]:
    if len(values) != 8:
        raise ValueError("test joint must contain eight bytes")
    tape = np.asarray(values, dtype=np.uint8)
    substrate = BFFSubstrate(tape_length=4, head_wrap=head_wrap, pc_wrap=pc_wrap)
    result = substrate.execute(tape, None, ExecutionBudget(max_steps=steps), None)
    return tape, result


class FixedExecutionView:
    def __init__(self, tag: bytes) -> None:
        self.tag = tag
        self.reads = 0
        self.written: list[bytes] = []

    def uptake_energy(self) -> float:
        return 1.0

    def read_signal(self) -> bytes:
        self.reads += 1
        return self.tag

    def write_signal(self, tag: bytes) -> bool:
        self.written.append(tag)
        return True


def test_signal_write_uses_following_active_tape_payload() -> None:
    active = [0xAA, 0xBB, 0xCC, 0xDD, OP_SIGNAL_WRITE, 0x11, 0x22, 0x33, 0x44] + [0] * 7
    joint = np.asarray(active + [0] * 16, dtype=np.uint8)
    view = FixedExecutionView(bytes.fromhex("aabbccdd"))
    substrate = BFFSubstrate(
        tape_length=16,
        signal_dispatch_enabled=True,
        signal_tag_length=4,
        signal_tag_stride=16,
        signal_writes_enabled=True,
    )
    result = substrate.execute(joint, None, ExecutionBudget(max_steps=1), view)
    assert result.signal_dispatches == 1
    assert result.signal_writes == 1
    assert view.written == [bytes.fromhex("11223344")]


def test_exact_signal_tag_dispatches_to_handler() -> None:
    joint = np.asarray([0xAA, 0xBB, 0xCC, 0xDD, OP_ENERGY_UPTAKE, 0, 0, 0] + [0] * 8, dtype=np.uint8)
    substrate = BFFSubstrate(
        tape_length=8,
        active_uptake_enabled=True,
        signal_dispatch_enabled=True,
        signal_tag_length=4,
        signal_tag_stride=8,
    )
    matched = FixedExecutionView(bytes.fromhex("aabbccdd"))
    result = substrate.execute(joint.copy(), None, ExecutionBudget(max_steps=1), matched)
    assert result.signal_reads == 1
    assert result.signal_dispatches == 1
    assert result.energy_uptake_executions == 1

    mismatched = FixedExecutionView(bytes.fromhex("11223344"))
    result = substrate.execute(joint.copy(), None, ExecutionBudget(max_steps=1), mismatched)
    assert result.signal_reads == 1
    assert result.signal_dispatches == 0
    assert result.energy_uptake_executions == 0


def test_disabled_signal_dispatch_preserves_pc_zero() -> None:
    joint = np.asarray([0xAA, 0xBB, 0xCC, 0xDD, OP_ENERGY_UPTAKE, 0, 0, 0] + [0] * 8, dtype=np.uint8)
    view = FixedExecutionView(bytes.fromhex("aabbccdd"))
    result = BFFSubstrate(tape_length=8, active_uptake_enabled=True).execute(
        joint, None, ExecutionBudget(max_steps=1), view
    )
    assert view.reads == 0
    assert result.signal_reads == 0
    assert result.signal_dispatches == 0
    assert result.energy_uptake_executions == 0


def test_uptake_opcode_counts_as_activity_only_when_enabled() -> None:
    tape = np.asarray([OP_ENERGY_UPTAKE, 0, 0, 0], dtype=np.uint8)
    assert BFFSubstrate(tape_length=4).is_inert(tape)
    assert not BFFSubstrate(tape_length=4, active_uptake_enabled=True).is_inert(tape)


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
