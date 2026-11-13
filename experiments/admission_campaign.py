"""SM-B003 once-only campaign orchestration; qualified simulator/replay untouched."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from typing import Any

from experiments.admission_seed_audit import audit
from experiments.stringmol import admission_workflow as w, admission_design as d, conservation_workflow as c
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.configure_control import StringmolControlConfig, render_config

QUALIFIED = 'a663885635ee79d03d1db8655e5cef2a64a02114'
HISTORY = Path('/var/home/jojo/bio-sim-proto')
PROTOCOL = 'reports/sm_b003_admission_replacement_preregistration.md'
QUALIFICATION = 'experiments/sm_b003_qualification.json'
EXTRA = (PROTOCOL, QUALIFICATION, 'experiments/admission_campaign.py', 'experiments/admission_seed_audit.py',
         'tests/test_admission_campaign.py', 'tests/test_admission_seed_audit.py')
METRICS = ('qualifying_transfers', 'transfer_renewing_descendants', 'serial_transfers', 'max_nonrelocation_depth',
           'late_transfer_renewing_descendants', 'retained_late_transfer_renewals')


def source(*, published: bool) -> dict[str, Any]:
    revision = c.command(['git', 'rev-parse', 'HEAD'], c.ROOT).decode().strip()
    files = w.implementation() | {path: c.record(c.ROOT/path) for path in EXTRA}
    for path, expected in files.items():
        committed = c.command(['git', 'show', revision+':'+path], c.ROOT)
        require({'size': len(committed), 'sha256': c.digest(committed)} == expected, 'uncommitted implementation: '+path)
    if published:
        remote = c.command(['git', 'ls-remote', 'origin', 'refs/heads/main'], c.ROOT).decode().split()
        require(remote == [revision, 'refs/heads/main'], 'actual origin/main differs from implementation')
    return {'revision': revision, 'files': files}


def qualified() -> dict[str, Any]:
    pins = c.read(c.ROOT/QUALIFICATION)
    require(pins['qualified_revision'] == QUALIFIED, 'qualification source identity')
    for item in pins['evidence']:
        require(c.record(Path(item['path'])) == {k: item[k] for k in ('size', 'sha256')}, 'qualification evidence changed')
    build = w.verify_build(Path(pins['build']))
    for path, expected in build['implementation'].items():
        original = c.command(['git', 'show', QUALIFIED+':'+path], c.ROOT)
        require({'size': len(original), 'sha256': c.digest(original)} == expected, 'qualified byte identity')
    result = c.read(Path(pins['development']))
    require(result['integrity'] is True and result['opportunity_qualified'] is True and result['execution_denominator'] == 20 and
            result['seed'] == w.DEV_SEED and len(result['analyses']) == 6, 'development qualification failed')
    return build


def jobs(raw: Path, build: dict[str, Any]) -> list[dict[str, Any]]:
    entry = build['builds']['candidate']
    matrix = Path(entry['source'])/'config/ALXII.mtx'
    rows = []
    for schedule, policy, seed in d.MATRIX:
        key = f'{schedule.value}_{policy.value}_{seed}'
        rows.append({'key': key, 'schedule': schedule.value, 'policy': policy.value, 'seed': seed,
                     'variant': 'observed', 'directory': str(raw/schedule.value/policy.value/str(seed)),
                     'config': render_config(StringmolControlConfig('host-only', seed, 0, 0, mutation_rate=0), matrix),
                     'command': [entry['runner'], '30', 'config.conf'], 'environment': w.environment(schedule, policy, 'observed')})
    require(len(rows) == len({r['key'] for r in rows}) == 120, 'frozen input denominator')
    return rows


def prepare(control: Path, raw: Path) -> None:
    control, raw = control.resolve(), raw.resolve()
    w.storage(control, raw)
    closure, build = source(published=True), qualified()
    require(not control.exists() and not raw.exists(), 'campaign paths already exist')
    control.mkdir(parents=True)
    rows = jobs(raw, build)
    for row in rows: c.seal(control/(row['key']+'-input.json'), row)
    plan = {'created_at': w.now(), 'source': closure, 'control': str(control), 'raw': str(raw), 'runs': rows,
            'matrix': str(Path(build['builds']['candidate']['source'])/'config/ALXII.mtx'),
            'workers': 6, 'native_timeout': 600, 'analysis_timeout': 1800, 'launch_authorized': False}
    c.seal(control/'preparation.json', plan)
    c.seal(control/'preparation.sha256.json', c.record(control/'preparation.json'))


def verify(control: Path, *, published: bool = False) -> dict[str, Any]:
    plan: dict[str, Any] = c.read(control/'preparation.json')
    require(c.record(control/'preparation.json') == c.read(control/'preparation.sha256.json'), 'preparation seal')
    require(plan['control'] == str(control.resolve()), 'control identity')
    require(plan['source'] == source(published=published), 'campaign source changed')
    build = qualified()
    require(plan['runs'] == jobs(Path(plan['raw']), build), 'frozen matrix/input identity')
    require(plan['matrix'] == str(Path(build['builds']['candidate']['source'])/'config/ALXII.mtx'), 'matrix path identity')
    require((plan['workers'], plan['native_timeout'], plan['analysis_timeout'], plan['launch_authorized']) == (6, 600, 1800, False), 'operational limits')
    for row in plan['runs']:
        require(c.read(control/(row['key']+'-input.json')) == row, 'sealed per-input identity')
    return plan


def authorized_files(control: Path, plan: dict[str, Any]) -> dict[Path, dict[str, Any]]:
    paths = [control/'preparation.json', control/'preparation.sha256.json',
             *[control/(row['key']+'-input.json') for row in plan['runs']]]
    return {path: c.record(path) for path in paths}


def audit_roots() -> tuple[Path, ...]:
    return (HISTORY/'runs', HISTORY/'sweeps', w.RAW, w.POSIX, HISTORY/'.git', HISTORY/'.venv')


def eligible(control: Path) -> None:
    plan = verify(control, published=True)
    w.storage(control, Path(plan['raw']))
    require(not Path(plan['raw']).exists() and not (control/'LAUNCHED.json').exists(), 'prior execution')
    result = audit(audit_roots(), d.SEEDS, allowed=authorized_files(control, plan),
                   progress=lambda row: print(json.dumps(row), flush=True))
    c.seal(control/'freshness-audit.json', result)
    require(result['passed'] is True, 'freshness audit blocks launch; evidence retained')
    require(verify(control, published=True) == plan, 'preparation drift during audit')
    c.seal(control/'eligibility.json', {'eligible': True, 'completed_at': w.now(), 'source': plan['source'],
                                      'preparation': c.record(control/'preparation.json'), 'audit': c.record(control/'freshness-audit.json')})


def execution_ready(control: Path, plan: dict[str, Any]) -> None:
    receipt = c.read(control/'eligibility.json')
    require(receipt['eligible'] is True and receipt['source'] == plan['source'] and receipt['preparation'] == c.record(control/'preparation.json'), 'eligibility binding')
    require(receipt['audit'] == c.record(control/'freshness-audit.json'), 'audit seal drift')
    checked = c.read(control/'freshness-audit.json')
    require(checked['passed'] is True and checked['matches'] == [] and checked['reserved_values'] == list(d.SEEDS), 'audit result/seed identity')
    require(checked['scope'] == [str(p.resolve()) for p in audit_roots()] and
            checked['authorized_files'] == {str(p): record for p, record in authorized_files(control, plan).items()}, 'audit scope/exclusion identity')
    for stamp in (receipt['completed_at'], checked['completed_at']):
        age = (datetime.now(timezone.utc)-datetime.fromisoformat(stamp)).total_seconds()
        require(0 <= age <= 180, 'launch eligibility expired; a new audit is required')
    require(not Path(plan['raw']).exists() and not (control/'LAUNCHED.json').exists(), 'once-only execution')


def run(control: Path) -> None:
    plan = verify(control, published=True)
    w.storage(control, Path(plan['raw']))
    execution_ready(control, plan)
    # Exclusive reservation precedes both directory creation and any native child.
    c.seal(control/'LAUNCHED.json', {'started_at': w.now(), 'preparation': c.record(control/'preparation.json'),
                                   'eligibility': c.record(control/'eligibility.json'), 'intended_denominator': 120})
    Path(plan['raw']).mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda job: w.execute_one(job, control, Path(plan['raw'])), plan['runs']))
    c.seal(control/'executions.json', results)
    c.seal(control/'native-complete.json', {'completed_at': w.now(), 'attempt_records': len(results),
                                          'successful_exits': sum(r['success'] for r in results), 'execution_inventory': c.record(control/'executions.json')})


def analysis_process(input_path: Path, prefix: Path, *, timeout: float = 1800) -> dict[str, Any]:
    command = ['/usr/bin/time', '-v', '-o', str(prefix)+'.resources.txt', sys.executable,
               '-m', 'experiments.stringmol.admission_workflow', 'analyze', str(input_path)]
    timed_out = False
    # Keep the whole process group under the deadline, including /usr/bin/time.
    with Path(str(prefix)+'.json').open('x') as record, Path(str(prefix)+'.stdout').open('xb') as out, Path(str(prefix)+'.stderr').open('xb') as err:
        try:
            with Path(str(prefix)+'.resources.txt').open('x'): pass
            process = subprocess.Popen(command, cwd=c.ROOT, env=c.ENV, stdout=out, stderr=err, start_new_session=True)
        except OSError as error:
            json.dump({'command': command, 'exit_status': None, 'error': str(error)}, record)
            raise
        try:
            status = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            status = process.wait()
        receipt = {'command': command, 'exit_status': status, 'timed_out': timed_out}
        json.dump(receipt, record)
    return receipt


def outcome(job: dict[str, Any], result: dict[str, Any]) -> d.Outcome:
    def continuity(name: str) -> d.Continuity:
        return d.Continuity(*(result[name][key] for key in METRICS))
    row = d.Outcome(d.Schedule(job['schedule']), d.Admission(job['policy']), job['seed'], True,
                    continuity('all_admission'), continuity('replacement_only'), result['partial_opportunities'], result['partial_commits'])
    require(row.valid, 'invalid derived scientific outcome')
    return row


def analyze(control: Path) -> None:
    plan = verify(control)
    require((control/'native-complete.json').is_file(), 'native campaign incomplete')
    require(c.read(control/'native-complete.json')['execution_inventory'] == c.record(control/'executions.json'), 'execution seal drift')
    executions = c.read(control/'executions.json')
    require(len(executions) == 120 and [r['job'] for r in executions] == plan['runs'], 'execution denominator/order')
    c.seal(control/'ANALYSIS-STARTED.json', {'started_at': w.now(), 'execution_inventory': c.record(control/'executions.json')})
    outcomes = []; reports = []
    for job, execution in zip(plan['runs'], executions, strict=True):
        report: dict[str, Any] = {'key': job['key'], 'seed': job['seed'], 'schedule': job['schedule'], 'policy': job['policy'],
                                  'integrity': False, 'all_admission': None, 'replacement_only': None, 'failures': []}
        row = d.Outcome(d.Schedule(job['schedule']), d.Admission(job['policy']), job['seed'], False)
        try:
            require(execution['success'] is True and execution['exit_status'] == 0 and execution['execution_inventory_seconds'] < 600, 'native execution/inventory failure')
            values: list[dict[str, Any] | None] = []
            statuses = []
            for phase in ('analysis', 'analysis-repeat'):
                output = control/(job['key']+'-'+phase+'.json')
                request = control/(job['key']+'-'+phase+'-input.json')
                c.seal(request, {'job': job, 'matrix': plan['matrix'], 'output': str(output), 'files': execution['files'], 'exit_status': execution['exit_status']})
                status = analysis_process(request, control/(job['key']+'-'+phase+'-process'))
                statuses.append(status)
                values.append(c.read(output) if status['exit_status'] == 0 and not status['timed_out'] else None)
            require(all(s['exit_status'] == 0 and not s['timed_out'] for s in statuses), 'independent replay process failure')
            require(values[0] == values[1] and values[0] is not None, 'repeat analysis disagreement')
            analysis = values[0]
            if not isinstance(analysis, dict): raise ValueError('missing/malformed analysis result')
            row = outcome(job, analysis)
            report.update(integrity=True, all_admission=list(row.all_edges.values), replacement_only=list(row.replacement_edges.values),
                          partial_opportunities=row.partial_opportunities, partial_commits=row.partial_commits)
        except (ValueError, OSError, KeyError, TypeError) as error:
            report['failures'].append(f'{type(error).__name__}: {error}')
        outcomes.append(row); reports.append(report)
        c.seal(control/(job['key']+'-verdict.json'), report)
        print(json.dumps({'completed_inputs': len(reports), 'key': job['key'], 'integrity': report['integrity']}), flush=True)
    require(verify(control) == plan, 'final source/preparation drift')
    decision = d.decide(tuple(outcomes))
    c.seal(control/'decision.json', {'completed_at': w.now(), 'decision': decision.value, 'integrity': all(r['integrity'] for r in reports),
                                   'intended_denominator': 120, 'arm_denominator': 20, 'seed_denominator': 20, 'runs': reports,
                                   'preparation': c.record(control/'preparation.json'), 'executions': c.record(control/'executions.json')})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'eligible', 'run', 'analyze'))
    parser.add_argument('control', type=Path)
    parser.add_argument('--raw', type=Path)
    args = parser.parse_args(); control = args.control.resolve()
    if args.action == 'prepare':
        require(args.raw is not None, 'prepare requires explicit external raw directory')
        prepare(control, args.raw)
    elif args.action == 'eligible': eligible(control)
    elif args.action == 'run': run(control)
    else: analyze(control)


if __name__ == '__main__': main()
