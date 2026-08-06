"""Offline Hill-number diversity metrics (Jost effective numbers)."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any, cast

import numpy as np
import pandas as pd


DEFAULT_Q: tuple[float, ...] = (0.0, 0.5, 1.0, 2.0, 3.0, math.inf)


def hill_number(abundances: Iterable[int | float], q: float) -> float:
    """Compute effective type count of order q from nonnegative abundances."""

    counts = np.asarray(list(abundances), dtype=np.float64)
    counts = counts[counts > 0]
    if counts.size == 0:
        return 0.0
    probabilities = counts / counts.sum()
    if q == 0.0:
        return float(counts.size)
    if q == 1.0:
        return float(np.exp(-np.sum(probabilities * np.log(probabilities))))
    if math.isinf(q):
        return float(1.0 / probabilities.max())
    return float(np.sum(probabilities**q) ** (1.0 / (1.0 - q)))


def epoch_hill_numbers(population: pd.DataFrame, q_values: Iterable[float] = DEFAULT_Q) -> pd.DataFrame:
    """Compute a q-profile for each logged population epoch."""

    rows: list[dict[str, float | int]] = []
    for epoch, group in population.groupby("epoch", sort=True):
        for q in q_values:
            rows.append({"epoch": int(cast(Any, epoch)), "q": float(q), "diversity": hill_number(group["count"], q)})
    return pd.DataFrame(rows, columns=["epoch", "q", "diversity"])


def spatial_beta_diversity(tapes: pd.DataFrame, block_size: int) -> pd.DataFrame:
    """Stage 2 hook: compute multiplicative beta diversity from spatial snapshots."""

    if block_size <= 0:
        raise ValueError("block_size must be positive")
    if (tapes["cell_x"] < 0).all():
        return pd.DataFrame(columns=["tick", "q", "beta"])
    raise NotImplementedError("spatial beta diversity is implemented when the lattice enters at Stage 2")
