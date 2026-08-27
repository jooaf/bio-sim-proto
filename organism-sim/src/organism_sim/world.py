from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from random import Random

import numpy as np

from .chemistry import ChemistryCatalog, Inventory, MoleculeBatch, add_batch
from .config import SimulationConfig
from .entities import Organism, Position

_MASK64 = (1 << 64) - 1


def _mix64(value: int) -> int:
    """splitmix64 finalizer: stable 64-bit scrambling for chunk seeds."""

    value = (value + 0x9E3779B97F4A7C15) & _MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK64
    return value ^ (value >> 31)


@dataclass(slots=True)
class Chunk:
    """One square region of the infinite world, generated on first touch."""

    cx: int
    cy: int
    heat: np.ndarray
    deposit_positions: set[Position] = field(default_factory=set)
    has_heat: bool = False


@dataclass(slots=True)
class World:
    """Infinite procedural world.

    The world has no edges and no wrapping. Terrain (deposits and thermal
    springs) is generated deterministically per chunk the first time the chunk
    is touched, so the world extends without bound as organisms explore it.
    Newly generated geological matter and energy are accumulated in
    ``generated_elements`` / ``generated_energy`` so conservation audits can
    separate dynamics from world generation.
    """

    config: SimulationConfig
    catalog: ChemistryCatalog
    chunk_size: int
    terrain_seed: int
    chunks: dict[tuple[int, int], Chunk] = field(default_factory=dict)
    deposits: dict[Position, Inventory] = field(default_factory=dict)
    occupancy: dict[Position, set[int]] = field(default_factory=dict)
    # Optional demand histogram over molecule IDs. When set, newly generated
    # chunks draw deposit molecules in proportion to these weights instead of
    # uniformly, mirroring the phase-1 matched-pool economy finding.
    molecule_weights: tuple[float, ...] | None = None
    generated_elements: tuple[int, ...] = ()
    generated_energy: float = 0.0

    @classmethod
    def generate(cls, config: SimulationConfig, catalog: ChemistryCatalog, rng: Random) -> World:
        world = cls(
            config=config,
            catalog=catalog,
            chunk_size=config.chunk_size,
            terrain_seed=rng.getrandbits(64),
            generated_elements=(0,) * len(catalog.elements),
        )
        # Materialize the founder region up front so the spawn area starts with
        # the configured resource density; everything else appears on demand.
        for cx in range(-(-config.width // config.chunk_size)):
            for cy in range(-(-config.height // config.chunk_size)):
                world.ensure_chunk(cx, cy)
        return world

    # ----------------------------------------------------------- chunk access

    def ensure_chunk(self, cx: int, cy: int) -> Chunk:
        chunk = self.chunks.get((cx, cy))
        if chunk is not None:
            return chunk
        chunk = Chunk(cx, cy, np.zeros((self.chunk_size, self.chunk_size), dtype=np.float64))
        self.chunks[(cx, cy)] = chunk
        self._generate_chunk(chunk)
        return chunk

    def chunk_at(self, position: Position) -> Chunk | None:
        """Read-only chunk lookup; never generates terrain."""

        return self.chunks.get((position[0] // self.chunk_size, position[1] // self.chunk_size))

    def ensure_positions(self, positions) -> None:
        size = self.chunk_size
        keys = {(x // size, y // size) for x, y in positions}
        for cx, cy in keys:
            self.ensure_chunk(cx, cy)

    def _chunk_rng(self, chunk: Chunk) -> Random:
        seed = _mix64(self.terrain_seed ^ _mix64(chunk.cx) ^ (_mix64(chunk.cy) * 3)) & _MASK64
        return Random(seed)

    def _generate_chunk(self, chunk: Chunk) -> None:
        config = self.config
        rng = self._chunk_rng(chunk)
        size = self.chunk_size
        chunk_area = size * size
        region_area = max(1, config.width * config.height)
        density = config.initial_deposits / region_area
        expected = density * chunk_area
        count = int(expected) + (1 if rng.random() < expected % 1.0 else 0)
        elements = [0] * len(self.catalog.elements)
        energy = 0.0
        for _ in range(count):
            x = chunk.cx * size + rng.randrange(size)
            y = chunk.cy * size + rng.randrange(size)
            molecule = (
                self._weighted_molecule(rng) if self.molecule_weights is not None
                else rng.choice(self.catalog.molecules)
            )
            units = rng.randint(config.initial_batch_min, config.initial_batch_max)
            charge = rng.uniform(0.45, 1.0)
            batch = MoleculeBatch(molecule.molecule_id, units, molecule.energy_capacity * units * charge)
            self.deposit_batch((x, y), batch)
            energy += batch.energy
            for element_id, amount in enumerate(molecule.composition):
                elements[element_id] += amount * units
        # Thermal springs: same density scaling as the original whole-map seeding.
        spring_expected = max(1, config.initial_deposits // 8) * chunk_area / region_area
        springs = int(spring_expected) + (1 if rng.random() < spring_expected % 1.0 else 0)
        for _ in range(springs):
            x = chunk.cx * size + rng.randrange(size)
            y = chunk.cy * size + rng.randrange(size)
            amount = rng.uniform(0.1, 2.0)
            self.add_heat((x, y), amount)
            energy += amount
        self.generated_elements = tuple(a + b for a, b in zip(self.generated_elements, elements))
        self.generated_energy += energy

    # ------------------------------------------------------------ coordinates

    def _weighted_molecule(self, rng: Random):
        weights = self.molecule_weights or ()
        draw = rng.random() * sum(weights)
        cumulative = 0.0
        for molecule, weight in zip(self.catalog.molecules, weights):
            cumulative += weight
            if draw < cumulative:
                return molecule
        return self.catalog.molecules[-1]

    def index(self, position: Position) -> Position:
        """Canonical deposit/occupancy key: absolute (unwrapped) coordinates."""

        return (position[0], position[1])

    def position(self, key: Position) -> Position:
        return (key[0], key[1])

    def delta(self, source: Position, target: Position) -> Position:
        return target[0] - source[0], target[1] - source[1]

    def distance(self, source: Position, target: Position) -> int:
        dx, dy = self.delta(source, target)
        return max(abs(dx), abs(dy))

    @staticmethod
    @lru_cache(maxsize=64)
    def footprint_offsets(area: int) -> tuple[Position, ...]:
        radius = 0
        candidates: list[Position] = []
        while len(candidates) < area:
            candidates = [
                (dx, dy)
                for dy in range(-radius, radius + 1)
                for dx in range(-radius, radius + 1)
            ]
            candidates.sort(key=lambda item: (item[0] * item[0] + item[1] * item[1], abs(item[1]), abs(item[0]), item))
            radius += 1
        return tuple(candidates[:area])

    @classmethod
    @lru_cache(maxsize=512)
    def nearby_offsets(cls, area: int, radius: int) -> tuple[Position, ...]:
        offsets = {
            (fx + dx, fy + dy)
            for fx, fy in cls.footprint_offsets(area)
            for dy in range(-radius, radius + 1)
            for dx in range(-radius, radius + 1)
        }
        return tuple(sorted(offsets))

    def footprint(self, organism: Organism) -> tuple[Position, ...]:
        origin_x, origin_y = organism.position
        area = organism.area(self.catalog)
        key = (origin_x, origin_y, area)
        if organism._footprint_key != key:
            organism._footprint_key = key
            organism._footprint_cells = tuple(
                (origin_x + dx, origin_y + dy) for dx, dy in self.footprint_offsets(area)
            )
        self.ensure_positions(organism._footprint_cells)
        return organism._footprint_cells

    def rebuild_occupancy(self, organisms: dict[int, Organism]) -> None:
        self.occupancy.clear()
        for organism in organisms.values():
            if organism.alive:
                self.add_to_occupancy(organism)

    def add_to_occupancy(self, organism: Organism) -> None:
        """Add one organism's current footprint to the spatial index."""

        for position in self.footprint(organism):
            self.occupancy.setdefault(position, set()).add(organism.organism_id)

    def remove_from_occupancy(self, organism: Organism) -> None:
        """Remove one organism's current footprint from the spatial index."""

        self.remove_id_from_occupancy(organism.organism_id, self.footprint(organism))

    def remove_id_from_occupancy(self, organism_id: int, positions: tuple[Position, ...]) -> None:
        """Remove an ID from known positions, including a dead organism's old footprint."""

        for position in positions:
            occupants = self.occupancy.get(position)
            if occupants is None:
                continue
            occupants.discard(organism_id)
            if not occupants:
                del self.occupancy[position]

    def organism_ids_at(self, position: Position) -> set[int]:
        return self.occupancy.get((position[0], position[1]), set())

    def can_place(self, organism: Organism, position: Position, ignore: set[int] | None = None) -> bool:
        origin_x, origin_y = position
        area = organism.area(self.catalog)
        offsets = self.footprint_offsets(area)
        size = self.chunk_size
        chunk_keys = {
            ((origin_x + dx) // size, (origin_y + dy) // size) for dx, dy in offsets
        }
        for cx, cy in chunk_keys:
            self.ensure_chunk(cx, cy)
        occupancy = self.occupancy
        if ignore is None:
            for dx, dy in offsets:
                if occupancy.get((origin_x + dx, origin_y + dy)) is not None:
                    return False
            return True
        for dx, dy in offsets:
            occupants = occupancy.get((origin_x + dx, origin_y + dy))
            if occupants is None:
                continue
            for organism_id in occupants:
                if organism_id not in ignore:
                    return False
        return True

    def nearby_cells(self, organism: Organism, radius: int) -> tuple[Position, ...]:
        origin_x, origin_y = organism.position
        area = organism.area(self.catalog)
        key = (origin_x, origin_y, area)
        cached = organism._nearby_cells_cache.get(radius)
        if cached is None or cached[0] != key:
            cells = tuple(
                (origin_x + dx, origin_y + dy) for dx, dy in self.nearby_offsets(area, radius)
            )
            cached = (key, cells)
            organism._nearby_cells_cache[radius] = cached
        self.ensure_positions(cached[1])
        return cached[1]

    def nearby_organism_ids(self, organism: Organism, radius: int) -> set[int]:
        result: set[int] = set()
        for cell in self.nearby_cells(organism, radius):
            occupants = self.occupancy.get(cell)
            if occupants is not None:
                result.update(occupants)
        result.discard(organism.organism_id)
        return result

    # -------------------------------------------------------------- deposits

    def deposit_batch(self, position: Position, batch: MoleculeBatch) -> None:
        if batch.count <= 0:
            return
        position = (position[0], position[1])
        inventory = self.deposits.setdefault(position, {})
        add_batch(inventory, batch)
        chunk = self.ensure_chunk(position[0] // self.chunk_size, position[1] // self.chunk_size)
        chunk.deposit_positions.add(position)

    def remove_deposit(self, position: Position) -> None:
        position = (position[0], position[1])
        self.deposits.pop(position, None)
        chunk = self.chunks.get((position[0] // self.chunk_size, position[1] // self.chunk_size))
        if chunk is not None:
            chunk.deposit_positions.discard(position)

    def inventory_at(self, position: Position) -> Inventory:
        position = (position[0], position[1])
        inventory = self.deposits.setdefault(position, {})
        if inventory:
            chunk = self.ensure_chunk(position[0] // self.chunk_size, position[1] // self.chunk_size)
            chunk.deposit_positions.add(position)
        return inventory

    def nonempty_inventory_at(self, position: Position) -> Inventory | None:
        return self.deposits.get((position[0], position[1]))

    # ----------------------------------------------------------------- heat

    def clear_heat(self) -> None:
        for chunk in self.chunks.values():
            chunk.heat.fill(0.0)
            chunk.has_heat = False

    def add_heat(self, position: Position, amount: float) -> None:
        if amount <= 0.0:
            return
        size = self.chunk_size
        chunk = self.ensure_chunk(position[0] // size, position[1] // size)
        chunk.heat[position[1] % size, position[0] % size] += amount
        chunk.has_heat = True

    def heat_at(self, position: Position) -> float:
        size = self.chunk_size
        chunk = self.chunks.get((position[0] // size, position[1] // size))
        if chunk is None:
            return 0.0
        return float(chunk.heat[position[1] % size, position[0] % size])

    def remove_heat(self, positions: tuple[Position, ...], amount: float) -> float:
        if amount <= 0.0:
            return 0.0
        size = self.chunk_size
        if len(positions) == 1:
            x, y = positions[0]
            chunk = self.ensure_chunk(x // size, y // size)
            lx, ly = x % size, y % size
            available = float(chunk.heat[ly, lx])
            removed = min(amount, available)
            if removed <= 0.0:
                return 0.0
            remaining = removed
            share = removed * float(chunk.heat[ly, lx]) / available
            debit = min(float(chunk.heat[ly, lx]), share, remaining)
            chunk.heat[ly, lx] -= debit
            remaining -= debit
            if remaining > 1e-12:
                debit = min(float(chunk.heat[ly, lx]), remaining)
                chunk.heat[ly, lx] -= debit
                remaining -= debit
            return removed - max(0.0, remaining)
        self.ensure_positions(positions)
        chunks = [
            (self.chunks[(x // size, y // size)], x % size, y % size) for x, y in positions
        ]
        available = sum(float(chunk.heat[ly, lx]) for chunk, lx, ly in chunks)
        removed = min(amount, available)
        if removed <= 0.0:
            return 0.0
        remaining = removed
        for chunk, lx, ly in chunks:
            share = removed * float(chunk.heat[ly, lx]) / available
            debit = min(float(chunk.heat[ly, lx]), share, remaining)
            chunk.heat[ly, lx] -= debit
            remaining -= debit
        if remaining > 1e-12:
            chunk, lx, ly = chunks[0]
            debit = min(float(chunk.heat[ly, lx]), remaining)
            chunk.heat[ly, lx] -= debit
            remaining -= debit
        return removed - max(0.0, remaining)

    def diffuse_heat(self) -> None:
        """Diffuse heat chunk by chunk with no-flux edges toward ungenerated space.

        Every cell keeps the flux that would leave toward a missing neighbour
        chunk, so energy is conserved exactly no matter which chunks exist.
        """

        rate = self.config.heat_diffusion
        if rate <= 0.0:
            return
        active: dict[tuple[int, int], Chunk] = {}
        for key, chunk in self.chunks.items():
            if not chunk.has_heat:
                continue
            active[key] = chunk
            cx, cy = key
            for neighbor_key in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                neighbor = self.chunks.get(neighbor_key)
                if neighbor is not None:
                    active.setdefault(neighbor_key, neighbor)
        if not active:
            return
        sources = {key: chunk.heat.copy() for key, chunk in active.items()}
        for key, chunk in active.items():
            s = sources[key]
            new = (1.0 - 4.0 * rate) * s
            new[1:, :] += rate * s[:-1, :]
            new[:-1, :] += rate * s[1:, :]
            new[:, 1:] += rate * s[:, :-1]
            new[:, :-1] += rate * s[:, 1:]
            cx, cy = key
            up = sources.get((cx, cy - 1))
            new[0, :] += rate * (up[-1, :] if up is not None else s[0, :])
            down = sources.get((cx, cy + 1))
            new[-1, :] += rate * (down[0, :] if down is not None else s[-1, :])
            left = sources.get((cx - 1, cy))
            new[:, 0] += rate * (left[:, -1] if left is not None else s[:, 0])
            right = sources.get((cx + 1, cy))
            new[:, -1] += rate * (right[:, 0] if right is not None else s[:, -1])
            np.clip(new, 0.0, None, out=new)
            chunk.heat = new
            chunk.has_heat = bool(new.any())

    def total_heat(self) -> float:
        return float(sum(chunk.heat.sum(dtype=np.float64) for chunk in self.chunks.values() if chunk.has_heat))
