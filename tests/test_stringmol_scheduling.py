"""SM-B001 frozen sequence endpoints, decisions and fail-closed launch fixtures."""
from __future__ import annotations
from copy import deepcopy
import json
import math
from pathlib import Path
from typing import Any
import pytest
from experiments.stringmol import analyze_scheduling as a, scheduling_workflow as w
from experiments.stringmol import conservation_workflow as v1w, analyze_renewal as h1, analyze_decay as decay
from experiments.stringmol.configure_control import HOST

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
    assert len(evidence['freshness_audit']['excluded_files']) == 62
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
    new.write_text('seed,result\n202627007,1\n')
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
    elif kind == 'audit-input': prior.write_text('RANDSEED 202627000\n')
    elif kind == 'remote-url': evidence['remote']['url'] = 'ssh://wrong.invalid/repo.git'
    elif kind == 'remote-ref': evidence['remote']['ref'] = 'refs/heads/other'
    elif kind == 'remote-revision': evidence['remote']['observed_revision'] = 'b'*40
    elif kind == 'remote-bytes': evidence['remote']['stdout_hex'] = ''
    else: evidence['committed_files'][str(tmp_path/'code.py')]['bytes_hex'] = '00'
    with pytest.raises(ValueError): w.verify_launch_evidence(path,evidence,data)


def test_matrix_launch_uses_fresh_audit_before_any_seal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(w,'verify_preparation',lambda p:data)
    (tmp_path/'runs'/'late.conf').write_text('RANDSEED 202627019\n')
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('launch wrote a seal or executed after seed reuse')
    monkeypatch.setattr(w,'seal',forbidden)
    monkeypatch.setattr(v1w,'execute',forbidden)
    with pytest.raises(ValueError,match='prior input/use'): w.run_matrix(path)


def test_audit_exclusion_cannot_hide_another_preparation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    other = tmp_path/'runs'/'other'; other.mkdir()
    config = other/'R-202627000.conf'; config.write_text('held out input\n')
    with pytest.raises(ValueError,match='prior input/use'): w.launch_evidence(path,data)
    with pytest.raises(ValueError,match='exclusion outside'):
        w.unseen_audit(path.parent,authorized_files={*w.authorized_inputs(path,data),config})


def prepared_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    source = tmp_path/'source'
    build = tmp_path/'build.json'; build.write_text('{}')
    gate = tmp_path/'gates.json'; gate.write_text('{}')
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
    assert len(list(root.iterdir())) == 62
    assert set(root.iterdir()) == w.authorized_inputs(path, data)
    assert all(not p.stat().st_mode & 0o222 for p in root.iterdir())
    return path


def test_preparation_never_executes_and_seals_exact_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = prepared_fixture(tmp_path, monkeypatch)
    root = path.parent
    original = path.read_bytes()
    changed = json.loads(original)
    changed['runs'][0]['expected_initial'][0]['id'] = 900
    path.chmod(0o644); path.write_text(json.dumps(changed, indent=2, sort_keys=True)+'\n'); path.chmod(0o444)
    digest = root/'preparation.sha256.json'
    digest.chmod(0o644); digest.write_text(json.dumps(w.record(path), indent=2, sort_keys=True)+'\n'); digest.chmod(0o444)
    with pytest.raises(ValueError, match='mismatch'): w.verify_preparation(path)
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
    data['runs'] = [w.run_input(tmp_path, path.parent, seed, arm) for arm, seed in a.MATRIX]
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
    assert len(receipts) == 60




@pytest.mark.parametrize('change', ['command', 'environment', 'material', 'identity', 'position', 'sequence', 'seed', 'matrix', 'workers', 'audit'])
def test_resealed_preparation_tampering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    path = prepared_fixture(tmp_path, monkeypatch)
    data = w.read(path)
    r = data['runs'][0]
    if change == 'command': r['command'][1] = '31'
    elif change == 'environment': r['environment']['NUMBA_NUM_THREADS'] = '2'
    elif change == 'material': r['initial_material']['total'][0] += 1
    elif change == 'identity': r['expected_initial'][0]['id'] = 140
    elif change == 'position': r['expected_initial'][0]['x'] += 1
    elif change == 'sequence': r['expected_initial'][0]['sequence_hex'] = '4142'
    elif change == 'seed': r['seed'] += 1
    elif change == 'matrix': data['runs'].pop()
    elif change == 'workers': data['workers'] = 7
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
    prior.write_text('202627999 202627020 1202627000 0.202627000 2026270000')
    assert w.unseen_audit(folder/'prepared')['matches'] == []
    directory = folder/'run-s202627019'; directory.mkdir()
    with pytest.raises(ValueError, match='prior input/use'): w.unseen_audit(folder/'prepared')
    directory.rmdir()
    (folder/'alias').symlink_to(prior)
    with pytest.raises(ValueError, match='symlink'): w.unseen_audit(folder/'prepared')



