from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from experiments.analyze_stage4_resource_birth import (
    exact_sign_test_greater,
    paired_effects,
    passes_gate,
)
from experiments.run_stage4_resource_birth import assignment
from soup.config import Config


def valid_runs() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for seed in range(202609250, 202609260):
        for initial_count in (8, 32, 56):
            initial_frequency = initial_count / 64.0
            for enabled in (False, True):
                rows.append(
                    {
                        "seed": seed,
                        "initial_uptake_count": initial_count,
                        "active_uptake_enabled": enabled,
                        "initial_frequency": initial_frequency,
                        "final_frequency": min(1.0, initial_frequency + 0.1) if enabled else initial_frequency,
                        "frequency_change": 0.1 if enabled else 0.0,
                        "births": 20 if enabled else 0,
                        "uptake_executions": 100 if enabled else 0,
                        "uptake_birth_fraction": 1.0 if enabled else 0.0,
                        "energy_blocked_births": 0 if enabled else 10,
                        "unexpected_population_events": 0,
                        "type_consistent": True,
                        "successful_exit": True,
                        "invariant_failures": 0,
                        "max_relative_energy_error": 1e-12,
                    }
                )
    return pd.DataFrame(rows)


def test_assignment_has_exact_deterministic_counts() -> None:
    config = Config.load(Path("experiments/configs/stage4_resource_birth.toml"))
    config.run.seed = 202609250
    first, protocol = assignment(config, 8)
    second, repeated = assignment(config, 8)
    assert protocol == repeated
    assert all(np.array_equal(first[index], second[index]) for index in first)
    assert protocol["initial_uptake_count"] == 8
    assert protocol["initial_control_count"] == 56


def test_resource_birth_gate_accepts_complete_result() -> None:
    runs = valid_runs()
    paired = paired_effects(runs)
    assert exact_sign_test_greater(paired["frequency_change"].to_numpy(dtype=np.float64)) == 2.0**-30
    assert passes_gate(runs, paired)


def test_resource_birth_gate_rejects_disabled_birth() -> None:
    runs = valid_runs()
    index = runs.index[~runs["active_uptake_enabled"]][0]
    runs.loc[index, "births"] = 1
    assert not passes_gate(runs, paired_effects(runs))
