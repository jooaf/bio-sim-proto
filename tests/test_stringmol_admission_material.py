"""Adversarial material-layer tests, not a full population/VM replay gate."""
from copy import deepcopy
from typing import Any

import pytest

from experiments.stringmol import admission_material as material
from experiments.stringmol import analyze_conservation as c
from experiments.stringmol.retirement_material import histogram


def initial() -> dict[str, Any]:
    buffer = b'A\0Z'.ljust(c.MAXL0, b'\0')
    counts = histogram({0: buffer})
    return {'maxl0': c.MAXL0, 'buffers': {'0': buffer.hex()},
            'pool': [0] * 33, 'molecular': counts, 'total': counts.copy()}


def eviction() -> dict[str, str]:
    return dict(tick='0', index='1', event='EVICT', outcome='REMOVED', before_ids='0',
                after_ids='', changes='0:0:41:00;0:2:5A:00', proposal='')


def test_hidden_eviction_has_separate_ledger() -> None:
    replay = material.Replay(initial())
    replay.step(eviction())
    assert replay.evictions == 1 and not replay.buffers
    assert replay.eviction_returns == initial()['total'] == replay.arrays['pool']
    assert replay.molecular == [0] * 33
    assert replay.exposure == replay.retirements == 0
    assert not any(replay.retirement_returns)
    for key in ('decay_returns', 'decay_removed', 'decay_to_pool', 'decay_to_waste', 'waste',
                'failed_placement_returns', 'cleavage_discard_returns'):
        assert replay.arrays[key] == [0] * 33


@pytest.mark.parametrize('patch', [
    {'event': 'RETIRE'}, {'event': 'unknown'}, {'index': '2'}, {'index': '01'},
    {'tick': '-1'}, {'outcome': 'PLACED'}, {'before_ids': '1'}, {'before_ids': '0;0'},
    {'after_ids': '0'}, {'proposal': '0:0:41:00'}, {'changes': '0:0:41:00'},
    {'changes': '0:0:42:00;0:2:5A:00'}, {'changes': '0:2:5A:00;0:0:41:00'}, {'extra': ''},
])
def test_corruption_is_terminal(patch: dict[str, str]) -> None:
    replay = material.Replay(initial())
    with pytest.raises(ValueError):
        replay.step(eviction() | patch)
    with pytest.raises(ValueError, match='already failed'):
        replay.step(eviction())
    with pytest.raises(ValueError, match='already failed'):
        replay.checkpoint({})


def test_duplicate_eviction_rejected() -> None:
    replay = material.Replay(initial())
    replay.step(eviction())
    with pytest.raises(ValueError, match='unknown/dead'):
        replay.step(eviction() | {'index': '2'})


def test_empty_visible_victim_rejected_even_with_hidden_material() -> None:
    state = initial()
    buffer = b'\0\0Z'.ljust(c.MAXL0, b'\0')
    state.update(buffers={'0': buffer.hex()}, molecular=histogram({0: buffer}), total=histogram({0: buffer}))
    replay = material.Replay(state)
    with pytest.raises(ValueError, match='empty-visible'):
        replay.step(eviction() | {'changes': '0:2:5A:00'})


@pytest.mark.parametrize('field', ['evictions', 'eviction_returns'])
def test_eviction_overflow_poisoning(field: str) -> None:
    replay = material.Replay(initial())
    if field == 'evictions':
        replay.evictions = c.LIMIT
    else:
        replay.eviction_returns[c.ALPHABET.index('A')] = c.LIMIT
    with pytest.raises(ValueError):
        replay.step(eviction())
    assert replay.failed


@pytest.mark.parametrize('patch', [
    {'maxl0': 2000}, {'pool': [0] * 32}, {'pool': [True] * 33}, {'total': [0] * 33},
    {'molecular': [0] * 33}, {'buffers': {'00': b'A'.ljust(c.MAXL0, b'\0').hex()}},
    {'buffers': {'0': b'A'.hex()}}, {'pool': [-1] * 33}, {'total': [c.LIMIT + 1] * 33},
])
def test_invalid_initial_state(patch: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        material.Replay(initial() | patch)


def test_initial_state_is_not_a_mutable_external_oracle() -> None:
    state = initial()
    expected = deepcopy(state)
    replay = material.Replay(state)
    state['total'][0] += 1
    state['buffers'].clear()
    replay.step(eviction())
    assert replay.initial == expected


def test_bad_checkpoint_cannot_be_retried() -> None:
    replay = material.Replay(initial())
    with pytest.raises(ValueError):
        replay.checkpoint({})
    with pytest.raises(ValueError, match='already failed'):
        replay.step(eviction())


def test_sequestering_not_an_admission_route() -> None:
    with pytest.raises(ValueError, match='exact recycling'):
        material.Replay(initial(), 'sequester')
