"""Whole-matrix diagnostics; never converts the failed full-off gate into a pass."""
import json
from pathlib import Path
import subprocess
from experiments.stringmol.locality_pilot import CONTROL,RAW,ARMS,PYTHON,inventory,record,save,OBS


def main():
    root=CONTROL/'diagnostic-v3';root.mkdir(exist_ok=False)
    result={}
    for arm in ARMS:
        receipts={kind:json.loads((RAW/f'{arm}-{kind}.receipt.json').read_text()) for kind in ('observed','repeat','off')}
        r={'native_exit_codes':{k:v['exit_code'] for k,v in receipts.items()},'inventories':{},'replays':[]}
        for kind,receipt in receipts.items():r['inventories'][kind]=inventory(RAW/f'{arm}-{kind}')==receipt['inventory']
        on,repeat,off=(receipts[k]['inventory'] for k in ('observed','repeat','off'))
        r['exact_repeat']=on==repeat
        r['common_file_parity']=all(on.get(k)==v for k,v in off.items())
        r['disabled_streams']=sorted(set(on)-set(off))
        r['full_observer_off']=not (OBS & set(off))
        for kind in ('observed','repeat'):
            output=root/f'{arm}-{kind}.json';log=root/f'{arm}-{kind}.log'
            cmd=[PYTHON,'-m','experiments.stringmol.locality_pilot','one',arm,kind,str(output)]
            with log.open('xb') as f:
                try:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=1800);code=p.returncode
                except subprocess.TimeoutExpired:code='TIMEOUT'
            r['replays'].append({'kind':kind,'exit_code':code,'log':record(log),'result':record(output) if output.exists() else None})
        result[arm]=r
        save(root/f'{arm}-diagnostic.json',r)
        (CONTROL/'STATUS.md').write_text(f'# SM-XL001\n12/12 native executions done; full-observer-off gate FAILED. Diagnostic v3 finished {arm}; current controller is active, no population interpretation.\n')
    save(root/'diagnostics.json',{'full_observer_gate':False,'population_interpretation_authorized':False,'arms':result})


if __name__=='__main__':main()
