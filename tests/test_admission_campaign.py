"""Launch guards with fake seeds/processes; never execute held-out simulations."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import subprocess
import sys
from typing import Any

import pytest

from experiments import admission_campaign as campaign
from experiments.stringmol import admission_design as d, admission_workflow as w, conservation_workflow as c


@pytest.fixture
def prepared(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict[str, Any]]:
    seeds = tuple(range(912345001, 912345021))
    monkeypatch.setattr(d, 'MATRIX', tuple((s, a, seed) for s in d.Schedule for a in d.Admission for seed in seeds))
    monkeypatch.setattr(d, 'SEEDS', seeds)
    build = {'builds': {'candidate': {'source': '/tmp/fixture-source', 'runner': '/tmp/fixture-runner'}}}
    monkeypatch.setattr(campaign, 'qualified', lambda: build)
    monkeypatch.setattr(campaign, 'source', lambda **kwargs: {'revision': 'fixture', 'files': {}})
    monkeypatch.setattr(w, 'storage', lambda *args, **kwargs: None)
    control, raw = tmp_path/'controls', tmp_path/'raw'
    campaign.prepare(control, raw)
    return control, campaign.verify(control)


def authorize(control: Path, plan: dict[str, Any], *, age: int = 0) -> None:
    c.seal(control/'freshness-audit.json', {'passed': True, 'matches': [], 'reserved_values': list(d.SEEDS),
        'completed_at': datetime.now(timezone.utc).isoformat(), 'scope': [str(p.resolve()) for p in campaign.audit_roots()],
        'authorized_files': {str(p): record for p, record in campaign.authorized_files(control, plan).items()}})
    c.seal(control/'eligibility.json', {'eligible': True, 'completed_at': (datetime.now(timezone.utc)-timedelta(seconds=age)).isoformat(),
        'source': plan['source'], 'preparation': c.record(control/'preparation.json'), 'audit': c.record(control/'freshness-audit.json')})


def test_prepare_is_complete_and_cannot_launch(prepared: tuple[Path, dict[str, Any]]) -> None:
    control, plan = prepared
    assert len(plan['runs']) == len({r['key'] for r in plan['runs']}) == 120
    assert not Path(plan['raw']).exists() and not (control/'LAUNCHED.json').exists()
    assert plan['launch_authorized'] is False
    for row in plan['runs']:
        assert row['seed'] in d.SEEDS and f"RANDSEED {row['seed']}" in row['config']
        assert row['environment']['STRINGMOL_ADMISSION_LOG'] == '1'
    with pytest.raises(FileNotFoundError): campaign.execution_ready(control, plan)


@pytest.mark.parametrize('mutation', ['config', 'policy', 'limit', 'duplicate'])
def test_changed_preparation_is_rejected_even_if_resealed(prepared: tuple[Path, dict[str, Any]], mutation: str) -> None:
    control, plan = prepared
    if mutation == 'config': plan['runs'][0]['config'] += 'MUTATE 1\n'
    elif mutation == 'policy': plan['runs'][0]['environment']['STRINGMOL_SOURCE_DISPOSITION'] = 'RETIRE'
    elif mutation == 'limit': plan['native_timeout'] = 601
    else: plan['runs'][1] = plan['runs'][0]
    # This is a deliberately corrupted synthetic control, not an actual seal edit.
    for name in ('preparation.json', 'preparation.sha256.json'): (control/name).chmod(0o644)
    (control/'preparation.json').write_text(json.dumps(plan))
    (control/'preparation.sha256.json').write_text(json.dumps(c.record(control/'preparation.json')))
    with pytest.raises(ValueError): campaign.verify(control)


def test_stale_eligibility_cannot_start_native(prepared: tuple[Path, dict[str, Any]]) -> None:
    control, plan = prepared
    authorize(control, plan, age=181)
    with pytest.raises(ValueError, match='expired'): campaign.execution_ready(control, plan)
    assert not Path(plan['raw']).exists()


def test_all_inputs_attempted_once_without_scientific_retry(prepared: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch) -> None:
    control, plan = prepared
    authorize(control, plan)
    seen: list[str] = []
    def execute(job: dict[str, Any], *args: object) -> dict[str, Any]:
        seen.append(job['key'])
        return {'job': job, 'success': False}
    monkeypatch.setattr(w, 'execute_one', execute)
    campaign.run(control)
    assert len(seen) == len(set(seen)) == 120
    assert c.read(control/'native-complete.json')['successful_exits'] == 0
    with pytest.raises(ValueError, match='once-only'): campaign.run(control)
    assert len(seen) == 120


def test_failed_audit_retained_without_eligibility(prepared: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch) -> None:
    control, plan = prepared
    monkeypatch.setattr(campaign, 'audit', lambda *args, **kwargs: {'passed': False, 'matches': ['fixture prior input']})
    with pytest.raises(ValueError, match='freshness audit'): campaign.eligible(control)
    assert (control/'freshness-audit.json').is_file() and not (control/'eligibility.json').exists()
    assert not Path(plan['raw']).exists()


def test_source_change_prevents_launch(prepared: tuple[Path, dict[str, Any]], monkeypatch: pytest.MonkeyPatch) -> None:
    control, plan = prepared
    authorize(control, plan)
    monkeypatch.setattr(campaign, 'source', lambda **kwargs: {'revision': 'changed', 'files': {}})
    with pytest.raises(ValueError, match='source changed'): campaign.run(control)
    assert not (control/'LAUNCHED.json').exists()


def test_analysis_timeout_kills_owned_process_group(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = subprocess.Popen
    processes: list[subprocess.Popen[bytes]] = []
    def spawn(command: list[str], **kwargs: Any) -> subprocess.Popen[bytes]:
        assert kwargs['start_new_session'] is True
        child = original([sys.executable, '-u', '-c', 'import time; print("before timeout", flush=True); time.sleep(30)'], **kwargs)
        processes.append(child)
        return child
    monkeypatch.setattr(subprocess, 'Popen', spawn)
    prefix = tmp_path/'process'
    result = campaign.analysis_process(tmp_path/'unused.json', prefix, timeout=.2)
    assert result['timed_out'] is True and result['exit_status'] != 0
    assert processes[0].poll() is not None
    assert c.read(tmp_path/'process.json') == result
    with pytest.raises(FileExistsError): campaign.analysis_process(tmp_path/'unused.json', prefix)
    assert len(processes) == 1


def test_derived_endpoint_mapping_keeps_negative_results() -> None:
    job = {'schedule': 'IMMEDIATE', 'policy': 'STRATIFIED_REPLACE', 'seed': 912345001}
    result = {'all_admission': dict(zip(campaign.METRICS, (1059,15,228,3,2,2), strict=True)),
              'replacement_only': dict(zip(campaign.METRICS, (453,6,36,2,1,1), strict=True)),
              'partial_opportunities': 531, 'partial_commits': 531}
    outcome = campaign.outcome(job, result)
    assert outcome.valid and not outcome.replacement_edges.passed and not outcome.all_edges.passed
    result['partial_commits'] = 530
    with pytest.raises(ValueError): campaign.outcome(job, result)
