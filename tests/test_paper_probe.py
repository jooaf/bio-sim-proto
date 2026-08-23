from __future__ import annotations

import hashlib

import numpy as np

from experiments.paper_probe import (
    initialize_soup,
    mutate_and_execute_epoch,
    shuffle_indices,
    splitmix64,
)


def test_splitmix_and_shuffle_match_reference_protocol() -> None:
    assert int(splitmix64(np.uint64(0))) == 16_294_208_416_658_607_535
    order = np.arange(256, dtype=np.uint32)
    shuffle_indices(order, seed=1, epoch=0)
    assert order[:8].tolist() == [188, 39, 21, 161, 222, 15, 152, 33]


def test_accelerated_first_epoch_matches_reference_digest() -> None:
    soup = initialize_soup(256, seed=1)
    order = np.arange(256, dtype=np.uint32)
    shuffle_indices(order, seed=1, epoch=0)
    mutate_and_execute_epoch(
        soup,
        order,
        seed=1,
        epoch=0,
        mutation_threshold=262_144,
        max_steps=8192,
    )
    assert hashlib.sha256(soup.tobytes()).hexdigest() == (
        "15b95a37cc6f48e526cbd8cd463607039f07da2d5c61714ac19d744e072871e3"
    )
