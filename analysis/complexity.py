"""Offline tape complexity summaries."""

from __future__ import annotations

import math
import zlib

import numpy as np


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


def assembly_index_placeholder() -> float:
    """Assembly-path approximation enters with construction histories in Stage 1+."""

    return math.nan