def decisions(immediate: int = 16, delay: int = 16, exposed: int = 16) -> list[dict[str, Any]]:
    rows=[]
    for arm,seed in a.MATRIX:
        i=seed-a.SEEDS[0]
        r: dict[str,Any] = dict.fromkeys(a.SCALARS,0)
        r.update(condition=arm,seed=seed,boundary_errors=0,applied_before_horizon=100 if i < exposed else 99,
                 policy_child_encounters=0,policy_child_bindings=0,policy_child_dispatches=0)
        if i < (immediate if arm == 'IMMEDIATE' else delay if arm == 'DELAY500' else 0):
            r.update(zip(h1.ENDPOINTS,h1.THRESHOLDS,strict=True))
        rows.append(r)
    return rows


@pytest.mark.parametrize('immediate,delay,exposed,branch',[(15,20,20,2),(16,16,16,3),(20,4,16,4),(16,4,16,5),(16,5,16,5),(20,15,16,5),(20,20,15,6),(20,0,15,6)])
def test_all_frozen_branches(immediate: int, delay: int, exposed: int, branch: int) -> None:
    result=a.outcomes(decisions(immediate,delay,exposed),[])
    assert result['branch'] == branch and result['integrity']
    assert result['run_denominator'] == 60 and result['arm_denominator'] == result['paired_denominator'] == 20
    assert result['separate_retention_preregistration_authorized'] == (branch in (3,4,5))


@pytest.mark.parametrize('key', ['policy_child_encounters','policy_child_bindings','policy_child_dispatches','boundary_errors'])
def test_locked_enforcement_is_integrity_not_birth_threshold(key: str) -> None:
    rows=decisions(); assert a.outcomes(rows,[])['branch'] == 3
    rows[2][key]=1
    assert a.outcomes(rows,[])['branch'] == 1


@pytest.mark.parametrize('count',[0,1,59,61])
def test_all_runs_remain_in_denominator(count: int) -> None:
    rows=(decisions()+decisions()[:1])[:count]
    result=a.outcomes(rows,[])
    assert result['branch'] == 1 and result['run_denominator'] == 60 and len(result['pairs']) == 20


@pytest.mark.parametrize('survived,participated,expected',[(99,50,0),(100,49,0),(100,50,20)])
def test_response_exposure_never_gates_total_effect(survived: int, participated: int, expected: int) -> None:
    rows=decisions()
    for r in rows:
        if r['condition']=='DELAY500': r.update(survived_to_eligibility=survived,released_with_participation=participated)
    result=a.outcomes(rows,[])
    assert result['branch'] == 3 and result['post_release_response_exposed_runs'] == expected


def test_strong_sensitivity_requires_same_sixteen_pairs() -> None:
    rows=decisions(16,4)
    assert a.outcomes(rows,[])['branch'] == 5
    for r in rows:
        if r['condition']=='DELAY500':
            r.update({k:t if r['seed'] >= a.SEEDS[16] else 0 for k,t in zip(h1.ENDPOINTS,h1.THRESHOLDS,strict=True)})
    assert a.outcomes(rows,[])['branch'] == 4


@pytest.mark.parametrize('field',h1.ENDPOINTS)
def test_unchanged_continuity_thresholds(field: str) -> None:
    rows=decisions()
    for r in rows:
        if r['condition']=='IMMEDIATE': r[field]=h1.THRESHOLDS[h1.ENDPOINTS.index(field)]-1
    assert a.outcomes(rows,[])['branch'] == 2


def test_all_configs_and_environments_differ_only_policy(tmp_path: Path) -> None:
    for seed in a.SEEDS:
        runs=[w.run_input(tmp_path,tmp_path,seed,arm) for arm in a.ARMS]
        assert len({w.custom_config(r,tmp_path) for r in runs}) == 1
        for r in runs:
            w.parse_config(w.custom_config(r,tmp_path),r,tmp_path)
            assert r['environment']==w.environment(r['condition'])
            assert r['expected_initial']==runs[0]['expected_initial']
            assert r['initial_material']==runs[0]['initial_material']
            assert sum(r['initial_material']['molecular'])==8960


