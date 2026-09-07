from __future__ import annotations

import pandas as pd

from experiments.analyze_stage3_population_regulation import (
    confirmation_passes,
    pilot_groups,
    selected_rate,
)


def _pilot_row(rate: float, seed: int, *, feasible: bool, change: float) -> dict[str, object]:
    return {
        "dissolution_rate": rate,
        "seed": seed,
        "regulation_feasible": feasible,
        "reproductive_births": 180,
        "dissolutions": 175,
        "late_mean_occupied_fraction": 0.75,
        "occupancy_change": change,
        "max_lineage_depth": 3,
        "conserved": True,
        "invariant_failures": 0,
    }


def test_pilot_selection_uses_frozen_ranking() -> None:
    rows = [
        _pilot_row(rate, seed, feasible=True, change=change)
        for rate, change in ((0.00002, 0.04), (0.00003, 0.01))
        for seed in range(3)
    ]
    groups = pilot_groups(pd.DataFrame(rows))
    assert selected_rate(groups) == 0.00003


def test_pilot_requires_two_feasible_seeds() -> None:
    rows = [
        _pilot_row(0.00002, seed, feasible=seed == 0, change=0.01)
        for seed in range(3)
    ]
    assert selected_rate(pilot_groups(pd.DataFrame(rows))) is None


def _confirmation_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "regulation_feasible": [True] * 10,
            "final_family_excess": [0.04] * 10,
            "final_family_p": [0.002] * 10,
            "successful_exit": [True] * 10,
            "conserved": [True] * 10,
            "invariant_failures": [0] * 10,
        }
    )


def test_confirmation_gate_passes_complete_positive_control() -> None:
    assert confirmation_passes(_confirmation_frame())


def test_confirmation_gate_keeps_failures_in_denominator() -> None:
    frame = _confirmation_frame()
    frame.loc[7:, "regulation_feasible"] = False
    assert not confirmation_passes(frame)
