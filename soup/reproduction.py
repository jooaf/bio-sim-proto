"""Pool-funded neutral copy birth for the experimental Stage 3R extension."""

from __future__ import annotations

from dataclasses import dataclass

from numpy.random import Generator

from soup.ledgers import SymbolPool
from soup.substrate.base import ByteTape
from soup.world import SpatialWorld


@dataclass(frozen=True, slots=True)
class ReproductionFact:
    parent_id: int
    parent_cell: tuple[int, int]
    child_id: int
    child_cell: tuple[int, int]
    born_tick: int
    tape: ByteTape


@dataclass(frozen=True, slots=True)
class ReproductionResult:
    attempted: int
    blocked_no_space: int
    blocked_pool: int
    births: tuple[ReproductionFact, ...]


def _free_neighbor_cells(
    world: SpatialWorld, parent_index: int, radius: int
) -> list[int]:
    if radius <= 0:
        raise ValueError("placement radius must be positive")
    x, y = world.cell(parent_index)
    candidates = {
        world.index(x + dx, y + dy)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if dx != 0 or dy != 0
    }
    candidates.discard(parent_index)
    return sorted(index for index in candidates if not world.occupied[index])


def reproduce_tapes(
    *,
    world: SpatialWorld,
    pool: SymbolPool,
    rng: Generator,
    tick: int,
    rate: float,
    placement_radius: int,
    max_births_per_tick: int,
) -> ReproductionResult:
    """Attempt neutral exact-copy births from the tick-start live parents."""

    if not 0.0 <= rate <= 1.0:
        raise ValueError("reproduction rate must be in [0, 1]")
    if placement_radius <= 0:
        raise ValueError("placement radius must be positive")
    if max_births_per_tick <= 0:
        raise ValueError("max births per tick must be positive")
    if rate == 0.0 or world.free_cells == 0:
        return ReproductionResult(0, 0, 0, ())

    parents = world.occupied_indices()
    attempted_parents = parents[rng.random(len(parents)) < rate]
    if len(attempted_parents):
        attempted_parents = rng.permutation(attempted_parents)
    attempted = 0
    blocked_no_space = 0
    blocked_pool = 0
    births: list[ReproductionFact] = []
    for parent_value in attempted_parents:
        if len(births) >= max_births_per_tick:
            break
        parent_index = int(parent_value)
        attempted += 1
        free_cells = _free_neighbor_cells(world, parent_index, placement_radius)
        if not free_cells:
            blocked_no_space += 1
            continue
        child_tape = world.tapes[parent_index].copy()
        if not pool.withdraw_tape(child_tape):
            blocked_pool += 1
            continue
        child_index = free_cells[int(rng.integers(len(free_cells)))]
        child_id = world.place(child_index, child_tape, tick)
        births.append(
            ReproductionFact(
                parent_id=int(world.tape_ids[parent_index]),
                parent_cell=world.cell(parent_index),
                child_id=child_id,
                child_cell=world.cell(child_index),
                born_tick=tick,
                tape=child_tape.copy(),
            )
        )
    return ReproductionResult(
        attempted=attempted,
        blocked_no_space=blocked_no_space,
        blocked_pool=blocked_pool,
        births=tuple(births),
    )
