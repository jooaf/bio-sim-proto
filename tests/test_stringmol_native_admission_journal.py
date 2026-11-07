"""Native transport conformance/fault tests, not native replacement qualification."""
from pathlib import Path
import csv
import hashlib
import io
import json
import os
import subprocess

import pytest

from experiments.stringmol import admission_design as a, admission_journal as j

ROOT = Path(__file__).resolve().parents[1]
SANITIZERS = os.environ.get('SM_ADMISSION_SANITIZERS', '0')
if SANITIZERS not in ('0', '1'):
    raise ValueError('SM_ADMISSION_SANITIZERS must be 0 or 1')


def sanitizer_flags() -> list[str]:
    directory = os.environ.get('SM_ADMISSION_SANITIZER_LIBDIR')
    if SANITIZERS == '0':
        if directory:
            raise ValueError('Sanitizer library override requires instrumentation')
        return []
    flags = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-fno-omit-frame-pointer', '-g']
    if directory:
        lib = Path(directory).resolve(strict=True)
        for name in ('libasan.so', 'libubsan.so'):
            if not (lib / name).is_file():
                raise ValueError(f'Missing sanitizer runtime: {lib / name}')
        flags.extend(['-L', str(lib), '-Xlinker', '-rpath', '-Xlinker', str(lib)])
    return flags


@pytest.fixture(scope='module')
def binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp('native-admission-journal') / 'fixture'
    subprocess.run(['g++', '-std=c++11', '-Wall', '-Wextra', '-Werror', '-O2', '-I', str(ROOT),
                    str(ROOT / 'tests/stringmol_admission_journal.cpp'), '-Wl,--wrap=fflush,--wrap=fwrite,--wrap=fclose',
                    *sanitizer_flags(), '-o', str(path)],
                   check=True, capture_output=True, text=True, timeout=60)
    if SANITIZERS == '1':
        linkage = subprocess.run(['ldd', str(path)], check=True, capture_output=True, text=True, timeout=10)
        (path.parent / 'linkage.txt').write_text(linkage.stdout, encoding='utf-8')
        library_dir = os.environ.get('SM_ADMISSION_SANITIZER_LIBDIR')
        for name in ('libasan.so', 'libubsan.so'):
            matches = [line.partition('=>')[2].rsplit(' (', 1)[0].strip()
                       for line in linkage.stdout.splitlines() if line.strip().startswith(name + '.')]
            assert len(matches) == 1 and Path(matches[0]).is_file(), linkage.stdout
            if library_dir:
                assert Path(matches[0]).resolve() == (Path(library_dir) / name).resolve(), linkage.stdout
    return path


