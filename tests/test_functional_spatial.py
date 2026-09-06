from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.distance_decay import opcode_js_distance_decay_test
from analysis.functional import (
    behavior_fingerprints,
    mantel_spearman_test,
    pairwise_gower_similarity,
    pairwise_js_similarity,
)
from analysis.spatial import bff_opcode_composition_matrix
from soup.substrate.bff import BFFSubstrate, OP_INC, OP_LOOP_START


def clustered_snapshot() -> pd.DataFrame:
    frame = pd.DataFrame(
        [
            {"cell_x": x, "cell_y": y, "content_hash": f"{x}-{y}"}
            for y in range(6)
            for x in range(6)
        ]
    )
    frame["full_bytes"] = [
        bytes([OP_INC] * 64) if x < 3 else bytes([OP_LOOP_START] * 64)
        for _y in range(6)
        for x in range(6)
    ]
    return frame


def test_behavior_fingerprints_are_deterministic_and_bounded() -> None:
    tapes = np.asarray(
        [[OP_INC] * 8, [OP_LOOP_START] * 8],
        dtype=np.uint8,
    )
    substrate = BFFSubstrate(tape_length=8)

    first = behavior_fingerprints(tapes, substrate=substrate, max_steps=32)
    second = behavior_fingerprints(tapes, substrate=substrate, max_steps=32)

    assert np.array_equal(first, second)
    assert first.shape[0] == 2
    assert np.all((first >= 0.0) & (first <= 1.0))


def test_mantel_test_detects_aligned_similarity_matrices() -> None:
    compositions = np.asarray(
        [[0.9, 0.1], [0.8, 0.2], [0.7, 0.3], [0.3, 0.7], [0.2, 0.8], [0.1, 0.9]],
        dtype=np.float64,
    )
    features = compositions.copy()

    result = mantel_spearman_test(
        pairwise_js_similarity(compositions),
        pairwise_gower_similarity(features),
        probes=1,
        permutations=199,
        rng=np.random.default_rng(18),
    )

    assert result.correlation > 0.9
    assert result.p_value < 0.05


def test_distance_decay_detects_clustered_opcode_composition() -> None:
    snapshot = clustered_snapshot()

    result, curve = opcode_js_distance_decay_test(
        snapshot,
        width=6,
        height=6,
        permutations=199,
        rng=np.random.default_rng(19),
    )

    assert bff_opcode_composition_matrix(snapshot).shape == (36, 11)
    assert result.decay_strength > 0
    assert result.p_value < 0.05
    assert list(curve["distance"]) == [1, 2, 3]
    assert float(curve.iloc[0]["mean_js_similarity"]) > float(
        curve.iloc[-1]["mean_js_similarity"]
    )
