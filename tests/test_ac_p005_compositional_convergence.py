from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from experiments import analyze_ac_p003_functional_origin_convergence as structural
from experiments import analyze_ac_p005_compositional_convergence as analysis


def controls() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            pool_ranks=np.asarray([0], dtype=np.int64),
            checkpoint=SimpleNamespace(
                witness=np.zeros(64, dtype=np.uint8),
                run=SimpleNamespace(label=f"run-{seed}", seed=seed),
            ),
        )
        for seed in range(6)
    ]


def test_reference_index_is_deterministic_and_bounded() -> None:
    observed = [analysis.reference_index(7, replicate, 2, 6) for replicate in range(100)]
    assert observed == [analysis.reference_index(7, replicate, 2, 6) for replicate in range(100)]
    assert all(0 <= value < 7 for value in observed)


def test_composition_gate_requires_effect_and_tail() -> None:
    with (
        patch.object(structural, "pairwise", return_value=(np.zeros((6, 6)), np.full((6, 6), 0.49))),
        patch.object(analysis, "reference_composition_medians", return_value=np.full(10_000, 0.5)),
    ):
        result = analysis.evaluate(controls(), True)  # type: ignore[arg-type]
    assert result["decision"] == "PASS"
    assert result["gates"]["composition_effect"]
    assert result["gates"]["composition_tail"]


def test_composition_gate_rejects_subthreshold_effect() -> None:
    with (
        patch.object(structural, "pairwise", return_value=(np.zeros((6, 6)), np.full((6, 6), 0.496))),
        patch.object(analysis, "reference_composition_medians", return_value=np.full(10_000, 0.5)),
    ):
        result = analysis.evaluate(controls(), True)  # type: ignore[arg-type]
    assert result["decision"] == "VALID NON-PASS"
    assert not result["gates"]["composition_effect"]
