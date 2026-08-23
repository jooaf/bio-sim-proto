"""Stage 2 structural dissolution and conserved-byte reclamation."""

from __future__ import annotations

from dataclasses import dataclass

from numpy.random import Generator

from soup.config import DissolutionConfig
from soup.ledgers import SymbolPool
from soup.substrate.base import ByteTape, Substrate
from soup.world import SpatialWorld


@dataclass(frozen=True, slots=True)
class DissolutionFact:
    tape_id: int
    born_tick: int
    died_tick: int
    cell: tuple[int, int]
    cause: str
    tape: ByteTape


def update_inert_timers(world: SpatialWorld, substrate: Substrate) -> None:
    """Advance consecutive structural-inertness counters after interactions."""

    for index_value in world.occupied_indices():
        index = int(index_value)
        if substrate.is_inert(world.tapes[index]):
            world.inert_ticks[index] += 1
        else:
            world.inert_ticks[index] = 0


def dissolve_candidates(
    *,
    world: SpatialWorld,
    substrate: Substrate,
    pool: SymbolPool,
    config: DissolutionConfig,
    rng: Generator,
    tick: int,
) -> list[DissolutionFact]:
    """Dissolve post-interaction candidates and return every byte to the pool.

    Starvation is intentionally absent: the energy ledger is disabled in Stage 2.
    """

    if not config.enabled:
        return []
    update_inert_timers(world, substrate)
    selected: list[tuple[int, str]] = []
    for index_value in world.occupied_indices():
        index = int(index_value)
        causes: list[str] = []
        if world.inert_ticks[index] >= config.inert_ticks:
            causes.append("inert")
        if config.max_age > 0 and world.ages[index] >= config.max_age:
            causes.append("max_age")
        if config.spontaneous_rate > 0.0 and float(rng.random()) < config.spontaneous_rate:
            causes.append("spontaneous")
        if causes:
            selected.append((index, "+".join(causes)))

    facts: list[DissolutionFact] = []
    for index, cause in selected:
        tape_id, tape, born_tick, cell = world.dissolve(index)
        pool.release_tape(tape)
        facts.append(
            DissolutionFact(
                tape_id=tape_id,
                born_tick=born_tick,
                died_tick=tick,
                cell=cell,
                cause=cause,
                tape=tape,
            )
        )
    return facts
