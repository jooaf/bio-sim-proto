from __future__ import annotations

import json
from pathlib import Path

from experiments.replicator_length_study.run_guarded_copier import (
    ALPHABET_SIZE,
    ExperimentConfig,
    functional_mask,
    run,
    seeded_replicator,
)


def test_guarded_copier_has_exact_parameterized_basin() -> None:
    config = ExperimentConfig(
        initialization="seeded",
        credential_length=3,
        population_size=8,
        tape_length=8,
        ticks=8,
        seed=7,
        mutation_rate=0.0,
        execution_budget=8,
        seeded_copies=2,
        metric_interval=1,
        takeover_fraction=0.5,
    )

    assert config.functional_information_bits == 8
    assert config.basin_density == ALPHABET_SIZE**-4
    assert bool(functional_mask(seeded_replicator(config)[None, :], config)[0])


def test_seeded_guarded_copier_validation_records_copy_events(tmp_path: Path) -> None:
    config = ExperimentConfig(
        initialization="seeded",
        credential_length=2,
        population_size=16,
        tape_length=8,
        ticks=32,
        seed=3,
        mutation_rate=0.0,
        execution_budget=8,
        seeded_copies=2,
        metric_interval=1,
        takeover_fraction=0.5,
    )

    output = run(config, tmp_path / "seeded")
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))

    assert summary["aggregate"]["copy_events"] > 0
    assert summary["aggregate"]["validation_passed"] is True
    assert summary["aggregate"]["final_functional_count"] >= 8
