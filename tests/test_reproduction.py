from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from numpy.random import Generator

from experiments.analyze_stage3r_lineage_patch import parent_map, root_map
from experiments.analyze_stage3r_reproduction_liveness import lineage_depth
from soup.config import (
    Config,
    OffspringPlacement,
    PairingMode,
    ReproductionTrigger,
)
from soup.energy import EnergyLedger
from soup.ledgers import SymbolPool
from soup.interactions import ExactCopyTriggerFact, run_local_interaction_round
from soup.logging.invariants import check_stage2
from soup.reproduction import reproduce_from_copy_triggers, reproduce_tapes
from soup.simulation import Simulation
from soup.substrate.base import (
    ByteTape,
    ExecutionBudget,
    ExecutionResult,
    HaltReason,
    SignalView,
    WriteMediator,
)
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


def test_transitive_root_map_handles_reproductive_and_random_roots() -> None:
    lineage = pd.DataFrame(
        {
            "tape_id": [2, 4, 8, 9],
            "progenitor_ids": [[], [2], [4], []],
        }
    )

    parents = parent_map(lineage)

    assert parents == {4: 2, 8: 4}
    assert root_map(parents, [2, 4, 8, 9]) == {2: 2, 4: 2, 8: 2, 9: 9}


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


def test_vacancy_first_birth_selects_parent_around_sampled_target() -> None:
    rng = np.random.default_rng(33)
    substrate = BFFSubstrate(tape_length=8)
    world = SpatialWorld.create(
        width=4,
        height=4,
        initial_tape_fill=0.5,
        substrate=substrate,
        rng=rng,
    )
    pool = SymbolPool.from_tapes(world.occupied_tapes(), 16.0)

    result = reproduce_tapes(
        world=world,
        pool=pool,
        rng=rng,
        tick=4,
        rate=1.0,
        placement_radius=1,
        max_births_per_tick=3,
        placement_protocol=OffspringPlacement.VACANCY_FIRST.value,
    )

    assert len(result.births) == 3
    assert result.blocked_no_space == 0
    assert result.blocked_no_parent == 0
    for birth in result.births:
        dx = min(
            abs(birth.parent_cell[0] - birth.child_cell[0]),
            world.width - abs(birth.parent_cell[0] - birth.child_cell[0]),
        )
        dy = min(
            abs(birth.parent_cell[1] - birth.child_cell[1]),
            world.height - abs(birth.parent_cell[1] - birth.child_cell[1]),
        )
        assert max(dx, dy) <= 1
    check_stage2(world, pool, substrate.tape_length)


def test_exact_copy_mode_rejects_a_scheduled_rate() -> None:
    config = Config()
    config.run.stage = 3
    config.world.pairing_mode = PairingMode.LOCAL_NEIGHBORHOOD.value
    config.reproduction.trigger = ReproductionTrigger.EXACT_COPY.value
    config.reproduction.rate = 0.1

    with pytest.raises(ValueError, match="requires reproduction.rate = 0"):
        config.validate()


def test_energy_birth_block_is_atomic() -> None:
    rng = np.random.default_rng(35)
    substrate = BFFSubstrate(tape_length=8)
    world = SpatialWorld.create(
        width=4,
        height=4,
        initial_tape_fill=0.5,
        substrate=substrate,
        rng=rng,
    )
    pool = SymbolPool.from_tapes(world.occupied_tapes(), 16.0)
    energy = EnergyLedger.create(world, Config().energy)
    occupied_before = world.occupied.copy()
    pool_before = pool.counts.copy()

    result = reproduce_tapes(
        world=world,
        pool=pool,
        rng=rng,
        tick=1,
        rate=1.0,
        placement_radius=1,
        max_births_per_tick=2,
        energy=energy,
        birth_energy_cost=1.0,
    )

    assert result.births == ()
    assert result.blocked_energy > 0
    assert np.array_equal(world.occupied, occupied_before)
    assert np.array_equal(pool.counts, pool_before)
    assert energy.accounted_total == 0.0


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


def test_reproduction_stop_tick_prevents_later_attempts(tmp_path: Path) -> None:
    config = Config()
    config.run.stage = 3
    config.run.n_ticks = 3
    config.run.epoch_length = 1
    config.substrate.tape_length = 8
    config.substrate.max_steps = 16
    config.world.width = 4
    config.world.height = 4
    config.world.interaction_radius = 1
    config.world.interactions_per_tick = 4
    config.world.pairing_mode = PairingMode.LOCAL_NEIGHBORHOOD.value
    config.symbols.initial_tape_fill = 0.5
    config.reproduction.enabled = True
    config.reproduction.rate = 1.0
    config.reproduction.stop_tick = 1
    config.reproduction.max_births_per_tick = 1
    config.logging.flush_interval = 3

    run_dir = Simulation(config, run_dir=tmp_path / "stopped-birth").run()
    events = pd.read_parquet(run_dir / "events.parquet")
    births = events[events["event_type"] == "offspring_born"]

    assert len(births) == 1
    assert births["tick"].tolist() == [0]


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


class CopyingSubstrate:
    name = "copying-test"
    tape_length = 4
    alphabet_size = 256

    def random_tape(self, rng: Generator) -> ByteTape:
        return rng.integers(0, 256, size=self.tape_length, dtype=np.uint8)

    def execute(
        self,
        joint: ByteTape,
        pool: WriteMediator | None,
        budget: ExecutionBudget,
        signals: SignalView | None,
    ) -> ExecutionResult:
        del budget, signals
        if pool is None:
            raise ValueError("copying test substrate requires a symbol pool")
        for index in range(self.tape_length):
            pool.write(joint, self.tape_length + index, int(joint[index]))
        return ExecutionResult(
            steps_executed=1,
            energy_consumed=0.0,
            writes_success=self.tape_length,
            writes_blocked=0,
            halt_reason=HaltReason.PC_OVERRUN,
        )

    def is_inert(self, tape: ByteTape) -> bool:
        del tape
        return False

    def describe(self, tape: ByteTape) -> dict[str, object]:
        return {"length": len(tape)}


def test_execution_exact_copy_trigger_can_fund_birth() -> None:
    rng = np.random.default_rng(34)
    substrate = CopyingSubstrate()
    world = SpatialWorld.create(
        width=3,
        height=3,
        initial_tape_fill=2 / 9,
        substrate=substrate,
        rng=rng,
    )
    occupied = world.occupied_indices()
    world.tapes[int(occupied[0])].fill(1)
    world.tapes[int(occupied[1])].fill(2)
    pool = SymbolPool.from_tapes(world.occupied_tapes(), 16.0)
    triggers: list[ExactCopyTriggerFact] = []

    facts = run_local_interaction_round(
        world=world,
        substrate=substrate,
        rng=rng,
        budget=ExecutionBudget(max_steps=8),
        tick=2,
        interactions_per_tick=1,
        interaction_radius=1,
        mutation_rate=0.0,
        pool=pool,
        hash_tape=lambda tape: tape.tobytes().hex(),
        copy_triggers=triggers,
    )
    result = reproduce_from_copy_triggers(
        world=world,
        pool=pool,
        rng=rng,
        tick=2,
        triggers=triggers,
        placement_radius=1,
        max_births_per_tick=1,
    )

    assert len(facts) == 1
    assert len(triggers) == 1
    assert triggers[0].direction == "a_into_b"
    assert len(result.births) == 1
    assert result.births[0].trigger == "exact_copy"
    assert result.births[0].trigger_target_id == triggers[0].target_id
    check_stage2(world, pool, substrate.tape_length)


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
