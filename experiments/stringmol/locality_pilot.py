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

CONTROL=Path('/tmp/sm/xl-e')
RAW=Path('/run/media/jojo/Elements/bio-sim-results/sm-xl001-exploration-v1')
SOURCE=CONTROL/'n'
SEED=202620999
ARMS={'GG':(0,0),'LG':(1,0),'GL':(0,1),'LL':(1,1)}
PYTHON='/var/home/jojo/bio-sim-proto/.venv/bin/python'
OBS={'lineage_events001.csv','lineage_snapshots001.csv','conservation002.csv','conservation_buffers002.csv',
     'material_events002.csv','scheduling_events001.csv','source_events006.csv','xl_vm_end.csv','xl_rng_end.txt'}


def record(path):
    path=Path(path)
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return {'sha256':h.hexdigest(),'bytes':path.stat().st_size}


def inventory(root):
    return {str(p.relative_to(root)):record(p) for p in sorted(Path(root).rglob('*')) if p.is_file() and not p.is_symlink()}


def save(path,data):
    with Path(path).open('x') as f:json.dump(data,f,sort_keys=True,indent=2);f.write('\n')


def preflight():
    mounts=Path('/proc/mounts').read_text()
    assert ' /tmp/sm ' in mounts and '/run/media/jojo/Elements/bio-sim-results/stringmol-posix.ext4' in mounts
    assert ' /run/media/jojo/Elements ' in mounts
    assert shutil.disk_usage(CONTROL).free >= 5*1024**3
    assert shutil.disk_usage(RAW.parent).free >= 10*1024**3
    # Every launch also enforces track-specific cumulative byte budgets.
    posix=sum(p.stat().st_size for p in CONTROL.rglob('*') if p.is_file() and not p.is_symlink())
    raw=sum(p.stat().st_size for p in RAW.rglob('*') if p.is_file() and not p.is_symlink()) if RAW.exists() else 0
    assert posix < 4*1024**3 and raw < 25*1024**3


def locality_environment(logging):
    """Explicit own log controls; inherited helper does not forward all flags.

    This correction is for a separately authorized future whole-matrix recovery.
    Existing sealed preparations and twelve retained executions are unchanged.
    """
    env=environment('IMMEDIATE_RETAIN',logging=logging)
    env['STRINGMOL_CONSERVATION_LOG']='1' if logging else '0'
    if not logging:
        env.pop('STRINGMOL_LINEAGE_LOG',None)
    return env


def prepare():
    preflight()
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='explore/sm-xl001'
    assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip(), 'commit before prepare'
    RAW.mkdir(exist_ok=False)
    jobs=[]
    for arm,(interaction,placement) in ARMS.items():
        config=CONTROL/f'{arm}.conf'
        raw=render_config(StringmolControlConfig('host-only',SEED,interaction,placement,mutation_rate=0),SOURCE/'config/ALXII.mtx')
        assert len(str(config).encode())<80 and len(str(SOURCE/'config/ALXII.mtx').encode())<80
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


