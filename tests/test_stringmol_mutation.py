"""SM-M001 frozen sequence endpoints, decisions and fail-closed launch fixtures."""
from __future__ import annotations
from copy import deepcopy
import json
import math
from pathlib import Path
from typing import Any
import pytest
from experiments.stringmol import analyze_mutation as a, mutation_workflow as w
from experiments.stringmol import conservation_workflow as v1w, analyze_renewal as h1
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
    new.write_text('seed,result\n202626007,1\n')
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
    elif kind == 'audit-input': prior.write_text('RANDSEED 202626000\n')
    elif kind == 'remote-url': evidence['remote']['url'] = 'ssh://wrong.invalid/repo.git'
    elif kind == 'remote-ref': evidence['remote']['ref'] = 'refs/heads/other'
    elif kind == 'remote-revision': evidence['remote']['observed_revision'] = 'b'*40
    elif kind == 'remote-bytes': evidence['remote']['stdout_hex'] = ''
    else: evidence['committed_files'][str(tmp_path/'code.py')]['bytes_hex'] = '00'
    with pytest.raises(ValueError): w.verify_launch_evidence(path,evidence,data)


def test_matrix_launch_uses_fresh_audit_before_any_seal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(w,'verify_preparation',lambda p:data)
    (tmp_path/'runs'/'late.conf').write_text('RANDSEED 202626019\n')
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError('launch wrote a seal or executed after seed reuse')
    monkeypatch.setattr(w,'seal',forbidden)
    monkeypatch.setattr(v1w,'execute',forbidden)
    with pytest.raises(ValueError,match='prior input/use'): w.run_matrix(path)


def test_audit_exclusion_cannot_hide_another_preparation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path,data,_ = launch_fixture(tmp_path,monkeypatch)
    other = tmp_path/'runs'/'other'; other.mkdir()
    config = other/'R-202626000.conf'; config.write_text('held out input\n')
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
    assert len(list(root.iterdir())) == 42
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
    assert len(receipts) == 40




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
    prior.write_text('202626999 202626020 1202626000 0.202626000 2026260000')
    assert w.unseen_audit(folder/'prepared')['matches'] == []
    directory = folder/'run-s202626019'; directory.mkdir()
    with pytest.raises(ValueError, match='prior input/use'): w.unseen_audit(folder/'prepared')
    directory.rmdir()
    (folder/'alias').symlink_to(prior)
    with pytest.raises(ValueError, match='symlink'): w.unseen_audit(folder/'prepared')



def empty() -> dict[str, Any]:
    return {**dict.fromkeys(a.COUNTS, 0), **a.sequence_endpoints({'source_edges': [], 'renewals': []})}


def fixture(native: int = 16, zero: int = 16, divergence: int = 16) -> list[dict[str, Any]]:
    rows = []
    for arm, seed in a.MATRIX:
        row = empty()
        i = seed-a.SEEDS[0]
        if i < (native if arm == 'NATIVE' else zero): row.update(zip(h1.ENDPOINTS, h1.THRESHOLDS, strict=True))
        if arm == 'NATIVE' and i < divergence:
            row.update(productive_unique_sequences=2, productive_noncanonical_fraction=0.5)
        rows.append({'condition': arm, 'seed': seed, **row})
    return rows


@pytest.mark.parametrize('native,zero,divergence,decision', [
    (16,16,16,'both viable, divergence detected'), (16,16,15,'both viable, divergence not detected'),
    (16,15,20,'native only viable'), (15,16,20,'ZERO only viable'), (15,15,20,'neither viable')])
def test_decisions(native: int, zero: int, divergence: int, decision: str) -> None:
    out = a.outcomes(fixture(native,zero,divergence), [])
    assert out['decision'] == decision
    assert out['arms']['NATIVE']['continuity_count'] == native
    assert out['arms']['ZERO']['continuity_count'] == zero
    assert out['birth_boundary_factorial_eligible'] == (native >= 16 and zero >= 16)
    assert out['descriptive_coin_tail'] == 0.005908966064453125
    assert len(out['pairs']) == out['paired_denominator'] == 20