@pytest.mark.parametrize('old,new',[('MUTATE 0','MUTATE 0.0002'),('NSTEPS 5000','NSTEPS 5001'),('DECAY 0.0005','DECAY 0'),('GRID 40 40','GRID 41 40')])
def test_config_scientific_tampering(tmp_path: Path, old: str, new: str) -> None:
    r=w.run_input(tmp_path,tmp_path,a.SEEDS[0],'IMMEDIATE'); raw=w.custom_config(r,tmp_path)
    # Every change, including arbitrary trailing directives, fails exact equality.
    changed=raw.replace(old,new) if old in raw else raw+'\n'+new+'\n'
    with pytest.raises(ValueError): w.parse_config(changed,r,tmp_path)


def synthetic(policy: str = 'DELAY500', *, dies: bool = False, horizon: int = 504) -> tuple[dict[str,Any],list[dict[str,str]],list[dict[str,str]]]:
    from experiments.stringmol import analyze_conservation as v1
    initial=v1.initial_material([{'id':0,'sequence_hex':'254142'},{'id':1,'sequence_hex':'4344'}],'histogram',0,8)
    material=[dict(zip(decay.JOURNAL_COLUMNS,map(str,[1,1,'CLEAVE','PLACED','0;1','0;1;2','1:1:44:00;2:0:00:44','']),strict=True))]
    rows: list[dict[str,str]]=[]
    def emit(event: str, tick: int, **fields: Any) -> None:
        rows.append({**a.DEFAULTS,'event':event,'tick':str(tick),'index':str(len(rows)+1),'policy':policy,**{k:str(v) for k,v in fields.items()}})
    def selection(tick: int, idx: int, other: int = -1, status: str = 'UNBOUND') -> None:
        et=eligible if idx==2 else 0
        emit('SELECT',tick,id=idx,other=other,eligible_tick=et,count=int(tick>=et),outcome=status)
        emit('SURVIVE',tick,id=idx,other=other)
    eligible=a.eligibility(1,policy,horizon)
    emit('START',0,eligible_tick=horizon,ids='0;1')
    emit('TICK',0,ids='0;1'); selection(0,0)
    emit('SEARCH',0,id=0,other=1,count=1,selected=0,outcome='SELECTED')
    emit('ENCOUNTER',0,id=0,other=1,active=0,passive=1,count=1,selected=0,outcome='BOUND')
    emit('TICK',1,ids='0;1'); selection(1,0,1,'ACTIVE')
    emit('DISPATCH',1,active=0,passive=1,opcode=37,owner=0,offset=0)
    emit('BIRTH',1,id=2,active=0,passive=1,source=1,eligible_tick=eligible,material_index=1)
    emit('COMPLETE',1,active=0,passive=1,material_index=1)
    for tick in range(2,horizon):
        alive=not dies or tick<=10
        emit('TICK',tick,ids='2;0;1' if alive else '0;1')
        if alive:
            if tick==eligible: emit('RELEASE',tick,id=2,eligible_tick=eligible)
            if dies and tick==10:
                emit('SELECT',tick,id=2,eligible_tick=eligible,count=int(tick>=eligible),outcome='UNBOUND')
                material.append(dict(zip(decay.JOURNAL_COLUMNS,map(str,[tick,2,'DECAY','REMOVED','2','','2:0:44:00','']),strict=True)))
                emit('DEATH',tick,id=2,eligible_tick=eligible,outcome='DECAY',material_index=2)
                emit('DECAY',tick,id=2)
            else:
                selection(tick,2)
                if tick>=eligible:
                    if tick<=4: emit('SEARCH',tick,id=2,outcome='EMPTY')
                    else:
                        emit('SEARCH',tick,id=2,other=0,count=2,selected=0,outcome='SELECTED')
                        emit('ENCOUNTER',tick,id=2,other=0,count=2,selected=0,outcome='UNBOUND')
                        selection(tick,1); emit('SEARCH',tick,id=1,outcome='EMPTY')
                        continue
        if tick<=4:
            selection(tick,0,1,'ACTIVE')
            emit('DISPATCH',tick,active=0,passive=1,opcode={2:65,3:66,4:0}[tick],owner=0,offset=tick-1,material_index=1)
            emit('COMPLETE',tick,active=0,passive=1,material_index=1)
        else:
            selection(tick,0)
            emit('SEARCH',tick,id=0,other=1,count=1,selected=0,outcome='SELECTED')
            emit('ENCOUNTER',tick,id=0,other=1,count=1,selected=0,outcome='UNBOUND')
    if not dies: emit('CENSOR',horizon,id=2,eligible_tick=eligible)
    emit('END',horizon,ids='0;1' if dies else '2;0;1',material_index=len(material))
    return initial,material,rows


