"""Stage 0 random ordered tape interactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from numpy.random import Generator

from soup.substrate.base import ExecutionBudget, Substrate
from soup.world import FlatWorld


@dataclass(frozen=True, slots=True)
class InteractionFact:
    tick: int
    round_index: int
    a_index: int
    b_index: int
    a_id: int
    b_id: int
    steps: int
    energy_spent: float
    writes_success: int
    writes_blocked: int
    halt_reason: str
    a_bytes_changed: int
    b_bytes_changed: int
    a_hash_before: str
    a_hash_after: str
    b_hash_before: str
    b_hash_after: str


HashTape = Callable[[np.ndarray[tuple[int], np.dtype[np.uint8]]], str]


def run_random_round(
    *,
    world: FlatWorld,
    substrate: Substrate,
    rng: Generator,
    budget: ExecutionBudget,
    tick: int,
    interactions_per_tick: int,
    hash_tape: HashTape,
) -> list[InteractionFact]:
    """Sample and execute ordered pairs, allowing tapes to interact repeatedly."""

    facts: list[InteractionFact] = []
    population_size = world.population_size
    for round_index in range(interactions_per_tick):
        a_index = int(rng.integers(population_size))
        b_draw = int(rng.integers(population_size - 1))
        b_index = b_draw + int(b_draw >= a_index)

        a_before = world.tapes[a_index].copy()
        b_before = world.tapes[b_index].copy()
        a_hash_before = hash_tape(a_before)
        b_hash_before = hash_tape(b_before)
        joint = np.concatenate((a_before, b_before))
        result = substrate.execute(joint, None, budget, None)
        length = substrate.tape_length
        a_after = joint[:length]
        b_after = joint[length:]
        world.tapes[a_index] = a_after
        world.tapes[b_index] = b_after
        facts.append(
            InteractionFact(
                tick=tick,
                round_index=round_index,
                a_index=a_index,
                b_index=b_index,
                a_id=int(world.tape_ids[a_index]),
                b_id=int(world.tape_ids[b_index]),
                steps=result.steps_executed,
                energy_spent=result.energy_consumed,
                writes_success=result.writes_success,
                writes_blocked=result.writes_blocked,
                halt_reason=result.halt_reason.value,
                a_bytes_changed=int(np.count_nonzero(a_before != a_after)),
                b_bytes_changed=int(np.count_nonzero(b_before != b_after)),
                a_hash_before=a_hash_before,
                a_hash_after=hash_tape(a_after),
                b_hash_before=b_hash_before,
                b_hash_after=hash_tape(b_after),
            )
        )
    return facts
