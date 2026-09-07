"""Pool-funded copy birth for experimental Stage 3 reproduction modes."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.random import Generator

from soup.config import OffspringPlacement
from soup.energy import EnergyLedger
from soup.interactions import ExactCopyTriggerFact
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
    trigger: str = "scheduled"
    trigger_target_id: int | None = None
    trigger_round_index: int | None = None


@dataclass(frozen=True, slots=True)
class ReproductionResult:
    attempted: int
    blocked_no_space: int
    blocked_pool: int
    births: tuple[ReproductionFact, ...]
    blocked_no_parent: int = 0
    invalidated_triggers: int = 0
    blocked_energy: int = 0


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


def _place_parent_copy(
    *,
    world: SpatialWorld,
    pool: SymbolPool,
    parent_index: int,
    child_index: int,
    tick: int,
    trigger: str,
    trigger_target_id: int | None = None,
    trigger_round_index: int | None = None,
    energy: EnergyLedger | None = None,
    birth_energy_cost: float = 0.0,
    offspring_energy: float = 0.0,
) -> tuple[ReproductionFact | None, str | None]:
    """Atomically fund and place one exact parent copy."""

    if energy is not None and not energy.can_fund_birth(
        parent_index, birth_energy_cost, offspring_energy
    ):
        return None, "energy"
    child_tape = world.tapes[parent_index].copy()
    if not pool.withdraw_tape(child_tape):
        return None, "pool"
    parent_id = int(world.tape_ids[parent_index])
    parent_cell = world.cell(parent_index)
    child_id = world.place(child_index, child_tape, tick)
    if energy is not None:
        energy.fund_birth(
            parent_index,
            child_index,
            birth_energy_cost,
            offspring_energy,
        )
    return (
        ReproductionFact(
            parent_id=parent_id,
            parent_cell=parent_cell,
            child_id=child_id,
            child_cell=world.cell(child_index),
            born_tick=tick,
            tape=child_tape.copy(),
            trigger=trigger,
            trigger_target_id=trigger_target_id,
            trigger_round_index=trigger_round_index,
        ),
        None,
    )


def _record_birth_outcome(
    birth: ReproductionFact | None,
    blocked: str | None,
    births: list[ReproductionFact],
) -> tuple[int, int]:
    """Append a birth and return pool/energy block increments."""

    if blocked == "pool":
        return 1, 0
    if blocked == "energy":
        return 0, 1
    if birth is None:
        raise ValueError("birth transaction returned no outcome")
    births.append(birth)
    return 0, 0


def _scheduled_parent_first(
    *,
    world: SpatialWorld,
    pool: SymbolPool,
    rng: Generator,
    tick: int,
    attempted_parents: np.ndarray[tuple[int, ...], np.dtype[np.int64]],
    placement_radius: int,
    max_births_per_tick: int,
    energy: EnergyLedger | None,
    birth_energy_cost: float,
    offspring_energy: float,
) -> ReproductionResult:
    attempted = 0
    blocked_no_space = 0
    blocked_pool = 0
    blocked_energy = 0
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
        child_index = free_cells[int(rng.integers(len(free_cells)))]
        birth, blocked = _place_parent_copy(
            world=world,
            pool=pool,
            parent_index=parent_index,
            child_index=child_index,
            tick=tick,
            trigger="scheduled",
            energy=energy,
            birth_energy_cost=birth_energy_cost,
            offspring_energy=offspring_energy,
        )
        pool_increment, energy_increment = _record_birth_outcome(
            birth, blocked, births
        )
        blocked_pool += pool_increment
        blocked_energy += energy_increment
    return ReproductionResult(
        attempted=attempted,
        blocked_no_space=blocked_no_space,
        blocked_pool=blocked_pool,
        births=tuple(births),
        blocked_energy=blocked_energy,
    )


def _scheduled_vacancy_first(
    *,
    world: SpatialWorld,
    pool: SymbolPool,
    rng: Generator,
    tick: int,
    n_attempts: int,
    placement_radius: int,
    max_births_per_tick: int,
    energy: EnergyLedger | None,
    birth_energy_cost: float,
    offspring_energy: float,
) -> ReproductionResult:
    attempted = 0
    blocked_no_parent = 0
    blocked_pool = 0
    blocked_energy = 0
    births: list[ReproductionFact] = []
    for _ in range(n_attempts):
        if len(births) >= max_births_per_tick or world.free_cells == 0:
            break
        attempted += 1
        free_cells = np.flatnonzero(~world.occupied)
        child_index = int(free_cells[int(rng.integers(len(free_cells)))])
        parents = world.neighbor_indices(child_index, placement_radius)
        if len(parents) == 0:
            blocked_no_parent += 1
            continue
        parent_index = int(parents[int(rng.integers(len(parents)))])
        birth, blocked = _place_parent_copy(
            world=world,
            pool=pool,
            parent_index=parent_index,
            child_index=child_index,
            tick=tick,
            trigger="scheduled",
            energy=energy,
            birth_energy_cost=birth_energy_cost,
            offspring_energy=offspring_energy,
        )
        pool_increment, energy_increment = _record_birth_outcome(
            birth, blocked, births
        )
        blocked_pool += pool_increment
        blocked_energy += energy_increment
    return ReproductionResult(
        attempted=attempted,
        blocked_no_space=0,
        blocked_pool=blocked_pool,
        births=tuple(births),
        blocked_no_parent=blocked_no_parent,
        blocked_energy=blocked_energy,
    )


def reproduce_tapes(
    *,
    world: SpatialWorld,
    pool: SymbolPool,
    rng: Generator,
    tick: int,
    rate: float,
    placement_radius: int,
    max_births_per_tick: int,
    placement_protocol: str = OffspringPlacement.PARENT_FIRST.value,
    energy: EnergyLedger | None = None,
    birth_energy_cost: float = 0.0,
    offspring_energy: float = 0.0,
) -> ReproductionResult:
    """Attempt scheduled exact-copy births from the current live population."""

    if not 0.0 <= rate <= 1.0:
        raise ValueError("reproduction rate must be in [0, 1]")
    if placement_radius <= 0:
        raise ValueError("placement radius must be positive")
    if max_births_per_tick <= 0:
        raise ValueError("max births per tick must be positive")
    if birth_energy_cost < 0.0 or offspring_energy < 0.0:
        raise ValueError("reproduction energy values must be nonnegative")
    if energy is None and (birth_energy_cost > 0.0 or offspring_energy > 0.0):
        raise ValueError("reproduction energy values require an energy ledger")
    protocol = OffspringPlacement(placement_protocol)
    if rate == 0.0 or world.free_cells == 0:
        return ReproductionResult(0, 0, 0, ())

    parents = world.occupied_indices()
    attempted_parents = parents[rng.random(len(parents)) < rate]
    if protocol is OffspringPlacement.VACANCY_FIRST:
        return _scheduled_vacancy_first(
            world=world,
            pool=pool,
            rng=rng,
            tick=tick,
            n_attempts=len(attempted_parents),
            placement_radius=placement_radius,
            max_births_per_tick=max_births_per_tick,
            energy=energy,
            birth_energy_cost=birth_energy_cost,
            offspring_energy=offspring_energy,
        )
    if len(attempted_parents):
        attempted_parents = rng.permutation(attempted_parents)
    return _scheduled_parent_first(
        world=world,
        pool=pool,
        rng=rng,
        tick=tick,
        attempted_parents=attempted_parents,
        placement_radius=placement_radius,
        max_births_per_tick=max_births_per_tick,
        energy=energy,
        birth_energy_cost=birth_energy_cost,
        offspring_energy=offspring_energy,
    )


def reproduce_from_copy_triggers(
    *,
    world: SpatialWorld,
    pool: SymbolPool,
    rng: Generator,
    tick: int,
    triggers: list[ExactCopyTriggerFact],
    placement_radius: int,
    max_births_per_tick: int,
    energy: EnergyLedger | None = None,
    birth_energy_cost: float = 0.0,
    offspring_energy: float = 0.0,
) -> ReproductionResult:
    """Attempt births from still-valid execution-mediated exact-copy triggers."""

    attempted = 0
    blocked_no_space = 0
    blocked_pool = 0
    blocked_energy = 0
    invalidated = 0
    births: list[ReproductionFact] = []
    for trigger in triggers:
        if len(births) >= max_births_per_tick:
            break
        attempted += 1
        matching = np.flatnonzero(
            world.occupied & (world.tape_ids == trigger.source_id)
        )
        if len(matching) != 1:
            invalidated += 1
            continue
        parent_index = int(matching[0])
        if not np.array_equal(world.tapes[parent_index], trigger.tape):
            invalidated += 1
            continue
        free_cells = _free_neighbor_cells(world, parent_index, placement_radius)
        if not free_cells:
            blocked_no_space += 1
            continue
        child_index = free_cells[int(rng.integers(len(free_cells)))]
        birth, blocked = _place_parent_copy(
            world=world,
            pool=pool,
            parent_index=parent_index,
            child_index=child_index,
            tick=tick,
            trigger="exact_copy",
            trigger_target_id=trigger.target_id,
            trigger_round_index=trigger.round_index,
            energy=energy,
            birth_energy_cost=birth_energy_cost,
            offspring_energy=offspring_energy,
        )
        pool_increment, energy_increment = _record_birth_outcome(
            birth, blocked, births
        )
        blocked_pool += pool_increment
        blocked_energy += energy_increment
    return ReproductionResult(
        attempted=attempted,
        blocked_no_space=blocked_no_space,
        blocked_pool=blocked_pool,
        births=tuple(births),
        invalidated_triggers=invalidated,
        blocked_energy=blocked_energy,
    )
