from __future__ import annotations

from dataclasses import dataclass, field

from .chemistry import (
    ChemistryCatalog,
    Inventory,
    Signature,
    inventory_energy,
    signature_similarity,
)
from .genetics import ACTIONS, FEATURES, Genome, Phenotype

Position = tuple[int, int]


@dataclass(slots=True)
class Organism:
    organism_id: int
    lineage_id: int
    genome: Genome
    phenotype: Phenotype
    species_id: int
    parent_ids: tuple[int, ...]
    generation: int
    birth_tick: int
    position: Position
    body: Inventory
    gut: Inventory = field(default_factory=dict)
    waste: Inventory = field(default_factory=dict)
    mana: float = 0.0
    integrity: float = 1.0
    max_integrity: float = 1.0
    target_mass: float = 1.0
    maintenance_debt: float = 0.0
    toxin_load: float = 0.0
    reproduction_cooldown: int = 0
    alive: bool = True
    facing: Position = (1, 0)
    next_action_tick: int = 0
    last_action: str = "born"
    offspring_count: int = 0
    kills: int = 0
    colony_id: int | None = None
    statuses: dict[str, tuple[int, float]] = field(default_factory=dict)
    _cached_structural_mass: int | None = field(default=None, init=False, repr=False, compare=False)
    _cached_energy_capacity: float | None = field(default=None, init=False, repr=False, compare=False)
    _cached_body_signature: Signature | None = field(default=None, init=False, repr=False, compare=False)
    _food_chemistry: tuple[tuple[float, float], ...] | None = field(
        default=None, init=False, repr=False, compare=False
    )
    _footprint_key: tuple[int, int, int] | None = field(
        default=None, init=False, repr=False, compare=False
    )
    _footprint_cells: tuple[Position, ...] = field(
        default=(), init=False, repr=False, compare=False
    )
    _nearby_cells_cache: dict[
        int, tuple[tuple[int, int, int], tuple[Position, ...]]
    ] = field(default_factory=dict, init=False, repr=False, compare=False)
    _policy_vectors: dict[str, tuple[float, ...]] | None = field(
        default=None, init=False, repr=False, compare=False
    )
    _distance_origin: Position | None = field(default=None, init=False, repr=False, compare=False)
    _distance_cache: dict[Position, int] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _maturity_multiplier: float | None = field(default=None, init=False, repr=False, compare=False)
    _cached_maturity_age: int = field(default=1, init=False, repr=False, compare=False)

    def inventories(self) -> tuple[Inventory, Inventory, Inventory]:
        return self.body, self.gut, self.waste

    def mass(self, catalog: ChemistryCatalog) -> int:
        return sum(catalog.inventory_mass(inventory) for inventory in self.inventories())

    def structural_mass(self, catalog: ChemistryCatalog) -> int:
        if self._cached_structural_mass is None:
            self._cached_structural_mass = catalog.inventory_mass(self.body)
        return self._cached_structural_mass

    def invalidate_body_cache(self) -> None:
        """Invalidate values derived from body molecule counts after matter transfer."""

        self._cached_structural_mass = None
        self._cached_energy_capacity = None
        self._cached_body_signature = None

    def area(self, catalog: ChemistryCatalog) -> int:
        ratio = min(1.0, self.structural_mass(catalog) / max(1.0, self.target_mass))
        return max(1, min(self.phenotype.adult_area, round(self.phenotype.adult_area * ratio)))

    def chemical_energy(self) -> float:
        return inventory_energy(self.body)

    def energy_capacity(self, catalog: ChemistryCatalog) -> float:
        if self._cached_energy_capacity is None:
            self._cached_energy_capacity = sum(
                catalog.molecules[mid].energy_capacity * batch.count for mid, batch in self.body.items()
            )
        return self._cached_energy_capacity

    def energy_fraction(self, catalog: ChemistryCatalog) -> float:
        capacity = self.energy_capacity(catalog)
        return self.chemical_energy() / capacity if capacity else 0.0

    def add_body_energy(self, amount: float, catalog: ChemistryCatalog) -> float:
        remaining = max(0.0, amount)
        for molecule_id in sorted(self.body):
            batch = self.body[molecule_id]
            capacity = catalog.molecules[molecule_id].energy_capacity * batch.count
            accepted = min(remaining, max(0.0, capacity - batch.energy))
            batch.energy += accepted
            remaining -= accepted
            if remaining <= 1e-15:
                break
        return amount - remaining

    def consume_body_energy(self, amount: float) -> float:
        remaining = max(0.0, amount)
        consumed = 0.0
        for molecule_id in sorted(self.body):
            batch = self.body[molecule_id]
            debit = min(batch.energy, remaining)
            batch.energy -= debit
            remaining -= debit
            consumed += debit
            if remaining <= 1e-15:
                break
        return consumed

    def body_signature(self, catalog: ChemistryCatalog) -> Signature:
        if self._cached_body_signature is None:
            self._cached_body_signature = catalog.inventory_signature(self.body)
        return self._cached_body_signature

    def policy_vectors(self) -> dict[str, tuple[float, ...]]:
        if self._policy_vectors is None:
            self._policy_vectors = {
                action: tuple(self.phenotype.policy[action][feature] for feature in FEATURES)
                for action in ACTIONS
            }
        return self._policy_vectors

    def food_chemistry(self, catalog: ChemistryCatalog) -> tuple[tuple[float, float], ...]:
        """Cache immutable diet match and toxicity hazard by molecule ID."""

        if self._food_chemistry is None:
            tolerance = max(self.phenotype.toxin_tolerance, 0.1)
            self._food_chemistry = tuple(
                (
                    signature_similarity(definition.signature, self.phenotype.diet_signature),
                    definition.reactivity
                    * sum(
                        a * b
                        for a, b in zip(
                            definition.signature,
                            self.phenotype.toxin_sensitivity,
                        )
                    )
                    / tolerance,
                )
                for definition in catalog.molecules
            )
        return self._food_chemistry


@dataclass(slots=True)
class Species:
    species_id: int
    representative_genome: Genome
    color: tuple[int, int, int]
    created_tick: int
    origin: str = "founder"
    parent_species_ids: tuple[int, ...] = ()
    founder_organism_id: int | None = None
    population: int = 0
    births: int = 0
    deaths: int = 0


@dataclass(slots=True)
class MagicEffect:
    effect_id: int
    channel: int
    source_id: int
    target_id: int
    energy: float
    expires_tick: int


@dataclass(slots=True)
class Corpse:
    corpse_id: int
    source_id: int
    position: Position
    inventory: Inventory
    created_tick: int


@dataclass(slots=True)
class Colony:
    colony_id: int
    members: set[int]
    bonus: float
    created_tick: int


@dataclass(slots=True)
class SimulationStats:
    births: int = 0
    deaths: int = 0
    reproduction_attempts: int = 0
    reproduction_resource_blocks: int = 0
    reproduction_mate_readiness_blocks: int = 0
    reproduction_energy_blocks: int = 0
    reproduction_body_matter_blocks: int = 0
    reproduction_matter_blocks_by_molecule: dict[int, int] = field(default_factory=dict)
    reproduction_probability_failures: int = 0
    reproduction_placement_failures: int = 0
    failed_reproductions: int = 0
    successful_reproductions: int = 0
    asexual_reproduction_events: int = 0
    sexual_reproduction_events: int = 0
    attacks: int = 0
    magic_casts: int = 0
    alliances: int = 0
    colonies: int = 0
    audit_error: float = 0.0