def replay_synthetic(policy: str = 'DELAY500', *, dies: bool = False) -> a.BoundaryReplay:
    initial,material,rows=synthetic(policy,dies=dies)
    replay=a.BoundaryReplay(initial,material,policy,504)
    for row in rows: replay.step(row)
    return replay


@pytest.mark.parametrize('policy',(*a.ARMS,'DISABLED'))
@pytest.mark.parametrize('dies',[False,True])
def test_independent_complete_boundary_replay(policy: str, dies: bool) -> None:
    replay=replay_synthetic(policy,dies=dies)
    summary=replay.summary(504); child=summary['children'][0]
    assert summary['physical_child_placements']==summary['policy_births']==1
    if policy=='LOCKED':
        assert child['encounters']==child['bindings']==child['dispatches']==0
        assert child['final_state']==('decayed before eligibility' if dies else 'alive but not yet eligible at END')
    elif policy=='DELAY500':
        assert child['released']==(None if dies else 502)
        assert child['first_participation']==(None if dies else {'tick':502,'role':'seeker','birth_latency':501,'release_latency':0})


@pytest.mark.parametrize('kind',['early-encounter','early-dispatch','wrong-source','missing-birth','duplicate-birth','duplicate-release','missing-release','duplicate-encounter','missing-select','wrong-candidates','wrong-index','wrong-opcode','wrong-material','id-reuse','missing-censor','missing-end','wrong-eligible','wrong-policy','wrong-order','wrong-survival','extra-material'])
def test_adversarial_boundary_replay(kind: str) -> None:
    initial,material,rows=synthetic()
    def find(event: str) -> int:
        return next(i for i,r in enumerate(rows) if r['event']==event)
    if kind=='early-encounter': rows[find('BIRTH')]['eligible_tick']='503'
    elif kind=='early-dispatch': rows[find('DISPATCH')]['active']='2'
    elif kind=='wrong-source': rows[find('BIRTH')]['source']='0'
    elif kind.startswith('missing-'):
        event={'missing-birth':'BIRTH','missing-release':'RELEASE','missing-select':'SELECT','missing-censor':'CENSOR','missing-end':'END'}[kind]
        rows.pop(find(event))
    elif kind.startswith('duplicate-'):
        event={'duplicate-birth':'BIRTH','duplicate-release':'RELEASE','duplicate-encounter':'ENCOUNTER'}[kind]
        i=find(event); rows.insert(i,deepcopy(rows[i]))
    elif kind=='wrong-candidates': rows[find('SEARCH')]['count']='2'
    elif kind=='wrong-index': rows[find('SEARCH')]['selected']='1'
    elif kind=='wrong-opcode': rows[find('DISPATCH')]['opcode']='61'
    elif kind=='wrong-material': rows[find('COMPLETE')]['material_index']='0'
    elif kind=='id-reuse': rows[find('BIRTH')]['id']='1'
    elif kind=='wrong-eligible': rows[find('BIRTH')]['eligible_tick']='501'
    elif kind=='wrong-policy': rows[find('BIRTH')]['policy']='IMMEDIATE'
    elif kind=='wrong-order': rows[find('TICK')]['ids']='1;0'
    elif kind=='wrong-survival': rows[find('SURVIVE')]['event']='DECAY'
    else: material.append(deepcopy(material[0]))
    for i,r in enumerate(rows): r['index']=str(i+1)
    replay=a.BoundaryReplay(initial,material,'DELAY500',504)
    with pytest.raises(ValueError):
        for row in rows: replay.step(row)
        replay.summary(504)


def test_eligibility_late_boundary_and_checked_sentinel() -> None:
    assert a.eligibility(2500,'DELAY500',5000)==3001
    assert a.eligibility(4999,'IMMEDIATE',5000)==5000
    assert a.eligibility(4999,'LOCKED',5000)==5001
    with pytest.raises(ValueError): a.eligibility(2**64-2,'DELAY500',2**64-1)


