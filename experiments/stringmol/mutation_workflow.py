"""SM-M001 immutable 40-run preparation; H001 replay and H003 gates reused unchanged.

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

from experiments.stringmol import replicated_workflow as h3, renewal_workflow as h1, perturbation_panel as panel_tools
from experiments.stringmol import decay_workflow as decay, conservation_workflow as c, analyze_decay, lineage_workflow
from experiments.stringmol import analyze_mutation as analyzer
from experiments.stringmol.configure_control import StringmolControlConfig, render_config
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.conservation_workflow import command as command, source_state as source_state, record as record, inventory as inventory, seal as seal, read as read, ENV, ROOT, HERE

PATCHES = h3.PATCHES
IMPLEMENTATION = [*h3.IMPLEMENTATION, HERE/'mutation_workflow.py', HERE/'analyze_mutation.py', ROOT/'tests/test_stringmol_mutation.py']
REMOTE = 'origin'
REMOTE_REF = 'refs/heads/main'
PROTOCOL_PATH = 'reports/sm_m001_mutation_baseline_preregistration.md'
PROTOCOL_REVISION = 'c3030c1a36f6c5e9de99e2cbf5f3d9bab22e062a'
PROTOCOL_SHA256 = 'ef0b652a4f631690ba75eaac6bdf65fdbb12f900258f81e75027b60b2e4d6715'
evidence_hash = h3.evidence_hash
serialization = h3.serialization


def protocol_pin() -> dict[str, Any]:
    raw = command(['git', 'show', f'{PROTOCOL_REVISION}:{PROTOCOL_PATH}'], ROOT)
    require(c.digest(raw) == PROTOCOL_SHA256 and (ROOT/PROTOCOL_PATH).read_bytes() == raw, 'committed SM-M001 protocol mismatch')
    for patch in PATCHES:
        require(command(['git', 'show', f'{PROTOCOL_REVISION}:{patch.relative_to(ROOT)}'], ROOT) == patch.read_bytes(), 'inherited patch differs from M001 commitment')
    return {'path': PROTOCOL_PATH, 'revision': PROTOCOL_REVISION, 'sha256': PROTOCOL_SHA256, 'bytes_hex': raw.hex(), 'inherited': h3.protocol_pin()}


def matrix_path_gate(root: Path, lineage_build: Path) -> list[str]:
    # Pinned upstream stores SUBMAT in char swt_fn[80] using strcpy. Long
    # paths overwrite adjacent parameters. Prevent this without changing C++.
    lineage = lineage_workflow.verify_build(lineage_build)
    paths = [str(Path(v['source'])/'config/ALXII.mtx') for v in lineage['builds'].values()]
    paths += [str(root.resolve()/'inherited'/'inherited'/kind/variant/'config/ALXII.mtx')
              for kind in ('conservation', 'decay') for variant in ('baseline', 'observer')]
    require(all(len(p.encode('ascii')) < 80 for p in paths), 'pinned SUBMAT filename requires fewer than 80 bytes; use a shorter build root')
    return paths


def build(root: Path, upstream: Path, lineage_build: Path) -> Path:
    root = root.resolve()
    paths = matrix_path_gate(root, lineage_build)
    root.mkdir(parents=True, exist_ok=False)
    inputs = {str(p): record(p) for p in IMPLEMENTATION}
    # Require the caller's newly built lineage package; conservation and decay
    # are freshly built by H002, including their upstream suites.
    inherited = h3.build(root/'inherited', upstream, lineage_build)
    checked = h3.verify_build(inherited)
    require(inputs == {str(p): record(p) for p in IMPLEMENTATION}, 'implementation changed during build')
    seal(root/'build.json', {'protocol_pin': protocol_pin(), 'implementation': inputs,
                           'lineage_build': str(lineage_build.resolve()), 'matrix_paths': paths,
                           'inherited': str(inherited), 'inherited_record': record(inherited), 'builds': checked['builds']})
    return root/'build.json'


def verify_build(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = read(path)
    require(data['protocol_pin'] == protocol_pin() and data['implementation'] == {str(p): record(p) for p in IMPLEMENTATION}, 'M001 build inputs changed')
    require(data['matrix_paths'] == matrix_path_gate(path.parent, Path(data['lineage_build'])), 'matrix path safety changed')
    inherited = Path(data['inherited'])
    require(record(inherited) == data['inherited_record'] and h3.verify_build(inherited)['builds'] == data['builds'], 'M001 inherited build')
    return data


def validation_commands() -> dict[str, list[str]]:
    commands = h3.validation_commands()
    commands['pytest'].append('tests/test_stringmol_mutation.py')
    commands['mypy'].extend([str(HERE/'mutation_workflow.py'), str(HERE/'analyze_mutation.py'), 'tests/test_stringmol_mutation.py'])
    return commands


def validation(root: Path) -> dict[str, Any]:
    checks = {}
    for name, args in validation_commands().items():
        proc = subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True)
        log = root/f'{name}.txt'
        log.write_bytes(proc.stdout + proc.stderr)
        require(proc.returncode == 0, f'M001 {name} failed: {log}')
        checks[name] = {'command': args, 'exit_status': 0, 'log': record(log)}
    return checks


def run_input(source: Path, root: Path, seed: int, condition: str) -> dict[str, Any]:
    require(condition in analyzer.ARMS and seed in [*analyzer.SEEDS, 202620999], 'M001 arm/seed')
    r = h1.run_input(source, root, seed, 'host')
    config = root/f'{condition}-{seed}.conf'
    return {**r, 'condition': condition, 'config': str(config),
            'command': [str(source/'release/stringmol'), '30', str(config)],
            'directory': str(root/'runs'/condition/str(seed)),
            'environment': {**decay.environment('recycle'), 'NUMBA_NUM_THREADS': '1'}}


def custom_config(r: dict[str, Any], source: Path) -> str:
    require(r['condition'] in analyzer.ARMS, 'mutation arm')
    return render_config(StringmolControlConfig('host-only', r['seed'], 0, 0,
                         mutation_rate=0.0002 if r['condition'] == 'NATIVE' else 0), source/'config/ALXII.mtx')


def parse_config(raw: str, r: dict[str, Any], source: Path) -> None:
    require(raw == custom_config(r, source), 'strict sole-MUTATE config equality')
    lines = raw.splitlines(keepends=True)
    indexes = [i for i, line in enumerate(lines) if line.startswith('MUTATE ')]
    require(len(indexes) == 1, 'single MUTATE setting')
    # Only after exact arm validation normalize the sole treatment for the
    # independent inherited loader parser (including IDs, positions, host bytes).
    lines[indexes[0]] = 'MUTATE 0.0002\n'
    panel_tools.parse_config(''.join(lines), r['expected_initial'], r['seed'], source/'config/ALXII.mtx')


def rng_semantics(source: Path) -> dict[str, Any]:
    loader = (source/'src/stringPM.cpp').read_text()
    copy = (source/'src/sm_spatial.cpp').read_text()
    loader_fragment = 'subrate = mut;\n\t\t\tindelrate = mut;\n\t\t\tif(mut<FLT_MIN)\n\t\t\t\tdomut=0;'
    require(loader_fragment in loader, 'MUTATE loader zero rates/disabled mode')
    patch = PATCHES[2].read_text()
    start = patch.index('+void SpatialConservation::copy(')
    end = patch.index('\n+}\n', start) + len('\n+}')
    expected = '\n'.join(line[1:] for line in patch[start:end].splitlines())
    actual_start = copy.index('void SpatialConservation::copy(')
    actual_end = copy.index('\n}\n', actual_start) + len('\n}')
    require(copy[actual_start:actual_end] == expected, 'pinned conserved copy semantics')
    require('if (!domut) indelrate = subrate = 0;' in expected and
            'else {\n        float draw = RandomBetween0And1();\n        if (draw < indelrate)' in expected,
            'unconditional baseline draw before mutation branch')
    return {'loader': record(source/'src/stringPM.cpp'), 'copy_source': record(source/'src/sm_spatial.cpp'),
            'copy_function_sha256': c.digest(expected.encode()), 'zero_sets_both_rates_to_zero': True,
            'baseline_draw_preserved': True,
            'interpretation': 'Within-arm repeatability only; native mutation branches may consume additional draws and desynchronize paired streams.'}


def gates(build_path: Path, root: Path) -> Path:
    data = verify_build(build_path)
    root = root.resolve(); root.mkdir(parents=True, exist_ok=False)
    inherited = h3.gates(Path(data['inherited']), root/'inherited')
    checks = validation(root)
    source = Path(data['builds']['observer']['source'])
    semantics = rng_semantics(source)
    arms = {}
    for arm in analyzer.ARMS:
        r = run_input(source, root, 202620999, arm)
        config = Path(r['config']); config.write_text(custom_config(r, source)); config.chmod(0o444)
        parse_config(config.read_text(), r, source)
        first = c.execute(Path(r['command'][0]), config, Path(r['directory']), r['environment'])
        repeat = c.execute(Path(r['command'][0]), config, root/f'repeat-{arm}', r['environment'])
        c.parity(first, repeat)
        if arm == 'NATIVE': c.parity(read(inherited)['execution'], first)
        summary = analyzer.analyze_run(Path(r['directory']), r['expected_initial'])
        require(set(first['files']) == analyze_decay.output_names(summary['end_timestep']), 'development output names')
        arms[arm] = {'input': r, 'config': record(config), 'first': first, 'repeat': repeat, 'summary': summary}
    seal(root/'gates.json', {'passed': True, 'build_record': record(build_path), 'inherited': str(inherited),
                           'inherited_record': record(inherited), 'validation': checks, 'rng_semantics': semantics, 'arms': arms})
    verify_gate(root/'gates.json', build_path)
    return root/'gates.json'


def verify_gate(path: Path, build_path: Path) -> None:
    data = verify_build(build_path); gate = read(path)
    inherited = Path(gate['inherited'])
    require(gate['passed'] is True and gate['build_record'] == record(build_path) and gate['inherited_record'] == record(inherited), 'M001 gate provenance')
    h3.verify_gate(inherited, Path(data['inherited']))
    for name, args in validation_commands().items():
        require(gate['validation'][name] == {'command': args, 'exit_status': 0, 'log': record(path.parent/f'{name}.txt')}, 'M001 validation changed')
    source = Path(data['builds']['observer']['source'])
    require(gate['rng_semantics'] == rng_semantics(source), 'RNG semantics changed')
    require(set(gate['arms']) == set(analyzer.ARMS), 'development arms')
    for arm in analyzer.ARMS:
        r = run_input(source, path.parent, 202620999, arm); entry = gate['arms'][arm]
        config = Path(r['config'])
        require(entry['input'] == r and entry['config'] == record(config), 'development input changed')
        parse_config(config.read_text(), r, source)
        for key, directory in [('first', Path(r['directory'])), ('repeat', path.parent/f'repeat-{arm}')]:
            require(entry[key]['exit_status'] == 0 and entry[key]['files'] == inventory(directory), 'development execution changed')
        c.parity(entry['first'], entry['repeat'])
        if arm == 'NATIVE': c.parity(read(inherited)['execution'], entry['first'])
        summary = analyzer.analyze_run(Path(r['directory']), r['expected_initial'])
        require(summary == entry['summary'] and set(entry['first']['files']) == analyze_decay.output_names(summary['end_timestep']), 'development replay changed')


def authorized_inputs(path: Path, data: dict[str,Any]) -> set[Path]:
    expected = {path.parent/f'{arm}-{seed}.conf' for arm, seed in analyzer.MATRIX}
    require({Path(r['config']) for r in data['runs']} == expected,'authorized preparation config paths')
    return expected | {path,path.with_name('preparation.sha256.json')}


def unseen_audit(root: Path, *, authorized_files: set[Path] | None = None) -> dict[str,Any]:
    """Audit all historical run/sweep inputs; exempt only exact authorized inputs.

    No directory subtree is exempt: an execution artifact inside the authorized
    preparation is still evidence of prior use. The caller verifies the complete
    preparation before passing its 42 immutable input paths.
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
    pattern = re.compile(rb'2026260[01][0-9](?![0-9])')
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
    require(audit['nonseed_counter_matches'] == [], 'no counter exemptions for M001')
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
    require(not (root/'runs').exists() and not (root/'campaign.json').exists(),'preparation must not contain execution')
    entries = []
    for arm, seed in analyzer.MATRIX:
        r = run_input(source,root,seed,arm); config = Path(r['config'])
        config.write_text(custom_config(r,source)); config.chmod(0o444)
        entries.append({**r,**record(config),'bytes_hex':config.read_bytes().hex()})
    path = root/'preparation.json'
    seal(path,{'protocol':'SM-M001','protocol_pin':protocol_pin(),'workers':6,'status':'prepared-only; commit and push required before launch','build_manifest':str(build_path),'build_record':record(build_path),'build':data,'gates':str(gate_path),'gate_record':record(gate_path),'implementation':{str(p):record(p) for p in IMPLEMENTATION},'schema':serialization(),'repository_state':source_state(ROOT),'launch_target':remote_target(),'unseen_audit':audit,'runs':entries})
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
    require(data['protocol'] == 'SM-M001' and data['protocol_pin'] == protocol_pin() and data['workers'] == 6,'prepared protocol')
    require(data['implementation'] == {str(p):record(p) for p in IMPLEMENTATION},'prepared implementation')
    require(data['schema'] == serialization(),'schema mismatch')
    require(data['launch_target'] == remote_target(),'prepared origin/main target changed')
    bp,gp = Path(data['build_manifest']),Path(data['gates'])
    require(record(bp) == data['build_record'] and verify_build(bp) == data['build'] and record(gp) == data['gate_record'],'prepared provenance')
    verify_gate(gp,bp)
    require([(r['condition'],r['seed']) for r in data['runs']] == analyzer.MATRIX,'matrix mismatch')
    source = Path(data['build']['builds']['observer']['source'])
    for r in data['runs']:
        config = Path(r['config']); raw = custom_config(r,source).encode()
        require(not config.is_symlink() and not config.stat().st_mode & 0o222 and config.read_bytes() == raw,'read-only input changed')
        parse_config(raw.decode(), r, source)
        require(r == {**run_input(source,path.parent,r['seed'],r['condition']),**record(config),'bytes_hex':raw.hex()},'input mismatch')
    for offset in range(0,40,2):
        block = data['runs'][offset:offset+2]
        for native, zero in ((block[0],block[1]),):
            for key in ('molecular','pool','total','waste'):
                require(native['initial_material'][key] == zero['initial_material'][key], 'paired initial per-symbol material inequality')
            require(native['expected_initial'] == zero['expected_initial'], 'paired initial identity')
            require(Path(native['config']).read_text().replace('MUTATE 0.0002\n', 'MUTATE 0\n') == Path(zero['config']).read_text(), 'sole treatment difference')
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
    # audit passed. Exempt only this verified manifest, digest, and 40 configs.
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
