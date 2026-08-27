from __future__ import annotations

from collections.abc import Iterable
from colorsys import hsv_to_rgb
from dataclasses import dataclass
from math import exp, log
from random import Random

from .chemistry import Signature, _simplex
from .config import SimulationConfig


@dataclass(frozen=True, slots=True)
class TraitGene:
    center: float
    spread: float
    minimum: float
    maximum: float
    logarithmic: bool = False

    def sample(self, rng: Random) -> float:
        if self.logarithmic:
            lower = log(max(1e-12, self.minimum))
            upper = log(max(self.minimum, self.maximum))
            center = log(max(self.minimum, self.center))
            sampled = min(upper, max(lower, rng.gauss(center, self.spread)))
            value = exp(sampled)
        else:
            value = rng.gauss(self.center, self.spread)
        return min(self.maximum, max(self.minimum, value))

    def mutated(self, rng: Random, rate: float, magnitude: float) -> TraitGene:
        if rng.random() >= rate:
            return self
        span = self.maximum - self.minimum
        if self.logarithmic:
            center = min(
                self.maximum,
                max(self.minimum, self.center * exp(rng.gauss(0.0, magnitude))),
            )
        else:
            center = min(self.maximum, max(self.minimum, self.center + rng.gauss(0.0, span * magnitude)))
        spread_limit = 1.0 if self.logarithmic else span * 0.5
        spread = min(spread_limit, max(0.0, self.spread * exp(rng.gauss(0.0, magnitude))))
        return TraitGene(center, spread, self.minimum, self.maximum, self.logarithmic)

    @classmethod
    def blend(cls, genes: Iterable[TraitGene], rng: Random) -> TraitGene:
        items = tuple(genes)
        chosen = rng.choice(items)
        if rng.random() < 0.55:
            return chosen
        if chosen.logarithmic:
            transformed = [log(max(chosen.minimum, gene.center)) for gene in items]
            transformed_center = sum(transformed) / len(transformed)
            center = exp(transformed_center)
            disagreement = sum((value - transformed_center) ** 2 for value in transformed) / len(items)
            spread = min(1.0, (sum(g.spread**2 for g in items) / len(items) + disagreement) ** 0.5)
        else:
            center = sum(g.center for g in items) / len(items)
            disagreement = sum((g.center - center) ** 2 for g in items) / len(items)
            spread = (sum(g.spread**2 for g in items) / len(items) + disagreement) ** 0.5
        return TraitGene(center, spread, chosen.minimum, chosen.maximum, chosen.logarithmic)


TRAIT_RANGES: dict[str, tuple[float, float]] = {
    "adult_area": (1.0, 14.0),
    "density": (0.5, 2.0),
    "basal": (0.006, 0.080),
    "move_efficiency": (0.25, 1.0),
    "speed": (0.5, 4.0),
    "sight": (1.0, 6.0),
    "digestion": (0.15, 0.98),
    "assimilation": (0.05, 0.75),
    "heat_absorption": (0.005, 0.20),
    "mana_efficiency": (0.20, 1.0),
    "mana_capacity": (0.5, 16.0),
    "mana_preference": (0.0, 1.0),
    "lifespan": (500.0, 5000.0),
    "maturity_fraction": (0.10, 0.45),
    "attack": (0.1, 1.2),
    "attack_efficiency": (0.25, 1.0),
    "toxin_tolerance": (0.2, 10.0),
    "asexual": (0.0, 1.0),
    "asexual_rate": (0.25, 4.0),
    "sexual": (0.0, 1.0),
    "fertility": (0.1, 0.95),
    "offspring": (1.0, 3.0),
    "reproduction_fraction": (0.08, 0.28),
    "mutation_rate": (0.005, 0.25),
    "mutation_magnitude": (0.005, 0.12),
    "risk": (0.0, 1.0),
    "social": (0.0, 1.0),
}

ACTIONS = (
    "rest",
    "wander",
    "forage",
    "hunt",
    "flee",
    "seek_mate",
    "eat",
    "heat",
    "detox",
    "attack",
    "magic",
    "reproduce",
    "ally",
)

FEATURES = (
    "hunger",
    "food",
    "heat",
    "threat",
    "prey",
    "toxin",
    "mana",
    "mate",
    "crowding",
    "energy_cost",
)

# --------------------------------------------------------------------- guilds
# Founder archetypes are drawn from ecological guilds. Each guild constrains a
# subset of trait ranges to a coherent body plan instead of independent
# uniform noise, so the first generation contains plausible specialists.

GUILDS = ("generalist", "grazer", "hunter", "scavenger", "thermophile")

