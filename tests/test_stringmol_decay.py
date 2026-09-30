"""Adversarial v2 replay, frozen thresholds, schema and preparation guards."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import pytest
from experiments.stringmol.analyze_lineage import EVENT_COLUMNS, SNAPSHOT_COLUMNS
from experiments.stringmol import analyze_decay as a, decay_workflow as w, analyze_conservation as v1, conservation_workflow as v1w


def replay(route: str = 'recycle') -> a.Replay:
    return a.Replay(v1.initial_material([{'id':0,'sequence_hex':'4142'},{'id':1,'sequence_hex':'41'},{'id':2,'sequence_hex':'41'}],'histogram',0,8),route)


def event(index: int, kind: str, outcome: str, before: str, after: str, changes: str = '', proposal: str = '', tick: int = 0) -> dict[str,str]:
    return dict(zip(a.JOURNAL_COLUMNS,map(str,[tick,index,kind,outcome,before,after,changes,proposal]),strict=True))


@pytest.mark.parametrize('route',['recycle','sequester'])
def test_decay_funds_copy_only_when_accessible(route: str) -> None:
    r = replay(route)
    r.step(event(1,'DECAY','REMOVED','2','','2:0:41:00'))
    blocked = route == 'sequester'
    r.step(event(2,'COPY','BLOCKED' if blocked else 'ACCEPTED','0;1','0;1','' if blocked else '1:1:00:41','1:1:00:41' if blocked else '',2500))
    assert r.late_growth == (0 if blocked else 1)
    assert r.arrays['waste'][0] == int(blocked)
    assert r.exposure == 1
    assert r.nums['event_count'] == 2


def test_nul_contraction_and_hidden_tail() -> None:
    r = replay()
    r.buffers[0] = b'A\0B'+bytes(5)
    r.step(event(1,'COPY','ACCEPTED','0;1','0;1','0:0:41:00'))
    assert r.buffers[0] == b'\0\0B'+bytes(5)
    assert r.nums['contraction_bytes'] == 1 and r.arrays['pool'][0] == 1
    r.step(event(2,'DECAY','REMOVED','0','','0:2:42:00'))
    assert r.arrays['decay_removed'][1] == 1



@pytest.mark.parametrize('outcome',['FAILED','PLACED'])
def test_actual_cleave_returns(outcome: str) -> None:
    r = replay()
    placed = outcome == 'PLACED'
    r.step(event(1,'CLEAVE',outcome,'0;1','1;3' if placed else '1','0:0:41:00;0:1:42:00'+(';3:0:00:42' if placed else ''),tick=2500))
    assert r.arrays['cleavage_discard_returns' if placed else 'failed_placement_returns'][0] == 1
    assert r.late_births == int(placed)
    assert 0 not in r.buffers


@pytest.mark.parametrize('mutation',[
    {'index':'2'}, {'tick':'-1'}, {'before_ids':'9'}, {'after_ids':'2'},
    {'changes':'2:0:42:00'}, {'changes':'2:0:41:41'}, {'changes':''},
    {'changes':'2:7:00:41'}, {'changes':'2:0:41:ff'}, {'changes':'2:0:41:21'},
    {'proposal':'2:0:41:00'}, {'outcome':'WRONG'}, {'event':'WRONG'},
    {'before_ids':'02'}, {'before_ids':'2;2'},
])
def test_corrupt_decay_rejected(mutation: dict[str,str]) -> None:
    r = replay(); e = event(1,'DECAY','REMOVED','2','','2:0:41:00'); e.update(mutation)
    with pytest.raises(ValueError): r.step(e)


def test_scarcity_must_be_real() -> None:
    r = replay()
    with pytest.raises(ValueError): r.step(event(1,'COPY','BLOCKED','0;1','0;1',proposal='0:0:41:00'))


def test_removed_identity_cannot_return() -> None:
    r = replay(); r.step(event(1,'DECAY','REMOVED','2','','2:0:41:00'))
    with pytest.raises(ValueError): r.step(event(2,'CLEAVE','PLACED','0;1','0;1;2','0:1:42:00;2:0:00:42'))


def test_checkpoint_all_counters_derived() -> None:
    r = replay()
    arrays = {**r.arrays,'molecular':r.initial['molecular'],'initial':r.initial['total']}
    row = {'tick':'0','event':'CHECKPOINT', **{k:str(v) for k,v in {**r.nums,'max_residual':0,'molecular_bytes':4,'free_bytes':0}.items()}, **{f:str(v) for p,vs in arrays.items() for f,v in zip(v1.fields(p),vs,strict=True)}}
    r.checkpoint(row)
    for column in a.COLUMNS[2:]:
        bad = {**row,column:str(int(row[column])+1)}
        with pytest.raises(ValueError): r.checkpoint(bad)


def results() -> list[dict[str,Any]]:
    return [{'condition':arm,'seed':seed,'G_late':896 if arm == 'R' else 0,'B_late':50 if arm == 'R' else 0,'L':896,'successful_births':100,'max_two_parent_depth':2,'final_noninitial_descendants':100,'final_descendant_fraction':.5,'decay_exposure':1} for seed in range(202622000,202622020) for arm in ('R','S')]


def test_frozen_same_sixteen_pairs() -> None:
    r = results()
    assert a.outcomes(r,[])['decision'] == 'full pass'
    for row in r:
        if row['condition'] == 'R' and row['seed'] >= 202622016: row['G_late'] = 0
    assert a.outcomes(r,[])['full_support']
    r[30]['G_late'] = 0
    assert not a.outcomes(r,[])['full_support']


def test_disjoint_component_support_not_joint() -> None:
    r = results()
    for row in r:
        if row['condition'] == 'R':
            if row['seed'] < 202622004: row['G_late'] = 0
            if row['seed'] >= 202622016: row['B_late'] = 0
    out = a.outcomes(r,[])
    assert out['material_support'] and out['birth_support'] and not out['full_support']
    assert out['decision'] == 'material support only'


@pytest.mark.parametrize('field,value',[('G_late',895),('B_late',49),('L',895),('successful_births',99),('max_two_parent_depth',1),('final_noninitial_descendants',99),('final_descendant_fraction',.499)])
def test_thresholds_fixed(field: str, value: Any) -> None:
    r = results()
    for row in r:
        if row['condition'] == 'R': row[field] = value
    assert not a.outcomes(r,[])['full_support']


def test_exposure_failure_is_not_integrity_failure() -> None:
    r = results(); r[0]['decay_exposure'] = 0
    out = a.outcomes(r,[])
    assert out['integrity'] and not out['exposure'] and not out['full_support']
    assert out['run_denominator'] == 40 and len(out['pairs']) == 20


def test_missing_failed_duplicate_runs_keep_denominator() -> None:
    r = results()
    for runs,errors in [(r[:-1],[]),(r,[{'error':'bad'}]),(r+[r[0]],[])]:
        out = a.outcomes(runs,errors)
        assert out['decision'] == 'unevaluable' and len(out['pairs']) == 20


def test_input_matrix_and_sanitized_environment(tmp_path: Path) -> None:
    for arm,route in [('R','recycle'),('S','sequester')]:
        r = w.run_input(tmp_path,tmp_path,202622000,arm)
        assert r['route'] == route and sum(r['initial_material']['molecular']) == 8960
        assert r['initial_material']['pool'] == r['initial_material']['waste'] == [0]*33
        assert r['environment'] == {**v1w.ENV,'STRINGMOL_LINEAGE_LOG':'1','STRINGMOL_CONSERVATION':'1','STRINGMOL_POOL_MODE':'histogram','STRINGMOL_POOL_AMOUNT':'0','STRINGMOL_DECAY_DESTINATION':route}
        assert not Path(r['directory']).exists()


def test_protocol_and_patch_order() -> None:
    assert w.protocol_pin()['revision'] == w.PROTOCOL_REVISION
    assert [p.name[:4] for p in w.PATCHES] == ['0001','0002','0003','0004']
    assert len(a.COLUMNS) == len(set(a.COLUMNS))


def write_csv(path: Path, columns: list[str], data: list[dict[str,Any]]) -> None:
    import csv
    with path.open('w',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=columns,lineterminator='\n')
        writer.writeheader(); writer.writerows(data)


def extinction_fixture(path: Path, end: int, route: str) -> None:
    from experiments.stringmol.lineage_workflow import expected_initial
    initial = expected_initial('host')
    events: list[dict[str,Any]] = []
    for item in initial:
        row: dict[str,Any] = dict.fromkeys(EVENT_COLUMNS,-1)
        row.update(event='INIT',timestep=0,x=item['x'],y=item['y'],active_sequence_hex='',passive_sequence_hex='')
        row.update({'child_'+k:item[k] for k in ('id','species','label','sequence_hex')})
        events.append(row)
    row = dict.fromkeys(EVENT_COLUMNS,-1)
    row.update(event='END',timestep=end,population=0,child_sequence_hex='',active_sequence_hex='',passive_sequence_hex='')
    events.append(row)
    write_csv(path/'lineage_events001.csv',EVENT_COLUMNS,events)
    write_csv(path/'lineage_snapshots001.csv',SNAPSHOT_COLUMNS,[{'tick':t,**item} for t in range(0,end,100) for item in initial])
    (path/'popdy001.dat').write_text(''.join(f'{t},1,140\n' for t in range(0,end,100)))
    (path/'stdout.txt').write_text('FINISHED smspatial\n'); (path/'stderr.txt').write_text('')
    r = a.Replay(v1.initial_material(initial,'histogram',0,65),route)
    aggregates: list[dict[str,Any]] = []; buffers: list[dict[str,Any]] = []; journal: list[dict[str,Any]] = []
    for tick,kind in [(t,'CHECKPOINT') for t in range(0,end,100)]+[(end,'END')]:
        if kind == 'END':
            for i,b in list(r.buffers.items()):
                changes = ';'.join(f'{i}:{o}:{byte:02X}:00' for o,byte in enumerate(b) if byte)
                e = event(len(journal)+1,'DECAY','REMOVED',str(i),'',changes,tick=end-1)
                r.step(e); journal.append(e)
        arrays = {**r.arrays,'molecular':a.histogram(r.buffers),'initial':r.initial['total']}
        aggregate = {'tick':tick,'event':kind,**r.nums,'waste_bytes':sum(r.arrays['waste']),'max_residual':0,'molecular_bytes':sum(arrays['molecular']),'free_bytes':sum(arrays['pool']),**{f:v for p,vs in arrays.items() for f,v in zip(v1.fields(p),vs,strict=True)}}
        aggregates.append(aggregate)
        buffers.extend({'tick':tick,'event':kind,'id':i,'full_buffer_hex':b.hex().upper()} for i,b in r.buffers.items())
    write_csv(path/'conservation002.csv',a.COLUMNS,aggregates)
    write_csv(path/'conservation_buffers002.csv',v1.BUFFER_COLUMNS,buffers)
    write_csv(path/'material_events002.csv',a.JOURNAL_COLUMNS,journal)


@pytest.mark.parametrize('end',[1,4900,4901,5000])
@pytest.mark.parametrize('route',['recycle','sequester'])
def test_extinction_end_and_late_zero(tmp_path: Path, end: int, route: str) -> None:
    from experiments.stringmol.lineage_workflow import expected_initial
    extinction_fixture(tmp_path,end,route)
    result = a.analyze_run(tmp_path,expected_initial('host'),route,maxl0=65)
    assert result['end_timestep'] == end and result['end_population'] == 0
    assert result['final_population'] == (140 if end > 4900 else 0)
    assert result['G_late'] == result['B_late'] == 0
    assert len(result['conservation']) == len(range(0,end,100))+1
    assert result['decay_exposure'] == 140


@pytest.mark.parametrize('kind',['event-missing','event-duplicate','late-event','end-map','aggregate','wrong-route','snapshot','schema','lowercase'])
def test_cross_artifact_corruption(tmp_path: Path, kind: str) -> None:
    from experiments.stringmol.lineage_workflow import expected_initial
    extinction_fixture(tmp_path,1,'recycle')
    journal = tmp_path/'material_events002.csv'
    if kind in {'event-missing','event-duplicate','late-event'}:
        rows = v1.canonical_rows(journal,a.JOURNAL_COLUMNS)
        if kind == 'event-missing': rows.pop()
        elif kind == 'event-duplicate': rows.append(rows[-1])
        else: rows[-1]['tick'] = '1'
        write_csv(journal,a.JOURNAL_COLUMNS,list(rows))
    elif kind == 'end-map':
        with (tmp_path/'conservation_buffers002.csv').open('a') as f: f.write('1,END,0,'+('42'+'00'*64)+'\n')
    elif kind == 'aggregate':
        path = tmp_path/'conservation002.csv'; rows = v1.canonical_rows(path,a.COLUMNS); rows[-1]['decay_to_pool_42'] = '1'; write_csv(path,a.COLUMNS,list(rows))
    elif kind == 'snapshot':
        path = tmp_path/'lineage_snapshots001.csv'; path.write_text(path.read_text().replace(',0,1,',',999,1,',1))
    elif kind == 'schema': journal.write_text(journal.read_text().replace('proposal','unknown',1))
    elif kind == 'lowercase': journal.write_text(journal.read_text().replace(':4A:',':4a:',1))
    with pytest.raises(ValueError): a.analyze_run(tmp_path,expected_initial('host'),'sequester' if kind == 'wrong-route' else 'recycle',maxl0=65)


def test_preparation_never_executes_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import experiments.stringmol.lineage_workflow as lineage
    source = tmp_path/'source'; source.mkdir()
    build = tmp_path/'build.json'; build.write_text('{}')
    gate = tmp_path/'gate.json'; gate.write_text('{}')
    monkeypatch.setattr(w,'verify_build',lambda p:{'builds':{'observer':{'source':str(source)}}})
    monkeypatch.setattr(w,'verify_gate',lambda *args:None)
    monkeypatch.setattr(w,'protocol_pin',lambda:{'frozen':True})
    monkeypatch.setattr(w,'source_state',lambda p:{'commit':'fixture'})
    monkeypatch.setattr(w,'unseen_audit',lambda p:{'matches':[]})
    monkeypatch.setattr(w,'verify_preparation',lambda p:{})
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('prepare executed a simulator')
    monkeypatch.setattr(v1w,'execute',forbidden)
    root = tmp_path/'prepared'
    path = w.prepare(build,gate,root)
    data = lineage.read(path)
    assert len(data['runs']) == 40 and not (root/'runs').exists()
    assert not path.stat().st_mode & 0o222
    for r in data['runs']:
        assert not Path(r['config']).stat().st_mode & 0o222
        assert not Path(r['directory']).exists()
    assert lineage.record(path) == lineage.read(root/'preparation.sha256.json')


def test_dirty_launch_refused_before_execution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(w,'verify_preparation',lambda p:{})
    monkeypatch.setattr(w,'command',lambda *args:b'?? implementation.py\n')
    with pytest.raises(ValueError,match='commit implementation'):
        w.run_matrix(tmp_path/'preparation.json')
    assert not (tmp_path/'campaign.json').exists()


def test_no_decay_serializer_has_no_route_metadata() -> None:
    assert not any('route' in name or 'destination' in name for name in a.COLUMNS+a.JOURNAL_COLUMNS)
    cases = {name:env for name,_,_,_,env in w.gate_cases()}
    assert cases['nodecay-recycle']['STRINGMOL_DECAY_DESTINATION'] == 'recycle'
    assert cases['nodecay-sequester']['STRINGMOL_DECAY_DESTINATION'] == 'sequester'
    assert len(cases) == len(w.gate_cases())


def test_unseen_audit_distinguishes_seeds_from_float_substrings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(w,'ROOT',tmp_path)
    runs = tmp_path/'runs'; runs.mkdir()
    writes = runs/'writes.csv'
    writes.write_text('749,0.0015265119202622008,7.994989202622007,7.947281202622001,7.954202622012127,0.2751652026220111,7.99324202622018\n')
    assert w.unseen_audit(tmp_path/'prepared')['matches'] == []
    config = runs/'prior.conf'; config.write_text('RANDSEED 202622000\n')
    with pytest.raises(ValueError,match='prior input/use'): w.unseen_audit(tmp_path/'prepared')


def test_unseen_audit_includes_empty_seed_directories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(w,'ROOT',tmp_path)
    (tmp_path/'runs'/'202622019').mkdir(parents=True)
    with pytest.raises(ValueError,match='prior input/use'): w.unseen_audit(tmp_path/'prepared')


def test_unseen_audit_includes_seed_filenames(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(w,'ROOT',tmp_path)
    runs = tmp_path/'runs'; runs.mkdir()
    (runs/'R-202622001.conf').write_text('')
    with pytest.raises(ValueError,match='prior input/use'): w.unseen_audit(tmp_path/'prepared')


@pytest.mark.parametrize('changes',[
    # Both gross ledgers are <=2, but these change four/three distinct positions.
    '0:0:41:00;0:1:42:00;1:1:00:41;1:2:00:42',
    '0:0:41:00;0:1:42:41;1:1:00:42',
])
def test_accepted_copy_distinct_positions_not_gross_exchange(changes: str) -> None:
    r = replay()
    before = dict(r.buffers)
    with pytest.raises(ValueError,match='distinct changed position'):
        r.step(event(1,'COPY','ACCEPTED','0;1','0;1',changes))
    assert r.buffers == before and r.arrays['pool'] == [0]*33


def test_two_changed_positions_still_allowed() -> None:
    r = replay()
    r.step(event(1,'COPY','ACCEPTED','0;1','0;1','0:0:41:00;1:1:00:41'))
    assert r.arrays['copy_withdrawals'][0] == r.arrays['copy_returns'][0] == 1


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
    for seed in range(202622000,202622020):
        for arm in ('R','S'):
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
    assert len(evidence['freshness_audit']['excluded_files']) == 42
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
    new.write_text('seed,result\n202622007,1\n')
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
    elif kind == 'audit-input': prior.write_text('RANDSEED 202622000\n')
    elif kind == 'remote-url': evidence['remote']['url'] = 'ssh://wrong.invalid/repo.git'
    elif kind == 'remote-ref': evidence['remote']['ref'] = 'refs/heads/other'
    elif kind == 'remote-revision': evidence['remote']['observed_revision'] = 'b'*40
    elif kind == 'remote-bytes': evidence['remote']['stdout_hex'] = ''
    else: evidence['committed_files'][str(tmp_path/'code.py')]['bytes_hex'] = '00'
    with pytest.raises(ValueError): w.verify_launch_evidence(path,evidence,data)


def test_matrix_launch_uses_fresh_audit_before_any_seal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(w,'verify_preparation',lambda p:data)
    (tmp_path/'runs'/'late.conf').write_text('RANDSEED 202622018\n')
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('launch wrote a seal or executed after seed reuse')
    monkeypatch.setattr(w,'seal',forbidden)
    monkeypatch.setattr(v1w,'execute',forbidden)
    with pytest.raises(ValueError,match='prior input/use'): w.run_matrix(path)


def test_audit_exclusion_cannot_hide_another_preparation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    other = tmp_path/'runs'/'other'; other.mkdir()
    config = other/'R-202622000.conf'; config.write_text('held out input\n')
    with pytest.raises(ValueError,match='prior input/use'): w.launch_evidence(path,data)
    with pytest.raises(ValueError,match='exclusion outside'):
        w.unseen_audit(path.parent,authorized_files={*w.authorized_inputs(path,data),config})
