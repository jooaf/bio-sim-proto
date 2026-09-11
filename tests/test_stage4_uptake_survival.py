from __future__ import annotations

import pandas as pd

from experiments.analyze_stage4_uptake_survival import effects, passes_gate


def valid_runs() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for seed in range(202609240, 202609250):
        for enabled in (False, True):
            rows.append(
                {
                    "seed": seed,
                    "active_uptake_enabled": enabled,
                    "uptake_survival": 1.0 if enabled else 0.0,
                    "control_survival": 0.0,
                    "total_survivors": 64 if enabled else 0,
                    "post_100_active_ticks": 400 if enabled else 0,
                    "gross_uptake": 100.0 if enabled else 0.0,
                    "all_deaths_starvation": True,
                    "type_consistent": True,
                    "successful_exit": True,
                    "invariant_failures": 0,
                    "max_relative_energy_error": 1e-12,
                }
            )
    return pd.DataFrame(rows)


def test_survival_gate_accepts_complete_causal_result() -> None:
    runs = valid_runs()
    assert passes_gate(runs, effects(runs))


def test_survival_gate_rejects_surviving_enabled_controls() -> None:
    runs = valid_runs()
    runs.loc[(runs["active_uptake_enabled"]) & (runs["seed"] == 202609240), "control_survival"] = 0.1
    assert not passes_gate(runs, effects(runs))
