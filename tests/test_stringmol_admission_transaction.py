"""Actual native replacement-component mechanics; no population execution."""
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from experiments.stringmol.native_testing import checked, sanitizer_flags, runtime_environment, verify_linkage, verify_native_agent

ROOT = Path(__file__).resolve().parents[1]
SOURCE = os.environ.get('SM_ADMISSION_NATIVE_SOURCE')
pytestmark = pytest.mark.skipif(not SOURCE, reason='explicit native source component qualification only')


@pytest.fixture(scope='module')
def binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    assert SOURCE
    source = Path(SOURCE).resolve(strict=True)
    verify_native_agent(source)
    root = tmp_path_factory.mktemp('native-replacement-component')
    (root / 'src').mkdir()
    shutil.copyfile(source / 'sm_conservation.h', root / 'src/sm_conservation.h')
    patch = ROOT / 'experiments/stringmol/native/eviction_ledger.patch'
    checked(['git', 'apply', str(patch)], root, 'apply-ledger')
    flags = ['-std=c++11', '-O1', '-ffunction-sections', '-fdata-sections', *sanitizer_flags()]
    compile_agent = ['g++', *flags, '-I', str(source), '-c', str(source / 'agent.cpp'), '-o', str(root / 'agent.o')]
    checked(compile_agent, root, 'compile-agent')
    path = root / 'fixture'
    fixture = ROOT / 'tests/stringmol_admission_transaction.cpp'
    args = ['g++', *flags, '-Wall', '-Wextra', '-Werror', '-isystem', str(root / 'src'), '-I', str(ROOT),
            '-isystem', str(source), str(fixture), str(root / 'agent.o'), '-Wl,--gc-sections',
            '-Wl,--wrap=_Z16AgentFreeAndNullPP4s_ag', '-o', str(path)]
    inputs = [source / 'agent.cpp', *sorted(source.glob('*.h')), fixture, patch,
              ROOT / 'experiments/stringmol/native/admission_transaction.h', root / 'src/sm_conservation.h']
    (root / 'inputs.json').write_text(json.dumps({'commands': [compile_agent, args],
        'inputs': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}}, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    checked(args, root, 'compile-fixture')
    verify_linkage(path)
    return path


def execute(binary: Path, root: Path, mode: str, future: int, position: int, hidden: int, expected: int = 0) -> None:
    result = subprocess.run([str(binary), mode, str(future), str(position), str(hidden)], cwd=root,
                            capture_output=True, text=True, timeout=10, env=runtime_environment())
    (root / 'fixture.stdout').write_text(result.stdout, encoding='utf-8')
    (root / 'fixture.stderr').write_text(result.stderr, encoding='utf-8')
    (root / 'exit.json').write_text(json.dumps({'mode': mode, 'exit_code': result.returncode}) + '\n', encoding='utf-8')
    assert result.returncode == expected, result.stderr
    assert 'AddressSanitizer' not in result.stderr and 'runtime error:' not in result.stderr, result.stderr
    if expected:
        assert result.stderr == 'POST_PUBLICATION_FATAL\n'
    else:
        assert not result.stderr


@pytest.mark.parametrize('future', [0, 1])
@pytest.mark.parametrize('position', [0, 1, 2])
@pytest.mark.parametrize('hidden', [0, 1])
def test_native_full_refund_and_both_reconciliation_sites(binary: Path, tmp_path: Path, future: int, position: int, hidden: int) -> None:
    execute(binary, tmp_path, 'success', future, position, hidden)
    with (tmp_path / 'material_events002.csv').open(newline='') as stream:
        events = list(csv.DictReader(stream))
    assert [row['event'] for row in events] == ['EVICT', 'CLEAVE']
    assert (tmp_path / 'conservation002.csv').is_file()
    assert (tmp_path / 'conservation_buffers002.csv').is_file()


@pytest.mark.parametrize('position', [0, 1, 2])
@pytest.mark.parametrize('hidden', [0, 1])
@pytest.mark.parametrize('mode', ['success-bound', *[f'fault-{point}-bound' for point in range(5)]])
def test_native_bound_next_queue_may_retain_now_grid_status(binary: Path, tmp_path: Path, position: int, hidden: int, mode: str) -> None:
    execute(binary, tmp_path, mode, 1, position, hidden)


@pytest.mark.parametrize('point', range(5))
@pytest.mark.parametrize('future', [0, 1])
@pytest.mark.parametrize('position', [0, 1, 2])
@pytest.mark.parametrize('hidden', [0, 1])
def test_native_prepublication_fault_restores_exact_baseline(binary: Path, tmp_path: Path, point: int, future: int, position: int, hidden: int) -> None:
    execute(binary, tmp_path, f'fault-{point}', future, position, hidden)
    assert not (tmp_path / 'material_events002.csv').exists()


@pytest.mark.parametrize('mode', ['publish-before', 'publish-after'])
@pytest.mark.parametrize('future', [0, 1])
@pytest.mark.parametrize('position', [0, 1, 2])
@pytest.mark.parametrize('hidden', [0, 1])
def test_native_publication_failure_is_fatal_and_not_rolled_back(binary: Path, tmp_path: Path, mode: str, future: int, position: int, hidden: int) -> None:
    execute(binary, tmp_path, mode, future, position, hidden, expected=23)
    journal = tmp_path / 'material_events002.csv'
    assert journal.exists() == (mode == 'publish-after')
    if journal.exists():
        with journal.open(newline='') as stream:
            assert [row['event'] for row in csv.DictReader(stream)] == ['EVICT']


@pytest.mark.parametrize('mode', ['abandon', 'free-early', 'free-staged'])
@pytest.mark.parametrize('future', [0, 1])
@pytest.mark.parametrize('position', [0, 1, 2])
@pytest.mark.parametrize('hidden', [0, 1])
def test_native_abandoned_stage_and_free_order(binary: Path, tmp_path: Path, mode: str, future: int, position: int, hidden: int) -> None:
    execute(binary, tmp_path, mode, future, position, hidden)


@pytest.mark.parametrize('mode', ['protected', 'bound', 'empty', 'inbound', 'head', 'dual', 'unowned', 'reuse', 'overflow', 'ledger-overflow', 'cycle',
                                  'negative-pool', 'invalid-min', 'invalid-grid-status', 'grid-duplicate', 'duplicate-id', 'backlink', 'child-owned', 'child-alias'])
@pytest.mark.parametrize('future', [0, 1])
def test_native_preflight_rejects_invalid_victims_and_ownership(binary: Path, tmp_path: Path, mode: str, future: int) -> None:
    execute(binary, tmp_path, mode, future, 1, 1)
