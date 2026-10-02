"""H002 frozen selection, source cohorts, thresholds, config and launch adversaries."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any
import pytest

from experiments.stringmol import analyze_perturbation as a, perturbation_workflow as w
from experiments.stringmol import perturbation_panel as p, conservation_workflow as v1w
from experiments.stringmol import analyze_renewal as h, analyze_conservation as v1, analyze_decay as d
from experiments.stringmol.configure_control import HOST, StringmolControlConfig, render_config

FIXTURE = Path(__file__).parent/'fixtures/sm_h002_source_candidates.json'


def frozen_panel() -> list[dict[str, Any]]:
    return p.panel(json.loads(FIXTURE.read_text()))


def test_frozen_panel_provenance_dedup_order() -> None:
    panel = frozen_panel()
    assert len(panel) == 15 and sum(len(g['provenances']) for g in panel) == 20
    assert w.evidence_hash(panel) == '1f7f2cb1b56c68c936d0c7c82a037f43b4535ab7027b58fc54a258ab6ae0b6c9'
    assert [g['sha256'] for g in panel] == sorted(g['sha256'] for g in panel)
    assert sum(g['distance'] == 0 for g in panel) == 1
    for g in panel:
        assert g['canonical_provenance'] == min(g['provenances'], key=lambda r: (r['source_seed'], r['id']))
        assert g['length'] == len(bytes.fromhex(g['sequence_hex']))
    assert p.distance(b'AB') == sum(x != y for x, y in zip(b'AB', HOST.encode())) + 62


def test_selection_distance_birth_then_id_ties() -> None:
    fixture = json.loads(FIXTURE.read_text())
    selected = frozen_panel()[0]['canonical_provenance']
    run = next(r for r in fixture['runs'] if r['seed'] == selected['source_seed'])
    renewal = next(r for r in run['renewals'] if r['id'] == selected['id'])
    edge = next(e for e in run['source_edges'] if e['child'] == selected['id'])
    run['renewals'].append({**renewal, 'id': 99999})
    run['source_edges'].append({**edge, 'child': 99999})
    assert p.panel(fixture) == frozen_panel()
    # An equally distant but earlier-born duplicate takes canonical provenance.
    run['renewals'][-1]['birth_tick'] -= 1
    run['source_edges'][-1]['tick'] -= 1
    out = p.panel(fixture)
    assert any(q['id'] == 99999 for g in out for q in g['provenances'])


@pytest.mark.parametrize('raw', [HOST.encode(), b'AB', b'ABC', b'AAC', b'AAAAAB', b'ABC$DEF%'])
def test_sha256_shuffle_independent_keys(raw: bytes) -> None:
    got = p.shuffle(raw)
    sha = hashlib.sha256(raw).hexdigest().encode()
    nonce = 0
    while True:
        keyed = [(hashlib.sha256(b'SM-H002\0' + sha + b'\0' + nonce.to_bytes(4,'big') + i.to_bytes(4,'big') + bytes([b])).digest(), i, b) for i, b in enumerate(raw)]
        expected = bytes(b for _, _, b in sorted(keyed))
        if expected != raw: break
        nonce += 1
    assert got['nonce'] == nonce and bytes.fromhex(got['sequence_hex']) == expected
    assert Counter(raw) == Counter(expected) and len(raw) == len(expected)
    assert sum(x != y for x, y in zip(raw, expected, strict=True)) >= 2
    assert got['sha256'] == hashlib.sha256(expected).hexdigest()


@pytest.mark.parametrize('raw', [b'', b'AAAA', b'AB\0', b'ab', b'AB!'])
def test_bad_or_unshufflable_sequence(raw: bytes) -> None:
    with pytest.raises(ValueError): p.shuffle(raw)


@pytest.mark.parametrize('rank', range(15))
def test_four_arm_configs_load_order_material_and_species(tmp_path: Path, rank: int) -> None:
    candidate = frozen_panel()[rank]
    entries = [w.run_input(tmp_path, tmp_path, 202624000+rank, arm, candidate) for arm in a.ARMS]
    for entry in entries:
        raw = w.custom_config(entry, candidate, tmp_path)
        p.parse_config(raw, entry['expected_initial'], entry['seed'], tmp_path/'config/ALXII.mtx')
        assert len(entry['expected_initial']) == 140
        assert all(r['label'] == ord('Q') for r in entry['expected_initial'])
        assert entry['initial_material']['pool'] == entry['initial_material']['waste'] == [0]*33
        assert list(entry['initial_cohorts']) == list(map(str, range(140)))
        assert sum(v == 'candidate' for v in entry['initial_cohorts'].values()) == (70 if entry['condition'].endswith('SUPPORT') else 140)
        with pytest.raises(ValueError):
            p.parse_config(raw.replace(' 1 Q', ' 1 R', 1), entry['expected_initial'], entry['seed'], tmp_path/'config/ALXII.mtx')
    for i, j in [(0, 1), (2, 3)]:
        assert entries[i]['initial_material']['total'] == entries[j]['initial_material']['total']
        assert entries[i]['initial_material']['molecular'] == entries[j]['initial_material']['molecular']
    support = entries[2]['expected_initial']
    assert support[70]['species'] == (1 if candidate['distance'] == 0 else 2)
    assert support[69]['sequence_hex'] == candidate['sequence_hex'] and support[70]['sequence_hex'] == HOST.encode().hex().upper()


def test_custom_canonical_byte_parity(tmp_path: Path) -> None:
    r = w.development_input(tmp_path, tmp_path)
    assert w.custom_config(r, w.canonical_candidate(), tmp_path) == render_config(StringmolControlConfig('host-only', 202620999, 0, 0), tmp_path/'config/ALXII.mtx')
    assert w.protocol_pin()['sha256'] == w.PROTOCOL_SHA256


def source_fixture(*, whole: bool = False, role: str = 'active', tick: int = 2500) -> dict[str, Any]:
    # Replay actual material changes, then apply cohorts to verified source edges.
    initial = v1.initial_material([{'id': 0, 'sequence_hex': b'ABCDE'.hex()}, {'id': 1, 'sequence_hex': b'AB'.hex()}], 'histogram', 0, 8)
    replay = h.SourceReplay(initial)
    def cut(source: int, other: int, child: int, offset: int, when: int) -> None:
        seq = h.visible(replay.material.buffers[source])
        after = {other: replay.material.buffers[other], child: seq[offset:] + bytes(8-len(seq[offset:]))}
        if offset: after[source] = seq[:offset] + bytes(8-offset)
        before = [source, other]
        changes: list[str] = []
        for idx in sorted(set(before) | set(after)):
            old = replay.material.buffers[idx] if idx in before else bytes(8)
            new = after.get(idx, bytes(8))
            changes.extend(f'{idx}:{j}:{b:02X}:{n:02X}' for j, (b, n) in enumerate(zip(old, new, strict=True)) if b != n)
        replay.step(dict(tick=str(when), index=str(len(replay.edges)+1), event='CLEAVE', outcome='PLACED', before_ids=';'.join(map(str,sorted(before))), after_ids=';'.join(map(str,sorted(after))), changes=';'.join(changes), proposal=''))
    cut(0, 1, 2, 0 if whole else 1, tick)
    cut(2, 1, 3, 1, tick+1)
    cut(1, 3, 4, 1, tick+2)
    native = []
    for e in replay.edges:
        other = next(i for i in e['participants'] if i != e['source'])
        active, passive = (e['source'], other) if role == 'active' else (other, e['source'])
        native.append({'child_id': str(e['child']), 'timestep': str(e['tick']), 'active_id': str(active), 'passive_id': str(passive)})
    replay.native_roles(native)
    return replay.summary(tick+3)


@pytest.mark.parametrize('role', ['active', 'passive'])
@pytest.mark.parametrize('whole', [False, True])
def test_cohort_source_separate_from_qualifying_depth(role: str, whole: bool) -> None:
    out = a.cohorts(source_fixture(whole=whole, role=role), {0: 'candidate', 1: 'support'})
    assert out['material_source_cohort'] == {'0':'candidate','1':'support','2':'candidate','3':'candidate','4':'support'}
    candidate, support = out['cohorts']['candidate'], out['cohorts']['support']
    assert candidate['whole_parent_transfers'] == int(whole)
    assert candidate['productive_source_births'] == 2-int(whole)
    assert candidate['orphan_source_productive_births'] == int(whole)
    assert candidate['serial_source_births'] == candidate['renewing_descendants'] == int(not whole)
    assert candidate['max_source_depth'] == (0 if whole else 2)
    assert support['max_source_depth'] == support['productive_source_births'] == 1
    assert candidate['partner_roles'] == {f'source_{role}:partner_support': 2}


@pytest.mark.parametrize('kind', ['unknown', 'bad-name', 'conflicting', 'unknown-source', 'missing-child', 'future'])
def test_cohort_integrity_failures(kind: str) -> None:
    summary = source_fixture()
    initial = {0: 'candidate', 1: 'support'}
    if kind == 'unknown': del initial[1]
    elif kind == 'bad-name': initial[1] = 'Q'
    elif kind == 'conflicting': summary['source_edges'][1]['child'] = 2
    elif kind == 'unknown-source': summary['source_edges'][1]['source'] = 999
    elif kind == 'missing-child': summary['source_edges'].pop()
    else: summary['source_edges'][-1]['tick'] = 5000
    with pytest.raises(ValueError): a.cohorts(summary, initial)


@pytest.mark.parametrize('tick,late_births,late_renewals', [(2498,0,0),(2499,1,0),(2500,2,1),(4997,2,1)])
def test_late_boundary(tick: int, late_births: int, late_renewals: int) -> None:
    c = a.cohorts(source_fixture(tick=tick), {0:'candidate',1:'support'})['cohorts']['candidate']
    assert c['late_productive_source_births'] == late_births
    assert c['late_renewing_descendants'] == late_renewals


def test_extinct_cohort_empty_denominator() -> None:
    summary = {'identity_history': [{'id':0,'origin':'initial','source_depth':0,'birth_tick':-1,'death_tick':0}], 'source_edges':[], 'renewals':[], 'end_surviving_descendants':[]}
    out = a.cohorts(summary, {0:'candidate'})
    assert not a.liveness(out['cohorts']['candidate'])
    assert out['cohorts']['candidate']['survival'][0]['death_tick'] == 0
    assert out['cohorts']['support']['productive_source_births'] == 0


def metrics(**updates: int) -> dict[str, Any]:
    return {**a.LIVENESS, **updates}


@pytest.mark.parametrize('key', list(a.LIVENESS))
def test_each_liveness_boundary(key: str) -> None:
    assert a.liveness(metrics())
    assert not a.liveness(metrics(**{key:a.LIVENESS[key]-1}))


@pytest.mark.parametrize('key,margin', [('productive_source_births',100),('serial_source_births',25),('late_productive_source_births',50)])
def test_each_specificity_margin(key: str, margin: int) -> None:
    exact = metrics(productive_source_births=200, serial_source_births=50, late_productive_source_births=100)
    shuffled = dict.fromkeys(a.LIVENESS, 0)
    shuffled[key] = exact[key]-margin
    assert a.specificity(exact, shuffled)['passes']
    shuffled[key] += 1
    assert not a.specificity(exact, shuffled)['passes']


def test_ratio_zero_and_twofold_edges() -> None:
    zero = dict.fromkeys(a.LIVENESS,0)
    assert a.specificity(metrics(),zero)['passes']
    assert not a.specificity(zero,zero)['passes']
    assert a.specificity(metrics(productive_source_births=202),{**zero,'productive_source_births':101})['passes']
    assert not a.specificity(metrics(productive_source_births=201),{**zero,'productive_source_births':101})['passes']


def outcomes_fixture(self_ranks: set[int], support_ranks: set[int]) -> tuple[list[dict[str, Any]],list[dict[str, Any]]]:
    panel = frozen_panel()
    runs = []
    for arm, seed in a.MATRIX:
        passes = seed-202624000 in (self_ranks if arm.endswith('SELF') else support_ranks)
        m = metrics() if arm.startswith('EXACT') or not passes else dict.fromkeys(a.LIVENESS,0)
        runs.append({'condition':arm,'seed':seed,'cohorts':{'candidate':m}})
    return runs,panel


@pytest.mark.parametrize('self_set,support_set,decision', [
    (set(range(12)),set(range(12)),'context-general pass'),
    (set(range(12)),set(range(3,15)),'dual-context screen pass with insufficient overlap'),
    (set(range(11)),set(range(12)),'supported-context-only screen pass'),
    (set(range(12)),set(range(11)),'self-context-only screen pass'),
    (set(range(11)),set(range(11)),'valid failure'),
])
def test_decision_ladder(self_set: set[int], support_set: set[int], decision: str) -> None:
    runs,panel = outcomes_fixture(self_set,support_set)
    out = a.outcomes(runs,[],panel)
    assert out['decision'] == decision and out['run_denominator'] == 60
    assert out['genotype_denominator_per_context'] == 15
    assert len(out['strata']['canonical']) == 1 and len(out['strata']['noncanonical']) == 14
    assert a.outcomes(runs, [{'error':'bad journal'}], panel)['decision'] == 'unevaluable'
    assert a.outcomes(runs[:-1], [], panel)['decision'] == 'unevaluable'
    assert a.outcomes(runs+[runs[0]], [], panel)['decision'] == 'unevaluable'


@pytest.mark.parametrize('context', ['SELF','SUPPORT'])
def test_canonical_positive_control(context: str) -> None:
    runs,panel = outcomes_fixture(set(range(15)),set(range(15)))
    rank = next(p['rank'] for p in panel if p['distance'] == 0)
    run = next(r for r in runs if r['seed'] == 202624000+rank and r['condition'] == 'EXACT_'+context)
    run['cohorts']['candidate']['max_source_depth'] = 1
    assert a.outcomes(runs,[],panel)['decision'] == 'unevaluable'


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
    new.write_text('seed,result\n202624007,1\n')
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
    elif kind == 'audit-input': prior.write_text('RANDSEED 202624000\n')
    elif kind == 'remote-url': evidence['remote']['url'] = 'ssh://wrong.invalid/repo.git'
    elif kind == 'remote-ref': evidence['remote']['ref'] = 'refs/heads/other'
    elif kind == 'remote-revision': evidence['remote']['observed_revision'] = 'b'*40
    elif kind == 'remote-bytes': evidence['remote']['stdout_hex'] = ''
    else: evidence['committed_files'][str(tmp_path/'code.py')]['bytes_hex'] = '00'
    with pytest.raises(ValueError): w.verify_launch_evidence(path,evidence,data)


def test_matrix_launch_uses_fresh_audit_before_any_seal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(w,'verify_preparation',lambda p:data)
    (tmp_path/'runs'/'late.conf').write_text('RANDSEED 202624014\n')
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('launch wrote a seal or executed after seed reuse')
    monkeypatch.setattr(w,'seal',forbidden)
    monkeypatch.setattr(v1w,'execute',forbidden)
    with pytest.raises(ValueError,match='prior input/use'): w.run_matrix(path)


def test_audit_exclusion_cannot_hide_another_preparation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    other = tmp_path/'runs'/'other'; other.mkdir()
    config = other/'R-202624000.conf'; config.write_text('held out input\n')
    with pytest.raises(ValueError,match='prior input/use'): w.launch_evidence(path,data)
    with pytest.raises(ValueError,match='exclusion outside'):
        w.unseen_audit(path.parent,authorized_files={*w.authorized_inputs(path,data),config})


def test_preparation_never_executes_and_seals_exact_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert len(list(root.iterdir())) == 62
    assert set(root.iterdir()) == w.authorized_inputs(path, data)
    assert all(not p.stat().st_mode & 0o222 for p in root.iterdir())
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
    data['runs'] = [w.run_input(tmp_path, path.parent, seed, arm, frozen_panel()[seed-202624000]) for arm, seed in a.MATRIX]
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


def test_source_analysis_pin_rejects_changed_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path/'analysis.json'; path.write_text('{}\n')
    monkeypatch.setattr(p, 'SOURCE_ANALYSIS', path)
    with pytest.raises(ValueError, match='analysis digest'): p.verify_source()


def test_missing_campaign_is_unevaluable(tmp_path: Path) -> None:
    result = a.analyze_campaign(tmp_path/'missing.json')
    assert result['decision'] == 'unevaluable' and result['run_denominator'] == 60


@pytest.mark.parametrize('alteration', ['position','count','settings','order'])
def test_config_parser_rejects_custom_load_mutations(tmp_path: Path, alteration: str) -> None:
    candidate = frozen_panel()[0]
    arm = 'EXACT_SUPPORT'
    expected = p.expected_initial(candidate,arm)
    raw = p.render(candidate,arm,202620999,tmp_path/'ALXII.mtx')
    if alteration == 'position': raw = raw.replace('GRIDPOS 12 15','GRIDPOS 11 15',1)
    elif alteration == 'count': raw = raw.replace(' 1 Q',' 2 Q',1)
    elif alteration == 'settings': raw = raw.replace('MUTATE 0.0002','MUTATE 0.002',1)
    else:
        lines = raw.splitlines()
        idx = next(i for i, line in enumerate(lines) if line.startswith('AGENT '))
        lines[idx:idx+4] = lines[idx+2:idx+4]+lines[idx:idx+2]
        raw = '\n'.join(lines)+'\n'
    with pytest.raises(ValueError): p.parse_config(raw,expected,202620999,tmp_path/'ALXII.mtx')


def counter_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path/w.COUNTER_PATH
    path.parent.mkdir(parents=True)
    raw = w.COUNTER_HEADER + b'\r\n' + w.COUNTER_ROW + b'\r\n'
    path.write_bytes(raw)
    path.with_name('config.json').write_text(json.dumps({'seed':202615008}))
    path.with_name('manifest.json').write_text(json.dumps({'config':{'seed':202615008}}))
    monkeypatch.setattr(w, 'COUNTER_SHA256', hashlib.sha256(raw).hexdigest())
    return path


def test_exact_counter_is_classified_not_excluded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    counter = counter_fixture(tmp_path,monkeypatch)
    evidence = w.launch_evidence(path,data)
    audit = evidence['freshness_audit']
    assert audit['matches'] == [] and len(audit['excluded_files']) == 62
    assert audit['inventory'][w.COUNTER_PATH] == w.record(counter)
    item = audit['nonseed_counter_matches'][0]
    assert item['field'] == 'withdrawals' and item['value'] == 202624012 and item['run_seed'] == 202615008
    w.verify_launch_evidence(path,evidence,data)
    item['value'] = 0
    evidence['freshness_audit_sha256'] = w.evidence_hash(audit)
    with pytest.raises(ValueError, match='counter audit evidence'): w.verify_launch_evidence(path,evidence,data)


@pytest.mark.parametrize('change', ['bytes','new-seed','new-file','header','second-match','other-path'])
def test_counter_classification_cannot_hide_seed_use(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    counter = counter_fixture(tmp_path,monkeypatch)
    raw = counter.read_bytes()
    if change == 'bytes': counter.write_bytes(raw.replace(b'92501',b'92502'))
    elif change == 'new-seed': counter.with_name('config.json').write_text(json.dumps({'seed':202624012}))
    elif change == 'new-file': counter.with_name('other.conf').write_text('RANDSEED 202624012\n')
    elif change == 'header':
        counter.write_bytes(raw.replace(b'withdrawals', b'seed'))
        monkeypatch.setattr(w,'COUNTER_SHA256',hashlib.sha256(counter.read_bytes()).hexdigest())
    elif change == 'second-match':
        counter.write_bytes(raw + w.COUNTER_ROW + b'\r\n')
        monkeypatch.setattr(w,'COUNTER_SHA256',hashlib.sha256(counter.read_bytes()).hexdigest())
    else: counter.with_name('other.csv').write_bytes(raw)
    with pytest.raises(ValueError): w.launch_evidence(path,data)
    assert not (path.parent/'launch.json').exists()


def test_source_worker_uses_unchanged_replay_and_exact_output_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from experiments.stringmol import analyze_decay, renewal_workflow
    expected = [{'id':0}]
    calls: list[Any] = []
    def analyze(directory: Path, initial: list[dict[str, Any]], *, exit_status: int) -> dict[str, Any]:
        calls.append((directory, initial, exit_status))
        return {'end_timestep':5000,'productive_source_births':123}
    monkeypatch.setattr(h,'analyze_run',analyze)
    monkeypatch.setattr(renewal_workflow,'inventory',lambda path: dict.fromkeys(analyze_decay.output_names(5000),{}))
    r = {'directory':str(tmp_path),'expected_initial':expected,'condition':'host','seed':202623000}
    result = p.replay_source_run(r)
    assert result == {'condition':'host','seed':202623000,'end_timestep':5000,'productive_source_births':123}
    assert calls == [(tmp_path,expected,0)]
    monkeypatch.setattr(renewal_workflow,'inventory',lambda path: {})
    with pytest.raises(ValueError,match='source output names'): p.replay_source_run(r)
