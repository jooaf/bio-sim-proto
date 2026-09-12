from __future__ import annotations

import pandas as pd

from experiments.analyze_ac_r001_derived_friction_validation import paired_results, passes_gate


def test_derived_friction_gate_accepts_matched_mechanics() -> None:
    rows: list[dict[str, object]] = []
    for seed in range(202610010, 202610015):
        for treatment, blocks in (("natural_six", 100), ("friction", 105)):
            rows.append({"seed": seed, "treatment": treatment, "matched_blocks": blocks, "changing_write_attempts": 1000, "successful_exit": True, "max_conservation_residual": 0})
    runs = pd.DataFrame(rows)
    passed, ratio = passes_gate(runs, paired_results(runs))
    assert passed
    assert ratio == 1.05


def test_derived_friction_gate_rejects_load_mismatch() -> None:
    rows: list[dict[str, object]] = []
    for seed in range(202610010, 202610015):
        for treatment, blocks in (("natural_six", 100), ("friction", 20)):
            rows.append({"seed": seed, "treatment": treatment, "matched_blocks": blocks, "changing_write_attempts": 1000, "successful_exit": True, "max_conservation_residual": 0})
    runs = pd.DataFrame(rows)
    assert not passes_gate(runs, paired_results(runs))[0]