GUILD_TRAIT_WINDOWS: dict[str, dict[str, tuple[float, float]]] = {
    "generalist": {
        "digestion": (0.45, 0.85),
        "assimilation": (0.3, 0.7),
    },
    "grazer": {
        "adult_area": (0.55, 1.0),
        "density": (0.4, 0.9),
        "basal": (0.3, 0.7),
        "move_efficiency": (0.3, 0.8),
        "speed": (0.0, 0.3),
        "sight": (0.0, 0.25),
        "digestion": (0.7, 1.0),
        "assimilation": (0.5, 1.0),
        "attack": (0.0, 0.2),
        "risk": (0.0, 0.2),
        "social": (0.4, 1.0),
        "asexual": (0.5, 1.0),
        "fertility": (0.5, 1.0),
        "offspring": (0.4, 1.0),
    },
    "hunter": {
        "adult_area": (0.25, 0.7),
        "basal": (0.5, 0.9),
        "move_efficiency": (0.6, 1.0),
        "speed": (0.6, 1.0),
        "sight": (0.6, 1.0),
        "digestion": (0.4, 0.8),
        "assimilation": (0.3, 0.7),
        "attack": (0.7, 1.0),
        "attack_efficiency": (0.6, 1.0),
        "risk": (0.5, 1.0),
        "sexual": (0.5, 1.0),
    },
    "scavenger": {
        "adult_area": (0.0, 0.3),
        "basal": (0.0, 0.3),
        "speed": (0.5, 1.0),
        "fertility": (0.6, 1.0),
        "offspring": (0.5, 1.0),
        "asexual_rate": (0.6, 1.0),
        "mutation_rate": (0.6, 1.0),
        "maturity_fraction": (0.0, 0.4),
        "lifespan": (0.0, 0.3),
    },
    "thermophile": {
        "adult_area": (0.3, 0.8),
        "speed": (0.0, 0.4),
        "heat_absorption": (0.7, 1.0),
        "mana_efficiency": (0.6, 1.0),
        "mana_capacity": (0.6, 1.0),
        "mana_preference": (0.6, 1.0),
    },
}

# Life-history traits move together along a shared r/K strategy axis (negative
# = fast-living many-offspring, positive = slow-living large-bodied), giving
# founders internally consistent trade-offs rather than trait soup.
STRATEGY_TRAITS: dict[str, float] = {
    "adult_area": 1.0,
    "lifespan": 1.0,
    "maturity_fraction": 0.5,
    "basal": 0.6,
    "offspring": -1.0,
    "fertility": -0.5,
}

GUILD_POLICY_PRIORS: dict[str, dict[str, dict[str, float]]] = {
    "generalist": {"forage": {"hunger": 1.0}},
    "grazer": {
        "forage": {"hunger": 1.4, "food": 0.9},
        "eat": {"food": 1.6},
        "heat": {"heat": 0.8},
        "rest": {"energy_cost": 0.5},
    },
    "hunter": {
        "hunt": {"prey": 1.4},
        "attack": {"prey": 0.9},
        "flee": {"threat": 1.2},
        "reproduce": {"mate": 0.4},
    },
    "scavenger": {
        "wander": {"hunger": 0.4},
        "forage": {"food": 1.2},
        "flee": {"threat": 1.3},
        "reproduce": {"mate": 1.0},
    },
    "thermophile": {
        "heat": {"heat": 1.6},
        "eat": {"food": 1.2},
        "rest": {"energy_cost": 0.7},
    },
}


