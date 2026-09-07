"""Explicit spatial energy flow and accounting for Stage 3."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from soup.config import EnergyConfig
from soup.substrate.base import ExecutionBudget
from soup.world import SpatialWorld


@dataclass(slots=True)
class EnergyLedger:
    """Track field energy, tape-held energy, external influx, and dissipation."""

    field: NDArray[np.float64]
    tapes: NDArray[np.float64]
    starved_ticks: NDArray[np.int64]
    tape_capacity: float
    initial_total: float = 0.0
    influx_cumulative: float = 0.0
    dissipated_cumulative: float = 0.0

    @classmethod
    def create(cls, world: SpatialWorld, config: EnergyConfig) -> EnergyLedger:
        """Create a zero-energy ledger aligned to the spatial lattice."""

        return cls(
            field=np.zeros(world.capacity, dtype=np.float64),
            tapes=np.zeros(world.capacity, dtype=np.float64),
            starved_ticks=np.zeros(world.capacity, dtype=np.int64),
            tape_capacity=config.tape_capacity,
        )

    @property
    def field_total(self) -> float:
        return float(self.field.sum())

    @property
    def tape_total(self) -> float:
        return float(self.tapes.sum())

    @property
    def accounted_total(self) -> float:
        return self.field_total + self.tape_total + self.dissipated_cumulative

    @property
    def expected_total(self) -> float:
        return self.initial_total + self.influx_cumulative

    def advance_field(
        self, world: SpatialWorld, config: EnergyConfig
    ) -> None:
        """Apply uniform influx, conservative diffusion, decay, and absorption."""

        if config.influx_rate:
            per_cell = config.influx_rate / world.capacity
            self.field += per_cell
            self.influx_cumulative += config.influx_rate

        if config.diffusion:
            grid = self.field.reshape(world.height, world.width)
            diffusion = config.diffusion
            self.field = (
                (1.0 - 4.0 * diffusion) * grid
                + diffusion * np.roll(grid, 1, axis=0)
                + diffusion * np.roll(grid, -1, axis=0)
                + diffusion * np.roll(grid, 1, axis=1)
                + diffusion * np.roll(grid, -1, axis=1)
            ).reshape(world.capacity)

        if config.decay:
            dissipated = float(self.field.sum()) * config.decay
            self.field *= 1.0 - config.decay
            self.dissipated_cumulative += dissipated

        occupied = world.occupied_indices()
        if len(occupied) and config.absorption_rate:
            room = np.maximum(0.0, self.tape_capacity - self.tapes[occupied])
            transfer = np.minimum(
                np.minimum(self.field[occupied], config.absorption_rate), room
            )
            self.field[occupied] -= transfer
            self.tapes[occupied] += transfer

    def execution_budget(
        self, index: int, config: EnergyConfig, max_steps: int
    ) -> ExecutionBudget:
        """Return a substrate budget funded by one active tape."""

        return ExecutionBudget(
            max_steps=max_steps,
            energy_available=float(self.tapes[index]),
            energy_per_instruction=config.per_instruction,
            energy_per_write=config.per_write,
        )

    def spend_execution(self, index: int, amount: float) -> None:
        """Deduct and dissipate a substrate-reported execution cost."""

        if amount < 0.0 or amount > self.tapes[index] + 1e-12:
            raise ValueError("execution energy exceeds active tape balance")
        charged = min(amount, float(self.tapes[index]))
        self.tapes[index] -= charged
        self.dissipated_cumulative += charged

    def update_starvation(self, world: SpatialWorld, tolerance: float = 1e-12) -> None:
        """Advance consecutive zero-energy counters for occupied tapes."""

        empty = ~world.occupied
        self.starved_ticks[empty] = 0
        occupied = world.occupied_indices()
        starving = self.tapes[occupied] <= tolerance
        self.starved_ticks[occupied[starving]] += 1
        self.starved_ticks[occupied[~starving]] = 0

    def can_fund_birth(
        self, parent_index: int, birth_cost: float, offspring_energy: float
    ) -> bool:
        """Return whether a parent can pay dissipative and transferred birth energy."""

        return bool(self.tapes[parent_index] + 1e-12 >= birth_cost + offspring_energy)

    def fund_birth(
        self,
        parent_index: int,
        child_index: int,
        birth_cost: float,
        offspring_energy: float,
    ) -> None:
        """Atomically charge a parent and initialize one child's energy."""

        if self.tapes[child_index] != 0.0:
            raise ValueError("offspring target already holds tape energy")
        if not self.can_fund_birth(parent_index, birth_cost, offspring_energy):
            raise ValueError("parent cannot fund offspring energy")
        self.tapes[parent_index] -= birth_cost + offspring_energy
        self.tapes[child_index] = offspring_energy
        self.dissipated_cumulative += birth_cost
        self.starved_ticks[child_index] = 0

    def dissolve(self, index: int) -> float:
        """Dissipate held energy and clear tape-local state at death."""

        amount = float(self.tapes[index])
        self.tapes[index] = 0.0
        self.starved_ticks[index] = 0
        self.dissipated_cumulative += amount
        return amount