def run():
    data=json.loads((CONTROL/'preparation.json').read_text())
    assert record(CONTROL/'preparation.json')==json.loads((CONTROL/'preparation.sha256.json').read_text())
    assert record(SOURCE/'release/stringmol')==data['binary'] and record(SOURCE/'config/ALXII.mtx')==data['matrix']
    assert inventory(SOURCE/'src')==data['source']
    assert all(record(p)==r for p,r in data['implementation'].items())
    assert all(record(CONTROL/n)==r for n,r in data['gates'].items())
    assert len(data['jobs'])==12
    assert not any(Path(j['directory']).exists() for j in data['jobs'])
    save(CONTROL/'launch.json',{'pid':os.getpid(),'time':time.time(),'preparation':record(CONTROL/'preparation.json')})
    for index,j in enumerate(data['jobs']):
        preflight(); assert record(j['config'])==j['config_record']
        directory=Path(j['directory']);directory.mkdir()
        started=time.time()
        with (directory/'stdout.txt').open('xb') as out,(directory/'stderr.txt').open('xb') as err:
            try:
                p=subprocess.run(j['command'],cwd=directory,env=j['environment'],stdout=out,stderr=err,timeout=600)
                code=p.returncode
            except subprocess.TimeoutExpired:code='TIMEOUT'
        save(RAW/f"{j['arm']}-{j['kind']}.receipt.json",{'command':j['command'],'environment':j['environment'],'exit_code':code,'seconds':time.time()-started,'inventory':inventory(directory)})
        (CONTROL/'STATUS.md').write_text(f"# SM-XL001\n{index+1}/12 native executions completed; last {j['arm']}-{j['kind']} exit={code}. Controller PID {os.getpid()} actively executing frozen matrix. No interpretation yet.\n")
    save(CONTROL/'native-complete.json',{'executions':12,'pid':os.getpid(),'time':time.time()})


def analyze_one(arm,kind,output):
    from experiments.stringmol.locality_replay import replay
    cells,_=inoculum()
    initial=initial_material([{'id':i,'sequence_hex':HOST.encode().hex()} for i in range(140)],'histogram',0)
    initial['waste']=[0]*33
    result=replay(RAW/f'{arm}-{kind}',initial,dict(enumerate(cells)),SEED,SOURCE/'config/ALXII.mtx',*ARMS[arm])
    save(output,result)


def analyze():
    reports={}
    for arm in ARMS:
        receipts={kind:json.loads((RAW/f'{arm}-{kind}.receipt.json').read_text()) for kind in ('observed','repeat','off')}
        assert all(r['exit_code']==0 for r in receipts.values()), 'native failure'
        for kind,r in receipts.items():assert inventory(RAW/f'{arm}-{kind}')==r['inventory']
        on,repeat,off=(receipts[k]['inventory'] for k in ('observed','repeat','off'))
        assert on==repeat, 'deterministic repeat byte mismatch'
        assert {k:v for k,v in on.items() if k not in OBS}==off, 'observer isolation mismatch'
        assert set(on)-set(off)==OBS, 'unexpected observer file set'
        reports[arm]={'deterministic_repeat':True,'observer_isolation':True,'analyses':[]}
        for kind in ('observed','repeat'):
            output=CONTROL/f'{arm}-{kind}-analysis.json'
            log=CONTROL/f'{arm}-{kind}-analysis.log'
            command=[PYTHON,'-m','experiments.stringmol.locality_pilot','one',arm,kind,str(output)]
            with log.open('xb') as f:
                try:p=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=1800);code=p.returncode
                except subprocess.TimeoutExpired:code='TIMEOUT'
            reports[arm]['analyses'].append({'exit_code':code,'log':record(log),'output':record(output) if output.exists() else None})
        save(CONTROL/f'{arm}-verification.json',reports[arm])
    save(CONTROL/'verification.json',reports)
    assert all(all(a['exit_code']==0 for a in r['analyses']) for r in reports.values()), 'replay failure; retain and diagnose, no population interpretation'
    results={}
    for arm in ARMS:
        assert (CONTROL/f'{arm}-observed-analysis.json').read_bytes()==(CONTROL/f'{arm}-repeat-analysis.json').read_bytes()
        results[arm]=json.loads((CONTROL/f'{arm}-observed-analysis.json').read_text())
    gg=results['GG'];pop4900=next(c['population'] for c in gg['checkpoints'] if c['tick']==4900)
    save(CONTROL/'results.json',{'integrity':True,'positive_control':gg['placed']>=100 and pop4900>0,'independent_seeds_per_cell':1,'results':results})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run','analyze','one']);parser.add_argument('args',nargs='*');args=parser.parse_args()
    if args.action=='one':analyze_one(*args.args)
    else:globals()[args.action]()
