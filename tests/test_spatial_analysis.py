from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from analysis.spatial import (
    bff_opcode_signature_snapshot,
    block_beta_diversity,
    block_beta_permutation_test,
    neighbor_byte_similarity_test,
    neighbor_identity_test,
    pooled_bff_opcode_beta_test,
    pooled_neighbor_byte_similarity_test,
    write_spatial_report,
)
from soup.config import Config, PairingMode
from soup.substrate.bff import OP_INC, OP_LOOP_START
from soup.simulation import Simulation


def _snapshot(labels: list[list[str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"cell_x": x, "cell_y": y, "content_hash": label}
            for y, row in enumerate(labels)
            for x, label in enumerate(row)
        ]
    )


def test_clustered_hashes_exceed_well_mixed_neighbor_null() -> None:
    clustered = _snapshot([["A"] * 3 + ["B"] * 3 for _ in range(6)])
    result = neighbor_identity_test(
        clustered,
        width=6,
        height=6,
        permutations=999,
        rng=np.random.default_rng(9),
    )

    assert result.observed > result.null_mean
    assert result.excess > 0.15
    assert result.p_value < 0.05


def test_neighbor_byte_similarity_detects_near_copy_clusters() -> None:
    clustered = _snapshot([["A"] * 3 + ["B"] * 3 for _ in range(6)])
    clustered["full_bytes"] = [
        bytes([1, 2, 3, y]) if x < 3 else bytes([9, 8, 7, y])
        for y in range(6)
        for x in range(6)
    ]
    result = neighbor_byte_similarity_test(
        clustered,
        width=6,
        height=6,
        permutations=499,
        rng=np.random.default_rng(11),
    )

    assert result.observed > result.null_mean
    assert result.excess > 0.2
    assert result.p_value < 0.05


def test_pooled_spatial_tests_detect_repeated_cluster_structure() -> None:
    clustered = _snapshot([["A"] * 3 + ["B"] * 3 for _ in range(6)])
    clustered["full_bytes"] = [
        bytes([OP_INC, 2, 3, y]) if x < 3 else bytes([OP_LOOP_START, 8, 7, y])
        for y in range(6)
        for x in range(6)
    ]
    snapshots = [clustered, clustered.copy()]

    byte_result = pooled_neighbor_byte_similarity_test(
        snapshots,
        width=6,
        height=6,
        permutations=199,
        rng=np.random.default_rng(12),
    )
    beta_result = pooled_bff_opcode_beta_test(
        snapshots,
        width=6,
        height=6,
        block_size=3,
        permutations=199,
        rng=np.random.default_rng(13),
    )

    assert byte_result.excess > 0.2
    assert byte_result.p_value < 0.05
    assert beta_result.excess > 0.2
    assert beta_result.p_value < 0.05


def test_bff_opcode_signatures_ignore_non_instruction_data() -> None:
    snapshot = _snapshot([["A", "B"]])
    snapshot["full_bytes"] = [
        bytes([0, OP_INC, 1, OP_LOOP_START]),
        bytes([99, OP_INC, 100, OP_LOOP_START]),
    ]

    signatures = bff_opcode_signature_snapshot(snapshot)

    assert signatures["content_hash"].nunique() == 1
    assert signatures.iloc[0]["content_hash"] == bytes([OP_INC, OP_LOOP_START]).hex()


def test_block_beta_detects_compositionally_distinct_blocks() -> None:
    clustered = _snapshot([["A"] * 3 + ["B"] * 3 for _ in range(6)])
    beta = block_beta_diversity(
        clustered,
        width=6,
        height=6,
        block_size=3,
    )
    test = block_beta_permutation_test(
        clustered,
        width=6,
        height=6,
        block_size=3,
        permutations=499,
        rng=np.random.default_rng(10),
    )
    q1 = test[np.isclose(test["q"], 1.0)].iloc[0]

    assert beta[1.0] == 2.0
    assert float(q1["observed_beta"]) > float(q1["null_mean_beta"])
    assert float(q1["p_value"]) < 0.05


def test_spatial_report_runs_on_stage2_snapshots(tmp_path: Path) -> None:
    config = Config()
    config.run.stage = 2
    config.run.n_ticks = 3
    config.run.epoch_length = 1
    config.substrate.tape_length = 8
    config.substrate.max_steps = 16
    config.world.width = 4
    config.world.height = 4
    config.world.interaction_radius = 1
    config.world.interactions_per_tick = 8
    config.world.pairing_mode = PairingMode.LOCAL_NEIGHBORHOOD.value
    config.symbols.initial_tape_fill = 1.0
    config.logging.flush_interval = 3
    config.logging.tape_snapshot_interval = 1
    run_dir = Simulation(config, run_dir=tmp_path / "spatial").run()

    report = write_spatial_report(
        run_dir,
        block_size=2,
        permutations=19,
        seed=2,
    )

    assert report.exists()
    assert (run_dir / "analysis_spatial.csv").exists()
    assert "Neighbor identity excess" in report.read_text(encoding="utf-8")
