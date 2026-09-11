from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.analyze_stage4_structured_field import (
    moran_i,
    paired_effects,
    passes_gate,
    primary_p,
)


def _runs() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for seed in range(202609230, 202609235):
        rows.append(
            {
                "seed": seed,
                "field_spec": "uniform",
                "correlation_length": np.nan,
                "uptake_moran": 0.0,
                "uptake_cv": 0.1,
                "tape_energy_moran": 0.0,
                "profile_moran": 0.0,
                "profile_cv": 0.0,
                "profile_min": 1.0,
                "profile_sum": 256.0,
                "successful_exit": True,
                "final_tapes": 128,
                "active_ticks": 1000,
                "gross_uptake": 10.0,
                "unchanged_tape_type": True,
                "invariant_failures": 0,
                "max_relative_energy_error": 1e-12,
            }
        )
        for length, uptake_moran in ((0.5, 0.2), (2.0, 0.4), (8.0, 0.6)):
            rows.append(
                {
                    "seed": seed,
                    "field_spec": "patches",
                    "correlation_length": length,
                    "uptake_moran": uptake_moran,
                    "uptake_cv": 0.5,
                    "tape_energy_moran": 0.3,
                    "profile_moran": 0.7,
                    "profile_cv": 1.0,
                    "profile_min": 0.01,
                    "profile_sum": 256.0,
                    "successful_exit": True,
                    "final_tapes": 128,
                    "active_ticks": 1000,
                    "gross_uptake": 10.0,
                    "unchanged_tape_type": True,
                    "invariant_failures": 0,
                    "max_relative_energy_error": 1e-12,
                }
            )
    return pd.DataFrame(rows)


def test_moran_i_distinguishes_clustered_from_checkerboard_fields() -> None:
    clustered = np.zeros((16, 16), dtype=np.float64)
    clustered[:8] = 1.0
    checkerboard = np.indices((16, 16)).sum(axis=0) % 2
    assert moran_i(clustered.reshape(-1)) > 0.5
    assert moran_i(checkerboard.astype(np.float64).reshape(-1)) < 0.0


def test_structured_field_gate_passes_complete_mechanics_result() -> None:
    runs = _runs()
    effects = paired_effects(runs)
    assert primary_p(effects) == 0.03125
    assert passes_gate(runs, effects)


def test_structured_field_gate_rejects_unclosed_profile() -> None:
    runs = _runs()
    patch_index = runs.index[runs["field_spec"] == "patches"][0]
    runs.loc[patch_index, "profile_sum"] = 255.0
    assert not passes_gate(runs, paired_effects(runs))
