"""Stage 0 flat soup state.

The lattice and occupancy ledger intentionally begin at Stage 2. Keeping this state
in flat NumPy arrays makes both the later spatial transition and a compiled-language
port straightforward.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from soup.substrate.base import Substrate
from numpy.random import Generator


@dataclass(slots=True)
class FlatWorld:
    tapes: NDArray[np.uint8]
    tape_ids: NDArray[np.int64]
    ages: NDArray[np.int64]

    @classmethod
    def create(cls, population_size: int, substrate: Substrate, rng: Generator) -> FlatWorld:
        """Create initial state by advancing the simulation's sole generator."""

        tapes = np.stack([substrate.random_tape(rng) for _ in range(population_size)])
        return cls(
            tapes=tapes,
            tape_ids=np.arange(population_size, dtype=np.int64),
            ages=np.zeros(population_size, dtype=np.int64),
        )

    @property
    def population_size(self) -> int:
        return int(self.tapes.shape[0])
