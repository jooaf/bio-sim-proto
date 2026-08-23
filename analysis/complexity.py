"""Offline tape complexity summaries."""

from __future__ import annotations

import math
import zlib
from typing import Any, cast

import brotli  # type: ignore[import-untyped]
import numpy as np
import pandas as pd


def byte_entropy(content: bytes) -> float:
    """Shannon byte entropy in bits, reported as complexity rather than diversity."""

    if not content:
        return 0.0
    counts = np.bincount(np.frombuffer(content, dtype=np.uint8), minlength=256)
    probabilities = counts[counts > 0] / len(content)
    return float(-np.sum(probabilities * np.log2(probabilities)))


def tape_complexity(content: bytes) -> dict[str, int | float]:
    """Return raw per-content proxies that require full bytes."""

    return {
        "nonzero_length": sum(value != 0 for value in content),
        "byte_entropy": byte_entropy(content),
        "zlib_length": len(zlib.compress(content)),
    }


def soup_high_order_entropy(tapes: pd.DataFrame) -> pd.DataFrame:
    """Compute the paper's Brotli-based soup complexity at full-byte snapshots."""

    columns = ["tick", "byte_entropy", "compressed_bytes", "compressed_bpb", "high_order_entropy"]
    full = tapes[tapes["full_bytes"].notna()]
    rows: list[dict[str, int | float]] = []
    for tick, snapshot in full.groupby("tick", sort=True):
        ordered = snapshot.sort_values("tape_id")
        content = b"".join(bytes(value) for value in ordered["full_bytes"])
        compressed_size = len(brotli.compress(content, quality=2, lgwin=24))
        compressed_bpb = 8.0 * compressed_size / len(content)
        entropy = byte_entropy(content)
        rows.append(
            {
                "tick": int(cast(Any, tick)),
                "byte_entropy": entropy,
                "compressed_bytes": compressed_size,
                "compressed_bpb": compressed_bpb,
                "high_order_entropy": entropy - compressed_bpb,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def assembly_index_placeholder() -> float:
    """Assembly-path approximation enters with construction histories in Stage 1+."""

    return math.nan
