from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.analyze_phase2_parasite_control import snapshot_family_counts
from experiments.run_phase2_parasite_control import (
    DEFAULT_INSERTED_COUNT,
    PARASITE_CONTENT_HASH,
    PARASITE_SHA256,
    override_indices,
    parasite_tape,
)
from soup.config import Config
from soup.simulation import Simulation


def test_frozen_parasite_identity_and_family_counts() -> None:
    candidate = parasite_tape()
    near = candidate.copy()
    near[0] = np.uint8((int(near[0]) + 1) % 256)
    far = candidate.copy()
    far[:9] = (far[:9].astype(np.uint16) + 17).astype(np.uint8)
    snapshot = pd.DataFrame(
        {
            "tick": [0, 0, 0],
            "full_bytes": [candidate.tobytes(), near.tobytes(), far.tobytes()],
        }
    )

    counts = snapshot_family_counts(snapshot).iloc[0]

    assert len(candidate) == 64
    assert hashlib.sha256(candidate.tobytes()).hexdigest() == PARASITE_SHA256
    assert PARASITE_CONTENT_HASH == "81603f482497218f10250a43385710f6"
    assert int(counts["exact_count"]) == 1
    assert int(counts["near_count"]) == 2


def test_parasite_override_indices_are_occupied_and_manifested(tmp_path: Path) -> None:
    config = Config.load("experiments/configs/stage2_parasite_mechanics.toml")
    config.run.n_ticks = 1
    indices = override_indices(config, DEFAULT_INSERTED_COUNT)
    candidate = parasite_tape()
    simulation = Simulation(
        config,
        run_dir=tmp_path / "parasite",
        initial_tape_overrides={index: candidate for index in indices},
    )

    assert len(indices) == DEFAULT_INSERTED_COUNT
    assert all(bool(simulation.world.occupied[index]) for index in indices)
    assert all(np.array_equal(simulation.world.tapes[index], candidate) for index in indices)
    assert simulation.writer.initialization_metadata is not None
    assert simulation.writer.initialization_metadata["count"] == DEFAULT_INSERTED_COUNT
    simulation.run()


def test_parasite_development_configs_match_preregistration() -> None:
    mechanics = Config.load("experiments/configs/stage2_parasite_mechanics.toml")
    viability = Config.load("experiments/configs/stage2_parasite_viability.toml")

    assert mechanics.world.width == mechanics.world.height == 8
    assert mechanics.world.interaction_radius == 4
    assert mechanics.world.mutation_rate == 0.0
    assert mechanics.run.debug_invariants is True
    assert viability.world.width == viability.world.height == 16
    assert viability.world.interaction_radius == 8
    assert viability.run.n_ticks == 2_000
    assert viability.world.mutation_rate == 1 / 4_096
    assert viability.world.reseed_rate == viability.dissolution.spontaneous_rate == 1e-5
