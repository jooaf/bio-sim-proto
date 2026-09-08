from __future__ import annotations

import pandas as pd

from experiments.analyze_stage4_active_uptake import passes_gate


def _runs() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for enabled in (False, True):
        for seed in range(202609210, 202609215):
            rows.append(
                {
                    "seed": seed,
                    "active_uptake_enabled": enabled,
                    "uptake_executions": 100 if enabled else 0,
                    "energy_absorbed": 50.0 if enabled else 0.0,
                    "final_tape_energy": 10.0 if enabled else 0.0,
                    "final_tapes": 8,
                    "successful_exit": True,
                    "invariant_failures": 0,
                    "max_relative_energy_error": 1e-12,
                }
            )
    return pd.DataFrame(rows)


def test_active_uptake_gate_passes_matched_mechanics_control() -> None:
    assert passes_gate(_runs())


def test_active_uptake_gate_rejects_disabled_transfer() -> None:
    runs = _runs()
    runs.loc[0, "energy_absorbed"] = 0.1
    assert not passes_gate(runs)


def test_active_uptake_gate_requires_every_enabled_seed() -> None:
    runs = _runs()
    index = runs.index[runs["active_uptake_enabled"]][0]
    runs.loc[index, "uptake_executions"] = 0
    assert not passes_gate(runs)
