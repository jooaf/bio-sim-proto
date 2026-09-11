"""Deterministic local signal fields and per-interaction access."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from soup.config import SignalsConfig
from soup.energy import LocalEnergyUptake
from soup.world import SpatialWorld


@dataclass(slots=True)
class SignalField:
    """Fixed-width byte tags aligned to spatial cells."""

    tags: NDArray[np.uint8]

    @classmethod
    def create(cls, world: SpatialWorld, config: SignalsConfig) -> SignalField:
        if config.signal_spec != "uniform":
            raise ValueError(f"unsupported signal field: {config.signal_spec}")
        tag = np.frombuffer(bytes.fromhex(config.initial_tag_hex), dtype=np.uint8)
        tags = np.tile(tag, (world.capacity, 1))
        return cls(tags=tags)

    def tag_at(self, index: int) -> bytes:
        return bytes(self.tags[index])


@dataclass(slots=True)
class LocalExecutionView:
    """Capabilities exposed to one active tape during one interaction."""

    energy: LocalEnergyUptake | None = None
    signals: SignalField | None = None
    active_index: int = 0

    def uptake_energy(self) -> float:
        return 0.0 if self.energy is None else self.energy.uptake_energy()

    def read_signal(self) -> bytes | None:
        return None if self.signals is None else self.signals.tag_at(self.active_index)
