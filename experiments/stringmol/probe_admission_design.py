"""Development-only SM-B003 selector/RNG qualification; no population execution."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

from experiments.stringmol import admission_design as a, conservation_workflow as c
from experiments.stringmol import recover_retirement as r, recover_retirement_io as io
from experiments.stringmol import retirement_workflow as w
from experiments.stringmol.analyze_conservation import MAXL0
from experiments.stringmol.analyze_lineage import require

LAYOUTS = ('APUU..', 'APUUUU', 'AP....', 'APXY..', 'APXYUU', 'APHHZZ', 'APU...', 'AP..U.')
CONTROL = io.IMAGE / 'sm-b003-selection-v1'
PORTABLE = io.STORE / 'verification/sm-b003-selection-v1'
INPUTS = ('experiments/stringmol/admission_design.py', 'experiments/stringmol/probe_admission_design.py',
          'tests/stringmol_admission_selection.cpp', 'tests/test_stringmol_admission_design.py',
          'reports/sm_b003_admission_replacement_design.md')


def slots(layout: str) -> tuple[a.Slot, ...]:
    cells = []
    for identity, label in enumerate(layout):
        actor = None
        if label != '.':
            role = a.Role.ACTIVE if label in 'AX' else a.Role.PASSIVE if label in 'PY' else a.Role.UNBOUND
            partner = {'A': 'P', 'P': 'A', 'X': 'Y', 'Y': 'X'}.get(label)
            prefix = b'\0BB' if label == 'H' else b'' if label == 'Z' else b'A\0BB'
            actor = a.Actor(identity, prefix + bytes(MAXL0 - len(prefix)), role,
                            layout.index(partner) if partner is not None else None,
                            eligible_tick=5000 if label == 'U' else 0)
        cells.append(a.Slot(identity // 2, identity % 2, actor))
    return tuple(cells)


def invoke(binary: Path, mode: str, seed: int, parameter: str) -> tuple[dict[str, Any], bytes]:
    raw = subprocess.check_output([str(binary), mode, str(seed), parameter], env=c.ENV, timeout=10)
    path = PORTABLE / 'raw' / f'{seed}-{mode}-{parameter}.txt'
    path.write_bytes(raw)
    header, state = raw.split(b'\n', 1)
    parsed: dict[str, Any] = json.loads(header)
    return parsed, state


def main() -> None:
    io.mounts()
    require(not CONTROL.exists() and not PORTABLE.exists(), 'retain previous probes; no overwrite')
    commit = c.command(['git', 'rev-parse', 'HEAD'], c.ROOT).decode().strip()
    files = {}
    for relative in INPUTS:
        path = c.ROOT / relative
        require(c.command(['git', 'show', f'{commit}:{relative}'], c.ROOT) == path.read_bytes(), 'commit design/probe before execution')
        files[relative] = c.record(path)
    source = io.IMAGE / 'b/observer'
    rng = source / 'release/mt19937-2.o'
    header = source / 'src/mt19937-2.h'
    wrapper = source / 'release/randutil.o'
    wrapper_source = source / 'src/randutil.cpp'
    gates_path = io.IMAGE / 'r1/preflight/gates.json'
    preparation = c.read(io.IMAGE / 'r1/prepared/preparation.json')
    require(c.record(gates_path) == preparation['gates_record'], 'historical native gate seal')
    artifacts = c.read(gates_path)['artifacts']
    for path in (rng, header, wrapper, wrapper_source):
        require(c.record(path) == artifacts[str(path)], 'pinned native RNG input changed')
    linkage = subprocess.check_output(['nm', '-u', str(wrapper)], env=c.ENV)
    require(b'U GenerateRandomDouble' in linkage and wrapper_source.read_text().count('GenerateRandomDouble()') == 1,
            'native uniform wrapper must call the pinned MT generator')
    CONTROL.mkdir(); PORTABLE.mkdir(); (PORTABLE / 'raw').mkdir()
    binary = CONTROL / 'selection-probe'
    command = ['g++', '-std=c++11', '-O2', '-Wall', '-Wextra', '-Werror', '-I', str(header.parent),
               str(c.ROOT / 'tests/stringmol_admission_selection.cpp'), str(rng), '-o', str(binary)]
    plan = {'scope': 'synthetic selector/RNG mechanics, not native population admission', 'source_commit': commit,
            'files': files, 'native_inputs': {str(p): c.record(p) for p in (rng, header, wrapper, wrapper_source)},
            'uniform_linkage': linkage.decode(),
            'layouts': LAYOUTS, 'synthetic_rng_seeds': list(range(1, 65)), 'command': command,
            'environment': c.ENV, 'working_tree': c.command(['git', 'status', '--porcelain'], c.ROOT).decode(),
            'population_assays_executed': 0, 'launch_authorized': False}
    c.seal(CONTROL / 'plan.json', plan)
    completed = subprocess.run(command, env=c.ENV, capture_output=True, check=False)
    (PORTABLE / 'build.stdout').write_bytes(completed.stdout)
    (PORTABLE / 'build.stderr').write_bytes(completed.stderr)
    require(completed.returncode == 0, 'native selector fixture build failed')
    checked = 0
    coverage: set[str] = set()
    for seed in range(1, 65):
        references = [invoke(binary, 'reference', seed, str(count)) for count in range(3)]
        for count, (_, state) in enumerate(references):
            path = PORTABLE / 'raw' / f'{seed}-reference-{count}.rng'
            path.write_bytes(state)
            w.validate_final_rng(path)
        for layout in LAYOUTS:
            world = slots(layout)
            for mode in a.Admission:
                native, state = invoke(binary, mode.value, seed, layout)
                values = references[2][0]['values']
                if mode is a.Admission.NATIVE:
                    channel = None
                    has_candidates = any(cell.actor is None for cell in world)
                    rank = values[0] if has_candidates else None
                else:
                    channel = values[0]
                    has_candidates = ('U' in layout) if channel < 0.5 else ('.' in layout)
                    rank = values[1] if has_candidates else None
                expected = a.plan(mode, world, 3, 2, (0, 1), channel_draw=channel, rank_draw=rank)
                target = -1 if expected.target is None else expected.target[0] * 2 + expected.target[1]
                require(native == {'channel': expected.channel.value, 'disposition': expected.disposition.value,
                                   'target': target, 'candidate_count': len(expected.candidates),
                                   'values': references[expected.draws][0]['values']}, 'native/Python selector mismatch')
                require(state == references[expected.draws][1], 'complete native RNG state differs')
                coverage.add(expected.disposition.value)
                checked += 1
        print(f'Synthetic RNG seed {seed}: {checked} selector checks passed', flush=True)
    require(coverage == {outcome.value for outcome in a.Disposition}, 'missing selector outcome coverage')
    require(all(c.record(c.ROOT / name) == record for name, record in files.items()), 'probe source changed')
    report = {'selector_checks': checked, 'reference_rng_checks': 64 * 3, 'passed': True,
              'population_assays_executed': 0, 'native_adapter_implemented': False, 'launch_authorized': False,
              'remaining': ['native atomic adapter', 'ordered independent admission replay', 'fault/adversarial gates',
                            'population development opportunity qualification', 'final preregistration and unseen execution audit'],
              'coverage': sorted(coverage), 'binary': c.record(binary), 'plan': c.record(CONTROL / 'plan.json'),
              'raw_inventory': c.inventory(PORTABLE / 'raw')}
    c.seal(CONTROL / 'report.json', report)
    for name in ('plan.json', 'report.json'):
        target_path = PORTABLE / name
        target_path.write_bytes((CONTROL / name).read_bytes())
        require(c.record(target_path) == c.record(CONTROL / name), 'portable probe export differs')
    print(json.dumps({key: value for key, value in report.items() if key != 'raw_inventory'}), flush=True)


if __name__ == '__main__':
    main()
