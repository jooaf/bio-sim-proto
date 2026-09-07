"""Stage-aware ordered tape interactions and background mutation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator

import numpy as np
from numpy.random import Generator

from soup.config import PairingMode
from soup.substrate.base import ByteTape, ExecutionBudget, Substrate, WriteMediator, WriteOutcome
from soup.world import FlatWorld, SpatialWorld, World


@dataclass(frozen=True, slots=True)
class ExactCopyTriggerFact:
    """Byte-exact execution-mediated copy observed during one interaction."""

    tick: int
    round_index: int
    direction: str
    source_id: int
    target_id: int
    source_cell: tuple[int, int] | None
    target_cell: tuple[int, int] | None
    tape: ByteTape


@dataclass(frozen=True, slots=True)
class InteractionFact:
    tick: int
    round_index: int
    a_index: int
    b_index: int
    a_id: int
    b_id: int
    a_cell: tuple[int, int] | None
    b_cell: tuple[int, int] | None
    a_mutations: int
    b_mutations: int
    mutation_writes_success: int
    mutation_writes_blocked: int
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


def draw_ordered_pairs(
    *,
    rng: Generator,
    population_size: int,
    n_pairs: int,
    pairing_mode: PairingMode,
) -> Iterator[tuple[int, int]]:
    """Yield ordered index pairs according to the configured protocol."""

    if pairing_mode is PairingMode.SHUFFLED_DISJOINT:
        order = rng.permutation(population_size)
        for pair_index in range(n_pairs):
            yield int(order[2 * pair_index]), int(order[2 * pair_index + 1])
        return
    if pairing_mode is PairingMode.LOCAL_NEIGHBORHOOD:
        raise ValueError("local_neighborhood pairs require a SpatialWorld")

    for _ in range(n_pairs):
        a_index = int(rng.integers(population_size))
        b_draw = int(rng.integers(population_size - 1))
        yield a_index, b_draw + int(b_draw >= a_index)


def mutate_joint(
    joint: np.ndarray[tuple[int], np.dtype[np.uint8]],
    *,
    rng: Generator,
    mutation_rate: float,
    tape_length: int,
    pool: WriteMediator | None = None,
) -> tuple[int, int, int, int]:
    """Apply uniform replacements and return per-tape events plus write outcomes."""

    if mutation_rate <= 0.0:
        return 0, 0, 0, 0
    mask = rng.random(len(joint)) < mutation_rate
    mutation_indices = np.flatnonzero(mask)
    replacements = rng.integers(0, 256, size=len(mutation_indices), dtype=np.uint8)
    successful = 0
    blocked = 0
    if pool is None:
        joint[mutation_indices] = replacements
        successful = len(mutation_indices)
    else:
        for index, replacement in zip(mutation_indices, replacements, strict=True):
            outcome = pool.write(joint, int(index), int(replacement))
            if outcome is WriteOutcome.BLOCKED:
                blocked += 1
            else:
                successful += 1
    return (
        int(np.count_nonzero(mask[:tape_length])),
        int(np.count_nonzero(mask[tape_length:])),
        successful,
        blocked,
    )


def _execute_pair(
    *,
    world: World,
    substrate: Substrate,
    rng: Generator,
    budget: ExecutionBudget,
    tick: int,
    round_index: int,
    a_index: int,
    b_index: int,
    mutation_rate: float,
    pool: WriteMediator | None,
    hash_tape: HashTape,
    detect_exact_copy: bool,
) -> tuple[InteractionFact, tuple[ExactCopyTriggerFact, ...]]:
    """Execute one ordered pair and return factual exact-copy triggers."""

    a_before = world.tapes[a_index].copy()
    b_before = world.tapes[b_index].copy()
    a_hash_before = hash_tape(a_before)
    b_hash_before = hash_tape(b_before)
    joint = np.concatenate((a_before, b_before))
    a_mutations, b_mutations, mutation_success, mutation_blocked = mutate_joint(
        joint,
        rng=rng,
        mutation_rate=mutation_rate,
        tape_length=substrate.tape_length,
        pool=pool,
    )
    execution_before = joint.copy() if detect_exact_copy else None
    result = substrate.execute(joint, pool, budget, None)
    length = substrate.tape_length
    a_after = joint[:length]
    b_after = joint[length:]
    world.tapes[a_index] = a_after
    world.tapes[b_index] = b_after
    triggers: list[ExactCopyTriggerFact] = []
    if execution_before is not None:
        a_execution_before = execution_before[:length]
        b_execution_before = execution_before[length:]
    else:
        a_execution_before = a_after
        b_execution_before = b_after
    if detect_exact_copy and (
        np.array_equal(a_execution_before, a_after)
        and not np.array_equal(b_execution_before, b_after)
        and np.array_equal(b_after, a_after)
    ):
        triggers.append(
            ExactCopyTriggerFact(
                tick=tick,
                round_index=round_index,
                direction="a_into_b",
                source_id=int(world.tape_ids[a_index]),
                target_id=int(world.tape_ids[b_index]),
                source_cell=world.cell(a_index),
                target_cell=world.cell(b_index),
                tape=a_after.copy(),
            )
        )
    if detect_exact_copy and (
        np.array_equal(b_execution_before, b_after)
        and not np.array_equal(a_execution_before, a_after)
        and np.array_equal(a_after, b_after)
    ):
        triggers.append(
            ExactCopyTriggerFact(
                tick=tick,
                round_index=round_index,
                direction="b_into_a",
                source_id=int(world.tape_ids[b_index]),
                target_id=int(world.tape_ids[a_index]),
                source_cell=world.cell(b_index),
                target_cell=world.cell(a_index),
                tape=b_after.copy(),
            )
        )
    fact = InteractionFact(
        tick=tick,
        round_index=round_index,
        a_index=a_index,
        b_index=b_index,
        a_id=int(world.tape_ids[a_index]),
        b_id=int(world.tape_ids[b_index]),
        a_cell=world.cell(a_index),
        b_cell=world.cell(b_index),
        a_mutations=a_mutations,
        b_mutations=b_mutations,
        mutation_writes_success=mutation_success,
        mutation_writes_blocked=mutation_blocked,
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
    return fact, tuple(triggers)


def run_interaction_round(
    *,
    world: FlatWorld,
    substrate: Substrate,
    rng: Generator,
    budget: ExecutionBudget,
    tick: int,
    interactions_per_tick: int,
    pairing_mode: PairingMode,
    mutation_rate: float,
    pool: WriteMediator | None,
    hash_tape: HashTape,
    copy_triggers: list[ExactCopyTriggerFact] | None = None,
) -> list[InteractionFact]:
    """Sample and execute one configured flat-world interaction round."""

    facts: list[InteractionFact] = []
    pairs = draw_ordered_pairs(
        rng=rng,
        population_size=world.population_size,
        n_pairs=interactions_per_tick,
        pairing_mode=pairing_mode,
    )
    for round_index, (a_index, b_index) in enumerate(pairs):
        fact, triggers = _execute_pair(
            world=world,
            substrate=substrate,
            rng=rng,
            budget=budget,
            tick=tick,
            round_index=round_index,
            a_index=a_index,
            b_index=b_index,
            mutation_rate=mutation_rate,
            pool=pool,
            hash_tape=hash_tape,
            detect_exact_copy=copy_triggers is not None,
        )
        facts.append(fact)
        if copy_triggers is not None:
            copy_triggers.extend(triggers)
    return facts


def run_local_interaction_round(
    *,
    world: SpatialWorld,
    substrate: Substrate,
    rng: Generator,
    budget: ExecutionBudget,
    tick: int,
    interactions_per_tick: int,
    interaction_radius: int,
    mutation_rate: float,
    pool: WriteMediator,
    hash_tape: HashTape,
    copy_triggers: list[ExactCopyTriggerFact] | None = None,
) -> list[InteractionFact]:
    """Execute with-replacement interactions between occupied local neighbors."""

    occupied = world.occupied_indices()
    if len(occupied) < 2:
        return []
    facts: list[InteractionFact] = []
    for round_index in range(interactions_per_tick):
        a_index = int(occupied[int(rng.integers(len(occupied)))])
        neighbors = world.neighbor_indices(a_index, interaction_radius)
        if len(neighbors) == 0:
            continue
        b_index = int(neighbors[int(rng.integers(len(neighbors)))])
        fact, triggers = _execute_pair(
            world=world,
            substrate=substrate,
            rng=rng,
            budget=budget,
            tick=tick,
            round_index=round_index,
            a_index=a_index,
            b_index=b_index,
            mutation_rate=mutation_rate,
            pool=pool,
            hash_tape=hash_tape,
            detect_exact_copy=copy_triggers is not None,
        )
        facts.append(fact)
        if copy_triggers is not None:
            copy_triggers.extend(triggers)
    return facts
