"""SM-B003 immutable development qualification and explicit launch boundary.

Raw data stays on Elements; POSIX controls stay in its mounted image. Development
is fixed to one previously used seed and is never a held-out-seed search.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

from experiments.stringmol import admission_design as design, admission_replay
from experiments.stringmol import conservation_workflow as c, retirement_workflow as inherited
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.analyze_conservation import initial_material
from experiments.stringmol.admission_journal import Header
from experiments.stringmol.configure_control import HOST, StringmolControlConfig, inoculum, render_config
from experiments.stringmol.native_testing import checked as native_checked

RAW = Path('/run/media/jojo/Elements/bio-sim-results')
POSIX = Path('/tmp/sm')
DEV_SEED = 202620999
NATIVE_TIMEOUT = 600
ANALYSIS_TIMEOUT = 1800
WORKERS = 6
NEW_LOGS = frozenset(('admission_events007.csv', 'vm_end007.csv'))
NATIVE = c.HERE / 'native'
PATCH = NATIVE / 'admission_integration.patch'
HEADERS = ('admission_adapter.h', 'admission_transaction.h', 'admission_journal.h')
PLAN = c.ROOT / 'reports/sm_b003_development_qualification_plan.md'
ARMS = tuple((schedule, policy) for schedule in design.Schedule for policy in design.Admission)


def checked(args: list[str], root: Path, name: str, timeout: int = 60) -> None:
    command = ['/usr/bin/env', '-i', *[f'{key}={value}' for key, value in c.ENV.items()], *args]
    native_checked(command, root, name, timeout)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def implementation() -> dict[str, Any]:
    paths = set(c.HERE.rglob('*.py')) | set(NATIVE.glob('*.h')) | {PATCH, PLAN}
    paths.update(inherited.PATCHES)
    paths.update((c.ROOT / 'tests').glob('*stringmol_admission*'))
    paths.add(c.ROOT / 'tests/stringmol_scheduling_rng.cpp')
    return {str(p.relative_to(c.ROOT)): c.record(p) for p in sorted(paths) if p.is_file()}


def storage(control: Path, raw: Path, *, preflight: bool = True) -> None:
    require(POSIX.is_mount() and (RAW / 'stringmol-posix.ext4').is_file(), 'Elements POSIX image is not mounted')
    require(control.resolve().is_relative_to(POSIX.resolve()), 'controls must remain on external POSIX image')
    require(raw.resolve().is_relative_to(RAW.resolve()) and not raw.resolve().is_relative_to(POSIX.resolve()), 'raw output must stay directly on Elements')
    require(POSIX.stat().st_dev != RAW.stat().st_dev, 'control/raw filesystem separation')
    require(shutil.disk_usage(POSIX).free >= (10 if preflight else 1) * 2**30, 'POSIX headroom')
    require(shutil.disk_usage(RAW).free >= (100 if preflight else 2) * 2**30, 'raw headroom')


def build(root: Path, upstream: Path) -> Path:
    root = root.resolve()
    storage(root, RAW / 'verification')
    require(not root.exists(), 'build directory already exists')
    require(len(str(root / 'candidate/config/ALXII.mtx')) < 80, 'matrix path exceeds inherited storage')
    inputs = implementation()
    root.mkdir(parents=True)
    c.seal(root / 'inputs.json', {'started_at': now(), 'implementation': inputs, 'pin': c.PIN})
    builds = {}
    for variant in ('baseline', 'candidate'):
        source = root / variant
        checked(['git', 'clone', '--no-hardlinks', '--no-checkout', str(upstream.resolve()), str(source)], root, variant+'-clone')
        checked(['git', '-C', str(source), 'checkout', '--detach', c.PIN], root, variant+'-checkout')
        for index, patch in enumerate(inherited.PATCHES):
            checked(['git', '-C', str(source), 'apply', str(patch)], root, f'{variant}-patch-{index+1}')
        if variant == 'candidate':
            checked(['git', '-C', str(source), 'apply', str(PATCH)], root, variant+'-patch-7')
            for name in HEADERS:
                shutil.copyfile(NATIVE / name, source / 'src' / name)
        for folder in ('debug', 'release', 'output'):
            (source / folder).mkdir(exist_ok=True)
        checked(['bash', 'RunCatchTests.sh'], source / 'tests', 'upstream-tests', timeout=600)
        require('All tests passed' in (source / 'tests/upstream-tests.stdout').read_text(), 'upstream test receipt')
        checked(['make', '-B', '-C', str(source / 'src'), '-j4', f'OUTPUT_DIR={source / "release"}',
                 *[f'{key}={value}' for key, value in c.FLAGS.items()]], root, variant+'-build', timeout=600)
        objects = c.release_objects(source)
        renamed = root / f'{variant}-main.o'
        runner = root / f'{variant}-rng'
        checked(['objcopy', '--redefine-sym', 'main=sm_b001_native_main', str(source / 'release/stringmol.o'), str(renamed)], root, variant+'-rename')
        checked(['g++', '-O3', '-Wall', '-Wunused', '-std=c++11', '-isystem', str(source / 'src'),
                 str(c.ROOT / 'tests/stringmol_scheduling_rng.cpp'), str(renamed),
                 *[str(source / 'release' / name) for name in sorted(objects) if name != 'stringmol.o'],
                 '-o', str(runner)], root, variant+'-link')
        builds[variant] = {'source': str(source), 'state': c.source_state(source), 'runner': str(runner), 'runner_record': c.record(runner),
                           'binary': c.record(source / 'release/stringmol'), 'objects': objects, 'renamed_main': c.record(renamed),
                           'matrix': c.record(source / 'config/ALXII.mtx')}
    require(implementation() == inputs, 'implementation changed during build')
    c.seal(root / 'build.json', {'pin': c.PIN, 'implementation': inputs, 'flags': c.FLAGS, 'builds': builds,
                               'completed_at': now(), 'compilers': {compiler: c.command([compiler, '--version'], root).decode() for compiler in ('gcc', 'g++')}})
    return root / 'build.json'


def verify_build(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = c.read(path)
    require(data['pin'] == c.PIN and data['implementation'] == implementation() and data['flags'] == c.FLAGS, 'build/source drift')
    require(set(data['builds']) == {'baseline', 'candidate'}, 'build variants')
    for variant, entry in data['builds'].items():
        source = Path(entry['source'])
        require(c.source_state(source) == entry['state'], 'native source drift')
        require(c.record(Path(entry['runner'])) == entry['runner_record'] and c.record(source / 'release/stringmol') == entry['binary'], 'binary drift')
        require(c.record(path.parent / f'{variant}-main.o') == entry['renamed_main'], 'renamed main drift')
        require(c.record(source / 'config/ALXII.mtx') == entry['matrix'], 'matrix drift')
        c.verify_release_objects(source, entry['objects'])
    return data


def environment(schedule: design.Schedule, policy: design.Admission, variant: str) -> dict[str, str]:
    require(variant in ('observed', 'off', 'repeat', 'baseline'), 'execution variant')
    require(variant != 'baseline' or policy is design.Admission.NATIVE, 'baseline has no stratified intervention')
    return {**inherited.environment(schedule.value+'_RETAIN'), 'STRINGMOL_CONSERVATION_LOG': '1',
            'STRINGMOL_ADMISSION': '0' if variant == 'baseline' else '1', 'STRINGMOL_ADMISSION_POLICY': policy.value,
            'STRINGMOL_ADMISSION_LOG': '0' if variant in ('off', 'baseline') else '1'}


def expected_initial() -> tuple[dict[str, Any], dict[int, tuple[int, int]]]:
    cells, _ = inoculum()
    initial = initial_material([{'id': i, 'sequence_hex': HOST.encode().hex()} for i in range(len(cells))], 'histogram', 0)
    return initial, dict(enumerate(cells))


def scientific_files(directory: Path, *, observer: bool) -> dict[str, Any]:
    # Parity includes all scientific CSVs and every MT word; new observer files
    # are excluded only when comparing observation off or the old interpreter.
    files = [p for p in directory.iterdir() if (p.suffix == '.csv' and (observer or p.name not in NEW_LOGS)) or p.name == 'final_rng.txt']
    require((directory / 'final_rng.txt').is_file(), 'missing final RNG')
    return {p.name: c.record(p) for p in sorted(files)}


def execute_one(job: dict[str, Any], control: Path, raw: Path) -> dict[str, Any]:
    directory = Path(job['directory'])
    started = now(); before = time.monotonic()
    status: int | None = None
    error: str | None = None
    created = False
    try:
        storage(control, raw, preflight=False)
        directory.mkdir(parents=True, exist_ok=False)
        created = True
        (directory / 'config.conf').write_text(job['config'], encoding='ascii')
        with (directory / 'native.stdout').open('xb') as out, (directory / 'native.stderr').open('xb') as err:
            process = subprocess.run(job['command'], cwd=directory, env=job['environment'], stdout=out, stderr=err, timeout=NATIVE_TIMEOUT)
            status = process.returncode
    except subprocess.TimeoutExpired:
        error = 'native timeout'
    except (OSError, ValueError) as failure:
        error = f'{type(failure).__name__}: {failure}'
    native_seconds = time.monotonic()-before
    files: dict[str, Any] = {}
    try:
        if created: files = c.inventory(directory)
    except (OSError, ValueError) as failure:
        error = f'inventory {type(failure).__name__}: {failure}'
    successful = (error is None and status == 0 and {'native.stdout', 'native.stderr'} <= files.keys() and
                  not (directory / 'native.stderr').read_bytes() and b'FINISHED smspatial' in (directory / 'native.stdout').read_bytes())
    if not successful and error is None: error = 'native exit/stderr/completion failure'
    result = {'job': job, 'started_at': started, 'completed_at': now(), 'exit_status': status, 'error': error,
              'success': successful, 'native_seconds': native_seconds, 'execution_inventory_seconds': time.monotonic()-before,
              'bytes': sum(entry['size'] for entry in files.values()), 'files': files}
    receipt = control / 'executions' / (job['key']+'.json')
    receipt.parent.mkdir(parents=True, exist_ok=True)
    c.seal(receipt, result)
    return result


def analyze_job(job: dict[str, Any], matrix: Path, output: Path, files: dict[str, Any], exit_status: int) -> None:
    require(exit_status == 0, 'failed native execution cannot be analyzed as successful')
    directory = Path(job['directory'])
    require(c.inventory(directory) == files, 'analysis input inventory drift')
    require((directory / 'config.conf').read_text(encoding='ascii') == job['config'] ==
            render_config(StringmolControlConfig('host-only', int(job['seed']), 0, 0, mutation_rate=0), matrix), 'analysis configuration identity')
    initial, coords = expected_initial()
    header = design.Schedule(job['schedule']), design.Admission(job['policy'])
    result = admission_replay.replay(directory, initial, coords,
        Header(header[1], header[0]), int(job['seed']), matrix, decay=.0005, exit_status=exit_status)
    require(c.inventory(directory) == files, 'analysis inputs changed during replay')
    c.seal(output, result)


def develop(build_path: Path, control: Path, raw: Path) -> Path:
    control, raw = control.resolve(), raw.resolve()
    storage(control, raw)
    data = verify_build(build_path)
    require(not control.exists() and not raw.exists(), 'development attempt already exists')
    control.mkdir(parents=True); raw.mkdir(parents=True)
    matrix = Path(data['builds']['candidate']['source']) / 'config/ALXII.mtx'
    config = render_config(StringmolControlConfig('host-only', DEV_SEED, 0, 0, mutation_rate=0), matrix)
    jobs = []
    for schedule, policy in ARMS:
        arm = schedule.value+'_'+policy.value
        for variant in ('observed', 'off', 'repeat', *(('baseline',) if policy is design.Admission.NATIVE else ())):
            entry = data['builds']['baseline' if variant == 'baseline' else 'candidate']
            jobs.append({'key': arm+'_'+variant, 'schedule': schedule.value, 'policy': policy.value, 'seed': DEV_SEED,
                         'variant': variant, 'directory': str(raw / arm / variant), 'config': config,
                         'command': [entry['runner'], '30', 'config.conf'], 'environment': environment(schedule, policy, variant)})
    require(len(jobs) == 20, 'fixed development denominator')
    plan = {'started_at': now(), 'build': str(build_path.resolve()), 'build_record': c.record(build_path), 'implementation': implementation(),
            'plan_record': c.record(PLAN), 'workers': WORKERS, 'native_timeout': NATIVE_TIMEOUT, 'analysis_timeout': ANALYSIS_TIMEOUT, 'jobs': jobs}
    c.seal(control / 'plan.json', plan)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(lambda job: execute_one(job, control, raw), jobs))
    c.seal(control / 'executions.json', results)
    require(all(r['success'] for r in results), 'development native execution failure; all attempts retained')
    require(all(r['execution_inventory_seconds'] < NATIVE_TIMEOUT for r in results), 'development execution/inventory budget')
    for schedule, policy in ARMS:
        folder = raw / (schedule.value+'_'+policy.value)
        require(scientific_files(folder/'observed', observer=True) == scientific_files(folder/'repeat', observer=True), 'development deterministic repeat')
        require(scientific_files(folder/'observed', observer=False) == scientific_files(folder/'off', observer=False), 'development observer isolation')
        require(all(not (folder/'off'/name).exists() for name in NEW_LOGS), 'observer-off emitted private logs')
        if policy is design.Admission.NATIVE:
            require(scientific_files(folder/'observed', observer=False) == scientific_files(folder/'baseline', observer=False), 'development pinned native parity')
    analyses = []
    for job, execution in zip(jobs, results, strict=True):
        if job['variant'] != 'observed': continue
        outputs = []
        for repetition in ('analysis', 'analysis-repeat'):
            output = control / (job['key']+'-'+repetition+'.json')
            input_path = control / (job['key']+'-'+repetition+'-input.json')
            c.seal(input_path, {'job': job, 'matrix': str(matrix), 'output': str(output), 'files': execution['files'], 'exit_status': execution['exit_status']})
            stats = control / (job['key']+'-'+repetition+'-resources.txt')
            args = ['/usr/bin/time', '-v', '-o', str(stats), sys.executable, '-m', 'experiments.stringmol.admission_workflow', 'analyze', str(input_path)]
            started = time.monotonic()
            checked(args, c.ROOT, str(control / (job['key']+'-'+repetition+'-process')), timeout=ANALYSIS_TIMEOUT)
            outputs.append(c.read(output))
            c.seal(control / (job['key']+'-'+repetition+'-receipt.json'), {'seconds': time.monotonic()-started, 'result': c.record(output), 'resources': c.record(stats)})
        require(outputs[0] == outputs[1], 'independent process replay disagreement')
        analyses.append({'key': job['key'], 'result': outputs[0]})
    require(implementation() == plan['implementation'] and c.record(build_path) == plan['build_record'], 'development inputs changed')
    for result in results:
        require(c.inventory(Path(result['job']['directory'])) == result['files'], 'development output drift')
    replacements = [item['result'] for item in analyses if 'STRATIFIED_REPLACE' in item['key']]
    opportunity = len(replacements) == 2 and all(r['partial_opportunities'] == r['partial_commits'] and r['partial_commits'] >= 100 for r in replacements)
    receipt = {'completed_at': now(), 'integrity': True, 'opportunity_qualified': opportunity,
               'execution_denominator': 20, 'seed': DEV_SEED, 'analyses': analyses,
               'max_execution_inventory_seconds': max(r['execution_inventory_seconds'] for r in results),
               'total_raw_bytes': sum(r['bytes'] for r in results), 'population_launch_eligible': False}
    c.seal(control / 'development.json', receipt)
    return control / 'development.json'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    build_parser = sub.add_parser('build'); build_parser.add_argument('root', type=Path); build_parser.add_argument('upstream', type=Path)
    dev = sub.add_parser('develop'); dev.add_argument('build', type=Path); dev.add_argument('control', type=Path); dev.add_argument('raw', type=Path)
    analysis = sub.add_parser('analyze'); analysis.add_argument('input', type=Path)
    args = parser.parse_args()
    if args.action == 'build': print(build(args.root, args.upstream))
    elif args.action == 'develop': print(develop(args.build, args.control, args.raw))
    else:
        data = c.read(args.input)
        analyze_job(data['job'], Path(data['matrix']), Path(data['output']), data['files'], data['exit_status'])


if __name__ == '__main__':
    main()
