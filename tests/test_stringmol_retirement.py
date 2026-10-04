"""SM-B002 adversarial transfer, retirement and fail-closed launch fixtures."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
import pytest
from experiments.stringmol import analyze_retirement as a, retirement_workflow as w
from experiments.stringmol import analyze_conservation as c, analyze_renewal as h1
from experiments.stringmol.analyze_scheduling import DEFAULTS, COLUMNS as BOUNDARY_COLUMNS
from experiments.stringmol.analyze_decay import JOURNAL_COLUMNS


def decisions(i: int = 16, d: int = 16, *, controls: int = 20, exposure: int = 20) -> list[dict[str,Any]]:
    rows=[]
    for arm,seed in a.MATRIX:
        n=seed-a.SEEDS[0]
        count=controls if arm.endswith('RETAIN') else i if arm.startswith('IMMEDIATE') else d
        rows.append({'condition':arm,'seed':seed,'boundary_errors':0,'fatal_enforcement_errors':0,'zero_residual':True,
            'retirement_eligible':100 if n<exposure else 99,'retirements':100 if n<exposure else 99,
            **{k:t if n<count else 0 for k,t in zip(a.ENDPOINTS,a.THRESHOLDS,strict=True)}})
    return rows


@pytest.mark.parametrize('i,d,controls,exposure,branch',[(16,16,16,16,4),(4,16,20,16,5),(16,4,20,16,6),(4,4,20,16,7),(5,16,20,16,8),(15,15,20,16,8),(20,20,15,20,2),(20,20,20,15,3)])
def test_ladder(i: int,d: int,controls: int,exposure: int,branch: int) -> None:
    result=a.outcomes(decisions(i,d,controls=controls,exposure=exposure),[])
    assert result['branch']==branch and result['run_denominator']==80 and len(result['pairs'])==20
    assert result['admission_design_authorized']==(branch>=4)
    assert not result['admission_execution_authorized']


@pytest.mark.parametrize('key',a.ENDPOINTS)
def test_every_endpoint_boundary(key: str) -> None:
    rows=decisions()
    for r in rows:
        if r['condition'].endswith('RETAIN'): r[key]=a.THRESHOLDS[a.ENDPOINTS.index(key)]-1
    assert a.outcomes(rows,[])['branch']==2


@pytest.mark.parametrize('change',['missing','duplicate','boundary','fatal','residual','failure'])
def test_integrity_precedes_controls_and_exposure(change: str) -> None:
    rows=decisions(0,0,controls=0,exposure=0); failures=[]
    if change=='missing': rows.pop()
    elif change=='duplicate': rows[-1]=rows[0]
    elif change=='boundary': rows[0]['boundary_errors']=1
    elif change=='fatal': rows[0]['fatal_enforcement_errors']=1
    elif change=='residual': rows[0]['zero_residual']=False
    else: failures=[{'error':'fixture'}]
    assert a.outcomes(rows,failures)['branch']==1


def test_same_pairs_required() -> None:
    rows=decisions(4,16,controls=16)
    assert a.outcomes(rows,[])['branch']==8
    for r in rows:
        if r['condition']=='IMMEDIATE_RETIRE':
            r.update({k:t if r['seed']>=a.SEEDS[16] else 0 for k,t in zip(a.ENDPOINTS,a.THRESHOLDS,strict=True)})
    assert a.outcomes(rows,[])['branch']==5


def test_factorial_configs() -> None:
    for seed in a.SEEDS:
        runs=[w.run_input(Path('/source'),Path('/inputs'),seed,arm) for arm in a.ARMS]
        assert len({w.custom_config(r,Path('/source')) for r in runs})==1
        assert all(r['initial_material']==runs[0]['initial_material'] and r['expected_initial']==runs[0]['expected_initial'] for r in runs)
        assert all(r['environment']['NUMBA_NUM_THREADS']=='1' for r in runs)
        assert len({tuple(sorted((k,v) for k,v in r['environment'].items() if k not in ('STRINGMOL_SCHEDULING_POLICY','STRINGMOL_SOURCE_DISPOSITION'))) for r in runs})==1


def test_inherited_suites() -> None:
    for name in ('control','lineage','conservation','decay','renewal','perturbation','replicated','mutation','scheduling','retirement'):
        assert f'tests/test_stringmol_{name}.py' in w.validation_commands()['pytest']


def test_both_schedules_have_exact_parity_and_rng_cases() -> None:
    cases=w.gate_cases()
    assert len(cases)==18
    receipts: dict[str,Any]={name:{'exit_status':0,'files':{'native':{'sha256':'same'},'final_rng.txt':{'sha256':'same'},
        **({'scheduling_events001.csv':{'sha256':'s'}} if env.get('STRINGMOL_SCHEDULING_LOG')=='1' else {}),
        **({'source_events006.csv':{'sha256':'r'}} if env.get('STRINGMOL_RETIREMENT_LOG')=='1' and env.get('STRINGMOL_SOURCE_RETENTION')=='1' else {})}}
        for name,_,env in cases}
    w.compare_final_rng(receipts)
    for name in receipts:
        bad=deepcopy(receipts); bad[name]['files']['final_rng.txt']['sha256']='changed'
        with pytest.raises(ValueError): w.compare_final_rng(bad)


@pytest.mark.parametrize('seed',a.SEEDS)
def test_unseen_seed_audit(seed: int,tmp_path: Path,monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(w,'ROOT',tmp_path); (tmp_path/'runs').mkdir()
    (tmp_path/'runs/prior.conf').write_text(f'RANDSEED {seed}\n')
    with pytest.raises(ValueError,match='prior input/use'): w.unseen_audit(tmp_path/'runs/prepared')


def material(event: str,before: dict[int,bytes],after: dict[int,bytes],index: int,tick: int = 0) -> dict[str,str]:
    changes=[]
    for i in sorted(before.keys()|after.keys()):
        for o,(x,y) in enumerate(zip(before.get(i,bytes(64)),after.get(i,bytes(64)),strict=True)):
            if x!=y: changes.append(f'{i}:{o}:{x:02X}:{y:02X}')
    return {'tick':str(tick),'index':str(index),'event':event,'outcome':'PLACED' if event=='CLEAVE' else 'REMOVED',
        'before_ids':';'.join(map(str,sorted(before))),'after_ids':';'.join(map(str,sorted(after))),'changes':';'.join(changes),'proposal':''}


def source_fixture() -> a.SourceReplay:
    return a.SourceReplay(c.initial_material([{'id':0,'sequence_hex':('A'*40).encode().hex()},{'id':1,'sequence_hex':'42'}],'histogram',0,64))


def cut(replay: a.SourceReplay,source: int,child: int,offset: int,tick: int = 0) -> None:
    other=1; before={i:replay.material.buffers[i] for i in (source,other)}
    seq=before[source].split(b'\0',1)[0]; raw=before[source]
    after={**before,source:raw[:offset]+bytes(len(seq)-offset)+raw[len(seq):],child:seq[offset:]+bytes(64-len(seq)+offset)}
    if offset==0: del after[source]
    replay.step(material('CLEAVE',before,after,replay.material.nums['event_count']+1,tick))


def test_rooted_transfer_and_first_source_retention() -> None:
    replay=source_fixture(); cut(replay,0,2,1,2500); cut(replay,2,3,1,2501)
    summary=replay.transfer_summary()
    assert summary['qualifying_transfers']==2 and summary['serial_transfers']==1
    assert summary['max_nonrelocation_depth']==2 and summary['retained_late_transfer_renewals']==1
    assert summary['transfer_renewals'][0]['retention']==1


def test_relocation_never_reconnects() -> None:
    replay=source_fixture(); cut(replay,0,2,0); cut(replay,2,3,1); cut(replay,3,4,1)
    summary=replay.transfer_summary()
    assert summary['qualifying_transfers']==summary['serial_transfers']==summary['max_nonrelocation_depth']==0
    assert summary['orphan_transfers']==2 and replay.transfer_depth[4] is None
    assert summary['max_relocation_depth']==1


def test_retirement_ledger_separate_and_hidden_tail() -> None:
    initial=c.initial_material([{'id':0,'sequence_hex':(b'A'*40+bytes(10)+b'Z').hex()},{'id':1,'sequence_hex':'42'}],'histogram',0,64)
    replay=a.SourceReplay(initial); cut(replay,0,2,1)
    before={0:replay.material.buffers[0]}
    replay.step(material('RETIRE',before,{},2))
    m=replay.material
    assert m.retirement_returns==m.arrays['pool'] and sum(m.retirement_returns)==2
    assert sum(m.arrays['decay_returns'])==sum(m.arrays['waste'])==0
    assert m.retirements==1
    with pytest.raises((ValueError,KeyError)): replay.step(material('RETIRE',before,{},3))

from experiments.stringmol import conservation_workflow as v1w
import json

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
    assert len(evidence['freshness_audit']['excluded_files']) == 82
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
    new.write_text('seed,result\n202628007,1\n')
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
    elif kind == 'audit-input': prior.write_text('RANDSEED 202628000\n')
    elif kind == 'remote-url': evidence['remote']['url'] = 'ssh://wrong.invalid/repo.git'
    elif kind == 'remote-ref': evidence['remote']['ref'] = 'refs/heads/other'
    elif kind == 'remote-revision': evidence['remote']['observed_revision'] = 'b'*40
    elif kind == 'remote-bytes': evidence['remote']['stdout_hex'] = ''
    else: evidence['committed_files'][str(tmp_path/'code.py')]['bytes_hex'] = '00'
    with pytest.raises(ValueError): w.verify_launch_evidence(path,evidence,data)


def test_matrix_launch_uses_fresh_audit_before_any_seal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(w,'verify_preparation',lambda p:data)
    (tmp_path/'runs'/'late.conf').write_text('RANDSEED 202628019\n')
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('launch wrote a seal or executed after seed reuse')
    monkeypatch.setattr(w,'seal',forbidden)
    monkeypatch.setattr(v1w,'execute',forbidden)
    with pytest.raises(ValueError,match='prior input/use'): w.run_matrix(path)


def test_audit_exclusion_cannot_hide_another_preparation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    other = tmp_path/'runs'/'other'; other.mkdir()
    config = other/'R-202628000.conf'; config.write_text('held out input\n')
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
    assert len(list(root.iterdir())) == 82
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
    assert len(receipts) == 80




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
    prior.write_text('202628999 202628020 1202628000 0.202628000 2026280000')
    assert w.unseen_audit(folder/'prepared')['matches'] == []
    directory = folder/'run-s202628019'; directory.mkdir()
    with pytest.raises(ValueError, match='prior input/use'): w.unseen_audit(folder/'prepared')
    directory.rmdir()
    (folder/'alias').symlink_to(prior)
    with pytest.raises(ValueError, match='symlink'): w.unseen_audit(folder/'prepared')




def boundary_fixture(disposition: str = 'RETIRE') -> tuple[a.BoundaryReplay,list[dict[str,str]]]:
    initial=c.initial_material([{'id':0,'sequence_hex':'254142'},{'id':1,'sequence_hex':'4344'}],'histogram',0,8)
    journal=[{'tick':'1','index':'1','event':'CLEAVE','outcome':'PLACED','before_ids':'0;1','after_ids':'0;1;2','changes':'1:1:44:00;2:0:00:44','proposal':''}]
    if disposition=='RETIRE': journal.append({'tick':'1','index':'2','event':'RETIRE','outcome':'REMOVED','before_ids':'1','after_ids':'','changes':'1:0:43:00','proposal':''})
    rows: list[dict[str,str]]=[]
    def emit(event: str,tick: int,**kw: Any) -> None:
        rows.append({**DEFAULTS,'event':event,'tick':str(tick),'index':str(len(rows)+1),'policy':'IMMEDIATE',**{k:str(v) for k,v in kw.items()}})
    emit('START',0,eligible_tick=2,ids='0;1'); emit('TICK',0,ids='0;1')
    emit('SELECT',0,id=0,count=1,outcome='UNBOUND'); emit('SURVIVE',0,id=0)
    emit('SEARCH',0,id=0,other=1,count=1,selected=0,outcome='SELECTED')
    emit('ENCOUNTER',0,id=0,other=1,active=0,passive=1,count=1,selected=0,outcome='BOUND')
    emit('TICK',1,ids='0;1'); emit('SELECT',1,id=0,other=1,count=1,outcome='ACTIVE'); emit('SURVIVE',1,id=0,other=1)
    emit('DISPATCH',1,active=0,passive=1,opcode=37,owner=0,offset=0)
    emit('BIRTH',1,id=2,active=0,passive=1,source=1,eligible_tick=2,material_index=1)
    if disposition=='RETIRE': emit('DEATH',1,id=1,outcome='RETIRE',material_index=2)
    emit('COMPLETE',1,active=0,passive=1,material_index=len(journal))
    emit('CENSOR',2,id=2,eligible_tick=2)
    emit('END',2,material_index=len(journal),ids='2;0' if disposition=='RETIRE' else '2;0;1')
    return a.BoundaryReplay(initial,journal,'IMMEDIATE',2,disposition=disposition),rows


@pytest.mark.parametrize('disposition',['RETAIN','RETIRE'])
def test_linked_boundary_completion_and_bijection(disposition: str) -> None:
    replay,rows=boundary_fixture(disposition)
    for row in rows: replay.step(row)
    assert replay.summary(2)['boundary_errors']==0
    assert (not replay.pairs)==(disposition=='RETIRE')
    assert replay.source.material.retirements==int(disposition=='RETIRE')
    assert replay.list_transactions[1]['next_after']==([2,0] if disposition=='RETIRE' else [2])


@pytest.mark.parametrize('kind',['wrong-source','double-refund','admission-order','missing-retire','missing-death','counter','id-reuse','dangling','duplicate-list','hidden-byte','wrong-policy','missing-complete'])
def test_retirement_boundary_adversaries(kind: str) -> None:
    replay,rows=boundary_fixture()
    def at(event: str) -> int: return next(i for i,r in enumerate(rows) if r['event']==event)
    if kind=='wrong-source': rows[at('BIRTH')]['source']='0'
    elif kind=='double-refund':
        replay.material.append({**replay.material[-1],'index':'3'}); rows[at('COMPLETE')]['material_index']='3'
    elif kind=='admission-order':
        birth,death=at('BIRTH'),at('DEATH'); rows[birth],rows[death]=rows[death],rows[birth]
    elif kind=='missing-retire':
        replay.material.pop(); rows.pop(at('DEATH')); rows[at('COMPLETE')]['material_index']='1'; rows[at('END')].update(material_index='1',ids='2;0;1')
    elif kind=='missing-death': rows.pop(at('DEATH'))
    elif kind=='counter': rows[at('COMPLETE')]['material_index']='1'
    elif kind=='id-reuse': rows[at('BIRTH')]['id']='0'
    elif kind=='dangling': rows[at('END')]['ids']='2;0;1'
    elif kind=='duplicate-list': rows[at('END')]['ids']='2;0;0'
    elif kind=='hidden-byte': replay.material[-1]['changes']=''
    elif kind=='wrong-policy': replay.disposition='RETAIN'
    else: rows.pop(at('COMPLETE'))
    for i,row in enumerate(rows): row['index']=str(i+1)
    with pytest.raises((ValueError,KeyError)):
        for row in rows: replay.step(row)
        replay.summary(2)


@pytest.mark.parametrize('born,length,kept,expected',[(2499,40,40,False),(2500,31,31,False),(2500,32,29,True),(2500,40,36,True),(2500,40,35,False)])
def test_retained_late_boundaries(born: int,length: int,kept: int,expected: bool) -> None:
    # First-source positional retention includes every non-NUL birth byte.
    birth=b'A'*length+bytes(64-length)
    now=b'A'*kept+b'B'*(length-kept)+bytes(64-length)
    stats=h1.retention(birth,now)
    assert (born>=2500 and stats['birth_length']>=32 and 10*stats['retained_bytes']>=9*stats['birth_length'])==expected

def counter_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path,bytes]:
    import re
    monkeypatch.setattr(w,'ROOT',tmp_path)
    p=tmp_path/w.COUNTER_PATH; p.parent.mkdir(parents=True)
    raw=w.COUNTER_HEADER+b'\r\n'+w.COUNTER_ROW+b'\r\n'
    p.write_bytes(raw)
    monkeypatch.setattr(w,'COUNTER_SHA256',v1w.digest(raw))
    p.with_name('config.json').write_text(json.dumps({'seed':202614006}))
    p.with_name('manifest.json').write_text(json.dumps({'config':{'seed':202614006},'artifact_checksums':{'symbols.csv':v1w.digest(raw)}}))
    original=w.record
    def record(path: Path) -> dict[str,Any]:
        saved=original(path)
        if path==p.with_name('config.json'): saved['sha256']='86e792e7d95382934ec751ba1eedf5bd99a9b1c3634b761c6d8d8fd4b41c4fa1'
        if path==p.with_name('manifest.json'): saved['sha256']='e88911210a0a5344c8a3012fddd8108c7597e58ba453c97d6eee68d7a56a009d'
        return saved
    monkeypatch.setattr(w,'record',record)
    assert len(list(re.finditer(rb'2026280[01][0-9](?![0-9])',raw)))==1
    return p,raw


def test_audit_classifies_only_pinned_historical_counter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p,raw=counter_fixture(tmp_path,monkeypatch)
    audit=w.unseen_audit(tmp_path/'runs/prepared')
    assert audit['matches']==[] and len(audit['nonseed_counter_matches'])==1
    evidence=audit['nonseed_counter_matches'][0]
    assert evidence['field']=='returns' and evidence['run_seed']==202614006 and evidence['value']==202628016
    assert audit['inventory'][w.COUNTER_PATH]['sha256']==v1w.digest(raw)
    assert evidence['path']==str(p.relative_to(tmp_path)) and not audit['excluded_files']


@pytest.mark.parametrize('change',['path','hash','header','cell','duplicate','seed','manifest-seed','manifest-artifact'])
def test_counter_classification_cannot_hide_seed_use(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    p,raw=counter_fixture(tmp_path,monkeypatch)
    if change=='path': p.rename(p.with_name('other.csv'))
    elif change=='hash': p.write_bytes(raw+b'\r\n')
    elif change in ('header','cell','duplicate'):
        if change=='header': raw=raw.replace(b'returns',b'seed')
        elif change=='cell': raw=raw.replace(b'88801,39,',b'88802,39,')
        else: raw+=w.COUNTER_ROW+b'\r\n'
        p.write_bytes(raw); monkeypatch.setattr(w,'COUNTER_SHA256',v1w.digest(raw))
    elif change=='seed': p.with_name('config.json').write_text(json.dumps({'seed':202628016}))
    elif change=='manifest-seed': p.with_name('manifest.json').write_text(json.dumps({'config':{'seed':202628016},'artifact_checksums':{'symbols.csv':v1w.digest(raw)}}))
    else: p.with_name('manifest.json').write_text(json.dumps({'config':{'seed':202614006},'artifact_checksums':{'symbols.csv':'bad'}}))
    with pytest.raises(ValueError): w.unseen_audit(tmp_path/'runs/prepared')


def test_real_counter_provenance_pin() -> None:
    import re
    p=Path(__file__).resolve().parents[1]/w.COUNTER_PATH
    raw=p.read_bytes()
    found=list(re.finditer(rb'2026280[01][0-9](?![0-9])',raw))
    evidence=w.nonseed_counter(p,raw,found)
    assert evidence is not None and evidence['record']['sha256']==w.COUNTER_SHA256




def source_journal_fixture() -> tuple[a.BoundaryReplay,list[dict[str,str]],list[dict[str,str]]]:
    replay,rows=boundary_fixture()
    for r in rows: replay.step(r)
    native=[{'event':'INIT' if i<2 else 'BIRTH','child_id':str(i),'x':str(i),'y':'0'} for i in range(3)]
    tx={'tick':'1','material_index':'1','active':'0','passive':'1','flow_source':'1','flow_offset':'1',
        'source':'1','offset':'1','child':'2','eligible_tick':'2','decision':'RETIRE','remnant_hex':'4300000000000000',
        'source_x':'1','source_y':'0','child_x':'2','child_y':'0','survivor':'0','now_before':'','next_before':'2',
        'now_after':'','next_after':'2;0','proposals':'1','eligible':'1','committed':'1'}
    return replay,[tx],native


def test_independent_full_source_journal() -> None:
    replay,rows,native=source_journal_fixture()
    result=a.verify_source_transactions(replay,rows,native)
    assert result['retirements']==1 and sum(result['retirement_returns'])==1


@pytest.mark.parametrize('field,value',[('active','1'),('passive','0'),('proposals','0'),('eligible','0'),('committed','2'),('source','0'),('flow_source','0'),('flow_offset','0'),('offset','0'),('decision','RETAIN'),('remnant_hex','4300410000000000'),('child_x','1'),('source_x','2'),('survivor','-1'),('next_before','2;0'),('next_after','0;2'),('now_after','0'),('material_index','2'),('eligible_tick','3')])
def test_source_journal_adversaries(field: str,value: str) -> None:
    replay,rows,native=source_journal_fixture(); rows[0][field]=value
    with pytest.raises((ValueError,KeyError)): a.verify_source_transactions(replay,rows,native)


def test_retirement_vacancy_cannot_fund_admission() -> None:
    replay,rows,native=source_journal_fixture(); native[2]['x']='1'; rows[0]['child_x']='1'
    with pytest.raises(ValueError,match='admission'): a.verify_source_transactions(replay,rows,native)


def test_native_partner_cleanup_does_not_erase_transfer_edge() -> None:
    initial=c.initial_material([{'id':0,'sequence_hex':''},{'id':1,'sequence_hex':(b'A'*40).hex()}],'histogram',0,64)
    replay=a.SourceReplay(initial); before=replay.material.buffers.copy()
    after={1:b'A'+bytes(63),2:b'A'*39+bytes(25)}
    replay.step(material('CLEAVE',before,after,1,2500))
    assert not replay.edges[0]['productive']
    assert replay.transfer_summary()['qualifying_transfers']==1 and replay.transfer_depth[2]==1


def test_h001_credit_is_explicitly_scoped_in_reports() -> None:
    replay=source_fixture(); cut(replay,0,2,1)
    edge=replay.transfer_summary()['transfer_edges'][0]
    assert not {'productive','orphan_source','source_depth','child_depth','origin'} & edge.keys()
    assert edge['rooted_transfer'] and edge['nonrelocation_depth']==1
    left={'qualifying_transfers':1,'pre_retirement_H001_diagnostic_credit':{'productive_source_births':2}}
    right={'qualifying_transfers':0,'pre_retirement_H001_diagnostic_credit':{'productive_source_births':0}}
    result=a.comparisons(left,right)
    assert 'productive_source_births' not in result
    assert result['qualifying_transfers']['difference']==1
    assert result['pre_retirement_H001_diagnostic_credit']['productive_source_births']['difference']==2
    distribution=a.distribution_comparisons(left,right)
    assert 'retention_distribution' not in distribution
    assert 'retention_distribution' in distribution['pre_retirement_H001_diagnostic_credit']


@pytest.mark.parametrize('phase', [*w.PREPUBLICATION_FAULTS, *w.POSTPUBLICATION_FAULTS, *w.WRITE_FAULTS])
def test_fatal_phase_cannot_be_evaluated_even_with_success_markers(phase: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path/'stdout.txt').write_text('FINISHED smspatial\n')
    (tmp_path/'stderr.txt').write_text(f'SM-B002 fatal enforcement: {phase}\n')
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('fatal run reached scientific replay')
    monkeypatch.setattr(a, 'diagnostic_run', forbidden)
    with pytest.raises(ValueError, match='fatal process; unevaluable'):
        a.analyze_run(tmp_path, [], policy='IMMEDIATE_RETIRE', exit_status=1)
    # A forged zero exit cannot convert fatal diagnostics to a successful run.
    with pytest.raises(ValueError, match='fatal diagnostic; unevaluable'):
        a.analyze_run(tmp_path, [], policy='IMMEDIATE_RETIRE', exit_status=0)


@pytest.mark.parametrize('marker', ['SM-C001 integrity failure: journal write', 'SM-B001 boundary failure: journal write', 'SM-B002 unevaluable after publication: free'])
def test_inherited_journal_failure_cannot_be_hidden_by_zero_exit(marker: str, tmp_path: Path) -> None:
    (tmp_path/'stderr.txt').write_text(marker+'\n')
    with pytest.raises(ValueError, match='fatal diagnostic; unevaluable'):
        a.analyze_run(tmp_path, [], policy='IMMEDIATE_RETIRE')


@pytest.mark.parametrize('last', ['BIRTH', 'DEATH'])
def test_partial_publication_is_not_a_completed_transaction(last: str) -> None:
    replay, rows = boundary_fixture()
    stop = next(i for i,r in enumerate(rows) if r['event']==last)
    for row in rows[:stop+1]: replay.step(row)
    with pytest.raises(ValueError): replay.summary(2)


def test_retire_failure_cannot_fall_back_to_retain() -> None:
    retained, rows = boundary_fixture('RETAIN')
    initial = c.initial_material([{'id':0,'sequence_hex':'254142'},{'id':1,'sequence_hex':'4344'}],'histogram',0,8)
    replay = a.BoundaryReplay(initial, retained.material, 'IMMEDIATE', 2, disposition='RETIRE')
    with pytest.raises(ValueError):
        for row in rows: replay.step(row)
        replay.summary(2)


@pytest.mark.parametrize('phase', [*w.POSTPUBLICATION_FAULTS, *w.WRITE_FAULTS])
def test_any_partial_publication_makes_campaign_unevaluable(phase: str) -> None:
    results = decisions(20,20)
    failed = results.pop()
    result = a.outcomes(results, [{'condition':failed['condition'],'seed':failed['seed'],
        'error':f'fatal {phase}; unevaluable'}])
    assert result['branch']==1 and not result['admission_design_authorized']


def fault_tree(root: Path) -> None:
    """Synthetic journal prefixes for adversarial receipt verification, no execution."""
    import csv
    import io
    def encode(columns: list[str], rows: list[dict[str,str]]) -> bytes:
        out=io.StringIO(); writer=csv.writer(out,lineterminator='\n')
        writer.writerows([[r[k] for k in columns] for r in rows])
        return out.getvalue().encode()
    replay, boundaries = boundary_fixture()
    _, sources, _ = source_journal_fixture()
    birth = next(r for r in boundaries if r['event']=='BIRTH')
    death = next(r for r in boundaries if r['event']=='DEATH')
    for phase in (*w.PREPUBLICATION_FAULTS,*w.POSTPUBLICATION_FAULTS,*w.WRITE_FAULTS):
        before = phase in w.PREPUBLICATION_FAULTS
        writing = phase in w.WRITE_FAULTS
        for target in (0,1):
            for state in (0,1,2):
                path=root/f'{phase}-{target}-{state}';path.mkdir(parents=True)
                m=[deepcopy(replay.material[0]),{**replay.material[1],'before_ids':str(1-target)}]
                b=[birth,{**death,'id':str(1-target)}]
                records={'material':[encode(JOURNAL_COLUMNS,[r]) for r in m],
                    'boundary':[encode(BOUNDARY_COLUMNS,[r]) for r in b],
                    'source':[encode(a.SOURCE_COLUMNS,sources)]}
                contents={'material':records['material'][0],'boundary':records['boundary'][0],'source':b''}
                if not before:
                    for stream in ('material','boundary','source'):
                        name='death' if stream=='boundary' else stream
                        if phase==name+'_write_error': break
                        row=records[stream][-1]
                        contents[stream]+=row[:len(row)//2] if phase==name+'_write_short' else row
                        if phase in (name,name+'_write_short'): break
                n=sum(len(contents[stream].rsplit(b'\n',1)[-1]) for stream in contents)
                for stream,raw in contents.items(): (path/f'{stream}.csv').write_bytes(raw)
                (path/'exit.json').write_text(json.dumps({'exit_status':1}))
                (path/'witness.json').write_text(json.dumps({'phase':phase,'target':target,'list':state,
                    'checkpoint_seen':int(before),'rolled_back':before,'committed':int(not before),'frees':int(phase=='free'),
                    'write_attempts':int(writing),'partial_write_bytes':n,'logging':True,'no_fallback':True}))
                diagnostic='journal write' if writing else f'SM-B002 {"rolled back before publication" if before else "unevaluable after publication"}: {phase}'
                (path/'stderr.txt').write_text(diagnostic+'\n')


@pytest.mark.parametrize('tamper', ['none','missing','exit','preflight','rollback','free','write','truncate','complete','retain','link'])
def test_fault_receipt_and_publication_adversaries(tmp_path: Path, tamper: str) -> None:
    fault_tree(tmp_path)
    if tamper=='missing': (tmp_path/'validate-0-0'/'exit.json').unlink()
    elif tamper in ('exit','preflight','rollback','free','write'):
        phase,filename,key,value={
            'exit':('free','exit.json','exit_status',0),
            'preflight':('refund','witness.json','checkpoint_seen',0),
            'rollback':('append','witness.json','rolled_back',False),
            'free':('free_before','witness.json','frees',1),
            'write':('material_write_short','witness.json','write_attempts',0),
        }[tamper]
        path=tmp_path/f'{phase}-0-0'/filename
        data=json.loads(path.read_text());data[key]=value;path.write_text(json.dumps(data))
    elif tamper=='truncate': (tmp_path/'source_write_short-0-0'/'source.csv').write_bytes(b'')
    elif tamper=='complete':
        with (tmp_path/'material-0-0'/'boundary.csv').open('ab') as out: out.write(b'COMPLETE\n')
    elif tamper in ('retain','link'):
        path=tmp_path/'free-0-0'/('source.csv' if tamper=='retain' else 'boundary.csv')
        path.write_text(path.read_text().replace('RETIRE','RETAIN' if tamper=='retain' else 'DECAY'))
    if tamper=='none':
        evidence=w.fault_evidence(tmp_path)
        assert evidence['cases']==114 and len(evidence['files'])==684
    else:
        with pytest.raises(ValueError): w.fault_evidence(tmp_path)
