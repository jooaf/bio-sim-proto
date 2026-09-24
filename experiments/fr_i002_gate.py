"""Execute the frozen FR-I002 mechanics matrix, without transplantation.

Run: uv run python -m experiments.fr_i002_gate
Artifacts contain no timestamps, timings, or machine-specific paths.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from experiments import phase1_probe as reference
from experiments.paper_probe import initialize_soup, shuffle_indices
from experiments import fr_i002_provenance as instrumented

U8 = NDArray[np.uint8]
I64 = NDArray[np.int64]
ROOT = Path(__file__).resolve().parents[1]
PIN = '3805a0d4987f2c24ba70fe25e9b688a9f40cb137'
PAPER_PIN = 'ee2b67f4ce17d8f78842e5b778abf48d2e32f0e5'
BUDGETS = (1, 2, 16, 128, 1024, 8192)
RATES = (0.0, 0.1, 0.27555027572734614, 1.0)
FIELDS = ('pool', 'withdrawals', 'returns', 'execution_blocked', 'mutation_blocked',
          'friction_blocked', 'cross_a_to_b', 'cross_b_to_a', 'counter')


def mix(value: int) -> int:
    """Independent unsigned SplitMix64 for fixture construction."""
    mask = (1 << 64) - 1
    value = (value + 0x9E3779B97F4A7C15) & mask
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & mask
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & mask
    return value ^ (value >> 31)


def pattern(key: int, offset: int, size: int, mask: int) -> U8:
    return np.array([mix(key ^ mix(offset + b)) & mask for b in range(size)], dtype=np.uint8)


def verify_pin() -> None:
    for name, expected in (('phase1_probe.py', PIN), ('paper_probe.py', PAPER_PIN)):
        source = (ROOT / 'experiments' / name).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest()
        if actual != expected:
            raise AssertionError(f'{name} reference changed: {actual}')
    prereg = 'reports/fr_i002_conserved_provenance_parity_preregistration.md'
    committed = subprocess.check_output(['git', 'show', f'HEAD:{prereg}'], cwd=ROOT)
    assert committed == (ROOT / prereg).read_bytes(), 'preregistration differs from HEAD'


@dataclass
class State:
    data: U8
    labels: U8
    arrays: dict[str, I64]
    order: NDArray[np.uint32]

    @classmethod
    def create(cls, data: U8, labels: U8, pool: I64, counter: int = 0) -> State:
        assert data.shape == labels.shape and labels.dtype == np.uint8
        assert np.all(labels <= 1) and not np.shares_memory(data, labels)
        arrays: dict[str, I64] = {name: np.zeros(256, dtype=np.int64) for name in FIELDS}
        arrays['pool'] = pool.copy()
        arrays['counter'] = np.array([counter], dtype=np.int64)
        return cls(data.copy(), labels.copy(), arrays,
                   np.arange(len(data) if data.ndim == 2 else 2, dtype=np.uint32))

    def copy(self, invert: bool = False) -> State:
        return State(self.data.copy(), self.labels.copy() ^ np.uint8(invert),
                     {k: v.copy() for k, v in self.arrays.items()}, self.order.copy())

    def interaction(self, provenance: bool, budget: int, threshold: int, seed: int) -> tuple[int, ...]:
        a = self.arrays
        fn: Any = instrumented.execute_bff_provenance if provenance else reference.execute_bff_conserved
        leading = (self.data, self.labels) if provenance else (self.data,)
        return tuple(fn(*leading, a['pool'], a['withdrawals'], a['returns'],
                        a['execution_blocked'], a['cross_a_to_b'], a['cross_b_to_a'],
                        budget, a['friction_blocked'], threshold, seed, a['counter']))

    def epoch(self, provenance: bool, seed: int, epoch: int, mutation: int,
              friction: int, budget: int = 8192) -> tuple[int, ...]:
        a = self.arrays
        fn: Any = (instrumented.mutate_and_execute_provenance_epoch if provenance
                   else reference.mutate_and_execute_conserved_epoch)
        leading = (self.data, self.labels) if provenance else (self.data,)
        return tuple(fn(*leading, self.order, a['pool'], seed, epoch, mutation, budget,
                        a['withdrawals'], a['returns'], a['execution_blocked'],
                        a['mutation_blocked'], a['friction_blocked'], a['cross_a_to_b'],
                        a['cross_b_to_a'], friction, seed, a['counter']))

    def digest(self, metrics: tuple[int, ...]) -> bytes:
        return b''.join([self.data.tobytes(), self.labels.tobytes(), self.order.astype('<u4').tobytes(),
                         *(self.arrays[k].astype('<i8').tobytes() for k in FIELDS),
                         np.array(metrics, dtype='<i8').tobytes()])


def equal(actual: State, expected: State, context: str, labels: bool = True) -> None:
    assert np.array_equal(actual.data, expected.data), f'{context}: data'
    assert np.array_equal(actual.order, expected.order), f'{context}: order'
    for name in FIELDS:
        assert np.array_equal(actual.arrays[name], expected.arrays[name]), f'{context}: {name}'
    assert np.all(actual.labels <= 1), f'{context}: nonbinary labels'
    if labels:
        assert np.array_equal(actual.labels, expected.labels), f'{context}: labels'


def exchange(expected: State, index: int, value: int, label: int, outcome: str,
             mutation: bool = False, source: int | None = None) -> int:
    """Fixture oracle: declarative expected exchange, independent of either kernel."""
    old = int(expected.data.flat[index])
    if old == value:
        return 0
    a = expected.arrays
    a['counter'][0] += 1
    if outcome != 'success':
        field = 'friction_blocked' if outcome == 'friction' else (
            'mutation_blocked' if mutation else 'execution_blocked')
        a[field][value] += 1
        return 3 if outcome == 'friction' else 2
    expected.data.flat[index] = value
    expected.labels.flat[index] = label
    a['pool'][value] -= 1
    a['pool'][old] += 1
    a['withdrawals'][value] += 1
    a['returns'][old] += 1
    if source is not None and source // 64 != index // 64:
        a['cross_a_to_b' if source < 64 else 'cross_b_to_a'][value] += 1
    return 1


@dataclass
class Fixture:
    name: str
    initial: State
    expected: State
    budget: int
    threshold: int
    seed: int
    metrics: tuple[int, ...]
    heads: tuple[int, int] = (0, 0)
    write: tuple[int, int, int, int] | None = None  # destination, value, label, outcome


def directed_fixtures() -> list[Fixture]:
    records = []
    for op, changed, src_label, dst_label, outcome in itertools.product(
            '.,+-', (False, True), (0, 1), (0, 1), ('success', 'scarcity', 'friction')):
        if op in '+-' and not changed:  # arithmetic always changes a uint8 value
            continue
        for cross in ((False, True) if op in '.,' else (False,)):
            prefix = ('{' if op == '.' else '<') if cross else (
                '<<{' if op == '.' else '<{{' if op == ',' else '<')
            src, dst = (0, 127) if cross else (126, 127)
            if op in '+-':
                src = dst = 127
            data = np.zeros(128, dtype=np.uint8)
            data[:len(prefix) + 1] = np.frombuffer((prefix + op).encode(), dtype=np.uint8)
            if op in '.,':
                value = int(data[src]) if cross else 77
                data[src] = value
                data[dst] = (value + int(changed)) & 255
            else:
                data[dst] = 255 if op == '+' else 0
                value = 0 if op == '+' else 255
            labels = np.zeros(128, dtype=np.uint8)
            labels[src] = src_label
            labels[dst] = dst_label
            pool = np.full(256, 4, dtype=np.int64)
            pool[value] = 0 if outcome in ('scarcity', 'friction') else 4
            start = State.create(data, labels, pool, 65535)
            expected = start.copy()
            label = src_label if op in '.,' else dst_label
            result = exchange(expected, dst, value, label, outcome,
                              source=src if op in '.,' else None)
            metrics = (len(prefix) + 1, int(result < 2), int(result == 2), int(result == 3),
                       int(cross and result == 1), int(cross and result >= 2))
            heads = (src, dst) if op == '.' else (dst, src) if op == ',' else (dst, 0)
            records.append(Fixture(f'{op}-{changed}-{src_label}-{dst_label}-{outcome}-{cross}',
                                   start, expected, len(prefix) + 1,
                                   (1 << 30) if outcome == 'friction' else 0, 202618000,
                                   metrics, heads, (dst, value, label, result)))
    # Reverse cross-half copies also freeze B-to-A counters and self-modifying writes.
    for op, changed, src_label, dst_label, outcome in itertools.product(
            '.,', (False, True), (0, 1), (0, 1), ('success', 'scarcity', 'friction')):
        prefix = '<' if op == '.' else '{'
        data = np.zeros(128, dtype=np.uint8)
        data[:2] = np.frombuffer((prefix + op).encode(), dtype=np.uint8)
        value = 77 if changed else ord(prefix)
        data[127] = value
        labels = np.zeros(128, dtype=np.uint8)
        labels[127], labels[0] = src_label, dst_label
        pool = np.full(256, 4, dtype=np.int64)
        pool[value] = 4 if outcome == 'success' else 0
        start = State.create(data, labels, pool, 65535)
        expected = start.copy()
        result = exchange(expected, 0, value, src_label, outcome, source=127)
        records.append(Fixture(f'reverse-{op}-{changed}-{src_label}-{dst_label}-{outcome}',
                               start, expected, 2, (1 << 30) if outcome == 'friction' else 0,
                               202618000, (2, int(result < 2), int(result == 2), int(result == 3),
                                          int(result == 1), int(result >= 2)),
                               (127, 0) if op == '.' else (0, 127), (0, value, src_label, result)))
    # Literal programs with independently enumerated execution paths.
    for name, program, budget, steps, successes in [
        ('nested-arithmetic', '<+[[-]]', 7, 7, 2),
        ('nested-skip', '<[[]]', 128, 125, 0),
        ('unmatched-open', '<[', 128, 2, 0),
        ('unmatched-close', ']', 128, 1, 0),
        ('self-modification', '+', 1, 1, 1),
        ('head0-wrap', '<>+', 3, 3, 1),
        ('head1-wrap', '{}.', 3, 3, 1),
        *((f'budget-{b}', '[]', b, b, 0) for b in BUDGETS),
    ]:
        data = np.zeros(128, dtype=np.uint8)
        data[:len(program)] = np.frombuffer(program.encode(), dtype=np.uint8)
        start = State.create(data, pattern(55, 0, 128, 1), np.full(256, 4096, dtype=np.int64))
        expected = start.copy()
        if name == 'nested-arithmetic':
            exchange(expected, 127, 1, int(start.labels[127]), 'success')
            exchange(expected, 127, 0, int(start.labels[127]), 'success')
        if name in ('self-modification', 'head0-wrap'):
            exchange(expected, 0, int(data[0]) + 1, int(start.labels[0]), 'success')
        records.append(Fixture(name, start, expected, budget, 0, 202618000,
                               (steps, successes, 0, 0, 0, 0)))
    return records


def check_fixture(f: Fixture) -> None:
    for provenance in (False, True, True):
        actual = f.initial.copy()
        metrics = actual.interaction(provenance, f.budget, f.threshold, f.seed)
        assert metrics == f.metrics, (f.name, metrics, f.metrics)
        equal(actual, f.expected, f.name, labels=provenance)
    inverted = f.initial.copy(invert=True)
    assert inverted.interaction(True, f.budget, f.threshold, f.seed) == f.metrics, f.name
    equal(inverted, f.expected, f.name + '/inverted', labels=False)
    if f.write is not None:
        dst, value, label, result = f.write
        for provenance in (False, True, True):
            actual = f.initial.copy()
            a = actual.arrays
            fn: Any = (instrumented.provenance_write_with_friction if provenance
                       else reference.conserved_write_with_friction)
            leading = (actual.data, actual.labels, label) if provenance else (actual.data,)
            got = fn(*leading, dst, value, a['pool'], a['withdrawals'], a['returns'],
                     a['execution_blocked'], a['friction_blocked'], f.threshold, f.seed, a['counter'])
            assert got == result, f.name
            # The primitive does not update interaction cross-direction counters.
            expected = f.expected.copy()
            expected.arrays['cross_a_to_b'][:] = 0
            expected.arrays['cross_b_to_a'][:] = 0
            equal(actual, expected, f.name + '/write', labels=provenance)


def mutation_values(seed: int, population: int, pair: int = 0) -> tuple[U8, list[int]]:
    epoch_seed = mix(mix(seed) ^ mix(0))
    values = [mix(((population * epoch_seed + pair) * 128 + b) & ((1 << 64) - 1))
              for b in range(128)]
    return np.array([x & 255 for x in values], dtype=np.uint8), [(x >> 8) & ((1 << 30) - 1) for x in values]


def epoch_fixtures() -> list[tuple[str, State, State, int, int, int, int, tuple[int, ...]]]:
    records: list[tuple[str, State, State, int, int, int, int, tuple[int, ...]]] = []
    seed = 202618000
    values, _ = mutation_values(seed, 2)
    for mode in ('success', 'equal', 'scarcity', 'friction'):
        data = values.copy() if mode == 'equal' else values ^ np.uint8(128)
        start = State.create(data.reshape(2, 64), np.ones((2, 64), dtype=np.uint8),
                             np.full(256, 4096 if mode in ('success', 'equal') else 0, dtype=np.int64))
        expected = start.copy()
        for b in range(128):
            exchange(expected, b, int(values[b]), 0, 'success' if mode == 'equal' else mode, mutation=True)
        metrics = (0, 0, 0, 0, 128 if mode in ('success', 'equal') else 0,
                   128 if mode == 'scarcity' else 0, 128 if mode == 'friction' else 0, 0, 0)
        records.append((f'mutation-{mode}', start, expected, seed, 1 << 30,
                        (1 << 30) if mode == 'friction' else 0, 0, metrics))
    # Select exactly byte 127 by a fixed independently constructed mutation stream.
    seed = 202618000
    while True:
        values, draws = mutation_values(seed, 2)
        if draws.index(min(draws)) == 127 and draws.count(min(draws)) == 1:
            break
        seed += 1
    data = np.zeros((2, 64), dtype=np.uint8)
    data.flat[:4] = np.frombuffer(b'<<{.', dtype=np.uint8)
    data.flat[126] = (int(values[127]) + 1) & 255
    data.flat[127] = (int(values[127]) + 2) & 255
    start = State.create(data, np.ones((2, 64), dtype=np.uint8), np.full(256, 4096, dtype=np.int64))
    expected = start.copy()
    exchange(expected, 127, int(values[127]), 0, 'success', mutation=True)
    exchange(expected, 127, int(data.flat[126]), 1, 'success', source=126)
    records.append(('mutation-then-copy', start, expected, seed, draws[127] + 1, 0, 4,
                    (4, 1, 0, 0, 1, 0, 0, 0, 0)))
    data = np.zeros((4, 64), dtype=np.uint8)
    data[2, :2] = np.frombuffer(b'{.', dtype=np.uint8)
    data[3, :2] = np.frombuffer(b'<,', dtype=np.uint8)
    data[0, 63] = 77
    data[1, 63] = 88
    # Four distinct position-sensitive patterns identify both halves of each pair.
    # Source labels differ, and each copy flips its destination label.
    label_rows = ('01' * 31 + '00', '0011' * 16, '10010110' * 8, '01101001' * 8)
    labels = np.array([[int(bit) for bit in row] for row in label_rows], dtype=np.uint8)
    start = State.create(data, labels, np.full(256, 4096, dtype=np.int64))
    start.order[:] = [2, 0, 3, 1]
    expected = start.copy()
    # Both joint programs copy first-half byte zero to second-half byte 63.
    for source, dest in ((128, 63), (192, 127)):
        exchange(expected, dest, int(data.flat[source]), int(labels.flat[source]), 'success')
    # Full literal post-scatter oracle in physical tape order; no kernel-derived labels.
    # [2,0] copies label 1 to tape 0 byte 63; [3,1] copies label 0 to tape 1 byte 63.
    expected_rows = ('01' * 32, '0011' * 15 + '0010', '10010110' * 8, '01101001' * 8)
    expected.labels[:] = np.array([[int(bit) for bit in row] for row in expected_rows], dtype=np.uint8)
    expected.arrays['cross_a_to_b'][123] = 1
    expected.arrays['cross_a_to_b'][60] = 1
    records.append(('nonidentity-gather-scatter', start, expected, 202618000, 0, 0, 2,
                    (4, 2, 0, 0, 0, 0, 0, 2, 0)))
    return records


def check_epoch_fixture(record: tuple[str, State, State, int, int, int, int, tuple[int, ...]]) -> None:
    name, start, expected, seed, mutation, friction, budget, metrics = record
    for provenance in (False, True, True):
        actual = start.copy()
        got = actual.epoch(provenance, seed, 0, mutation, friction, budget)
        assert got == metrics, (name, got, metrics)
        equal(actual, expected, name, labels=provenance)
    inverted = start.copy(invert=True)
    assert inverted.epoch(True, seed, 0, mutation, friction, budget) == metrics, name
    equal(inverted, expected, name + '/inverted', labels=False)


def random_state(case: int) -> State:
    data = pattern(0xAC008100, case * 128, 128, 255)
    labels = pattern(0xAC008101, case * 128, 128, 1)
    regime = (case // 4) % 3
    pool = np.full(256, 1 if regime == 1 else 4096, dtype=np.int64)
    if regime == 2:
        pool[pattern(0xAC008102, case * 256, 256, 3) == 0] = 0
    return State.create(data, labels, pool, (0, 1, 65535, 2147483647)[(case // 12) % 4])


def check_random(case: int) -> bytes:
    start = random_state(case)
    states = [start.copy(), start.copy(), start.copy(), start.copy(invert=True)]
    metrics = [s.interaction(i != 0, BUDGETS[(case // 48) % 6],
                             round(RATES[case % 4] * (1 << 30)), 202618000 + case)
               for i, s in enumerate(states)]
    for i in range(1, 4):
        assert metrics[i] == metrics[0], f'interaction {case}: metrics'
        equal(states[i], states[0], f'interaction {case}', labels=False)
    equal(states[1], states[2], f'interaction {case}: repeat')
    return states[1].digest(metrics[1])


def check_epochs(seed: int, mutation: float, friction: float, multiplier: int) -> str:
    init: Any = initialize_soup
    shuffle: Any = shuffle_indices
    data = init(32, seed)
    labels = pattern(0xAC008200, seed * 2048, 2048, 1).reshape(32, 64)
    counts = np.bincount(data.ravel(), minlength=256).astype(np.int64)
    start = State.create(data, labels, counts * multiplier)
    total = counts * (multiplier + 1)
    states = [start.copy(), start.copy(), start.copy(), start.copy(invert=True)]
    digest = hashlib.sha256()
    for epoch in range(100):
        metrics = []
        for i, state in enumerate(states):
            shuffle(state.order, seed, epoch)
            metrics.append(state.epoch(i != 0, seed, epoch, round(mutation * (1 << 30)),
                                       round(friction * (1 << 30))))
            residual = np.bincount(state.data.ravel(), minlength=256) + state.arrays['pool'] - total
            assert np.all(residual == 0), f'{seed}/{epoch}: conservation'
            assert np.array_equal(state.arrays['pool'], start.arrays['pool']
                                  - state.arrays['withdrawals'] + state.arrays['returns']), 'ledger balance'
        for i in range(1, 4):
            assert metrics[i] == metrics[0], f'{seed}/{epoch}: metrics'
            equal(states[i], states[0], f'{seed}/{epoch}', labels=False)
        equal(states[1], states[2], f'{seed}/{epoch}: repeat')
        digest.update(states[1].digest(metrics[1]))
    return digest.hexdigest()


def state_record(state: State) -> dict[str, Any]:
    """Lossless compact fixture encoding: modal array value plus indexed exceptions."""
    arrays = {}
    for name, values in state.arrays.items():
        symbols, counts = np.unique(values, return_counts=True)
        default = int(symbols[int(np.argmax(counts))])
        arrays[name] = dict(size=len(values), default=default,
                            exceptions={str(i): int(v) for i, v in enumerate(values) if v != default})
    return dict(bytes_hex=state.data.tobytes().hex(), labels_hex=state.labels.tobytes().hex(),
                shape=list(state.data.shape), order=state.order.tolist(), arrays=arrays)


def run_gate() -> dict[str, Any]:
    verify_pin()
    directed = directed_fixtures()
    epochs = epoch_fixtures()
    for fixture in directed:
        check_fixture(fixture)
    for record in epochs:
        check_epoch_fixture(record)
    fixture_records = [dict(name=f.name, initial=state_record(f.initial), expected=state_record(f.expected),
                            budget=f.budget, threshold=f.threshold, seed=f.seed, metrics=f.metrics,
                            heads_at_write=f.heads, write=f.write) for f in directed]
    fixture_records.extend(dict(name=n, initial=state_record(s), expected=state_record(e), seed=seed,
                                mutation_threshold=m, friction_threshold=f, budget=b, metrics=metrics)
                           for n, s, e, seed, m, f, b, metrics in epochs)
    digest = hashlib.sha256()
    for case in range(1000):
        digest.update(check_random(case))
    configurations = []
    for seed, mutation, friction, multiplier in itertools.product(
            range(202618000, 202618005), (0.0, 1 / 4096), (0.0, RATES[2]), (2, 16)):
        configurations.append(dict(seed=seed, mutation=mutation, friction=friction, multiplier=multiplier,
                                   trajectory_sha256=check_epochs(seed, mutation, friction, multiplier)))
    fixture_json = json.dumps(fixture_records, sort_keys=True, separators=(',', ':'))
    (ROOT / 'reports/fr_i002_directed_fixtures.json').write_text(fixture_json + '\n')
    verify_pin()
    return dict(gate='FR-I002', mechanics='PASS', production_blob=PIN, paper_probe_blob=PAPER_PIN,
                directed_interactions=len(directed), directed_writes=sum(f.write is not None for f in directed),
                epoch_label_fixtures=len(epochs), fixture_sha256=hashlib.sha256(fixture_json.encode()).hexdigest(),
                randomized_interactions=1000, interaction_sha256=digest.hexdigest(),
                configurations=configurations, epochs_per_configuration=100,
                complete_instrumented_repeats=2, inverted_label_mechanics_runs=1,
                conservation_residual=0, transplantation_launched=False,
                acceptance='Pending full existing test suite checks.')


def main() -> None:
    report = ROOT / 'reports/fr_i002_mechanics_parity.json'
    decision = ROOT / 'reports/fr_i002_mechanics_decision.md'
    result: dict[str, Any] = {'gate': 'FR-I002', 'mechanics': 'NOT_COMPLETED',
                              'transplantation_launched': False}
    try:
        result = run_gate()
        print('Mechanics matrix passed; checking mypy and both full test suites.', flush=True)
        checks = {}
        commands = {
            'mypy': ['uv', 'run', 'mypy', 'experiments/fr_i002_provenance.py',
                     'experiments/fr_i002_gate.py', 'tests/test_fr_i002_provenance.py'],
            'root_tests': ['uv', 'run', 'pytest'],
            'organism_tests': ['uv', 'run', '--project', 'organism-sim', '--group', 'dev',
                              'pytest', 'organism-sim/tests'],
        }
        for name, command in commands.items():
            check = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            if check.returncode:
                raise AssertionError(f'{name} failed\n{check.stdout}\n{check.stderr}')
            counts = re.findall(r'(\d+) passed', check.stdout)
            checks[name] = dict(status='PASS', command=command,
                                passed=int(counts[-1]) if counts else None)
            print(f'{name}: PASS', flush=True)
        result['checks'] = checks
        result['acceptance'] = 'PASS'
        result['source_sha256'] = {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
                'experiments/fr_i002_provenance.py', 'experiments/fr_i002_gate.py',
                'tests/test_fr_i002_provenance.py',
                'experiments/phase1_probe.py', 'experiments/paper_probe.py',
                'reports/fr_i002_conserved_provenance_parity_preregistration.md')}
        verify_pin()
    except Exception as error:
        result['acceptance'] = 'FAIL'
        result['failure'] = str(error)
        report.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        decision.write_text('# FR-I002 mechanics decision: FAIL\n\n'
                            'Stop before transplantation. See fr_i002_mechanics_parity.json.\n')
        raise
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    decision.write_text(
        '# FR-I002 mechanics decision: PASS\n\n'
        f"Passed {result['directed_interactions']} independently specified interaction fixtures, "
        f"{result['directed_writes']} directed write fixtures, and "
        f"{result['epoch_label_fixtures']} forced mutation/gather-scatter epoch fixtures. "
        'The nonidentity fixture uses four distinct position-sensitive binary label patterns '
        'and a complete independently specified post-scatter label array; regression tests '
        'reject first-pair label reuse during either gathering or scattering. '
        'All 1,000 frozen randomized interactions and all 40 configurations × 100 epochs '
        'matched every mechanics field. Two complete instrumented runs agreed exactly; '
        'inverting initial labels preserved mechanics. Conservation residuals were zero.\n\n'
        f"Full suites: {checks['root_tests']['passed']} root tests and "
        f"{checks['organism_tests']['passed']} organism-sim tests passed. "
        'Strict mypy passed for both new modules and the focused tests.\n\n'
        'Production `phase1_probe.py` remains pinned to Git blob `' + PIN + '`. '
        '`paper_probe.py` (including initialization and shuffling) is verified against Git blob `'
        + PAPER_PIN + '`. '
        'No registries were changed. Fixture records are in `fr_i002_directed_fixtures.json`; '
        'matrix checksums and validation commands are in `fr_i002_mechanics_parity.json`. '
        'Reproduce with `uv run python -m experiments.fr_i002_gate`.\n\n'
        'The preregistered next step is a new held-out composition-preserving transplantation '
        'preregistration using the frozen 0.75 threshold and prospective descendant counts. '
        'No transplantation was launched. This pass validates observational instrumentation '
        'only; it does not establish biological ancestry, persistence, heredity, organisms, '
        'adaptation, ecology, or organization, and does not reclassify AC-P006.\n')
    print('FR-I002 acceptance PASS', flush=True)


if __name__ == '__main__':
    main()
