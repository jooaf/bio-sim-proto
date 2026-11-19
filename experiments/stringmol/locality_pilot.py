"""Bounded SM-XL001 development-only controller. No retry/resume/seed search."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from experiments.stringmol.configure_control import HOST, inoculum, StringmolControlConfig,render_config
from experiments.stringmol.analyze_conservation import initial_material
from experiments.stringmol.retirement_workflow import environment
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.locality_process import FileRecord, execute
from typing import TypedDict, cast


class Job(TypedDict):
    arm: str
    interaction: int
    placement: int
    kind: str
    config: str
    config_record: FileRecord
    directory: str
    environment: dict[str, str]
    command: list[str]


class Preparation(TypedDict):
    jobs: list[Job]
    binary: FileRecord
    matrix: FileRecord
    source: dict[str, FileRecord]
    implementation: dict[str, FileRecord]
    gates: dict[str, FileRecord]


class NativeReceipt(TypedDict):
    exit_code: int | str
    inventory: dict[str, FileRecord]


class Analysis(TypedDict):
    exit_code: int | str
    log: FileRecord
    output: FileRecord | None


class Verification(TypedDict):
    deterministic_repeat: bool
    observer_isolation: bool
    analyses: list[Analysis]

CONTROL=Path('/tmp/sm/xl-e')
RAW=Path('/run/media/jojo/Elements/bio-sim-results/sm-xl001-exploration-v1')
SOURCE=CONTROL/'n'
SEED=202620999
ARMS={'GG':(0,0),'LG':(1,0),'GL':(0,1),'LL':(1,1)}
PYTHON='/var/home/jojo/bio-sim-proto/.venv/bin/python'
OBS={'lineage_events001.csv','lineage_snapshots001.csv','conservation002.csv','conservation_buffers002.csv',
     'material_events002.csv','scheduling_events001.csv','source_events006.csv','xl_vm_end.csv','xl_rng_end.txt'}


def record(path: str | Path) -> FileRecord:
    path=Path(path)
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return {'sha256':h.hexdigest(),'bytes':path.stat().st_size}


def inventory(root: str | Path) -> dict[str, FileRecord]:
    root = Path(root)
    return {str(p.relative_to(root)):record(p) for p in sorted(Path(root).rglob('*')) if p.is_file() and not p.is_symlink()}


def save(path: str | Path, data: object) -> None:
    with Path(path).open('x') as f:json.dump(data,f,sort_keys=True,indent=2);f.write('\n')


def preflight() -> None:
    mounts=Path('/proc/mounts').read_text()
    require(' /tmp/sm ' in mounts and '/run/media/jojo/Elements/bio-sim-results/stringmol-posix.ext4' in mounts, 'safety/provenance check failed')
    require(' /run/media/jojo/Elements ' in mounts, 'safety/provenance check failed')
    require(shutil.disk_usage(CONTROL).free >= 5*1024**3, 'safety/provenance check failed')
    require(shutil.disk_usage(RAW.parent).free >= 10*1024**3, 'safety/provenance check failed')
    # Every launch also enforces track-specific cumulative byte budgets.
    posix=sum(p.stat().st_size for p in CONTROL.rglob('*') if p.is_file() and not p.is_symlink())
    raw=sum(p.stat().st_size for p in RAW.rglob('*') if p.is_file() and not p.is_symlink()) if RAW.exists() else 0
    require(posix < 4*1024**3 and raw < 25*1024**3, 'safety/provenance check failed')


def locality_environment(logging: bool) -> dict[str, str]:
    """Explicit own log controls; inherited helper does not forward all flags.

    This correction is for a separately authorized future whole-matrix recovery.
    Existing sealed preparations and twelve retained executions are unchanged.
    """
    env=environment('IMMEDIATE_RETAIN',logging=logging)
    env['STRINGMOL_CONSERVATION_LOG']='1' if logging else '0'
    if not logging:
        env.pop('STRINGMOL_LINEAGE_LOG',None)
    return env


def prepare() -> None:
    preflight()
    require(subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='explore/sm-xl001', 'safety/provenance check failed')
    require(not subprocess.check_output(['git','status','--porcelain'],text=True).strip(), 'commit before prepare')
    RAW.mkdir(exist_ok=False)
    jobs: list[Job]=[]
    for arm,(interaction,placement) in ARMS.items():
        config=CONTROL/f'{arm}.conf'
        raw=render_config(StringmolControlConfig('host-only',SEED,interaction,placement,mutation_rate=0),SOURCE/'config/ALXII.mtx')
        require(len(str(config).encode())<80 and len(str(SOURCE/'config/ALXII.mtx').encode())<80, 'safety/provenance check failed')
        with config.open('x') as f:f.write(raw)
        config.chmod(0o444)
        for kind in ('observed','repeat','off'):
            env=locality_environment(kind!='off')
            jobs.append(dict(arm=arm,interaction=interaction,placement=placement,kind=kind,config=str(config),config_record=record(config),
                             directory=str(RAW/f'{arm}-{kind}'),environment=env,command=[str(SOURCE/'release/stringmol'),'30',str(config)]))
    manifest=dict(seed=SEED,horizon=5000,jobs=jobs,commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                  binary=record(SOURCE/'release/stringmol'),matrix=record(SOURCE/'config/ALXII.mtx'),source=inventory(SOURCE/'src'),
                  implementation={p:record(p) for p in subprocess.check_output(['git','ls-files','experiments/stringmol','tests/test_stringmol_locality.py','tests/stringmol_locality_directed.cpp','reports/sm_xl001_plan.md'],text=True).splitlines()},
                  gates={n:record(CONTROL/n) for n in ('pytest2.log','native-fixtures-v4.log','build-v2.log')})
    save(CONTROL/'preparation.json',manifest)
    (CONTROL/'preparation.json').chmod(0o444)
    save(CONTROL/'preparation.sha256.json',record(CONTROL/'preparation.json'))


def validate_preparation(data: object) -> None:
    """Reject malformed and redirected jobs before any execution reservation."""
    if not isinstance(data, dict) or not isinstance(data.get('jobs'), list):
        raise ValueError('preparation/jobs schema')
    jobs = data['jobs']
    if len(jobs) != 12:
        raise ValueError('whole matrix required')
    expected = {(arm, kind) for arm in ARMS for kind in ('observed', 'repeat', 'off')}
    seen: set[tuple[str, str]] = set()
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError('job schema')
        arm, kind = job.get('arm'), job.get('kind')
        if not isinstance(arm, str) or not isinstance(kind, str) or (arm, kind) not in expected or (arm, kind) in seen:
            raise ValueError('job identity')
        seen.add((arm, kind))
        if job.get('command') != [str(SOURCE/'release/stringmol'), '30', str(CONTROL/f'{arm}.conf')]:
            raise ValueError('job command binding')
        if job.get('directory') != str(RAW/f'{arm}-{kind}') or job.get('config') != str(CONTROL/f'{arm}.conf'):
            raise ValueError('job path binding')
        if job.get('environment') != locality_environment(kind != 'off'):
            raise ValueError('logger/environment binding; historical failed off preparations cannot be relaunched')
        if (job.get('interaction'), job.get('placement')) != ARMS[arm]:
            raise ValueError('geometry binding')


def run() -> None:
    data=cast(Preparation, json.loads((CONTROL/'preparation.json').read_text()))
    validate_preparation(data)
    require(record(CONTROL/'preparation.json')==json.loads((CONTROL/'preparation.sha256.json').read_text()), 'safety/provenance check failed')
    require(record(SOURCE/'release/stringmol')==data['binary'] and record(SOURCE/'config/ALXII.mtx')==data['matrix'], 'safety/provenance check failed')
    require(inventory(SOURCE/'src')==data['source'], 'safety/provenance check failed')
    require(all(record(p)==r for p,r in data['implementation'].items()), 'safety/provenance check failed')
    require(all(record(CONTROL/n)==r for n,r in data['gates'].items()), 'safety/provenance check failed')
    require(len(data['jobs'])==12, 'safety/provenance check failed')
    require(not any(Path(j['directory']).exists() for j in data['jobs']), 'safety/provenance check failed')
    save(CONTROL/'launch.json',{'pid':os.getpid(),'time':time.time(),'preparation':record(CONTROL/'preparation.json')})
    for index,j in enumerate(data['jobs']):
        preflight(); require(record(j['config'])==j['config_record'], 'safety/provenance check failed')
        directory=Path(j['directory']);directory.mkdir()
        result = execute(j['command'], cwd=directory, environment=j['environment'],
            receipt=RAW/f"{j['arm']}-{j['kind']}.receipt.json", stdout=directory/'stdout.txt',
            stderr=directory/'stderr.txt', timeout=600, output_root=directory)
        code = result['exit_code']
        require(code == 0, 'native failure; receipt retained; no retry')
        (CONTROL/'STATUS.md').write_text(f"# SM-XL001\n{index+1}/12 native executions completed; last {j['arm']}-{j['kind']} exit={code}. Controller PID {os.getpid()} actively executing frozen matrix. No interpretation yet.\n")
    save(CONTROL/'native-complete.json',{'executions':12,'pid':os.getpid(),'time':time.time()})


def analyze_one(arm: str, kind: str, output: str | Path) -> None:
    require(arm in ARMS and kind in ('observed', 'repeat'), 'unqualified replay input')
    from experiments.stringmol.locality_replay import replay
    cells,_=inoculum()
    initial=initial_material([{'id':i,'sequence_hex':HOST.encode().hex()} for i in range(140)],'histogram',0)
    initial['waste']=[0]*33
    result=replay(RAW/f'{arm}-{kind}',initial,dict(enumerate(cells)),SEED,SOURCE/'config/ALXII.mtx',*ARMS[arm])
    save(output,result)


def analyze() -> None:
    reports: dict[str, Verification]={}
    for arm in ARMS:
        receipts={kind:cast(NativeReceipt, json.loads((RAW/f'{arm}-{kind}.receipt.json').read_text())) for kind in ('observed','repeat','off')}
        require(all(r['exit_code']==0 for r in receipts.values()), 'native failure')
        for kind,r in receipts.items():require(inventory(RAW/f'{arm}-{kind}')==r['inventory'], 'safety/provenance check failed')
        on,repeat,off=(receipts[k]['inventory'] for k in ('observed','repeat','off'))
        require(on==repeat, 'deterministic repeat byte mismatch')
        require({k:v for k,v in on.items() if k not in OBS}==off, 'observer isolation mismatch')
        require(set(on)-set(off)==OBS, 'unexpected observer file set')
        reports[arm]={'deterministic_repeat':True,'observer_isolation':True,'analyses':[]}
        for kind in ('observed','repeat'):
            output=CONTROL/f'{arm}-{kind}-analysis.json'
            log=CONTROL/f'{arm}-{kind}-analysis.log'
            command=[PYTHON,'-m','experiments.stringmol.locality_pilot','one',arm,kind,str(output)]
            process = execute(command, cwd=Path.cwd(), environment=dict(os.environ),
                receipt=CONTROL/f'{arm}-{kind}-analysis.process.json', stdout=log,
                stderr=CONTROL/f'{arm}-{kind}-analysis.stderr', timeout=1800, output_root=CONTROL)
            code = process['exit_code']
            reports[arm]['analyses'].append({'exit_code':code,'log':record(log),'output':record(output) if output.exists() else None})
        save(CONTROL/f'{arm}-verification.json',reports[arm])
    save(CONTROL/'verification.json',reports)
    require(all(all(a['exit_code']==0 for a in r['analyses']) for r in reports.values()), 'replay failure; retain and diagnose, no population interpretation')
    from experiments.stringmol.locality_models import ReplayResult
    results: dict[str, ReplayResult]={}
    for arm in ARMS:
        require((CONTROL/f'{arm}-observed-analysis.json').read_bytes()==(CONTROL/f'{arm}-repeat-analysis.json').read_bytes(), 'safety/provenance check failed')
        results[arm]=cast(ReplayResult, json.loads((CONTROL/f'{arm}-observed-analysis.json').read_text()))
    gg=results['GG'];pop4900=next(c['population'] for c in gg['checkpoints'] if c['tick']==4900)
    save(CONTROL/'results.json',{'integrity':True,'positive_control':gg['placed']>=100 and pop4900>0,'independent_seeds_per_cell':1,'results':results})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run','analyze','one']);parser.add_argument('args',nargs='*');args=parser.parse_args()
    if args.action=='one':
        if len(args.args) != 3:
            parser.error('one requires ARM KIND OUTPUT')
        analyze_one(args.args[0], args.args[1], args.args[2])
    else:
        if args.args:
            parser.error('unexpected arguments')
        {'prepare': prepare, 'run': run, 'analyze': analyze}[args.action]()
