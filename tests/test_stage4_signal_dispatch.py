from __future__ import annotations

import pandas as pd

from experiments.analyze_stage4_signal_dispatch import passes_gate


def test_signal_dispatch_gate_accepts_exact_control_pattern() -> None:
    rows: list[dict[str, object]] = []
    for seed in range(202609260, 202609265):
        for arm in ("matched", "mismatched", "disabled"):
            matched = arm == "matched"
            enabled = arm != "disabled"
            rows.append(
                {
                    "seed": seed,
                    "arm": arm,
                    "interactions": 800,
                    "signal_reads": 800 if enabled else 0,
                    "signal_dispatches": 800 if matched else 0,
                    "all_reads_one": enabled,
                    "all_reads_zero": not enabled,
                    "all_dispatches_one": matched,
                    "all_dispatches_zero": not matched,
                    "uptake_executions": 800 if matched else 0,
                    "final_tapes": 8,
                    "final_mean_energy": 9.99 if matched else 0.0,
                    "unchanged_tapes": True,
                    "successful_exit": True,
                    "invariant_failures": 0,
                    "max_relative_energy_error": 1e-12,
                }
            )
    assert passes_gate(pd.DataFrame(rows))


def test_signal_dispatch_gate_rejects_mismatched_dispatch() -> None:
    rows: list[dict[str, object]] = []
    for seed in range(202609260, 202609265):
        for arm in ("matched", "mismatched", "disabled"):
            matched = arm == "matched"
            enabled = arm != "disabled"
            rows.append(
                {
                    "seed": seed,
                    "arm": arm,
                    "interactions": 800,
                    "signal_reads": 800 if enabled else 0,
                    "signal_dispatches": 800 if matched else 0,
                    "all_reads_one": enabled,
                    "all_reads_zero": not enabled,
                    "all_dispatches_one": matched,
                    "all_dispatches_zero": not matched,
                    "uptake_executions": 800 if matched else 0,
                    "final_tapes": 8,
                    "final_mean_energy": 9.99 if matched else 0.0,
                    "unchanged_tapes": True,
                    "successful_exit": True,
                    "invariant_failures": 0,
                    "max_relative_energy_error": 1e-12,
                }
            )
    runs = pd.DataFrame(rows)
    runs.loc[(runs["arm"] == "mismatched") & (runs["seed"] == 202609260), "all_dispatches_zero"] = False
    assert not passes_gate(runs)
