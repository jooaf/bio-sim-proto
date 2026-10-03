"""Frozen H003 aggregation, canonical union, exact matrix and fail-closed gates."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any
import pytest

from experiments.stringmol import analyze_replicated as a, replicated_workflow as w
from experiments.stringmol import analyze_perturbation as h2, perturbation_panel as p
from experiments.stringmol import conservation_workflow as v1w
from experiments.stringmol.configure_control import HOST, StringmolControlConfig, render_config

FIXTURE = Path(__file__).parent/'fixtures/sm_h002_source_candidates.json'


def frozen_panel() -> list[dict[str, Any]]:
    return p.panel(json.loads(FIXTURE.read_text()))


def metrics(**updates: int) -> dict[str, Any]:
    return {**dict.fromkeys(a.COUNTS, 0), **h2.LIVENESS, **updates}


def outcomes_fixture(passing: int = 14) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    panel = frozen_panel()
    eligible = [q['rank'] for q in panel if q['sha256'] != a.CANONICAL_SHA256][:passing]
    runs = []
    for arm, seed in a.MATRIX:
        rank = (seed-202625000)//3
        m = metrics() if arm == 'EXACT_SUPPORT' or rank not in eligible else metrics(**dict.fromkeys(h2.LIVENESS, 0))
        runs.append({'condition': arm, 'seed': seed, **a.CONTROL, 'cohorts': {'candidate': m, 'support': metrics()}})
    return runs, panel


def test_exact_matrix_and_unchanged_panel() -> None:
    assert a.MATRIX == [(arm, 202625000+3*i+j) for i in range(15) for j in range(3) for arm in ('EXACT_SUPPORT', 'SHUFFLE_SUPPORT')]
    assert len(a.MATRIX) == len(set(a.MATRIX)) == 90
    w.verify_panel(frozen_panel())
    assert w.protocol_pin()['sha256'] == w.PROTOCOL_SHA256


@pytest.mark.parametrize('rank', range(15))
def test_three_paired_configs(tmp_path: Path, rank: int) -> None:
    candidate = frozen_panel()[rank]
    for j in range(3):
        seed = 202625000+3*rank+j
        exact, shuffled = [w.run_input(tmp_path, tmp_path, seed, arm, candidate) for arm in a.ARMS]
        assert all(exact['initial_material'][k] == shuffled['initial_material'][k] for k in ('molecular', 'pool', 'total', 'waste'))
        assert exact['initial_material']['pool'] == exact['initial_material']['waste'] == [0]*33
        for r in (exact, shuffled):
            assert r['rank'] == rank and r['replicate'] == j
            assert r['environment']['NUMBA_NUM_THREADS'] == '1'
            assert r['command'] == [str(tmp_path/'release/stringmol'), '30', r['config']]
            assert r['initial_cohorts'] == {str(i): 'candidate' if i < 70 else 'support' for i in range(140)}
            raw = w.custom_config(r, candidate, tmp_path)
            p.parse_config(raw, r['expected_initial'], seed, tmp_path/'config/ALXII.mtx')
            expected = r['expected_initial']
            assert [m['id'] for m in expected] == list(range(140))
            assert all(m['sequence_hex'] == HOST.encode().hex().upper() for m in expected[70:])
            if candidate['sha256'] == a.CANONICAL_SHA256 and r is exact:
                assert raw == render_config(StringmolControlConfig('host-only', seed, 0, 0), tmp_path/'config/ALXII.mtx')


@pytest.mark.parametrize('change', ['panel-order', 'sequence', 'shuffle', 'nonce', 'provenance', 'canonical'])
def test_panel_tampering(change: str) -> None:
    panel = frozen_panel()
    if change == 'panel-order': panel.reverse()
    elif change == 'sequence': panel[0]['sequence_hex'] = '4142'
    elif change == 'shuffle': panel[0]['shuffle']['sequence_hex'] = panel[0]['sequence_hex']
    elif change == 'nonce': panel[0]['shuffle']['nonce'] += 1
    elif change == 'provenance': panel[0]['provenances'].pop()
    else: panel[0]['sha256'] = a.CANONICAL_SHA256
    with pytest.raises(ValueError): w.verify_panel(panel)


@pytest.mark.parametrize('key', list(h2.LIVENESS))
def test_candidate_threshold_edges(key: str) -> None:
    zero = metrics(**dict.fromkeys(h2.LIVENESS, 0))
    assert h2.specificity(metrics(), zero)['passes']
    assert not h2.specificity(metrics(**{key: h2.LIVENESS[key]-1}), zero)['passes']


@pytest.mark.parametrize('key', list(a.CONTROL))
def test_canonical_threshold_edges(key: str) -> None:
    assert a.control(dict(a.CONTROL))['passes']
    assert not a.control({**a.CONTROL, key: a.CONTROL[key]-1})['passes']


def test_specificity_margin_ratio_edges_and_zero() -> None:
    zero = metrics(**dict.fromkeys(h2.LIVENESS, 0))
    assert h2.specificity(metrics(), zero)['passes']
    assert not h2.specificity(zero, zero)['components']['productive_ratio']
    assert h2.specificity(metrics(productive_source_births=200), metrics(productive_source_births=100, late_productive_source_births=0, serial_source_births=0))['passes']
    for key, value in [('productive_source_births', 101), ('late_productive_source_births', 1), ('serial_source_births', 1)]:
        shuffled = metrics(productive_source_births=100, late_productive_source_births=0, serial_source_births=0)
        shuffled[key] = value
        assert not h2.specificity(metrics(productive_source_births=200), shuffled)['passes']


def test_same_two_conjunction_not_component_majorities() -> None:
    zero = metrics(**dict.fromkeys(h2.LIVENESS, 0))
    pairs: list[dict[str, Any] | None] = [h2.specificity(metrics(**{key: h2.LIVENESS[key]-1}), zero)
             for key in ('productive_source_births', 'late_productive_source_births', 'serial_source_births')]
    assert all(sum(pair['components'][key] for pair in pairs if pair is not None) >= 2 for key in ('productive_margin', 'late_margin', 'serial_margin'))
    assert not a.aggregate(pairs)['same_two_of_three']
    pairs[:2] = [h2.specificity(metrics(), zero) for _ in range(2)]
    assert a.aggregate(pairs)['replicated_specificity']
    assert a.aggregate(pairs)['specific_replicates'] == [0, 1]
    assert a.aggregate(pairs)['pooled_totals']['exact']['productive_source_births'] == 300
    # The third pair may miss specificity but must still have positive direction.
    pairs[2] = h2.specificity(metrics(), metrics())
    assert not a.aggregate(pairs)['all_three_direction']
    pairs[2] = h2.specificity(metrics(), metrics(productive_source_births=101))
    assert not a.aggregate(pairs)['replicated_specificity']
    pairs[2] = None
    assert not a.aggregate(pairs)['replicated_specificity']


@pytest.mark.parametrize('passing,decision', [(14, 'pass'), (12, 'pass'), (11, 'valid non-pass'), (0, 'valid non-pass')])
def test_all_decisions_and_denominators(passing: int, decision: str) -> None:
    runs, panel = outcomes_fixture(passing)
    result = a.outcomes(runs, [], panel)
    assert result['decision'] == decision and result['replicated_panel'] == passing
    assert result['genotype_denominator'] == 14 and result['run_denominator'] == 90
    assert result['paired_block_denominator'] == 45
    assert result['descriptive_coin_tail'] == 0.0064697265625
    for bad in (runs[:-1], runs + [runs[0]], [{**runs[0], 'seed': 0}, *runs[1:]]):
        assert a.outcomes(bad, [], panel)['decision'] == 'unevaluable'
    assert a.outcomes(runs, [{'error': 'integrity'}], panel)['decision'] == 'unevaluable'
    assert a.outcomes(runs, [], panel, mechanics=False)['decision'] == 'unevaluable'


def test_canonical_union_two_of_three_and_exclusion() -> None:
    runs, panel = outcomes_fixture(11)
    canonical = next(q for q in panel if q['sha256'] == a.CANONICAL_SHA256)
    exact = [r for r in runs if (r['seed']-202625000)//3 == canonical['rank'] and r['condition'] == 'EXACT_SUPPORT']
    # Arbitrary subcohorts fail; the whole native population passes.
    for r in exact:
        r['cohorts']['candidate'] = metrics(**dict.fromkeys(h2.LIVENESS, 0))
        r['cohorts']['support'] = metrics(**dict.fromkeys(h2.LIVENESS, 0))
    assert a.outcomes(runs, [], panel)['canonical_positive_control']
    exact[0]['renewing_descendants'] = 9
    assert a.outcomes(runs, [], panel)['decision'] == 'valid non-pass'
    exact[1]['renewing_descendants'] = 9
    assert a.outcomes(runs, [], panel)['decision'] == 'unevaluable'
    # Canonical specificity cannot be the twelfth scientific genotype.
    for r in runs:
        if (r['seed']-202625000)//3 == canonical['rank']:
            r.update(a.CONTROL)
            r['cohorts']['candidate'] = metrics() if r['condition'] == 'EXACT_SUPPORT' else metrics(**dict.fromkeys(h2.LIVENESS, 0))
    result = a.outcomes(runs, [], panel)
    assert result['replicated_panel'] == 11 and result['decision'] == 'valid non-pass'
    assert canonical['rank'] not in result['passing_genotypes']


def test_missing_campaign_unevaluable(tmp_path: Path) -> None:
    out = a.analyze_campaign(tmp_path/'missing.json')
    assert out['decision'] == 'unevaluable' and out['run_denominator'] == 90


@pytest.mark.parametrize('arm,seed,rank', [('EXACT_SELF',202625000,0), ('EXACT_SUPPORT',202625045,14), ('EXACT_SUPPORT',202625003,0)])
def test_invalid_run_input(tmp_path: Path, arm: str, seed: int, rank: int) -> None:
    with pytest.raises(ValueError): w.run_input(tmp_path, tmp_path, seed, arm, frozen_panel()[rank])


def launch_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path,dict[str,Any],list[list[str]]]:
    import json
    root = tmp_path/'runs'/'authorized'; root.mkdir(parents=True)
    path = root/'preparation.json'
    (tmp_path/'code.py').write_text('committed code\n')
    (tmp_path/'protocol.md').write_text('committed protocol\n')
    monkeypatch.setattr(w,'ROOT',tmp_path)
    monkeypatch.setattr(w,'IMPLEMENTATION',[tmp_path/'code.py'])
    monkeypatch.setattr(w,'PATCHES',[])
    monkeypatch.setattr(w,'PROTOCOL_PATH','protocol.md')
    data: dict[str,Any] = {'launch_target':{'remote':'origin','url':'ssh://example.invalid/repo.git','ref':'refs/heads/main'},'runs':[]}
    for arm, seed in a.MATRIX:
        config = root/f'{arm}-{seed}.conf'; config.write_text('authorized input\n'); config.chmod(0o444)
        data['runs'].append({'config':str(config)})
    path.write_text(json.dumps(data)); path.chmod(0o444)
    v1w.seal(root/'preparation.sha256.json',v1w.record(path))
    calls: list[list[str]] = []
    def command(args: list[str], cwd: Path) -> bytes:
        calls.append(args)
        if args == ['git','status','--porcelain']: return b''
        if args == ['git','rev-parse','HEAD']: return b'a'*40+b'\n'
        if args[:2] == ['git','show']:
            commit,name = args[2].split(':',1)
            assert commit == 'a'*40
            return (tmp_path/name).read_bytes()
        if args == ['git','remote','get-url','--all','origin']: return b'ssh://example.invalid/repo.git\n'
        if args == ['git','ls-remote','--exit-code','--refs','ssh://example.invalid/repo.git','refs/heads/main']:
            return b'a'*40+b'\trefs/heads/main\n'
        raise AssertionError(f'unexpected command (including local upstream shortcuts): {args}')
    monkeypatch.setattr(w,'command',command)
    return path,data,calls


def test_launch_evidence_direct_remote_and_fresh_audit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,calls = launch_fixture(tmp_path,monkeypatch)
    prior = tmp_path/'runs'/'development.conf'; prior.write_text('RANDSEED 202620999\n')
    evidence = w.launch_evidence(path,data)
    assert evidence['remote']['observed_revision'] == 'a'*40
    assert evidence['freshness_audit_sha256'] == w.evidence_hash(evidence['freshness_audit'])
    assert len(evidence['freshness_audit']['excluded_files']) == 92
    assert evidence['freshness_audit']['inventory']['runs/development.conf'] == v1w.record(prior)
    assert evidence['committed_files'][str(tmp_path/'code.py')]['bytes_hex'] == b'committed code\n'.hex()
    w.verify_launch_evidence(path,evidence,data)
    assert any(cmd[1] == 'ls-remote' for cmd in calls)
    assert not (path.parent/'launch.json').exists()


@pytest.mark.parametrize('location',['outside','inside-authorized'])
def test_launch_reaudits_seed_use_added_after_preparation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, location: str) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    assert w.unseen_audit(path.parent,authorized_files=w.authorized_inputs(path,data))['matches'] == []
    new = (path.parent if location == 'inside-authorized' else tmp_path/'runs')/'late-output.csv'
    new.write_text('seed,result\n202625007,1\n')
    with pytest.raises(ValueError,match='prior input/use'): w.launch_evidence(path,data)
    assert not (path.parent/'launch.json').exists()


@pytest.mark.parametrize('observation',[
    b'', b'b'*40+b'\trefs/heads/main\n', b'a'*40+b'\trefs/heads/other\n',
    (b'a'*40+b'\trefs/heads/main\n')*2,
])
def test_stale_local_upstream_cannot_authorize_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, observation: bytes) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    original = w.command
    def command(args: list[str], cwd: Path) -> bytes:
        if args[:2] == ['git','ls-remote']: return observation
        return original(args,cwd)
    monkeypatch.setattr(w,'command',command)
    with pytest.raises(ValueError): w.launch_evidence(path,data)
    assert not (path.parent/'launch.json').exists()


def test_remote_query_failure_is_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    original = w.command
    def command(args: list[str], cwd: Path) -> bytes:
        if args[:2] == ['git','ls-remote']: raise subprocess.CalledProcessError(128,args)
        return original(args,cwd)
    monkeypatch.setattr(w,'command',command)
    with pytest.raises(subprocess.CalledProcessError): w.launch_evidence(path,data)
    assert not (path.parent/'launch.json').exists()


def test_changed_remote_url_is_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    data['launch_target']['url'] = 'ssh://wrong.invalid/repo.git'
    with pytest.raises(ValueError,match='target changed'): w.launch_evidence(path,data)


@pytest.mark.parametrize('kind',['audit-hash','audit-exclusions','audit-input','remote-url','remote-ref','remote-revision','remote-bytes','committed-bytes'])
def test_launch_evidence_tampering_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    prior = tmp_path/'runs'/'development.conf'; prior.write_text('RANDSEED 202620999\n')
    evidence = w.launch_evidence(path,data)
    if kind == 'audit-hash': evidence['freshness_audit_sha256'] = '0'*64
    elif kind == 'audit-exclusions':
        evidence['freshness_audit']['excluded_files'] = {}
        evidence['freshness_audit_sha256'] = w.evidence_hash(evidence['freshness_audit'])
    elif kind == 'audit-input': prior.write_text('RANDSEED 202625000\n')
    elif kind == 'remote-url': evidence['remote']['url'] = 'ssh://wrong.invalid/repo.git'
    elif kind == 'remote-ref': evidence['remote']['ref'] = 'refs/heads/other'
    elif kind == 'remote-revision': evidence['remote']['observed_revision'] = 'b'*40
    elif kind == 'remote-bytes': evidence['remote']['stdout_hex'] = ''
    else: evidence['committed_files'][str(tmp_path/'code.py')]['bytes_hex'] = '00'
    with pytest.raises(ValueError): w.verify_launch_evidence(path,evidence,data)


def test_matrix_launch_uses_fresh_audit_before_any_seal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(w,'verify_preparation',lambda p:data)
    (tmp_path/'runs'/'late.conf').write_text('RANDSEED 202625044\n')
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('launch wrote a seal or executed after seed reuse')
    monkeypatch.setattr(w,'seal',forbidden)
    monkeypatch.setattr(v1w,'execute',forbidden)
    with pytest.raises(ValueError,match='prior input/use'): w.run_matrix(path)


def test_audit_exclusion_cannot_hide_another_preparation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    other = tmp_path/'runs'/'other'; other.mkdir()
    config = other/'R-202625000.conf'; config.write_text('held out input\n')
    with pytest.raises(ValueError,match='prior input/use'): w.launch_evidence(path,data)
    with pytest.raises(ValueError,match='exclusion outside'):
        w.unseen_audit(path.parent,authorized_files={*w.authorized_inputs(path,data),config})


def prepared_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source = tmp_path/'source'
    build = tmp_path/'build.json'; build.write_text('{}')
    gate = tmp_path/'gates.json'; gate.write_text(json.dumps({'source_package': {'panel': frozen_panel()}}))
    root = tmp_path/'runs'/'prepared'
    monkeypatch.setattr(w, 'ROOT', tmp_path)
    monkeypatch.setattr(w, 'verify_build', lambda p: {'builds': {'observer': {'source': str(source)}}})
    monkeypatch.setattr(w, 'verify_gate', lambda *args: None)
    monkeypatch.setattr(w, 'protocol_pin', lambda: {})
    monkeypatch.setattr(w, 'IMPLEMENTATION', [])
    monkeypatch.setattr(w, 'source_state', lambda p: {})
    monkeypatch.setattr(w, 'remote_target', lambda: {'remote': 'origin', 'url': 'test', 'ref': 'refs/heads/main'})
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('prepare must never launch')
    monkeypatch.setattr(v1w, 'execute', forbidden)
    monkeypatch.setattr(w, 'observe_remote', forbidden)
    path = w.prepare(build, gate, root)
    data = w.verify_preparation(path)
    assert [(r['condition'], r['seed']) for r in data['runs']] == a.MATRIX
    assert data['workers'] == 6
    assert len(list(root.iterdir())) == 92
    assert set(root.iterdir()) == w.authorized_inputs(path, data)
    assert all(not p.stat().st_mode & 0o222 for p in root.iterdir())
    return path


def test_preparation_never_executes_and_seals_exact_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = prepared_fixture(tmp_path, monkeypatch)
    root = path.parent
    original = path.read_bytes()
    changed = json.loads(original)
    changed['runs'][0]['initial_cohorts']['0'] = 'support'
    path.chmod(0o644); path.write_text(json.dumps(changed, indent=2, sort_keys=True)+'\n'); path.chmod(0o444)
    digest = root/'preparation.sha256.json'
    digest.chmod(0o644); digest.write_text(json.dumps(w.record(path), indent=2, sort_keys=True)+'\n'); digest.chmod(0o444)
    with pytest.raises(ValueError, match='input mismatch'): w.verify_preparation(path)
    path.chmod(0o644); path.write_bytes(original); path.chmod(0o444)
    digest.chmod(0o644); digest.write_text(json.dumps(w.record(path), indent=2, sort_keys=True)+'\n'); digest.chmod(0o444)
    assert not (root/'runs').exists() and not (root/'launch.json').exists()
    with pytest.raises((FileExistsError, ValueError)): w.prepare(tmp_path/'build.json', tmp_path/'gates.json', root)


@pytest.mark.parametrize('marker', ['runs', 'launch.json', 'campaign.json', 'campaign-results.json'])
def test_no_resume_marker_before_remote(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, marker: str) -> None:
    path, data, calls = launch_fixture(tmp_path, monkeypatch)
    (path.parent/marker).touch()
    with pytest.raises(ValueError, match='no resume'): w.launch_evidence(path, data)
    assert not any(cmd[:2] == ['git', 'ls-remote'] for cmd in calls)


def test_dirty_launch_refused_before_remote(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path, data, calls = launch_fixture(tmp_path, monkeypatch)
    command = w.command
    monkeypatch.setattr(w, 'command', lambda args, cwd: b' M code.py\n' if args == ['git', 'status', '--porcelain'] else command(args, cwd))
    with pytest.raises(ValueError, match='commit implementation'): w.launch_evidence(path, data)
    assert not any(cmd[:2] == ['git', 'ls-remote'] for cmd in calls)


def test_six_worker_matrix_receipts_without_simulator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from concurrent.futures import ThreadPoolExecutor
    path, data, _ = launch_fixture(tmp_path, monkeypatch)
    data['runs'] = [w.run_input(tmp_path, path.parent, seed, arm, frozen_panel()[(seed-202625000)//3]) for arm, seed in a.MATRIX]
    monkeypatch.setattr(w, 'verify_preparation', lambda p: data)
    monkeypatch.setattr(w, 'launch_evidence', lambda p, d: {'validated': True})
    monkeypatch.setattr(w, 'verify_launch', lambda p: None)
    workers = []
    def pool(max_workers: int) -> ThreadPoolExecutor:
        workers.append(max_workers)
        return ThreadPoolExecutor(max_workers=max_workers)
    def execute(binary: Path, config: Path, directory: Path, env: dict[str, str]) -> dict[str, Any]:
        directory.mkdir(parents=True, exist_ok=False)
        return {'exit_status': 0, 'files': {}}
    monkeypatch.setattr(w, 'ThreadPoolExecutor', pool)
    monkeypatch.setattr(v1w, 'execute', execute)
    w.run_matrix(path)
    assert workers == [6]
    receipts = w.read(path.parent/'campaign-results.json')
    assert [(r['condition'], r['seed']) for r in receipts] == a.MATRIX
    assert len(receipts) == 90




@pytest.mark.parametrize('change', ['command', 'environment', 'material', 'cohort', 'identity', 'position', 'sequence', 'shuffle', 'rank', 'replicate', 'seed', 'matrix', 'workers', 'panel', 'audit'])
def test_resealed_preparation_tampering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    path = prepared_fixture(tmp_path, monkeypatch)
    data = w.read(path)
    r = data['runs'][0]
    if change == 'command': r['command'][1] = '31'
    elif change == 'environment': r['environment']['NUMBA_NUM_THREADS'] = '2'
    elif change == 'material': r['initial_material']['total'][0] += 1
    elif change == 'cohort': r['initial_cohorts']['70'] = 'candidate'
    elif change == 'identity': r['expected_initial'][0]['id'] = 140
    elif change == 'position': r['expected_initial'][0]['x'] += 1
    elif change == 'sequence': r['expected_initial'][0]['sequence_hex'] = '4142'
    elif change == 'shuffle': data['panel'][0]['shuffle']['nonce'] += 1
    elif change == 'rank': r['rank'] += 1
    elif change == 'replicate': r['replicate'] = 2
    elif change == 'seed': r['seed'] += 1
    elif change == 'matrix': data['runs'].pop()
    elif change == 'workers': data['workers'] = 7
    elif change == 'panel': data['panel'].reverse()
    else: data['unseen_audit']['seeds'].pop()
    path.chmod(0o644)
    path.write_text(json.dumps(data, indent=2, sort_keys=True)+'\n')
    path.chmod(0o444)
    digest = path.with_name('preparation.sha256.json')
    digest.chmod(0o644)
    digest.write_text(json.dumps(w.record(path), indent=2, sort_keys=True)+'\n')
    digest.chmod(0o444)
    with pytest.raises(ValueError): w.verify_preparation(path)


@pytest.mark.parametrize('seed', a.SEEDS)
def test_every_seed_is_held_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, seed: int) -> None:
    monkeypatch.setattr(w, 'ROOT', tmp_path)
    (tmp_path/'runs').mkdir()
    (tmp_path/'runs'/'prior.conf').write_text(f'RANDSEED {seed}\n')
    with pytest.raises(ValueError, match='prior input/use'): w.unseen_audit(tmp_path/'runs'/'prepared')


def test_seed_audit_boundaries_names_and_symlinks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(w, 'ROOT', tmp_path)
    folder = tmp_path/'runs'; folder.mkdir()
    prior = folder/'prior.txt'
    prior.write_text('202624999 202625045 1202625000 0.202625000 2026250000')
    assert w.unseen_audit(folder/'prepared')['matches'] == []
    directory = folder/'run-s202625044'; directory.mkdir()
    with pytest.raises(ValueError, match='prior input/use'): w.unseen_audit(folder/'prepared')
    directory.rmdir()
    (folder/'alias').symlink_to(prior)
    with pytest.raises(ValueError, match='symlink'): w.unseen_audit(folder/'prepared')


def test_source_integrity_pins_and_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = tmp_path/'fixture.json'; fixture.write_text('{}')
    monkeypatch.setattr(w, 'SOURCE_FIXTURE', fixture)
    with pytest.raises(ValueError, match='fixture hash'): w.verify_panel(frozen_panel())
    manifest = tmp_path/'preparation.json'; manifest.write_text('{}')
    analysis = tmp_path/'analysis.json'; analysis.write_text('{}')
    monkeypatch.setattr(w, 'H002_PREPARATION', manifest)
    monkeypatch.setattr(w, 'H002_ANALYSIS', analysis)
    with pytest.raises(ValueError, match='source-integrity'): w.source_evidence({'panel': frozen_panel()})


def test_replay_is_inherited_unchanged() -> None:
    assert a.analyze_run is h2.analyze_run