def test_relocation_transfer_depth_is_separate_from_h001() -> None:
    base={'productive':False,'orphan_source':False,'offset':0,'tick':0}
    edges=[{**base,'source':0,'child':2,'whole_transfer':True},
           {**base,'source':2,'child':3,'whole_transfer':True,'tick':1},
           {**base,'source':3,'child':4,'whole_transfer':False,'offset':1,'tick':2},
           {**base,'source':99,'child':5,'whole_transfer':False,'offset':1,'tick':3},
           {**base,'source':5,'child':6,'whole_transfer':False,'offset':1,'tick':4}]
    summary={'source_edges':edges,'identity_history':[{'id':i,'death_tick':0 if i==0 else 1 if i==2 else None} for i in range(7)],'boundary_end_ids':[1,3,4,5,6]}
    result=a.transfer_endpoints(summary,{0,1})
    assert result['max_transfer_depth']==3 and result['max_relocation_chain_depth']==2
    assert result['nonrelocation_serial_transfers']==1 and result['max_nonrelocation_depth']==1
    assert result['transfer_edges'][-1]['transfer_orphan']
    assert result['transfer_edges'][2]['source_remnant_survived_placement']
    assert summary['source_edges']==edges
@pytest.mark.parametrize('bound,dispatched,expected',[(False,False,'eligible but never encountered'),(True,False,'bound but never dispatched'),(True,True,'dispatched')])
def test_remaining_terminal_states(bound: bool, dispatched: bool, expected: str) -> None:
    horizon=504 if dispatched else 503 if bound else 3
    policy='DELAY500' if bound else 'IMMEDIATE'
    initial,material,rows=synthetic(policy,horizon=horizon)
    if bound:
        for r in rows:
            if r['event']=='ENCOUNTER' and r['tick']=='502': r.update(outcome='BOUND',active='2',passive='0')
    if dispatched:
        start=next(i for i,r in enumerate(rows) if r['event']=='TICK' and r['tick']=='503')
        end=next(i for i,r in enumerate(rows) if r['event']=='CENSOR')
        def row(event: str, **fields: Any) -> dict[str,str]:
            return {**a.DEFAULTS,'event':event,'tick':'503','policy':policy,**{k:str(v) for k,v in fields.items()}}
        rows[start:end]=[row('TICK',ids='2;0;1'),row('SELECT',id=2,other=0,eligible_tick=502,count=1,outcome='ACTIVE'),
            row('SURVIVE',id=2,other=0),row('DISPATCH',active=2,passive=0,opcode=68,owner=2,offset=0,material_index=1),
            row('COMPLETE',active=2,passive=0,material_index=1),row('SELECT',id=1,count=1,outcome='UNBOUND'),row('SURVIVE',id=1),row('SEARCH',id=1,outcome='EMPTY')]
    for i,r in enumerate(rows): r['index']=str(i+1)
    replay=a.BoundaryReplay(initial,material,policy,horizon)
    for r in rows: replay.step(r)
    assert replay.summary(horizon)['children'][0]['final_state']==expected


@pytest.mark.parametrize('change',['omit-survival','omit-encounter','false-empty-search','duplicate-death','wrong-death-link','pre-release-search'])
def test_more_ordered_lifecycle_adversaries(change: str) -> None:
    initial,material,rows=synthetic(dies=True)
    def find(event: str) -> int: return next(i for i,r in enumerate(rows) if r['event']==event)
    if change=='omit-survival': rows.pop(find('SURVIVE'))
    elif change=='omit-encounter': rows.pop(find('ENCOUNTER'))
    elif change=='false-empty-search': rows[find('SEARCH')].update(other='-1',count='0',selected='-1',outcome='EMPTY')
    elif change=='duplicate-death': rows.insert(find('DEATH'),deepcopy(rows[find('DEATH')]))
    elif change=='wrong-death-link': rows[find('DEATH')]['material_index']='1'
    else:
        i=next(i for i,r in enumerate(rows) if r['event']=='SURVIVE' and r['id']=='2')
        rows.insert(i+1,{**a.DEFAULTS,'event':'SEARCH','tick':rows[i]['tick'],'policy':'DELAY500','id':'2','outcome':'EMPTY'})
    for i,r in enumerate(rows): r['index']=str(i+1)
    replay=a.BoundaryReplay(initial,material,'DELAY500',504)
    with pytest.raises(ValueError):
        for r in rows: replay.step(r)
        replay.summary(504)


