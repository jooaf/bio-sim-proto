"""Offline Stage 1 symbol-conservation validation."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import pandas as pd


def conservation_residuals(ticks: pd.DataFrame, tapes: pd.DataFrame) -> pd.DataFrame:
    """Compare per-symbol tape-plus-pool totals at every tape snapshot."""

    columns = ["tick", "pool_total", "matter_total", "max_abs_residual", "conserved"]
    if ticks.empty or tapes.empty:
        return pd.DataFrame(columns=columns)
    tick_rows = ticks.set_index("tick")
    totals: list[tuple[int, int, int, np.ndarray[tuple[int], np.dtype[np.int64]]]] = []
    for tick, snapshot in tapes.groupby("tick", sort=True):
        tick_value = int(cast(Any, tick))
        if tick_value not in tick_rows.index:
            continue
        histograms = [np.asarray(value, dtype=np.int64) for value in snapshot["byte_histogram"]]
        tape_histograms = np.stack(histograms)
        tape_total = np.sum(tape_histograms, axis=0)
        pool_histogram = np.asarray(tick_rows.loc[tick_value, "pool_histogram"], dtype=np.int64)
        combined = tape_total + pool_histogram
        totals.append((tick_value, int(np.sum(pool_histogram)), int(np.sum(combined)), combined))
    if not totals:
        return pd.DataFrame(columns=columns)
    baseline = totals[0][3]
    rows = [
        {
            "tick": tick,
            "pool_total": pool_total,
            "matter_total": matter_total,
            "max_abs_residual": int(np.max(np.abs(combined - baseline))),
            "conserved": bool(np.array_equal(combined, baseline)),
        }
        for tick, pool_total, matter_total, combined in totals
    ]
    return pd.DataFrame(rows, columns=columns)
