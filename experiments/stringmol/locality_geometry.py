"""SM-XL001 independent radius-0/1 geometry, not admission replacement replay."""
from experiments.stringmol.analyze_lineage import require
from collections.abc import Callable
from typing import Any

Cell = tuple[int, int]
Grid = dict[int, Cell]
from experiments.stringmol.analyze_retirement import BoundaryReplay as NativeBoundary


def cells(center: Cell, radius: int, width: int = 40, height: int = 40) -> list[Cell]:
    require(radius in (0, 1), 'only qualified radii 0/1')
    if radius == 0:
        return [(x, y) for x in range(width) for y in range(height)]
    x, y = center
    return [((x+dx) % width, (y+dy) % height) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]


def candidates(now: list[int], pairs: dict[int, int], grid: Grid, seeker: int, radius: int, tick: int, eligible: Callable[[int], int]) -> list[int]:
    allowed = {i for i in now if i not in pairs and tick >= eligible(i)}
    if radius == 0:
        return [i for i in now if i in allowed]
    by_cell = {cell: i for i, cell in grid.items()}
    origin = grid[seeker]
    return [by_cell[c] for c in cells(origin, radius) if c != origin and by_cell.get(c) in allowed]


def population_candidates(now: list[int], pairs: dict[int, int], grid: Grid, seeker: int, radius: int, tick: int, eligible: Callable[[int], int]) -> list[int]:
    # Native AgentPlaceOnGrid initializes all cells G_NEXT. Run does not advance
    # grid readiness before tick0; TimestepGridIncrement does so after each tick.
    # At later ticks queue ownership encodes readiness, with pairs excluded.
    if radius == 1 and tick == 0:
        return []
    return candidates(now,pairs,grid,seeker,radius,tick,eligible)


def vacancies(grid: Grid, active: int, radius: int) -> list[Cell]:
    occupied = set(grid.values())
    return [c for c in cells(grid[active], radius) if c not in occupied]


class Boundary(NativeBoundary):
    """Retained lifecycle verifier with explicit local SEARCH-order qualification.

    The inherited verifier checks list ownership and all lifecycle/material links.
    Only candidate traversal differs. Temporary traversal order never changes the
    native surviving now queue, and candidate identity is checked before removal.
    """
    def __init__(self, initial: dict[str, Any], material: list[dict[str, str]], policy: str,
                 horizon: int = 5000, initial_order: list[int] | None = None,
                 disposition: str = 'RETAIN', *, grid: Grid, interaction: int) -> None:
        # Any is confined to the inherited material-initialization interface.
        super().__init__(initial, material, policy, horizon, initial_order, disposition)
        self.grid, self.interaction = grid, interaction

    def step(self, row: dict[str, str]) -> None:
        if row['event'] != 'SEARCH' or self.interaction == 0:
            return super().step(row)
        saved = self.now.copy()
        local = population_candidates(saved, self.pairs, self.grid, int(row['id']), 1, self.tick, self.eligible_tick)
        # Inherited SEARCH filters by pair/eligibility, so temporarily hide
        # nonlocal unbound agents; restore the unchanged queue after validation.
        self.now = local.copy()
        try:
            super().step(row)
        finally:
            selected = int(row['other'])
            self.now = [i for i in saved if i != selected]
