"""SM-H001 fresh inherited gates, immutable preparation and explicit six-worker launch.

Preparation only seals inputs. Launch requires clean committed implementation,
direct origin/main equality and a repeated held-out seed audit; it never resumes.
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

from experiments.stringmol import conservation_workflow as c, lineage_workflow as lineage
from experiments.stringmol import decay_workflow as decay, analyze_decay as decay_analyzer
from experiments.stringmol import analyze_renewal as analyzer, analyze_conservation as v1
from experiments.stringmol.configure_control import StringmolControlConfig, render_config
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.conservation_workflow import command as command, source_state as source_state, record as record, inventory as inventory, seal as seal, read as read, ENV, ROOT, HERE

PATCHES = decay.PATCHES
IMPLEMENTATION = [*decay.IMPLEMENTATION, HERE/'renewal_workflow.py', HERE/'analyze_renewal.py', ROOT/'tests/test_stringmol_renewal.py']
REMOTE = 'origin'
REMOTE_REF = 'refs/heads/main'
PROTOCOL_PATH = 'reports/sm_h001_reproductive_renewal_preregistration.md'
PROTOCOL_REVISION = '6d698246d6cdace4d769558e99b510abbd0e45a3'
PROTOCOL_SHA256 = '0f00754ab3d2a9cdd69cea3a5c19dfed8791cf4be03de80041248dfc758d302e'


def protocol_pin() -> dict[str, Any]:
    raw = command(['git', 'show', f'{PROTOCOL_REVISION}:{PROTOCOL_PATH}'], ROOT)
    require(c.digest(raw) == PROTOCOL_SHA256 and (ROOT/PROTOCOL_PATH).read_bytes() == raw, 'committed SM-H001 protocol mismatch')
    for patch in PATCHES:
        require(command(['git', 'show', f'{PROTOCOL_REVISION}:{patch.relative_to(ROOT)}'], ROOT) == patch.read_bytes(), 'inherited patch differs from H001 commitment')
    return {'path': PROTOCOL_PATH, 'revision': PROTOCOL_REVISION, 'sha256': PROTOCOL_SHA256, 'bytes_hex': raw.hex(), 'inherited': decay.protocol_pin()}


def build(root: Path, upstream: Path, lineage_build: Path) -> Path:
    protocol = protocol_pin()
    lineage.verify_build(lineage_build)
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    inputs = {str(p): record(p) for p in IMPLEMENTATION}
    conservation_build = c.build(root/'conservation', upstream)
    decay_build = decay.build(root/'decay', upstream)
    data = decay.verify_build(decay_build)
    inherited = {name: {'path': str(path), 'record': record(path)} for name, path in
                 (('lineage', lineage_build.resolve()), ('conservation', conservation_build), ('decay', decay_build))}
    require(inputs == {str(p): record(p) for p in IMPLEMENTATION}, 'H001 implementation changed during build')
    seal(root/'build.json', {'protocol_pin': protocol, 'implementation': inputs, 'inherited': inherited, 'builds': data['builds']})
    return root/'build.json'


def verify_build(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = read(path)
    require(data['protocol_pin'] == protocol_pin() and data['implementation'] == {str(p): record(p) for p in IMPLEMENTATION}, 'H001 build inputs changed')
    require(set(data['inherited']) == {'lineage', 'conservation', 'decay'}, 'H001 inherited builds')
    for name, module in (('lineage', lineage), ('conservation', c), ('decay', decay)):
        entry = data['inherited'][name]
        require(record(Path(entry['path'])) == entry['record'], 'inherited build record')
        checked = module.verify_build(Path(entry['path']))
        if name == 'decay':
            require(checked['builds'] == data['builds'], 'H001 baseline is fresh patch 0004')
    return data


def validation_commands() -> dict[str, list[str]]:
    tests = ['tests/test_stringmol_' + n + '.py' for n in ('renewal', 'decay', 'conservation', 'lineage', 'control')]
    modules = [str(HERE/n) for n in ('renewal_workflow.py', 'analyze_renewal.py', 'decay_workflow.py', 'analyze_decay.py', 'conservation_workflow.py', 'analyze_conservation.py', 'lineage_workflow.py', 'analyze_lineage.py')]
    return {'pytest': [str(ROOT/'.venv/bin/python'), '-m', 'pytest', '-q', *tests],
            'mypy': [str(ROOT/'.venv/bin/python'), '-m', 'mypy', *modules, *tests]}


def validation(root: Path) -> dict[str, Any]:
    results = {}
    for name, args in validation_commands().items():
        proc = subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True)
        (root/f'{name}.txt').write_bytes(proc.stdout + proc.stderr)
        require(proc.returncode == 0, f'H001 {name} failed: {root/name}')
        results[name] = {'command': args, 'exit_status': 0, 'log': record(root/f'{name}.txt')}
    return results


def run_input(source: Path, root: Path, seed: int, condition: str) -> dict[str, Any]:
    require(condition in {'host', 'inert'}, 'unknown H001 condition')
    config = root/f'{condition}-{seed}.conf'
    expected = lineage.expected_initial(condition)
    initial = v1.initial_material(expected, 'histogram', 0)
    return {'condition': condition, 'seed': seed, 'route': 'recycle', 'config': str(config),
            'command': [str(source/'release/stringmol'), '30', str(config)],
            'directory': str(root/'runs'/condition/str(seed)), 'environment': decay.environment('recycle'),
            'expected_initial': expected, 'initial_material': {**initial, 'waste': [0]*33}}


def development_input(source: Path, root: Path) -> dict[str, Any]:
    return run_input(source, root, 202620999, 'host')


def gates(build_path: Path, root: Path) -> Path:
    data = verify_build(build_path)
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    paths = {k: Path(v['path']) for k, v in data['inherited'].items()}
    lg = lineage.isolation(paths['lineage'], root/'lineage')
    cg = c.gates(paths['conservation'], root/'conservation', paths['lineage'], lg)
    dg = decay.gates(paths['decay'], root/'decay', paths['lineage'], lg)
    checks = validation(root)
    source = Path(data['builds']['observer']['source'])
    r = development_input(source, root)
    config = Path(r['config'])
    config.write_text(render_config(StringmolControlConfig('host-only', r['seed'], 0, 0), source/'config/ALXII.mtx'))
    config.chmod(0o444)
    # Both workflows receive identical canonical config/command/environment.
    old = decay.run_input(source, root, r['seed'], 'R')
    require(old['environment'] == r['environment'] and old['expected_initial'] == r['expected_initial'], 'development input compatibility')
    inherited_run = c.execute(source/'release/stringmol', config, root/'development-inherited', old['environment'])
    new_run = c.execute(Path(r['command'][0]), config, Path(r['directory']), r['environment'])
    c.parity(inherited_run, new_run)
    summary = analyzer.analyze_run(Path(r['directory']), r['expected_initial'])
    require(set(new_run['files']) == decay_analyzer.output_names(summary['end_timestep']), 'development output names')
    seal(root/'gates.json', {'passed': True, 'build_record': record(build_path),
                           'inherited': {k: {'path': str(p), 'record': record(p)} for k, p in (('lineage', lg), ('conservation', cg), ('decay', dg))},
                           'validation': checks, 'development_input': r, 'config': record(config),
                           'inherited_run': inherited_run, 'new_run': new_run, 'summary': summary})
    verify_gate(root/'gates.json', build_path)
    return root/'gates.json'


def verify_gate(path: Path, build_path: Path) -> None:
    data = verify_build(build_path)
    gate = read(path)
    root = path.parent
    require(gate['passed'] is True and gate['build_record'] == record(build_path), 'H001 gate provenance')
    require(set(gate['inherited']) == {'lineage', 'conservation', 'decay'}, 'H001 inherited gate set')
    for name, module in (('lineage', lineage), ('conservation', c), ('decay', decay)):
        entry = gate['inherited'][name]
        require(record(Path(entry['path'])) == entry['record'], 'H001 inherited gate record')
        module.verify_gate(Path(entry['path']), Path(data['inherited'][name]['path']))
    for name, args in validation_commands().items():
        require(gate['validation'][name] == {'command': args, 'exit_status': 0, 'log': record(root/f'{name}.txt')}, 'H001 validation changed')
    source = Path(data['builds']['observer']['source'])
    r = development_input(source, root)
    require(gate['development_input'] == r, 'development input changed')
    config = Path(r['config'])
    require(record(config) == gate['config'] and config.read_text() == render_config(StringmolControlConfig('host-only', r['seed'], 0, 0), source/'config/ALXII.mtx'), 'development config changed')
    for key, directory in (('inherited_run', root/'development-inherited'), ('new_run', Path(r['directory']))):
        require(gate[key]['files'] == inventory(directory), 'development output changed')
    c.parity(gate['inherited_run'], gate['new_run'])
    summary = analyzer.analyze_run(Path(r['directory']), r['expected_initial'])
    require(summary == gate['summary'] and set(gate['new_run']['files']) == decay_analyzer.output_names(summary['end_timestep']), 'development replay changed')


def evidence_hash(value: Any) -> str:
    return c.digest(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())


def authorized_inputs(path: Path, data: dict[str,Any]) -> set[Path]:
    expected = {path.parent/f'{arm}-{seed}.conf' for arm, seed in analyzer.MATRIX}
    require({Path(r['config']) for r in data['runs']} == expected,'authorized preparation config paths')
    return expected | {path,path.with_name('preparation.sha256.json')}


def unseen_audit(root: Path, *, authorized_files: set[Path] | None = None) -> dict[str,Any]:
    """Audit all historical run/sweep inputs; exempt only exact authorized inputs.

    No directory subtree is exempt: an execution artifact inside the authorized
    preparation is still evidence of prior use. The caller verifies the complete
    preparation before passing its 32 immutable input paths.
    """
    started = datetime.now(timezone.utc).isoformat()
    allowed = authorized_files or set()
    require(all(p.parent == root for p in allowed),'audit exclusion outside authorized preparation')
    excluded = {str(p):record(p) for p in sorted(allowed)}
    matches = []
    checked: dict[str,Any] = {}
    directories = []
    # Literal prefix permits efficient scanning of large historical CSVs. The
    # preceding-byte check rejects decimal substrings, not seed-bearing names.
    pattern = re.compile(rb'2026230(?:0[0-9]|1[0-9])(?![0-9])')
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
            if contains_seed(raw): matches.append(str(p))
    require(not matches, 'unseen seed prior input/use: '+str(matches))
    return {'scope':['runs','sweeps'],'authorized_preparation':str(root),'excluded_files':excluded,'checked_files':len(checked),'inventory':checked,'directories':directories,'matches':matches,'seeds':list(range(202623000,202623020)), 'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat()}


def verify_audit(audit: dict[str,Any], path: Path, data: dict[str,Any]) -> None:
    require(audit['scope'] == ['runs','sweeps'] and audit['seeds'] == list(range(202623000,202623020)) and audit['matches'] == [],'freshness audit scope/results')
    require(audit['authorized_preparation'] == str(path.parent) and audit['excluded_files'] == {str(p):record(p) for p in sorted(authorized_inputs(path,data))},'freshness audit exclusions')
    require(audit['checked_files'] == len(audit['inventory']),'freshness audit inventory count')
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


def serialization() -> dict[str, Any]:
    return {'json': 'ASCII escapes; sorted keys; indent=2; final LF; SHA-256 of exact bytes',
            'csv': 'ASCII; canonical decimals and uppercase hex; exact ordered columns; LF',
            'aggregate': decay_analyzer.COLUMNS, 'buffers': v1.BUFFER_COLUMNS,
            'journal': decay_analyzer.JOURNAL_COLUMNS,
            'full_horizon_filenames': sorted(decay_analyzer.output_names(5000)),
            'early_END_rule': 'output_names(actual_END); checkpoints range(0, actual_END, 100)'}


def prepare(build_path: Path, gate_path: Path, root: Path) -> Path:
    data = verify_build(build_path); verify_gate(gate_path,build_path)
    root = root.resolve()
    audit = unseen_audit(root)
    root.mkdir(parents=True,exist_ok=False)
    source = Path(data['builds']['observer']['source'])
    require(not (root/'runs').exists() and not (root/'campaign.json').exists(),'preparation must not contain execution')
    entries = []
    for arm, seed in analyzer.MATRIX:
        r = run_input(source,root,seed,arm); config = Path(r['config'])
        config.write_text(render_config(StringmolControlConfig('host-only' if arm == 'host' else 'inert',seed,0,0),source/'config/ALXII.mtx')); config.chmod(0o444)
        entries.append({**r,**record(config),'bytes_hex':config.read_bytes().hex()})
    path = root/'preparation.json'
    seal(path,{'protocol':'SM-H001','protocol_pin':protocol_pin(),'workers':6,'status':'prepared-only; commit and push required before launch','build_manifest':str(build_path),'build_record':record(build_path),'build':data,'gates':str(gate_path),'gate_record':record(gate_path),'implementation':{str(p):record(p) for p in IMPLEMENTATION},'schema':serialization(),'repository_state':source_state(ROOT),'launch_target':remote_target(),'unseen_audit':audit,'runs':entries})
    seal(root/'preparation.sha256.json',record(path))
    verify_preparation(path)
    return path


def verify_preparation(path: Path) -> dict[str,Any]:
    require(not path.stat().st_mode & 0o222 and record(path) == read(path.with_name('preparation.sha256.json')),'preparation seal')
    data: dict[str,Any] = read(path)
    require(path.read_bytes() == (json.dumps(data, indent=2, sort_keys=True) + '\n').encode('ascii'), 'noncanonical preparation serialization')
    require(not path.with_name('preparation.sha256.json').stat().st_mode & 0o222, 'mutable preparation digest')
    expected_names = {p.name for p in authorized_inputs(path, data)}
    allowed_names = expected_names | {'runs', 'launch.json', 'campaign.json', 'campaign-results.json'}
    require(expected_names <= {p.name for p in path.parent.iterdir()} <= allowed_names, 'preparation filename set')
    audit = data['unseen_audit']
    require(audit['scope'] == ['runs', 'sweeps'] and audit['seeds'] == list(range(202623000,202623020)) and not audit['matches'] and not audit['excluded_files'], 'preparation seed audit')
    require(data['protocol'] == 'SM-H001' and data['protocol_pin'] == protocol_pin() and data['workers'] == 6,'prepared protocol')
    require(data['implementation'] == {str(p):record(p) for p in IMPLEMENTATION},'prepared implementation')
    require(data['schema'] == serialization(),'schema mismatch')
    require(data['launch_target'] == remote_target(),'prepared origin/main target changed')
    bp,gp = Path(data['build_manifest']),Path(data['gates'])
    require(record(bp) == data['build_record'] and verify_build(bp) == data['build'] and record(gp) == data['gate_record'],'prepared provenance')
    verify_gate(gp,bp)
    require([(r['condition'],r['seed']) for r in data['runs']] == analyzer.MATRIX,'matrix mismatch')
    source = Path(data['build']['builds']['observer']['source'])
    for r in data['runs']:
        config = Path(r['config']); raw = render_config(StringmolControlConfig('host-only' if r['condition'] == 'host' else 'inert',r['seed'],0,0),source/'config/ALXII.mtx').encode()
        require(not config.stat().st_mode & 0o222 and config.read_bytes() == raw,'read-only input changed')
        require(r == {**run_input(source,path.parent,r['seed'],r['condition']),**record(config),'bytes_hex':raw.hex()},'input mismatch')
    return data


def launch_evidence(path: Path, data: dict[str,Any]) -> dict[str,Any]:
    require(not command(['git','status','--porcelain'],ROOT).strip(),'commit implementation before launch')
    require(not any((path.parent/n).exists() for n in ('runs','campaign.json','launch.json','campaign-results.json')),'no resume/selective retry')
    commit = command(['git','rev-parse','HEAD'],ROOT).decode().strip()
    require(re.fullmatch('[0-9a-f]{40}',commit) is not None,'invalid HEAD revision')
    committed = {}
    for p in [*IMPLEMENTATION,*PATCHES,ROOT/PROTOCOL_PATH]:
        raw = command(['git','show',commit+':'+str(p.relative_to(ROOT))],ROOT)
        require(raw == p.read_bytes(),'uncommitted input')
        committed[str(p)] = {**record(p),'bytes_hex':raw.hex()}
    remote = observe_remote(data['launch_target'],commit)
    # Last substantive pre-seal action: repeat the audit even if preparation's
    # audit passed. Exempt only this verified manifest, digest, and 30 configs.
    audit = unseen_audit(path.parent,authorized_files=authorized_inputs(path,data))
    return {'input_manifest':record(path),'commit':commit,'remote':remote,'committed_files':committed,'freshness_audit':audit,'freshness_audit_sha256':evidence_hash(audit)}


def verify_launch(path: Path) -> None:
    launch_path = path.parent/'launch.json'
    launch = read(launch_path); data = read(path)
    require(not launch_path.stat().st_mode & 0o222 and launch['input_manifest'] == record(path),'launch input seal')
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
