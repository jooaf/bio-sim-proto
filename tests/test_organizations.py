from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.organizations import (
    CompositionReaction,
    detect_organizations,
    permute_products,
    recurrence_diagnostics,
)
from soup.config import Config, PairingMode
from soup.simulation import Simulation


A = (1, 0, 3)
B = (0, 1, 3)
C = (1, 1, 2)


def test_composition_reactions_are_deterministically_logged_as_events(
    tmp_path: Path,
) -> None:
    config = Config()
    config.run.stage = 3
    config.run.n_ticks = 1
    config.substrate.tape_length = 8
    config.substrate.max_steps = 16
    config.world.width = 3
    config.world.height = 3
    config.world.interaction_radius = 1
    config.world.interactions_per_tick = 4
    config.world.pairing_mode = PairingMode.LOCAL_NEIGHBORHOOD.value
    config.symbols.initial_tape_fill = 0.5
    config.logging.reaction_log_rate = 1.0
    config.logging.flush_interval = 1

    run_dir = Simulation(config, run_dir=tmp_path / "reaction-events").run()
    events = pd.read_parquet(run_dir / "events.parquet")
    reactions = events[events["event_type"] == "composition_reaction"]

    assert len(reactions) == 4
    for value in reactions["details_json"]:
        details = json.loads(str(value))
        for name in ("a_before", "b_before", "a_after", "b_after"):
            assert len(details[name]) == 11
            assert sum(details[name]) == 8


def test_balanced_active_component_is_empirically_self_maintaining() -> None:
    reactions = [
        CompositionReaction((A, A), (B, C)),
        CompositionReaction((B, C), (A, A)),
    ]

    candidates = detect_organizations(reactions)

    assert len(candidates) == 1
    assert candidates[0].members == frozenset((A, B, C))
    assert candidates[0].closed
    assert candidates[0].self_maintaining
    assert candidates[0].minimum_net_production == 0


def test_unbalanced_component_is_not_self_maintaining() -> None:
    candidates = detect_organizations(
        [CompositionReaction((A, A), (B, B))]
    )

    assert len(candidates) == 1
    assert candidates[0].closed
    assert not candidates[0].self_maintaining
    assert candidates[0].minimum_net_production == -2


def test_recurrence_and_product_permutation_preserve_product_abundance() -> None:
    reactions = [
        CompositionReaction((A, B), (B, C)),
        CompositionReaction((A, C), (A, B)),
    ]

    diagnostics = recurrence_diagnostics(reactions)
    shuffled = permute_products(reactions, np.random.default_rng(7))

    assert diagnostics["sampled_reactions"] == 2
    assert diagnostics["species"] == 3
    assert diagnostics["singleton_species_fraction"] == 0.0
    assert sorted(product for reaction in shuffled for product in reaction.products) == sorted(
        product for reaction in reactions for product in reaction.products
    )
    assert [reaction.reactants for reaction in shuffled] == [
        reaction.reactants for reaction in reactions
    ]
