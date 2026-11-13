"""Directed real native opcodes; not a population experiment or full replay gate."""
import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

import pytest

from experiments.stringmol import admission_design as design, admission_journal as journal, admission_material
from experiments.stringmol.retirement_material import histogram
from experiments.stringmol import admission_boundary, admission_numeric, admission_replay, analyze_conservation as conservation
from experiments.stringmol.native_testing import checked, runtime_environment, sanitizer_flags, verify_linkage, verify_native_agent

ROOT = Path(__file__).resolve().parents[1]
SOURCE = os.environ.get('SM_ADMISSION_NATIVE_SOURCE')
pytestmark = pytest.mark.skipif(not SOURCE, reason='explicit native interpreter qualification only')


@pytest.fixture(scope='module')
def interpreter(tmp_path_factory: pytest.TempPathFactory) -> Path:
    assert SOURCE
    baseline = Path(SOURCE).resolve(strict=True)
    verify_native_agent(baseline)
    root = tmp_path_factory.mktemp('admission-interpreter')
    source = root / 'src'
    shutil.copytree(baseline, source)
    native = ROOT / 'experiments/stringmol/native'
    checked(['git', 'apply', str(native / 'admission_integration.patch')], root, 'apply-integration')
    (root / 'native').mkdir()
    for name in ('admission_adapter.h', 'admission_transaction.h', 'admission_journal.h'):
        shutil.copyfile(native / name, source / name)
        shutil.copyfile(native / name, root / 'native' / name)
    shutil.copyfile(baseline.parent / 'config/ALXII.mtx', root / 'ALXII.mtx')
    shutil.copyfile(ROOT / 'tests/stringmol_admission_interpreter.cpp', root / 'fixture.cpp')
    shutil.copyfile(ROOT / 'tests/stringmol_admission_fault_witness.h', root / 'stringmol_admission_fault_witness.h')
    inputs = [p for p in source.iterdir() if p.is_file()] + [root / 'fixture.cpp', root / 'stringmol_admission_fault_witness.h', root / 'ALXII.mtx']
    (root / 'inputs.json').write_text(json.dumps({str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                               for p in inputs}, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    output = root / 'objects'
    output.mkdir()
    flags = ['-O1', '-g', '-Wall', '-Wunused', *sanitizer_flags()]
    checked(['make', '-B', '-C', str(source), '-j4', f'OUTPUT_DIR={output}',
             'CC=' + shlex.join(['g++', '-std=c++11', *flags]), 'C4C=' + shlex.join(['gcc', *flags])], root, 'build', timeout=300)
    binary = root / 'fixture'
    objects = [str(p) for p in sorted(output.glob('*.o')) if p.name != 'stringmol.o']
    checked(['g++', '-std=c++11', *flags, '-Wextra', '-Werror', '-I', str(root / 'native'), '-isystem', str(source),
             str(root / 'fixture.cpp'), *objects, '-lm', '-Wl,--wrap=fwrite', '-Wl,--wrap=fflush', '-Wl,--wrap=fopen', '-Wl,--wrap=fclose',
             '-Wl,--wrap=__cxa_throw', '-Wl,--wrap=_Z9AgentMakeim', '-Wl,--wrap=_Z16AgentFreeAndNullPP4s_ag',
             '-o', str(binary)], root, 'link')
    verify_linkage(binary)
    link_full_runner(root, flags)
    return binary


@pytest.fixture(scope='module')
def legacy_interpreter(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Unmodified patches-0001–0006 reference, not the candidate's disabled branch."""
    assert SOURCE
    baseline = Path(SOURCE).resolve(strict=True)
    verify_native_agent(baseline)
    root = tmp_path_factory.mktemp('admission-legacy')
    shutil.copytree(baseline, root / 'src')
    shutil.copyfile(baseline.parent / 'config/ALXII.mtx', root / 'ALXII.mtx')
    shutil.copyfile(ROOT / 'tests/stringmol_admission_interpreter.cpp', root / 'fixture.cpp')
    inputs = [p for p in (root / 'src').iterdir() if p.is_file()] + [root / 'fixture.cpp', root / 'ALXII.mtx']
    (root / 'inputs.json').write_text(json.dumps({str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                               for p in inputs}, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    output = root / 'objects'; output.mkdir()
    checked(['make', '-B', '-C', str(root / 'src'), '-j4', f'OUTPUT_DIR={output}',
             'CC=g++ -std=c++11 -O1 -Wall -Wunused', 'C4C=gcc -O1 -Wall -Wunused'], root, 'build', timeout=300)
    objects = [str(p) for p in sorted(output.glob('*.o')) if p.name != 'stringmol.o']
    path = root / 'fixture'
    checked(['g++', '-std=c++11', '-O1', '-Wall', '-Wextra', '-Werror', '-DSM_ADMISSION_LEGACY', '-isystem', str(root / 'src'),
             str(root / 'fixture.cpp'), *objects, '-lm', '-o', str(path)], root, 'link')
    link_full_runner(root, ['-O1', '-Wall', '-Wunused'])
    return path


def link_full_runner(root: Path, flags: list[str]) -> None:
    checked(['objcopy', '--redefine-sym', 'main=sm_b001_native_main', str(root / 'objects/stringmol.o'),
             str(root / 'renamed-main.o')], root, 'rename-main')
    objects = [str(p) for p in sorted((root / 'objects').glob('*.o')) if p.name != 'stringmol.o']
    checked(['g++', '-std=c++11', *flags, '-isystem', str(root / 'src'), str(ROOT / 'tests/stringmol_scheduling_rng.cpp'),
             str(root / 'renamed-main.o'), *objects, '-lm', '-o', str(root / 'full-runner')], root, 'link-full-runner')


CASES = list(itertools.product(
    [p.value for p in design.Admission], ['IMMEDIATE', 'DELAY500'], [0, 1], [0, 1, 3, 4], [0, 1], [0, 1],
    ['sparse', 'full', 'protected'], [1, 2], ['none']))
CASES.extend((policy.value, schedule, target, offset, hidden, future, 'sparse', seed, empty)
             for policy, schedule, (target, empty), offset, hidden, future, seed in itertools.product(
                 design.Admission, ['IMMEDIATE', 'DELAY500'], [(0, 'active'), (1, 'passive')],
                 [0, 1, 4], [0, 1], [0, 1], [1, 2]))


def fixture_state(layout: str, hidden: int, future: int, target: int, offset: int, empty: str = 'none') -> journal.SelectionState:
    """Independent synthetic inputs, never reconstructed from the producer's CSV."""
    actors: dict[int, design.Actor] = {}
    coordinates: dict[tuple[int, int], int] = {(0, 0): 0, (1, 0): 1}
    for x in range(3):
        for y in range(3):
            if (x, y) in coordinates or (layout == 'sparse' and len(coordinates) >= 3):
                continue
            coordinates[x, y] = len(coordinates)
    for idx in coordinates.values():
        data = bytearray(2001)
        value = ((b'' if empty == 'active' else b'%ABC') if idx == 0 else
                 (b'' if empty == 'passive' else b'%ABC' if empty == 'active' else b'BCDA') if idx == 1 else b'A')
        data[:len(value)] = value
        if hidden:
            if idx == 0:
                data[10] = ord('Z')
            elif idx == 1:
                data[11] = ord('Y')
            else:
                data[10:12] = b'BB'
        if idx < 2 or (layout == 'protected' and idx < 8):
            role = design.Role.ACTIVE if idx % 2 == 0 else design.Role.PASSIVE
            partner, eligible = idx ^ 1, 0
        else:
            role, partner, eligible = design.Role.UNBOUND, None, 999
        if layout == 'protected' and idx == 8:
            data[0] = 0
        actors[idx] = design.Actor(idx, bytes(data), role, partner, eligible)
    slots = tuple(design.Slot(x, y, actors.get(coordinates.get((x, y), -1))) for x in range(3) for y in range(3))
    queue = tuple(range(2, len(actors)))
    return journal.SelectionState(slots, () if future else queue, queue if future else (), 0, 1, 0 if target else 1,
                                  offset, len(actors), 0, 2, 0)


@pytest.mark.parametrize('case', CASES)
def test_actual_native_opcode(interpreter: Path, tmp_path: Path, case: tuple[str, str, int, int, int, int, str, int, str]) -> None:
    policy, schedule, target, offset, hidden, future, layout, seed, empty = case
    args = [str(interpreter), *map(str, case[:-1]), str(interpreter.parent / 'ALXII.mtx'), empty]
    environment = runtime_environment()
    environment.pop('STRINGMOL_ADMISSION_FAULT', None)
    environment.pop('SM_TEST_NATIVE_FLUSH', None)
    environment.pop('SM_TEST_ADMISSION_MODE', None)
    result = subprocess.run(args, cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=15)
    (tmp_path / 'native.stdout').write_text(result.stdout, encoding='utf-8')
    (tmp_path / 'native.stderr').write_text(result.stderr, encoding='utf-8')
    (tmp_path / 'result.json').write_text(json.dumps({'args': args, 'exit_code': result.returncode}) + '\n', encoding='utf-8')
    assert result.returncode == 0 and not result.stderr, result.stderr
    rows = list(journal.read(tmp_path / journal.NAME))
    header = journal.Header(design.Admission(policy), design.Schedule(schedule), horizon=1, width=3, height=3)
    journal.audit_structure(rows, header)  # framing only, never scientific certification
    with (tmp_path / 'material_events002.csv').open(newline='') as stream:
        material = list(csv.DictReader(stream))
    with (tmp_path / 'scheduling_events001.csv').open(newline='') as stream:
        boundary = list(csv.DictReader(stream))
    state = fixture_state(layout, hidden, future, target, offset, empty)
    buffers = {s.actor.identity: s.actor.buffer for s in state.slots if s.actor is not None}
    counts = histogram(buffers)
    replay = admission_material.Replay({'maxl0': 2001, 'buffers': {str(i): b.hex() for i, b in buffers.items()},
                                       'pool': [0] * 33, 'molecular': counts, 'total': counts.copy()})
    with (tmp_path / 'conservation002.csv').open(newline='') as stream:
        checkpoints = list(csv.DictReader(stream))
    replay.checkpoint(checkpoints[0])
    if offset < 4:
        replay = admission_material.check_transaction(replay, rows[1], rows[2], header, state, material)
    else:
        for event in material:
            replay.step(event)
    replay.checkpoint(checkpoints[-1])
    assert material[-1]['event'] == 'CLEAVE'
    if offset == 4:
        assert [row.event for row in rows] == [journal.Event.START, journal.Event.END]
        assert material[-1]['outcome'] == 'NO_CHANGE'
        return
    begin, resolved = rows[1], rows[2]
    journal.check_selection(begin, header, state)
    journal.check_native_cleanup(begin, resolved, state)
    assert int(begin['source']) == (0 if target else 1) and int(begin['offset']) == offset
    assert int(begin['occupied_count']) == (0 if layout == 'protected' else 1 if layout == 'sparse' else 7)
    assert int(begin['vacant_count']) == (6 if layout == 'sparse' else 0)
    selected = begin['target_x'] != ''
    occupied = begin['channel'] == 'OCCUPIED'
    replaced = occupied and selected and policy == 'STRATIFIED_REPLACE'
    admitted = selected and (not occupied or replaced)
    assert int(begin['partial_opportunity']) == int(occupied and selected and offset > 0)
    assert [r['event'] for r in material] == (['EVICT', 'CLEAVE'] if replaced else ['CLEAVE'])
    assert material[-1]['outcome'] == ('PLACED' if admitted else 'FAILED')
    assert int(resolved['source_alive']) == int(offset > 0 or empty == 'active')
    by_index = {int(r['index']): r for r in boundary}
    assert by_index[int(begin['boundary_index'])]['event'] == 'DISPATCH'
    assert by_index[int(resolved['boundary_index'])]['event'] == 'COMPLETE'
    if selected and occupied:
        assert begin['victim_owner'] == ('NEXT' if future else 'NOW')
        assert int(begin['victim_eligible_tick']) == 999
    if replaced:
        death = by_index[int(resolved['death_index'])]
        assert death['event'] == 'DEATH' and death['outcome'] == 'EVICT'
        assert death['id'] == begin['victim'] and death['material_index'] == resolved['eviction_material_index']
    if admitted:
        birth = by_index[int(resolved['birth_index'])]
        assert birth['event'] == 'BIRTH' and birth['id'] == begin['child']
        assert int(resolved['child_eligible_tick']) == (501 if schedule == 'DELAY500' else 1)
        assert birth['material_index'] == resolved['cleave_material_index']


@pytest.mark.parametrize('corruption', ['victim', 'tick', 'child_sequence', 'queue', 'ledger', 'missing', 'duplicate', 'index', 'source'])
def test_joined_material_corruption(interpreter: Path, tmp_path: Path, corruption: str) -> None:
    from copy import deepcopy
    case = ('STRATIFIED_REPLACE', 'IMMEDIATE', 1, 1, 1, 1, 'sparse', 2, 'none')
    test_actual_native_opcode(interpreter, tmp_path, case)
    rows = list(journal.read(tmp_path / journal.NAME))
    begin, resolved = rows[1], rows[2]
    state = fixture_state('sparse', 1, 1, 1, 1)
    buffers = {s.actor.identity: s.actor.buffer for s in state.slots if s.actor is not None}
    counts = histogram(buffers)
    replay = admission_material.Replay({'maxl0': 2001, 'buffers': {str(i): b.hex() for i, b in buffers.items()},
                                       'pool': [0] * 33, 'molecular': counts, 'total': counts.copy()})
    original = deepcopy(replay.__dict__)
    with (tmp_path / 'material_events002.csv').open(newline='') as stream:
        events = list(csv.DictReader(stream))
    def alter(row: journal.Row, key: str, value: str) -> journal.Row:
        values = list(row.values); values[journal.COLUMN_INDEX[key]] = value
        return journal.Row(tuple(values))
    if corruption == 'victim':
        events[0]['before_ids'] = begin['source']
    elif corruption == 'tick':
        events[-1]['tick'] = '1'
    elif corruption == 'child_sequence':
        # Same histogram and total mass, wrong child ordering: accounting alone passes.
        changes = events[-1]['changes']
        assert '3:0:00:41' in changes and '3:1:00:42' in changes
        events[-1]['changes'] = changes.replace('3:0:00:41', '3:0:00:42').replace('3:1:00:42', '3:1:00:41')
        accounting_only = deepcopy(replay)
        for event in events:
            accounting_only.step(event)
    elif corruption == 'queue':
        resolved = alter(resolved, 'next_ids', ';'.join(reversed(resolved['next_ids'].split(';'))))
    elif corruption == 'ledger':
        resolved = alter(resolved, 'eviction_returns', ';'.join(['0'] * 33))
    elif corruption == 'missing':
        events.pop(0)
    elif corruption == 'duplicate':
        events.insert(0, events[0].copy())
    elif corruption == 'index':
        resolved = alter(resolved, 'cleave_material_index', '1')
    else:
        begin = alter(begin, 'source', begin['passive'])
    (tmp_path / 'corruption.json').write_text(json.dumps({'corruption': corruption}) + '\n', encoding='utf-8')
    with pytest.raises(ValueError):
        admission_material.check_transaction(replay, begin, resolved,
            journal.Header(design.Admission.REPLACE, design.Schedule.IMMEDIATE, horizon=1, width=3, height=3), state, events)
    assert replay.__dict__ == original


PHASES = ['validate', 'unlink', 'grid', 'refund', 'ready', 'publication', 'material', 'death', 'lineage',
          'free', 'birth', 'cleave', 'complete', 'journal']


@pytest.mark.parametrize('phase', PHASES)
@pytest.mark.parametrize('target', [0, 1])
@pytest.mark.parametrize('future', [0, 1])
def test_native_failure_witness(interpreter: Path, tmp_path: Path, phase: str, target: int, future: int) -> None:
    args = [str(interpreter), 'STRATIFIED_REPLACE', 'IMMEDIATE', str(target), '1', '1', str(future), 'sparse', '2',
            str(interpreter.parent / 'ALXII.mtx')]
    env = runtime_environment() | {'STRINGMOL_ADMISSION_FAULT': phase}
    env.pop('SM_TEST_NATIVE_FLUSH', None)
    env.pop('SM_TEST_ADMISSION_MODE', None)
    result = subprocess.run(args, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
    (tmp_path / 'native.stdout').write_text(result.stdout, encoding='utf-8')
    (tmp_path / 'native.stderr').write_text(result.stderr, encoding='utf-8')
    (tmp_path / 'result.json').write_text(json.dumps({'args': args, 'exit_code': result.returncode, 'phase': phase}) + '\n', encoding='utf-8')
    assert result.returncode == 1 and result.stderr == f'SM-B003 fatal admission: {phase}\n', result.stderr
    witness = json.loads((tmp_path / 'fault-witness.json').read_text())
    assert witness['phase'] == phase and witness['checkpoint_seen'] == 1 and witness['rng_preserved']
    assert witness['rollback'] is (PHASES.index(phase) < 5) and witness['next_identity'] == 4
    assert witness['victim_frees'] == int(PHASES.index(phase) >= PHASES.index('free'))
    rows = list(journal.read(tmp_path / journal.NAME))
    assert [r.event for r in rows] == [journal.Event.START, journal.Event.BEGIN] + ([journal.Event.RESOLVE] if phase == 'journal' else [])
    with pytest.raises(ValueError):
        journal.audit_structure(rows, journal.Header(design.Admission.REPLACE, design.Schedule.IMMEDIATE, horizon=1, width=3, height=3))


@pytest.mark.parametrize('phase', ['begin', 'material', 'death', 'birth', 'source', 'complete', 'resolve', 'terminal', 'terminal-open', 'terminal-close', 'end'])
@pytest.mark.parametrize('target', [0, 1])
@pytest.mark.parametrize('future', [0, 1])
def test_native_publication_flush_failure(interpreter: Path, tmp_path: Path, phase: str, target: int, future: int) -> None:
    args = [str(interpreter), 'STRATIFIED_REPLACE', 'IMMEDIATE', str(target), '1', '1', str(future), 'sparse', '2',
            str(interpreter.parent / 'ALXII.mtx')]
    env = runtime_environment() | {'SM_TEST_NATIVE_FLUSH': phase}
    env.pop('STRINGMOL_ADMISSION_FAULT', None)
    env.pop('SM_TEST_ADMISSION_MODE', None)
    result = subprocess.run(args, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15)
    (tmp_path / 'native.stdout').write_text(result.stdout, encoding='utf-8')
    (tmp_path / 'native.stderr').write_text(result.stderr, encoding='utf-8')
    (tmp_path / 'result.json').write_text(json.dumps({'args': args, 'exit_code': result.returncode, 'flush_failure': phase}) + '\n', encoding='utf-8')
    assert result.returncode == 1 and any(word in result.stderr for word in ('journal', 'write', 'terminal VM')), result.stderr
    assert 'Sanitizer' not in result.stderr and 'runtime error:' not in result.stderr
    witness = json.loads((tmp_path / 'fault-witness.json').read_text())
    assert witness['checkpoint_seen'] == 1 and witness['rng_preserved'] and witness['next_identity'] == 4
    assert witness['rollback'] is (phase == 'begin')
    assert witness['victim_frees'] == int(phase not in ('begin', 'material', 'death'))
    rows = list(journal.read(tmp_path / journal.NAME))
    header = journal.Header(design.Admission.REPLACE, design.Schedule.IMMEDIATE, horizon=1, width=3, height=3)
    if phase == 'end':
        # A complete-looking journal does not rescue a failed execution.
        journal.audit_structure(rows, header)
    else:
        with pytest.raises(ValueError):
            journal.audit_structure(rows, header)


@pytest.mark.parametrize('policy', [p.value for p in design.Admission])
@pytest.mark.parametrize('schedule', ['IMMEDIATE', 'DELAY500'])
@pytest.mark.parametrize('layout', ['sparse', 'full', 'protected'])
@pytest.mark.parametrize('seed', [1, 2])
@pytest.mark.parametrize('target', [0, 1])
@pytest.mark.parametrize('offset', [0, 1, 4])
def test_native_disabled_and_observer_isolation(interpreter: Path, legacy_interpreter: Path, tmp_path: Path,
                                                policy: str, schedule: str, layout: str, seed: int, target: int, offset: int) -> None:
    def invoke(binary: Path, mode: str) -> dict[str, bytes]:
        directory = tmp_path / mode; directory.mkdir()
        env = runtime_environment() | {'SM_TEST_ADMISSION_MODE': mode}
        env.pop('STRINGMOL_ADMISSION_FAULT', None); env.pop('SM_TEST_NATIVE_FLUSH', None)
        args = [str(binary), policy, schedule, str(target), str(offset), '1', '1', layout, str(seed),
                str(binary.parent / 'ALXII.mtx'), 'none']
        result = subprocess.run(args, cwd=directory, env=env, capture_output=True, text=True, timeout=15)
        (directory / 'native.stdout').write_text(result.stdout, encoding='utf-8')
        (directory / 'native.stderr').write_text(result.stderr, encoding='utf-8')
        (directory / 'result.json').write_text(json.dumps({'args': args, 'mode': mode, 'exit_code': result.returncode}) + '\n', encoding='utf-8')
        assert result.returncode == 0 and not result.stderr, result.stderr
        assert (directory / journal.NAME).exists() is (mode == 'observed')
        assert (directory / 'vm_end007.csv').exists() is (mode == 'observed')
        return {p.name: p.read_bytes() for p in directory.iterdir() if p.suffix == '.csv' and p.name not in {journal.NAME, 'vm_end007.csv'}} | {
            'final-rng.txt': (directory / 'final-rng.txt').read_bytes()}
    observed = invoke(interpreter, 'observed')
    assert invoke(interpreter, 'unobserved') == observed
    if policy == 'NATIVE_VACANCY':
        assert invoke(interpreter, 'disabled') == invoke(legacy_interpreter, 'legacy') == observed


@pytest.fixture(scope='module')
def linked_program(interpreter: Path, legacy_interpreter: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp('linked-program')
    test_complete_simulator_plumbing(interpreter, legacy_interpreter, root, 'STRATIFIED_REPLACE', 'IMMEDIATE', 'program', 2)
    directory = root / 'observed'
    summary = json.loads((directory / 'independent-replay.json').read_text())
    assert summary['evictions'] > 0 and summary['partial_commits'] > 0
    return directory


@pytest.mark.parametrize('corruption', ['draw', 'instruction', 'missing-proposals', 'target', 'lineage', 'missing-eviction',
                                       'source', 'retirement', 'buffer', 'rng', 'terminal-head', 'terminal-grid', 'exit', 'seed'])
def test_whole_history_adversaries(linked_program: Path, tmp_path: Path, corruption: str) -> None:
    from experiments.stringmol.configure_control import HOST
    directory = tmp_path / 'trace'; shutil.copytree(linked_program, directory)
    header = journal.Header(design.Admission.REPLACE, design.Schedule.IMMEDIATE, horizon=600, width=3, height=3)
    def read_rows(name: str) -> tuple[list[str], list[dict[str, str]]]:
        with (directory / name).open(newline='') as stream:
            reader = csv.DictReader(stream)
            assert reader.fieldnames is not None
            return list(reader.fieldnames), list(reader)
    def save_rows(name: str, columns: list[str], rows: list[dict[str, str]]) -> None:
        with (directory / name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, columns, lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
    if corruption in ('draw', 'missing-proposals', 'target'):
        admission_rows = list(journal.read(directory / journal.NAME))
        if corruption == 'missing-proposals':
            values = list(admission_rows[-1].values)
            values[journal.COLUMN_INDEX['index']] = '2'
            for key in journal.COUNTERS[:-1]: values[journal.COLUMN_INDEX[key]] = '0'
            values[journal.COLUMN_INDEX['eviction_returns']] = ';'.join(['0'] * 33)
            admission_rows = [admission_rows[0], journal.Row(tuple(values))]
        else:
            index = next(i for i, row in enumerate(admission_rows) if row.event is journal.Event.BEGIN)
            values = list(admission_rows[index].values)
            if corruption == 'draw':
                old = journal.uniform(admission_rows[index]['channel_bits']); assert old is not None
                values[journal.COLUMN_INDEX['channel_bits']] = journal.uniform_bits((int(old * 2**32) ^ 1) * 2**-32)
            else:
                values[journal.COLUMN_INDEX['target_x']] = str((int(admission_rows[index]['target_x']) + 1) % 3)
            admission_rows[index] = journal.Row(tuple(values))
        # The corrupted journal remains internally well-framed and self-consistent.
        journal.audit_structure(admission_rows, header)
        (directory / journal.NAME).write_text(','.join(journal.COLUMNS)+'\n'+''.join(row.encode() for row in admission_rows), encoding='ascii')
    elif corruption == 'instruction':
        columns, rows = read_rows('scheduling_events001.csv')
        row = next(row for row in rows if row['event'] == 'DISPATCH')
        offset, opcode = int(row['offset']), chr(int(row['opcode']))
        assert HOST[offset] == opcode
        row['offset'] = str(next(i for i, symbol in enumerate(HOST) if symbol == opcode and i != offset))
        save_rows('scheduling_events001.csv', columns, rows)
    elif corruption in ('lineage', 'missing-eviction'):
        columns, rows = read_rows('lineage_events001.csv')
        if corruption == 'lineage':
            next(row for row in rows if row['event'] == 'BIRTH')['child_species'] = '99999'
        else:
            rows = [row for row in rows if row['event'] != 'EVICT']
        save_rows('lineage_events001.csv', columns, rows)
    elif corruption in ('source', 'retirement'):
        columns, rows = read_rows('source_events006.csv')
        if corruption == 'source': rows[0]['flow_offset'] = str(int(rows[0]['flow_offset']) + 1)
        else: rows[0]['decision'] = 'RETIRE'
        save_rows('source_events006.csv', columns, rows)
    elif corruption == 'buffer':
        columns, rows = read_rows('conservation_buffers002.csv')
        buffer = bytearray.fromhex(rows[-1]['full_buffer_hex']); buffer[-2] = ord('Z')
        rows[-1]['full_buffer_hex'] = buffer.hex().upper()
        save_rows('conservation_buffers002.csv', columns, rows)
    elif corruption in ('terminal-head', 'terminal-grid'):
        columns, rows = read_rows('vm_end007.csv')
        if corruption == 'terminal-head':
            row = next((row for row in rows if row['role'] == 'ACTIVE'), rows[0])
            row['i0'] = str(int(row['i0'] or '0')+1)
        else:
            rows[0]['x'] = str((int(rows[0]['x'])+1) % 3)
        save_rows('vm_end007.csv', columns, rows)
    elif corruption == 'rng':
        lines = (directory / 'final_rng.txt').read_text().splitlines()
        lines[-1] = str(int(lines[-1]) ^ 1)
        (directory / 'final_rng.txt').write_text('\n'.join(lines)+'\n')
    initial = conservation.initial_material([{'id': i, 'sequence_hex': s.hex()} for i, s in enumerate((HOST.encode(), HOST.encode(), b'A'))],
                                            'uniform', 128, 2001)
    if corruption == 'instruction':
        # Ordered material/queue replay accepts the same-byte head forgery.
        with (directory / 'material_events002.csv').open(newline='') as stream:
            material_rows = list(csv.DictReader(stream))
        boundary = admission_boundary.BoundaryReplay(initial, material_rows, 'IMMEDIATE', 600)
        with (directory / 'scheduling_events001.csv').open(newline='') as stream:
            for row in csv.DictReader(stream): boundary.step(row)
        assert boundary.summary(600)['boundary_errors'] == 0
    assert SOURCE
    with pytest.raises(ValueError) as error:
        admission_replay.replay(directory, initial, {0: (0, 0), 1: (1, 0), 2: (0, 1)}, header,
            3 if corruption == 'seed' else 2, Path(SOURCE).resolve().parent / 'config/ALXII.mtx', decay=0,
            exit_status=1 if corruption == 'exit' else 0)
    (tmp_path / 'rejection.json').write_text(json.dumps({'corruption': corruption, 'reason': str(error.value)})+'\n')


@pytest.mark.parametrize('seed', [0, 1, 2, 2**32-1])
@pytest.mark.parametrize('draws', [0, 1, 623, 624, 625, 1249])
def test_independent_numeric_kernels(interpreter: Path, tmp_path: Path, seed: int, draws: int) -> None:
    pairs: list[tuple[bytes, bytes]] = []
    if seed == 2 and draws == 625:
        from experiments.stringmol.configure_control import HOST
        pairs = [(b'ABC', b'ABC'), (b'A', b'Z'), (b'%', b'}'), (HOST.encode(), HOST.encode()),
                 (admission_numeric.complement(HOST.encode()), HOST.encode())]
        generator = admission_numeric.MT(42)
        alphabet = conservation.ALPHABET.encode()
        for _ in range(128):
            pair = [bytes(alphabet[generator.rank(len(alphabet))] for _ in range(1+generator.rank(24))) for _ in range(2)]
            pairs.append((pair[0], pair[1]))
    matrix = interpreter.parent / 'ALXII.mtx'
    result = subprocess.run([str(interpreter), 'numeric', str(seed), str(draws), str(matrix)], cwd=tmp_path,
                            input=''.join(a.decode()+' '+b.decode()+'\n' for a, b in pairs),
                            env=runtime_environment(), capture_output=True, text=True, timeout=30)
    (tmp_path / 'native.stdout').write_text(result.stdout, encoding='utf-8')
    (tmp_path / 'native.stderr').write_text(result.stderr, encoding='utf-8')
    assert result.returncode == 0 and not result.stderr, result.stderr
    rng = admission_numeric.MT(seed)
    assert [float(line[5:]) for line in result.stdout.splitlines() if line.startswith('DRAW ')] == [rng.uniform() for _ in range(draws)]
    assert (tmp_path / 'numeric-rng.txt').read_text() == rng.encoded()
    observed = [line.split()[1:] for line in result.stdout.splitlines() if line.startswith('ALIGN ')]
    assert len(observed) == len(pairs)
    oracle = admission_numeric.Matrix(matrix)
    for (a, b), fields in zip(pairs, observed, strict=True):
        expected = oracle.align(a, b)
        assert tuple(map(int, fields[:4])) == (expected.s1, expected.e1, expected.s2, expected.e2)
        assert admission_numeric.f32(float(fields[4])) == expected.score
        assert int(fields[5]) == expected.match
        assert admission_numeric.f32(float(fields[6])) == expected.probability(binding=True)


@pytest.mark.parametrize('directive', ['SUBMAT', 'USING'])
@pytest.mark.parametrize('length', [0, 80, 2000])
def test_table_loader_rejects_invalid_paths(interpreter: Path, tmp_path: Path, directive: str, length: int) -> None:
    config = tmp_path / 'loader.conf'
    config.write_text(directive + ' ' + 'x' * length + '\n', encoding='ascii')
    result = subprocess.run([str(interpreter), 'loader', str(config), '4'], cwd=tmp_path,
                            env=runtime_environment(), capture_output=True, text=True, timeout=15)
    (tmp_path / 'native.stderr').write_text(result.stderr, encoding='utf-8')
    assert result.returncode == 0 and result.stderr == 'Invalid or oversized substitution-table filename\n', result.stderr


def test_table_loader_accepts_maximum_filename(interpreter: Path, tmp_path: Path) -> None:
    name = 'x' * 79
    shutil.copyfile(interpreter.parent / 'ALXII.mtx', tmp_path / name)
    config = tmp_path / 'loader.conf'
    config.write_text('SUBMAT ' + name + '\n', encoding='ascii')
    result = subprocess.run([str(interpreter), 'loader', str(config), '0'], cwd=tmp_path,
                            env=runtime_environment(), capture_output=True, text=True, timeout=15)
    (tmp_path / 'native.stderr').write_text(result.stderr, encoding='utf-8')
    assert result.returncode == 0 and not result.stderr, result.stderr


@pytest.mark.parametrize('policy', [p.value for p in design.Admission])
@pytest.mark.parametrize('schedule', ['IMMEDIATE', 'DELAY500'])
@pytest.mark.parametrize('scenario', ['tiny', 'program', 'decay'])
@pytest.mark.parametrize('seed', [2, 17])
def test_complete_simulator_plumbing(interpreter: Path, legacy_interpreter: Path, tmp_path: Path, policy: str, schedule: str, scenario: str, seed: int) -> None:
    """Small mechanical worlds, not the frozen zero-pool population assay."""
    from experiments.stringmol.configure_control import HOST
    horizon, report, pool = (3, 1, 0) if scenario == 'tiny' else (600, 100, 128)
    decay_rate = .005 if scenario == 'decay' else 0
    sequences = (b'%ABC', b'BCDA', b'A') if scenario == 'tiny' else (HOST.encode(), HOST.encode(), b'A')
    assert SOURCE
    matrix = Path(SOURCE).resolve().parent / 'config/ALXII.mtx'
    assert len(str(matrix)) < 80  # inherited fixed-size configuration path storage
    config = ('%% synthetic full-loop plumbing fixture\nGRIDX 3\nGRIDY 3\nCELLRAD 2500\nAGRAD 10\nENERGY 0\n'
              f'ESTEP 2500\nNSTEPS {horizon}\nDECAY {decay_rate}\nMUTATE 0\nREPORTEVERY {report}\nIMAGEEVERY 1000000\n'
              f'INTERACTION_RADIUS 0\nPLACEMENT_RADIUS 0\nRANDSEED {seed}\nSUBMAT {matrix}\nNUMAGENTS 3\n'
              f'AGENT {sequences[0].decode()} 1 Q\nGRIDPOS 0 0\nAGENT {sequences[1].decode()} 1 Q\nGRIDPOS 1 0\nAGENT A 1 Q\nGRIDPOS 0 1\n')
    def invoke(binary: Path, mode: str) -> dict[str, bytes]:
        directory = tmp_path / mode; directory.mkdir()
        (directory / 'fixture.conf').write_text(config, encoding='ascii')
        env = runtime_environment()
        for key in list(env):
            if key.startswith(('STRINGMOL_', 'SM_TEST_')):
                del env[key]
        env.update(STRINGMOL_CONSERVATION='1', STRINGMOL_DECAY_DESTINATION='recycle', STRINGMOL_POOL_MODE='uniform',
                   STRINGMOL_POOL_AMOUNT=str(pool), STRINGMOL_CONSERVATION_LOG='1', STRINGMOL_LINEAGE_LOG='1', STRINGMOL_SCHEDULING='1',
                   STRINGMOL_SCHEDULING_POLICY=schedule, STRINGMOL_SCHEDULING_LOG='1', STRINGMOL_SOURCE_RETENTION='1',
                   STRINGMOL_SOURCE_DISPOSITION='RETAIN', STRINGMOL_RETIREMENT_LOG='1',
                   STRINGMOL_ADMISSION='0' if mode in ('legacy', 'disabled') else '1', STRINGMOL_ADMISSION_POLICY=policy,
                   STRINGMOL_ADMISSION_LOG='0' if mode == 'unobserved' else '1')
        result = subprocess.run([str(binary.parent / 'full-runner'), '30', 'fixture.conf'], cwd=directory, env=env,
                                capture_output=True, text=True, timeout=30)
        (directory / 'native.stdout').write_text(result.stdout, encoding='utf-8')
        (directory / 'native.stderr').write_text(result.stderr, encoding='utf-8')
        (directory / 'result.json').write_text(json.dumps({'exit_code': result.returncode, 'mode': mode, 'env': {k: v for k, v in env.items() if k.startswith('STRINGMOL_')}}) + '\n', encoding='utf-8')
        assert result.returncode == 0 and not result.stderr, result.stderr
        assert 'FINISHED smspatial' in result.stdout
        assert (directory / journal.NAME).exists() is (mode == 'observed')
        if mode == 'observed':
            journal.audit_structure(journal.read(directory / journal.NAME),
                                    journal.Header(design.Admission(policy), design.Schedule(schedule), horizon=horizon, width=3, height=3))
            initial = conservation.initial_material([{'id': i, 'sequence_hex': s.hex()} for i, s in enumerate(sequences)],
                                                    'uniform', pool, 2001)
            with (directory / 'material_events002.csv').open(newline='') as stream:
                material_rows = list(csv.DictReader(stream))
            initial_rng = admission_numeric.MT(seed)
            remaining, order = [0, 1, 2], []
            while remaining: order.append(remaining.pop(initial_rng.rank(len(remaining))))
            boundary = admission_boundary.BoundaryReplay(initial, material_rows, schedule, horizon, initial_order=order)
            with (directory / 'scheduling_events001.csv').open(newline='') as stream:
                for row in csv.DictReader(stream):
                    boundary.step(row)
            assert boundary.summary(boundary.tick+1)['boundary_errors'] == 0
            reconstructed = admission_replay.replay(directory, initial, {0: (0, 0), 1: (1, 0), 2: (0, 1)},
                journal.Header(design.Admission(policy), design.Schedule(schedule), horizon=horizon, width=3, height=3),
                seed, matrix, decay=decay_rate, report_every=report)
            (directory / 'independent-replay.json').write_text(json.dumps(reconstructed, sort_keys=True) + '\n', encoding='utf-8')
        assert (directory / 'vm_end007.csv').exists() is (mode == 'observed')
        return {p.name: p.read_bytes() for p in directory.iterdir() if p.suffix == '.csv' and p.name not in {journal.NAME, 'vm_end007.csv'}} | {
            'final_rng.txt': (directory / 'final_rng.txt').read_bytes()}
    observed = invoke(interpreter, 'observed')
    assert invoke(interpreter, 'unobserved') == observed
    if policy == 'NATIVE_VACANCY':
        assert invoke(interpreter, 'disabled') == invoke(legacy_interpreter, 'legacy') == observed