@pytest.mark.parametrize('content',['bad\n',','.join(a.COLUMNS)+'\r\n',','.join(a.COLUMNS)+'\n"bad"\n',','.join(a.COLUMNS)+'\nmissing-newline'])
def test_strict_boundary_csv(tmp_path: Path, content: str) -> None:
    path=tmp_path/'boundary.csv'; path.write_bytes(content.encode())
    with pytest.raises(ValueError): list(a.boundary_rows(path))


def test_missing_material_transaction_cannot_be_hidden_by_complete() -> None:
    initial,material,rows=synthetic()
    # Remove child and CLEAVE evidence together, but retain the dispatch opcode.
    rows=[r for r in rows if r['event']!='BIRTH']
    complete=next(r for r in rows if r['event']=='COMPLETE'); complete['material_index']='0'
    for i,r in enumerate(rows): r['index']=str(i+1)
    replay=a.BoundaryReplay(initial,[],'DELAY500',504)
    with pytest.raises(ValueError,match='missing/spurious'):
        for r in rows: replay.step(r)
def test_plausible_same_suffix_wrong_source_rejected() -> None:
    from experiments.stringmol import analyze_conservation as v1
    _,material,rows=synthetic()
    initial=v1.initial_material([{'id':0,'sequence_hex':'254144'},{'id':1,'sequence_hex':'4344'}],'histogram',0,8)
    for r in rows:
        if r['event']=='DISPATCH' and r['tick']=='3': r['opcode']='68'
    valid=a.BoundaryReplay(initial,material,'DELAY500',504)
    for r in rows: valid.step(r)
    next(r for r in rows if r['event']=='BIRTH')['source']='0'
    wrong=a.BoundaryReplay(initial,material,'DELAY500',504)
    with pytest.raises(ValueError,match='source/cleanup'):
        for r in rows: wrong.step(r)


def test_first_participation_as_selected_partner() -> None:
    initial,material,rows=synthetic()
    start=next(i for i,r in enumerate(rows) if r['event']=='SELECT' and r['tick']=='502')
    stop=next(i for i,r in enumerate(rows) if r['event']=='TICK' and r['tick']=='503')
    def row(event: str, **fields: Any) -> dict[str,str]:
        return {**a.DEFAULTS,'event':event,'tick':'502','policy':'DELAY500',**{k:str(v) for k,v in fields.items()}}
    rows[start:stop]=[row('SELECT',id=0,count=1,outcome='UNBOUND'),row('SURVIVE',id=0),
        row('SEARCH',id=0,other=2,count=2,selected=0,outcome='SELECTED'),
        row('ENCOUNTER',id=0,other=2,count=2,selected=0,outcome='UNBOUND'),
        row('SELECT',id=1,count=1,outcome='UNBOUND'),row('SURVIVE',id=1),row('SEARCH',id=1,outcome='EMPTY')]
    next(r for r in rows if r['event']=='TICK' and r['tick']=='503')['ids']='0;2;1'
    for i,r in enumerate(rows): r['index']=str(i+1)
    replay=a.BoundaryReplay(initial,material,'DELAY500',504)
    for r in rows: replay.step(r)
    assert replay.summary(504)['children'][0]['first_participation']['role']=='selected-partner'


def test_no_candidate_is_not_participation() -> None:
    initial,material,rows=synthetic('IMMEDIATE',horizon=3)
    replay=a.BoundaryReplay(initial,material,'IMMEDIATE',3)
    for r in rows: replay.step(r)
    summary=replay.summary(3)
    assert summary['survived_to_eligibility']==1 and summary['released_with_participation']==0
    assert summary['children'][0]['first_participation'] is None


def test_distribution_pair_differences_keep_twenty_units() -> None:
    rows=decisions()
    rows[0].update(productive_length_counts={'64':3},productive_sequence_abundances=[{'length':64,'visible_hex':'41','count':3}],retention_distribution=[1,1])
    rows[1].update(productive_length_counts={'64':1},productive_sequence_abundances=[{'length':64,'visible_hex':'41','count':1}],retention_distribution=[1])
    result=a.outcomes(rows,[])
    assert result['pairs'][0]['distribution_comparisons']['productive_length_counts']['64']['difference']==2
    assert result['paired_distribution_summary']['productive_length_counts']['64']['pair_denominator']==20
    assert result['paired_distribution_summary']['productive_length_counts']['64']['direction_counts']=={'immediate_greater':1,'tie':19}
