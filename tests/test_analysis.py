from __future__ import annotations

import math

import pandas as pd

from analysis.diversity import hill_number
from analysis.report import detect_replications


def test_hill_numbers_are_effective_type_counts() -> None:
    assert hill_number([1, 1, 1, 1], 0) == 4
    assert hill_number([1, 1, 1, 1], 1) == 4
    assert hill_number([1, 1, 1, 1], 2) == 4
    assert hill_number([9, 1], math.inf) == 10 / 9


def test_replication_is_detected_only_offline_from_hashes() -> None:
    interactions = pd.DataFrame(
        [
            {
                "tick": 3,
                "round_index": 2,
                "a_id": 1,
                "b_id": 2,
                "a_hash_before": "source",
                "a_hash_after": "source",
                "b_hash_before": "food",
                "b_hash_after": "source",
                "a_bytes_changed": 0,
                "b_bytes_changed": 12,
            },
            {
                "tick": 4,
                "round_index": 0,
                "a_id": 3,
                "b_id": 4,
                "a_hash_before": "x",
                "a_hash_after": "y",
                "b_hash_before": "z",
                "b_hash_after": "y",
                "a_bytes_changed": 1,
                "b_bytes_changed": 1,
            },
        ]
    )
    detected = detect_replications(interactions)
    assert len(detected) == 1
    assert detected.iloc[0]["source_hash"] == "source"
