"""Empirical composition-reaction organization diagnostics for Stage 3."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
from numpy.random import Generator


Species = tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CompositionReaction:
    reactants: tuple[Species, Species]
    products: tuple[Species, Species]

    @property
    def changed(self) -> bool:
        return sorted(self.reactants) != sorted(self.products)


@dataclass(frozen=True, slots=True)
class OrganizationCandidate:
    members: frozenset[Species]
    closed: bool
    self_maintaining: bool
    active_reactions: int
    minimum_net_production: int


class _UnionFind:
    def __init__(self, members: Iterable[Species]) -> None:
        self.parent = {member: member for member in members}

    def find(self, member: Species) -> Species:
        root = member
        while self.parent[root] != root:
            root = self.parent[root]
        while member != root:
            parent = self.parent[member]
            self.parent[member] = root
            member = parent
        return root

    def union(self, left: Species, right: Species) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def reaction_components(
    reactions: Sequence[CompositionReaction],
) -> list[frozenset[Species]]:
    """Return deterministic weak components induced by changed reactions."""

    changed = [reaction for reaction in reactions if reaction.changed]
    species = sorted(
        {
            member
            for reaction in changed
            for member in (*reaction.reactants, *reaction.products)
        }
    )
    union_find = _UnionFind(species)
    for reaction in changed:
        participants = (*reaction.reactants, *reaction.products)
        for member in participants[1:]:
            union_find.union(participants[0], member)
    grouped: dict[Species, set[Species]] = {}
    for member in species:
        grouped.setdefault(union_find.find(member), set()).add(member)
    return sorted(
        (frozenset(members) for members in grouped.values()),
        key=lambda members: (len(members), sorted(members)),
    )


def evaluate_candidate(
    members: frozenset[Species], reactions: Sequence[CompositionReaction]
) -> OrganizationCandidate:
    """Test empirical closure and observed count-weighted self-maintenance."""

    internal = [
        reaction
        for reaction in reactions
        if set(reaction.reactants).issubset(members) and reaction.changed
    ]
    closed = all(set(reaction.products).issubset(members) for reaction in internal)
    participation: set[Species] = set()
    net: Counter[Species] = Counter()
    for reaction in internal:
        participation.update((*reaction.reactants, *reaction.products))
        net.subtract(reaction.reactants)
        net.update(reaction.products)
    minimum = min((net[member] for member in members), default=0)
    self_maintaining = bool(
        internal
        and closed
        and participation == set(members)
        and minimum >= 0
    )
    return OrganizationCandidate(
        members=members,
        closed=closed,
        self_maintaining=self_maintaining,
        active_reactions=len(internal),
        minimum_net_production=minimum,
    )


def detect_organizations(
    reactions: Sequence[CompositionReaction],
) -> list[OrganizationCandidate]:
    """Evaluate every changed-reaction weak component as one empirical candidate."""

    return [
        evaluate_candidate(component, reactions)
        for component in reaction_components(reactions)
    ]


def permute_products(
    reactions: Sequence[CompositionReaction], rng: Generator
) -> list[CompositionReaction]:
    """Permute product species over fixed reaction/reactant slots."""

    if not reactions:
        return []
    products = [product for reaction in reactions for product in reaction.products]
    order = rng.permutation(len(products))
    shuffled = [products[int(index)] for index in order]
    return [
        CompositionReaction(
            reactants=reaction.reactants,
            products=(shuffled[2 * index], shuffled[2 * index + 1]),
        )
        for index, reaction in enumerate(reactions)
    ]


def recurrence_diagnostics(
    reactions: Sequence[CompositionReaction],
) -> dict[str, float | int]:
    """Measure species and changed-reaction identifiability without conclusions."""

    counts: Counter[Species] = Counter(
        member
        for reaction in reactions
        for member in (*reaction.reactants, *reaction.products)
    )
    observations = 4 * len(reactions)
    singletons = sum(count == 1 for count in counts.values())
    recurrent_observations = sum(count for count in counts.values() if count >= 2)
    return {
        "sampled_reactions": len(reactions),
        "changed_reactions": sum(reaction.changed for reaction in reactions),
        "species": len(counts),
        "unique_species_fraction": len(counts) / observations if observations else 0.0,
        "singleton_species_fraction": singletons / len(counts) if counts else 0.0,
        "recurrent_observation_fraction": (
            recurrent_observations / observations if observations else 0.0
        ),
    }
