from __future__ import annotations

import pandas as pd

from experiments.analyze_stage3_regulated_lineage_persistence import (
    holm_adjust,
    passes_gate,
)


def _runs() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for stop_tick in (0, 10_000):
        for seed in range(10):
            rows.append(
                {
                    "seed": seed,
                    "stop_tick": stop_tick,
                    "final_family_excess": 0.08 if stop_tick == 0 else 0.04,
                    "final_family_p": 0.002,
                    "retention_ratio": 1.0 if stop_tick == 0 else 0.5,
                    "regulation_feasible": True,
                    "stopped_persistence_feasible": True,
                    "successful_exit": True,
                    "conserved": True,
                    "invariant_failures": 0,
                }
            )
    return pd.DataFrame(rows)


def _endpoints() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "endpoint": ["stopped_final", "continued_minus_stopped"],
            "mean": [0.04, 0.04],
            "bootstrap_lower": [0.03, 0.03],
            "holm_p": [0.002, 0.002],
        }
    )


def test_holm_adjustment_preserves_endpoint_order() -> None:
    assert holm_adjust((0.04, 0.01)) == (0.04, 0.02)


def test_integrated_gate_accepts_complete_positive_result() -> None:
    assert passes_gate(_runs(), _endpoints())


def test_integrated_gate_requires_both_coprimary_endpoints() -> None:
    endpoints = _endpoints()
    endpoints.loc[1, "bootstrap_lower"] = -0.001
    assert not passes_gate(_runs(), endpoints)


def test_integrated_gate_keeps_mechanical_failures_in_denominator() -> None:
    runs = _runs()
    runs.loc[
        (runs["stop_tick"] == 10_000) & (runs["seed"] >= 7),
        "stopped_persistence_feasible",
    ] = False
    assert not passes_gate(runs, _endpoints())
