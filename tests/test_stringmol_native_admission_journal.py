"""Native transport conformance/fault tests, not native replacement qualification."""
from pathlib import Path
import subprocess

import pytest

from experiments.stringmol import admission_design as a, admission_journal as j

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp('native-admission-journal') / 'fixture'
    subprocess.run(['g++', '-std=c++11', '-Wall', '-Wextra', '-Werror', '-O2', '-I', str(ROOT),
                    str(ROOT / 'tests/stringmol_admission_journal.cpp'), '-Wl,--wrap=fflush,--wrap=fwrite,--wrap=fclose', '-o', str(path)],
                   check=True, capture_output=True, text=True, timeout=60)
    return path


def run(binary: Path, mode: str, path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(binary), mode, str(path)], capture_output=True, text=True, timeout=10)


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