def counter_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path,bytes]:
    import re
    monkeypatch.setattr(w,'ROOT',tmp_path)
    p=tmp_path/w.COUNTER_PATH; p.parent.mkdir(parents=True)
    raw=w.COUNTER_HEADER+b'\r\n'+w.COUNTER_ROW+b'\r\n'
    p.write_bytes(raw)
    monkeypatch.setattr(w,'COUNTER_SHA256',v1w.digest(raw))
    p.with_name('config.json').write_text(json.dumps({'seed':202615013}))
    p.with_name('manifest.json').write_text(json.dumps({'config':{'seed':202615013},'artifact_checksums':{'symbols.csv':v1w.digest(raw)}}))
    original=w.record
    def record(path: Path) -> dict[str,Any]:
        saved=original(path)
        if path==p.with_name('config.json'): saved['sha256']='ac167746de1671af977b61d972ebc3a98a3d42c532ed0d0724c5f5cb48a18e06'
        if path==p.with_name('manifest.json'): saved['sha256']='2b6b7274fcbcb1a40917cd54d6604f3c9cf3052cc9edb04e30ffaf26b5bbc3be'
        return saved
    monkeypatch.setattr(w,'record',record)
    assert len(list(re.finditer(rb'2026270[01][0-9](?![0-9])',raw)))==1
    return p,raw


def test_audit_classifies_only_pinned_historical_counter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p,raw=counter_fixture(tmp_path,monkeypatch)
    audit=w.unseen_audit(tmp_path/'runs/prepared')
    assert audit['matches']==[] and len(audit['nonseed_counter_matches'])==1
    evidence=audit['nonseed_counter_matches'][0]
    assert evidence['field']=='cross_a_to_b' and evidence['run_seed']==202615013 and evidence['value']==202627000
    assert audit['inventory'][w.COUNTER_PATH]['sha256']==v1w.digest(raw)
    assert evidence['path']==str(p.relative_to(tmp_path)) and not audit['excluded_files']


