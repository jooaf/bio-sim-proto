from __future__ import annotations

import pandas as pd

from experiments.analyze_stage4_mixed_energy_access import passes_gate, primary_p
from experiments.run_stage4_mixed_energy_access import assignment
from soup.config import Config


def _runs() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for enabled in (False, True):
        for seed in range(202609220, 202609225):
            rows.append(
                {
                    "seed": seed,
                    "active_uptake_enabled": enabled,
                    "final_energy_difference": 9.0 if enabled else 0.0,
                    "energy_area_difference": 900.0 if enabled else 0.0,
                    "uptake_type_final_energy": 9.0 if enabled else 0.0,
                    "control_type_final_energy": 0.0,
                    "uptake_type_steps": 1000 if enabled else 0,
                    "control_type_steps": 0,
                    "gross_uptake": 100.0 if enabled else 0.0,
                    "final_tape_energy": 36.0 if enabled else 0.0,
                    "final_tapes": 8,
                    "successful_exit": True,
                    "invariant_failures": 0,
                    "max_relative_energy_error": 1e-12,
                }
            )
    return pd.DataFrame(rows)


def test_mixed_assignment_is_balanced_and_seed_crossed() -> None:
    config = Config()
    config.run.stage = 4
    config.world.width = 4
    config.world.height = 4
    config.symbols.initial_tape_fill = 0.5
    config.substrate.tape_length = 8
    config.run.seed = 202609220
    _, even = assignment(config)
    config.run.seed += 1
    _, odd = assignment(config)

    assert even["uptake_count"] == even["control_count"] == 4
    assert [record["type"] for record in even["records"]] == [
        "uptake",
        "control",
        "uptake",
        "control",
        "uptake",
        "control",
        "uptake",
        "control",
    ]
    assert [record["type"] for record in odd["records"]] == [
        "control",
        "uptake",
        "control",
        "uptake",
        "control",
        "uptake",
        "control",
        "uptake",
    ]


def test_mixed_access_gate_passes_complete_differentiation() -> None:
    runs = _runs()
    assert primary_p(runs) == 0.03125
    assert passes_gate(runs)


def test_mixed_access_gate_rejects_funded_control_steps() -> None:
    runs = _runs()
    enabled_index = runs.index[runs["active_uptake_enabled"]][0]
    runs.loc[enabled_index, "control_type_steps"] = 1
    assert not passes_gate(runs)
