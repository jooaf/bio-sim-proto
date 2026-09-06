"""Deterministic offline BFF execution assays and matrix association tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd
from numpy.random import Generator
from numpy.typing import NDArray

from analysis.spatial import jensen_shannon_similarity
from soup.substrate.base import ByteTape, ExecutionBudget, HaltReason
from soup.substrate.bff import BFFSubstrate, INSTRUCTIONS


@dataclass(frozen=True, slots=True)
class MantelResult:
    correlation: float
    null_mean: float
    p_value: float
    tapes: int
    pairs: int
    probes: int
    permutations: int


def standard_behavior_probes(tape_length: int) -> tuple[ByteTape, ...]:
    """Return four fixed partners spanning inert, instruction-rich, and random tapes."""

    if tape_length <= 0:
        raise ValueError("tape_length must be positive")
    instruction_cycle = np.resize(np.asarray(INSTRUCTIONS, dtype=np.uint8), tape_length)
    random_probe = np.random.default_rng(20260907).integers(
        0, 256, size=tape_length, dtype=np.uint8
    )
    return (
        np.zeros(tape_length, dtype=np.uint8),
        np.full(tape_length, 255, dtype=np.uint8),
        instruction_cycle,
        random_probe,
    )


def behavior_fingerprints(
    tapes: NDArray[np.uint8],
    *,
    substrate: BFFSubstrate,
    max_steps: int,
) -> NDArray[np.float64]:
    """Assay every focal tape against fixed probes without mutation or pool limits."""

    if tapes.ndim != 2 or tapes.shape[1] != substrate.tape_length:
        raise ValueError("tapes must be a matrix matching the substrate tape length")
    if max_steps <= 0:
        raise ValueError("max_steps must be positive")
    probes = standard_behavior_probes(substrate.tape_length)
    halt_reasons = tuple(HaltReason)
    rows: list[list[float]] = []
    for tape in tapes:
        features: list[float] = []
        for probe in probes:
            joint = np.concatenate((tape.copy(), probe.copy()))
            before = joint.copy()
            result = substrate.execute(
                joint,
                pool=None,
                budget=ExecutionBudget(max_steps=max_steps),
                signals=None,
            )
            length = substrate.tape_length
            features.extend(
                [
                    result.steps_executed / max_steps,
                    result.writes_success / max_steps,
                    np.count_nonzero(joint != before) / (2 * length),
                    np.count_nonzero(joint[:length] != before[:length]) / length,
                    np.count_nonzero(joint[length:] != before[length:]) / length,
                ]
            )
            features.extend(
                1.0 if result.halt_reason is reason else 0.0 for reason in halt_reasons
            )
        rows.append(features)
    return np.asarray(rows, dtype=np.float64)


def pairwise_js_similarity(compositions: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return a symmetric Jensen–Shannon similarity matrix."""

    if compositions.ndim != 2 or len(compositions) < 2:
        raise ValueError("compositions must contain at least two probability rows")
    matrix = np.empty((len(compositions), len(compositions)), dtype=np.float64)
    for index, composition in enumerate(compositions):
        left = np.repeat(composition[None, :], len(compositions), axis=0)
        matrix[index] = jensen_shannon_similarity(left, compositions)
    return matrix


def pairwise_gower_similarity(features: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return one minus mean absolute difference over normalized assay features."""

    if features.ndim != 2 or len(features) < 2:
        raise ValueError("features must contain at least two rows")
    if np.any(features < 0.0) or np.any(features > 1.0):
        raise ValueError("Gower assay features must lie in [0, 1]")
    return cast(
        NDArray[np.float64],
        1.0 - np.mean(np.abs(features[:, None, :] - features[None, :, :]), axis=2),
    )


def mantel_spearman_test(
    composition_similarity: NDArray[np.float64],
    behavior_similarity: NDArray[np.float64],
    *,
    probes: int,
    permutations: int = 999,
    rng: Generator | None = None,
) -> MantelResult:
    """Test association of two tape-similarity matrices by label permutation."""

    if composition_similarity.shape != behavior_similarity.shape:
        raise ValueError("similarity matrices must have equal shape")
    if composition_similarity.ndim != 2 or composition_similarity.shape[0] < 3:
        raise ValueError("similarity matrices must be square with at least three tapes")
    if composition_similarity.shape[0] != composition_similarity.shape[1]:
        raise ValueError("similarity matrices must be square")
    if permutations <= 0:
        raise ValueError("permutations must be positive")
    upper = np.triu_indices(len(composition_similarity), k=1)
    composition_values = composition_similarity[upper]
    behavior_values = behavior_similarity[upper]
    composition_ranks = pd.Series(composition_values).rank(method="average").to_numpy(dtype=np.float64)
    behavior_ranks = pd.Series(behavior_values).rank(method="average").to_numpy(dtype=np.float64)
    observed = float(np.corrcoef(composition_ranks, behavior_ranks)[0, 1])
    if not np.isfinite(observed):
        raise ValueError("observed similarity matrices must have nonconstant ranks")
    behavior_rank_matrix = np.zeros_like(behavior_similarity)
    behavior_rank_matrix[upper] = behavior_ranks
    behavior_rank_matrix[(upper[1], upper[0])] = behavior_ranks
    generator = np.random.default_rng(0) if rng is None else rng
    null = np.empty(permutations, dtype=np.float64)
    for index in range(permutations):
        permutation = generator.permutation(len(behavior_similarity))
        permuted_ranks = behavior_rank_matrix[
            permutation[upper[0]], permutation[upper[1]]
        ]
        null[index] = float(np.corrcoef(composition_ranks, permuted_ranks)[0, 1])
    return MantelResult(
        correlation=observed,
        null_mean=float(np.mean(null)),
        p_value=float((1 + np.count_nonzero(null >= observed - 1e-15)) / (permutations + 1)),
        tapes=len(composition_similarity),
        pairs=len(composition_values),
        probes=probes,
        permutations=permutations,
    )
