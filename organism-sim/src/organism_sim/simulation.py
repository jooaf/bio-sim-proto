from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import ceil, exp, sqrt
from random import Random
from statistics import median

from .chemistry import (
    ChemistryCatalog,
    Inventory,
    MoleculeBatch,
    add_batch,
    inventory_count,
    inventory_energy,
    signature_similarity,
)
from .config import BehaviorModel, Scheduler, SimulationConfig
from .entities import Colony, Corpse, MagicEffect, Organism, SimulationStats, Species
from .genetics import ACTIONS, GUILDS, Genome, Phenotype, species_color
from .randomness import RandomStreams
from .world import World


@dataclass(frozen=True, slots=True)
class FoodCandidate:
    position: tuple[int, int]
    molecule_id: int
    score: float


class Simulation:
    """Compact, deterministic prototype engine.

    The engine deliberately keeps all state transitions in one class. The later
    engineered version can split systems according to SPEC.md after the rules
    prove interesting in play.
    """

    def __init__(self, config: SimulationConfig | None = None):
        self.config = config or SimulationConfig()
        self.config.validate()
        if self.config.behavior_model != BehaviorModel.LEGACY_LINEAR_MACRO_V1:
            raise ValueError("V2 behavior models require the Rust engine")
        if self.config.scheduler != Scheduler.SERIAL_V2:
            raise ValueError("parallel schedulers require the Rust engine")
        if self.config.seasons_enabled:
            raise ValueError("random environment seasons require the Rust engine")
        if self.config.cellular_emergence_enabled:
            raise ValueError("stochastic cellular affordances require the Rust engine")
        if self.config.biodeposits_enabled:
            raise ValueError("physical biodeposits require the Rust engine")
        random_streams = RandomStreams.from_seed(self.config.seed)
        self.rng = random_streams.dynamics
        self.catalog = ChemistryCatalog.generate(self.config, random_streams.chemistry)
        self._molecule_instability = tuple(1.0 - molecule.stability for molecule in self.catalog.molecules)
        self.world = World.generate(self.config, self.catalog, random_streams.world)
        self.organisms: dict[int, Organism] = {}
        self.living_ids: dict[int, None] = {}
        self.species: dict[int, Species] = {}
        self.corpses: dict[int, Corpse] = {}
        self.effects: dict[int, MagicEffect] = {}
        self.colonies: dict[int, Colony] = {}
        self.alliances: set[frozenset[int]] = set()
        self.alliance_events: list[tuple[int, int, int]] = []
        self.colony_events: list[tuple[int, int]] = []
        self.death_events: list[tuple[int, int]] = []
        self.sexual_parent_ids: set[int] = set()
        self.stats = SimulationStats()
        self.tick = 0
        self._next_organism_id = 1
        self._next_genome_id = 1
        self._next_species_id = 1
        self._next_effect_id = 1
        self._next_corpse_id = 1
        self._next_colony_id = 1
        self._occupancy_dirty: dict[int, tuple[tuple[int, int], ...]] = {}
        self._genome_distances: dict[tuple[int, int], float] = {}
        self.reference_energy = self.catalog.reference_energy
        self.reference_body_mass = 1.0
        self._spawn_founders(random_streams.founders)
        if self.config.deposit_match_ecology:
            # Phase-1 B-experiment: an established ecology's matter demand equals
            # its own body-content histogram, so a demand-matched deposit pool
            # stops binding. The founder region keeps primordial uniform geology;
            # chunks generated on demand after founding mirror founder demand.
            self.world.molecule_weights = self._founder_body_weights()
        masses = [self.organisms[organism_id].structural_mass(self.catalog) for organism_id in self.living_ids]
        self.reference_body_mass = float(median(masses)) if masses else 1.0
        # Geological generation (chunks appearing on demand) adds matter and
        # energy throughout the run; audits only police the dynamic budget.
        self.initial_elements = self._dynamic_element_totals()
        self.initial_energy = self.total_energy() - self.world.generated_energy
        self.last_audit_error = 0.0

    # ------------------------------------------------------------------ setup

    def _spawn_founders(self, rng: Random) -> None:
        archetype_count = min(self.config.founder_archetype_count, self.config.founder_count)
        archetypes = tuple(
            Genome.random(
                self._claim_genome_id(),
                rng,
                guild=GUILDS[index % len(GUILDS)],
                diet_anchor=self._sample_diet_anchor(GUILDS[index % len(GUILDS)], rng),
            )
            for index in range(archetype_count)
        )
        archetype_species: dict[int, int] = {}
        for founder_index in range(self.config.founder_count):
            archetype_index = founder_index if founder_index < archetype_count else rng.randrange(archetype_count)
            archetype = archetypes[archetype_index]
            genome = Genome.offspring(self._claim_genome_id(), (archetype,), rng, 0.20)
            phenotype = Phenotype.sample(genome, rng, self.config)
            body: Inventory = {}
            # Bodies are built from molecules the founder can actually digest,
            # so morphology follows diet instead of being unrelated soup.
            digestible = sorted(
                self.catalog.molecules,
                key=lambda molecule: -signature_similarity(
                    molecule.signature, phenotype.diet_signature
                ),
            )
            pool = digestible[: max(3, len(digestible) // 3)]
            molecule_choices = rng.sample(pool, k=min(rng.randint(2, 4), len(pool)))
            total_units = max(4, phenotype.adult_area * rng.randint(2, 4))
            for index, molecule in enumerate(molecule_choices):
                count = max(1, total_units // len(molecule_choices) + (1 if index < total_units % len(molecule_choices) else 0))
                add_batch(
                    body,
                    MoleculeBatch(
                        molecule.molecule_id,
                        count,
                        molecule.energy_capacity * count * rng.uniform(0.45, 0.95),
                    ),
                )
            target_mass = float(self.catalog.inventory_mass(body))
            organism_id = self._claim_organism_id()
            organism = Organism(
                organism_id=organism_id,
                lineage_id=organism_id,
                genome=genome,
                phenotype=phenotype,
                species_id=-1,
                parent_ids=(),
                generation=0,
                birth_tick=0,
                position=(0, 0),
                body=body,
                mana=rng.uniform(0.0, phenotype.mana_capacity * 0.2),
                target_mass=target_mass,
            )
            organism.max_integrity = max(2.0, 4.0 + phenotype.adult_area * phenotype.density * 2.0)
            organism.integrity = organism.max_integrity
            if not self._place_founder(organism, rng):
                continue
            if archetype_index not in archetype_species:
                archetype_species[archetype_index] = self._create_species(genome, origin="founder")
            else:
                self.species[archetype_species[archetype_index]].population += 1
            organism.species_id = archetype_species[archetype_index]
            self.organisms[organism.organism_id] = organism
            self.living_ids[organism.organism_id] = None
            self.world.add_to_occupancy(organism)

    def _founder_body_weights(self) -> tuple[float, ...]:
        """Demand histogram over molecule IDs from all founder bodies."""

        totals = [0.0] * len(self.catalog.molecules)
        for organism_id in self.living_ids:
            organism = self.organisms[organism_id]
            for molecule_id, batch in organism.body.items():
                totals[molecule_id] += batch.count
        total = sum(totals)
        if total <= 0.0:
            return tuple(1.0 for _ in totals)
        return tuple(value / total for value in totals)

    def _sample_diet_anchor(self, guild: str, rng: Random):
        """Pick a diet anchor from real catalog chemistry so founders can
        digest the food their region actually contains."""

        if guild == "generalist":
            return None
        molecules = self.catalog.molecules
        if guild == "grazer":
            # Grazers anchor on stable, simple molecules worth eating slowly.
            ordered = sorted(molecules, key=lambda m: (m.complexity, -m.stability))
        elif guild == "hunter":
            ordered = sorted(molecules, key=lambda m: -m.energy_capacity)
        else:
            ordered = list(molecules)
        pool = ordered[: max(2, len(ordered) // 2)]
        picked = rng.sample(pool, k=min(2, len(pool)))
        anchor = [sum(molecule.signature[axis] for molecule in picked) / len(picked) for axis in range(4)]
        total = sum(anchor)
        return tuple(value / total for value in anchor)

    def _place_founder(self, organism: Organism, rng: Random) -> bool:
        for _ in range(300):
            position = (rng.randrange(self.config.width), rng.randrange(self.config.height))
            if self.world.can_place(organism, position):
                organism.position = position
                return True
        return False

    def _claim_organism_id(self) -> int:
        value = self._next_organism_id
        self._next_organism_id += 1
        return value

    def _claim_genome_id(self) -> int:
        value = self._next_genome_id
        self._next_genome_id += 1
        return value

    # --------------------------------------------------------------- main tick

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            self.tick += 1
            self.world.diffuse_heat()
            self._produce_deposits()
            self._resolve_effects()
            self._decompose_environment()
            order = sorted(self.living_ids)
            self.rng.shuffle(order)
            for organism_id in order:
                organism = self.organisms.get(organism_id)
                if organism is None or not organism.alive:
                    continue
                self._upkeep(organism)
                if not organism.alive:
                    continue
                self._digest(organism)
                if self.tick >= organism.next_action_tick:
                    self._decide_and_act(organism)
            self._expire_corpses()
            self._refresh_dirty_occupancy()
            if self.config.audit_every > 0 and self.tick % self.config.audit_every == 0:
                self.audit()

    def _upkeep(self, organism: Organism) -> None:
        production_target = self.reference_energy * self.config.primary_production_rate
        if production_target > 0.0:
            harvested = self.world.remove_heat(self.world.footprint(organism), production_target)
            produced = organism.add_body_energy(harvested, self.catalog)
            self.world.add_heat(organism.position, harvested - produced)

        decay = min(organism.mana, organism.mana * self.config.mana_decay)
        organism.mana -= decay
        self.world.add_heat(organism.position, decay)

        colony_bonus = 0.0
        if organism.colony_id is not None and organism.colony_id in self.colonies:
            colony_bonus = self.colonies[organism.colony_id].bonus
        demand = (
            organism.phenotype.basal
            * self.reference_energy
            * self.config.maintenance_cost_multiplier
            * (1.0 - colony_bonus)
        )
        mana_target = demand * organism.phenotype.mana_preference
        mana_paid = min(organism.mana, mana_target)
        organism.mana -= mana_paid
        chemical_paid = organism.consume_body_energy(demand - mana_paid)
        paid = mana_paid + chemical_paid
        self.world.add_heat(organism.position, paid)
        deficit = demand - paid
        if deficit > 1e-12:
            organism.maintenance_debt += deficit
            organism.integrity -= deficit / max(self.reference_energy, 1e-9) * 0.25
        else:
            organism.maintenance_debt = max(0.0, organism.maintenance_debt - demand * 0.2)

        if organism.toxin_load > organism.phenotype.toxin_tolerance:
            excess = organism.toxin_load - organism.phenotype.toxin_tolerance
            organism.integrity -= excess * 0.0015
        organism.toxin_load *= 0.999

        age = self.tick - organism.birth_tick
        if age > organism.phenotype.lifespan:
            ratio = age / organism.phenotype.lifespan
            base_hazard = min(0.08, 0.0005 * ratio * ratio)
            support_budget = min(
                organism.chemical_energy() * 0.002,
                organism.mana * 0.002,
                base_hazard * self.reference_energy,
            )
            if support_budget > 0.0:
                mana_support = min(organism.mana, support_budget * 0.5)
                organism.mana -= mana_support
                chemical_support = organism.consume_body_energy(support_budget - mana_support)
                spent = mana_support + chemical_support
                self.world.add_heat(organism.position, spent)
                base_hazard *= max(0.05, 1.0 - spent / max(base_hazard * self.reference_energy, 1e-9))
            if self.rng.random() < base_hazard:
                organism.integrity = 0.0

        if organism.integrity <= 0.0 or organism.maintenance_debt > self.reference_energy * 4.0:
            self._kill(organism, "attrition")

    # ------------------------------------------------------------ chemistry

    def _digest(self, organism: Organism) -> None:
        if not organism.gut or self.rng.random() > min(1.0, self.config.reaction_rate * 0.35):
            return
        molecule_id = min(organism.gut)
        source = organism.gut[molecule_id]
        product = source.take(1)
        if source.count == 0:
            del organism.gut[molecule_id]
        definition = self.catalog.molecules[molecule_id]
        match = signature_similarity(definition.signature, organism.phenotype.diet_signature)

        activation_target = self.reference_energy * 0.0005
        activation = organism.consume_body_energy(activation_target)
        self.world.add_heat(organism.position, activation)

        capture_target = product.energy * organism.phenotype.digestion * match
        captured = organism.add_body_energy(capture_target, self.catalog)
        remaining = product.energy - captured
        process_heat = remaining * 0.15
        product.energy = max(0.0, remaining - process_heat)
        self.world.add_heat(organism.position, process_heat)

        sensitivity = sum(a * b for a, b in zip(definition.signature, organism.phenotype.toxin_sensitivity))
        organism.toxin_load += definition.reactivity * definition.permeability * sensitivity

        if self.rng.random() < organism.phenotype.assimilation * match and organism.structural_mass(self.catalog) < organism.target_mass * 1.3:
            self._mark_occupancy_dirty(organism)
            add_batch(organism.body, product)
            organism.invalidate_body_cache()
        else:
            add_batch(organism.waste, product)

        if organism.toxin_load > organism.phenotype.toxin_tolerance:
            detox_cost = min(organism.chemical_energy(), self.reference_energy * 0.002)
            spent = organism.consume_body_energy(detox_cost)
            self.world.add_heat(organism.position, spent)
            organism.toxin_load = max(0.0, organism.toxin_load - spent / max(self.reference_energy, 1e-9) * 2.0)

        if inventory_count(organism.waste) > 12:
            waste_id = min(organism.waste)
            expelled = organism.waste[waste_id].take(max(1, organism.waste[waste_id].count // 2))
            if organism.waste[waste_id].count == 0:
                del organism.waste[waste_id]
            self.world.deposit_batch(organism.position, expelled)

    def _decompose_environment(self) -> None:
        if self.config.decomposition_rate <= 0.0:
            return
        rate = self.config.decomposition_rate
        instability = self._molecule_instability
        world = self.world
        add_heat = world.add_heat
        for position, inventory in world.deposits.items():
            released = 0.0
            for molecule_id, batch in inventory.items():
                amount = batch.energy * rate * instability[molecule_id]
                batch.energy -= amount
                released += amount
            if released:
                add_heat(position, released)

    def _produce_deposits(self) -> None:
        """Recharge deposit chemical energy from ambient heat each tick.

        This is the ecosystem's sustained energy influx (a photosynthesis
        analogue): without it, chemical energy flows one way into heat and the
        food web runs down its initial budget, so mortality is dominated by
        attrition and selection has no renewable resource to compete over.
        Heat removed equals chemical energy added, exactly conserving energy;
        matter and molecule counts are untouched.
        """
        rate = self.config.deposit_production_rate
        if rate <= 0.0:
            return
        world = self.world
        remove_heat = world.remove_heat
        heat_at = world.heat_at
        molecules = self.catalog.molecules
        for position, inventory in world.deposits.items():
            heat = heat_at(position)
            if heat <= 1e-12:
                continue
            if len(inventory) == 1:
                batch = next(iter(inventory.values()))
                capacity = (
                    molecules[batch.molecule_id].energy_capacity * batch.count - batch.energy
                )
                if capacity <= 1e-12:
                    continue
                removed = remove_heat((position,), min(heat * rate, capacity))
                if removed > 0.0:
                    batch.energy += removed
                continue
            batches = tuple(inventory.values())
            headrooms: list[float] = []
            capacity = 0.0
            for batch in batches:
                headroom = molecules[batch.molecule_id].energy_capacity * batch.count - batch.energy
                headrooms.append(headroom)
                capacity += headroom
            if capacity <= 1e-12:
                continue
            wanted = min(heat * rate, capacity)
            removed = remove_heat((position,), wanted)
            if removed <= 0.0:
                continue
            for batch, headroom in zip(batches, headrooms):
                if headroom > 0.0:
                    batch.energy += removed * (headroom / capacity)

    # -------------------------------------------------------------- decisions

    def _decide_and_act(self, organism: Organism) -> None:
        effective_sight = organism.phenotype.sight
        radius_one_cells = self.world.nearby_cells(organism, 1)
        cells = radius_one_cells
        if effective_sight > 1:
            expanded_cells = self.world.nearby_cells(organism, effective_sight)
            sight_cost = (
                self.config.sight_cost_per_cell
                * self.reference_energy
                * max(0, len(expanded_cells) - len(radius_one_cells))
            )
            if organism.chemical_energy() >= sight_cost:
                spent = organism.consume_body_energy(sight_cost)
                self.world.add_heat(organism.position, spent)
                cells = expanded_cells
            else:
                effective_sight = 1
        food = self._best_food(organism, cells)
        heat_at = self.world.heat_at
        cell_iter = iter(cells)
        heat_position = next(cell_iter)
        local_heat = heat_at(heat_position)
        for position in cell_iter:
            heat = heat_at(position)
            if heat > local_heat:
                heat_position = position
                local_heat = heat
        occupancy = self.world.occupancy
        nearby_ids: set[int] = set()
        for cell in cells:
            occupants = occupancy.get(cell)
            if occupants is not None:
                nearby_ids.update(occupants)
        nearby_ids.discard(organism.organism_id)
        organisms = self.organisms
        nearby: list[Organism] = []
        for organism_id in nearby_ids:
            other = organisms.get(organism_id)
            if other is not None and other.alive:
                nearby.append(other)
        contact_ids: set[int] = set()
        for cell in radius_one_cells:
            occupants = occupancy.get(cell)
            if occupants is not None:
                contact_ids.update(occupants)
        contact_ids.discard(organism.organism_id)
        contact: list[Organism] = []
        for organism_id in contact_ids:
            other = organisms.get(organism_id)
            if other is not None and other.alive:
                contact.append(other)
        prey = self._best_prey(organism, nearby)
        visible_mate = self._best_mate(organism, nearby)
        contact_mate = self._best_mate(organism, contact)
        threat_target: Organism | None = None
        threat = 0.0
        for other in nearby:
            score = other.phenotype.attack * other.structural_mass(self.catalog)
            if threat_target is None or score > threat:
                threat_target = other
                threat = score
        hunger = 1.0 - organism.energy_fraction(self.catalog)
        feature_values = (
            hunger,
            max(0.0, food.score) if food else 0.0,
            min(1.0, local_heat / max(self.reference_energy, 1e-9)),
            min(1.0, threat / max(self.reference_body_mass, 1.0)),
            1.0 if prey else 0.0,
            min(1.0, organism.toxin_load / max(organism.phenotype.toxin_tolerance, 1e-9)),
            organism.mana / max(organism.phenotype.mana_capacity, 1e-9),
            max(
                1.0 if visible_mate else 0.0,
                organism.phenotype.asexual,
                self.config.asexual_probability_floor,
            ),
            min(1.0, len(nearby) / 8.0),
            hunger,
        )
        eligible = set(ACTIONS)
        on_food = food is not None and food.position in self.world.footprint(organism)
        if food is None:
            eligible.discard("forage")
        if not on_food:
            eligible.discard("eat")
        if local_heat <= 1e-9 or organism.mana >= organism.phenotype.mana_capacity:
            eligible.discard("heat")
        if organism.toxin_load <= organism.phenotype.toxin_tolerance * 0.5:
            eligible.discard("detox")
        prey_is_touching = prey is not None and prey.organism_id in contact_ids
        if prey is None or prey_is_touching:
            eligible.discard("hunt")
        if not prey_is_touching:
            eligible.discard("attack")
        if threat_target is None:
            eligible.discard("flee")
        if visible_mate is None or visible_mate.organism_id in contact_ids:
            eligible.discard("seek_mate")
        if prey is None or organism.mana <= 1e-9:
            eligible.discard("magic")
        mature = self._is_reproductively_ready(organism)
        if not mature:
            eligible.discard("reproduce")
        if not contact:
            eligible.discard("ally")

        action = self._sample_action(organism, feature_values, eligible)
        organism.last_action = action
        slowed = 2.0 if "water" in organism.statuses else 1.0
        base_delay = max(1, ceil(4.0 / organism.phenotype.speed * slowed))
        organism.next_action_tick = self.tick + base_delay

        if action == "eat" and food:
            self._eat(organism, food)
        elif action == "heat":
            self._seek_or_absorb_heat(organism, heat_position)
        elif action == "detox":
            self._active_detox(organism)
        elif action == "attack" and prey:
            self._attack(organism, prey)
        elif action == "magic" and prey:
            self._cast_magic(organism, prey)
        elif action == "reproduce":
            self._attempt_reproduction(organism, contact_mate)
        elif action == "ally" and contact:
            self._attempt_alliance(organism, self.rng.choice(contact))
        elif action == "forage" and food:
            self._move(organism, food.position)
        elif action == "hunt" and prey:
            self._move(organism, prey.position)
        elif action == "flee" and threat_target:
            self._move_away(organism, threat_target.position)
        elif action == "seek_mate" and visible_mate:
            self._move(organism, visible_mate.position)
        elif action == "wander":
            self._move(organism, None)
        elif action == "rest" and organism.integrity < organism.max_integrity:
            self._repair(organism)

    def _sample_action(
        self,
        organism: Organism,
        feature_values: tuple[float, ...],
        eligible: set[str],
    ) -> str:
        scored: list[tuple[str, float]] = []
        policy_vectors = organism.policy_vectors()
        for action in sorted(eligible):
            weights = policy_vectors[action]
            score = (
                weights[0] * feature_values[0]
                + weights[1] * feature_values[1]
                + weights[2] * feature_values[2]
                + weights[3] * feature_values[3]
                + weights[4] * feature_values[4]
                + weights[5] * feature_values[5]
                + weights[6] * feature_values[6]
                + weights[7] * feature_values[7]
                + weights[8] * feature_values[8]
                + weights[9] * feature_values[9]
            )
            if action == "reproduce":
                reserve_factor = max(0.0, 1.0 - feature_values[0])
                reproductive_signal = max(0.25, feature_values[7])
                score += self.config.reproduction_action_bonus * reserve_factor * reproductive_signal
            scored.append((action, score))
        if not scored:
            return "rest"
        maximum = max(score for _, score in scored)
        weights = [exp(max(-30.0, min(30.0, score - maximum))) for _, score in scored]
        choice = self.rng.random() * sum(weights)
        for (action, _), weight in zip(scored, weights):
            choice -= weight
            if choice <= 0.0:
                return action
        return scored[-1][0]

    def _distance_from(self, organism: Organism, target: tuple[int, int]) -> int:
        if organism._distance_origin != organism.position:
            organism._distance_origin = organism.position
            organism._distance_cache.clear()
        distance = organism._distance_cache.get(target)
        if distance is None:
            distance = self.world.distance(organism.position, target)
            organism._distance_cache[target] = distance
        return distance

    def _best_food(self, organism: Organism, cells: Iterable[tuple[int, int]]) -> FoodCandidate | None:
        best: FoodCandidate | None = None
        chemistry = organism.food_chemistry(self.catalog)
        reference_energy = max(self.reference_energy, 1e-9)
        deposits = self.world.deposits
        if organism._distance_origin != organism.position:
            organism._distance_origin = organism.position
            organism._distance_cache.clear()
        distance_cache = organism._distance_cache
        world_distance = self.world.distance
        uniform = self.rng.uniform
        noise_scale = 0.25 + organism.phenotype.risk
        for position in cells:
            inventory = deposits.get(position)
            if not inventory:
                continue
            distance = distance_cache.get(position)
            if distance is None:
                distance = world_distance(organism.position, position)
                distance_cache[position] = distance
            distance_cost = distance * 0.03
            for molecule_id, batch in inventory.items():
                if batch.count <= 0:
                    continue
                match, hazard = chemistry[molecule_id]
                energy_density = batch.energy / batch.count / reference_energy
                score = match * energy_density - hazard - distance_cost
                score += uniform(-0.08, 0.08) * noise_scale
                if best is None or score > best.score:
                    best = FoodCandidate(position, molecule_id, score)
        return best if best and best.score > -0.1 else None

    def _best_prey(self, organism: Organism, nearby: list[Organism]) -> Organism | None:
        best: Organism | None = None
        best_score = 0.0
        threshold = self.config.prey_compatibility_threshold
        risk_scale = 0.25 + organism.phenotype.risk
        organism_mass = organism.structural_mass(self.catalog)
        uniform = self.rng.uniform
        distance_from = self._distance_from
        for other in nearby:
            compatibility = signature_similarity(organism.phenotype.diet_signature, other.body_signature(self.catalog))
            if compatibility < threshold:
                continue
            size_advantage = organism_mass / max(1, other.structural_mass(self.catalog))
            score = compatibility + 0.25 * size_advantage - distance_from(organism, other.position) * 0.05
            score += uniform(-0.05, 0.05) * risk_scale
            if best is None or score > best_score:
                best = other
                best_score = score
        return best

    def _genome_distance(self, left: Genome, right: Genome) -> float:
        key = (
            (left.genome_id, right.genome_id)
            if left.genome_id <= right.genome_id
            else (right.genome_id, left.genome_id)
        )
        distance = self._genome_distances.get(key)
        if distance is None:
            distance = left.distance(right)
            self._genome_distances[key] = distance
        return distance

    def _best_mate(self, organism: Organism, contact: list[Organism]) -> Organism | None:
        best: Organism | None = None
        best_score = 0.0
        uniform = self.rng.uniform
        genome_distance = self._genome_distance
        for other in contact:
            if not self._is_reproductively_ready(other) or other.phenotype.sexual <= 0.05:
                continue
            score = genome_distance(organism.genome, other.genome) + uniform(0.0, 0.03)
            if best is None or score < best_score:
                best = other
                best_score = score
        return best

    # ---------------------------------------------------------------- actions

    def _move(self, organism: Organism, target: tuple[int, int] | None) -> bool:
        if target is None:
            dx, dy = self.rng.choice(
                ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))
            )
        else:
            delta = self.world.delta(organism.position, target)
            dx = 0 if delta[0] == 0 else (1 if delta[0] > 0 else -1)
            dy = 0 if delta[1] == 0 else (1 if delta[1] > 0 else -1)
            if dx == 0 and dy == 0:
                return False
            # Choose among steps that still reduce distance. This keeps
            # pursuit directed while preventing every organism from tracing the
            # same deterministic diagonal path.
            options = {(dx, dy)}
            if dx:
                options.add((dx, 0))
            if dy:
                options.add((0, dy))
            reducing = [
                direction
                for direction in options
                if self.world.distance(
                    (organism.position[0] + direction[0], organism.position[1] + direction[1]),
                    target,
                )
                < self.world.distance(organism.position, target)
            ]
            if reducing and self.rng.random() < 0.30:
                dx, dy = self.rng.choice(sorted(reducing))
        mass_ratio = organism.structural_mass(self.catalog) / max(self.reference_body_mass, 1.0)
        speed_fraction = min(1.0, organism.phenotype.speed / 4.0)
        cost = (
            self.config.reference_move_cost
            * self.reference_energy
            * mass_ratio
            * (1.0 + speed_fraction * speed_fraction)
            / organism.phenotype.move_efficiency
        )
        if organism.chemical_energy() < cost:
            return False
        destination = (organism.position[0] + dx, organism.position[1] + dy)
        if not self.world.can_place(organism, destination, {organism.organism_id}):
            spent = organism.consume_body_energy(cost * self.config.failed_move_cost_fraction)
            self.world.add_heat(organism.position, spent)
            return False
        spent = organism.consume_body_energy(cost)
        self.world.add_heat(organism.position, spent)
        self.world.remove_from_occupancy(organism)
        organism.position = destination
        organism.facing = (dx, dy)
        self.world.add_to_occupancy(organism)
        return True

    def _move_away(self, organism: Organism, threat: tuple[int, int]) -> bool:
        dx, dy = self.world.delta(organism.position, threat)
        away = (
            organism.position[0] - (0 if dx == 0 else (1 if dx > 0 else -1)),
            organism.position[1] - (0 if dy == 0 else (1 if dy > 0 else -1)),
        )
        return self._move(organism, away)

    def _seek_or_absorb_heat(self, organism: Organism, target: tuple[int, int]) -> None:
        if target in self.world.footprint(organism):
            self._absorb_heat(organism, target)
        else:
            self._move(organism, target)

    def _eat(self, organism: Organism, candidate: FoodCandidate) -> None:
        inventory = self.world.nonempty_inventory_at(candidate.position)
        if not inventory or candidate.molecule_id not in inventory:
            return
        source = inventory[candidate.molecule_id]
        count = min(2, source.count)
        cost = self.config.reference_ingest_cost * self.reference_energy * count
        if organism.chemical_energy() < cost:
            return
        spent = organism.consume_body_energy(cost)
        self.world.add_heat(organism.position, spent)
        eaten = source.take(count)
        if source.count == 0:
            del inventory[candidate.molecule_id]
        if not inventory:
            self.world.remove_deposit(candidate.position)
        add_batch(organism.gut, eaten)

    def _absorb_heat(self, organism: Organism, target: tuple[int, int]) -> None:
        capacity = organism.phenotype.mana_capacity - organism.mana
        if capacity <= 0.0:
            return
        available = self.world.heat_at(target)
        gain_target = min(
            capacity,
            organism.phenotype.heat_absorption * self.reference_energy,
            available * organism.phenotype.mana_efficiency,
        )
        removed = self.world.remove_heat((target,), gain_target)
        organism.mana += removed

    def _active_detox(self, organism: Organism) -> None:
        cost = min(organism.chemical_energy(), self.reference_energy * 0.01)
        spent = organism.consume_body_energy(cost)
        self.world.add_heat(organism.position, spent)
        organism.toxin_load = max(0.0, organism.toxin_load - 3.0 * spent / max(self.reference_energy, 1e-9))

    def _attack(self, attacker: Organism, target: Organism) -> None:
        if not target.alive:
            return
        mass_ratio = attacker.structural_mass(self.catalog) / max(self.reference_body_mass, 1.0)
        cost = (
            self.config.reference_attack_cost
            * self.reference_energy
            * mass_ratio
            * attacker.phenotype.attack**2
            / attacker.phenotype.attack_efficiency
        )
        if attacker.chemical_energy() < cost:
            return
        spent = attacker.consume_body_energy(cost)
        self.world.add_heat(attacker.position, spent)
        shield = 0.5 if "earth" in target.statuses else 1.0
        damage = (
            self.config.attack_damage_multiplier
            * attacker.phenotype.attack
            * (0.5 + mass_ratio)
            * shield
        )
        target.integrity -= damage
        self.stats.attacks += 1
        if target.integrity <= 0.0:
            attacker.kills += 1
            self._kill(target, "predation")

    def _cast_magic(self, caster: Organism, target: Organism) -> None:
        if not target.alive or caster.mana <= 0.0:
            return
        channel = max(range(4), key=lambda axis: caster.phenotype.magic_affinity[axis])
        committed = min(caster.mana * 0.30, self.reference_energy * 0.5)
        caster.mana -= committed
        raw = committed * caster.phenotype.magic_affinity[channel]
        effective = raw * (1.0 - target.phenotype.magic_resistance[channel])
        immediate_heat = committed - effective
        self.world.add_heat(target.position, immediate_heat)
        self.stats.magic_casts += 1
        if channel == 0:  # fire
            target.integrity -= effective / max(self.reference_energy, 1e-9) * 4.0
            self.world.add_heat(target.position, effective)
            if target.integrity <= 0.0:
                self._kill(target, "fire")
        elif channel in (1, 2):  # water slow, earth ward
            effect_id = self._next_effect_id
            self._next_effect_id += 1
            name = "water" if channel == 1 else "earth"
            duration = max(2, round(4 + effective / max(self.reference_energy, 1e-9) * 10))
            self.effects[effect_id] = MagicEffect(effect_id, channel, caster.organism_id, target.organism_id, effective, self.tick + duration)
            target.statuses[name] = (self.tick + duration, float(effect_id))
        else:  # air
            dx, dy = self.world.delta(caster.position, target.position)
            push = (0 if dx == 0 else (1 if dx > 0 else -1), 0 if dy == 0 else (1 if dy > 0 else -1))
            destination = (target.position[0] + push[0], target.position[1] + push[1])
            if self.world.can_place(target, destination, {target.organism_id}):
                self.world.remove_from_occupancy(target)
                target.position = destination
                self.world.add_to_occupancy(target)
            self.world.add_heat(target.position, effective)

    def _repair(self, organism: Organism) -> None:
        cost = min(organism.chemical_energy(), self.reference_energy * 0.005)
        if cost <= 0.0:
            return
        spent = organism.consume_body_energy(cost)
        self.world.add_heat(organism.position, spent)
        organism.integrity = min(organism.max_integrity, organism.integrity + spent / self.reference_energy)

    # ------------------------------------------------------------- reproduction

    def _attempt_reproduction(self, parent: Organism, mate: Organism | None) -> None:
        self.stats.reproduction_attempts += 1
        parents = (parent,) if mate is None else (parent, mate)
        if mate is not None and (not mate.alive or not self._is_reproductively_ready(mate)):
            self.stats.reproduction_resource_blocks += 1
            self.stats.reproduction_mate_readiness_blocks += 1
            return
        count = 1 if mate is None else max(1, round((parent.phenotype.offspring_count + mate.phenotype.offspring_count) / 2))
        planned_mass = sum(p.structural_mass(self.catalog) * p.phenotype.reproduction_fraction for p in parents)
        total_cost = (
            self.config.reference_reproduction_cost
            * self.config.reproduction_cost_multiplier
            * self.reference_energy
            * planned_mass
            / max(self.reference_body_mass, 1.0)
        )
        shares = [total_cost / len(parents)] * len(parents)
        if any(p.chemical_energy() < share for p, share in zip(parents, shares)):
            self.stats.reproduction_resource_blocks += 1
            self.stats.reproduction_energy_blocks += 1
            return
        for participant, share in zip(parents, shares):
            spent = participant.consume_body_energy(share)
            self.world.add_heat(participant.position, spent)
            participant.reproduction_cooldown = self.tick + self._reproduction_cooldown_ticks(
                participant, asexual=mate is None
            )

        if mate is None:
            success_probability = max(
                self.config.asexual_probability_floor,
                parent.phenotype.fertility * parent.phenotype.asexual,
            )
            success = self.rng.random() < min(1.0, success_probability)
        else:
            success = self.rng.random() < self._sexual_success_probability(parent, mate)
        if not success:
            self.stats.failed_reproductions += 1
            self.stats.reproduction_probability_failures += 1
            return

        created = 0
        for _ in range(count):
            genome = Genome.offspring(
                self._claim_genome_id(), tuple(p.genome for p in parents), self.rng, self.config.mutation_multiplier
            )
            phenotype = Phenotype.sample(genome, self.rng, self.config)
            child_body = self._preview_reproductive_body(parents, phenotype)
            if not child_body:
                self.stats.failed_reproductions += 1
                self.stats.reproduction_resource_blocks += 1
                self.stats.reproduction_body_matter_blocks += 1
                self._record_matter_block(parents)
                break
            child_id = self._claim_organism_id()
            child = Organism(
                organism_id=child_id,
                lineage_id=parent.lineage_id if mate is None else child_id,
                genome=genome,
                phenotype=phenotype,
                species_id=-1,
                parent_ids=tuple(p.organism_id for p in parents),
                generation=max(p.generation for p in parents) + 1,
                birth_tick=self.tick,
                position=parent.position,
                body=child_body,
                target_mass=max(1.0, self.catalog.inventory_mass(child_body) * 3.0),
            )
            child.max_integrity = max(2.0, 4.0 + phenotype.adult_area * phenotype.density * 2.0)
            child.integrity = child.max_integrity
            placement = self._find_child_position(child, parents)
            if placement is None:
                self.stats.failed_reproductions += 1
                self.stats.reproduction_placement_failures += 1
                break
            child.body = self._extract_reproductive_body(parents, phenotype)
            child.invalidate_body_cache()
            if not child.body:
                self.stats.failed_reproductions += 1
                self.stats.reproduction_resource_blocks += 1
                self.stats.reproduction_body_matter_blocks += 1
                self._record_matter_block(parents)
                break
            child.position = placement
            child.species_id = self._assign_species(
                genome,
                origin="mutation" if mate is None else "sexual",
                parent_species_ids=tuple(sorted({participant.species_id for participant in parents})),
                founder_organism_id=child.organism_id,
            )
            self.organisms[child.organism_id] = child
            self.living_ids[child.organism_id] = None
            self._refresh_dirty_occupancy()
            self.world.add_to_occupancy(child)
            for participant in parents:
                participant.offspring_count += 1
            self.stats.births += 1
            self.stats.successful_reproductions += 1
            self.species[child.species_id].births += 1
            created += 1
        if created > 0:
            self._record_reproduction_event(parents)

    def _record_matter_block(self, parents: tuple[Organism, ...]) -> None:
        """Attribute a body-matter block to the molecule that limited the split.

        Phase-1 bio-sim findings showed scarcity is resource-specific and
        structured, not uniform; recording the limiting molecule lets analysis
        identify which nutrient actually constrains reproduction.
        """

        fraction = min(p.phenotype.reproduction_fraction for p in parents) / max(1, len(parents))
        limiting: tuple[int, int] | None = None  # (count, molecule_id)
        for parent in parents:
            for molecule_id, batch in parent.body.items():
                if batch.count * fraction < 1.0 and (
                    limiting is None or (batch.count, molecule_id) > limiting
                ):
                    limiting = (batch.count, molecule_id)
        if limiting is not None:
            counts = self.stats.reproduction_matter_blocks_by_molecule
            counts[limiting[1]] = counts.get(limiting[1], 0) + 1

    def _record_reproduction_event(self, parents: tuple[Organism, ...]) -> None:
        if len(parents) > 1:
            self.stats.sexual_reproduction_events += 1
            self.sexual_parent_ids.update(parent.organism_id for parent in parents)
        else:
            self.stats.asexual_reproduction_events += 1

    @property
    def living_sexual_parent_count(self) -> int:
        return sum(organism_id in self.living_ids for organism_id in self.sexual_parent_ids)

    def _sexual_success_probability(self, parent: Organism, mate: Organism) -> float:
        distance = self._genome_distance(parent.genome, mate.genome)
        fertility = sqrt(parent.phenotype.fertility * mate.phenotype.fertility)
        sexual_propensity = sqrt(parent.phenotype.sexual * mate.phenotype.sexual)
        probability = fertility * sexual_propensity * exp(-4.0 * distance)
        if self.config.sexual_probability_floor_enabled:
            probability = max(self.config.sexual_probability_floor, probability)
        return min(1.0, probability)

    def _effective_maturity_age(self, organism: Organism) -> int:
        multiplier = self.config.maturity_age_multiplier
        if organism._maturity_multiplier != multiplier:
            organism._maturity_multiplier = multiplier
            organism._cached_maturity_age = max(
                1,
                round(organism.phenotype.maturity_age * multiplier),
            )
        return organism._cached_maturity_age

    def _is_reproductively_ready(self, organism: Organism) -> bool:
        return (
            organism.alive
            and self.tick - organism.birth_tick >= self._effective_maturity_age(organism)
            and self.tick >= organism.reproduction_cooldown
        )

    def _reproduction_cooldown_ticks(self, organism: Organism, *, asexual: bool) -> int:
        base_cooldown = max(10, round(organism.phenotype.maturity_age / 5))
        adjusted = max(3, round(base_cooldown * self.config.reproduction_cooldown_multiplier))
        if not asexual:
            return adjusted
        return max(3, round(adjusted / organism.phenotype.asexual_rate))

    def _preview_reproductive_body(self, parents: tuple[Organism, ...], phenotype: Phenotype) -> Inventory:
        preview: Inventory = {}
        fraction = min(p.phenotype.reproduction_fraction for p in parents) / max(1, len(parents))
        for parent in parents:
            for molecule_id, batch in parent.body.items():
                count = int(batch.count * fraction)
                if count > 0:
                    energy = batch.energy * count / batch.count
                    add_batch(preview, MoleculeBatch(molecule_id, count, energy))
        if not preview:
            richest = max(
                ((batch.count, molecule_id, batch) for parent in parents for molecule_id, batch in parent.body.items()),
                key=lambda item: (item[0], item[1]),
                default=None,
            )
            if richest and richest[0] > 1:
                add_batch(preview, MoleculeBatch(richest[1], 1, richest[2].energy / richest[2].count))
        return preview

    def _extract_reproductive_body(self, parents: tuple[Organism, ...], phenotype: Phenotype) -> Inventory:
        child: Inventory = {}
        for parent in parents:
            self._mark_occupancy_dirty(parent)
        fraction = min(p.phenotype.reproduction_fraction for p in parents) / max(1, len(parents))
        for parent in parents:
            for molecule_id in tuple(sorted(parent.body)):
                source = parent.body[molecule_id]
                count = int(source.count * fraction)
                if count > 0 and source.count - count >= 1:
                    add_batch(child, source.take(count))
                if source.count == 0:
                    del parent.body[molecule_id]
        if not child:
            richest_parent = max(parents, key=lambda p: sum(batch.count for batch in p.body.values()))
            richest_id = max(richest_parent.body, key=lambda mid: richest_parent.body[mid].count, default=None)
            if richest_id is not None and richest_parent.body[richest_id].count > 1:
                add_batch(child, richest_parent.body[richest_id].take(1))
        for parent in parents:
            parent.invalidate_body_cache()
        return child

    def _find_child_position(self, child: Organism, parents: tuple[Organism, ...]) -> tuple[int, int] | None:
        origin = parents[0].position
        candidates = [
            (origin[0] + dx, origin[1] + dy)
            for radius in range(1, 5)
            for dy in range(-radius, radius + 1)
            for dx in range(-radius, radius + 1)
            if max(abs(dx), abs(dy)) == radius
        ]
        for position in candidates:
            if self.world.can_place(child, position):
                return position
        return None

    # ---------------------------------------------------------- social/species

    def _attempt_alliance(self, organism: Organism, other: Organism) -> None:
        edge = frozenset((organism.organism_id, other.organism_id))
        if edge in self.alliances:
            return
        complement = 1.0 - signature_similarity(organism.phenotype.diet_signature, other.phenotype.diet_signature)
        probability = self.config.alliance_probability + 0.25 * organism.phenotype.social * other.phenotype.social * complement
        if self.rng.random() >= probability:
            return
        self.alliances.add(edge)
        left_id, right_id = sorted(edge)
        self.alliance_events.append((self.tick, left_id, right_id))
        self.stats.alliances += 1
        if (
            organism.phenotype.sexual <= self.config.sexual_colony_max
            and other.phenotype.sexual <= self.config.sexual_colony_max
            and organism.phenotype.asexual >= self.config.asexual_colony_min
            and other.phenotype.asexual >= self.config.asexual_colony_min
            and organism.colony_id is None
            and other.colony_id is None
        ):
            colony_id = self._next_colony_id
            self._next_colony_id += 1
            bonus = min(self.config.colony_bonus_cap, 0.05 + complement * 0.10)
            self.colonies[colony_id] = Colony(colony_id, {organism.organism_id, other.organism_id}, bonus, self.tick)
            self.colony_events.append((self.tick, colony_id))
            organism.colony_id = colony_id
            other.colony_id = colony_id
            self.stats.colonies += 1

    def _assign_species(
        self,
        genome: Genome,
        *,
        origin: str = "mutation",
        parent_species_ids: tuple[int, ...] = (),
        founder_organism_id: int | None = None,
    ) -> int:
        if self.species:
            closest = min(
                self.species.values(),
                key=lambda species: self._genome_distance(genome, species.representative_genome),
            )
            if self._genome_distance(genome, closest.representative_genome) <= self.config.species_distance_threshold:
                closest.population += 1
                return closest.species_id
        return self._create_species(
            genome,
            origin=origin,
            parent_species_ids=parent_species_ids,
            founder_organism_id=founder_organism_id,
        )

    def _create_species(
        self,
        genome: Genome,
        *,
        origin: str,
        parent_species_ids: tuple[int, ...] = (),
        founder_organism_id: int | None = None,
    ) -> int:
        if origin not in {"founder", "mutation", "sexual"}:
            raise ValueError(f"unsupported species origin: {origin}")
        species_id = self._next_species_id
        self._next_species_id += 1
        species = Species(
            species_id=species_id,
            representative_genome=genome,
            color=species_color(species_id, genome),
            created_tick=self.tick,
            origin=origin,
            parent_species_ids=parent_species_ids,
            founder_organism_id=founder_organism_id,
            population=1,
        )
        self.species[species_id] = species
        return species_id

    # -------------------------------------------------------------- lifecycle

    def _mark_occupancy_dirty(self, organism: Organism) -> None:
        self._occupancy_dirty.setdefault(organism.organism_id, self.world.footprint(organism))

    def _refresh_dirty_occupancy(self) -> None:
        for organism_id, old_positions in self._occupancy_dirty.items():
            self.world.remove_id_from_occupancy(organism_id, old_positions)
            if organism_id in self.living_ids:
                self.world.add_to_occupancy(self.organisms[organism_id])
        self._occupancy_dirty.clear()

    def _kill(self, organism: Organism, cause: str) -> None:
        if not organism.alive:
            return
        self._mark_occupancy_dirty(organism)
        self.living_ids.pop(organism.organism_id, None)
        organism.alive = False
        organism.last_action = f"dead:{cause}"
        self.world.add_heat(organism.position, organism.mana)
        organism.mana = 0.0
        corpse_inventory: Inventory = {}
        for inventory in organism.inventories():
            for molecule_id in tuple(inventory):
                add_batch(corpse_inventory, inventory.pop(molecule_id))
        organism.invalidate_body_cache()
        for batch in corpse_inventory.values():
            self.world.deposit_batch(organism.position, batch)
        corpse_id = self._next_corpse_id
        self._next_corpse_id += 1
        self.corpses[corpse_id] = Corpse(corpse_id, organism.organism_id, organism.position, {}, self.tick)
        species = self.species.get(organism.species_id)
        if species:
            species.population = max(0, species.population - 1)
            species.deaths += 1
        if organism.colony_id is not None and organism.colony_id in self.colonies:
            colony = self.colonies[organism.colony_id]
            colony.members.discard(organism.organism_id)
            if len(colony.members) < 2:
                for member_id in colony.members:
                    if member_id in self.organisms:
                        self.organisms[member_id].colony_id = None
                del self.colonies[colony.colony_id]
        self.stats.deaths += 1
        self.death_events.append((self.tick, organism.organism_id))

    def _resolve_effects(self) -> None:
        for effect_id, effect in tuple(self.effects.items()):
            if self.tick < effect.expires_tick:
                continue
            target = self.organisms.get(effect.target_id)
            source = self.organisms.get(effect.source_id)
            position = target.position if target else (source.position if source else (0, 0))
            self.world.add_heat(position, effect.energy)
            if target:
                name = "water" if effect.channel == 1 else "earth"
                target.statuses.pop(name, None)
            del self.effects[effect_id]

    def _expire_corpses(self) -> None:
        for corpse_id, corpse in tuple(self.corpses.items()):
            if self.tick - corpse.created_tick > 200:
                del self.corpses[corpse_id]

    def _touching(self, left: Organism, right: Organism) -> bool:
        right_tiles = set(self.world.footprint(right))
        for x, y in self.world.footprint(left):
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if (x + dx, y + dy) in right_tiles:
                        return True
        return False

    # --------------------------------------------------------------- auditing

    def all_inventories(self) -> Iterable[Inventory]:
        yield from self.world.deposits.values()
        for organism_id in self.living_ids:
            yield from self.organisms[organism_id].inventories()
        for corpse in self.corpses.values():
            yield corpse.inventory

    def current_element_totals(self) -> tuple[int, ...]:
        return self.catalog.element_totals(self.all_inventories())

    def _dynamic_element_totals(self) -> tuple[int, ...]:
        """Element totals excluding geological generation so far."""

        return tuple(
            current - generated
            for current, generated in zip(self.current_element_totals(), self.world.generated_elements)
        )

    def total_energy(self) -> float:
        chemical = sum(inventory_energy(inventory) for inventory in self.all_inventories())
        mana = sum(self.organisms[organism_id].mana for organism_id in self.living_ids)
        effects = sum(effect.energy for effect in self.effects.values())
        return chemical + mana + effects + self.world.total_heat()

    def audit(self, *, raise_on_error: bool = True) -> float:
        current_elements = self.current_element_totals()
        expected_elements = tuple(
            initial + generated
            for initial, generated in zip(self.initial_elements, self.world.generated_elements)
        )
        if current_elements != expected_elements and raise_on_error:
            raise AssertionError(f"matter conservation failed: {current_elements} != {expected_elements}")
        for inventory in self.all_inventories():
            for batch in inventory.values():
                self.catalog.validate_batch(batch)
        dynamic_energy = self.total_energy() - self.world.generated_energy
        error = dynamic_energy - self.initial_energy
        self.last_audit_error = error
        self.stats.audit_error = error
        tolerance = max(1e-7, abs(self.initial_energy) * 1e-10)
        if raise_on_error and abs(error) > tolerance:
            raise AssertionError(f"energy conservation failed by {error:.12g} (tolerance {tolerance:.12g})")
        return error

    @property
    def population(self) -> int:
        return len(self.living_ids)

    def snapshot(self) -> tuple[object, ...]:
        living = tuple(
            (
                oid,
                organism.position,
                organism.species_id,
                round(organism.chemical_energy(), 8),
                round(organism.mana, 8),
                round(organism.integrity, 8),
            )
            for oid in sorted(self.living_ids)
            for organism in (self.organisms[oid],)
        )
        return self.tick, living, self.current_element_totals(), round(self.total_energy(), 8)
