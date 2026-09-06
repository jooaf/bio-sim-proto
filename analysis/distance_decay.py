"""Toroidal distance-decay analysis for continuous tape compositions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.random import Generator
from numpy.typing import NDArray

from analysis.functional import pairwise_js_similarity
from analysis.spatial import bff_opcode_composition_matrix


@dataclass(frozen=True, slots=True)
class DistanceDecayResult:
    decay_strength: float
    null_mean: float
    excess: float
    p_value: float
    occupied_tapes: int
    pairs: int
    max_distance: int
    permutations: int


def toroidal_chebyshev_distances(
    snapshot: pd.DataFrame, *, width: int, height: int
) -> tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int64]]:
    """Return upper-triangle tape indices and toroidal Chebyshev distances."""

    if width <= 0 or height <= 0:
        raise ValueError("world dimensions must be positive")
    coordinates = snapshot[["cell_x", "cell_y"]].to_numpy(dtype=np.int64)
    if len(coordinates) < 2:
        raise ValueError("distance decay requires at least two occupied tapes")
    left, right = np.triu_indices(len(coordinates), k=1)
    dx_raw = np.abs(coordinates[left, 0] - coordinates[right, 0])
    dy_raw = np.abs(coordinates[left, 1] - coordinates[right, 1])
    dx = np.minimum(dx_raw, width - dx_raw)
    dy = np.minimum(dy_raw, height - dy_raw)
    return left.astype(np.int64), right.astype(np.int64), np.maximum(dx, dy).astype(np.int64)


def _curve_from_pairs(
    similarities: NDArray[np.float64], distances: NDArray[np.int64], max_distance: int
) -> NDArray[np.float64]:
    counts = np.bincount(distances, minlength=max_distance + 1)[1:]
    totals = np.bincount(distances, weights=similarities, minlength=max_distance + 1)[1:]
    if np.any(counts == 0):
        raise ValueError("every toroidal distance bin must contain a pair")
    return totals / counts


def _decay_strength(curve: NDArray[np.float64]) -> float:
    distances = np.arange(1, len(curve) + 1, dtype=np.float64)
    slope = np.polyfit(distances, curve, deg=1)[0]
    return float(-slope)


def opcode_js_distance_decay_test(
    snapshot: pd.DataFrame,
    *,
    width: int,
    height: int,
    permutations: int = 199,
    rng: Generator | None = None,
) -> tuple[DistanceDecayResult, pd.DataFrame]:
    """Test whether opcode-composition similarity decreases with toroidal distance."""

    if permutations <= 0:
        raise ValueError("permutations must be positive")
    frame = snapshot.reset_index(drop=True)
    compositions = bff_opcode_composition_matrix(frame)
    similarity = pairwise_js_similarity(compositions)
    left, right, distances = toroidal_chebyshev_distances(frame, width=width, height=height)
    max_distance = max(width // 2, height // 2)
    curve = _curve_from_pairs(similarity[left, right], distances, max_distance)
    observed = _decay_strength(curve)
    generator = np.random.default_rng(0) if rng is None else rng
    null = np.empty(permutations, dtype=np.float64)
    for index in range(permutations):
        permutation = generator.permutation(len(similarity))
        values = similarity[permutation[left], permutation[right]]
        null[index] = _decay_strength(_curve_from_pairs(values, distances, max_distance))
    null_mean = float(np.mean(null))
    result = DistanceDecayResult(
        decay_strength=observed,
        null_mean=null_mean,
        excess=observed - null_mean,
        p_value=float((1 + np.count_nonzero(null >= observed - 1e-15)) / (permutations + 1)),
        occupied_tapes=len(frame),
        pairs=len(left),
        max_distance=max_distance,
        permutations=permutations,
    )
    curve_frame = pd.DataFrame(
        {
            "distance": np.arange(1, max_distance + 1, dtype=np.int64),
            "mean_js_similarity": curve,
        }
    )
    return result, curve_frame
