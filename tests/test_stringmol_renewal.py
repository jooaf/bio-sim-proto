"""Frozen SM-H001 scientific definitions, adversarial replay, and launch seals."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import pytest

from experiments.stringmol import analyze_renewal as a, renewal_workflow as w
from experiments.stringmol import analyze_decay as d, analyze_conservation as v1
from experiments.stringmol import conservation_workflow as v1w, decay_workflow, lineage_workflow
from experiments.stringmol.analyze_lineage import EVENT_COLUMNS, SNAPSHOT_COLUMNS


def replay(*raw: bytes) -> a.SourceReplay:
    size = max(map(len, raw)) + 2
    initial = v1.initial_material([{'id': i, 'sequence_hex': b'A'.hex()} for i in range(len(raw))], 'histogram', 0, size)
    buffers = {i: b + bytes(size - len(b)) for i, b in enumerate(raw)}
    initial['buffers'] = {str(i): b.hex().upper() for i, b in buffers.items()}
    initial['molecular'] = initial['total'] = d.histogram(buffers)
    return a.SourceReplay(initial)


def step(r: a.SourceReplay, before: list[int], after: dict[int, bytes], *, kind: str = 'CLEAVE', outcome: str = 'PLACED', tick: int = 0) -> None:
    size = r.material.size
    after = {i: raw + bytes(size - len(raw)) for i, raw in after.items()}
    changes: list[str] = []
    for i in sorted(set(before) | set(after)):
        old = r.material.buffers[i] if i in before else bytes(size)
        new = after.get(i, bytes(size))
        changes.extend(f'{i}:{o}:{b:02X}:{n:02X}' for o, (b, n) in enumerate(zip(old, new, strict=True)) if b != n)
    r.step({'tick': str(tick), 'index': str(r.material.nums['event_count'] + 1), 'event': kind, 'outcome': outcome,
            'before_ids': ';'.join(map(str, sorted(before))), 'after_ids': ';'.join(map(str, sorted(after))), 'changes': ';'.join(changes), 'proposal': ''})


def cleave(r: a.SourceReplay, source: int, other: int, child: int, offset: int, tick: int = 0) -> None:
    raw = r.material.buffers[source]
    seq = a.visible(raw)
    after = {other: r.material.buffers[other], child: seq[offset:]}
    if offset:
        after[source] = raw[:offset] + bytes(len(seq) - offset) + raw[len(seq):]
    step(r, [source, other], after, tick=tick)


def native(r: a.SourceReplay, roles: list[str]) -> None:
    rows = []
    for edge, role in zip(r.edges, roles, strict=True):
        other = next(i for i in edge['participants'] if i != edge['source'])
        active, passive = (edge['source'], other) if role == 'active' else (other, edge['source'])
        rows.append({'child_id': str(edge['child']), 'timestep': str(edge['tick']), 'active_id': str(active), 'passive_id': str(passive)})
    r.native_roles(rows)


@pytest.mark.parametrize('role', ['active', 'passive'])
def test_independent_source_depth_roles_and_survival(role: str) -> None:
    r = replay(b'ABCD', b'A')
    cleave(r, 0, 1, 2, 1)
    cleave(r, 2, 1, 3, 1, 1)
    cleave(r, 3, 1, 4, 1, 2)
    native(r, [role]*3)
    summary = r.summary(3)
    assert summary['productive_source_births'] == 3
    assert summary['renewing_descendants'] == summary['serial_source_births'] == 2
    assert summary['max_source_depth'] == 3
    assert summary['retention_distribution'] == [1.0, 1.0]
    assert summary['source_role_counts'] == {role: 3}
    step(r, [2], {}, kind='DECAY', outcome='REMOVED', tick=3)
    assert not r.summary(4)['renewals'][0]['survived_END']
    with pytest.raises(ValueError):
        r.step(event(5, 'COPY', 'NOOP', '1;2', '1;2', tick=4))


def test_transfer_orphan_exclusion_propagates_and_roles_reported() -> None:
    r = replay(b'ABCDE', b'AB')
    cleave(r, 0, 1, 2, 0)
    cleave(r, 2, 1, 3, 1, 1)
    cleave(r, 3, 1, 4, 1, 2)
    # An initial source remains qualifying even when its other parent is orphaned.
    cleave(r, 1, 4, 5, 1, 3)
    native(r, ['active', 'passive', 'active', 'active'])
    out = r.summary(4)
    assert out['whole_parent_transfers'] == 1
    assert out['orphan_source_productive_births'] == 2
    assert out['productive_source_births'] == 3
    assert out['renewing_descendants'] == out['serial_source_births'] == 0
    assert out['late_renewing_descendants'] == out['retained_late_renewals'] == 0
    assert out['max_source_depth'] == 1
    assert [r.depth[i] for i in (2, 3, 4, 5)] == [None, None, None, 1]
    assert out['excluded_descendants'][0]['participation'] == {'passive': 1, 'source': 1, 'productive_source': 1}
    assert out['excluded_descendants'][2]['participation'] == {'passive': 1}


def test_hidden_tails_preserved_partial_and_released_whole() -> None:
    r = replay(b'ABC\0D', b'A')
    cleave(r, 0, 1, 2, 1)
    assert r.material.buffers[0].startswith(b'A\0\0\0D')
    assert r.material.buffers[2].startswith(b'BC\0\0\0')
    assert r.edges[0]['productive']
    cleave(r, 0, 1, 3, 0, 1)
    assert r.edges[1]['whole_transfer'] and r.depth[3] is None
    assert r.material.arrays['pool'][v1.ALPHABET.index('D')] == 1


def test_failed_nochange_and_source_death() -> None:
    r = replay(b'AB', b'A')
    step(r, [0, 1], {0: b'AB', 1: b'A'}, outcome='NO_CHANGE')
    step(r, [0, 1], {1: b'A'}, outcome='FAILED')
    out = r.summary(1)
    assert out['native_births'] == 0
    assert out['failed_placements'] == out['no_change_cleavages'] == 1
    assert r.deaths == {0: 0}
    assert r.material.arrays['failed_placement_returns'][:2] == [1, 1]


@pytest.mark.parametrize('source', [0, 1])
@pytest.mark.parametrize('active', [0, 1])
@pytest.mark.parametrize('offset', [0, 1])
def test_failed_cut_empty_partner_native_single_cleanup(source: int, active: int, offset: int) -> None:
    # COPY makes the partner empty-visible but leaves its second B hidden.
    # Sorting IDs cannot reveal whether the source or partner is active.
    other = 1 - source
    r = replay(*([b'ABC\0D', b'BB'] if source == 0 else [b'BB', b'ABC\0D']))
    step(r, [0, 1], {source: r.material.buffers[source], other: b'\0B'}, kind='COPY', outcome='ACCEPTED')
    before = r.material.buffers.copy()
    healed = {source: b'A'[:offset] + bytes(4 - offset) + b'D', other: b'\0B'}
    # Native return 1 takes precedence over return 2, even if both are empty.
    removed = active if not a.visible(healed[active]) else 1 - active
    after = {i: b for i, b in healed.items() if i != removed}
    padded = {i: b + bytes(r.material.size - len(b)) for i, b in after.items()}
    assert a.infer_suffix(before, padded, None) == (source, offset)
    assert a.suffix_cleanup_orders(before, padded, source, offset, None) == ([active] if offset == 0 else [0, 1])
    step(r, [0, 1], after, outcome='FAILED')
    assert r.material.buffers == padded and r.deaths == {removed: 0}
    assert all(r.summary(1)[k] == 0 for k in a.ENDPOINTS)
    assert r.summary(1)['failed_placements'] == 1 and not r.edges
    assert sum(r.material.arrays['failed_placement_returns']) == (3 - offset) + 1
    # The survivor's hidden tail is released only on its later death.
    survivor = next(iter(after))
    if survivor == source:
        assert r.material.buffers[survivor][4] == ord('D')
    else:
        assert r.material.buffers[survivor][1] == ord('B')
    step(r, [survivor], {}, kind='DECAY', outcome='REMOVED', tick=1)
    assert r.material.arrays['pool'] == r.material.initial['total']
    assert not r.material.buffers and r.summary(2)['native_births'] == 0


@pytest.mark.parametrize('active', [0, 1])
@pytest.mark.parametrize('source', [0, 1])
def test_placed_cut_empty_partner_crosschecks_cleanup_without_choosing_source(active: int, source: int) -> None:
    other = 1 - source
    r = replay(*([b'ABC\0D', b'\0B'] if source == 0 else [b'\0B', b'ABC\0D']))
    healed = {source: b'\0\0\0\0D', other: b'\0B'}
    after = {i: b for i, b in healed.items() if i != active}
    after[2] = b'ABC'
    step(r, [0, 1], after)
    edge = r.edges[0]
    assert (edge['source'], edge['offset']) == (source, 0)
    assert edge['cleanup_active_ids'] == [active]
    assert r.depth[2] is None and not edge['productive']
    assert edge['whole_transfer'] == (active == source)
    role = 'active' if active == source else 'passive'
    native(r, [role])
    with pytest.raises(ValueError, match='source/native cleanup order'):
        native(r, ['passive' if role == 'active' else 'active'])
    assert (edge['source'], edge['offset']) == (source, 0)


@pytest.mark.parametrize('after', [
    {},  # Old blanket empty-buffer filtering incorrectly accepted both deaths.
    {0: b'\0\0\0\0D', 1: b'\0B'},  # Native must remove one empty parent.
    {0: b''},  # Illicit release of the surviving passive's hidden D.
    {1: b''},  # Illicit release of the surviving passive's hidden B.
    {0: b'ABC\0D'},  # No source suffix was lost.
])
def test_failed_whole_cut_rejects_impossible_cleanup(after: dict[int, bytes]) -> None:
    r = replay(b'ABC\0D', b'\0B')
    with pytest.raises(ValueError, match='suffix transfer'):
        step(r, [0, 1], after, outcome='FAILED')


@pytest.mark.parametrize('after', [
    {0: b'AC', 1: b'A', 2: b'BD'},  # noncontiguous
    {0: b'A', 1: b'A', 2: b'DCB'},  # reorder
    {0: b'A', 1: b'A', 2: b'BC'},   # pool double credit D
    {0: b'AB', 1: b'A', 2: b'CD\0A'},  # child hidden gain
    {0: b'AB', 1: b'B', 2: b'CD'},  # unexplained other change
])
def test_invalid_suffix_and_double_credit_fail(after: dict[int, bytes]) -> None:
    with pytest.raises(ValueError): step(replay(b'ABCD', b'A'), [0, 1], after)


def test_reuse_cycles_and_unknown_parent_fail() -> None:
    r = replay(b'ABCD', b'A')
    cleave(r, 0, 1, 2, 0)
    with pytest.raises(ValueError): cleave(r, 2, 1, 0, 1)
    with pytest.raises(ValueError): cleave(r, 2, 1, 2, 1)
    with pytest.raises(ValueError):
        r.step({'tick': '0', 'index': '2', 'event': 'CLEAVE', 'outcome': 'PLACED', 'before_ids': '1;99', 'after_ids': '1;99;100', 'changes': '100:0:00:41', 'proposal': ''})


@pytest.mark.parametrize('value', [0.0, 0.9, 1.0])
def test_positional_retention(value: float) -> None:
    birth = b'ABCDEFGHIJ\0K'
    current = bytearray(birth)
    positions = [o for o, b in enumerate(birth) if b]
    # Include hidden non-NUL material in the complete birth-buffer denominator.
    for o in positions[:len(positions) - int(value * len(positions))]: current[o] = ord('Z')
    out = a.retention(birth, bytes(current))
    assert out['birth_length'] == 11
    assert out['retained_bytes'] == int(value * 11)
    assert a.retention(b'ABCDEFGHIJ', b'ZBCDEFGHIJ')['retention'] == .9
    assert a.retention(b'AB', b'BA')['retention'] == 0


@pytest.mark.parametrize('birth_tick,late', [(2499, False), (2500, True)])
@pytest.mark.parametrize('length,retained,accepted', [(40, 36, True), (40, 35, False), (40, 40, True), (40, 0, False), (31, 31, False)])
def test_late_retention_at_first_source_only(birth_tick: int, late: bool, length: int, retained: int, accepted: bool) -> None:
    r = replay(b'A'*(length+1), b'B'*length)
    cleave(r, 0, 1, 2, 1, birth_tick)
    # Return B into the free pool, then mutate the descendant through actual COPY events.
    step(r, [1], {}, kind='DECAY', outcome='REMOVED', tick=birth_tick)
    for pos in range(length - retained):
        buf = bytearray(r.material.buffers[2]); buf[pos] = ord('B')
        step(r, [0, 2], {0: r.material.buffers[0], 2: bytes(buf)}, kind='COPY', outcome='ACCEPTED', tick=birth_tick)
    cleave(r, 2, 0, 3, length - 1, birth_tick + 1)
    out = r.summary(birth_tick + 2)
    assert out['late_renewing_descendants'] == int(late)
    assert out['retained_late_renewals'] == int(late and accepted)
    assert out['renewals'][0]['retained_bytes'] == retained
    assert out['renewals'][0]['birth_length'] == length
    # A later source birth must not overwrite the first pre-source retention.
    saved = dict(r.renewals[2])
    cleave(r, 2, 0, 4, 1, birth_tick + 2)
    assert r.renewals[2] == saved


def results() -> list[dict[str, Any]]:
    return [{'condition': arm, 'seed': seed, 'native_births': 100 if arm == 'host' else 0,
             **{key: value if arm == 'host' else 0 for key, value in zip(a.ENDPOINTS, a.THRESHOLDS, strict=True)}} for arm, seed in a.MATRIX]


def test_frozen_decision_ladder_and_same_sixteen() -> None:
    data = results()
    assert a.outcomes(data, [])['decision'] == 'pass'
    for r in data[16:20]: r['retained_late_renewals'] = 0
    assert a.outcomes(data, [])['decision'] == 'pass'
    data[15]['retained_late_renewals'] = 0
    assert a.outcomes(data, [])['decision'] == 'renewal without retention'
    for r in data[:5]: r['productive_source_births'] = 99
    assert a.outcomes(data, [])['decision'] == 'valid failure'
    data = results()
    for r in data[:4]: r['productive_source_births'] = 99
    for r in data[16:20]: r['renewing_descendants'] = 9
    assert not a.outcomes(data, [])['renewal_core']


@pytest.mark.parametrize('field,threshold', list(zip(a.ENDPOINTS, a.THRESHOLDS, strict=True)))
def test_all_endpoint_boundaries(field: str, threshold: int) -> None:
    data = results()
    for r in data[:20]: r[field] = threshold - 1
    assert not a.outcomes(data, [])['full_support']
    assert a.outcomes(data, [])['renewal_core'] == (field == 'retained_late_renewals')


def test_missing_duplicate_failed_controls_and_mechanics() -> None:
    data = results()
    for rows, failures in ((data[:-1], []), (data + [data[0]], []), (data, [{'error': 'bad'}])):
        out = a.outcomes(rows, failures)
        assert out['decision'] == 'unevaluable' and out['run_denominator'] == 30
        assert len(out['hosts']) == 20
    assert a.outcomes(data, [], mechanics=False)['decision'] == 'unevaluable'
    for key in ('native_births', 'productive_source_births', 'renewing_descendants', 'max_source_depth'):
        corrupt = results(); corrupt[-1][key] = 1
        out = a.outcomes(corrupt, [])
        assert not out['inert_controls'] and not out['renewal_core'] and not out['full_support']


def test_input_matrix_protocol_and_environment(tmp_path: Path) -> None:
    assert len(a.MATRIX) == 30 and len(set(a.MATRIX)) == 30
    for arm, count in [('host', 8960), ('inert', 140)]:
        r = w.run_input(tmp_path, tmp_path, 202623000, arm)
        assert sum(r['initial_material']['molecular']) == count
        assert r['route'] == 'recycle' and r['initial_material']['pool'] == [0]*33
        assert r['environment'] == decay_workflow.environment('recycle')
    assert w.protocol_pin()['sha256'] == w.PROTOCOL_SHA256
    assert [p.name[:4] for p in w.PATCHES] == ['0001', '0002', '0003', '0004']


def event(index: int, kind: str, outcome: str, before: str, after: str, changes: str = '', proposal: str = '', tick: int = 0) -> dict[str,str]:
    return dict(zip(d.JOURNAL_COLUMNS,map(str,[tick,index,kind,outcome,before,after,changes,proposal]),strict=True))


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
    r = d.Replay(v1.initial_material(initial,'histogram',0,65),route)
    aggregates: list[dict[str,Any]] = []; buffers: list[dict[str,Any]] = []; journal: list[dict[str,Any]] = []
    for tick,kind in [(t,'CHECKPOINT') for t in range(0,end,100)]+[(end,'END')]:
        if kind == 'END':
            for i,b in list(r.buffers.items()):
                changes = ';'.join(f'{i}:{o}:{byte:02X}:00' for o,byte in enumerate(b) if byte)
                e = event(len(journal)+1,'DECAY','REMOVED',str(i),'',changes,tick=end-1)
                r.step(e); journal.append(e)
        arrays = {**r.arrays,'molecular':d.histogram(r.buffers),'initial':r.initial['total']}
        aggregate = {'tick':tick,'event':kind,**r.nums,'waste_bytes':sum(r.arrays['waste']),'max_residual':0,'molecular_bytes':sum(arrays['molecular']),'free_bytes':sum(arrays['pool']),**{f:v for p,vs in arrays.items() for f,v in zip(v1.fields(p),vs,strict=True)}}
        aggregates.append(aggregate)
        buffers.extend({'tick':tick,'event':kind,'id':i,'full_buffer_hex':b.hex().upper()} for i,b in r.buffers.items())
    write_csv(path/'conservation002.csv',d.COLUMNS,aggregates)
    write_csv(path/'conservation_buffers002.csv',v1.BUFFER_COLUMNS,buffers)
    write_csv(path/'material_events002.csv',d.JOURNAL_COLUMNS,journal)



@pytest.mark.parametrize('end', [1, 2500, 4900, 4901, 5000])
def test_extinction_and_actual_end(tmp_path: Path, end: int) -> None:
    extinction_fixture(tmp_path, end, 'recycle')
    out = a.analyze_run(tmp_path, lineage_workflow.expected_initial('host'), maxl0=65)
    assert all(out[k] == 0 for k in a.ENDPOINTS)
    assert out['end_population'] == 0 and out['end_timestep'] == end
    assert len(out['identity_history']) == 140
    assert not out['end_surviving_descendants']


@pytest.mark.parametrize('kind', ['checkpoint', 'end-identity', 'counter', 'pool-credit', 'future-event', 'native-birth'])
def test_cross_observation_fail_closed(tmp_path: Path, kind: str) -> None:
    extinction_fixture(tmp_path, 1, 'recycle')
    if kind in {'checkpoint', 'end-identity'}:
        p = tmp_path/'conservation_buffers002.csv'
        text = p.read_text()
        if kind == 'checkpoint': text = text.replace('0,CHECKPOINT,0,', '0,CHECKPOINT,999,', 1)
        else: text += '1,END,999,' + ('41' + '00'*64) + '\n'
    elif kind in {'counter', 'pool-credit'}:
        p = tmp_path/'conservation002.csv'
        rows = v1.canonical_rows(p, d.COLUMNS)
        rows[-1]['event_count' if kind == 'counter' else 'pool_41'] = '999'
        write_csv(p, d.COLUMNS, rows)
        text = p.read_text()
    elif kind == 'future-event':
        p = tmp_path/'material_events002.csv'
        text = p.read_text().replace('0,1,DECAY', '1,1,DECAY')
    else:
        p = tmp_path/'lineage_events001.csv'
        text = p.read_text().replace('INIT,0', 'BIRTH,0', 1)
    p.write_text(text)
    with pytest.raises(ValueError): a.analyze_run(tmp_path, lineage_workflow.expected_initial('host'), maxl0=65)


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
    assert len(evidence['freshness_audit']['excluded_files']) == 32
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
    new.write_text('seed,result\n202623007,1\n')
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
    elif kind == 'audit-input': prior.write_text('RANDSEED 202623000\n')
    elif kind == 'remote-url': evidence['remote']['url'] = 'ssh://wrong.invalid/repo.git'
    elif kind == 'remote-ref': evidence['remote']['ref'] = 'refs/heads/other'
    elif kind == 'remote-revision': evidence['remote']['observed_revision'] = 'b'*40
    elif kind == 'remote-bytes': evidence['remote']['stdout_hex'] = ''
    else: evidence['committed_files'][str(tmp_path/'code.py')]['bytes_hex'] = '00'
    with pytest.raises(ValueError): w.verify_launch_evidence(path,evidence,data)


def test_matrix_launch_uses_fresh_audit_before_any_seal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(w,'verify_preparation',lambda p:data)
    (tmp_path/'runs'/'late.conf').write_text('RANDSEED 202623018\n')
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('launch wrote a seal or executed after seed reuse')
    monkeypatch.setattr(w,'seal',forbidden)
    monkeypatch.setattr(v1w,'execute',forbidden)
    with pytest.raises(ValueError,match='prior input/use'): w.run_matrix(path)


def test_audit_exclusion_cannot_hide_another_preparation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    other = tmp_path/'runs'/'other'; other.mkdir()
    config = other/'R-202623000.conf'; config.write_text('held out input\n')
    with pytest.raises(ValueError,match='prior input/use'): w.launch_evidence(path,data)
    with pytest.raises(ValueError,match='exclusion outside'):
        w.unseen_audit(path.parent,authorized_files={*w.authorized_inputs(path,data),config})


def test_preparation_never_executes_and_seals_exact_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert len(list(root.iterdir())) == 32
    assert set(root.iterdir()) == w.authorized_inputs(path, data)
    assert all(not p.stat().st_mode & 0o222 for p in root.iterdir())
    assert not (root/'runs').exists() and not (root/'launch.json').exists()
    with pytest.raises((FileExistsError, ValueError)): w.prepare(build, gate, root)


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
    assert len(receipts) == 30
