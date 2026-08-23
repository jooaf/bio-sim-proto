from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from soup.config import Config, PairingMode
from soup.interactions import draw_ordered_pairs, mutate_joint
from soup.simulation import Simulation


def test_shuffled_disjoint_pairs_cover_population_once() -> None:
    rng = np.random.Generator(np.random.PCG64(42))
    pairs = list(
        draw_ordered_pairs(
            rng=rng,
            population_size=10,
            n_pairs=5,
            pairing_mode=PairingMode.SHUFFLED_DISJOINT,
        )
    )

    assert len(pairs) == 5
    assert sorted(index for pair in pairs for index in pair) == list(range(10))
    assert all(a_index != b_index for a_index, b_index in pairs)


def test_pair_draws_are_seed_deterministic() -> None:
    def draw(mode: PairingMode) -> list[tuple[int, int]]:
        return list(
            draw_ordered_pairs(
                rng=np.random.Generator(np.random.PCG64(123)),
                population_size=8,
                n_pairs=4,
                pairing_mode=mode,
            )
        )

    for mode in (PairingMode.WITH_REPLACEMENT, PairingMode.SHUFFLED_DISJOINT):
        assert draw(mode) == draw(mode)


def test_mutation_rate_one_replaces_every_byte() -> None:
    joint = np.arange(16, dtype=np.uint8)
    before = joint.copy()
    counts = mutate_joint(
        joint,
        rng=np.random.Generator(np.random.PCG64(7)),
        mutation_rate=1.0,
        tape_length=8,
    )

    assert counts == (8, 8, 16, 0)
    assert not np.array_equal(joint, before)


def test_disjoint_simulation_logs_each_tape_once_per_tick(tmp_path: Path) -> None:
    config = Config()
    config.run.n_ticks = 2
    config.substrate.tape_length = 8
    config.substrate.max_steps = 8
    config.world.population_size = 8
    config.world.interactions_per_tick = 4
    config.world.pairing_mode = PairingMode.SHUFFLED_DISJOINT.value
    run_dir = Simulation(config, run_dir=tmp_path / "run").run()

    interactions = pd.read_parquet(run_dir / "interactions.parquet")
    for _, tick_rows in interactions.groupby("tick"):
        tape_ids = [*tick_rows["a_id"], *tick_rows["b_id"]]
        assert sorted(tape_ids) == list(range(config.world.population_size))
