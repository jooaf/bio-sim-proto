"""SM-XP001 frozen 12-execution pilot and changed-inoculum replay."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
from typing import NotRequired, TypedDict
import subprocess
import sys
from experiments.stringmol import xp001 as x
from experiments.stringmol import xp001_provenance as provenance
from experiments.stringmol.xp001_safety import Case, Founder, Snapshot, object_from, require

from experiments.stringmol.configure_control import HOST, StringmolControlConfig, render_config, inoculum
from experiments.stringmol.analyze_retirement import BoundaryReplay, SourceReplay, verify_source_transactions
from experiments.stringmol.analyze_scheduling import boundary_rows
from experiments.stringmol.analyze_conservation import initial_material

class Execution(TypedDict):
    case: Case
    returncode: int | None
    analysis_returncode: NotRequired[int | None]


CONTROL = x.EVIDENCE/'p001'
POP = x.RAW/'population-v1'
ENV = {'STRINGMOL_CONSERVATION':'1', 'STRINGMOL_POOL_MODE':'histogram', 'STRINGMOL_POOL_AMOUNT':'0',
       'STRINGMOL_DECAY_DESTINATION':'recycle', 'STRINGMOL_SCHEDULING':'1', 'STRINGMOL_SCHEDULING_POLICY':'IMMEDIATE',
       'STRINGMOL_SOURCE_RETENTION':'1', 'STRINGMOL_SOURCE_DISPOSITION':'RETAIN'}

def expected(count: int, mixed: bool) -> list[Founder]:
    return [{'id': i, 'x': cell[0], 'y': cell[1], 'label': ord('Q'),
             'sequence_hex': ('B' if mixed and i%2 else HOST).encode().hex().upper()}
            for i, cell in enumerate(inoculum()[0][:count])]

def analyze(directory: Path, founders: list[Founder]) -> dict[str, object]:
    # Independent initial buffers come from frozen inputs, never producer output.
    initial = initial_material([dict(f) for f in founders], 'histogram', 0)
    events = x.rows(directory/'lineage_events001.csv')
    init = [r for r in events if r['event']=='INIT']
    require(len(init)==len(founders), 'initial founder count')
    by_id = {r['id']: r for r in founders}
    require(len(by_id)==len(founders) and {int(r['child_id']) for r in init}==set(by_id), 'initial IDs')
    for r in init:
        f=by_id[int(r['child_id'])]
        require((int(r['x']), int(r['y']), r['child_sequence_hex'])==(f['x'],f['y'],f['sequence_hex']), 'initial founder mismatch')
    ends = [r for r in events if r['event']=='END']; require(len(ends)==1, 'one END required')
    end = int(ends[0]['timestep'])
    material = x.rows(directory/'material_events002.csv')
    boundary = BoundaryReplay(initial, material, 'IMMEDIATE', 5000, [int(r['child_id']) for r in init], 'RETAIN')
    for r in boundary_rows(directory/'scheduling_events001.csv'):
        boundary.step(r)
    boundary.summary(end)
    # A second traversal cross-checks every aggregate and full-buffer checkpoint,
    # independent of the boundary stream's dispatch/link traversal.
    source = SourceReplay(initial)
    buffers: dict[tuple[int,str],dict[int,bytes]] = {}
    for r in x.rows(directory/'conservation_buffers002.csv'):
        key=(int(r['tick']),r['event']); target=buffers.setdefault(key,{})
        idx=int(r['id']); require(idx not in target, 'duplicate buffer ID')
        target[idx]=bytes.fromhex(r['full_buffer_hex'])
    lineage_snapshots: dict[int,dict[int,bytes]] = {}
    for r in x.rows(directory/'lineage_snapshots001.csv'):
        target=lineage_snapshots.setdefault(int(r['tick']),{})
        idx=int(r['id']); require(idx not in target, 'duplicate lineage ID')
        target[idx]=bytes.fromhex(r['sequence_hex'])
    aggregates=x.rows(directory/'conservation002.csv'); cursor=0
    snapshots: list[Snapshot] = []
    for r in aggregates:
        tick=int(r['tick'])
        while cursor<len(material) and int(material[cursor]['tick'])<tick:
            source.step(material[cursor]); cursor+=1
        source.material.checkpoint(r)
        key=(tick,r['event'])
        require(source.material.buffers==buffers.get(key,{}), 'full-buffer checkpoint mismatch')
        visible={i:b.split(b'\0',1)[0] for i,b in source.material.buffers.items()}
        if r['event']=='CHECKPOINT':
            require(visible==lineage_snapshots.get(tick,{}), 'visible checkpoint mismatch')
        snapshots.append({'tick':tick, 'event':r['event'], 'total':len(visible), 'host':sum(b==HOST.encode() for b in visible.values())})
    require(cursor==len(material) and source.material.buffers==boundary.source.material.buffers, 'material traversal mismatch')
    require(source.edges==boundary.source.edges, 'edge traversal mismatch')
    births=[r for r in events if r['event']=='BIRTH']; require(len(births)==len(source.edges), 'birth count mismatch')
    for row, edge in zip(births,source.edges,strict=True):
        child=int(row['child_id'])
        require(child==edge['child'] and int(row['timestep'])==edge['tick'], 'birth edge mismatch')
        require(bytes.fromhex(row['child_sequence_hex'])==source.birth_buffers[child].split(b'\0',1)[0], 'birth sequence mismatch')
    require(int(ends[0]['population'])==len(source.material.buffers), 'end population mismatch')
    transaction = verify_source_transactions(boundary,x.rows(directory/'source_events006.csv'),events)
    counts: Counter[str] = Counter(); bound=0
    for r in boundary_rows(directory/'scheduling_events001.csv'):
        counts[r['event']]+=1
        bound+=r['event']=='ENCOUNTER' and r['outcome']=='BOUND'
    return {'integrity':True,'end_tick':end, 'final_population':len(source.material.buffers),
            'final_host':snapshots[-1]['host'], 'late_min_host':min((s['host'] for s in snapshots if 4000<=s['tick']<=4900),default=0),
            'encounters':counts['ENCOUNTER'],'bound_encounters':bound,'dispatches':counts['DISPATCH'],
            'successful_cleavages':len(source.edges),
            'exact_host_children':sum(bytes.fromhex(r['child_sequence_hex'])==HOST.encode() for r in births),
            'transfer':source.transfer_summary(), 'source_transactions':transaction, 'snapshots':snapshots}

def freeze() -> None:
    x.preflight()
    gate=json.loads((x.RAW/'reactions-v2/gate.json').read_text())
    require(gate['population_authorized_by_reaction_gate'] is True, 'reaction gate failed')
    CONTROL.mkdir(); POP.mkdir()
    native=x.EVIDENCE/'native-v2'
    matrix: list[Case] = []
    cases=[(count,mixed,seed,0,1) for count in [70,140] for mixed in [False,True] for seed in [1,2]]
    cases += [(140,False,s,1,1) for s in [1,2]]
    cases += [(140,m,1,0,0) for m in [False,True]]
    for index,(count,mixed,seed,repeat,observed) in enumerate(cases):
        founders=expected(count,mixed)
        raw=render_config(StringmolControlConfig('host-only',seed,0,0,mutation_rate=0),native/'ALXII.mtx')
        header=raw.split('AGENT ',1)[0].replace('NUMAGENTS 140',f'NUMAGENTS {count}')
        raw=header+''.join(f"AGENT {bytes.fromhex(f['sequence_hex']).decode()} 1 Q\nGRIDPOS {f['x']} {f['y']}\n" for f in founders)
        previous=next((r for r in matrix if (r['count'],r['mixed'],r['seed'])==(count,mixed,seed)),None)
        config=Path(previous['config']) if previous else CONTROL/f'{index:02}.conf'
        if not previous:
            config.write_text(raw); config.chmod(0o444)
        require(config.read_text()==raw, 'rendered config mismatch')
        environment={**ENV, **{k:str(observed) for k in ['STRINGMOL_LINEAGE_LOG','STRINGMOL_CONSERVATION_LOG','STRINGMOL_SCHEDULING_LOG','STRINGMOL_RETIREMENT_LOG']}}
        matrix.append({'index':index,'count':count,'mixed':mixed,'seed':seed,'repeat':repeat,'observed':observed,
                       'founders':founders,'config':str(config),'config_sha256':x.digest(config),'environment':environment})
    require(len(matrix)==12, 'exactly twelve cases required')
    x.save(CONTROL/'freeze.json',{'matrix':matrix, 'binary':str(native/'objects/stringmol'),
        'binary_sha256':x.digest(native/'objects/stringmol'),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=x.ROOT,text=True).strip(),
        'plan_sha256':x.digest(x.ROOT/'reports/sm_xp001_development_plan.md'),
        'recovery_plan_sha256':x.digest(x.ROOT/'reports/sm_xp001_reaction_recovery_plan.md')})
    (CONTROL/'freeze.json').chmod(0o444)
    provenance.bind(CONTROL, matrix)
    (CONTROL/'bindings-v1.json').chmod(0o444)

def run() -> None:
    binary, cases = provenance.verify(CONTROL)
    require(not (CONTROL/'launch.json').exists(), 'launch already reserved')
    x.preflight(); x.save(CONTROL/'launch.json',{'pid':__import__('os').getpid(),'freeze_sha256':x.digest(CONTROL/'freeze.json')})
    results: list[Execution] = []
    for case in cases:
        x.preflight()
        # Mutable dependencies are rechecked immediately before every execution.
        provenance.verify(CONTROL)
        config=Path(case['config'])
        directory=POP/f"{case['index']:02}"; directory.mkdir()
        x.EVIDENCE.joinpath('STATUS.md').write_text(f"# SM-XP001 live\n\nPopulation execution {case['index']+1}/12 starting. Controller PID {__import__('os').getpid()}; current raw {directory}. Reactions v1 retained scarce negative; v2 canonical support control passed.\n")
        rc=x.command([str(binary),'30',str(config)],directory,'native',600,case['environment'])
        result: Execution = {'case':case,'returncode':rc}
        x.save(directory.with_suffix('.inventory.json'),x.inventory(directory))
        results.append(result)
        x.save(CONTROL/f"execution-{case['index']:02}.json",result)
        require(rc == 0, f"native execution {case['index']} failed; launch remains consumed")
    x.save(CONTROL/'executions.json',results)
    for result in results:
        c=result['case']; directory=POP/f"{c['index']:02}"
        if c['observed'] and result['returncode']==0:
            rc=x.command([sys.executable,'-m','experiments.stringmol.xp001_population','analyze-one',str(c['index'])],CONTROL,f"analysis-{c['index']:02}",1800,working_dir=x.ROOT)
            result['analysis_returncode']=rc
    x.save(CONTROL/'completed.json',results)

def analyze_one(index: int, repeat: bool = False) -> None:
    case=provenance.cases_from(object_from(CONTROL/'freeze.json'))[index]
    directory=POP/f'{index:02}'
    require(x.inventory(directory)==json.loads(directory.with_suffix('.inventory.json').read_text()), 'inventory mismatch')
    result=analyze(directory,case['founders'])
    x.save(CONTROL/f"{'repeat' if repeat else 'summary'}-{index:02}.json",result)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('action',choices=['freeze','run','analyze-one','repeat-analyze']);p.add_argument('index',type=int,nargs='?');args=p.parse_args()
    if args.action in ('analyze-one','repeat-analyze'):
        if args.index is None:
            p.error('index required')
        analyze_one(args.index,args.action=='repeat-analyze')
    else: {'freeze':freeze,'run':run}[args.action]()
