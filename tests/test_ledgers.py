from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from analysis.report import write_stage1_report
from soup.config import Config, PairingMode
from soup.ledgers import SymbolPool
from soup.logging.invariants import InvariantViolation, check_stage1
from soup.simulation import Simulation
from soup.substrate.base import ExecutionBudget, WriteOutcome
from soup.substrate.bff import BFFSubstrate


def test_symbol_pool_exchanges_bytes_atomically() -> None:
    tape = np.asarray([1, 2], dtype=np.uint8)
    counts = np.zeros(256, dtype=np.int64)
    counts[3] = 1
    pool = SymbolPool(counts=counts, conserved_totals=np.zeros(256, dtype=np.int64))

    assert pool.write(tape, 0, 3) is WriteOutcome.SUCCESS
    assert tape.tolist() == [3, 2]
    assert pool.counts[1] == 1
    assert pool.counts[3] == 0
    assert pool.write(tape, 1, 4) is WriteOutcome.BLOCKED
    assert tape.tolist() == [3, 2]


def test_bff_write_is_blocked_when_target_symbol_is_unavailable() -> None:
    joint = np.asarray([ord(">"), 10, ord("+"), 0, 0, 0, 0, 0], dtype=np.uint8)
    pool = SymbolPool(
        counts=np.zeros(256, dtype=np.int64),
        conserved_totals=np.bincount(joint, minlength=256).astype(np.int64),
    )
    result = BFFSubstrate(tape_length=4).execute(
        joint,
        pool,
        ExecutionBudget(max_steps=8),
        None,
    )

    assert joint[1] == 10
    assert result.writes_success == 0
    assert result.writes_blocked == 1


def test_stage1_simulation_conserves_every_symbol(tmp_path: Path) -> None:
    config = Config()
    config.run.stage = 1
    config.run.n_ticks = 10
    config.substrate.tape_length = 16
    config.substrate.max_steps = 64
    config.substrate.noop_density = 0.75
    config.world.population_size = 16
    config.world.interactions_per_tick = 8
    config.world.pairing_mode = PairingMode.SHUFFLED_DISJOINT.value
    config.world.mutation_rate = 0.1
    config.logging.flush_interval = 5
    simulation = Simulation(config, run_dir=tmp_path / "stage1")
    initial_pool_total = simulation.pool.total if simulation.pool is not None else 0
    run_dir = simulation.run()

    assert simulation.pool is not None
    check_stage1(simulation.world, simulation.pool, config.substrate.tape_length)
    ticks = pd.read_parquet(run_dir / "ticks.parquet")
    interactions = pd.read_parquet(run_dir / "interactions.parquet")
    assert (ticks["pool_total"] == initial_pool_total).all()
    assert interactions["mutation_writes_success"].sum() > 0
    assert (simulation.pool.counts >= 0).all()
    report = write_stage1_report(run_dir)
    assert "Exact per-symbol conservation: **True**" in report.read_text(encoding="utf-8")

    simulation.pool.counts[0] += 1
    with pytest.raises(InvariantViolation, match="conservation failed"):
        check_stage1(simulation.world, simulation.pool, config.substrate.tape_length)
