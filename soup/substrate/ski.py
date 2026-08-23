"""Fixed-tape SKI combinator chemistry for the Stage 1 portability check.

Each tape stores one prefix expression followed by zero padding. An ordered
interaction replaces tape A with a bounded reduction of application ``A B``;
tape B is unchanged. The whole serialized replacement is one atomic conserved
batch, so a blocked reaction cannot leave a malformed partial expression.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

import numpy as np
from numpy.random import Generator

from soup.substrate.base import (
    BatchWriteResult,
    ByteTape,
    ExecutionBudget,
    ExecutionResult,
    HaltReason,
    SignalView,
    WriteMediator,
    WriteOutcome,
)

EMPTY = 0
APPLY = ord("@")
S = ord("S")
K = ord("K")
I = ord("I")
ATOMS = np.asarray([S, K, I], dtype=np.uint8)


@dataclass(frozen=True, slots=True)
class Application:
    function: Expression
    argument: Expression


Expression: TypeAlias = int | Application


def parse_expression(tape: ByteTape) -> Expression | None:
    """Parse one complete padded prefix expression, returning None if malformed."""

    zero_positions = np.flatnonzero(tape == EMPTY)
    end = int(zero_positions[0]) if len(zero_positions) else len(tape)
    if bool(np.any(tape[end:] != EMPTY)):
        return None
    tokens = tape[:end]
    if len(tokens) == 0:
        return None

    def parse_at(index: int) -> tuple[Expression, int] | None:
        if index >= len(tokens):
            return None
        token = int(tokens[index])
        if token in (S, K, I):
            return token, index + 1
        if token != APPLY:
            return None
        left = parse_at(index + 1)
        if left is None:
            return None
        right = parse_at(left[1])
        if right is None:
            return None
        return Application(left[0], right[0]), right[1]

    parsed = parse_at(0)
    if parsed is None or parsed[1] != len(tokens):
        return None
    return parsed[0]


def serialize_expression(expression: Expression) -> list[int]:
    """Serialize an expression to canonical prefix form."""

    if isinstance(expression, int):
        return [expression]
    return [APPLY, *serialize_expression(expression.function), *serialize_expression(expression.argument)]


def reduce_once(expression: Expression) -> tuple[Expression, bool]:
    """Perform one leftmost-outermost SKI reduction."""

    if isinstance(expression, int):
        return expression, False
    function = expression.function
    argument = expression.argument
    if function == I:
        return argument, True
    if isinstance(function, Application) and function.function == K:
        return function.argument, True
    if (
        isinstance(function, Application)
        and isinstance(function.function, Application)
        and function.function.function == S
    ):
        x = function.function.argument
        y = function.argument
        z = argument
        return Application(Application(x, z), Application(y, z)), True
    reduced_function, changed = reduce_once(function)
    if changed:
        return Application(reduced_function, argument), True
    reduced_argument, changed = reduce_once(argument)
    if changed:
        return Application(function, reduced_argument), True
    return expression, False


def expression_depth(expression: Expression) -> int:
    if isinstance(expression, int):
        return 1
    return 1 + max(expression_depth(expression.function), expression_depth(expression.argument))


@dataclass(slots=True)
class SKISubstrate:
    """Conservation-aware SKI application/reduction substrate."""

    tape_length: int = 64
    application_probability: float = 0.35
    name: str = "ski"
    alphabet_size: int = 256

    def random_tape(self, rng: Generator) -> ByteTape:
        """Generate one valid random prefix expression and zero-pad it."""

        tokens: list[int] = []
        pending = 1
        while pending > 0:
            remaining = self.tape_length - len(tokens)
            can_apply = remaining >= pending + 2
            if can_apply and float(rng.random()) < self.application_probability:
                tokens.append(APPLY)
                pending += 1
            else:
                tokens.append(int(rng.choice(ATOMS)))
                pending -= 1
        tape = np.zeros(self.tape_length, dtype=np.uint8)
        tape[: len(tokens)] = np.asarray(tokens, dtype=np.uint8)
        return tape

    def execute(
        self,
        joint: ByteTape,
        pool: WriteMediator | None,
        budget: ExecutionBudget,
        signals: SignalView | None,
    ) -> ExecutionResult:
        """Apply B to A, reduce, and atomically replace A when feasible."""

        del signals
        expected_length = 2 * self.tape_length
        if joint.dtype != np.uint8 or joint.ndim != 1 or len(joint) != expected_length:
            raise ValueError(f"joint tape must be a uint8 vector of length {expected_length}")
        first = parse_expression(joint[: self.tape_length])
        second = parse_expression(joint[self.tape_length :])
        if first is None or second is None:
            return ExecutionResult(0, 0.0, 0, 0, HaltReason.INVALID_PROGRAM)

        expression: Expression = Application(first, second)
        steps = 0
        normal_form = False
        while steps < budget.max_steps:
            reduced, changed = reduce_once(expression)
            steps += 1
            if not changed:
                normal_form = True
                break
            expression = reduced

        serialized = serialize_expression(expression)
        if len(serialized) > self.tape_length:
            return ExecutionResult(steps, 0.0, 0, 0, HaltReason.CAPACITY_EXHAUSTED)
        replacement = np.zeros(self.tape_length, dtype=np.uint8)
        replacement[: len(serialized)] = np.asarray(serialized, dtype=np.uint8)
        indices = np.arange(self.tape_length, dtype=np.int64)
        if pool is None:
            changed_slots = int(np.count_nonzero(joint[: self.tape_length] != replacement))
            joint[: self.tape_length] = replacement
            batch = BatchWriteResult(
                WriteOutcome.SUCCESS_NOOP if changed_slots == 0 else WriteOutcome.SUCCESS,
                changed_slots,
            )
        else:
            batch = pool.write_batch(joint, indices, replacement)
        if batch.outcome is WriteOutcome.BLOCKED:
            return ExecutionResult(steps, 0.0, 0, batch.changed_slots, HaltReason.POOL_BLOCKED)
        halt_reason = HaltReason.NORMAL_FORM if normal_form else HaltReason.BUDGET_EXHAUSTED
        return ExecutionResult(steps, 0.0, batch.changed_slots, 0, halt_reason)

    def is_inert(self, tape: ByteTape) -> bool:
        expression = parse_expression(tape)
        if expression is None or isinstance(expression, int):
            return True
        _, changed = reduce_once(expression)
        return not changed

    def describe(self, tape: ByteTape) -> dict[str, object]:
        expression = parse_expression(tape)
        if expression is None:
            return {"valid": False, "tokens": int(np.count_nonzero(tape))}
        serialized = serialize_expression(expression)
        return {
            "valid": True,
            "tokens": len(serialized),
            "depth": expression_depth(expression),
            "applications": serialized.count(APPLY),
            "S": serialized.count(S),
            "K": serialized.count(K),
            "I": serialized.count(I),
            "prefix": bytes(serialized).decode("ascii"),
        }
