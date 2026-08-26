from __future__ import annotations

import tomllib
from pathlib import Path

import pandas as pd

from experiments.analyze_phase2_liveness_pilot import treatment_summary, write_report
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
