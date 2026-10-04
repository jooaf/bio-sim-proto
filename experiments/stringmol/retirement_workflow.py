"""SM-B002 immutable 80-run preparation with all inherited suites and native gates.

Build/gates use development seeds only. Prepare cannot launch. Run requires a
clean committed implementation, direct origin/main observation and a fresh audit.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from experiments.stringmol import mutation_workflow as m1, renewal_workflow as h1, perturbation_panel as panel_tools
from experiments.stringmol import decay_workflow as decay, conservation_workflow as c, analyze_decay, lineage_workflow, analyze_mutation as mutation_analyzer
from experiments.stringmol import analyze_retirement as analyzer
from experiments.stringmol import scheduling_workflow as b1
from experiments.stringmol.analyze_scheduling import LOGS as SCHEDULING_LOGS, COLUMNS as BOUNDARY_COLUMNS
from experiments.stringmol.configure_control import StringmolControlConfig, render_config
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.conservation_workflow import command as command, source_state as source_state, record as record, inventory as inventory, seal as seal, read as read, ENV, ROOT, HERE

PATCHES = [*b1.PATCHES, HERE/'patches/0006-add-source-remnant-retirement.patch']
IMPLEMENTATION = [*b1.IMPLEMENTATION, HERE/'retirement_workflow.py', HERE/'analyze_retirement.py', HERE/'retirement_material.py', ROOT/'tests/test_stringmol_retirement.py', ROOT/'tests/stringmol_retirement_directed.cpp', PATCHES[-1]]
REMOTE = 'origin'
REMOTE_REF = 'refs/heads/main'
PROTOCOL_PATH = 'reports/sm_b002_scheduling_source_retention_preregistration.md'
PROTOCOL_REVISION = '0e0d0a9a1f47c53ead2de314addbe3ffbca0ab14'
PROTOCOL_SHA256 = '10bee908d8ab1597539932ae839e9775974d39546d7eb6a475b61cff54c64a62'
evidence_hash = m1.evidence_hash
def serialization() -> dict[str, Any]:
    return {**b1.serialization(), 'source': analyzer.SOURCE_COLUMNS}


def protocol_pin() -> dict[str, Any]:
    raw = command(['git', 'show', f'{PROTOCOL_REVISION}:{PROTOCOL_PATH}'], ROOT)
    require(c.digest(raw) == PROTOCOL_SHA256 and (ROOT/PROTOCOL_PATH).read_bytes() == raw, 'committed SM-B002 protocol mismatch')
    for patch in PATCHES[:-1]:
        require(command(['git', 'show', f'{PROTOCOL_REVISION}:{patch.relative_to(ROOT)}'], ROOT) == patch.read_bytes(), 'inherited patch differs from B002 commitment')
    return {'path': PROTOCOL_PATH, 'revision': PROTOCOL_REVISION, 'sha256': PROTOCOL_SHA256, 'bytes_hex': raw.hex(), 'inherited': b1.protocol_pin()}


def build(root: Path, upstream: Path, lineage_build: Path, scheduling_build: Path | None = None) -> Path:
    root = root.resolve()
    # Inherited loader constraint applies to all nested builds.
    m1.matrix_path_gate(root/'b'/'m', lineage_build)
    require(len(str(root/'observer/config/ALXII.mtx').encode('ascii')) < 80, 'SUBMAT path too long')
    root.mkdir(parents=True, exist_ok=False)
    inputs = {str(p): record(p) for p in IMPLEMENTATION}
    inherited = scheduling_build.resolve() if scheduling_build else b1.build(root/'b', upstream, lineage_build)
    old = b1.verify_build(inherited)
    source = root/'observer'
    command(['git','clone','--no-hardlinks','--no-checkout',str(upstream.resolve()),str(source)],root)
    command(['git','checkout','--detach',c.PIN],source)
    for patch in PATCHES: command(['git','apply',str(patch)],source)
    for folder in ('debug','release','output'): (source/folder).mkdir(exist_ok=True)
    logs = {}
    for name,args,cwd in [('upstream',['bash','RunCatchTests.sh'],source/'tests'),
                          ('build',['make','all',*[f'{k}={v}' for k,v in c.FLAGS.items()]],source/'src')]:
        with (root/f'{name}.txt').open('xb') as log:
            process = subprocess.run(args,cwd=cwd,env=ENV,stdout=log,stderr=subprocess.STDOUT)
        require(process.returncode == 0, 'fresh patch0006 '+name+' failed')
        if name == 'upstream': require(b'All tests passed' in (root/f'{name}.txt').read_bytes(), 'upstream assertion receipt')
        logs[name] = {'command':args,'log':record(root/f'{name}.txt'),'exit_status':0}
    info = {'source':str(source),'state':source_state(source),'binary':record(source/'release/stringmol'),
            'release_objects':c.release_objects(source),'matrix':record(source/'config/ALXII.mtx'),
            'headers':{n:record(source/'src'/n) for n in ('sm_conservation.h','sm_scheduling.h','sm_retirement.h')},'new_header':record(source/'src/sm_retirement.h'),'patch_order':[str(p) for p in PATCHES]}
    require(inputs == {str(p):record(p) for p in IMPLEMENTATION}, 'build inputs changed')
    seal(root/'build.json', {'protocol_pin':protocol_pin(),'implementation':inputs,'inherited':str(inherited),
        'inherited_record':record(inherited),'builds':{'baseline':old['builds']['observer'],'observer':info},
        'flags':c.FLAGS,'environment':ENV,'logs':logs,
        'compilers':{compiler:command([compiler,'--version'],root).decode() for compiler in ('gcc','g++')}})
    return root/'build.json'


def verify_build(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = read(path)
    require(data['protocol_pin'] == protocol_pin() and data['implementation'] == {str(p):record(p) for p in IMPLEMENTATION}, 'B002 build inputs changed')
    inherited = Path(data['inherited'])
    old = b1.verify_build(inherited)
    require(record(inherited) == data['inherited_record'] and data['builds']['baseline'] == old['builds']['observer'], 'inherited baseline changed')
    require(set(data['builds']) == {'baseline','observer'} and data['flags'] == c.FLAGS and data['environment'] == ENV,'build schema')
    info = data['builds']['observer']; source = Path(info['source'])
    require(info['state']['commit'] == c.PIN and source_state(source) == info['state'], 'patched source changed')
    require(info['new_header'] == record(source/'src/sm_retirement.h') and info['binary'] == record(source/'release/stringmol') and info['matrix'] == record(source/'config/ALXII.mtx'), 'build artifact changed')
    require(info['headers'] == {n:record(source/'src'/n) for n in ('sm_conservation.h','sm_scheduling.h','sm_retirement.h')}, 'patched headers changed')
    require(info['patch_order'] == [str(p) for p in PATCHES], 'patch order changed')
    c.verify_release_objects(source,info['release_objects'])
    for name,entry in data['logs'].items(): require(entry['exit_status'] == 0 and entry['log'] == record(path.parent/f'{name}.txt'), 'build log changed')
    return data


def validation_commands() -> dict[str, list[str]]:
    commands = b1.validation_commands()
    commands['pytest'].append('tests/test_stringmol_retirement.py')
    commands['mypy'].extend([str(HERE/'retirement_workflow.py'), str(HERE/'analyze_retirement.py'), str(HERE/'retirement_material.py'), 'tests/test_stringmol_retirement.py'])
    return commands


def validation(root: Path) -> dict[str, Any]:
    checks = {}
    for name, args in validation_commands().items():
        proc = subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True)
        log = root/f'{name}.txt'
        log.write_bytes(proc.stdout + proc.stderr)
        require(proc.returncode == 0, f'B002 {name} failed: {log}')
        checks[name] = {'command': args, 'exit_status': 0, 'log': record(log)}
    return checks


def run_input(source: Path, root: Path, seed: int, condition: str) -> dict[str, Any]:
    require(condition in analyzer.ARMS and seed in [*analyzer.SEEDS, 202620999], 'B002 arm/seed')
    r = h1.run_input(source, root, seed, 'host')
    config = root/f'{condition}-{seed}.conf'
    return {**r, 'condition': condition, 'config': str(config),
            'command': [str(source/'release/stringmol'), '30', str(config)],
            'directory': str(root/'runs'/condition/str(seed)),
            'environment': environment(condition)}


def environment(policy: str | None, *, logging: bool = True) -> dict[str,str]:
    require(policy in (*analyzer.ARMS,None), 'factorial policy')
    schedule,disposition = policy.split('_') if policy else ('IMMEDIATE','RETAIN')
    return {**b1.environment(schedule,logging=logging),
        'STRINGMOL_SOURCE_RETENTION':'1' if policy else '0',
        'STRINGMOL_SOURCE_DISPOSITION':disposition,
        'STRINGMOL_RETIREMENT_LOG':'1' if logging else '0'}


def custom_config(r: dict[str, Any], source: Path) -> str:
    require(r['condition'] in analyzer.ARMS, 'scheduling arm')
    return render_config(StringmolControlConfig('host-only', r['seed'], 0, 0, mutation_rate=0), source/'config/ALXII.mtx')


def parse_config(raw: str, r: dict[str, Any], source: Path) -> None:
    require(raw == custom_config(r, source), 'strict zero-mutation config equality')
    panel_tools.parse_config(raw.replace('MUTATE 0\n','MUTATE 0.0002\n'), r['expected_initial'], r['seed'], source/'config/ALXII.mtx')


def directed_linkage(data: dict[str, Any], root: Path) -> dict[str, Any]:
    info = data['builds']['observer']; source = Path(info['source'])
    c.verify_release_objects(source,info['release_objects'])
    objects = {str(source/'release'/n):v for n,v in sorted(info['release_objects'].items()) if n != 'stringmol.o'}
    fixture = ROOT/'tests/stringmol_retirement_directed.cpp'
    args = ['g++','-std=c++11','-O2','-Wall','-Wl,--wrap=_Z11AgentUnbindP4s_ag', '-Wl,--wrap=__cxa_throw', '-Wl,--wrap=_Z16AgentFreeAndNullPP4s_ag','-I',str(source/'src'),str(fixture),*objects,'-o',str(root/'directed-test')]
    return {'command':args,'environment':ENV,'objects':objects,'fixture':record(fixture)}


PREPUBLICATION_FAULTS = ('validate','unlink','grid','refund','complete','unbind','append','publication')
POSTPUBLICATION_FAULTS = ('material','death','journal','free_before','free')
WRITE_FAULTS = tuple(f'{stream}_write_{mode}' for stream in ('material','death','source') for mode in ('error','short'))


def fault_evidence(root: Path) -> dict[str, Any]:
    """Check actual fatal child receipts and journal prefixes, not just a marker."""
    import csv
    phases = (*PREPUBLICATION_FAULTS,*POSTPUBLICATION_FAULTS,*WRITE_FAULTS)
    expected = {f'{phase}-{target}-{state}' for phase in phases for target in (0,1) for state in (0,1,2)}
    require({p.name for p in root.iterdir()} == expected, 'fault case coverage')
    for phase in phases:
        for target in (0,1):
            for state in (0,1,2):
                path = root/f'{phase}-{target}-{state}'
                require({p.name for p in path.iterdir()} == {'exit.json','witness.json','stderr.txt','material.csv','boundary.csv','source.csv'}, 'fault artifact set')
                receipt, witness = read(path/'exit.json'), read(path/'witness.json')
                before = phase in PREPUBLICATION_FAULTS
                writing = phase in WRITE_FAULTS
                short = phase.endswith('_short')
                require(receipt == {'exit_status':1}, 'fault must exit fatally')
                require(witness == {'phase':phase,'target':target,'list':state,'checkpoint_seen':int(before),
                    'rolled_back':before,'committed':int(not before),'frees':int(phase=='free'),
                    'write_attempts':int(writing),'partial_write_bytes':witness['partial_write_bytes'],
                    'logging':True,'no_fallback':True}, 'fault state witness')
                require(type(witness['partial_write_bytes']) is int and (witness['partial_write_bytes']>0 if short else witness['partial_write_bytes']==0), 'fault write witness')
                stderr = (path/'stderr.txt').read_bytes()
                require(b'journal write' in stderr if writing else
                    (f'SM-B002 rolled back before publication: {phase}\n'.encode() if before else
                     f'SM-B002 unevaluable after publication: {phase}\n'.encode()) in stderr, 'fault diagnostic')
                raw = {name:(path/f'{name}.csv').read_bytes() for name in ('material','boundary','source')}
                require(b'COMPLETE' not in raw['boundary'] and b'RETAIN' not in raw['source'], 'fatal completion/RETAIN fallback')
                rows = {}
                for name,columns in (('material',analyze_decay.JOURNAL_COLUMNS),('boundary',BOUNDARY_COLUMNS),('source',analyzer.SOURCE_COLUMNS)):
                    content = raw[name]
                    stream = 'death' if name=='boundary' else name
                    if short and phase.startswith(stream+'_write_'):
                        n = witness['partial_write_bytes']
                        require(n <= len(content) and not content.endswith(b'\n'), 'missing partial journal prefix')
                        content = content[:-n]
                    require(not content or content.endswith(b'\n'), 'unexpected journal truncation')
                    records = list(csv.reader(content.decode('ascii').splitlines()))
                    require(all(len(row)==len(columns) for row in records), 'fault journal columns')
                    rows[name] = [dict(zip(columns,row,strict=True)) for row in records]
                material_published = not before and not phase.startswith('material_write_')
                death_published = material_published and phase!='material' and not phase.startswith('death_write_')
                source_published = death_published and phase!='death' and not phase.startswith('source_write_')
                require([r['event'] for r in rows['material']] == ['CLEAVE']+(['RETIRE'] if material_published else []), 'fault material publication order')
                require([r['event'] for r in rows['boundary']] == ['BIRTH']+(['DEATH'] if death_published else []), 'fault boundary publication order')
                require(len(rows['source']) == int(source_published), 'fault source publication order')
                if material_published:
                    require(rows['material'][1]['before_ids']==str(1-target) and rows['material'][1]['after_ids']=='', 'fault retirement source')
                if death_published:
                    require(rows['boundary'][1]['id']==str(1-target) and rows['boundary'][1]['material_index']=='2' and rows['boundary'][1]['outcome']=='RETIRE', 'fault death link')
                if source_published:
                    require(rows['source'][0]['decision']=='RETIRE' and rows['source'][0]['committed']=='1' and rows['source'][0]['material_index']=='1', 'fault source link')
                # Even complete publication/free is not evaluable after fatal exit.
                try:
                    analyzer.analyze_run(path,[],policy='IMMEDIATE_RETIRE',exit_status=receipt['exit_status'])
                except ValueError as exc:
                    require(str(exc)=='SM-B002 fatal process; unevaluable', 'fault process gate ordering')
                else:
                    raise ValueError('fatal retirement accepted by analyzer')
    return {'cases':len(expected),'rolled_back':48,'publication_or_free_fatal':30,'journal_write_failures':36,
            'files':inventory(root)}


def directed(data: dict[str, Any], root: Path) -> dict[str, Any]:
    linkage = directed_linkage(data,root)
    command(linkage['command'],root)
    proc = subprocess.run([str(root/'directed-test')],cwd=root,env=ENV,capture_output=True)
    (root/'directed.stdout').write_bytes(proc.stdout); (root/'directed.stderr').write_bytes(proc.stderr)
    require(proc.returncode == 0 and b'SM-B002 directed gates passed' in proc.stdout, 'directed retirement fixture failed')
    return {**linkage,'exit_status':proc.returncode,'binary':record(root/'directed-test'),
            'stdout':record(root/'directed.stdout'),'stderr':record(root/'directed.stderr'),'faults':fault_evidence(root/'faults')}


def gate_cases() -> list[tuple[str,str,dict[str,str]]]:
    cases = []
    for schedule in ('IMMEDIATE','DELAY500'):
        native = b1.environment(schedule)
        cases.extend([(schedule+'-baseline','baseline',native),(schedule+'-absent','observer',native),
            (schedule+'-disabled','observer',{**native,'STRINGMOL_SOURCE_RETENTION':'0'})])
    for arm in analyzer.ARMS:
        cases.extend([(arm,'observer',environment(arm)),(arm+'-repeat','observer',environment(arm)),
                      (arm+'-off','observer',environment(arm,logging=False))])
    return cases


def rng_linkage(data: dict[str,Any], root: Path, variant: str) -> dict[str,Any]:
    info = data['builds'][variant]; source = Path(info['source'])
    c.verify_release_objects(source,info['release_objects'])
    objects = {str(source/'release'/n):v for n,v in sorted(info['release_objects'].items())}
    renamed = root/f'{variant}-native-main.o'
    fixture = ROOT/'tests/stringmol_scheduling_rng.cpp'
    # Rename only the exported main symbol in a COPY of the verified object.
    # All simulator code, including native main initialization/destruction, stays.
    copy_command = ['objcopy','--redefine-sym','main=sm_b001_native_main',str(source/'release/stringmol.o'),str(renamed)]
    link_command = ['g++','-std=c++11','-O2','-Wall','-I',str(source/'src'),str(fixture),str(renamed),
                    *[p for p in objects if Path(p).name != 'stringmol.o'],'-o',str(root/f'{variant}-rng')]
    return {'copy_command':copy_command,'command':link_command,'environment':ENV,
            'objects':objects,'fixture':record(fixture)}


def compare_final_rng(results: dict[str,Any]) -> None:
    for schedule in ('IMMEDIATE','DELAY500'):
        for suffix in ('-absent','-disabled'):
            c.parity(results[schedule+'-baseline'],results[schedule+suffix])
        c.parity(results[schedule+'-baseline'],results[schedule+'_RETAIN'],analyzer.LOGS)
    for arm in analyzer.ARMS:
        c.parity(results[arm],results[arm+'-repeat'])
        c.parity(results[arm+'-off'],results[arm],analyzer.LOGS | SCHEDULING_LOGS)


def validate_final_rng(path: Path) -> None:
    raw=path.read_bytes(); lines=raw.splitlines()
    require(len(lines) == 625 and raw == b'\n'.join(lines)+b'\n', 'final RNG complete canonical state')
    require(re.fullmatch(rb'MTI (0|[1-9][0-9]*)',lines[0]) is not None and int(lines[0][4:]) <= 624, 'final RNG cursor')
    require(all(re.fullmatch(rb'0|[1-9][0-9]*',line) is not None and int(line) < 2**32 for line in lines[1:]), 'final RNG word bounds')


def rng_gates(data: dict[str,Any], root: Path, config: Path, ordinary: dict[str,Any]) -> dict[str,Any]:
    root.mkdir(exist_ok=False)
    links = {}
    for variant in ('baseline','observer'):
        linkage = rng_linkage(data,root,variant)
        command(linkage['copy_command'],root); command(linkage['command'],root)
        links[variant] = {**linkage,'renamed_main':record(root/f'{variant}-native-main.o'),
                          'binary':record(root/f'{variant}-rng')}
    results = {}
    for name,variant,env in gate_cases():
        results[name] = c.execute(root/f'{variant}-rng',config,root/name,env)
        c.parity(ordinary[name],results[name],{'final_rng.txt'})
        validate_final_rng(root/name/'final_rng.txt')
    compare_final_rng(results)
    return {'links':links,'runs':results}


def verify_rng(data: dict[str,Any], root: Path, saved: dict[str,Any], ordinary: dict[str,Any]) -> None:
    require(set(saved['links']) == {'baseline','observer'} and set(saved['runs']) == {x[0] for x in gate_cases()}, 'final RNG case set')
    for variant in ('baseline','observer'):
        require(saved['links'][variant] == {**rng_linkage(data,root,variant),
                'renamed_main':record(root/f'{variant}-native-main.o'),'binary':record(root/f'{variant}-rng')}, 'final RNG release linkage changed')
    for name,_,_ in gate_cases():
        require(saved['runs'][name] == {'exit_status':0,'files':inventory(root/name)}, 'final RNG capture changed')
        c.parity(ordinary[name],saved['runs'][name],{'final_rng.txt'})
        validate_final_rng(root/name/'final_rng.txt')
    compare_final_rng(saved['runs'])


@lru_cache(maxsize=8)
def _gate_replay(directory: str, expected_json: str, policy: str, output_hash: str, implementation_hash: str) -> str:
    # Only process-local memoization of a complete independent replay, keyed by
    # every current output byte and implementation byte. Return serialized data
    # so callers cannot mutate the cached result. No disk cache authorizes gates.
    summary = (mutation_analyzer.analyze_run(Path(directory),json.loads(expected_json)) if policy == 'NATIVE' else
               analyzer.analyze_run(Path(directory),json.loads(expected_json),policy=policy))
    return json.dumps(summary,sort_keys=True)


def replay_gate(directory: Path, expected: list[dict[str,Any]], policy: str) -> dict[str,Any]:
    outputs = evidence_hash(inventory(directory))
    implementation = evidence_hash({str(p):record(p) for p in IMPLEMENTATION})
    result: dict[str,Any] = json.loads(_gate_replay(str(directory),json.dumps(expected,sort_keys=True),policy,outputs,implementation))
    return result


def compare_gates(root: Path, results: dict[str,Any], expected: list[dict[str,Any]]) -> dict[str,Any]:
    compare_final_rng(results)
    summaries = {}
    for arm in analyzer.ARMS:
        summaries[arm] = replay_gate(root/arm,expected,arm)
        require(set(results[arm]['files']) == analyzer.output_names(summaries[arm]['end_timestep']), 'retirement output names')
    return summaries


def focused_gates(build_path: Path, root: Path) -> Path:
    data = verify_build(build_path)
    root = root.resolve(); root.mkdir(parents=True,exist_ok=False)
    checks = validation(root)
    fixture = directed(data,root)
    (root/'scheduling-fixture').mkdir()
    scheduling_fixture = b1.directed(data,root/'scheduling-fixture')
    source = Path(data['builds']['observer']['source'])
    r = run_input(source,root,202620999,'IMMEDIATE_RETAIN'); config = root/'development.conf'
    config.write_text(custom_config(r,source)); config.chmod(0o444)
    results = {}
    for name,variant,env in gate_cases():
        results[name] = c.execute(Path(data['builds'][variant]['source'])/'release/stringmol',config,root/name,env)
    final_rng = rng_gates(data,root/'rng',config,results)
    summaries = compare_gates(root,results,r['expected_initial'])
    seal(root/'focused.json',{'passed':True,'build_record':record(build_path),'validation':checks,
        'directed':fixture,'scheduling_directed':scheduling_fixture,'runs':results,
        'config':record(config),'summaries':summaries,'final_rng':final_rng})
    verify_focused_gate(root/'focused.json',build_path)
    return root/'focused.json'


def verify_focused_gate(path: Path, build_path: Path) -> None:
    data = verify_build(build_path); gate = read(path); root = path.parent
    require(gate['passed'] is True and gate['build_record'] == record(build_path), 'focused gate provenance')
    sd=gate['scheduling_directed']; sr=root/'scheduling-fixture'
    require(all(sd[k] == v for k,v in b1.directed_linkage(data,sr).items()) and sd['exit_status'] == 0, 'patch0006 inherited scheduling linkage')
    for key,name in [('binary','directed-test'),('stdout','directed.stdout'),('stderr','directed.stderr')]:
        require(sd[key] == record(sr/name), 'patch0006 inherited scheduling fixture bytes')
    for name,args in validation_commands().items():
        require(gate['validation'][name] == {'command':args,'exit_status':0,'log':record(root/f'{name}.txt')}, 'validation changed')
    source = Path(data['builds']['observer']['source'])
    r = run_input(source,root,202620999,'IMMEDIATE_RETAIN'); config = root/'development.conf'
    require(config.read_text() == custom_config(r,source) and record(config) == gate['config'],'development config changed')
    parse_config(config.read_text(),r,source)
    require(set(gate['runs']) == {v[0] for v in gate_cases()},'development cases changed')
    for name,_,_ in gate_cases(): require(gate['runs'][name] == {'exit_status':0,'files':inventory(root/name)}, 'development outputs changed')
    verify_rng(data,root/'rng',gate['final_rng'],gate['runs'])
    require(compare_gates(root,gate['runs'],r['expected_initial']) == gate['summaries'],'boundary gate replay changed')
    d = gate['directed']
    require(d['faults'] == fault_evidence(root/'faults'), 'fault evidence changed')
    require(all(d[k] == v for k,v in directed_linkage(data,root).items()) and d['exit_status'] == 0,'directed linkage changed')
    for key,filename in [('binary','directed-test'),('stdout','directed.stdout'),('stderr','directed.stderr')]:
        require(d[key] == record(root/filename),'directed artifact changed')



def gates(build_path: Path, root: Path, inherited_gate: Path | None = None, mutation_gate: Path | None = None, focused_gate: Path | None = None) -> Path:
    data = verify_build(build_path)
    root = root.resolve(); root.mkdir(parents=True,exist_ok=False)
    inherited = inherited_gate.resolve() if inherited_gate else b1.gates(Path(data['inherited']),root/'inherited')
    b1.verify_gate(inherited,Path(data['inherited']))
    mutation_build = Path(read(Path(data['inherited']))['inherited'])
    mutation = mutation_gate.resolve() if mutation_gate else m1.gates(mutation_build,root/'mutation-suite')
    m1.verify_gate(mutation,mutation_build)
    focused = focused_gate.resolve() if focused_gate else focused_gates(build_path,root/'focused')
    verify_focused_gate(focused,build_path)
    seal(root/'gates.json',{'passed':True,'build_record':record(build_path),
        'inherited':str(inherited),'inherited_record':record(inherited),
        'mutation_suite':{'path':str(mutation),'record':record(mutation),'build':str(mutation_build)},
        'focused':str(focused),'focused_record':record(focused)})
    verify_gate(root/'gates.json',build_path)
    return root/'gates.json'


def verify_gate(path: Path, build_path: Path) -> None:
    data=verify_build(build_path); gate=read(path)
    inherited=Path(gate['inherited']); focused=Path(gate['focused'])
    require(gate['passed'] is True and gate['build_record'] == record(build_path) and
        gate['inherited_record'] == record(inherited) and gate['focused_record'] == record(focused), 'full gate provenance')
    b1.verify_gate(inherited,Path(data['inherited']))
    mutation=gate['mutation_suite']; mutation_build=Path(read(Path(data['inherited']))['inherited'])
    require(mutation['build'] == str(mutation_build) and mutation['record'] == record(Path(mutation['path'])), 'full inherited suite provenance')
    m1.verify_gate(Path(mutation['path']),mutation_build)
    verify_focused_gate(focused,build_path)


def authorized_inputs(path: Path, data: dict[str,Any]) -> set[Path]:
    expected = {path.parent/f'{arm}-{seed}.conf' for arm, seed in analyzer.MATRIX}
    require({Path(r['config']) for r in data['runs']} == expected,'authorized preparation config paths')
    return expected | {path,path.with_name('preparation.sha256.json')}


# This historical counter happens to equal a held-out seed. Classify only this
# exact hashed CSV/cell; retain the file in the audit, and never exempt a subtree.
COUNTER_PATH = 'sweeps/ac_p004_prospective_controlled_convergence/runs/p1_m16_n32768_s202614006_funcv1_prectrlv1/symbols.csv'
COUNTER_SHA256 = '95809444c406d449e5148b27dbe92ad146e4f36833360cde9c5b2e81bdd52f18'
COUNTER_HEADER = b'epoch,symbol,pool_count,initial_pool_count,withdrawals,returns,execution_blocked,mutation_blocked,friction_blocked,cross_a_to_b,cross_b_to_a'
COUNTER_ROW = b'88801,39,133570,130896,202625342,202628016,0,0,0,195052720,2628238'


def nonseed_counter(path: Path, raw: bytes, found: list[re.Match[bytes]]) -> dict[str, Any] | None:
    if str(path.relative_to(ROOT)) != COUNTER_PATH or c.digest(raw) != COUNTER_SHA256 or len(found) != 1:
        return None
    match = found[0]
    start = raw.rfind(b'\n', 0, match.start()) + 1
    end = raw.find(b'\n', match.end())
    if (raw.split(b'\n', 1)[0].rstrip(b'\r') != COUNTER_HEADER
            or raw[start:end].rstrip(b'\r') != COUNTER_ROW
            or match.start() - start != len(b'88801,39,133570,130896,202625342,')
            or match.group() != b'202628016'):
        return None
    config, manifest = path.with_name('config.json'), path.with_name('manifest.json')
    require(record(config)['sha256'] == '86e792e7d95382934ec751ba1eedf5bd99a9b1c3634b761c6d8d8fd4b41c4fa1' and record(manifest)['sha256'] == 'e88911210a0a5344c8a3012fddd8108c7597e58ba453c97d6eee68d7a56a009d', 'historical counter provenance bytes changed')
    require(read(manifest)['artifact_checksums']['symbols.csv'] == COUNTER_SHA256, 'historical counter artifact seal')
    require(read(config)['seed'] == 202614006 and read(manifest)['config']['seed'] == 202614006,
            'historical counter run seed changed')
    return {'path': COUNTER_PATH, 'record': record(path), 'offset': match.start(),
            'epoch': 88801, 'symbol': 39, 'field': 'returns', 'value': 202628016,
            'run_seed': 202614006, 'config': record(config), 'manifest': record(manifest)}


def unseen_audit(root: Path, *, authorized_files: set[Path] | None = None) -> dict[str,Any]:
    """Audit all historical run/sweep inputs; exempt only exact authorized inputs.

    No directory subtree is exempt: an execution artifact inside the authorized
    preparation is still evidence of prior use. The caller verifies the complete
    preparation before passing its 82 immutable input paths.
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
    pattern = re.compile(rb'2026280[01][0-9](?![0-9])')
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
                counter = nonseed_counter(p,raw,found)
                if counter is None: matches.append(str(p))
                else: classified.append(counter)
    require(not matches, 'unseen seed prior input/use: '+str(matches))
    return {'scope':['runs','sweeps'],'authorized_preparation':str(root),'excluded_files':excluded,'nonseed_counter_matches':classified,'checked_files':len(checked),'inventory':checked,'directories':directories,'matches':matches,'seeds':analyzer.SEEDS, 'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat()}


def verify_audit(audit: dict[str,Any], path: Path, data: dict[str,Any], *, preparation: bool = False) -> None:
    require(audit['scope'] == ['runs','sweeps'] and audit['seeds'] == analyzer.SEEDS and audit['matches'] == [],'freshness audit scope/results')
    require(audit['authorized_preparation'] == str(path.parent) and audit['excluded_files'] == ({} if preparation else {str(p):record(p) for p in sorted(authorized_inputs(path,data))}),'freshness audit exclusions')
    require(audit['checked_files'] == len(audit['inventory']),'freshness audit inventory count')
    expected_counter = []
    if COUNTER_PATH in audit['inventory']:
        p = ROOT/COUNTER_PATH; raw = p.read_bytes()
        found = [m for m in re.finditer(rb'2026280[01][0-9](?![0-9])',raw) if m.start() == 0 or raw[m.start()-1] not in b'0123456789.']
        item = nonseed_counter(p,raw,found)
        require(item is not None, 'historical counter classification changed')
        expected_counter.append(item)
    require(audit['nonseed_counter_matches'] == expected_counter, 'counter audit evidence changed')
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
    seal(path,{'protocol':'SM-B002','protocol_pin':protocol_pin(),'workers':6,'status':'prepared-only; commit and push required before launch','build_manifest':str(build_path),'build_record':record(build_path),'build':data,'gates':str(gate_path),'gate_record':record(gate_path),'implementation':{str(p):record(p) for p in IMPLEMENTATION},'schema':serialization(),'repository_state':source_state(ROOT),'launch_target':remote_target(),'unseen_audit':audit,'runs':entries})
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
    require(data['protocol'] == 'SM-B002' and data['protocol_pin'] == protocol_pin() and data['workers'] == 6,'prepared protocol')
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
    reference=data['runs'][0]
    normalized=Path(reference['config']).read_text().replace(f"RANDSEED {reference['seed']}\n",'RANDSEED FROZEN\n')
    for r in data['runs']:
        require(r['expected_initial'] == reference['expected_initial'] and r['initial_material'] == reference['initial_material'], 'all-80 initial bytes/matter/positions differ')
        require(Path(r['config']).read_text().replace(f"RANDSEED {r['seed']}\n",'RANDSEED FROZEN\n') == normalized, 'all-80 chemistry/horizon differ')
    for offset in range(0,80,4):
        block = data['runs'][offset:offset+4]
        for r in block[1:]:
            require(r['initial_material'] == block[0]['initial_material'] and r['expected_initial'] == block[0]['expected_initial'], 'paired initial material/identity inequality')
            require(Path(r['config']).read_bytes() == Path(block[0]['config']).read_bytes(), 'paired config inequality')
            require({k:v for k,v in r['environment'].items() if k not in ('STRINGMOL_SCHEDULING_POLICY','STRINGMOL_SOURCE_DISPOSITION')} ==
                    {k:v for k,v in block[0]['environment'].items() if k not in ('STRINGMOL_SCHEDULING_POLICY','STRINGMOL_SOURCE_DISPOSITION')}, 'sole scheduling treatment difference')
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
    # audit passed. Exempt only this verified manifest, digest, and 80 configs.
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
    parser.add_argument('action', choices=('build', 'focused', 'gates', 'prepare', 'run'))
    for name in ('root', 'build', 'gates', 'manifest', 'lineage-build', 'scheduling-build', 'inherited-gates', 'mutation-gates', 'focused-gates'):
        parser.add_argument('--'+name, type=Path)
    parser.add_argument('--upstream', type=Path, default=HERE/'vendor/stringmol')
    args = parser.parse_args()
    if args.action == 'build' and args.root and args.lineage_build:
        print(build(args.root, args.upstream, args.lineage_build.resolve(),args.scheduling_build))
    elif args.action == 'focused' and args.root and args.build:
        print(focused_gates(args.build.resolve(),args.root))
    elif args.action == 'gates' and args.root and args.build:
        print(gates(args.build.resolve(), args.root,args.inherited_gates,args.mutation_gates,args.focused_gates))
    elif args.action == 'prepare' and args.root and args.build and args.gates:
        print(prepare(args.build.resolve(), args.gates.resolve(), args.root))
    elif args.action == 'run' and args.manifest:
        run_matrix(args.manifest.resolve())
    else:
        parser.error('missing required paths')


if __name__ == '__main__':
    main()
