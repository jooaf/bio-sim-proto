from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from random import Random

from .config import SimulationConfig

Signature = tuple[float, float, float, float]
Composition = tuple[int, ...]


def _simplex(values: Iterable[float]) -> Signature:
    raw = tuple(max(1e-9, float(value)) for value in values)
    total = sum(raw)
    normalized = tuple(value / total for value in raw)
    if len(normalized) != 4:
        raise ValueError("prototype signatures require four dimensions")
    return normalized  # type: ignore[return-value]


def signature_similarity(left: Signature, right: Signature) -> float:
    """Bounded similarity for diet, pathways, and toxicity."""
    return max(0.0, 1.0 - 0.5 * sum(abs(a - b) for a, b in zip(left, right)))


@dataclass(frozen=True, slots=True)
class ElementDefinition:
    element_id: int
    symbol: str
    atomic_mass: int
    energy_contribution: float
    bond_capacity: int
    polarity: float
    reactivity: float
    rigidity: float
    signature: Signature
    color: tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class MoleculeDefinition:
    molecule_id: int
    composition: Composition
    mass: int
    energy_capacity: float
    signature: Signature
    polarity: float
    reactivity: float
    stability: float
    rigidity: float
    permeability: float
    complexity: float
    color: tuple[int, int, int]

    @property
    def element_units(self) -> int:
        return sum(self.composition)


@dataclass(slots=True)
class MoleculeBatch:
    molecule_id: int
    count: int
    energy: float

    def take(self, count: int) -> MoleculeBatch:
        count = max(0, min(count, self.count))
        if count == 0:
            return MoleculeBatch(self.molecule_id, 0, 0.0)
        taken_energy = self.energy * count / self.count
        self.count -= count
        self.energy -= taken_energy
        if self.count == 0:
            self.energy = 0.0
        return MoleculeBatch(self.molecule_id, count, taken_energy)


Inventory = dict[int, MoleculeBatch]


def add_batch(inventory: Inventory, batch: MoleculeBatch) -> None:
    if batch.count <= 0:
        return
    existing = inventory.get(batch.molecule_id)
    if existing is None:
        inventory[batch.molecule_id] = batch
    else:
        existing.count += batch.count
        existing.energy += batch.energy


def inventory_count(inventory: Inventory) -> int:
    return sum(batch.count for batch in inventory.values())


def inventory_energy(inventory: Inventory) -> float:
    return sum(batch.energy for batch in inventory.values())


