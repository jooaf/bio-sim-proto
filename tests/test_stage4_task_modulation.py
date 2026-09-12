from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.analyze_stage4_task_modulation import paired_effects, passes_gate
from soup.tasks import TaskLedger


def test_task_weights_scale_only_scored_cells() -> None:
    ledger = TaskLedger(scores=np.asarray([1.0, 0.0, 1.0, 0.0]))
    probabilities = ledger.active_probabilities(np.asarray([0, 1, 2, 3]), 3.0)
    assert np.allclose(probabilities, [0.4, 0.1, 0.4, 0.1])


def test_task_modulation_gate_accepts_complete_selection_effect() -> None:
    rows: list[dict[str, object]] = []
    for seed in range(202609300, 202609310):
        for enabled in (False, True):
            rows.append({
                "seed": seed, "task_enabled": enabled,
                "correct_selection_fraction": 0.8 if enabled else 0.5,
                "correct_scores_one": enabled, "incorrect_scores_zero": True,
                "all_scores_zero": not enabled, "behavior_exact": True,
                "final_tapes": 16, "two_immutable_types": True,
                "successful_exit": True, "invariant_failures": 0,
                "max_relative_energy_error": 1e-12,
            })
    runs = pd.DataFrame(rows)
    assert passes_gate(runs, paired_effects(runs))
