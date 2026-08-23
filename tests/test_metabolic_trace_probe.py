from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from experiments.metabolic_trace_probe import run_trace
from experiments.phase1_probe import run_probe


def test_token_trace_is_conserved_and_records_reacquisition(tmp_path: Path) -> None:
    run_dir = run_trace(
        population_size=32,
        epochs=200,
        seed=2,
        mutation_rate=1.0 / 4096.0,
        pool_multiplier=0.5,
        callback_interval=20,
        output_dir=tmp_path,
        sample_denominator=1,
        max_events=100_000,
        max_steps=512,
    )

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["exit_status"] == "success"
    assert manifest["max_conservation_residual"] == 0
    assert manifest["token_validation_passed"] is True
    assert manifest["total_reacquisitions"] > 0
    assert manifest["cross_tape_reacquisitions"] > 0
    assert manifest["event_overflow"] == 0

    events = pd.read_csv(run_dir / "sampled_token_events.csv")
    assert not events.empty
    assert (events["pool_residence_interactions"] >= 0).all()
    assert (events["donor_tape"] != events["receiver_tape"]).any()

    aggregate = pd.read_csv(run_dir / "aggregate.csv")
    assert (aggregate["max_conservation_residual"] == 0).all()
    assert aggregate["token_validation_passed"].all()


def test_token_labels_do_not_change_byte_level_trajectory(tmp_path: Path) -> None:
    traced = run_trace(
        population_size=32,
        epochs=50,
        seed=3,
        mutation_rate=1.0 / 4096.0,
        pool_multiplier=2.0,
        callback_interval=10,
        output_dir=tmp_path / "trace",
        sample_denominator=8,
        max_events=10_000,
        max_steps=512,
    )
    baseline = run_probe(
        population_size=32,
        epochs=50,
        seed=3,
        mutation_rate=1.0 / 4096.0,
        pool_multiplier=2.0,
        callback_interval=10,
        output_dir=tmp_path / "baseline",
        max_steps=512,
    )

    traced_rows = pd.read_csv(traced / "aggregate.csv")
    baseline_rows = pd.read_csv(baseline / "aggregate.csv")
    columns = [
        "epoch",
        "character_reads",
        "byte_entropy",
        "brotli_size",
        "compressed_bpb",
        "high_order_entropy",
        "pool_total",
        "pool_entropy",
        "pool_jsd_from_initial",
        "zero_pool_symbols",
    ]
    pd.testing.assert_frame_equal(traced_rows[columns], baseline_rows[columns])
