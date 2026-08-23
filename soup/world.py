"""Flat and spatial program-soup state containers.

Stages 0/1 use a dense flat population. Stage 2 uses a fixed-capacity toroidal
lattice with explicit occupancy; empty cells contain no conserved bytes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.random import Generator
from numpy.typing import NDArray

from soup.substrate.base import ByteTape, Substrate


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

    @property
    def capacity(self) -> int:
        return self.population_size

    @property
    def free_cells(self) -> int:
        return 0

    def occupied_indices(self) -> NDArray[np.int64]:
        return np.arange(self.population_size, dtype=np.int64)

    def cell(self, index: int) -> tuple[int, int] | None:
        del index
        return None


@dataclass(slots=True)
class SpatialWorld:
    """Fixed-capacity toroidal lattice with sparse occupancy in flat arrays."""

    width: int
    height: int
    tapes: NDArray[np.uint8]
    occupied: NDArray[np.bool_]
    tape_ids: NDArray[np.int64]
    ages: NDArray[np.int64]
    inert_ticks: NDArray[np.int64]
    born_ticks: NDArray[np.int64]
    next_tape_id: int
    _neighbor_cache: dict[int, tuple[NDArray[np.int64], ...]] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        width: int,
        height: int,
        initial_tape_fill: float,
        substrate: Substrate,
        rng: Generator,
    ) -> SpatialWorld:
        """Create deterministic occupancy and random tapes from the sole RNG."""

        capacity = width * height
        population = min(capacity, max(2, int(round(capacity * initial_tape_fill))))
        chosen = rng.permutation(capacity)[:population].astype(np.int64)
        tapes = np.zeros((capacity, substrate.tape_length), dtype=np.uint8)
        occupied = np.zeros(capacity, dtype=np.bool_)
        tape_ids = np.full(capacity, -1, dtype=np.int64)
        ages = np.zeros(capacity, dtype=np.int64)
        inert_ticks = np.zeros(capacity, dtype=np.int64)
        born_ticks = np.full(capacity, -1, dtype=np.int64)
        for tape_id, cell_index in enumerate(chosen):
            index = int(cell_index)
            occupied[index] = True
            tapes[index] = substrate.random_tape(rng)
            tape_ids[index] = tape_id
            born_ticks[index] = 0
        return cls(
            width=width,
            height=height,
            tapes=tapes,
            occupied=occupied,
            tape_ids=tape_ids,
            ages=ages,
            inert_ticks=inert_ticks,
            born_ticks=born_ticks,
            next_tape_id=population,
        )

    @property
    def capacity(self) -> int:
        return self.width * self.height

    @property
    def population_size(self) -> int:
        return int(np.count_nonzero(self.occupied))

    @property
    def free_cells(self) -> int:
        return self.capacity - self.population_size

    def occupied_indices(self) -> NDArray[np.int64]:
        return np.flatnonzero(self.occupied).astype(np.int64)

    def occupied_tapes(self) -> NDArray[np.uint8]:
        return self.tapes[self.occupied]

    def cell(self, index: int) -> tuple[int, int]:
        return index % self.width, index // self.width

    def index(self, x: int, y: int) -> int:
        return (y % self.height) * self.width + (x % self.width)

    def neighbor_indices(self, index: int, radius: int) -> NDArray[np.int64]:
        """Return occupied Moore neighbors using cached toroidal geometry."""

        cached = self._neighbor_cache.get(radius)
        if cached is None:
            rows: list[NDArray[np.int64]] = []
            for center in range(self.capacity):
                x, y = self.cell(center)
                cell_candidates = {
                    self.index(x + dx, y + dy)
                    for dy in range(-radius, radius + 1)
                    for dx in range(-radius, radius + 1)
                    if dx != 0 or dy != 0
                }
                cell_candidates.discard(center)
                rows.append(np.asarray(sorted(cell_candidates), dtype=np.int64))
            cached = tuple(rows)
            self._neighbor_cache[radius] = cached
        neighbor_cells = cached[index]
        return neighbor_cells[self.occupied[neighbor_cells]]

    def dissolve(self, index: int) -> tuple[int, ByteTape, int, tuple[int, int]]:
        """Clear one occupied cell and return facts needed by ledgers/logging."""

        if not self.occupied[index]:
            raise ValueError("cannot dissolve an empty cell")
        tape_id = int(self.tape_ids[index])
        tape = self.tapes[index].copy()
        born_tick = int(self.born_ticks[index])
        cell = self.cell(index)
        self.tapes[index].fill(0)
        self.occupied[index] = False
        self.tape_ids[index] = -1
        self.ages[index] = 0
        self.inert_ticks[index] = 0
        self.born_ticks[index] = -1
        return tape_id, tape, born_tick, cell

    def place(self, index: int, tape: ByteTape, tick: int) -> int:
        """Occupy one empty cell with a newly allocated tape ID."""

        if self.occupied[index]:
            raise ValueError("cannot place into an occupied cell")
        if tape.shape != self.tapes[index].shape:
            raise ValueError("placed tape has the wrong shape")
        tape_id = self.next_tape_id
        self.next_tape_id += 1
        self.tapes[index] = tape
        self.occupied[index] = True
        self.tape_ids[index] = tape_id
        self.ages[index] = 0
        self.inert_ticks[index] = 0
        self.born_ticks[index] = tick
        return tape_id


World = FlatWorld | SpatialWorld
