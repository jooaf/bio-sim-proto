from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from soup.config import Config, PairingMode
from soup.energy import EnergyLedger
from soup.logging.invariants import check_energy
from soup.simulation import Simulation
from soup.substrate.base import ExecutionBudget
from soup.substrate.bff import BFFSubstrate, OP_ENERGY_UPTAKE
from soup.world import SpatialWorld


def spatial_world(seed: int = 41) -> SpatialWorld:
    return SpatialWorld.create(
        width=4,
        height=4,
        initial_tape_fill=0.5,
        substrate=BFFSubstrate(tape_length=8),
        rng=np.random.default_rng(seed),
    )


def test_energy_flow_balances_influx_absorption_decay_and_diffusion() -> None:
    world = spatial_world()
    config = Config().energy
    config.enabled = True
    config.influx_rate = 16.0
    config.diffusion = 0.1
    config.decay = 0.25
    config.absorption_rate = 0.5
    ledger = EnergyLedger.create(world, config)

    ledger.advance_field(world, config)

    assert ledger.influx_cumulative == 16.0
    assert ledger.dissipated_cumulative == pytest.approx(4.0)
    assert ledger.tape_total == pytest.approx(4.0)
    assert ledger.field_total == pytest.approx(8.0)
    check_energy(world, ledger)


def test_active_uptake_is_local_local_capacity_bounded_and_pays_execution() -> None:
    world = spatial_world(43)
    config = Config().energy
    config.enabled = True
    config.tape_capacity = 0.5
    ledger = EnergyLedger.create(world, config)
    active = int(world.occupied_indices()[0])
    ledger.field[active] = 2.0
    ledger.initial_total = 2.0
    joint = np.zeros(16, dtype=np.uint8)
    joint[0] = OP_ENERGY_UPTAKE

    result = BFFSubstrate(tape_length=8).execute(
        joint,
        None,
        ExecutionBudget(
            max_steps=16,
            energy_available=0.0,
            energy_per_instruction=0.01,
        ),
        ledger.uptake_access(active, 1.0),
    )
    ledger.spend_execution(active, result.energy_consumed)

    assert result.energy_uptake_executions == 1
    assert result.energy_absorbed == pytest.approx(0.5)
    assert result.energy_consumed == pytest.approx(0.16)
    assert ledger.field[active] == pytest.approx(1.5)
    assert ledger.tapes[active] == pytest.approx(0.34)
    check_energy(world, ledger)


def test_uptake_opcode_is_inert_when_access_is_disabled() -> None:
    joint = np.zeros(16, dtype=np.uint8)
    joint[0] = OP_ENERGY_UPTAKE

    result = BFFSubstrate(tape_length=8).execute(
        joint,
        None,
        ExecutionBudget(
            max_steps=16,
            energy_available=0.0,
            energy_per_instruction=0.01,
        ),
        None,
    )

    assert result.steps_executed == 0
    assert result.energy_uptake_executions == 0
    assert result.energy_absorbed == 0.0
    assert result.energy_consumed == 0.0


def test_energy_birth_transfer_and_cost_preserve_ledger_balance() -> None:
    world = spatial_world(42)
    config = Config().energy
    config.enabled = True
    ledger = EnergyLedger.create(world, config)
    parent = int(world.occupied_indices()[0])
    child = int(np.flatnonzero(~world.occupied)[0])
    ledger.tapes[parent] = 5.0
    ledger.initial_total = 5.0

    ledger.fund_birth(parent, child, birth_cost=1.5, offspring_energy=1.0)
    world.place(child, world.tapes[parent].copy(), tick=1)

    assert ledger.tapes[parent] == pytest.approx(2.5)
    assert ledger.tapes[child] == pytest.approx(1.0)
    assert ledger.dissipated_cumulative == pytest.approx(1.5)
    check_energy(world, ledger)


