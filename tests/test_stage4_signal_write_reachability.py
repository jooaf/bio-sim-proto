from __future__ import annotations

import pandas as pd

from experiments.analyze_stage4_signal_write_reachability import passes_gate


def test_reachability_gate_accepts_complete_connected_result() -> None:
    rows: list[dict[str, object]] = []
    for seed in range(202609280, 202609285):
        for arm in ("write_enabled", "write_disabled", "mismatched"):
            rows.append(
                {
                    "seed": seed, "arm": arm, "interactions": 800,
                    "signal_writes": 16 if arm == "write_enabled" else 0,
                    "occupied_final_written": arm == "write_enabled",
                    "all_reads_one": True,
                    "all_dispatches_one": arm == "write_disabled",
                    "all_dispatches_zero": arm == "mismatched",
                    "field_unchanged": arm != "write_enabled",
                    "changed_targets_valid": True, "final_tapes": 16,
                    "unchanged_tapes": True, "matter_total_constant": True,
                    "successful_exit": True, "invariant_failures": 0,
                }
            )
    assert passes_gate(pd.DataFrame(rows))