@dataclass(frozen=True, slots=True)
class ChemistryCatalog:
    elements: tuple[ElementDefinition, ...]
    molecules: tuple[MoleculeDefinition, ...]

    @classmethod
    def generate(cls, config: SimulationConfig, rng: Random) -> ChemistryCatalog:
        elements: list[ElementDefinition] = []
        for element_id in range(config.element_count):
            signature = _simplex(rng.random() + 0.05 for _ in range(4))
            elements.append(
                ElementDefinition(
                    element_id=element_id,
                    symbol=chr(65 + element_id),
                    atomic_mass=rng.randint(1, 12),
                    energy_contribution=rng.uniform(0.7, 1.5),
                    bond_capacity=rng.randint(1, 4),
                    polarity=rng.random(),
                    reactivity=rng.random(),
                    rigidity=rng.random(),
                    signature=signature,
                    color=(rng.randint(70, 245), rng.randint(70, 245), rng.randint(70, 245)),
                )
            )

        compositions: list[Composition] = []
        seen: set[Composition] = set()
        for element_id in range(config.element_count):
            composition = tuple(1 if i == element_id else 0 for i in range(config.element_count))
            compositions.append(composition)
            seen.add(composition)

        attempts = 0
        while len(compositions) < config.molecule_count and attempts < config.molecule_count * 100:
            attempts += 1
            units = rng.randint(2, config.maximum_molecule_units)
            counts = [0] * config.element_count
            for _ in range(units):
                counts[rng.randrange(config.element_count)] += 1
            composition = tuple(counts)
            if composition in seen:
                continue
            active = [elements[i] for i, count in enumerate(composition) if count]
            total_bonds = sum(element.bond_capacity * composition[element.element_id] for element in active)
            if total_bonds < 2 * (units - 1):
                continue
            seen.add(composition)
            compositions.append(composition)

        molecules = tuple(
            cls._derive_molecule(molecule_id, composition, elements, rng)
            for molecule_id, composition in enumerate(compositions)
        )
        return cls(tuple(elements), molecules)

    @staticmethod
    def _derive_molecule(
        molecule_id: int,
        composition: Composition,
        elements: list[ElementDefinition],
        rng: Random,
    ) -> MoleculeDefinition:
        units = sum(composition)
        weights = [count / units for count in composition]
        mass = sum(count * element.atomic_mass for count, element in zip(composition, elements))
        capacity = sum(count * element.energy_contribution for count, element in zip(composition, elements))
        signature = _simplex(
            sum(weight * element.signature[axis] for weight, element in zip(weights, elements))
            + rng.uniform(-0.04, 0.04)
            for axis in range(4)
        )
        diversity = sum(1 for count in composition if count) / len(elements)
        polarity = min(1.0, max(0.0, sum(w * e.polarity for w, e in zip(weights, elements)) + rng.uniform(-0.08, 0.08)))
        reactivity = min(1.0, max(0.0, sum(w * e.reactivity for w, e in zip(weights, elements)) + 0.15 * diversity + rng.uniform(-0.08, 0.08)))
        rigidity = min(1.0, max(0.0, sum(w * e.rigidity for w, e in zip(weights, elements)) + rng.uniform(-0.08, 0.08)))
        stability = min(1.0, max(0.0, 0.75 - 0.45 * reactivity + 0.25 * rigidity + rng.uniform(-0.08, 0.08)))
        complexity = min(1.0, (units - 1) / 11 + diversity * 0.25)
        permeability = min(1.0, max(0.05, 1.0 - 0.65 * complexity + 0.15 * polarity))
        color = tuple(
            int(min(255, max(35, sum(w * e.color[channel] for w, e in zip(weights, elements)))))
            for channel in range(3)
        )
        return MoleculeDefinition(
            molecule_id=molecule_id,
            composition=composition,
            mass=mass,
            energy_capacity=capacity,
            signature=signature,
            polarity=polarity,
            reactivity=reactivity,
            stability=stability,
            rigidity=rigidity,
            permeability=permeability,
            complexity=complexity,
            color=color,  # type: ignore[arg-type]
        )

    def element_totals(self, inventories: Iterable[Inventory]) -> tuple[int, ...]:
        totals = [0] * len(self.elements)
        for inventory in inventories:
            for molecule_id, batch in inventory.items():
                definition = self.molecules[molecule_id]
                for element_id, amount in enumerate(definition.composition):
                    totals[element_id] += amount * batch.count
        return tuple(totals)

    def validate_batch(self, batch: MoleculeBatch) -> None:
        if batch.count < 0 or batch.energy < -1e-12:
            raise AssertionError("negative molecule batch")
        capacity = batch.count * self.molecules[batch.molecule_id].energy_capacity
        if batch.energy > capacity + 1e-9:
            raise AssertionError("molecule batch exceeds energy capacity")

    def inventory_mass(self, inventory: Inventory) -> int:
        return sum(self.molecules[mid].mass * batch.count for mid, batch in inventory.items())

    def inventory_signature(self, inventory: Inventory) -> Signature:
        weighted = [0.0] * 4
        total_mass = 0.0
        for molecule_id, batch in inventory.items():
            definition = self.molecules[molecule_id]
            weight = definition.mass * batch.count
            total_mass += weight
            for axis in range(4):
                weighted[axis] += weight * definition.signature[axis]
        if total_mass <= 0:
            return (0.25, 0.25, 0.25, 0.25)
        return _simplex(value / total_mass for value in weighted)

    @property
    def reference_energy(self) -> float:
        ordered = sorted(molecule.energy_capacity for molecule in self.molecules)
        return ordered[len(ordered) // 2]
