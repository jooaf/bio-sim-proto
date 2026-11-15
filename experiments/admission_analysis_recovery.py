"""Once-only analysis recovery of the complete preserved SM-B003 campaign."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from typing import Any
import xml.etree.ElementTree as ET

from experiments import admission_campaign as a
from experiments.stringmol import admission_workflow as w, admission_design as d, conservation_workflow as c
from experiments.stringmol.analyze_lineage import require

FROZEN = '525a745524d0a655695248017799c2e4febf10f8'
CHECKOUT = Path('/tmp/sm/p3')
CHANGES = frozenset(('experiments/stringmol/admission_vm.py', 'tests/stringmol_admission_interpreter.cpp',
                     'tests/test_stringmol_admission_interpreter.py', 'tests/test_stringmol_admission_vm.py'))
PINS = 'experiments/sm_b003_analysis_recovery_qualification.json'
EXTRA = (PINS, 'experiments/admission_analysis_recovery.py', 'tests/test_admission_analysis_recovery.py',
         'reports/sm_b003_analysis_recovery_plan.md')
PHASES = ('analysis', 'analysis-repeat')


def source(*, published: bool) -> dict[str, Any]:
    result = a.source(published=published)
    for path in EXTRA:
        expected = c.record(c.ROOT/path)
        committed = c.command(['git', 'show', result['revision']+':'+path], c.ROOT)
        require(expected == {'size': len(committed), 'sha256': c.digest(committed)}, 'uncommitted recovery source')
        result['files'][path] = expected
    return result


def gate() -> None:
    pins = c.read(c.ROOT/PINS)
    root = Path(pins['development'])
    required = {str(root/'COMPLETE.json'), str(root/'STARTED.json'), *pins['test_suites']}
    require(len(pins['test_suites']) == 2 and 4007 in pins['test_suites'].values() and
            required <= {item['path'] for item in pins['evidence']}, 'missing qualification evidence')
    for item in pins['evidence']:
        require(c.record(Path(item['path'])) == {k: item[k] for k in ('size', 'sha256')}, 'recovery qualification evidence drift')
    for path, count in pins['test_suites'].items():
        suites = ET.parse(path).getroot().findall('testsuite')
        require(count > 0 and sum(int(s.attrib['tests']) for s in suites) == count and
                all(int(s.attrib[k]) == 0 for s in suites for k in ('errors', 'failures', 'skipped')), 'recovery test gate')
    complete, start = c.read(root/'COMPLETE.json'), c.read(root/'STARTED.json')
    require(complete['integrity'] is True and complete['analyses'] == 12 and complete['native_executions'] == 0 and
            complete['implementation'] == start['implementation'] == w.implementation() and
            complete['start_record'] == c.record(root/'STARTED.json'), 'development qualification binding')
    for path, record in start['originals'].items():
        require(c.record(Path(path)) == record, 'development original drift')
    expected = [s.value+'_'+p.value+'_observed' for s, p in w.ARMS]
    require(complete['reports'] == [{'key': k, 'passes': 2, 'original_agreement': True} for k in expected], 'development denominator')
    for key in expected:
        for phase in PHASES:
            request = c.read(root/(key+'-'+phase+'-input.json'))
            require(request['job']['seed'] == w.DEV_SEED and request['job']['key'] == key, 'development input identity')
            require(c.record(root/(key+'-'+phase+'.json')) == c.record(Path(pins['original_development'])/(key+'-'+phase+'.json')),
                    'development output drift')


def validate_original(plan: dict[str, Any], executions: list[dict[str, Any]], decision: dict[str, Any],
                      current: dict[str, Any]) -> None:
    require(plan['source']['revision'] == FROZEN, 'wrong original source')
    old = plan['source']['files']
    require(old.keys() <= current.keys() and {p for p in old if old[p] != current[p]} == CHANGES, 'unexpected original dependency changes')
    expected = [(s.value, p.value, seed) for s, p, seed in d.MATRIX]
    require([(r['schedule'], r['policy'], r['seed']) for r in plan['runs']] == expected, 'original matrix order/denominator')
    require(len(executions) == 120 and [r['job'] for r in executions] == plan['runs'], 'original execution identity')
    require(all(r['success'] is True and r['exit_status'] == 0 and r['execution_inventory_seconds'] < 600 for r in executions), 'original native failure')
    require(decision['decision'] == 'Unevaluable integrity' and decision['integrity'] is False and
            [r['key'] for r in decision['runs']] == [r['key'] for r in plan['runs']] and
            sum(r['integrity'] is True for r in decision['runs']) == 98, 'original verdict identity')


def original(control: Path, current: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    # The frozen checkout verifies its own original source/build/preparation seals.
    command = [sys.executable, '-c', 'import json,sys; from pathlib import Path; from experiments.admission_campaign import verify; print(json.dumps(verify(Path(sys.argv[1]))))', str(control)]
    result = subprocess.run(command, cwd=CHECKOUT, env=c.ENV, check=True, capture_output=True, text=True, timeout=180)
    plan = json.loads(result.stdout)
    executions, decision = c.read(control/'executions.json'), c.read(control/'decision.json')
    require(c.read(control/'native-complete.json')['execution_inventory'] == c.record(control/'executions.json'), 'native completion seal')
    require(decision['preparation'] == c.record(control/'preparation.json') and decision['executions'] == c.record(control/'executions.json'), 'original decision seal')
    validate_original(plan, executions, decision, current)
    return plan, executions, decision


def replay_job(control: Path, old: Path, job: dict[str, Any], execution: dict[str, Any], matrix: str,
               previously_valid: bool) -> tuple[d.Outcome, dict[str, Any]]:
    report: dict[str, Any] = {'key': job['key'], 'seed': job['seed'], 'schedule': job['schedule'], 'policy': job['policy'],
                             'integrity': False, 'failures': [], 'previously_valid': previously_valid}
    row = d.Outcome(d.Schedule(job['schedule']), d.Admission(job['policy']), job['seed'], False)
    values = []
    for phase in PHASES:
        try:
            output, request = control/(job['key']+'-'+phase+'.json'), control/(job['key']+'-'+phase+'-input.json')
            c.seal(request, {'job': job, 'matrix': matrix, 'output': str(output), 'files': execution['files'], 'exit_status': execution['exit_status']})
            status = a.analysis_process(request, control/(job['key']+'-'+phase+'-process'), timeout=1800)
            require(status['exit_status'] == 0 and not status['timed_out'], 'independent replay process failure')
            if previously_valid:
                require(c.record(output) == c.record(old/(job['key']+'-'+phase+'.json')), 'previously valid scientific output changed')
            values.append(c.read(output))
        except (ValueError, OSError, KeyError, TypeError) as error:
            report['failures'].append(f'{phase}: {type(error).__name__}: {error}')
    try:
        require(len(values) == 2 and values[0] == values[1], 'two-pass replay agreement required')
        row = a.outcome(job, values[0])
        report.update(integrity=True, all_admission=list(row.all_edges.values), replacement_only=list(row.replacement_edges.values),
                      partial_opportunities=row.partial_opportunities, partial_commits=row.partial_commits)
    except (ValueError, OSError, KeyError, TypeError) as error:
        report['failures'].append(f'{type(error).__name__}: {error}')
    c.seal(control/(job['key']+'-verdict.json'), report)
    return row, report


def portable_inventory(root: Path) -> dict[str, Any]:
    """Record fixture links/special nodes as metadata; never follow/read them."""
    require(root.is_dir() and not root.is_symlink(), 'missing/nonregular portable root')
    def fail(error: OSError) -> None: raise error
    records: dict[str, Any] = {}
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        for name in sorted(dirs+files):
            path = Path(directory)/name
            mode = path.lstat().st_mode
            key = str(path.relative_to(root))
            if stat.S_ISLNK(mode): records[key] = {'kind': 'symlink', 'target': os.readlink(path)}
            elif stat.S_ISREG(mode): records[key] = {'kind': 'file', **c.record(path)}
            elif not stat.S_ISDIR(mode): records[key] = {'kind': 'special', 'type': stat.S_IFMT(mode)}
    return records


def export_root(root: Path, output: Path) -> dict[str, Any]:
    require(not output.exists() and not output.resolve().is_relative_to(root.resolve()), 'portable export exists/overlaps source')
    before = portable_inventory(root)
    output.mkdir(parents=True, exist_ok=False)
    for name, record in before.items():
        if record['kind'] != 'file': continue
        target = output/'files'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        with (root/name).open('rb') as src, target.open('xb') as dst: shutil.copyfileobj(src, dst)
        require(c.record(target) == {k: record[k] for k in ('size', 'sha256')}, 'portable checksum mismatch')
    require(portable_inventory(root) == before, 'portable source changed during export')
    c.seal(output/'INVENTORY.json', {'source': str(root), 'entries': before})
    return {'source': str(root), 'inventory': c.record(output/'INVENTORY.json'),
            'files': sum(r['kind'] == 'file' for r in before.values())}


def run(old: Path, control: Path) -> None:
    old, control = old.resolve(), control.resolve()
    require(not control.exists() and not control.is_relative_to(old), 'recovery directory already exists/overlaps original')
    w.storage(control, w.RAW/'sm-b003-v1')
    closure = source(published=True)
    gate()
    plan, executions, decision = original(old, closure['files'])
    inventory = c.inventory(old)
    control.mkdir(parents=True, exist_ok=False)
    c.seal(control/'STARTED.json', {'started_at': w.now(), 'source': closure, 'original_control': str(old),
        'original_inventory': inventory, 'analyses': 240, 'native_executions': 0, 'timeout': 1800})
    outcomes, reports = [], []
    for job, execution, previous in zip(plan['runs'], executions, decision['runs'], strict=True):
        require(source(published=False) == closure, 'recovery source drift')
        w.storage(control, Path(plan['raw']), preflight=False)
        row, report = replay_job(control, old, job, execution, plan['matrix'], previous['integrity'] is True)
        outcomes.append(row); reports.append(report)
        print(json.dumps({'completed_inputs': len(reports), 'key': job['key'], 'integrity': report['integrity']}), flush=True)
    for execution in executions:
        require(c.inventory(Path(execution['job']['directory'])) == execution['files'], 'final campaign raw inventory drift')
    require(source(published=False) == closure and c.inventory(old) == inventory, 'final source/original control drift')
    gate()
    require(original(old, closure['files']) == (plan, executions, decision), 'final original provenance drift')
    c.seal(control/'decision.json', {'completed_at': w.now(), 'decision': d.decide(tuple(outcomes)).value,
        'integrity': all(r['integrity'] for r in reports), 'intended_denominator': 120, 'arm_denominator': 20,
        'seed_denominator': 20, 'native_executions': 0, 'runs': reports, 'start_record': c.record(control/'STARTED.json')})
    destination = w.RAW/'verification'/('sm-b003-analysis-recovery-'+control.name)/'portable'
    require(not destination.exists(), 'portable recovery attempt already exists')
    roots = [old, control, *map(Path, c.read(c.ROOT/PINS)['artifact_roots'])]
    require(len({p.name for p in roots}) == len(roots), 'portable root collision')
    exports = [export_root(root, destination/root.name) for root in roots]
    c.seal(destination/'COMPLETE.json', {'completed_at': w.now(), 'exports': exports,
        'decision': c.record(control/'decision.json'), 'source': closure,
        'raw': plan['raw'], 'raw_execution_inventory': c.record(old/'executions.json'),
        'note': 'Raw campaign files already reside on Elements; fixture links/special nodes are metadata, not followed.'})
    print(json.dumps({'finished': True, 'portable': str(destination), 'integrity': all(r['integrity'] for r in reports)}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path); parser.add_argument('control', type=Path)
    args = parser.parse_args()
    run(args.original, args.control)


if __name__ == '__main__': main()