@dataclass(frozen=True, slots=True)
class Genome:
    genome_id: int
    parent_genome_ids: tuple[int, ...]
    traits: dict[str, TraitGene]
    diet_signature: tuple[TraitGene, TraitGene, TraitGene, TraitGene]
    toxin_sensitivity: tuple[TraitGene, TraitGene, TraitGene, TraitGene]
    magic_affinity: tuple[TraitGene, TraitGene, TraitGene, TraitGene]
    magic_resistance: tuple[TraitGene, TraitGene, TraitGene, TraitGene]
    policy: dict[str, dict[str, TraitGene]]
    guild: str = "generalist"

    @classmethod
    def random(
        cls,
        genome_id: int,
        rng: Random,
        *,
        guild: str = "generalist",
        diet_anchor: Signature | None = None,
    ) -> Genome:
        if guild not in GUILDS:
            raise ValueError(f"unknown guild: {guild}")
        windows = GUILD_TRAIT_WINDOWS[guild]
        # Shared r/K strategy axis correlates life-history traits so that each
        # founder genome is one coherent body plan, not independent noise.
        strategy = rng.uniform(-1.0, 1.0)
        traits: dict[str, TraitGene] = {}
        for name, (minimum, maximum) in TRAIT_RANGES.items():
            lo_frac, hi_frac = windows.get(name, (0.0, 1.0))
            lo = minimum + (maximum - minimum) * lo_frac
            hi = minimum + (maximum - minimum) * hi_frac
            center = rng.uniform(lo, hi)
            strength = STRATEGY_TRAITS.get(name)
            if strength is not None:
                pole = maximum if strength > 0 else minimum
                center += 0.35 * strength * strategy * (pole - center)
                center = min(maximum, max(minimum, center))
            logarithmic = name in {"lifespan", "mana_capacity"}
            spread = rng.uniform(0.01, 0.15) if logarithmic else (maximum - minimum) * rng.uniform(0.01, 0.10)
            traits[name] = TraitGene(center, spread, minimum, maximum, logarithmic)

        if diet_anchor is None:
            diet_anchor = (0.25, 0.25, 0.25, 0.25) if guild == "generalist" else _simplex(
                rng.random() + 0.05 for _ in range(4)
            )
        diet_signature = tuple(  # type: ignore[assignment]
            TraitGene(
                min(1.0, max(0.0, diet_anchor[axis] + rng.uniform(-0.06, 0.06))),
                rng.uniform(0.01, 0.10),
                0.0,
                1.0,
            )
            for axis in range(4)
        )
        toxin_sensitivity = tuple(
            TraitGene(rng.random(), rng.uniform(0.01, 0.12), 0.0, 1.0) for _ in range(4)
        )
        # Magic follows a budget: affinity axes are normalized to sum to one,
        # and strong affinity in a channel trades off against resistance.
        affinity_weights = [rng.uniform(0.05, 1.0) for _ in range(4)]
        affinity_total = sum(affinity_weights)
        magic_affinity = tuple(
            TraitGene(weight / affinity_total, rng.uniform(0.01, 0.12), 0.0, 1.0)
            for weight in affinity_weights
        )
        magic_resistance = tuple(
            TraitGene(
                min(0.9, rng.uniform(0.05, 0.75) * (1.15 - weight / affinity_total)),
                rng.uniform(0.01, 0.12),
                0.0,
                1.0,
            )
            for weight in affinity_weights
        )
        policy = {
            action: {
                feature: TraitGene(rng.uniform(-1.2, 1.2), rng.uniform(0.01, 0.15), -3.0, 3.0)
                for feature in FEATURES
            }
            for action in ACTIONS
        }
        # A few weak priors make the first generation active without assigning roles.
        policy["eat"]["food"] = TraitGene(rng.uniform(0.8, 1.8), 0.08, -3.0, 3.0)
        policy["forage"]["hunger"] = TraitGene(rng.uniform(0.5, 1.5), 0.08, -3.0, 3.0)
        policy["hunt"]["prey"] = TraitGene(rng.uniform(0.5, 1.5), 0.08, -3.0, 3.0)
        policy["flee"]["threat"] = TraitGene(rng.uniform(0.7, 1.7), 0.08, -3.0, 3.0)
        policy["seek_mate"]["mate"] = TraitGene(rng.uniform(0.5, 1.5), 0.08, -3.0, 3.0)
        policy["heat"]["heat"] = TraitGene(rng.uniform(0.2, 1.4), 0.08, -3.0, 3.0)
        for action, priors in GUILD_POLICY_PRIORS[guild].items():
            for feature, center in priors.items():
                policy[action][feature] = TraitGene(center + rng.uniform(-0.1, 0.1), 0.08, -3.0, 3.0)
        return cls(
            genome_id=genome_id,
            parent_genome_ids=(),
            traits=traits,
            diet_signature=diet_signature,
            toxin_sensitivity=toxin_sensitivity,
            magic_affinity=magic_affinity,
            magic_resistance=magic_resistance,
            policy=policy,
            guild=guild,
        )

    @classmethod
    def offspring(
        cls,
        genome_id: int,
        parents: tuple[Genome, ...],
        rng: Random,
        mutation_multiplier: float,
    ) -> Genome:
        inherited_rate = sum(parent.traits["mutation_rate"].center for parent in parents) / len(parents)
        inherited_magnitude = sum(parent.traits["mutation_magnitude"].center for parent in parents) / len(parents)
        rate = min(0.8, inherited_rate * mutation_multiplier)
        magnitude = min(0.35, inherited_magnitude * mutation_multiplier)
        traits = {
            name: TraitGene.blend((parent.traits[name] for parent in parents), rng).mutated(rng, rate, magnitude)
            for name in TRAIT_RANGES
        }

        def blend_vector(name: str) -> tuple[TraitGene, TraitGene, TraitGene, TraitGene]:
            vectors = [getattr(parent, name) for parent in parents]
            return tuple(
                TraitGene.blend((vector[axis] for vector in vectors), rng).mutated(rng, rate, magnitude)
                for axis in range(4)
            )  # type: ignore[return-value]

        policy = {
            action: {
                feature: TraitGene.blend((parent.policy[action][feature] for parent in parents), rng).mutated(
                    rng, rate, magnitude
                )
                for feature in FEATURES
            }
            for action in ACTIONS
        }
        guilds = {parent.guild for parent in parents}
        guild = guilds.pop() if len(guilds) == 1 else "generalist"
        return cls(
            genome_id=genome_id,
            parent_genome_ids=tuple(parent.genome_id for parent in parents),
            traits=traits,
            diet_signature=blend_vector("diet_signature"),
            toxin_sensitivity=blend_vector("toxin_sensitivity"),
            magic_affinity=blend_vector("magic_affinity"),
            magic_resistance=blend_vector("magic_resistance"),
            policy=policy,
            guild=guild,
        )

    def distance(self, other: Genome) -> float:
        values: list[float] = []
        for name, gene in self.traits.items():
            other_gene = other.traits[name]
            span = gene.maximum - gene.minimum
            values.append(abs(gene.center - other_gene.center) / span)
        for field in ("diet_signature", "magic_affinity", "magic_resistance"):
            left = getattr(self, field)
            right = getattr(other, field)
            values.extend(abs(a.center - b.center) for a, b in zip(left, right))
        return sum(values) / len(values)


