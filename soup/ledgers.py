"""Exact symbol-conservation ledger introduced at Stage 1."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from soup.substrate.base import BatchWriteResult, ByteTape, WriteOutcome


@dataclass(slots=True)
class SymbolPool:
    """Global counts of free bytes available for atomic tape replacement."""

    counts: NDArray[np.int64]
    conserved_totals: NDArray[np.int64]

    @classmethod
    def from_tapes(cls, tapes: NDArray[np.uint8], multiplier: float) -> SymbolPool:
        """Create a pool proportional to the initial soup's per-symbol histogram."""

        tape_counts = np.bincount(tapes.ravel(), minlength=256).astype(np.int64)
        pool_counts = np.rint(tape_counts.astype(np.float64) * multiplier).astype(np.int64)
        return cls(counts=pool_counts, conserved_totals=tape_counts + pool_counts)

    @property
    def total(self) -> int:
        return int(np.sum(self.counts))

    @property
    def entropy(self) -> float:
        total = self.total
        if total == 0:
            return 0.0
        probabilities = self.counts[self.counts > 0].astype(np.float64) / total
        return float(-np.sum(probabilities * np.log2(probabilities)))

    def withdraw_tape(self, tape: ByteTape) -> bool:
        """Atomically withdraw every symbol needed to place a complete tape."""

        requested = np.bincount(tape, minlength=256).astype(np.int64)
        if np.any(self.counts < requested):
            return False
        self.counts -= requested
        return True

    def release_tape(self, tape: ByteTape) -> None:
        """Return every symbol from a dissolved tape to the free pool."""

        self.counts += np.bincount(tape, minlength=256).astype(np.int64)

    def write(self, tape: ByteTape, index: int, new_value: int) -> WriteOutcome:
        """Exchange the destination byte atomically or reject an unavailable symbol."""

        value = new_value & 0xFF
        old_value = int(tape[index])
        if old_value == value:
            return WriteOutcome.SUCCESS_NOOP
        if self.counts[value] <= 0:
            return WriteOutcome.BLOCKED
        self.counts[value] -= 1
        self.counts[old_value] += 1
        tape[index] = value
        return WriteOutcome.SUCCESS

    def write_batch(
        self,
        tape: ByteTape,
        indices: NDArray[np.int64],
        new_values: NDArray[np.uint8],
    ) -> BatchWriteResult:
        """Atomically replace unique slots, allowing simultaneous returned symbols."""

        if indices.ndim != 1 or new_values.ndim != 1 or len(indices) != len(new_values):
            raise ValueError("indices and new_values must be equal-length vectors")
        if len(np.unique(indices)) != len(indices):
            raise ValueError("batch-write indices must be unique")
        if np.any(indices < 0) or np.any(indices >= len(tape)):
            raise IndexError("batch-write index is outside the tape")
        old_values = tape[indices]
        changed = old_values != new_values
        changed_slots = int(np.count_nonzero(changed))
        if changed_slots == 0:
            return BatchWriteResult(WriteOutcome.SUCCESS_NOOP, 0)
        old_counts = np.bincount(old_values[changed], minlength=256).astype(np.int64)
        new_counts = np.bincount(new_values[changed], minlength=256).astype(np.int64)
        resulting_pool = self.counts + old_counts - new_counts
        if np.any(resulting_pool < 0):
            return BatchWriteResult(WriteOutcome.BLOCKED, changed_slots)
        self.counts[:] = resulting_pool
        tape[indices] = new_values
        return BatchWriteResult(WriteOutcome.SUCCESS, changed_slots)