def test_conjunction_and_discordance() -> None:
    rows = fixture(16,16,16)
    # Each direction has 16 wins, but the intersection has 15.
    rows[0]['productive_noncanonical_fraction'] = 0
    rows[32]['productive_noncanonical_fraction'] = 0.5
    out = a.outcomes(rows, [])
    assert out['divergence_pairs'] == 15 and not out['realized_divergence']
    rows[1]['retained_late_renewals'] = 4
    out = a.outcomes(rows, [])
    assert out['arms']['ZERO']['core_count'] == 16
    assert out['arms']['ZERO']['continuity_count'] == 15
    assert out['discordant_pairs'] == [a.SEEDS[0]]
    assert out['paired_summary']['retention_median']['median_difference'] is None
    for bad in (rows[:-1], rows+[rows[0]], [{**rows[0], 'seed': 0}, *rows[1:]]):
        assert a.outcomes(bad, [])['decision'] == 'unevaluable'
    assert a.outcomes(rows, [{'error': 'bad'}])['decision'] == 'unevaluable'
    assert a.outcomes(rows, [], mechanics=False)['decision'] == 'unevaluable'


def test_complete_sequences_abundance_lengths_and_empty() -> None:
    host = HOST.encode()
    m = a.sequence_metrics([host, host, host+b'B', host[:-1]], 'productive')
    assert m['productive_exact_births'] == 2 and m['productive_noncanonical_fraction'] == 0.5
    assert m['productive_unique_sequences'] == m['productive_hill_q0'] == 3
    assert m['productive_hill_q1'] == pytest.approx(math.sqrt(8))
    assert m['productive_length_distribution'] == [63,64,64,65]
    assert m['productive_unique_lengths'] == 3
    e = empty()
    assert all(e['productive_'+k] == 0 for k in a.SEQUENCE_SCALARS)
    assert all(e['renewing_'+k] == 0 for k in a.SEQUENCE_SCALARS)
    assert e['retention_minimum'] is e['retention_median'] is None
    assert e['retention_distribution'] == e['productive_length_distribution'] == []


def test_filter_and_first_source_retention() -> None:
    edges = [{'child': i, 'productive': i != 4, 'whole_transfer': i == 3,
              'orphan_source': i == 2, 'birth_buffer_hex': (HOST.encode()+b'\0HIDDEN').hex()} for i in range(5)]
    renewals = [{'id': 0, 'retention': 1.0}, {'id': 1, 'retention': 0.5}]
    m = a.sequence_endpoints({'source_edges': edges, 'renewals': renewals})
    assert m['productive_births'] == m['productive_exact_births'] == 2
    assert m['renewing_unique_sequences'] == m['renewing_hill_q1'] == 1
    assert m['retention_median'] == 0.75 and m['retention_minimum'] == 0.5
    assert m['retention_exact_fraction'] == 0.5
    assert all(len(v) == 1 for v in m['excluded_sequence_births'].values())
    with pytest.raises(ValueError): a.sequence_endpoints({'source_edges': edges, 'renewals': [{'id': 2}]})


@pytest.mark.parametrize('seed', a.SEEDS)
def test_strict_configs(tmp_path: Path, seed: int) -> None:
    native, zero = [w.run_input(tmp_path,tmp_path,seed,arm) for arm in a.ARMS]
    assert native['initial_material'] == zero['initial_material']
    assert native['expected_initial'] == zero['expected_initial']
    n, z = [w.custom_config(r,tmp_path) for r in (native,zero)]
    assert n.replace('MUTATE 0.0002\n','MUTATE 0\n') == z
    for r,raw in [(native,n),(zero,z)]:
        w.parse_config(raw,r,tmp_path)
        for bad in [raw+'MUTATE 0\n', raw.replace('DECAY 0.0005','DECAY 0'), raw.replace('GRIDPOS 12 15','GRIDPOS 13 15')]:
            with pytest.raises(ValueError): w.parse_config(bad,r,tmp_path)
    with pytest.raises(ValueError): w.parse_config(n,zero,tmp_path)
    with pytest.raises(ValueError): w.parse_config(z,native,tmp_path)