def energy_config(tmp_path: Path) -> Config:
    config = Config()
    config.run.stage = 3
    config.run.n_ticks = 5
    config.run.epoch_length = 1
    config.run.debug_invariants = True
    config.substrate.tape_length = 8
    config.substrate.max_steps = 16
    config.world.width = 4
    config.world.height = 4
    config.world.interaction_radius = 1
    config.world.interactions_per_tick = 8
    config.world.pairing_mode = PairingMode.LOCAL_NEIGHBORHOOD.value
    config.world.mutation_rate = 0.0
    config.world.reseed_rate = 0.0
    config.symbols.initial_tape_fill = 0.5
    config.energy.enabled = True
    config.energy.influx_rate = 4.0
    config.energy.absorption_rate = 0.5
    config.energy.tape_capacity = 10.0
    config.energy.per_instruction = 0.01
    config.energy.per_write = 0.02
    config.energy.diffusion = 0.1
    config.energy.decay = 0.05
    config.energy.min_to_interact = 0.01
    config.dissolution.enabled = False
    config.reproduction.enabled = False
    config.logging.flush_interval = 5
    config.logging.full_tape_snapshot_interval = 1
    config.run.output_dir = str(tmp_path)
    return config


def test_energy_stage_logs_balanced_nonzero_flow(tmp_path: Path) -> None:
    config = energy_config(tmp_path)

    run_dir = Simulation(config, run_dir=tmp_path / "energy-flow").run()

    ticks = pd.read_parquet(run_dir / "ticks.parquet")
    final = ticks.iloc[-1]
    accounted = (
        float(final["energy_field_total"])
        + float(final["energy_tape_total"])
        + float(final["energy_dissipated_cum"])
    )
    assert float(final["energy_influx_cum"]) == pytest.approx(20.0)
    assert accounted == pytest.approx(20.0)
    assert float(final["energy_tape_total"]) > 0.0
    assert float(final["energy_dissipated_cum"]) > 0.0
    assert (ticks["n_interactions"] > 0).all()


def test_stage4_uptake_logs_execution_mediated_transfer(tmp_path: Path) -> None:
    config = energy_config(tmp_path)
    config.run.stage = 4
    config.run.n_ticks = 2
    config.symbols.initial_tape_fill = 1.0
    config.energy.influx_rate = 16.0
    config.energy.absorption_rate = 0.0
    config.energy.active_uptake_enabled = True
    config.energy.uptake_amount = 1.0
    config.energy.min_to_interact = 0.0
    config.logging.tick_tables = ["ticks", "interactions"]
    config.logging.interaction_log_rate = 1.0
    config.logging.flush_interval = 2
    tape = np.zeros(8, dtype=np.uint8)
    tape[0] = OP_ENERGY_UPTAKE

    run_dir = Simulation(
        config,
        run_dir=tmp_path / "active-uptake",
        initial_tape_overrides={index: tape for index in range(16)},
    ).run()

    events = pd.read_parquet(run_dir / "events.parquet")
    uptake = events[events["event_type"] == "energy_uptake"]
    ticks = pd.read_parquet(run_dir / "ticks.parquet")
    assert len(uptake) == 2
    assert float(ticks.iloc[-1]["energy_tape_total"]) > 0.0
    assert float(ticks.iloc[-1]["energy_dissipated_cum"]) > 0.0
    assert float(ticks.iloc[-1]["energy_influx_cum"]) == pytest.approx(32.0)


def test_starvation_dissolves_zero_energy_tapes(tmp_path: Path) -> None:
    config = energy_config(tmp_path)
    config.run.n_ticks = 2
    config.energy.influx_rate = 0.0
    config.energy.absorption_rate = 0.0
    config.dissolution.enabled = True
    config.dissolution.inert_ticks = 1000
    config.dissolution.starved_ticks = 2
    config.logging.flush_interval = 2

    run_dir = Simulation(config, run_dir=tmp_path / "energy-starvation").run()

    events = pd.read_parquet(run_dir / "events.parquet")
    deaths = events[events["event_type"] == "tape_dissolved"]
    assert len(deaths) == 8
    assert all('"cause":"starved"' in details for details in deaths["details_json"])
