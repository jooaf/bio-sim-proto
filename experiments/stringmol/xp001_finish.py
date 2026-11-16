"""Serial repeat analysis and exact parity audit for SM-XP001 (no native launch)."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import sys
import time
from experiments.stringmol import xp001 as x, xp001_population as p


def finish() -> None:
    x.preflight()
    deadline=time.monotonic()+1800
    while not (p.CONTROL/'completed.json').exists():
        if time.monotonic()>deadline:
            raise TimeoutError('first analysis controller has not completed in 1800s')
        time.sleep(3)
    executions=json.loads((p.CONTROL/'completed.json').read_text())
    assert len(executions)==12 and all(r['returncode']==0 for r in executions)
    assert all(r.get('analysis_returncode')==0 for r in executions if r['case']['observed'])
    for r in executions:
        c=r['case']; index=c['index']
        if not c['observed']: continue
        assert x.command([sys.executable,'-m','experiments.stringmol.xp001_population','repeat-analyze',str(index)],
                         p.CONTROL,f'repeat-analysis-{index:02}',1800,working_dir=x.ROOT)==0
        assert (p.CONTROL/f'summary-{index:02}.json').read_bytes()==(p.CONTROL/f'repeat-{index:02}.json').read_bytes()
    parity={}
    for a,b in [(4,8),(5,9),(4,10),(6,11)]:
        left=json.loads((p.POP/f'{a:02}.inventory.json').read_text())
        right=json.loads((p.POP/f'{b:02}.inventory.json').read_text())
        left.pop('native.receipt.json');right.pop('native.receipt.json')
        if b>=10:
            for name in ['lineage_events001.csv','lineage_snapshots001.csv','conservation002.csv','conservation_buffers002.csv',
                         'material_events002.csv','scheduling_events001.csv','source_events006.csv']:
                del left[name]
        parity[f'{a:02}-{b:02}']=left==right
    summaries=[]
    for r in executions[:8]:
        c=r['case']; s=json.loads((p.CONTROL/f"summary-{c['index']:02}.json").read_text())
        summaries.append({**{k:c[k] for k in ['index','count','mixed','seed']},
            **{k:s[k] for k in ['integrity','end_tick','final_population','final_host','late_min_host','encounters','bound_encounters','dispatches','successful_cleavages','exact_host_children']},
            **{k:s['transfer'][k] for k in ['qualifying_transfers','serial_transfers','transfer_renewing_descendants','max_nonrelocation_depth']}})
    canonical=all(s['exact_host_children']>0 and s['final_host']>0 for s in summaries if s['count']==140 and not s['mixed'])
    result={'population_executions':12,'native_successes':12,'analyses_passed_twice':10,
            'repeat_analysis_byte_equal':True,'output_parity':parity,'canonical_reference_gate':canonical,
            'interpretation_integrity':all(parity.values()),'summaries':summaries,
            'inference':'Development only; short binding-excluded B changes material/length as well as compatible frequency; no significance or heredity claims.'}
    x.save(p.CONTROL/'final-audit.json',result)
    with (p.CONTROL/'population-summary.csv').open('x',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(summaries[0]));writer.writeheader();writer.writerows(summaries)

if __name__=='__main__':
    finish()
