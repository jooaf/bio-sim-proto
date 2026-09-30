"""SM-C002 fresh build/gates and sealed preparation; execution is a separate action."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
from typing import Any
from experiments.stringmol import conservation_workflow as c, lineage_workflow as lineage, analyze_decay as analyzer
from experiments.stringmol import analyze_conservation as v1
from experiments.stringmol.configure_control import StringmolControlConfig, render_config
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.conservation_workflow import command as command, source_state, release_objects, verify_release_objects, record, inventory, seal, read, ENV, FLAGS, PIN, ROOT, HERE


PATCHES = [*c.PATCHES, HERE / "patches/0004-add-decay-routing-and-material-journal.patch"]
IMPLEMENTATION = [*c.IMPLEMENTATION, HERE/'decay_workflow.py', HERE/'analyze_decay.py', ROOT/'tests/test_stringmol_decay.py', ROOT/'tests/stringmol_decay_directed.cpp', ROOT/'pyproject.toml', ROOT/'uv.lock', HERE/'README.md']
REMOTE = 'origin'
REMOTE_REF = 'refs/heads/main'

PROTOCOL_PATH = 'reports/sm_c002_decay_recycling_preregistration.md'
PROTOCOL_REVISION = '5cce74b73b199ceab5472bf3a27ad11119617d64'
PROTOCOL_SHA256 = '76672a6229b7cfbd845d9fd659a7bfaa0184a61078488debf6996a1b858ecc93'

def protocol_pin() -> dict[str,Any]:
    raw = command(['git','show',f'{PROTOCOL_REVISION}:{PROTOCOL_PATH}'],ROOT)
    require(c.digest(raw) == PROTOCOL_SHA256 and (ROOT/PROTOCOL_PATH).read_bytes() == raw, 'committed SM-C002 protocol mismatch')
    for patch in c.PATCHES:
        require(command(['git','show',f'{PROTOCOL_REVISION}:{patch.relative_to(ROOT)}'],ROOT) == patch.read_bytes(),'inherited patch differs from preregistration commit')
    return {'path':PROTOCOL_PATH,'revision':PROTOCOL_REVISION,'sha256':PROTOCOL_SHA256,'bytes_hex':raw.hex(),'inherited':c.protocol_pin()}

def build(root: Path, upstream: Path) -> Path:
    protocol = protocol_pin()
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    inputs = {str(p):record(p) for p in [*IMPLEMENTATION,*PATCHES]}
    builds = {}
    for name, patches in (("baseline", PATCHES[:3]), ("observer", PATCHES)):
        source = root / name
        command(["git", "clone", "--no-hardlinks", "--no-checkout", str(upstream.resolve()), str(source)], root)
        command(["git", "checkout", "--detach", PIN], source)
        for patch in patches:
            command(["git", "apply", str(patch)], source)
        for folder in ("debug", "release", "output"):
            (source / folder).mkdir(exist_ok=True)
        with (root / f"{name}-tests.txt").open("wb") as f:
            tested = subprocess.run(["bash", "RunCatchTests.sh"], cwd=source / "tests", env=ENV, stdout=f, stderr=subprocess.STDOUT)
        if tested.returncode or b"All tests passed" not in (root / f"{name}-tests.txt").read_bytes():
            raise ValueError(f"upstream tests failed: {name}")
        with (root / f"{name}-build.txt").open("wb") as f:
            subprocess.run(["make", "all", *[f"{k}={v}" for k, v in FLAGS.items()]], cwd=source / "src", env=ENV, stdout=f, stderr=subprocess.STDOUT, check=True)
        builds[name] = {"source": str(source), "state": source_state(source), "binary": record(source / "release/stringmol"), "release_objects": release_objects(source), "matrix": record(source / "config/ALXII.mtx"), "patch_order": [str(p) for p in patches]}
    manifest = {"builds": builds, "patches": [{"path": str(p), **record(p), "bytes_hex": p.read_bytes().hex()} for p in PATCHES], "flags": FLAGS, "environment": ENV,
                "compilers": {c: command([c, "--version"], root).decode() for c in ("gcc", "g++")},
                "logs": {p.name: record(p) for p in root.glob("*.txt")}}
    require(inputs == {str(p):record(p) for p in [*IMPLEMENTATION,*PATCHES]}, "build inputs changed while building")
    manifest["protocol_pin"] = protocol
    manifest["implementation"] = {str(p): record(p) for p in IMPLEMENTATION}
    seal(root / "build.json", manifest)
    return root / "build.json"


def verify_build(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = read(path)
    if data.get("protocol_pin") != protocol_pin():
        raise ValueError("build protocol pin mismatch")
    if data["implementation"] != {str(p): record(p) for p in IMPLEMENTATION}:
        raise ValueError("build implementation changed")
    if data["environment"] != ENV or data["flags"] != FLAGS:
        raise ValueError("build environment/flags mismatch")
    for saved, patch in zip(data["patches"], PATCHES, strict=True):
        if saved != {"path": str(patch), **record(patch), "bytes_hex": patch.read_bytes().hex()}:
            raise ValueError("patch mismatch")
    for name, info in data["builds"].items():
        source = Path(info["source"])
        if info["state"]["commit"] != PIN or source_state(source) != info["state"]:
            raise ValueError("source changed")
        if info["binary"] != record(source / "release/stringmol") or info["matrix"] != record(source / "config/ALXII.mtx"):
            raise ValueError("binary/matrix changed")
        verify_release_objects(source, info["release_objects"])
        expected = PATCHES[:3] if name == "baseline" else PATCHES
        if info["patch_order"] != [str(p) for p in expected]:
            raise ValueError("patch order mismatch")
    if set(data["builds"]) != {"baseline", "observer"}:
        raise ValueError("missing build")
    for name, expected_record in data["logs"].items():
        if record(path.parent / name) != expected_record:
            raise ValueError("build log changed")
    return data


def environment(route: str | None = None, *, conservation: bool = True, logging: bool = True, lineage_log: bool = True) -> dict[str,str]:
    env = c.environment('histogram' if conservation else None, 0, logging=lineage_log)
    if route is not None: env['STRINGMOL_DECAY_DESTINATION'] = route
    if not logging: env['STRINGMOL_CONSERVATION_LOG'] = '0'
    return env


def directed_linkage(data: dict[str,Any], root: Path) -> dict[str,Any]:
    source = Path(data['builds']['observer']['source'])
    verify_release_objects(source,data['builds']['observer']['release_objects'])
    objects = {str(source/'release'/n):v for n,v in data['builds']['observer']['release_objects'].items() if n != 'stringmol.o'}
    args = ['g++','-std=c++11','-O2','-Wall','-I',str(source/'src'),str(ROOT/'tests/stringmol_decay_directed.cpp'),*objects,'-o',str(root/'directed-test')]
    return {'command':args,'environment':ENV,'objects':objects,'fixture':record(ROOT/'tests/stringmol_decay_directed.cpp')}


def directed(data: dict[str,Any], root: Path) -> dict[str,Any]:
    linkage = directed_linkage(data,root)
    command(linkage['command'],root)
    require(directed_linkage(data,root) == linkage,'directed inputs changed during link')
    result = subprocess.run([str(root/'directed-test')],cwd=root,env=ENV,capture_output=True)
    (root/'directed.stdout').write_bytes(result.stdout); (root/'directed.stderr').write_bytes(result.stderr)
    require(result.returncode == 0 and b'SM-C002 directed gates passed\n' in result.stdout,'directed mechanics failed')
    return {**linkage,'exit_status':0,'binary':record(root/'directed-test'),'stdout':record(root/'directed.stdout'),'stderr':record(root/'directed.stderr')}


def validation(root: Path) -> dict[str,Any]:
    tests = ['tests/test_stringmol_decay.py','tests/test_stringmol_conservation.py','tests/test_stringmol_lineage.py','tests/test_stringmol_control.py']
    args = {'pytest':[str(ROOT/'.venv/bin/python'),'-m','pytest','-q',*tests], 'mypy':[str(ROOT/'.venv/bin/python'),'-m','mypy',*[str(HERE/n) for n in ('decay_workflow.py','analyze_decay.py','conservation_workflow.py','analyze_conservation.py','lineage_workflow.py','analyze_lineage.py')],*tests]}
    results = {}
    for name,cmd in args.items():
        proc = subprocess.run(cmd,cwd=ROOT,env=ENV,capture_output=True)
        (root/f'{name}.txt').write_bytes(proc.stdout+proc.stderr)
        require(proc.returncode == 0,f'{name} failed: {root/name}')
        results[name] = {'command':cmd,'exit_status':0,'log':record(root/f'{name}.txt')}
    return results


def projection(base: Path, routed: Path) -> None:
    from experiments.stringmol import analyze_conservation as a
    old = a.canonical_rows(base/'conservation001.csv',a.COLUMNS)
    new = a.canonical_rows(routed/'conservation002.csv',analyzer.COLUMNS)
    require(old == [{k:r[k] for k in a.COLUMNS} for r in new],'v2/v1 aggregate projection')
    require((base/'conservation_buffers001.csv').read_bytes() == (routed/'conservation_buffers002.csv').read_bytes(),'v2/v1 buffers')
    require(all(r[k] == '0' for r in new for p in ('waste','decay_to_waste','residual') for k in a.fields(p)),'recycle nonzero waste')


def gate_cases() -> list[tuple[str,str,int,float,dict[str,str]]]:
    return [
        ('absent-base','baseline',202620998,.0005,environment()),
        ('absent-new','observer',202620998,.0005,environment()),
        ('recycle-base','baseline',202620999,.0005,environment()),
        ('recycle','observer',202620999,.0005,environment('recycle')),
        ('repeat','observer',202620999,.0005,environment('recycle')),
        ('log-off','observer',202620999,.0005,environment('recycle',logging=False)),
        ('lineage-off','observer',202620999,.0005,environment('recycle',lineage_log=False)),
        ('sequester','observer',202620999,.0005,environment('sequester')),
        ('sequester-repeat','observer',202620999,.0005,environment('sequester')),
        ('sequester-off','observer',202620999,.0005,environment('sequester',logging=False)),
        *[(f'disabled-zero-{r or "absent"}','observer',202620998,.0005,{**environment(r,conservation=False),'STRINGMOL_CONSERVATION':'0','STRINGMOL_POOL_MODE':'invalid','STRINGMOL_POOL_AMOUNT':'invalid'}) for r in (None,'recycle','sequester')],
        *[(f'disabled-{r or "absent"}','observer',202620998,.0005,environment(r,conservation=False)) for r in (None,'recycle','sequester')],
        *[(f'nodecay-{r}','observer',202620999,0.,environment(r)) for r in ('recycle','sequester')],
    ]


def compare_gates(root: Path, results: dict[str,Any]) -> dict[str,Any]:
    def stripped(name: str, files: set[str]) -> dict[str,Any]:
        r = results[name]
        require(files <= r['files'].keys(), 'missing observation files')
        return {**r,'files':{k:v for k,v in r['files'].items() if k not in files}}
    c.parity(results['absent-base'],results['absent-new'])
    c.parity(stripped('recycle-base',c.CONSERVATION_LOGS),stripped('recycle',analyzer.LOGS))
    projection(root/'recycle-base',root/'recycle')
    for route in ('recycle','sequester'):
        c.parity(results[route],results['repeat' if route == 'recycle' else 'sequester-repeat'])
        c.parity(results['log-off' if route == 'recycle' else 'sequester-off'],results[route],analyzer.LOGS)
    c.parity(results['lineage-off'],results['recycle'],c.LOGS)
    for route in ('absent','recycle','sequester'):
        c.parity(results['disabled-absent'],results['disabled-'+route])
        c.parity(results['disabled-absent'],results['disabled-zero-'+route])
    # No route metadata is serialized: zero-decay observations must all match.
    c.parity(results['nodecay-recycle'],results['nodecay-sequester'])
    summaries = {}
    for name,_,_,_,env in gate_cases():
        if env.get('STRINGMOL_DECAY_DESTINATION') and env.get('STRINGMOL_CONSERVATION') == '1' and env.get('STRINGMOL_CONSERVATION_LOG') != '0' and env.get('STRINGMOL_LINEAGE_LOG') == '1':
            summary = analyzer.analyze_run(root/name,lineage.expected_initial('host'),env['STRINGMOL_DECAY_DESTINATION'],nsteps=500)
            if name.startswith('nodecay'): require(summary['decay_exposure'] == 0 and not any(summary['end_arrays']['waste']), 'no-decay exposure')
            require(set(results[name]['files']) == analyzer.output_names(summary['end_timestep']),'gate v2 filename set')
            summaries[name] = summary
    return summaries


def gates(build_path: Path, root: Path, lineage_build: Path, lineage_gate: Path) -> Path:
    data = verify_build(build_path)
    lineage.verify_build(lineage_build); lineage.verify_gate(lineage_gate,lineage_build)
    root = root.resolve(); root.mkdir(parents=True,exist_ok=False)
    checks = validation(root)
    fixture = directed(data,root)
    results = {}
    configs = {}
    matrix = Path(data['builds']['baseline']['source'])/'config/ALXII.mtx'
    for name,source,seed,decay,env in gate_cases():
        config = root/f'{seed}-{decay}.conf'
        if not config.exists():
            config.write_text(render_config(StringmolControlConfig('host-only',seed,0,0,nsteps=500,decay_rate=decay),matrix)); config.chmod(0o444)
        configs[config.name] = record(config)
        binary = Path(data['builds'][source]['source'])/'release/stringmol'
        result = c.execute(binary,config,root/name,env)
        require(lineage.loader_ok(root/name),'gate loader warning')
        results[name] = {**result,'environment':env,'command':[str(binary),'30',str(config)]}
        seal(root/f'{name}-inventory.json',results[name])
    summaries = compare_gates(root,results)
    seal(root/'gates.json',{'passed':True,'build_record':record(build_path),'configs':configs,'runs':results,'summaries':summaries,'directed':fixture,'validation':checks,'lineage':{'build':str(lineage_build),'gate':str(lineage_gate),'build_record':record(lineage_build),'gate_record':record(lineage_gate)}})
    verify_gate(root/'gates.json',build_path)
    return root/'gates.json'


def verify_gate(path: Path, build_path: Path) -> None:
    data = verify_build(build_path); gate = read(path); root = path.parent
    require(gate['passed'] is True and gate['build_record'] == record(build_path),'gate build provenance')
    inherited = gate['lineage']; lb,lg = Path(inherited['build']),Path(inherited['gate'])
    require(record(lb) == inherited['build_record'] and record(lg) == inherited['gate_record'],'lineage provenance')
    lineage.verify_build(lb); lineage.verify_gate(lg,lb)
    require(set(gate['runs']) == {r[0] for r in gate_cases()},'gate case set')
    matrix = Path(data['builds']['baseline']['source'])/'config/ALXII.mtx'
    for name,source,seed,decay,env in gate_cases():
        r = gate['runs'][name]; config = root/f'{seed}-{decay}.conf'
        require(config.read_text() == render_config(StringmolControlConfig('host-only',seed,0,0,nsteps=500,decay_rate=decay),matrix) and record(config) == gate['configs'][config.name], 'gate config')
        require(r['environment'] == env and r['command'] == [str(Path(data['builds'][source]['source'])/'release/stringmol'),'30',str(config)],'gate command/environment')
        require(r == read(root/f'{name}-inventory.json') and r['files'] == inventory(root/name) and r['exit_status'] == 0 and lineage.loader_ok(root/name),'gate outputs')
    require(compare_gates(root,gate['runs']) == gate['summaries'],'gate replay changed')
    for name in ('pytest','mypy'):
        require(gate['validation'][name]['exit_status'] == 0 and gate['validation'][name]['log'] == record(root/f'{name}.txt'),'validation changed')
    d = gate['directed']
    linkage = directed_linkage(data,root)
    require(all(d[k] == v for k,v in linkage.items()),'directed command/fixture/environment')
    directed_source = Path(data['builds']['observer']['source'])
    require(d['exit_status'] == 0 and d['objects'] == {str(directed_source/'release'/n):v for n,v in data['builds']['observer']['release_objects'].items() if n != 'stringmol.o'},'directed linkage')
    for key,filename in (('binary','directed-test'),('stdout','directed.stdout'),('stderr','directed.stderr')): require(d[key] == record(root/filename),'directed artifact')


def run_input(source: Path, root: Path, seed: int, condition: str) -> dict[str,Any]:
    route = {'R':'recycle','S':'sequester'}[condition]
    config = root/f'{condition}-{seed}.conf'
    expected = lineage.expected_initial('host')
    initial = v1.initial_material(expected,'histogram',0)
    return {'condition':condition,'seed':seed,'route':route,'config':str(config),'command':[str(source/'release/stringmol'),'30',str(config)],'directory':str(root/'runs'/condition/str(seed)),'environment':environment(route),'expected_initial':expected,'initial_material':{**initial,'waste':[0]*33}}


def evidence_hash(value: Any) -> str:
    return c.digest(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())


def authorized_inputs(path: Path, data: dict[str,Any]) -> set[Path]:
    expected = {path.parent/f'{arm}-{seed}.conf' for seed in range(202622000,202622020) for arm in ('R','S')}
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
    checked: dict[str,Any] = {}
    directories = []
    # Literal prefix permits efficient scanning of large historical CSVs. The
    # preceding-byte check rejects decimal substrings, not seed-bearing names.
    pattern = re.compile(rb'2026220(?:0[0-9]|1[0-9])(?![0-9])')
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
    return {'scope':['runs','sweeps'],'authorized_preparation':str(root),'excluded_files':excluded,'checked_files':len(checked),'inventory':checked,'directories':directories,'matches':matches,'seeds':list(range(202622000,202622020)), 'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat()}


def verify_audit(audit: dict[str,Any], path: Path, data: dict[str,Any]) -> None:
    require(audit['scope'] == ['runs','sweeps'] and audit['seeds'] == list(range(202622000,202622020)) and audit['matches'] == [],'freshness audit scope/results')
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


def prepare(build_path: Path, gate_path: Path, root: Path) -> Path:
    data = verify_build(build_path); verify_gate(gate_path,build_path)
    root = root.resolve()
    audit = unseen_audit(root)
    root.mkdir(parents=True,exist_ok=False)
    source = Path(data['builds']['observer']['source'])
    require(not (root/'runs').exists() and not (root/'campaign.json').exists(),'preparation must not contain execution')
    entries = []
    for seed in range(202622000,202622020):
        for arm in ('R','S'):
            r = run_input(source,root,seed,arm); config = Path(r['config'])
            config.write_text(render_config(StringmolControlConfig('host-only',seed,0,0),source/'config/ALXII.mtx')); config.chmod(0o444)
            entries.append({**r,**record(config),'bytes_hex':config.read_bytes().hex()})
    path = root/'preparation.json'
    seal(path,{'protocol':'SM-C002','protocol_pin':protocol_pin(),'workers':6,'status':'prepared-only; commit and push required before launch','build_manifest':str(build_path),'build_record':record(build_path),'build':data,'gates':str(gate_path),'gate_record':record(gate_path),'implementation':{str(p):record(p) for p in IMPLEMENTATION},'schema':{'aggregate':analyzer.COLUMNS,'buffers':v1.BUFFER_COLUMNS,'journal':analyzer.JOURNAL_COLUMNS},'repository_state':source_state(ROOT),'launch_target':remote_target(),'unseen_audit':audit,'runs':entries})
    seal(root/'preparation.sha256.json',record(path))
    verify_preparation(path)
    return path


def verify_preparation(path: Path) -> dict[str,Any]:
    require(not path.stat().st_mode & 0o222 and record(path) == read(path.with_name('preparation.sha256.json')),'preparation seal')
    data: dict[str,Any] = read(path)
    require(data['protocol'] == 'SM-C002' and data['protocol_pin'] == protocol_pin() and data['workers'] == 6,'prepared protocol')
    require(data['implementation'] == {str(p):record(p) for p in IMPLEMENTATION},'prepared implementation')
    require(data['schema'] == {'aggregate':analyzer.COLUMNS,'buffers':v1.BUFFER_COLUMNS,'journal':analyzer.JOURNAL_COLUMNS},'schema mismatch')
    require(data['launch_target'] == remote_target(),'prepared origin/main target changed')
    bp,gp = Path(data['build_manifest']),Path(data['gates'])
    require(record(bp) == data['build_record'] and verify_build(bp) == data['build'] and record(gp) == data['gate_record'],'prepared provenance')
    verify_gate(gp,bp)
    require([(r['condition'],r['seed']) for r in data['runs']] == [(a,s) for s in range(202622000,202622020) for a in ('R','S')],'matrix mismatch')
    source = Path(data['build']['builds']['observer']['source'])
    for r in data['runs']:
        config = Path(r['config']); raw = render_config(StringmolControlConfig('host-only',r['seed'],0,0),source/'config/ALXII.mtx').encode()
        require(not config.stat().st_mode & 0o222 and config.read_bytes() == raw,'read-only input changed')
        require(r == {**run_input(source,path.parent,r['seed'],r['condition']),**record(config),'bytes_hex':raw.hex()},'input mismatch')
    return data


def launch_evidence(path: Path, data: dict[str,Any]) -> dict[str,Any]:
    require(not command(['git','status','--porcelain'],ROOT).strip(),'commit implementation before launch')
    require(not any((path.parent/n).exists() for n in ('runs','campaign.json','launch.json')),'no resume/selective retry')
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
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('build','gates','prepare','run'))
    for arg in ('root','build','gates','manifest','lineage-build','lineage-gate'): p.add_argument('--'+arg,type=Path)
    p.add_argument('--upstream',type=Path,default=HERE/'vendor/stringmol')
    a = p.parse_args()
    if a.action == 'build' and a.root: print(build(a.root,a.upstream))
    elif a.action == 'gates' and a.root and a.build and a.lineage_build and a.lineage_gate: print(gates(a.build.resolve(),a.root,a.lineage_build.resolve(),a.lineage_gate.resolve()))
    elif a.action == 'prepare' and a.root and a.build and a.gates: print(prepare(a.build.resolve(),a.gates.resolve(),a.root))
    elif a.action == 'run' and a.manifest: run_matrix(a.manifest.resolve())
    else: p.error('missing required paths')


if __name__ == '__main__': main()
