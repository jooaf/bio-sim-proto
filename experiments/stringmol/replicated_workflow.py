"""SM-H003 immutable 90-run preparation; H002 mechanics and replay reused unchanged.

Build/gates use development seeds only. Prepare cannot launch. Run requires a
clean committed implementation, direct origin/main observation and a fresh audit.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from experiments.stringmol import perturbation_workflow as h2, perturbation_panel as panel_tools
from experiments.stringmol import decay_workflow as decay, conservation_workflow as c
from experiments.stringmol import analyze_replicated as analyzer
from experiments.stringmol.configure_control import StringmolControlConfig, render_config
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.conservation_workflow import command as command, source_state as source_state, record as record, inventory as inventory, seal as seal, read as read, ENV, ROOT, HERE

PATCHES = h2.PATCHES
IMPLEMENTATION = [*h2.IMPLEMENTATION, HERE/'replicated_workflow.py', HERE/'analyze_replicated.py', ROOT/'tests/test_stringmol_replicated.py']
REMOTE = 'origin'
REMOTE_REF = 'refs/heads/main'
PROTOCOL_PATH = 'reports/sm_h003_replicated_supported_sequence_order_preregistration.md'
PROTOCOL_REVISION = '10ae4553cd6a23781e45388c103ff17d4a9a70e9'
PROTOCOL_SHA256 = 'af2ab0bbdc451e1a0a27c4b9e98ab71da86684cf00614e2b4fa83766983ea693'
PANEL_SHA256 = '1f7f2cb1b56c68c936d0c7c82a037f43b4535ab7027b58fc54a258ab6ae0b6c9'
SOURCE_FIXTURE = ROOT/'tests/fixtures/sm_h002_source_candidates.json'
FIXTURE_SHA256 = '463ec5dbcf090a001d80e44fc6cfaf38942d52e284843dab1b4b24834abeba8b'
H002_PREPARATION = ROOT/'runs/sm_h002_work/prepared/preparation.json'
H002_ANALYSIS = ROOT/'runs/sm_h002_work/analysis/analysis.json'
H002_PREPARATION_SHA256 = '47fdb0f9d12910efcf5433d1e7ba1d7b368860b4d93e93837acff61e5efe1965'
H002_ANALYSIS_SHA256 = '344f0f12470c5390ed19efd4c7ae4241f5c17c27c1c3f4b98d07cf826de9d8c9'

evidence_hash = h2.evidence_hash
custom_config = h2.custom_config
serialization = h2.serialization


def protocol_pin() -> dict[str, Any]:
    raw = command(['git', 'show', f'{PROTOCOL_REVISION}:{PROTOCOL_PATH}'], ROOT)
    require(c.digest(raw) == PROTOCOL_SHA256 and (ROOT/PROTOCOL_PATH).read_bytes() == raw, 'committed SM-H003 protocol mismatch')
    for patch in PATCHES:
        require(command(['git', 'show', f'{PROTOCOL_REVISION}:{patch.relative_to(ROOT)}'], ROOT) == patch.read_bytes(), 'inherited patch differs from H003 commitment')
    return {'path': PROTOCOL_PATH, 'revision': PROTOCOL_REVISION, 'sha256': PROTOCOL_SHA256, 'bytes_hex': raw.hex(), 'inherited': h2.protocol_pin()}


def verify_panel(panel: list[dict[str, Any]]) -> None:
    fixture = SOURCE_FIXTURE
    require(record(fixture)['sha256'] == FIXTURE_SHA256, 'committed source fixture hash')
    require(panel == panel_tools.panel(read(fixture)) and evidence_hash(panel) == PANEL_SHA256, 'frozen panel/shuffle mismatch')
    require(sum(p['sha256'] == analyzer.CANONICAL_SHA256 for p in panel) == 1, 'canonical identity')


def source_evidence(source_package: dict[str, Any]) -> dict[str, Any]:
    # Historical outcomes never select, rank or remove candidates.
    require(record(H002_PREPARATION)['sha256'] == H002_PREPARATION_SHA256 and record(H002_ANALYSIS)['sha256'] == H002_ANALYSIS_SHA256, 'H002 source-integrity records')
    historical = read(H002_PREPARATION)
    verify_panel(source_package['panel'])
    require(source_package == panel_tools.verify_source() and historical['panel'] == source_package['panel'], 'H001/H002 source panel mismatch')
    return {'h001': source_package, 'h002_preparation': record(H002_PREPARATION), 'h002_analysis': record(H002_ANALYSIS)}


def build(root: Path, upstream: Path, lineage_build: Path) -> Path:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    inputs = {str(p): record(p) for p in IMPLEMENTATION}
    # Require the caller's newly built lineage package; conservation and decay
    # are freshly built by H002, including their upstream suites.
    inherited = h2.build(root/'inherited', upstream, lineage_build)
    checked = h2.verify_build(inherited)
    require(inputs == {str(p): record(p) for p in IMPLEMENTATION}, 'implementation changed during build')
    seal(root/'build.json', {'protocol_pin': protocol_pin(), 'implementation': inputs,
                           'inherited': str(inherited), 'inherited_record': record(inherited), 'builds': checked['builds']})
    return root/'build.json'


def verify_build(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = read(path)
    require(data['protocol_pin'] == protocol_pin() and data['implementation'] == {str(p): record(p) for p in IMPLEMENTATION}, 'H003 build inputs changed')
    inherited = Path(data['inherited'])
    require(record(inherited) == data['inherited_record'] and h2.verify_build(inherited)['builds'] == data['builds'], 'H003 inherited build')
    return data


def validation_commands() -> dict[str, list[str]]:
    commands = h2.validation_commands()
    commands['pytest'].append('tests/test_stringmol_replicated.py')
    commands['mypy'].extend([str(HERE/'replicated_workflow.py'), str(HERE/'analyze_replicated.py'), 'tests/test_stringmol_replicated.py'])
    return commands


def validation(root: Path) -> dict[str, Any]:
    checks = {}
    for name, args in validation_commands().items():
        proc = subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True)
        log = root/f'{name}.txt'
        log.write_bytes(proc.stdout + proc.stderr)
        require(proc.returncode == 0, f'H003 {name} failed: {log}')
        checks[name] = {'command': args, 'exit_status': 0, 'log': record(log)}
    return checks


def run_input(source: Path, root: Path, seed: int, condition: str, candidate: dict[str, Any]) -> dict[str, Any]:
    require(condition in analyzer.ARMS and seed in analyzer.SEEDS and candidate['rank'] == (seed-202625000)//3, 'H003 arm/seed/rank')
    return {**h2.run_input(source, root, seed, condition, candidate), 'replicate': (seed-202625000)%3,
            'environment': {**decay.environment('recycle'), 'NUMBA_NUM_THREADS': '1'}}


def development_input(source: Path, root: Path) -> dict[str, Any]:
    return {**h2.run_input(source, root, 202620999, 'EXACT_SUPPORT', h2.canonical_candidate()),
            'environment': {**decay.environment('recycle'), 'NUMBA_NUM_THREADS': '1'}}


def gates(build_path: Path, root: Path) -> Path:
    data = verify_build(build_path)
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    inherited = h2.gates(Path(data['inherited']), root/'inherited')
    checks = validation(root)
    source_package = read(inherited)['source_package']
    evidence = source_evidence(source_package)
    source = Path(data['builds']['observer']['source'])
    r = development_input(source, root)
    config = Path(r['config'])
    config.write_text(custom_config(r, h2.canonical_candidate(), source))
    config.chmod(0o444)
    require(config.read_text() == render_config(StringmolControlConfig('host-only', r['seed'], 0, 0), source/'config/ALXII.mtx'), 'canonical supported config byte parity')
    execution = c.execute(Path(r['command'][0]), config, Path(r['directory']), r['environment'])
    c.parity(read(inherited)['new_run'], execution)
    summary = analyzer.analyze_run(Path(r['directory']), r['expected_initial'], {int(i): v for i, v in r['initial_cohorts'].items()})
    seal(root/'gates.json', {'passed': True, 'build_record': record(build_path), 'inherited': str(inherited),
                           'inherited_record': record(inherited), 'validation': checks, 'source_package': source_package,
                           'source_evidence': evidence, 'development_input': r, 'config': record(config),
                           'execution': execution, 'summary': summary, 'canonical_diagnostic': analyzer.control(summary)})
    verify_gate(root/'gates.json', build_path)
    return root/'gates.json'


def verify_gate(path: Path, build_path: Path) -> None:
    data = verify_build(build_path)
    gate = read(path)
    inherited = Path(gate['inherited'])
    require(gate['passed'] is True and gate['build_record'] == record(build_path) and gate['inherited_record'] == record(inherited), 'H003 gate provenance')
    h2.verify_gate(inherited, Path(data['inherited']))
    require(gate['source_package'] == read(inherited)['source_package'] and gate['source_evidence'] == source_evidence(gate['source_package']), 'source evidence changed')
    for name, args in validation_commands().items():
        require(gate['validation'][name] == {'command': args, 'exit_status': 0, 'log': record(path.parent/f'{name}.txt')}, 'H003 validation changed')
    source = Path(data['builds']['observer']['source'])
    r = development_input(source, path.parent)
    config = Path(r['config'])
    require(gate['development_input'] == r and gate['config'] == record(config) and config.read_text() == custom_config(r, h2.canonical_candidate(), source), 'development config changed')
    require(gate['execution']['exit_status'] == 0 and gate['execution']['files'] == inventory(Path(r['directory'])), 'development execution changed')
    c.parity(read(inherited)['new_run'], gate['execution'])
    summary = analyzer.analyze_run(Path(r['directory']), r['expected_initial'], {int(i): v for i, v in r['initial_cohorts'].items()})
    require(summary == gate['summary'] and gate['canonical_diagnostic'] == analyzer.control(summary), 'development replay changed')


def authorized_inputs(path: Path, data: dict[str,Any]) -> set[Path]:
    expected = {path.parent/f'{arm}-{seed}.conf' for arm, seed in analyzer.MATRIX}
    require({Path(r['config']) for r in data['runs']} == expected,'authorized preparation config paths')
    return expected | {path,path.with_name('preparation.sha256.json')}


def unseen_audit(root: Path, *, authorized_files: set[Path] | None = None) -> dict[str,Any]:
    """Audit all historical run/sweep inputs; exempt only exact authorized inputs.

    No directory subtree is exempt: an execution artifact inside the authorized
    preparation is still evidence of prior use. The caller verifies the complete
    preparation before passing its 92 immutable input paths.
    """
    started = datetime.now(timezone.utc).isoformat()
    allowed = authorized_files or set()
    require(all(p.parent == root for p in allowed),'audit exclusion outside authorized preparation')
    excluded = {str(p):record(p) for p in sorted(allowed)}
    matches = []
    classified: list[dict[str, Any]] = []
    checked: dict[str,Any] = {}
    directories = []
    # Literal prefix permits efficient scanning of large historical CSVs. The
    # preceding-byte check rejects decimal substrings, not seed-bearing names.
    pattern = re.compile(rb'2026250(?:[0-3][0-9]|4[0-4])(?![0-9])')
    def contains_seed(raw: bytes) -> bool:
        return any(m.start() == 0 or raw[m.start()-1] not in b'0123456789.' for m in pattern.finditer(raw))
    for folder in (ROOT/'runs',ROOT/'sweeps'):
        for p in sorted(folder.rglob('*')):
            if p in allowed: continue
            require(not p.is_symlink(),'symlink in freshness audit: '+str(p))
            if contains_seed(p.name.encode()): matches.append(str(p))
            if p.is_dir(): directories.append(str(p.relative_to(ROOT))); continue
            if not p.is_file() or p.suffix not in {'.json','.conf','.csv','.txt','.jsonl','.yaml','.toml'}: continue
            if '.git' in p.parts or 'vendor' in p.parts: continue
            raw = p.read_bytes()
            checked[str(p.relative_to(ROOT))] = {'size':len(raw),'sha256':c.digest(raw)}
            found = [m for m in pattern.finditer(raw) if m.start() == 0 or raw[m.start()-1] not in b'0123456789.']
            if found:
                matches.append(str(p))
    require(not matches, 'unseen seed prior input/use: '+str(matches))
    return {'scope':['runs','sweeps'],'authorized_preparation':str(root),'excluded_files':excluded,'nonseed_counter_matches':classified,'checked_files':len(checked),'inventory':checked,'directories':directories,'matches':matches,'seeds':analyzer.SEEDS, 'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat()}


def verify_audit(audit: dict[str,Any], path: Path, data: dict[str,Any], *, preparation: bool = False) -> None:
    require(audit['scope'] == ['runs','sweeps'] and audit['seeds'] == analyzer.SEEDS and audit['matches'] == [],'freshness audit scope/results')
    require(audit['authorized_preparation'] == str(path.parent) and audit['excluded_files'] == ({} if preparation else {str(p):record(p) for p in sorted(authorized_inputs(path,data))}),'freshness audit exclusions')
    require(audit['checked_files'] == len(audit['inventory']),'freshness audit inventory count')
    require(audit['nonseed_counter_matches'] == [], 'no counter exemptions for H003')
    require(datetime.fromisoformat(audit['started_at']) <= datetime.fromisoformat(audit['completed_at']),'freshness audit timestamps')
    for name,expected in audit['inventory'].items():
        p = ROOT/name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and Path(name).parts[0] in audit['scope'],'audit inventory path')
        require(p not in authorized_inputs(path,data) and record(p) == expected,'freshness audit historical input changed')


def remote_target() -> dict[str,str]:
    urls = command(['git','remote','get-url','--all',REMOTE],ROOT).decode().splitlines()
    require(len(urls) == 1 and bool(urls[0]),'origin must have exactly one remote URL')
    return {'remote':REMOTE,'url':urls[0],'ref':REMOTE_REF}


def observe_remote(target: dict[str,str], commit: str) -> dict[str,Any]:
    require(target == remote_target(),'intended origin/main target changed')
    args = ['git','ls-remote','--exit-code','--refs',target['url'],REMOTE_REF]
    raw = command(args,ROOT)  # Direct server observation; never a tracking ref.
    require(re.fullmatch(rb'[0-9a-f]{40}\trefs/heads/main\n',raw) is not None,'missing/ambiguous origin/main observation')
    observed = raw.decode().split('\t')[0]
    require(observed == commit,'HEAD is not the directly observed origin/main revision')
    return {**target,'observed_revision':observed,'command':args,'environment':ENV,'stdout_hex':raw.hex(),'stdout_sha256':c.digest(raw),'observed_at':datetime.now(timezone.utc).isoformat()}


def prepare(build_path: Path, gate_path: Path, root: Path) -> Path:
    data = verify_build(build_path); verify_gate(gate_path,build_path)
    root = root.resolve()
    audit = unseen_audit(root)
    root.mkdir(parents=True,exist_ok=False)
    source = Path(data['builds']['observer']['source'])
    panel = read(gate_path)['source_package']['panel']
    require(not (root/'runs').exists() and not (root/'campaign.json').exists(),'preparation must not contain execution')
    verify_panel(panel)
    entries = []
    for arm, seed in analyzer.MATRIX:
        candidate = panel[(seed - 202625000)//3]
        r = run_input(source,root,seed,arm,candidate); config = Path(r['config'])
        config.write_text(custom_config(r,candidate,source)); config.chmod(0o444)
        entries.append({**r,**record(config),'bytes_hex':config.read_bytes().hex()})
    path = root/'preparation.json'
    seal(path,{'protocol':'SM-H003','panel':panel,'source_package':read(gate_path)['source_package'],'protocol_pin':protocol_pin(),'workers':6,'status':'prepared-only; commit and push required before launch','build_manifest':str(build_path),'build_record':record(build_path),'build':data,'gates':str(gate_path),'gate_record':record(gate_path),'implementation':{str(p):record(p) for p in IMPLEMENTATION},'schema':serialization(),'repository_state':source_state(ROOT),'launch_target':remote_target(),'unseen_audit':audit,'runs':entries})
    seal(root/'preparation.sha256.json',record(path))
    verify_preparation(path)
    return path


def verify_preparation(path: Path) -> dict[str,Any]:
    require(not path.is_symlink() and not path.stat().st_mode & 0o222 and record(path) == read(path.with_name('preparation.sha256.json')),'preparation seal')
    data: dict[str,Any] = read(path)
    require(path.read_bytes() == (json.dumps(data, indent=2, sort_keys=True) + '\n').encode('ascii'), 'noncanonical preparation serialization')
    require(not path.with_name('preparation.sha256.json').is_symlink() and not path.with_name('preparation.sha256.json').stat().st_mode & 0o222, 'mutable preparation digest')
    expected_names = {p.name for p in authorized_inputs(path, data)}
    allowed_names = expected_names | {'runs', 'launch.json', 'campaign.json', 'campaign-results.json'}
    require(expected_names <= {p.name for p in path.parent.iterdir()} <= allowed_names, 'preparation filename set')
    audit = data['unseen_audit']
    require(audit['scope'] == ['runs', 'sweeps'] and audit['seeds'] == analyzer.SEEDS and not audit['matches'] and not audit['excluded_files'], 'preparation seed audit')
    verify_audit(audit, path, data, preparation=True)
    require(data['protocol'] == 'SM-H003' and data['protocol_pin'] == protocol_pin() and data['workers'] == 6,'prepared protocol')
    require(data['implementation'] == {str(p):record(p) for p in IMPLEMENTATION},'prepared implementation')
    require(data['schema'] == serialization(),'schema mismatch')
    require(data['launch_target'] == remote_target(),'prepared origin/main target changed')
    bp,gp = Path(data['build_manifest']),Path(data['gates'])
    require(record(bp) == data['build_record'] and verify_build(bp) == data['build'] and record(gp) == data['gate_record'],'prepared provenance')
    verify_gate(gp,bp)
    require(data['source_package'] == read(gp)['source_package'] and data['panel'] == data['source_package']['panel'], 'sealed source/panel mismatch')
    verify_panel(data['panel'])
    require([(r['condition'],r['seed']) for r in data['runs']] == analyzer.MATRIX,'matrix mismatch')
    source = Path(data['build']['builds']['observer']['source'])
    for r in data['runs']:
        candidate = data['panel'][(r['seed'] - 202625000)//3]
        config = Path(r['config']); raw = custom_config(r,candidate,source).encode()
        require(not config.is_symlink() and not config.stat().st_mode & 0o222 and config.read_bytes() == raw,'read-only input changed')
        if candidate['sha256'] == analyzer.CANONICAL_SHA256 and r['condition'] == 'EXACT_SUPPORT':
            require(raw.decode() == render_config(StringmolControlConfig('host-only', r['seed'], 0, 0), source/'config/ALXII.mtx'), 'canonical exact config parity')
        require(r == {**run_input(source,path.parent,r['seed'],r['condition'],candidate),**record(config),'bytes_hex':raw.hex()},'input mismatch')
    for offset in range(0,90,2):
        block = data['runs'][offset:offset+2]
        for exact, shuffled in ((block[0],block[1]),):
            for key in ('molecular','pool','total','waste'):
                require(exact['initial_material'][key] == shuffled['initial_material'][key], 'paired initial per-symbol material inequality')
            require(exact['initial_cohorts'] == shuffled['initial_cohorts'], 'paired cohort ranges')
    return data


def launch_evidence(path: Path, data: dict[str,Any]) -> dict[str,Any]:
    require(not command(['git','status','--porcelain'],ROOT).strip(),'commit implementation before launch')
    require(not any((path.parent/n).exists() or (path.parent/n).is_symlink() for n in ('runs','campaign.json','launch.json','campaign-results.json')),'no resume/selective retry')
    commit = command(['git','rev-parse','HEAD'],ROOT).decode().strip()
    require(re.fullmatch('[0-9a-f]{40}',commit) is not None,'invalid HEAD revision')
    committed = {}
    for p in [*IMPLEMENTATION,*PATCHES,ROOT/PROTOCOL_PATH]:
        raw = command(['git','show',commit+':'+str(p.relative_to(ROOT))],ROOT)
        require(raw == p.read_bytes(),'uncommitted input')
        committed[str(p)] = {**record(p),'bytes_hex':raw.hex()}
    remote = observe_remote(data['launch_target'],commit)
    # Last substantive pre-seal action: repeat the audit even if preparation's
    # audit passed. Exempt only this verified manifest, digest, and 90 configs.
    audit = unseen_audit(path.parent,authorized_files=authorized_inputs(path,data))
    return {'input_manifest':record(path),'commit':commit,'remote':remote,'committed_files':committed,'freshness_audit':audit,'freshness_audit_sha256':evidence_hash(audit)}


def verify_launch(path: Path) -> None:
    launch_path = path.parent/'launch.json'
    launch = read(launch_path); data = read(path)
    require(not launch_path.is_symlink() and not launch_path.stat().st_mode & 0o222 and launch['input_manifest'] == record(path),'launch input seal')
    verify_launch_evidence(path,launch,data)


def verify_launch_evidence(path: Path, launch: dict[str,Any], data: dict[str,Any]) -> None:
    require(launch['input_manifest'] == record(path),'launch input seal')
    target = data['launch_target']; remote = launch['remote']; commit = launch['commit']
    require(target == {'remote':REMOTE,'url':target['url'],'ref':REMOTE_REF},'launch intended remote/ref')
    require({k:remote[k] for k in target} == target and remote['observed_revision'] == commit,'launch remote target/revision')
    raw = bytes.fromhex(remote['stdout_hex'])
    require(re.fullmatch('[0-9a-f]{40}',commit) is not None and raw == f'{commit}\t{REMOTE_REF}\n'.encode() and remote['stdout_sha256'] == c.digest(raw),'launch remote observation bytes')
    require(remote['command'] == ['git','ls-remote','--exit-code','--refs',target['url'],REMOTE_REF] and remote['environment'] == ENV,'launch remote observation command')
    files = [*IMPLEMENTATION,*PATCHES,ROOT/PROTOCOL_PATH]
    require(launch['committed_files'] == {str(p):{**record(p),'bytes_hex':p.read_bytes().hex()} for p in files},'launch committed file hashes/bytes')
    for p in files:
        require(command(['git','show',commit+':'+str(p.relative_to(ROOT))],ROOT) == p.read_bytes(),'launch committed bytes')
    audit = launch['freshness_audit']
    require(launch['freshness_audit_sha256'] == evidence_hash(audit),'launch freshness evidence hash')
    require(datetime.fromisoformat(remote['observed_at']) <= datetime.fromisoformat(audit['started_at']),'launch audit must follow remote observation')
    verify_audit(audit,path,data)


def run_matrix(path: Path) -> None:
    data = verify_preparation(path)
    # No launch seal is written until committed bytes, direct origin/main
    # observation and a fresh held-out audit all pass. Preparation never calls it.
    evidence = launch_evidence(path,data)
    seal(path.parent/'launch.json',evidence)
    verify_launch(path)
    seal(path.parent/'campaign.json',{'input_manifest':record(path),'workers':6,'launch_record':record(path.parent/'launch.json')})
    def run(r: dict[str,Any]) -> dict[str,Any]:
        directory = Path(r['directory'])
        result = c.execute(Path(r['command'][0]),Path(r['config']),directory,r['environment'])
        result.update(input_manifest=record(path),condition=r['condition'],seed=r['seed'])
        seal(directory.with_suffix('.inventory.json'),result)
        return result
    with ThreadPoolExecutor(max_workers=6) as pool: results = list(pool.map(run,data['runs']))
    seal(path.parent/'campaign-results.json',results)
    verify_preparation(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'gates', 'prepare', 'run'))
    for name in ('root', 'build', 'gates', 'manifest', 'lineage-build'):
        parser.add_argument('--'+name, type=Path)
    parser.add_argument('--upstream', type=Path, default=HERE/'vendor/stringmol')
    args = parser.parse_args()
    if args.action == 'build' and args.root and args.lineage_build:
        print(build(args.root, args.upstream, args.lineage_build.resolve()))
    elif args.action == 'gates' and args.root and args.build:
        print(gates(args.build.resolve(), args.root))
    elif args.action == 'prepare' and args.root and args.build and args.gates:
        print(prepare(args.build.resolve(), args.gates.resolve(), args.root))
    elif args.action == 'run' and args.manifest:
        run_matrix(args.manifest.resolve())
    else:
        parser.error('missing required paths')


if __name__ == '__main__':
    main()
