"""Report every diagnostic outcome without promoting the failed observer gate."""
import csv
import json
from experiments.stringmol.locality_pilot import CONTROL,RAW,ARMS,record,save


def main():
    root=CONTROL/'diagnostic-v3'
    diagnostics=json.loads((root/'diagnostics.json').read_text())
    summary=[]
    for arm in ARMS:
        facts=diagnostics['arms'][arm]
        row={'arm':arm,'seed':202620999,'independent_seeds':1,'native_executions':3,
             'native_successes':sum(code==0 for code in facts['native_exit_codes'].values()),
             'repeat_bytes':facts['exact_repeat'],'partial_observer_parity':facts['common_file_parity'],
             'full_observer_off':facts['full_observer_off'],'replay_passes':sum(r['exit_code']==0 for r in facts['replays'])}
        path=root/f'{arm}-observed.json';repeat=root/f'{arm}-repeat.json'
        if row['replay_passes']==2:
            assert path.read_bytes()==repeat.read_bytes(), 'repeat analysis byte mismatch'
            if arm in ('GG','GL'):
                assert path.read_bytes()==(CONTROL/'diagnostic-v2'/path.name).read_bytes(), 'global reconstruction regression'
            result=json.loads(path.read_text())
            edges=result['renewal']['transfer_edges']
            row.update(end_tick=result['end_tick'],end_population=result['end_population'],
                       population4900=next((c['population'] for c in result['checkpoints'] if c['tick']==4900),0),
                       births=result['placed'],partial_transfers=sum(e['transfer_eligible'] for e in edges),
                       nonfounder_sources=len({e['source'] for e in edges if e['source']>=140}),
                       searches=result['searches'],empty_searches=result['empty_searches'],encounters=result['encounters'],
                       bindings=result['bindings'],nonempty_cleavage_attempts=result['proposals'],failed_placements=result['failed_placement'],
                       vacancy_sum=result['vacancy_sum'])
        summary.append(row)
    assert len(summary)==4 and sum(r['native_executions'] for r in summary)==12
    assert all(not r['full_observer_off'] for r in summary), 'unexpected reinterpretation of observer condition'
    keys=list(dict.fromkeys(k for row in summary for k in row))
    with (CONTROL/'diagnostic-summary.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,keys,lineterminator='\n');writer.writeheader();writer.writerows(summary)
    gg=summary[0]
    positive=(gg['births']>=100 and gg['population4900']>0) if gg['replay_passes']==2 else None
    save(CONTROL/'decision.json',{'decision':'BLOCKED: frozen full-observer-off qualification not executed',
         'canonical_positive_control_observed':positive,
         'population_interpretation_authorized':False,'native_executions':12,'additional_native_executions_authorized':0,
         'diagnostic_replays_passed':sum(r['replay_passes'] for r in summary),'diagnostic_replays_total':8,
         'summary':summary,'verification':record(root/'diagnostics.json'),
         'required_parent_decision':'Review a fresh complete recovery protocol/budget; never selectively repeat off runs or failed cells.'})


if __name__=='__main__':main()
