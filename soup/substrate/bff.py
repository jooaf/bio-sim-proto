"""Plain-Python BFF byte-tape substrate.

Semantics were checked against arXiv:2406.19108v2 and the corresponding
``paradigms-of-intelligence/cubff`` ``bff_noheads`` implementation. That code
wraps data heads over the 2L-byte joint tape, bounds the PC, wraps uint8
arithmetic, starts both heads and the PC at zero, scans brackets dynamically,
and permits 8,192 character reads. The build prompt described clamped heads as
the default; ``head_wrap=True`` intentionally follows the cited implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.random import Generator

from soup.substrate.base import (
    ByteTape,
    ExecutionBudget,
    ExecutionResult,
    HaltReason,
    SignalView,
    WriteMediator,
    WriteOutcome,
)


OP_DEC_H0 = 0x3C
OP_INC_H0 = 0x3E
OP_DEC_H1 = 0x7B
OP_INC_H1 = 0x7D
OP_DEC = 0x2D
OP_INC = 0x2B
OP_COPY_01 = 0x2E
OP_COPY_10 = 0x2C
OP_LOOP_START = 0x5B
OP_LOOP_END = 0x5D
OP_ENERGY_UPTAKE = 0x3A
INSTRUCTIONS: tuple[int, ...] = (
    OP_DEC_H0,
    OP_INC_H0,
    OP_DEC_H1,
    OP_INC_H1,
    OP_DEC,
    OP_INC,
    OP_COPY_01,
    OP_COPY_10,
    OP_LOOP_START,
    OP_LOOP_END,
)
INSTRUCTION_SET = frozenset(INSTRUCTIONS)
WRITE_OPS = frozenset((OP_DEC, OP_INC, OP_COPY_01, OP_COPY_10))


@dataclass(slots=True)
class BFFSubstrate:
    tape_length: int = 64
    head_wrap: bool = True
    pc_wrap: bool = False
    noop_density: float = 246.0 / 256.0
    name: str = "bff"
    alphabet_size: int = 256

    def random_tape(self, rng: Generator) -> ByteTape:
        """Draw an initial tape without using global random state.

        The paper-compatible density is exactly the result of a uniform draw over
        all bytes. Other densities first choose instruction versus data and then
        choose uniformly inside that category.
        """

        paper_density = 246.0 / 256.0
        if self.noop_density == paper_density:
            return rng.integers(0, self.alphabet_size, size=self.tape_length, dtype=np.uint8)
        instruction_mask = rng.random(self.tape_length) >= self.noop_density
        result = np.empty(self.tape_length, dtype=np.uint8)
        instruction_values = np.asarray(INSTRUCTIONS, dtype=np.uint8)
        noop_values = np.asarray([value for value in range(256) if value not in INSTRUCTION_SET], dtype=np.uint8)
        n_instruction = int(np.count_nonzero(instruction_mask))
        n_noop = self.tape_length - n_instruction
        if n_instruction:
            result[instruction_mask] = rng.choice(instruction_values, size=n_instruction)
        if n_noop:
            result[~instruction_mask] = rng.choice(noop_values, size=n_noop)
        return result

    @staticmethod
    def _matching_forward(joint: ByteTape, pc: int) -> int | None:
        depth = 1
        for candidate in range(pc + 1, len(joint)):
            value = int(joint[candidate])
            if value == OP_LOOP_START:
                depth += 1
            elif value == OP_LOOP_END:
                depth -= 1
                if depth == 0:
                    return candidate
        return None

    @staticmethod
    def _matching_backward(joint: ByteTape, pc: int) -> int | None:
        depth = 1
        for candidate in range(pc - 1, -1, -1):
            value = int(joint[candidate])
            if value == OP_LOOP_END:
                depth += 1
            elif value == OP_LOOP_START:
                depth -= 1
                if depth == 0:
                    return candidate
        return None

    @staticmethod
    def _write(joint: ByteTape, index: int, value: int, pool: WriteMediator | None) -> WriteOutcome:
        value &= 0xFF
        if pool is not None:
            return pool.write(joint, index, value)
        old = int(joint[index])
        if old == value:
            return WriteOutcome.SUCCESS_NOOP
        joint[index] = value
        return WriteOutcome.SUCCESS

    def execute(
        self,
        joint: ByteTape,
        pool: WriteMediator | None,
        budget: ExecutionBudget,
        signals: SignalView | None,
    ) -> ExecutionResult:
        """Execute a joint tape in place, reading one character per step."""
        expected_length = 2 * self.tape_length
        if joint.dtype != np.uint8 or joint.ndim != 1 or len(joint) != expected_length:
            raise ValueError(f"joint tape must be a uint8 vector of length {expected_length}")

        pc = 0
        h0 = 0
        h1 = 0
        steps = 0
        energy = 0.0
        writes_success = 0
        writes_blocked = 0
        uptake_executions = 0
        energy_absorbed = 0.0
        halt_reason = HaltReason.BUDGET_EXHAUSTED

        while steps < budget.max_steps:
            op = int(joint[pc])
            if op == OP_ENERGY_UPTAKE and signals is not None:
                energy_absorbed += signals.uptake_energy()
                uptake_executions += 1
            instruction_cost = budget.energy_per_instruction
            if energy + instruction_cost > budget.energy_available + energy_absorbed:
                halt_reason = HaltReason.ENERGY_EXHAUSTED
                break
            energy += instruction_cost
            steps += 1
            next_pc = pc + 1

            if op in (OP_DEC_H0, OP_INC_H0, OP_DEC_H1, OP_INC_H1):
                delta = -1 if op in (OP_DEC_H0, OP_DEC_H1) else 1
                if op in (OP_DEC_H0, OP_INC_H0):
                    candidate = h0 + delta
                    if self.head_wrap:
                        h0 = candidate % expected_length
                    elif not 0 <= candidate < expected_length:
                        halt_reason = HaltReason.PC_OVERRUN
                        break
                    else:
                        h0 = candidate
                else:
                    candidate = h1 + delta
                    if self.head_wrap:
                        h1 = candidate % expected_length
                    elif not 0 <= candidate < expected_length:
                        halt_reason = HaltReason.PC_OVERRUN
                        break
                    else:
                        h1 = candidate
            elif op in WRITE_OPS:
                if op == OP_DEC:
                    new_value = (int(joint[h0]) - 1) & 0xFF
                    destination = h0
                elif op == OP_INC:
                    new_value = (int(joint[h0]) + 1) & 0xFF
                    destination = h0
                elif op == OP_COPY_01:
                    new_value = int(joint[h0])
                    destination = h1
                else:
                    new_value = int(joint[h1])
                    destination = h0
                write_cost = budget.energy_per_write
                if energy + write_cost > budget.energy_available + energy_absorbed:
                    halt_reason = HaltReason.ENERGY_EXHAUSTED
                    break
                outcome = self._write(joint, destination, new_value, pool)
                if outcome is WriteOutcome.BLOCKED:
                    writes_blocked += 1
                else:
                    writes_success += 1
                    energy += write_cost
            elif op == OP_LOOP_START and int(joint[h0]) == 0:
                match = self._matching_forward(joint, pc)
                if match is None:
                    halt_reason = HaltReason.PC_OVERRUN
                    break
                next_pc = match + 1
            elif op == OP_LOOP_END and int(joint[h0]) != 0:
                match = self._matching_backward(joint, pc)
                if match is None:
                    halt_reason = HaltReason.PC_OVERRUN
                    break
                next_pc = match + 1

            if self.pc_wrap:
                pc = next_pc % expected_length
            elif not 0 <= next_pc < expected_length:
                halt_reason = HaltReason.PC_OVERRUN
                break
            else:
                pc = next_pc

        return ExecutionResult(
            steps_executed=steps,
            energy_consumed=energy,
            writes_success=writes_success,
            writes_blocked=writes_blocked,
            halt_reason=halt_reason,
            energy_uptake_executions=uptake_executions,
            energy_absorbed=energy_absorbed,
        )

    def is_inert(self, tape: ByteTape) -> bool:
        """Conservatively call a tape inert when it contains no write opcode."""

        return not bool(np.isin(tape, np.asarray(tuple(WRITE_OPS), dtype=np.uint8)).any())

    def describe(self, tape: ByteTape) -> dict[str, object]:
        """Return raw inspector facts, not evolutionary conclusions."""

        histogram = np.bincount(tape, minlength=256)
        return {
            "length": int(len(tape)),
            "instruction_count": int(np.isin(tape, np.asarray(INSTRUCTIONS, dtype=np.uint8)).sum()),
            "nonzero_count": int(np.count_nonzero(tape)),
            "byte_histogram": histogram.tolist(),
            "hex": tape.tobytes().hex(),
        }
