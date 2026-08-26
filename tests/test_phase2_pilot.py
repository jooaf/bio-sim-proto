from __future__ import annotations

import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.analyze_phase2_liveness_pilot import (
    _count_pool_changes,
    treatment_summary,
    write_report,
)
from experiments.analyze_phase2_radius_pilot import exact_paired_sign_flip_greater
from soup.config import Config, PairingMode


def test_liveness_pilot_config_and_sweep_are_frozen_consistently() -> None:
    config = Config.load("experiments/configs/stage2_liveness_pilot.toml")
    with Path("experiments/configs/stage2_liveness_pilot_sweep.toml").open("rb") as handle:
        sweep = tomllib.load(handle)

    assert config.run.stage == 2
    assert config.run.n_ticks == 5_000
    assert config.world.width == config.world.height == 8
    assert config.world.pairing_mode == PairingMode.LOCAL_NEIGHBORHOOD.value
    assert config.energy.enabled is False
    assert config.dissolution.inert_ticks > config.run.n_ticks
    assert sweep["sweep"]["n_seeds"] == 3
    assert sweep["parameters"]["dissolution.spontaneous_rate"] == [1e-6, 1e-5, 1e-4]
    assert sweep["parameters"]["world.reseed_rate"] == [1e-5, 1e-4, 1e-3]


def test_liveness_confirmation_keeps_selected_rates_at_larger_scale() -> None:
    config = Config.load("experiments/configs/stage2_liveness_confirmation.toml")
    with Path("experiments/configs/stage2_liveness_confirmation_sweep.toml").open("rb") as handle:
        sweep = tomllib.load(handle)

    assert config.world.width == config.world.height == 32
    assert config.world.interactions_per_tick == 512
    assert config.run.n_ticks == 5_000
    assert config.world.reseed_rate == 1e-5
    assert config.dissolution.spontaneous_rate == 1e-5
    assert config.logging.full_tape_snapshot_interval == 500
    assert sweep["sweep"]["n_seeds"] == 3
    assert sweep["parameters"]["dissolution.spontaneous_rate"] == [1e-5]
    assert sweep["parameters"]["world.reseed_rate"] == [1e-5]


def test_radius_pilot_uses_unseen_matched_seeds_and_frozen_radii() -> None:
    config = Config.load("experiments/configs/stage2_radius_pilot.toml")
    with Path("experiments/configs/stage2_radius_pilot_sweep.toml").open("rb") as handle:
        sweep = tomllib.load(handle)

    assert config.world.width == config.world.height == 32
    assert config.world.reseed_rate == config.dissolution.spontaneous_rate == 1e-5
    assert config.logging.full_tape_snapshot_interval == 500
    assert sweep["sweep"]["start_seed"] == 202608260
    assert sweep["sweep"]["n_seeds"] == 5
    assert sweep["parameters"]["world.interaction_radius"] == [1, 2, 4, 8]


def test_acceptance_candidate_freezes_pilot_selected_configuration() -> None:
    config = Config.load("experiments/configs/stage2_acceptance_candidate.toml")

    assert config.run.seed == 202608300
    assert config.run.n_ticks == 500_000
    assert config.world.width == config.world.height == 32
    assert config.world.interaction_radius == 1
    assert config.world.interactions_per_tick == 512
    assert config.world.reseed_rate == config.dissolution.spontaneous_rate == 1e-5
    assert config.logging.interaction_log_rate == 0.0
    assert config.logging.full_tape_snapshot_interval == 5_000


def test_pool_changes_compare_each_adjacent_pair_once() -> None:
    values = pd.Series(
        [
            np.asarray([1, 2], dtype=np.int64),
            np.asarray([1, 2], dtype=np.int64),
            np.asarray([2, 1], dtype=np.int64),
        ]
    )
    assert _count_pool_changes(values) == 1


def test_exact_sign_flip_test_has_expected_five_pair_resolution() -> None:
    assert exact_paired_sign_flip_greater(np.ones(5)) == 1 / 32
    assert exact_paired_sign_flip_greater(-np.ones(5)) == 1.0


def test_treatment_selection_uses_feasibility_then_occupancy_distance(tmp_path: Path) -> None:
    rows: list[dict[str, object]] = []
    for seed in range(3):
        rows += [
            {
                "seed": seed,
                "dissolution_rate": 1e-6,
                "reseed_rate": 1e-5,
                "mechanically_feasible": True,
                "successful_exit": True,
                "conserved": True,
                "invariant_failures": 0,
                "late_mean_occupied_fraction": 0.60,
                "minimum_tapes": 30,
                "dissolutions": 2,
                "placements": 2,
                "neighbor_identity_excess": 0.0,
                "q1_beta_excess": 0.0,
                "final_tapes": 50,
                "final_unique_hashes": 50,
                "byte_snapshot_tick": -1,
                "neighbor_byte_identity_excess": float("nan"),
                "opcode_q1_beta_excess": float("nan"),
            },
            {
                "seed": seed,
                "dissolution_rate": 1e-5,
                "reseed_rate": 1e-4,
                "mechanically_feasible": True,
                "successful_exit": True,
                "conserved": True,
                "invariant_failures": 0,
                "late_mean_occupied_fraction": 0.79,
                "minimum_tapes": 40,
                "dissolutions": 4,
                "placements": 4,
                "neighbor_identity_excess": 0.0,
                "q1_beta_excess": 0.0,
                "final_tapes": 50,
                "final_unique_hashes": 50,
                "byte_snapshot_tick": -1,
                "neighbor_byte_identity_excess": float("nan"),
                "opcode_q1_beta_excess": float("nan"),
            },
        ]
    runs = pd.DataFrame(rows)
    treatments = treatment_summary(runs)

    assert float(treatments.iloc[0]["dissolution_rate"]) == 1e-5
    assert float(treatments.iloc[0]["reseed_rate"]) == 1e-4
    assert bool(treatments.iloc[0]["eligible"])

    report = tmp_path / "pilot.md"
    write_report(runs, treatments, report)
    assert "Selected for larger-lattice confirmation" in report.read_text(encoding="utf-8")

    write_report(runs, treatments, report, confirmation=True)
    confirmation = report.read_text(encoding="utf-8")
    assert "larger-lattice confirmation" in confirmation.lower()
    assert "operating point confirmed" in confirmation.lower()
