"""Explicitly gated serial native logger fixture, never a population loop."""
import json
import os
from pathlib import Path

import pytest
from experiments.stringmol.locality_pilot import OBS, locality_environment, record
from experiments.stringmol.locality_process import execute


def test_directed_native_log_switches(tmp_path: Path) -> None:
    binary = os.environ.get('XL_LOGGING_FIXTURE')
    if binary is None:
        pytest.skip('directed native logger binary not supplied; not a native pass')
    cases = {'off': (False, False, False, False), 'on': (True, True, True, True),
             'conservation': (True, False, False, False),
             'scheduling': (True, True, False, False),
             'retirement': (True, False, True, False),
             'lineage': (True, False, False, True), 'lineage-alone': (False, False, False, True)}
    ordinary: dict[str, bytes] | None = None
    evidence: dict[str, object] = {}
    for name, (conservation, scheduling, retirement, lineage) in cases.items():
        root = tmp_path/name; root.mkdir()
        env = locality_environment(True)
        for key, enabled in [('STRINGMOL_CONSERVATION_LOG', conservation),
                             ('STRINGMOL_SCHEDULING_LOG', scheduling),
                             ('STRINGMOL_RETIREMENT_LOG', retirement)]:
            env[key] = str(int(enabled))
        if not lineage: env.pop('STRINGMOL_LINEAGE_LOG', None)
        if name == 'off': assert env == locality_environment(False)
        if name == 'on': assert env == locality_environment(True)
        result = execute([binary], cwd=root, environment=env, receipt=root/'process.json',
            stdout=root/'stdout.txt', stderr=root/'stderr.txt', timeout=30, output_root=root)
        assert result['exit_code'] == 0
        expected: set[str] = set()
        if conservation: expected |= {'conservation002.csv', 'conservation_buffers002.csv', 'material_events002.csv'}
        if scheduling: expected |= {'scheduling_events001.csv', 'xl_vm_end.csv', 'xl_rng_end.txt'}
        if retirement: expected.add('source_events006.csv')
        if lineage: expected |= {'lineage_events001.csv', 'lineage_snapshots001.csv'}
        actual = set(result['inventory']) & OBS
        assert actual == expected
        assert all((root/p).stat().st_size > 0 for p in expected)
        current = {p:(root/p).read_bytes() for p in ('ordinary-state.bin', 'ordinary-rng.txt', 'stdout.txt', 'stderr.txt')}
        if ordinary is None: ordinary = current
        else: assert ordinary == current
        evidence[name] = {'observers':sorted(actual), 'ordinary':{p:record(root/p) for p in current}}
    for name, bad_env in [('scheduling-without-material', {'STRINGMOL_CONSERVATION_LOG':'0'}),
                          ('retirement-without-material', {'STRINGMOL_CONSERVATION_LOG':'0','STRINGMOL_SCHEDULING_LOG':'0'}),
                          ('invalid-conservation', {'STRINGMOL_CONSERVATION_LOG':'invalid'}),
                          ('invalid-scheduling', {'STRINGMOL_SCHEDULING_LOG':'invalid'}),
                          ('invalid-retirement', {'STRINGMOL_RETIREMENT_LOG':'invalid'})]:
        root=tmp_path/name; root.mkdir()
        env=locality_environment(True); env.update(bad_env)
        result=execute([binary], cwd=root, environment=env, receipt=root/'process.json',
            stdout=root/'stdout.txt', stderr=root/'stderr.txt', timeout=30, output_root=root)
        assert isinstance(result['exit_code'], int) and result['exit_code'] != 0
        assert (root/'stderr.txt').stat().st_size > 0
        assert not (root/'ordinary-state.bin').exists()
        evidence[name]={'expected_native_rejection':True, 'receipt':record(root/'process.json')}
    (tmp_path/'qualification.json').write_text(json.dumps(evidence, sort_keys=True, indent=2))
