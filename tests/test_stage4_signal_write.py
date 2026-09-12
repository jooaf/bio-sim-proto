from __future__ import annotations

import pandas as pd

from experiments.analyze_stage4_signal_write import passes_gate


def valid_runs() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for seed in range(202609270, 202609275):
        for arm in ("write_enabled", "write_disabled", "mismatched"):
            rows.append(
                {
                    "seed": seed,
                    "arm": arm,
                    "interactions": 800,
                    "signal_reads": 800,
                    "signal_dispatches": 8 if arm == "write_enabled" else (800 if arm == "write_disabled" else 0),
                    "signal_writes": 8 if arm == "write_enabled" else 0,
                    "all_reads_one": True,
                    "all_dispatches_one": arm == "write_disabled",
                    "all_dispatches_zero": arm == "mismatched",
                    "occupied_final_written": arm == "write_enabled",
                    "field_unchanged": arm != "write_enabled",
                    "empty_cells_unchanged": True,
                    "changed_targets_valid": True,
                    "final_tapes": 8,
                    "unchanged_tapes": True,
                    "matter_total_constant": True,
                    "successful_exit": True,
                    "invariant_failures": 0,
                }
            )
    return pd.DataFrame(rows)


def test_signal_write_gate_accepts_complete_mechanics_result() -> None:
    assert passes_gate(valid_runs())


def test_signal_write_gate_rejects_empty_cell_change() -> None:
    runs = valid_runs()
    runs.loc[0, "empty_cells_unchanged"] = False
    assert not passes_gate(runs)