def test_protocol_and_rng_static(tmp_path: Path) -> None:
    assert w.protocol_pin()['sha256'] == w.PROTOCOL_SHA256
    # Build synthetic source from pinned patch, then reject a guarded draw.
    patch = w.PATCHES[2].read_text()
    start = patch.index('+void SpatialConservation::copy(')
    end = patch.index('\n+}\n', start)+len('\n+}')
    copy = '\n'.join(line[1:] for line in patch[start:end].splitlines())+'\n'
    (tmp_path/'src').mkdir()
    (tmp_path/'src/sm_spatial.cpp').write_text(copy)
    loader = Path('experiments/stringmol/vendor/stringmol/src/stringPM.cpp')
    (tmp_path/'src/stringPM.cpp').write_bytes(loader.read_bytes())
    assert w.rng_semantics(tmp_path)['baseline_draw_preserved']
    (tmp_path/'src/sm_spatial.cpp').write_text(copy.replace('float draw = RandomBetween0And1();','float draw = domut ? RandomBetween0And1() : 0;'))
    with pytest.raises(ValueError): w.rng_semantics(tmp_path)


def test_missing_campaign(tmp_path: Path) -> None:
    assert a.analyze_campaign(tmp_path/'missing')['decision'] == 'unevaluable'


@pytest.mark.parametrize('endpoint,threshold', list(zip(h1.ENDPOINTS, h1.THRESHOLDS, strict=True)))
def test_every_renewal_boundary(endpoint: str, threshold: int) -> None:
    m = dict(zip(h1.ENDPOINTS, h1.THRESHOLDS, strict=True))
    assert a.renewal(m)['continuity']
    m[endpoint] = threshold-1
    result = a.renewal(m)
    assert not result['continuity']
    assert result['core'] == (endpoint == 'retained_late_renewals')


def test_signed_differences_and_ties() -> None:
    rows = fixture(0,0,0)
    rows[0]['productive_unique_sequences'] = 1
    rows[3]['productive_unique_sequences'] = 2
    out = a.outcomes(rows, [])
    assert out['paired_summary']['productive_unique_sequences']['direction_counts'] == {'native_greater': 1, 'zero_greater': 1, 'tie': 18}
    assert out['paired_summary']['productive_unique_sequences']['median_difference'] == 0
    assert not out['realized_divergence']


def test_native_matrix_filename_bound(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from experiments.stringmol import lineage_workflow
    monkeypatch.setattr(lineage_workflow, 'verify_build', lambda p: {'builds': {'observer': {'source': '/tmp/l/o'}}})
    assert len(w.matrix_path_gate(Path('/tmp/m'),tmp_path/'build')) == 5
    with pytest.raises(ValueError, match='fewer than 80 bytes'):
        w.matrix_path_gate(tmp_path/('too-long-'*20),tmp_path/'build')
    monkeypatch.setattr(lineage_workflow, 'verify_build', lambda p: {'builds': {'observer': {'source': '/tmp/'+ 'a'*80}}})
    with pytest.raises(ValueError, match='fewer than 80 bytes'):
        w.matrix_path_gate(Path('/tmp/m'),tmp_path/'build')


@pytest.mark.parametrize('length,allowed', [(79,True),(80,False)])
def test_matrix_filename_exact_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, length: int, allowed: bool) -> None:
    from experiments.stringmol import lineage_workflow
    source = '/tmp/'+'x'*(length-len('/tmp//config/ALXII.mtx'))
    assert len(source+'/config/ALXII.mtx') == length
    monkeypatch.setattr(lineage_workflow, 'verify_build', lambda p: {'builds': {'observer': {'source': source}}})
    if allowed: w.matrix_path_gate(Path('/tmp/m'),tmp_path/'build')
    else:
        with pytest.raises(ValueError, match='fewer than 80 bytes'): w.matrix_path_gate(Path('/tmp/m'),tmp_path/'build')
