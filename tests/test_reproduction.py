from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from experiments.analyze_stage3r_reproduction_liveness import lineage_depth
from soup.config import Config, PairingMode
from soup.ledgers import SymbolPool
from soup.logging.invariants import check_stage2
from soup.reproduction import reproduce_tapes
from soup.simulation import Simulation
from soup.substrate.bff import BFFSubstrate
from soup.world import SpatialWorld


def test_lineage_depth_follows_transitive_single_parent_births() -> None:
    lineage = pd.DataFrame(
        {
            "tape_id": [0, 1, 2, 3],
            "progenitor_ids": [[], [0], [1], [2]],
        }
    )

    assert lineage_depth(lineage) == 3


def test_copy_birth_is_local_pool_funded_and_conserved() -> None:
    rng = np.random.default_rng(31)
    substrate = BFFSubstrate(tape_length=8)
    world = SpatialWorld.create(
        width=4,
        height=4,
        initial_tape_fill=0.5,
        substrate=substrate,
        rng=rng,
    )
    pool = SymbolPool.from_tapes(world.occupied_tapes(), 16.0)
    population_before = world.population_size
    pool_before = pool.total

    result = reproduce_tapes(
        world=world,
        pool=pool,
        rng=rng,
        tick=7,
        rate=1.0,
        placement_radius=1,
        max_births_per_tick=3,
    )

    assert len(result.births) == 3
    assert world.population_size == population_before + 3
    assert pool.total == pool_before - 3 * substrate.tape_length
    for birth in result.births:
        dx = min(abs(birth.parent_cell[0] - birth.child_cell[0]), world.width - abs(birth.parent_cell[0] - birth.child_cell[0]))
        dy = min(abs(birth.parent_cell[1] - birth.child_cell[1]), world.height - abs(birth.parent_cell[1] - birth.child_cell[1]))
        assert max(dx, dy) <= 1
        child_index = world.index(*birth.child_cell)
        assert np.array_equal(world.tapes[child_index], birth.tape)
    check_stage2(world, pool, substrate.tape_length)


def test_stage3r_scheduler_logs_parent_child_lineage(tmp_path: Path) -> None:
    config = Config()
    config.run.stage = 3
    config.run.n_ticks = 2
    config.run.epoch_length = 1
    config.substrate.tape_length = 8
    config.substrate.max_steps = 16
    config.world.width = 4
    config.world.height = 4
    config.world.interaction_radius = 1
    config.world.interactions_per_tick = 8
    config.world.pairing_mode = PairingMode.LOCAL_NEIGHBORHOOD.value
    config.world.reseed_rate = 0.0
    config.symbols.initial_tape_fill = 0.5
    config.reproduction.enabled = True
    config.reproduction.rate = 1.0
    config.reproduction.placement_radius = 1
    config.reproduction.max_births_per_tick = 2
    config.logging.flush_interval = 2
    config.logging.full_tape_snapshot_interval = 1

    run_dir = Simulation(config, run_dir=tmp_path / "stage3r").run()

    events = pd.read_parquet(run_dir / "events.parquet")
    births = events[events["event_type"] == "offspring_born"]
    lineage = pd.read_parquet(run_dir / "lineage.parquet")
    reproductive_rows = lineage[lineage["progenitor_ids"].map(len) == 1]
    assert len(births) > 0
    assert len(reproductive_rows) == len(births)
    assert set(reproductive_rows["tape_id"]) == set(births["tape_id"])


def test_stage2_forces_reproduction_off(tmp_path: Path) -> None:
    config = Config()
    config.run.stage = 2
    config.run.n_ticks = 1
    config.substrate.tape_length = 8
    config.substrate.max_steps = 16
    config.world.width = 3
    config.world.height = 3
    config.world.interaction_radius = 1
    config.world.interactions_per_tick = 4
    config.world.pairing_mode = PairingMode.LOCAL_NEIGHBORHOOD.value
    config.symbols.initial_tape_fill = 0.5
    config.reproduction.enabled = True
    config.reproduction.rate = 1.0
    config.logging.flush_interval = 1

    simulation = Simulation(config, run_dir=tmp_path / "stage2-no-birth")
    population_before = simulation.world.population_size
    simulation.run()

    assert not simulation.config.reproduction.enabled
    assert simulation.world.population_size == population_before


def test_copy_birth_pool_block_is_atomic() -> None:
    rng = np.random.default_rng(32)
    substrate = BFFSubstrate(tape_length=8)
    world = SpatialWorld.create(
        width=3,
        height=3,
        initial_tape_fill=0.5,
        substrate=substrate,
        rng=rng,
    )
    tape_counts = np.bincount(world.occupied_tapes().ravel(), minlength=256).astype(np.int64)
    pool = SymbolPool(
        counts=np.zeros(256, dtype=np.int64),
        conserved_totals=tape_counts,
    )
    occupied_before = world.occupied.copy()

    result = reproduce_tapes(
        world=world,
        pool=pool,
        rng=rng,
        tick=1,
        rate=1.0,
        placement_radius=1,
        max_births_per_tick=4,
    )

    assert result.births == ()
    assert result.blocked_pool > 0
    assert np.array_equal(world.occupied, occupied_before)
    check_stage2(world, pool, substrate.tape_length)
