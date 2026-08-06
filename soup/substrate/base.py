"""Substrate interface shared by simulator cores.

Stage 0 passes ``pool=None`` because matter conservation is intentionally disabled.
The mediator protocol is present so Stage 1 can add conservation without coupling the
scheduler to a concrete substrate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import numpy as np
from numpy.random import Generator
from numpy.typing import NDArray


ByteTape = NDArray[np.uint8]


class HaltReason(str, Enum):
    BUDGET_EXHAUSTED = "budget_exhausted"
    PC_OVERRUN = "pc_overrun"
    ENERGY_EXHAUSTED = "energy_exhausted"


class WriteOutcome(str, Enum):
    SUCCESS = "success"
    SUCCESS_NOOP = "success_noop"
    BLOCKED = "blocked"


class WriteMediator(Protocol):
    """Minimal interface through which a substrate requests a tape write."""

    def write(self, tape: ByteTape, index: int, new_value: int) -> WriteOutcome: ...


class SignalView(Protocol):
    """Opaque local signal interface reserved for Stage 4."""


@dataclass(frozen=True, slots=True)
class ExecutionBudget:
    max_steps: int
    energy_available: float = float("inf")
    energy_per_instruction: float = 0.0
    energy_per_write: float = 0.0


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    steps_executed: int
    energy_consumed: float
    writes_success: int
    writes_blocked: int
    halt_reason: HaltReason
    signal_reads: int = 0
    signal_writes: int = 0


class Substrate(Protocol):
    name: str
    tape_length: int
    alphabet_size: int

    def random_tape(self, rng: Generator) -> ByteTape: ...

    def execute(
        self,
        joint: ByteTape,
        pool: WriteMediator | None,
        budget: ExecutionBudget,
        signals: SignalView | None,
    ) -> ExecutionResult: ...

    def is_inert(self, tape: ByteTape) -> bool: ...

    def describe(self, tape: ByteTape) -> dict[str, object]: ...
