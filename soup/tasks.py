"""Task-response state used to modulate future interaction opportunity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from soup.config import SignalsConfig, TaskConfig
from soup.world import SpatialWorld

if TYPE_CHECKING:
    from soup.interactions import InteractionFact


@dataclass(slots=True)
class TaskLedger:
    """Per-cell task score, updated after a complete interaction tick."""

    scores: NDArray[np.float64]

    @classmethod
    def create(cls, world: SpatialWorld) -> TaskLedger:
        return cls(scores=np.zeros(world.capacity, dtype=np.float64))

    def active_probabilities(
        self, active: NDArray[np.int64], bonus: float
    ) -> NDArray[np.float64]:
        weights = 1.0 + bonus * self.scores[active]
        return weights / float(weights.sum())

    def update_signal_uptake(
        self,
        facts: list[InteractionFact],
        world: SpatialWorld,
        signal_config: SignalsConfig,
        task_config: TaskConfig,
    ) -> None:
        if task_config.task_spec != "signal_uptake":
            raise ValueError(f"unsupported task specification: {task_config.task_spec}")
        primary = bytes.fromhex(signal_config.initial_tag_hex)
        secondary = bytes.fromhex(signal_config.secondary_tag_hex)
        for fact in facts:
            tag = None if fact.signal_tag_hex is None else bytes.fromhex(fact.signal_tag_hex)
            responded = fact.energy_uptake_executions > 0
            correct = bool(
                fact.signal_dispatches == 1
                and ((tag == primary and responded) or (tag == secondary and not responded))
            )
            self.scores[fact.a_index] = float(correct)
        self.scores[~world.occupied] = 0.0
