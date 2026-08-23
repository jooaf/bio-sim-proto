from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from analysis.report import parquet_digest
from soup.config import Config, PairingMode
from soup.ledgers import SymbolPool
from soup.simulation import Simulation
from soup.substrate.base import ExecutionBudget, HaltReason, WriteOutcome
from soup.substrate.ski import APPLY, I, K, S, SKISubstrate, parse_expression, serialize_expression


def tape(prefix: str, length: int = 8) -> np.ndarray:
    values = np.zeros(length, dtype=np.uint8)
    values[: len(prefix)] = np.frombuffer(prefix.encode("ascii"), dtype=np.uint8)
    return values


def execute(first: str, second: str, *, steps: int = 16, pool: SymbolPool | None = None) -> tuple[np.ndarray, object]:
    joint = np.concatenate((tape(first), tape(second)))
    result = SKISubstrate(tape_length=8).execute(joint, pool, ExecutionBudget(max_steps=steps), None)
    return joint, result


def test_i_reduction() -> None:
    joint, result = execute("I", "S")
    assert joint[:8].tolist() == tape("S").tolist()
    assert result.halt_reason is HaltReason.NORMAL_FORM


def test_k_reduction() -> None:
    joint, result = execute("@KS", "I")
    assert joint[:8].tolist() == tape("S").tolist()
    assert result.halt_reason is HaltReason.NORMAL_FORM


def test_s_reduction_one_step() -> None:
    joint, result = execute("@@SKK", "I", steps=1)
    assert joint[:8].tolist() == tape("@@KI@KI").tolist()
    assert result.halt_reason is HaltReason.BUDGET_EXHAUSTED


def test_blocked_ski_rewrite_is_atomic() -> None:
    joint = np.concatenate((tape("I"), tape("S")))
    original = joint.copy()
    pool = SymbolPool(
        counts=np.zeros(256, dtype=np.int64),
        conserved_totals=np.bincount(joint, minlength=256).astype(np.int64),
    )
    result = SKISubstrate(tape_length=8).execute(joint, pool, ExecutionBudget(max_steps=8), None)
    assert result.halt_reason is HaltReason.POOL_BLOCKED
    assert np.array_equal(joint, original)
    assert np.count_nonzero(pool.counts) == 0


def test_atomic_batch_can_use_symbols_returned_by_same_reaction() -> None:
    values = np.asarray([1, 2], dtype=np.uint8)
    counts = np.zeros(256, dtype=np.int64)
    pool = SymbolPool(counts=counts, conserved_totals=np.bincount(values, minlength=256).astype(np.int64))
    result = pool.write_batch(
        values,
        np.asarray([0, 1], dtype=np.int64),
        np.asarray([2, 1], dtype=np.uint8),
    )
    assert result.outcome is WriteOutcome.SUCCESS
    assert result.changed_slots == 2
    assert values.tolist() == [2, 1]
    assert np.count_nonzero(pool.counts) == 0


def test_random_ski_tapes_are_valid_and_deterministic() -> None:
    first_rng = np.random.Generator(np.random.PCG64(42))
    second_rng = np.random.Generator(np.random.PCG64(42))
    substrate = SKISubstrate(tape_length=32)
    first = substrate.random_tape(first_rng)
    second = substrate.random_tape(second_rng)
    assert np.array_equal(first, second)
    expression = parse_expression(first)
    assert expression is not None
    assert set(serialize_expression(expression)) <= {APPLY, S, K, I}


def ski_config() -> Config:
    config = Config()
    config.run.stage = 1
    config.run.seed = 77
    config.run.n_ticks = 20
    config.substrate.name = "ski"
    config.substrate.tape_length = 16
    config.substrate.max_steps = 16
    config.world.population_size = 16
    config.world.interactions_per_tick = 8
    config.world.pairing_mode = PairingMode.SHUFFLED_DISJOINT.value
    config.world.mutation_rate = 0.0
    config.logging.flush_interval = 5
    config.logging.tape_snapshot_interval = 1
    config.logging.full_tape_snapshot_interval = 5
    return config


def test_ski_uses_existing_pipeline_and_is_deterministic(tmp_path: Path) -> None:
    first_simulation = Simulation(ski_config(), run_dir=tmp_path / "first")
    first = first_simulation.run()
    second = Simulation(ski_config(), run_dir=tmp_path / "second").run()

    assert first_simulation.substrate.name == "ski"
    assert first_simulation.pool is not None
    assert parquet_digest(first) == parquet_digest(second)
    ticks = pd.read_parquet(first / "ticks.parquet")
    interactions = pd.read_parquet(first / "interactions.parquet")
    assert len(ticks) == 20
    assert len(interactions) == 160
    assert (first_simulation.pool.counts >= 0).all()
