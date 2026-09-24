"""Independent label fixtures and complete FR-I002 mechanics acceptance matrix."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from experiments import fr_i002_gate as gate
from experiments.fr_i002_gate import (
    Fixture, State, check_epoch_fixture, check_epochs, check_fixture, check_random,
    directed_fixtures, epoch_fixtures, verify_pin, RATES,
)


def test_pinned_reference() -> None:
    verify_pin()


@pytest.mark.parametrize('name', ('phase1_probe.py', 'paper_probe.py'))
def test_changed_reference_rejected(name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / 'experiments'
    directory.mkdir()
    for filename in ('phase1_probe.py', 'paper_probe.py'):
        contents = (gate.ROOT / 'experiments' / filename).read_bytes()
        (directory / filename).write_bytes(contents + (b'\n' if filename == name else b''))
    monkeypatch.setattr(gate, 'ROOT', tmp_path)
    with pytest.raises(AssertionError, match=name + ' reference changed'):
        verify_pin()


@pytest.mark.parametrize('routing', ('gather', 'scatter'))
def test_nonidentity_fixture_rejects_first_pair_reuse(
    routing: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = next(r for r in epoch_fixtures() if r[0] == 'nonidentity-gather-scatter')
    start, expected = record[1:3]
    assert len({row.tobytes() for row in start.labels}) == 4
    assert all(np.unique(row).tolist() == [0, 1] for row in start.labels)
    assert expected.labels[0, 63] == 1 and expected.labels[1, 63] == 0
    original_epoch = State.epoch

    def wrong_routing(
        self: State, provenance: bool, seed: int, epoch: int, mutation: int,
        friction: int, budget: int = 8192,
    ) -> tuple[int, ...]:
        if provenance and routing == 'gather':
            self.labels[self.order[2:4]] = self.labels[self.order[:2]].copy()
        metrics = original_epoch(self, provenance, seed, epoch, mutation, friction, budget)
        if provenance and routing == 'scatter':
            self.labels[self.order[2:4]] = self.labels[self.order[:2]].copy()
        # The injected defect affects only labels; mechanics still pass exactly.
        gate.equal(self, expected, 'wrong routing mechanics', labels=False)
        return metrics

    monkeypatch.setattr(State, 'epoch', wrong_routing)
    with pytest.raises(AssertionError, match='nonidentity-gather-scatter: labels'):
        check_epoch_fixture(record)


@pytest.mark.parametrize('fixture', directed_fixtures(), ids=lambda f: f.name)
def test_directed(fixture: Fixture) -> None:
    check_fixture(fixture)


@pytest.mark.parametrize('index', range(6))
def test_epoch_labels(index: int) -> None:
    check_epoch_fixture(epoch_fixtures()[index])


def test_all_randomized_interactions() -> None:
    for case in range(1000):
        check_random(case)


@pytest.mark.parametrize('seed', range(202618000, 202618005))
@pytest.mark.parametrize('mutation', (0.0, 1 / 4096))
@pytest.mark.parametrize('friction', (0.0, RATES[2]))
@pytest.mark.parametrize('multiplier', (2, 16))
def test_full_epoch_matrix(seed: int, mutation: float, friction: float, multiplier: int) -> None:
    check_epochs(seed, mutation, friction, multiplier)