def run(binary: Path, mode: str, path: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if SANITIZERS == '1':
        # Do not inherit caller suppressions or disabled instrumentation options.
        env.pop('LSAN_OPTIONS', None)
        env['ASAN_OPTIONS'] = 'detect_leaks=1:halt_on_error=1:strict_string_checks=1'
        env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
    return subprocess.run([str(binary), mode, str(path)], capture_output=True, text=True, timeout=10, env=env)


@pytest.mark.skipif(SANITIZERS != '1', reason='explicit sanitizer qualification only')
@pytest.mark.parametrize('mode,diagnostic', [('uaf', 'heap-use-after-free'), ('overflow', 'signed integer overflow')])
def test_sanitizer_rejects_deliberate_fault(tmp_path: Path, mode: str, diagnostic: str) -> None:
    path = tmp_path / 'sanitizer-control'
    subprocess.run(['g++', '-std=c++11', '-O1', *sanitizer_flags(),
                    str(ROOT / 'tests/stringmol_sanitizer_controls.cpp'), '-o', str(path)],
                   check=True, capture_output=True, text=True, timeout=60)
    result = run(path, mode, tmp_path / 'unused')
    (tmp_path / 'control.stderr').write_text(result.stderr, encoding='utf-8')
    assert result.returncode != 0 and diagnostic in result.stderr, result.stderr


@pytest.mark.skipif(SANITIZERS != '1' or not os.environ.get('SM_ADMISSION_NATIVE_SOURCE'),
                    reason='explicit instrumented native source qualification only')
def test_real_native_cleanup_branch(tmp_path: Path) -> None:
    source = Path(os.environ['SM_ADMISSION_NATIVE_SOURCE']).resolve(strict=True)
    pins = {'agent.cpp': '81218d2c1083e24c8b10c916a482664d309ccbdfbfd8cedc054c1e5f5b68b1a1',
            'agent.h': '0066da3fb8233ddb5f7b8abb43e79cc5b47f407eca4126a569eb00e2d0f89941'}
    for name, expected in pins.items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected, 'native cleanup implementation changed'
    path = tmp_path / 'native-cleanup'
    fixture = ROOT / 'tests/stringmol_admission_cleanup.cpp'
    args = ['g++', '-std=c++11', '-O1', '-ffunction-sections', '-fdata-sections', *sanitizer_flags(),
            '-I', str(source), str(fixture), str(source / 'agent.cpp'), '-Wl,--gc-sections', '-o', str(path)]
    inputs = [source / 'agent.cpp', *sorted(source.glob('*.h')), fixture]
    receipt = {'command': args, 'inputs': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}}
    (tmp_path / 'native-cleanup-inputs.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    subprocess.run(args, check=True, capture_output=True, text=True, timeout=60)
    result = run(path, 'cases', tmp_path / 'unused')
    (tmp_path / 'native-cleanup.csv').write_text(result.stdout, encoding='utf-8')
    (tmp_path / 'native-cleanup.stderr').write_text(result.stderr, encoding='utf-8')
    assert result.returncode == 0 and not result.stderr, result.stderr
    actual = list(csv.reader(io.StringIO(result.stdout)))
    assert actual[0] == ['active_empty', 'passive_empty', 'hidden', 'action']
    assert [list(map(int, row)) for row in actual[1:]] == [
        [active, passive, hidden, 1 if active else 2 if passive else 0]
        for active in (0, 1) for passive in (0, 1) for hidden in (0, 1)]


def test_native_header_and_markers_match_python(binary: Path, tmp_path: Path) -> None:
    path = tmp_path / j.NAME
    result = run(binary, 'complete', path)
    assert result.returncode == 0, result.stderr
    rows = tuple(j.read(path))
    assert j.audit_structure(rows, j.Header(a.Admission.REPLACE, a.Schedule.DELAY500, 50, 3, 2)).rows == 2
    assert path.read_bytes().splitlines()[0] == ','.join(j.COLUMNS).encode('ascii')
    original = path.read_bytes()
    assert run(binary, 'complete', path).returncode == 92  # exclusive creation, never overwrite
    assert path.read_bytes() == original


def test_native_complete_proposal_transport(binary: Path, tmp_path: Path) -> None:
    path = tmp_path / j.NAME
    result = run(binary, 'proposal', path)
    assert result.returncode == 0, result.stderr
    rows = tuple(j.read(path))
    summary = j.audit_structure(rows, j.Header(a.Admission.REPLACE, a.Schedule.DELAY500, 50, 3, 2))
    assert summary.proposals == summary.evictions == summary.partial_commits == 1
    assert sum(summary.eviction_returns) == 3
    assert j.full_buffer(rows[1]['victim_buffer'])[:4] == b'A\0BB'


def test_native_uniform_wire_bits(binary: Path, tmp_path: Path) -> None:
    result = run(binary, 'bits', tmp_path / 'unused')
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [j.uniform_bits(value) for value in (0.0, 0.5, (2**32-1)*2**-32)]


@pytest.mark.parametrize('mode,code', [('header-fault', 92), ('write-fault', 91), ('short-write', 91), ('missing-end', 0),
                                      ('duplicate', 92), ('pending', 92), ('oversize', 92)])
def test_native_fault_prefix_cannot_pass_framing(binary: Path, tmp_path: Path, mode: str, code: int) -> None:
    path = tmp_path / j.NAME
    result = run(binary, mode, path)
    assert result.returncode == code, result.stderr
    with pytest.raises(ValueError):
        j.audit_structure(j.read(path), j.Header(a.Admission.REPLACE, a.Schedule.DELAY500, 50, 3, 2))


@pytest.mark.parametrize('mode', ['after-end', 'close-fault'])
def test_complete_file_does_not_override_fatal_exit(binary: Path, tmp_path: Path, mode: str) -> None:
    path = tmp_path / j.NAME
    result = run(binary, mode, path)
    assert result.returncode == 92
    # A complete prefix alone cannot authorize a run with fatal process status.
    assert j.audit_structure(j.read(path), j.Header(a.Admission.REPLACE, a.Schedule.DELAY500, 50, 3, 2)).rows == 2
