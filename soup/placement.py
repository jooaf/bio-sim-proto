"""Stage 2 exogenous random placement into empty lattice cells."""

from __future__ import annotations

from dataclasses import dataclass

from numpy.random import Generator

from soup.ledgers import SymbolPool
from soup.substrate.base import ByteTape, Substrate
from soup.world import SpatialWorld


@dataclass(frozen=True, slots=True)
class PlacementFact:
    tape_id: int
    born_tick: int
    cell: tuple[int, int]
    tape: ByteTape


@dataclass(frozen=True, slots=True)
class PlacementResult:
    attempted: int
    blocked: int
    placements: tuple[PlacementFact, ...]


def place_random_tapes(
    *,
    world: SpatialWorld,
    substrate: Substrate,
    pool: SymbolPool,
    rng: Generator,
    tick: int,
    reseed_rate: float,
) -> PlacementResult:
    """Attempt atomic pool-funded random placement in each current vacancy."""

    if reseed_rate <= 0.0 or world.free_cells == 0:
        return PlacementResult(0, 0, ())
    attempted = 0
    blocked = 0
    facts: list[PlacementFact] = []
    free_indices = [index for index in range(world.capacity) if not world.occupied[index]]
    for index in free_indices:
        if float(rng.random()) >= reseed_rate:
            continue
        attempted += 1
        candidate = substrate.random_tape(rng)
        if not pool.withdraw_tape(candidate):
            blocked += 1
            continue
        tape_id = world.place(index, candidate, tick)
        facts.append(
            PlacementFact(
                tape_id=tape_id,
                born_tick=tick,
                cell=world.cell(index),
                tape=candidate.copy(),
            )
        )
    return PlacementResult(attempted, blocked, tuple(facts))
