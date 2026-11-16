"""SM-XP001 bounded development reaction qualification; no confirmation API."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from experiments.stringmol.configure_control import HOST
from experiments.stringmol.analyze_conservation import initial_material
from experiments.stringmol.analyze_retirement import SourceReplay

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path('/tmp/sm/xp-e')
RAW = Path('/run/media/jojo/Elements/bio-sim-results/sm-xp001-exploration-v1')

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path: Path, value: object) -> None:
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')

def preflight() -> None:
    mounts = subprocess.check_output(['findmnt', '-rn', '-o', 'TARGET,SOURCE,FSTYPE'], text=True)
    assert '/run/media/jojo/Elements /dev/' in mounts
    assert '/tmp/sm /run/media/jojo/Elements/bio-sim-results/stringmol-posix.ext4 ' in mounts
    assert shutil.disk_usage(EVIDENCE).free >= 5 * 1024**3
    assert shutil.disk_usage(RAW.parent).free >= 10 * 1024**3

def command(args: list[str], cwd: Path, label: str, timeout: int = 600, overrides: dict | None = None, working_dir: Path | None = None) -> int | None:
    env = {k: v for k, v in os.environ.items() if not k.startswith(('STRINGMOL_', 'SM_'))}
    env.update(overrides or {})
    with (cwd / (label+'.stdout')).open('xb') as out, (cwd / (label+'.stderr')).open('xb') as err:
        try:
            p = subprocess.run(args, cwd=working_dir or cwd, env=env, stdout=out, stderr=err, timeout=timeout)
            result = {'args': args, 'environment_overrides': overrides or {}, 'returncode': p.returncode, 'timeout': False}
        except (subprocess.TimeoutExpired, OSError) as e:
            result = {'args': args, 'returncode': None, 'timeout': isinstance(e, subprocess.TimeoutExpired), 'error': str(e)}
    save(cwd / (label+'.receipt.json'), result)
    return result['returncode']

def build() -> None:
    preflight()
    root = EVIDENCE/'native-v2'
    root.mkdir()
    shutil.copytree('/tmp/sm/a7/src', root/'src')
    shutil.copyfile('/tmp/sm/a7/config/ALXII.mtx', root/'ALXII.mtx')
    shutil.copyfile(ROOT/'tests/stringmol_xp001_reaction.cpp', root/'fixture.cpp')
    inputs = {str(p.relative_to(root)): digest(p) for p in root.rglob('*') if p.is_file()}
    save(root/'inputs.json', inputs)
    objects = root/'objects'; objects.mkdir()
    assert command(['make', '-B', '-C', str(root/'src'), '-j2', f'OUTPUT_DIR={objects}',
                    'CC=g++ -std=c++11 -O1 -g -Wall', 'C4C=gcc -O1 -g -Wall'], root, 'build') == 0
    args = ['g++', '-std=c++11', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-isystem', str(root/'src'),
            str(root/'fixture.cpp'), *map(str, sorted(p for p in objects.glob('*.o') if p.name != 'stringmol.o')),
            '-lm', '-o', str(root/'reaction')]
    assert command(args, root, 'link') == 0
    save(root/'build.json', {'inputs': inputs, 'binary': digest(root/'reaction'), 'matrix': digest(root/'ALXII.mtx')})

def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))

def initial(sequences: list[str], amount: int = 0) -> dict:
    expected = [{'id': i, 'sequence_hex': s.encode().hex()} for i, s in enumerate(sequences)]
    return initial_material(expected, 'histogram', amount)

def replay(directory: Path, sequences: list[str], amount: int = 0) -> dict:
    state = SourceReplay(initial(sequences, amount))
    checkpoints = rows(directory/'conservation002.csv')
    material = rows(directory/'material_events002.csv')
    assert len(checkpoints) == 2 and checkpoints[0]['event'] == 'START' and checkpoints[-1]['event'] == 'END'
    state.material.checkpoint(checkpoints[0])
    for row in material:
        state.step(row)
    state.material.checkpoint(checkpoints[-1])
    final = json.loads((directory/'summary.json').read_text())
    assert {str(i): b.hex().upper() for i, b in state.material.buffers.items()} == final['buffers']
    return {'conserved': True, 'events': len(material), 'births': len(state.edges),
            'exact_host_children': sum(bytes.fromhex(b).split(b'\0', 1)[0] == HOST.encode()
                                       for i, b in final['buffers'].items() if int(i) >= 2),
            'final_visible': {i: bytes.fromhex(b).split(b'\0', 1)[0].decode() for i, b in final['buffers'].items()},
            'transfer': state.transfer_summary()}

def inventory(directory: Path) -> dict:
    return {p.name: digest(p) for p in directory.iterdir() if p.is_file()}

def assays() -> None:
    preflight()
    native = EVIDENCE/'native-v2'
    receipt = json.loads((native/'build.json').read_text())
    assert receipt['binary'] == digest(native/'reaction')
    assert receipt['matrix'] == digest(native/'ALXII.mtx')
    root = RAW/'reactions-v2'; root.mkdir(parents=True)
    cases = [(a+b, seed, repeat, observed) for a, b in [('H','H'), ('H','B'), ('B','H'), ('B','B')]
             for seed in [1,2] for repeat, observed in [(0,1), (1,1), (0,0)]]
    save(root/'freeze.json', {'cases': cases, 'sequences': {'H': HOST, 'B': 'B'}, 'cap': 5000, 'pool_mode': 'histogram', 'pool_amount': 16,
                             'binary': receipt, 'plan': digest(ROOT/'reports/sm_xp001_reaction_recovery_plan.md')})
    results = []
    for pair, seed, repeat, observed in cases:
        directory = root/f'{pair}-s{seed}-r{repeat}-o{observed}'; directory.mkdir()
        seq = [HOST if c=='H' else 'B' for c in pair]
        args = [str(native/'reaction'), *seq, str(seed), str(native/'ALXII.mtx'), str(observed), 'summary.json', 'histogram', '16']
        rc = command(args, directory, 'native')
        result = {'pair': pair, 'seed': seed, 'repeat': repeat, 'observed': observed, 'returncode': rc}
        if rc == 0:
            try:
                result['native'] = json.loads((directory/'summary.json').read_text())
                if observed:
                    result['replay'] = replay(directory, seq, 16)
            except Exception as error:
                result['analysis_error'] = repr(error)
        results.append(result)
        save(directory.with_suffix('.inventory.json'), inventory(directory))
    save(root/'results.json', results)
    valid = all(r['returncode']==0 and 'analysis_error' not in r for r in results)
    repeats = isolation = True
    for pair in ['HH','HB','BH','BB']:
        for seed in [1,2]:
            dirs = [root/f'{pair}-s{seed}-r{r}-o{o}' for r,o in [(0,1),(1,1),(0,0)]]
            enabled = [{k:v for k,v in inventory(d).items() if k != 'native.receipt.json'} for d in dirs[:2]]
            repeats &= enabled[0] == enabled[1]
            for name in ['summary.json','final-rng.txt','native.stdout','native.stderr']:
                isolation &= len({digest(d/name) for d in dirs if (d/name).exists()})==1 and all((d/name).exists() for d in dirs)
    observed = [r for r in results if r['observed'] and r['repeat']==0]
    positive = all(r.get('replay',{}).get('exact_host_children',0)>=1 and r.get('native',{}).get('stop')!='CAP'
                   for r in observed if r['pair']=='HH')
    nonproductive = all(r.get('replay',{}).get('exact_host_children',0)==0 for r in observed if r['pair']!='HH')
    save(root/'gate.json', {'valid': valid, 'deterministic': repeats, 'observation_isolation': isolation,
                           'canonical_positive': positive, 'candidate_nonproductive': nonproductive,
                           'population_authorized_by_reaction_gate': valid and repeats and isolation and positive and nonproductive,
                           'population_executions': 0})

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['build','assays']); args=p.parse_args()
    {'build':build, 'assays':assays}[args.action]()
if __name__=='__main__':
    main()
