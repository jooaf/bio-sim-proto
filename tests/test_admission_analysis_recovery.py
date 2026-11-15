"""Recovery denominator, source scope and fail-closed two-pass controls."""
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from experiments import admission_analysis_recovery as r, admission_campaign as a
from experiments.stringmol import admission_design as d, conservation_workflow as c, admission_workflow as w


def original_fixture() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    jobs = [{'key': f'{s.value}_{p.value}_{seed}', 'schedule': s.value, 'policy': p.value, 'seed': seed}
            for s, p, seed in d.MATRIX]
    old = {key: {'sha256': 'old'} for key in (*r.CHANGES, 'protected')}
    current = {key: {'sha256': 'new' if key in r.CHANGES else 'old'} for key in old}
    plan = {'source': {'revision': r.FROZEN, 'files': old}, 'runs': jobs}
    executions = [{'job': j, 'success': True, 'exit_status': 0, 'execution_inventory_seconds': 1} for j in jobs]
    decision = {'decision': 'Unevaluable integrity', 'integrity': False,
                'runs': [{'key': j['key'], 'integrity': i < 98} for i, j in enumerate(jobs)]}
    return plan, executions, decision, current


def test_original_complete_matrix() -> None:
    r.validate_original(*original_fixture())


@pytest.mark.parametrize('fault', ['source', 'protected', 'missing', 'matrix', 'execution', 'success', 'status', 'budget', 'decision', 'denominator'])
def test_original_drift_fails(fault: str) -> None:
    plan, executions, decision, current = deepcopy(original_fixture())
    if fault == 'source': plan['source']['revision'] = 'wrong'
    elif fault == 'protected': current['protected'] = {'sha256': 'changed'}
    elif fault == 'missing': del current['protected']
    elif fault == 'matrix': plan['runs'].reverse()
    elif fault == 'execution': executions.pop()
    elif fault == 'success': executions[0]['success'] = False
    elif fault == 'status': executions[0]['exit_status'] = 1
    elif fault == 'budget': executions[0]['execution_inventory_seconds'] = 600
    elif fault == 'decision': decision['integrity'] = True
    elif fault == 'denominator': decision['runs'][0]['integrity'] = False
    with pytest.raises(ValueError): r.validate_original(plan, executions, decision, current)


@pytest.mark.parametrize('mode', ['ok', 'exit', 'timeout', 'missing', 'repeat', 'drift', 'exception'])
def test_two_passes_no_retries_and_old_output_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    old, control = tmp_path/'old', tmp_path/'new'
    old.mkdir(); control.mkdir()
    job = original_fixture()[0]['runs'][0]
    execution = {'files': {}, 'exit_status': 0}
    result: dict[str, Any] = {'all_admission': dict.fromkeys(a.METRICS, 0), 'replacement_only': dict.fromkeys(a.METRICS, 0),
              'partial_opportunities': 0, 'partial_commits': 0}
    for phase in r.PHASES: c.seal(old/(job['key']+'-'+phase+'.json'), result)
    old_inventory = c.inventory(old)
    calls = []
    def process(request: Path, prefix: Path, *, timeout: float) -> dict[str, Any]:
        calls.append(str(request)); assert timeout == 1800
        assert request != prefix.with_suffix('.json')
        data = c.read(request)
        value = deepcopy(result)
        if mode == 'exception': raise OSError('launch failure')
        if mode in ('drift', 'repeat') and (mode == 'drift' or len(calls) == 2):
            value['all_admission']['qualifying_transfers'] = 1
            value['all_admission']['max_nonrelocation_depth'] = 1
        if mode != 'missing': c.seal(Path(data['output']), value)
        return {'exit_status': 1 if mode == 'exit' else 0, 'timed_out': mode == 'timeout'}
    monkeypatch.setattr(a, 'analysis_process', process)
    row, report = r.replay_job(control, old, job, execution, 'matrix', mode != 'repeat')
    assert len(calls) == 2 and len(set(calls)) == 2
    assert row.integrity is (mode == 'ok') and report['integrity'] is (mode == 'ok')
    assert bool(report['failures']) is (mode != 'ok')
    assert c.inventory(old) == old_inventory


