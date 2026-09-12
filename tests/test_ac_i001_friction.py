from __future__ import annotations

import pandas as pd

from experiments.analyze_ac_i001_friction_calibration import select_rate


def test_calibration_selects_closest_acceptable_lower_tie() -> None:
    rows: list[dict[str, object]] = []
    for seed in range(5):
        rows.append({"seed": seed, "treatment": "natural_six", "friction_rate": 0.0, "matched_blocks": 100, "successful_exit": True, "max_conservation_residual": 0})
        for rate, blocks in ((0.01, 50), (0.02, 90), (0.03, 110), (0.05, 150), (0.08, 200)):
            rows.append({"seed": seed, "treatment": "friction", "friction_rate": rate, "matched_blocks": blocks, "successful_exit": True, "max_conservation_residual": 0})
    selected, groups = select_rate(pd.DataFrame(rows))
    assert selected == 0.03
    assert len(groups) == 5


def test_calibration_stops_when_closest_rate_is_outside_match_band() -> None:
    rows: list[dict[str, object]] = []
    for seed in range(5):
        rows.append({"seed": seed, "treatment": "natural_six", "friction_rate": 0.0, "matched_blocks": 1000, "successful_exit": True, "max_conservation_residual": 0})
        for rate, blocks in ((0.01, 10), (0.02, 20), (0.03, 30), (0.05, 50), (0.08, 80)):
            rows.append({"seed": seed, "treatment": "friction", "friction_rate": rate, "matched_blocks": blocks, "successful_exit": True, "max_conservation_residual": 0})
    selected, _ = select_rate(pd.DataFrame(rows))
    assert selected is None
