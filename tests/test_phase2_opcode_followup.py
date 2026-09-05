from __future__ import annotations

import pandas as pd

from experiments.analyze_phase2_opcode_beta_followup import (
    BASELINE_MUTATION,
    LOW_MUTATION,
    holm_two,
    opcode_presence_label,
    paired_effect,
)
from experiments.analyze_phase2_opcode_js_followup import paired_results
from soup.substrate.bff import OP_DEC, OP_INC


def test_opcode_presence_label_ignores_order_and_noninstructions() -> None:
    left = opcode_presence_label(bytes([19, OP_INC, OP_DEC, OP_INC, 77]))
    right = opcode_presence_label(bytes([OP_DEC, OP_INC]))

    assert left == right
    assert left.count("1") == 2


def test_holm_two_requires_both_step_down_thresholds() -> None:
    assert holm_two({"H1": 0.01, "H2": 0.04}) == {"H1": True, "H2": True}
    assert holm_two({"H1": 0.03, "H2": 0.04}) == {"H1": False, "H2": False}


def test_js_paired_results_use_radius_one_minus_radius_eight() -> None:
    runs = pd.DataFrame(
        [
            {"seed": seed, "radius": radius, "opcode_js_excess": 0.2 if radius == 1 else 0.1}
            for seed in range(10)
            for radius in (1, 8)
        ]
    )

    differences, p_value, lower, upper = paired_results(runs)

    assert all(value > 0 for value in differences)
    assert p_value == 1 / 1_024
    assert lower > 0
    assert upper > 0


def test_paired_effect_selects_matched_factorial_slice() -> None:
    rows: list[dict[str, float | int]] = []
    for seed in range(10):
        for radius in (1, 8):
            for mutation in (LOW_MUTATION, BASELINE_MUTATION):
                rows.append(
                    {
                        "seed": seed,
                        "radius": radius,
                        "mutation_rate": mutation,
                        "outcome": float(radius) + 1000 * mutation,
                    }
                )
    differences, p_value = paired_effect(
        pd.DataFrame(rows),
        fixed_column="radius",
        fixed_value=1,
        compared_column="mutation_rate",
        high=BASELINE_MUTATION,
        low=LOW_MUTATION,
        outcome="outcome",
    )

    assert all(value > 0 for value in differences)
    assert p_value == 1 / 1_024