@pytest.mark.parametrize('failure', [False, True])
def test_whole_matrix_two_passes_export_and_failure_denominator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: bool) -> None:
    plan, executions, decision, current = original_fixture()
    old, control, raw = tmp_path/'old', tmp_path/'recovery', tmp_path/'raw'
    old.mkdir(); raw.mkdir()
    plan.update(raw=str(raw), matrix='matrix')
    value = {'all_admission': dict.fromkeys(a.METRICS, 0), 'replacement_only': dict.fromkeys(a.METRICS, 0),
             'partial_opportunities': 0, 'partial_commits': 0}
    for i, (job, execution) in enumerate(zip(plan['runs'], executions, strict=True)):
        directory = raw/job['key']; directory.mkdir()
        job['directory'] = str(directory); execution['files'] = {}
        if i < 98:
            for phase in r.PHASES: c.seal(old/(job['key']+'-'+phase+'.json'), value)
    c.seal(old/'executions.json', executions)
    before = c.inventory(old)
    monkeypatch.setattr(c, 'ROOT', tmp_path)
    monkeypatch.setattr(w, 'RAW', raw)
    pins = tmp_path/r.PINS; pins.parent.mkdir()
    c.seal(pins, {'artifact_roots': []})
    monkeypatch.setattr(r, 'source', lambda **kw: {'revision': 'test', 'files': current})
    monkeypatch.setattr(r, 'gate', lambda: None)
    monkeypatch.setattr(w, 'storage', lambda *args, **kw: None)
    monkeypatch.setattr(r, 'original', lambda *args: (plan, executions, decision))
    def forbidden(*args: Any, **kwargs: Any) -> None: pytest.fail('no native execution permitted')
    monkeypatch.setattr(w, 'execute_one', forbidden)
    calls = []
    def process(request: Path, prefix: Path, *, timeout: float) -> dict[str, Any]:
        assert timeout == 1800
        calls.append(str(request)); data = c.read(request)
        failed = failure and len(calls) == 239
        if not failed: c.seal(Path(data['output']), value)
        return {'exit_status': int(failed), 'timed_out': False}
    monkeypatch.setattr(a, 'analysis_process', process)
    r.run(old, control)
    result = c.read(control/'decision.json')
    assert len(calls) == len(set(calls)) == 240
    assert result['intended_denominator'] == len(result['runs']) == 120
    assert result['integrity'] is (not failure)
    assert (result['decision'] == 'Unevaluable integrity') is failure
    assert sum(row['integrity'] for row in result['runs']) == (119 if failure else 120)
    assert c.inventory(old) == before
    assert (raw/'verification/sm-b003-analysis-recovery-recovery/portable/COMPLETE.json').is_file()


def test_portable_export_links_are_metadata(tmp_path: Path) -> None:
    source, output = tmp_path/'source', tmp_path/'portable'
    source.mkdir(); (source/'data').write_bytes(b'preserved')
    (source/'link').symlink_to(tmp_path)
    before = r.portable_inventory(source)
    receipt = r.export_root(source, output)
    assert receipt['files'] == 1 and (output/'files/data').read_bytes() == b'preserved'
    assert not (output/'files/link').exists()
    assert c.read(output/'INVENTORY.json')['entries'] == before
    assert r.portable_inventory(source) == before
    with pytest.raises(ValueError): r.export_root(source, output)
    with pytest.raises(ValueError): r.export_root(source, source/'nested')


def test_missing_portable_source_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError): r.export_root(tmp_path/'missing', tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_missing_qualification_evidence_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(c, 'ROOT', tmp_path)
    target = tmp_path/r.PINS; target.parent.mkdir()
    c.seal(target, {'development': str(tmp_path), 'test_suites': {}, 'evidence': []})
    with pytest.raises(ValueError, match='missing qualification'): r.gate()


def test_existing_directory_cannot_resume(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None: pytest.fail('must reject before any source check or launch')
    monkeypatch.setattr(r, 'source', forbidden)
    with pytest.raises(ValueError, match='directory'): r.run(tmp_path/'original', tmp_path)