@pytest.mark.parametrize('change',['path','hash','header','cell','duplicate','seed','manifest-seed','manifest-artifact'])
def test_counter_classification_cannot_hide_seed_use(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    p,raw=counter_fixture(tmp_path,monkeypatch)
    if change=='path': p.rename(p.with_name('other.csv'))
    elif change=='hash': p.write_bytes(raw+b'\r\n')
    elif change in ('header','cell','duplicate'):
        if change=='header': raw=raw.replace(b'cross_a_to_b',b'seed')
        elif change=='cell': raw=raw.replace(b'85701,3,',b'85702,3,')
        else: raw+=w.COUNTER_ROW+b'\r\n'
        p.write_bytes(raw); monkeypatch.setattr(w,'COUNTER_SHA256',v1w.digest(raw))
    elif change=='seed': p.with_name('config.json').write_text(json.dumps({'seed':202627000}))
    elif change=='manifest-seed': p.with_name('manifest.json').write_text(json.dumps({'config':{'seed':202627000},'artifact_checksums':{'symbols.csv':v1w.digest(raw)}}))
    else: p.with_name('manifest.json').write_text(json.dumps({'config':{'seed':202615013},'artifact_checksums':{'symbols.csv':'bad'}}))
    with pytest.raises(ValueError): w.unseen_audit(tmp_path/'runs/prepared')


def test_real_counter_provenance_pin() -> None:
    import re
    p=Path(__file__).resolve().parents[1]/w.COUNTER_PATH
    raw=p.read_bytes()
    found=list(re.finditer(rb'2026270[01][0-9](?![0-9])',raw))
    evidence=w.nonseed_counter(p,raw,found)
    assert evidence is not None and evidence['record']['sha256']==w.COUNTER_SHA256


@pytest.mark.parametrize('value',['01','-0','+1',' 1','1.0',str(2**64),'nan'])
def test_numeric_boundary_schema_rejects_noncanonical_values(value: str) -> None:
    initial,material,rows=synthetic()
    rows[0]['eligible_tick']=value
    with pytest.raises(ValueError): a.BoundaryReplay(initial,material,'DELAY500',504).step(rows[0])
def test_gate_replay_cache_is_byte_keyed_and_immutable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls=[]
    code=tmp_path/'code.py'; code.write_text('first')
    outputs=tmp_path/'outputs'; outputs.mkdir(); journal=outputs/'journal.csv'; journal.write_text('first')
    monkeypatch.setattr(w,'IMPLEMENTATION',[code])
    def analyze(directory: Path, expected: list[dict[str,Any]], *, policy: str) -> dict[str,Any]:
        calls.append((directory,expected,policy)); return {'nested':{'value':len(calls)}}
    monkeypatch.setattr(a,'analyze_run',analyze)
    result=w.replay_gate(outputs,[],'IMMEDIATE'); result['nested']['value']=999
    assert w.replay_gate(outputs,[],'IMMEDIATE')['nested']['value']==1 and len(calls)==1
    journal.write_text('second')
    assert w.replay_gate(outputs,[],'IMMEDIATE')['nested']['value']==2
    code.write_text('second')
    assert w.replay_gate(outputs,[],'IMMEDIATE')['nested']['value']==3
    assert w.replay_gate(outputs,[],'LOCKED')['nested']['value']==4
    assert w.replay_gate(outputs,[{'id':1}],'LOCKED')['nested']['value']==5
@pytest.mark.parametrize('corruption',['missing-word','extra-word','cursor','overflow','noncanonical','crlf','empty'])
def test_complete_final_rng_schema(tmp_path: Path, corruption: str) -> None:
    path=tmp_path/'final_rng.txt'; raw=b'MTI 624\n'+b'0\n'*624; path.write_bytes(raw)
    w.validate_final_rng(path)
    if corruption=='missing-word': raw=raw[:-2]
    elif corruption=='extra-word': raw+=b'0\n'
    elif corruption=='cursor': raw=raw.replace(b'MTI 624',b'MTI 625')
    elif corruption=='overflow': raw=raw.replace(b'0\n',b'4294967296\n',1)
    elif corruption=='noncanonical': raw=raw.replace(b'0\n',b'00\n',1)
    elif corruption=='crlf': raw=raw.replace(b'\n',b'\r\n')
    else: raw=b''
    path.write_bytes(raw)
    with pytest.raises(ValueError): w.validate_final_rng(path)


def test_final_rng_changes_fail_even_with_identical_native_outputs() -> None:
    receipts: dict[str,Any]={name:{'exit_status':0,'files':{'native':{'sha256':'same'},'final_rng.txt':{'sha256':'same'},
                **({'scheduling_events001.csv':{'sha256':env.get('STRINGMOL_SCHEDULING_POLICY')}} if env.get('STRINGMOL_SCHEDULING_LOG')=='1' else {})}}
              for name,_,env in w.gate_cases()}
    w.compare_final_rng(receipts)
    for name in receipts:
        changed=deepcopy(receipts); changed[name]['files']['final_rng.txt']['sha256']='changed'
        with pytest.raises(ValueError): w.compare_final_rng(changed)
def test_all_inherited_suites_remain_required() -> None:
    commands=w.validation_commands()
    for name in ('control','lineage','conservation','decay','renewal','perturbation','replicated','mutation','scheduling'):
        assert f'tests/test_stringmol_{name}.py' in commands['pytest']
        assert f'tests/test_stringmol_{name}.py' in commands['mypy']


def test_foundation_builds_are_exact_native_packages(tmp_path: Path) -> None:
    m,h3,h2=(tmp_path/name for name in ('mutation.json','replicated.json','perturbation.json'))
    m.write_text(json.dumps({'inherited':str(h3)})); h3.write_text(json.dumps({'inherited':str(h2)}))
    entries={name:{'path':str(tmp_path/(name+'.json'))} for name in ('lineage','conservation','decay')}
    h2.write_text(json.dumps({'inherited':entries}))
    assert w.foundation_builds({'inherited':str(m)})=={k:Path(v['path']) for k,v in entries.items()}
    entries['unexpected']={'path':'unexpected'}; h2.write_text(json.dumps({'inherited':entries}))
    with pytest.raises(ValueError,match='native gate build set'): w.foundation_builds({'inherited':str(m)})


def test_native_control_uses_unchanged_m001_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from experiments.stringmol import analyze_mutation
    def analyze(directory: Path, expected: list[dict[str,Any]]) -> dict[str,Any]:
        assert directory==tmp_path and expected==[]
        return {'unchanged_m001':True}
    monkeypatch.setattr(w,'IMPLEMENTATION',[])
    monkeypatch.setattr(analyze_mutation,'analyze_run',analyze)
    assert w.replay_gate(tmp_path,[],'NATIVE')=={'unchanged_m001':True}
