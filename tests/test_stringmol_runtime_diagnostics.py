"""Development profiling cannot qualify changed outputs or leave timed-out children."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import time

import pytest

from experiments.stringmol import diagnose_retirement_runtime as d, conservation_workflow as c


def test_qualification_requires_every_output_and_fixed_boundary() -> None:
    passed = {'exit_status': 0, 'parity': True, 'wall_seconds': 300.0}
    assert d.qualify([passed], 300)
    assert not d.qualify([], 300)
    for changed in ({'exit_status': 'timeout'}, {'exit_status': 1}, {'parity': False}, {'wall_seconds': 300.01}):
        assert not d.qualify([passed, {**passed, **changed}], 300)
    assert d.SEED not in range(202628000, 202628020)
    assert max(workers for _, workers, _ in d.PROFILES) == 6


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux resource instrumentation')
def test_resource_sample() -> None:
    current = d.resources(os.getpid())
    assert current['cpu_seconds'] >= 0
    assert 'wchar' in current['io']
    assert d.resources(2147483647)['exited']


@pytest.mark.skipif(sys.platform != 'linux', reason='GNU time probe')
def test_probe_metrics_do_not_contaminate_native_inventory(tmp_path: Path) -> None:
    root = tmp_path / 'metrics'; root.mkdir()
    config = tmp_path / 'config'; config.write_text('synthetic test, not simulation')
    expected = {name: {'size': 0, 'sha256': c.digest(b'')} for name in ('stdout.txt', 'stderr.txt')}
    result = d.probe(0, root, tmp_path / 'raw', Path('/usr/bin/true'), config, expected, deadline=10)
    assert result['exit_status'] == 0 and result['parity'] is True
    assert result['timing']['user_seconds'] >= 0
    assert set(result['files']) == set(expected)
    assert c.read(root / '0.receipt.json') == result


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux process group timeout')
def test_timeout_kills_native_descendant_group(tmp_path: Path) -> None:
    root = tmp_path / 'metrics'; root.mkdir()
    pidfile = tmp_path / 'child.pid'
    binary = tmp_path / 'synthetic-native'
    binary.write_text('#!/usr/bin/python3\nimport subprocess, sys, time\n'
                      'p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])\n'
                      f'open({str(pidfile)!r}, "w").write(str(p.pid))\n'
                      'time.sleep(60)\n')
    binary.chmod(0o755)
    config = tmp_path / 'config'; config.write_text('synthetic')
    result = d.probe(0, root, tmp_path / 'raw', binary, config, {}, deadline=0.2)
    assert result['exit_status'] == 'timeout' and not result['parity']
    pid = int(pidfile.read_text())
    for _ in range(20):
        state = d.resources(pid)
        if state.get('exited') or state.get('state') == 'Z':
            break
        time.sleep(0.05)
    else:
        pytest.fail('timeout left a live descendant')
