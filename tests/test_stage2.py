from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.report import parquet_digest, write_stage2_report
from soup.config import Config, PairingMode
from soup.interactions import run_local_interaction_round
from soup.ledgers import SymbolPool
from soup.logging.invariants import check_stage2
from soup.logging.writer import RunWriter
from soup.placement import place_random_tapes
from soup.simulation import Simulation
from soup.substrate.base import ExecutionBudget
from soup.substrate.bff import BFFSubstrate
from soup.world import SpatialWorld


def _stage2_config() -> Config:
    config = Config()
    config.run.stage = 2
    config.run.n_ticks = 5
    config.substrate.tape_length = 8
    config.substrate.max_steps = 16
    config.world.width = 4
    config.world.height = 4
    config.world.interaction_radius = 1
    config.world.interactions_per_tick = 8
    config.world.pairing_mode = PairingMode.LOCAL_NEIGHBORHOOD.value
    config.symbols.initial_tape_fill = 0.75
    config.logging.flush_interval = 5
    config.logging.tape_snapshot_interval = 1
    config.logging.full_tape_snapshot_interval = 1
    return config


def test_local_pairs_respect_toroidal_radius() -> None:
    rng = np.random.Generator(np.random.PCG64(12))
    substrate = BFFSubstrate(tape_length=8)
    world = SpatialWorld.create(
        width=4,
        height=4,
        initial_tape_fill=1.0,
        substrate=substrate,
        rng=rng,
    )
    pool = SymbolPool.from_tapes(world.occupied_tapes(), 2.0)
    facts = run_local_interaction_round(
        world=world,
        substrate=substrate,
        rng=rng,
        budget=ExecutionBudget(max_steps=16),
        tick=0,
        interactions_per_tick=40,
        interaction_radius=1,
        mutation_rate=0.0,
        pool=pool,
        hash_tape=lambda tape: tape.tobytes().hex(),
    )

    assert len(facts) == 40
    for fact in facts:
        assert fact.a_cell is not None and fact.b_cell is not None
        ax, ay = fact.a_cell
        bx, by = fact.b_cell
        dx = min(abs(ax - bx), world.width - abs(ax - bx))
        dy = min(abs(ay - by), world.height - abs(ay - by))
        assert max(dx, dy) <= 1
        assert (ax, ay) != (bx, by)


def test_pool_funded_placement_is_atomic() -> None:
    rng = np.random.Generator(np.random.PCG64(4))
    substrate = BFFSubstrate(tape_length=8)
    world = SpatialWorld.create(
        width=2,
        height=2,
        initial_tape_fill=0.5,
        substrate=substrate,
        rng=rng,
    )
    counts = np.full(256, 100, dtype=np.int64)
    tape_counts = np.bincount(world.occupied_tapes().ravel(), minlength=256).astype(np.int64)
    pool = SymbolPool(counts=counts.copy(), conserved_totals=counts + tape_counts)
    before_total = pool.total

    result = place_random_tapes(
        world=world,
        substrate=substrate,
        pool=pool,
        rng=rng,
        tick=3,
        reseed_rate=1.0,
    )

    assert len(result.placements) == 2
    assert result.blocked == 0
    assert world.population_size == world.capacity
    assert pool.total == before_total - 2 * substrate.tape_length
    check_stage2(world, pool, substrate.tape_length)

    unavailable = np.zeros(256, dtype=np.int64)
    blocked_pool = SymbolPool(
        counts=unavailable.copy(),
        conserved_totals=np.bincount(world.occupied_tapes().ravel(), minlength=256).astype(np.int64),
    )
    snapshot = blocked_pool.counts.copy()
    assert not blocked_pool.withdraw_tape(np.arange(8, dtype=np.uint8))
    assert np.array_equal(blocked_pool.counts, snapshot)


def test_stage2_ignores_starvation_until_energy_exists(tmp_path: Path) -> None:
    config = _stage2_config()
    config.run.n_ticks = 2
    config.world.reseed_rate = 0.0
    config.dissolution.enabled = True
    config.dissolution.inert_ticks = 10_000
    config.dissolution.starved_ticks = 1
    simulation = Simulation(config, run_dir=tmp_path / "no-starvation")
    initial_population = simulation.world.population_size

    run_dir = simulation.run()

    assert simulation.world.population_size == initial_population
    ticks = pd.read_parquet(run_dir / "ticks.parquet")
    assert int(ticks["n_dissolutions"].sum()) == 0


def test_stage2_dissolution_returns_all_matter(tmp_path: Path) -> None:
    config = _stage2_config()
    config.run.n_ticks = 1
    config.world.reseed_rate = 0.0
    config.dissolution.enabled = True
    config.dissolution.inert_ticks = 10_000
    config.dissolution.starved_ticks = 1
    config.dissolution.max_age = 1
    simulation = Simulation(config, run_dir=tmp_path / "dissolve")
    initial_tape_matter = simulation.world.population_size * config.substrate.tape_length
    initial_pool_total = simulation.pool.total if simulation.pool is not None else 0

    run_dir = simulation.run()

    assert simulation.pool is not None
    assert isinstance(simulation.world, SpatialWorld)
    assert simulation.world.population_size == 0
    assert simulation.pool.total == initial_pool_total + initial_tape_matter
    check_stage2(simulation.world, simulation.pool, config.substrate.tape_length)
    ticks = pd.read_parquet(run_dir / "ticks.parquet")
    assert int(ticks.iloc[-1]["n_dissolutions"]) > 0
    events = pd.read_parquet(run_dir / "events.parquet")
    assert set(events["event_type"]) == {"tape_dissolved"}


def test_initial_tape_overrides_precede_pool_and_lineage_initialization(tmp_path: Path) -> None:
    config = _stage2_config()
    config.run.n_ticks = 1
    config.symbols.initial_tape_fill = 1.0
    candidate = np.arange(config.substrate.tape_length, dtype=np.uint8)
    simulation = Simulation(
        config,
        run_dir=tmp_path / "seeded",
        initial_tape_overrides={0: candidate},
    )
    seeded_tape_id = int(simulation.world.tape_ids[0])

    assert np.array_equal(simulation.world.tapes[0], candidate)
    run_dir = simulation.run()

    lineage = pd.read_parquet(run_dir / "lineage.parquet")
    birth = lineage[
        (lineage["tape_id"] == seeded_tape_id) & lineage["died_tick"].isna()
    ].iloc[0]
    assert birth["content_hash_at_birth"] == RunWriter.hash_tape(candidate)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["initialization"]["mode"] == "explicit_tape_overrides"
    assert manifest["initialization"]["count"] == 1
    assert manifest["initialization"]["overrides"][0]["flat_index"] == 0


def test_stage2_short_runs_are_byte_deterministic(tmp_path: Path) -> None:
    config = _stage2_config()
    first = Simulation(config, run_dir=tmp_path / "first").run()
    second = Simulation(config, run_dir=tmp_path / "second").run()

    assert parquet_digest(first) == parquet_digest(second)
    report = write_stage2_report(first)
    text = report.read_text(encoding="utf-8")
    assert "Exact per-symbol conservation: **True**" in text
    assert "Anti-extinction/liveness criterion: **False**" in text