def species_color(species_id: int, genome: Genome) -> tuple[int, int, int]:
    """Visually distinct, stable colors: golden-angle hue spacing between
    species, rotated by diet signature so similar chemistries cluster in hue."""

    diet_hue = sum(axis * (0.15 + 0.2 * index) for index, axis in enumerate(gene.center for gene in genome.diet_signature))
    hue = (species_id * 0.61803398875 + diet_hue * 0.25) % 1.0
    attack_norm = min(1.0, max(0.0, genome.traits["attack"].center / 1.2))
    saturation = 0.5 + 0.3 * attack_norm
    red, green, blue = hsv_to_rgb(hue, saturation, 0.88)
    return (int(45 + red * 200), int(45 + green * 200), int(45 + blue * 200))


@dataclass(frozen=True, slots=True)
class Phenotype:
    adult_area: int
    density: float
    basal: float
    move_efficiency: float
    speed: float
    sight: int
    digestion: float
    assimilation: float
    heat_absorption: float
    mana_efficiency: float
    mana_capacity: float
    mana_preference: float
    lifespan: int
    maturity_age: int
    attack: float
    attack_efficiency: float
    toxin_tolerance: float
    asexual: float
    asexual_rate: float
    sexual: float
    fertility: float
    offspring_count: int
    reproduction_fraction: float
    risk: float
    social: float
    diet_signature: Signature
    toxin_sensitivity: Signature
    magic_affinity: Signature
    magic_resistance: Signature
    policy: dict[str, dict[str, float]]

    @classmethod
    def sample(cls, genome: Genome, rng: Random, config: SimulationConfig) -> Phenotype:
        sampled = {name: gene.sample(rng) for name, gene in genome.traits.items()}
        diet = _simplex(gene.sample(rng) + 0.01 for gene in genome.diet_signature)
        sensitivity = _simplex(gene.sample(rng) + 0.01 for gene in genome.toxin_sensitivity)
        affinity = _simplex(gene.sample(rng) + 0.01 for gene in genome.magic_affinity)
        resistance = tuple(min(0.95, gene.sample(rng)) for gene in genome.magic_resistance)
        policy = {
            action: {feature: gene.sample(rng) for feature, gene in weights.items()}
            for action, weights in genome.policy.items()
        }
        lifespan = max(1, round(sampled["lifespan"]))
        return cls(
            adult_area=max(1, round(sampled["adult_area"])),
            density=sampled["density"],
            basal=sampled["basal"],
            move_efficiency=sampled["move_efficiency"],
            speed=sampled["speed"],
            sight=min(config.max_sight, max(1, round(sampled["sight"]))),
            digestion=sampled["digestion"],
            assimilation=sampled["assimilation"],
            heat_absorption=sampled["heat_absorption"],
            mana_efficiency=sampled["mana_efficiency"],
            mana_capacity=sampled["mana_capacity"],
            mana_preference=sampled["mana_preference"],
            lifespan=lifespan,
            maturity_age=max(1, round(lifespan * sampled["maturity_fraction"])),
            attack=sampled["attack"],
            attack_efficiency=sampled["attack_efficiency"],
            toxin_tolerance=sampled["toxin_tolerance"],
            asexual=sampled["asexual"],
            asexual_rate=sampled["asexual_rate"],
            sexual=sampled["sexual"],
            fertility=sampled["fertility"],
            offspring_count=max(1, round(sampled["offspring"])),
            reproduction_fraction=sampled["reproduction_fraction"],
            risk=sampled["risk"],
            social=sampled["social"],
            diet_signature=diet,
            toxin_sensitivity=sensitivity,
            magic_affinity=affinity,
            magic_resistance=resistance,  # type: ignore[arg-type]
            policy=policy,
        )
