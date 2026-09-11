"""Explicit spatial energy flow and accounting for Stage 3."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from soup.config import EnergyConfig, EnvironmentConfig
from soup.substrate.base import ExecutionBudget, SignalView
from soup.world import SpatialWorld


ENVIRONMENT_SEED_XOR = 0x534634


def influx_profile(
    world: SpatialWorld, config: EnvironmentConfig, seed: int
) -> NDArray[np.float64] | None:
    """Return a deterministic normalized static profile, or None for uniform."""

    if config.influx_spec == "uniform":
        return None
    if config.influx_spec != "patches":
        raise ValueError(f"unsupported influx field: {config.influx_spec}")
    rng = np.random.default_rng(seed ^ ENVIRONMENT_SEED_XOR)
    noise = rng.standard_normal((world.height, world.width))
    ky = np.fft.fftfreq(world.height)[:, None]
    kx = np.fft.rfftfreq(world.width)[None, :]
    scale = 2.0 * np.pi * config.correlation_length
    spectral_filter = np.exp(-0.5 * scale * scale * (kx * kx + ky * ky))
    smooth = np.fft.irfft2(np.fft.rfft2(noise) * spectral_filter, s=noise.shape)
    deviation = float(smooth.std())
    if deviation <= np.finfo(np.float64).eps:
        raise ValueError("patch field has no representable spatial variation")
    standardized = (smooth - float(smooth.mean())) / deviation
    weights = np.exp(config.influx_contrast * standardized).reshape(world.capacity)
    weights *= world.capacity / float(weights.sum())
    weights[0] += world.capacity - float(weights.sum())
    if not np.isfinite(weights).all() or bool(np.any(weights <= 0.0)):
        raise ValueError("patch field weights must be finite and positive")
    return weights


@dataclass(slots=True)
class EnergyLedger:
    """Track field energy, tape-held energy, external influx, and dissipation."""

    field: NDArray[np.float64]
    tapes: NDArray[np.float64]
    starved_ticks: NDArray[np.int64]
    tape_capacity: float
    influx_weights: NDArray[np.float64] | None = None
    initial_total: float = 0.0
    influx_cumulative: float = 0.0
    dissipated_cumulative: float = 0.0

    @classmethod
    def create(
        cls,
        world: SpatialWorld,
        config: EnergyConfig,
        environment: EnvironmentConfig | None = None,
        seed: int = 0,
    ) -> EnergyLedger:
        """Create a zero-energy ledger aligned to the spatial lattice."""

        return cls(
            field=np.zeros(world.capacity, dtype=np.float64),
            tapes=np.zeros(world.capacity, dtype=np.float64),
            starved_ticks=np.zeros(world.capacity, dtype=np.int64),
            tape_capacity=config.tape_capacity,
            influx_weights=(
                None if environment is None else influx_profile(world, environment, seed)
            ),
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
            if self.influx_weights is None:
                self.field += config.influx_rate / world.capacity
            else:
                self.field += config.influx_rate * self.influx_weights / world.capacity
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

    def uptake_access(self, index: int, amount: float) -> SignalView:
        """Return execution-scoped access to one tape's local field cell."""

        return LocalEnergyUptake(self, index, amount)

    def uptake(self, index: int, maximum: float) -> float:
        """Transfer bounded local field energy into one occupied tape."""

        if maximum < 0.0:
            raise ValueError("uptake maximum must be nonnegative")
        room = max(0.0, self.tape_capacity - float(self.tapes[index]))
        transfer = min(float(self.field[index]), maximum, room)
        self.field[index] -= transfer
        self.tapes[index] += transfer
        return transfer

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


@dataclass(slots=True)
class LocalEnergyUptake:
    """Execution-scoped adapter for one active tape and field cell."""

    ledger: EnergyLedger
    index: int
    amount: float

    def uptake_energy(self) -> float:
        return self.ledger.uptake(self.index, self.amount)
