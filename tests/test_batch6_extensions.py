from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from experiments.phase1_probe import run_probe


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_excluded_list_pool_zero_for_listed_symbols(tmp_path: Path) -> None:
    run_dir = run_probe(
        population_size=16,
        epochs=4,
        seed=5,
        mutation_rate=1.0 / 512.0,
        pool_multiplier=2.0,
        pool_mode="excluded_list",
        pool_exclude_symbols=(0, 60, 91),
        callback_interval=2,
        max_steps=256,
        output_dir=tmp_path / "runs",
    )
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["exit_status"] == "success"
    assert manifest["max_conservation_residual"] == 0
    config = manifest["config"]
    assert config["pool_mode"] == "excluded_list"
    assert config["pool_exclude_symbols"] == [0, 60, 91]
    assert "_exlist" in run_dir.name

    symbols = _rows(run_dir / "symbols.csv")
    first_epoch = min(int(row["epoch"]) for row in symbols)
    initial = {
        int(row["symbol"]): int(row["initial_pool_count"])
        for row in symbols
        if int(row["epoch"]) == first_epoch
    }
    for symbol in (0, 60, 91):
        assert initial[symbol] == 0, f"symbol {symbol} must have zero pool stock"
    total = sum(initial.values())
    # Matched multiplier-2 pool total is preserved.
    assert total == int(np.rint(np.bincount(_soup16(16, 5).ravel(), minlength=256) * 2.0).sum())
    aggregate = _rows(run_dir / "aggregate.csv")
    assert all(int(row["max_conservation_residual"]) == 0 for row in aggregate)


def _soup16(population: int, seed: int) -> np.ndarray:
    from experiments.paper_probe import initialize_soup

    return initialize_soup(population, seed)


def test_final_soup_saved(tmp_path: Path) -> None:
    final_soup = tmp_path / "final" / "soup.npy"
    run_dir = run_probe(
        population_size=16,
        epochs=3,
        seed=9,
        mutation_rate=0.0,
        pool_multiplier=2.0,
        callback_interval=1,
        max_steps=64,
        output_dir=tmp_path / "runs",
        final_soup=final_soup,
    )
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["exit_status"] == "success"
    assert manifest["config"]["final_soup"] == str(final_soup)
    assert "soup.npy" in manifest["artifacts"]
    assert final_soup.exists()
    loaded = np.load(final_soup)
    assert loaded.shape == (16, 64)
    assert loaded.dtype == np.uint8

    # The saved soup is a valid continuation input: rerunning from it with the
    # same seed/offset stays conserved.
    continued = run_probe(
        population_size=16,
        epochs=2,
        seed=9,
        mutation_rate=0.0,
        pool_multiplier=2.0,
        callback_interval=1,
        max_steps=64,
        output_dir=tmp_path / "runs2",
        initial_soup=final_soup,
        epoch_offset=3,
    )
    manifest2 = json.loads((continued / "manifest.json").read_text(encoding="utf-8"))
    assert manifest2["exit_status"] == "success"
    assert manifest2["max_conservation_residual"] == 0


def test_distinct_excluded_lists_get_distinct_run_dirs(tmp_path: Path) -> None:
    """Regression: different excluded symbol lists must not share a run dir."""

    first = run_probe(
        population_size=8,
        epochs=2,
        seed=3,
        mutation_rate=0.0,
        pool_multiplier=2.0,
        pool_mode="excluded_list",
        pool_exclude_symbols=(0, 60, 91, 44, 125, 93),
        callback_interval=1,
        max_steps=64,
        output_dir=tmp_path / "runs",
    )
    second = run_probe(
        population_size=8,
        epochs=2,
        seed=3,
        mutation_rate=0.0,
        pool_multiplier=2.0,
        pool_mode="excluded_list",
        pool_exclude_symbols=(0,),
        callback_interval=1,
        max_steps=64,
        output_dir=tmp_path / "runs",
    )
    assert first.name != second.name


def test_excluded_list_validation(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError):
        run_probe(
            population_size=16,
            epochs=2,
            seed=1,
            mutation_rate=0.0,
            pool_multiplier=2.0,
            pool_mode="excluded_list",
            pool_exclude_symbols=(),
            callback_interval=1,
            output_dir=tmp_path / "runs",
        )
    with pytest.raises(ValueError):
        run_probe(
            population_size=16,
            epochs=2,
            seed=1,
            mutation_rate=0.0,
            pool_multiplier=2.0,
            pool_mode="excluded_list",
            pool_exclude_symbols=(0, 0, 1),
            callback_interval=1,
            output_dir=tmp_path / "runs",
        )
    with pytest.raises(ValueError):
        run_probe(
            population_size=16,
            epochs=2,
            seed=1,
            mutation_rate=0.0,
            pool_multiplier=2.0,
            pool_mode="uniform",
            pool_exclude_symbols=(0,),
            callback_interval=1,
            output_dir=tmp_path / "runs",
        )
