"""Whole-matrix diagnostics; never converts the failed full-off gate into a pass."""
import json
from pathlib import Path
import os
from typing import cast
from experiments.stringmol.locality_models import Diagnostic
from experiments.stringmol.locality_process import execute
from experiments.stringmol.locality_pilot import NativeReceipt
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.locality_pilot import CONTROL,RAW,ARMS,PYTHON,inventory,record,save,OBS


def main() -> None:
    root=CONTROL/'diagnostic-v3';root.mkdir(exist_ok=False)
    result: dict[str, Diagnostic]={}
    for arm in ARMS:
        receipts={kind:cast(NativeReceipt, json.loads((RAW/f'{arm}-{kind}.receipt.json').read_text())) for kind in ('observed','repeat','off')}
        require(all(r.get('collection_complete', True) for r in receipts.values()), 'incomplete native evidence')
        r: Diagnostic={'native_exit_codes':{k:v['exit_code'] for k,v in receipts.items()},
            'inventories':{},'replays':[], 'exact_repeat':False, 'common_file_parity':False,
            'disabled_streams':[], 'full_observer_off':False}
        for kind,receipt in receipts.items():r['inventories'][kind]=inventory(RAW/f'{arm}-{kind}')==receipt['inventory']
        on,repeat,off=(receipts[k]['inventory'] for k in ('observed','repeat','off'))
        r['exact_repeat']=on==repeat
        r['common_file_parity']=all(on.get(k)==v for k,v in off.items())
        r['disabled_streams']=sorted(set(on)-set(off))
        r['full_observer_off']=not (OBS & set(off))
        for kind in ('observed','repeat'):
            output=root/f'{arm}-{kind}.json';log=root/f'{arm}-{kind}.log'
            cmd=[PYTHON,'-m','experiments.stringmol.locality_pilot','one',arm,kind,str(output)]
            process = execute(cmd, cwd=Path.cwd(), environment=dict(os.environ),
                receipt=root/f'{arm}-{kind}.process.json', stdout=log,
                stderr=root/f'{arm}-{kind}.stderr', timeout=1800, output_root=root)
            code = process['exit_code']
            r['replays'].append({'kind':kind,'exit_code':code,'log':record(log),'result':record(output) if output.exists() else None})
        result[arm]=r
        save(root/f'{arm}-diagnostic.json',r)
        (CONTROL/'STATUS.md').write_text(f'# SM-XL001\n12/12 native executions done; full-observer-off gate FAILED. Diagnostic v3 finished {arm}; current controller is active, no population interpretation.\n')
    save(root/'diagnostics.json',{'full_observer_gate':False,'population_interpretation_authorized':False,'arms':result})


if __name__=='__main__':main()
