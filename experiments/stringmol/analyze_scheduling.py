"""SM-B001 ordered boundary/material replay and frozen matched-run decisions.

H001 source qualification and M001 sequence endpoints are called unchanged.
Boundary replay reconstructs the two scheduling lists and bound pairs without
trusting lifecycle summaries or the runtime's source attribution.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
import csv
import json
from pathlib import Path
from statistics import median
import subprocess
from typing import Any

from experiments.stringmol import analyze_conservation as c, analyze_decay as d
from experiments.stringmol import analyze_renewal as h1, analyze_mutation as m1
from experiments.stringmol.analyze_lineage import EVENT_COLUMNS, integer, require

ARMS = ('IMMEDIATE', 'DELAY500', 'LOCKED')
SEEDS = list(range(202627000, 202627020))
MATRIX = [(arm, seed) for seed in SEEDS for arm in ARMS]
LOGS = {'scheduling_events001.csv'}
COLUMNS = 'event,tick,index,id,other,active,passive,source,eligible_tick,policy,count,selected,outcome,opcode,owner,offset,material_index,ids'.split(',')
NUMERIC = [k for k in COLUMNS if k not in ('event', 'policy', 'outcome', 'ids')]
DEFAULTS = {k: ('0' if k in ('eligible_tick', 'count', 'material_index') else '-1') for k in NUMERIC if k not in ('tick', 'index')}
DEFAULT_NUMBERS = {k:int(v) for k,v in DEFAULTS.items()}
DEFAULTS.update(outcome='', ids='')
FIELDS = {
    'START': {'eligible_tick', 'ids'}, 'TICK': {'ids'}, 'RELEASE': {'id', 'eligible_tick'},
    'SELECT': {'id', 'other', 'eligible_tick', 'count', 'outcome'},
    'SURVIVE': {'id', 'other'}, 'DECAY': {'id', 'other'},
    'SEARCH': {'id', 'other', 'count', 'selected', 'outcome'},
    'ENCOUNTER': {'id', 'other', 'active', 'passive', 'count', 'selected', 'outcome'},
    'DISPATCH': {'active', 'passive', 'opcode', 'owner', 'offset', 'material_index'},
    'COMPLETE': {'active', 'passive', 'material_index'},
    'BIRTH': {'id', 'active', 'passive', 'source', 'eligible_tick', 'material_index'},
    'DEATH': {'id', 'eligible_tick', 'outcome', 'material_index'},
    'CENSOR': {'id', 'eligible_tick'}, 'END': {'ids', 'material_index'},
}


def output_names(end: int) -> set[str]:
    return d.output_names(end) | LOGS


def ordered_ids(raw: str) -> list[int]:
    values = [integer(v) for v in raw.split(';')] if raw else []
    require(len(values) == len(set(values)), 'duplicate ordered identity')
    return values


def boundary_rows(path: Path) -> Iterator[dict[str, str]]:
    # Streaming canonical CSV: this schema cannot contain escaped/quoted fields.
    with path.open(encoding='ascii', newline='') as f:
        require(next(f, '') == ','.join(COLUMNS)+'\n', 'boundary CSV header')
        for line in f:
            require(line.endswith('\n') and '\r' not in line and '"' not in line, 'boundary CSV bytes')
            values = line[:-1].split(',')
            require(len(values) == len(COLUMNS), 'boundary CSV width')
            yield dict(zip(COLUMNS, values, strict=True))


def eligibility(birth: int, policy: str, horizon: int) -> int:
    require(policy in (*ARMS, 'DISABLED') and 0 <= birth < horizon < 2**64-1, 'eligibility domain')
    result = horizon+1 if policy == 'LOCKED' else birth+1+(500 if policy == 'DELAY500' else 0)
    require(result < 2**64, 'eligibility overflow')
    return result


class BoundaryReplay:
    def __init__(self, initial: dict[str, Any], material: list[dict[str, str]], policy: str, horizon: int = 5000, initial_order: list[int] | None = None):
        require(policy in (*ARMS, 'DISABLED'), 'boundary policy')
        self.policy, self.horizon = policy, horizon
        self.source = h1.SourceReplay(initial)
        self.initial_order = initial_order if initial_order is not None else list(self.source.material.buffers)
        self.material = material
        self.cursor = self.index = self.dispatch_cursor = 0
        self.tick = -1
        self.started = self.ended = False
        self.now: list[int] = []
        self.next: list[int] = []
        self.pairs: dict[int, int] = {}
        self.active: set[int] = set()
        self.children: dict[int, dict[str, Any]] = {}
        self.releases: list[int] = []
        self.pending_birth: dict[str, Any] | None = None
        self.pending_deaths: dict[int, tuple[int, str]] = {}
        self.selection: tuple[int, int] | None = None
        self.dispatch: tuple[int, int, int] | None = None
        self.search: tuple[int, int, int] | None = None
        self.phase = 'idle'
        self.append: list[int] = []
        self.censored: list[int] = []
        self.events: Counter[str] = Counter()
        self.occupancy: list[int] = []

    def eligible_tick(self, idx: int) -> int:
        return int(self.children[idx]['eligible_tick']) if idx in self.children else 0

    def check(self, idx: int) -> None:
        require(idx in self.source.material.buffers and self.tick >= self.eligible_tick(idx), 'early/dead participation')
        if idx in self.children:
            require(self.children[idx]['released'] is not None, 'participation without release')

    def participate(self, idx: int, role: str, bound: bool = False, dispatch: bool = False) -> None:
        self.check(idx)
        if idx not in self.children: return
        child = self.children[idx]
        key = 'dispatches' if dispatch else 'bindings' if bound else 'encounters'
        child[key] += 1
        if not bound and not dispatch and child['first_participation'] is None:
            child['first_participation'] = {'tick': self.tick, 'role': role,
                'birth_latency': self.tick-child['birth_tick'], 'release_latency': self.tick-child['eligible_tick']}

    def unbind(self, idx: int) -> None:
        partner = self.pairs.pop(idx, None)
        self.active.discard(idx)
        if partner is not None:
            self.pairs.pop(partner, None); self.active.discard(partner)

    def advance(self, target: int) -> None:
        require(self.cursor <= target <= self.cursor+1 <= len(self.material)+1, 'material link skipped/reordered')
        if target == self.cursor: return
        require(not self.pending_birth and not self.pending_deaths, 'unreported material lifecycle')
        row = self.material[self.cursor]
        require(integer(row['tick']) == self.tick and integer(row['index']) == target, 'material link tick/index')
        before = set(self.source.material.buffers)
        participants = d.ids(row['before_ids'])
        if row['event'] == 'DECAY':
            require(self.selection is not None and self.phase == 'survival' and set(participants) <= set(self.selection), 'unselected decay')
        else:
            require(self.dispatch is not None and self.phase == 'dispatch', 'material outside dispatch')
            assert self.dispatch is not None
            active, passive, opcode = self.dispatch
            require(set(participants) == {active, passive} and row['event'] == ('COPY' if opcode == ord('=') else 'CLEAVE' if opcode == ord('%') else ''), 'opcode/material mismatch')
        self.source.step(row)
        self.cursor = target
        after = set(self.source.material.buffers)
        for idx in before-after:
            self.pending_deaths[idx] = (target, row['event'])
        if after-before:
            self.pending_birth = self.source.edges[-1]

    def finish_selection(self) -> None:
        if self.selection is None: return
        require(self.phase == 'done' and self.dispatch is None and not self.pending_birth and not self.pending_deaths, 'incomplete selection lifecycle')
        require(len(self.append) == len(set(self.append)) and not set(self.append) & set(self.next), 'duplicate next-list insertion')
        require(set(self.append) <= self.source.material.buffers.keys(), 'appending dead child')
        self.next.extend(self.append)
        self.selection = None; self.append = []; self.search = None; self.phase = 'idle'

    def step(self, row: dict[str, str]) -> None:
        require(set(row) == set(COLUMNS), 'boundary schema')
        event = row['event']
        require(event in FIELDS and not self.ended and row['policy'] == self.policy, 'boundary event/policy/END')
        for k,v in DEFAULTS.items():
            if k not in FIELDS[event]: require(row[k] == v, 'noncanonical unused boundary field: '+k)
        # Unused fields were compared to exact canonical defaults above. Parse
        # only the event's used numbers; the scheduling stream has millions of rows.
        n = DEFAULT_NUMBERS.copy()
        for k in ('tick','index',*(key for key in FIELDS[event] if key in NUMERIC)):
            n[k] = integer(row[k], -1 if k in ('id','other','active','passive','source','selected','opcode','owner','offset') else 0,
                           2**64-1 if k in ('eligible_tick','index','material_index','tick') else 2**31-1)
        require(n['index'] == self.index+1, 'boundary order/index')
        self.index += 1; self.events[event] += 1
        tick, idx = n['tick'], n['id']
        if event == 'START':
            require(not self.started and self.index == 1 and tick == 0 and n['eligible_tick'] == self.horizon, 'boundary START')
            self.next = ordered_ids(row['ids'])
            require(set(self.next) == self.source.initial_ids and self.next == self.initial_order, 'boundary initial identity/order')
            self.started = True
            return
        require(self.started, 'missing boundary START')
        if event in ('TICK','END','CENSOR'):
            self.finish_selection()
            require(not self.now and not self.releases, 'missing top-level selection/release')
            require(not self.pending_birth and not self.pending_deaths, 'missing lifecycle events')
            require(set(self.next) == set(self.source.material.buffers), 'scheduling/material roster mismatch')
            if event == 'TICK':
                require(not self.censored and tick == self.tick+1 and tick < self.horizon and bool(self.next), 'tick order/horizon')
                require(ordered_ids(row['ids']) == self.next, 'native next-list order mismatch')
                self.tick=tick; self.now=self.next; self.next=[]
                self.occupancy.append(len(self.now))
                self.releases=[i for i in self.now if i in self.children and self.children[i]['released'] is None and self.eligible_tick(i) <= tick]
                return
            require(tick == self.tick+1 and (tick == self.horizon or not self.next), 'END horizon/extinction')
            if event == 'CENSOR':
                expected=[i for i in self.next if i in self.children]
                require(len(self.censored) < len(expected) and idx == expected[len(self.censored)] and n['eligible_tick'] == self.eligible_tick(idx), 'END censor order/identity')
                self.censored.append(idx); return
            require(self.censored == [i for i in self.next if i in self.children] and ordered_ids(row['ids']) == self.next, 'missing END censor')
            require(n['material_index'] == self.cursor == len(self.material), 'missing material events at END')
            self.ended=True; return
        require(tick == self.tick, 'boundary tick mismatch')
        if event == 'RELEASE':
            require(bool(self.releases) and idx == self.releases.pop(0), 'duplicate/missing eligibility transition')
            require(n['eligible_tick'] == tick == self.eligible_tick(idx), 'eligibility exact boundary')
            self.children[idx]['released']=tick; return
        require(not self.releases and not self.censored, 'event before releases/after censor')
        if event == 'SELECT':
            self.finish_selection()
            require(idx in self.now, 'duplicate/missing top-level selection')
            other=self.pairs.get(idx,-1)
            require(n['other'] == other and n['eligible_tick'] == self.eligible_tick(idx) and n['count'] == int(tick >= self.eligible_tick(idx)), 'selection eligibility/partner')
            require(row['outcome'] == ('UNBOUND' if other == -1 else 'ACTIVE' if idx in self.active else 'PASSIVE'), 'selection status')
            self.now.remove(idx)
            if other != -1:
                self.check(idx); self.check(other)
                require(other in self.now, 'bound partner already processed'); self.now.remove(other)
            self.selection=(idx,other); self.phase='survival'; return
        require(self.selection is not None, 'event outside selected processing')
        assert self.selection is not None
        selected, partner=self.selection
        if event in ('SURVIVE','DECAY'):
            require(self.phase == 'survival' and (idx,n['other']) == self.selection and not self.pending_deaths, 'selection outcome order')
            participants={i for i in self.selection if i != -1}
            alive=self.source.material.buffers.keys()
            require((participants <= alive) if event == 'SURVIVE' else not (participants & alive), 'decay/survival material mismatch')
            self.phase='action' if event == 'SURVIVE' else 'done'
            if event == 'SURVIVE' and tick < self.eligible_tick(idx):
                require(partner == -1, 'bound locked survivor'); self.append=[idx]; self.phase='done'
            return
        if event == 'SEARCH':
            require(self.phase == 'action' and partner == -1 and idx == selected, 'seeker search ordering')
            self.check(idx)
            candidates=[i for i in self.now if i not in self.pairs and tick >= self.eligible_tick(i)]
            require(n['count'] == len(candidates), 'pre-sampling candidate count')
            if not candidates:
                require(n['selected'] == n['other'] == -1 and row['outcome'] == 'EMPTY', 'empty search outcome')
                self.append=[idx]; self.phase='done'
            else:
                require(0 <= n['selected'] < len(candidates) and n['other'] == candidates[n['selected']] and row['outcome'] == 'SELECTED', 'candidate rank/list order')
                self.check(n['other']); self.now.remove(n['other']); self.phase='encounter'
                self.search=(n['other'],n['count'],n['selected'])
            return
        if event == 'ENCOUNTER':
            require(self.phase == 'encounter' and idx == selected and self.search == (n['other'],n['count'],n['selected']), 'duplicate/missing encounter')
            require(row['outcome'] in ('BOUND','UNBOUND'), 'binding outcome')
            for i,role in ((idx,'seeker'),(n['other'],'selected-partner')): self.participate(i,role)
            if row['outcome'] == 'BOUND':
                a,b=n['active'],n['passive']
                require(a != b and {a,b} == {idx,n['other']}, 'binding roles')
                self.pairs[a]=b; self.pairs[b]=a; self.active.add(a)
                self.participate(a,'active',bound=True); self.participate(b,'passive',bound=True)
            else: require(n['active'] == n['passive'] == -1, 'failed binding roles')
            self.append=[idx,n['other']]; self.phase='done'; return
        if event == 'DISPATCH':
            require(self.phase == 'action' and partner != -1 and self.dispatch is None, 'bound dispatch ordering')
            a,b=n['active'],n['passive']
            require({a,b} == {selected,partner} and a in self.active and self.pairs[a] == b, 'dispatch roles')
            self.participate(a,'active',dispatch=True); self.participate(b,'passive',dispatch=True)
            require(n['material_index'] == self.cursor and n['owner'] in (a,b), 'dispatch material cursor/owner')
            buffer=self.source.material.buffers[n['owner']]
            require(0 <= n['offset'] < len(buffer) and n['opcode'] == buffer[n['offset']], 'dispatch opcode/full-buffer link')
            self.dispatch_cursor=self.cursor
            self.dispatch=(a,b,n['opcode']); self.phase='dispatch'; return
        if event in ('BIRTH','DEATH','COMPLETE'):
            self.advance(n['material_index'])
            if event == 'DEATH':
                require(idx in self.pending_deaths and self.pending_deaths.pop(idx) == (n['material_index'],row['outcome']), 'death material link/cause')
                require(n['eligible_tick'] == self.eligible_tick(idx), 'death eligibility')
                self.unbind(idx)
                if idx in self.children: self.children[idx]['death']={'tick':tick,'cause':row['outcome']}
                return
            require(self.dispatch is not None, 'birth/completion outside dispatch')
            assert self.dispatch is not None
            a,b,opcode=self.dispatch
            require((n['active'],n['passive']) == (a,b), 'birth/completion dispatch roles')
            if event == 'BIRTH':
                edge=self.pending_birth
                require(edge is not None and idx == edge['child'] and tick == edge['tick'] and n['material_index'] == edge['index'], 'missing/duplicate policy child')
                assert edge is not None
                require(n['source'] == edge['source'] and a in edge['cleanup_active_ids'], 'wrong material source/cleanup attribution')
                require(n['eligible_tick'] == eligibility(tick,self.policy,self.horizon) and idx not in self.children, 'child policy/identity')
                self.children[idx]={'id':idx,'birth_tick':tick,'eligible_tick':n['eligible_tick'],'source':n['source'],
                    'released':None,'death':None,'first_participation':None,'encounters':0,'bindings':0,'dispatches':0}
                self.append.append(idx); self.pending_birth=None; return
            require(self.phase == 'dispatch' and not self.pending_birth and not self.pending_deaths, 'unreported birth/death')
            # COPY/CLEAVE always emit one material event; other opcodes emit none.
            # Source replay above validates the event's exact byte transfer.
            require(self.cursor == self.dispatch_cursor+int(opcode in (ord('='),ord('%'))), 'missing/spurious opcode material event')
            if opcode in (0,ord('}')): self.unbind(a)
            self.append.extend(i for i in (a,b) if i in self.source.material.buffers)
            self.dispatch=None; self.phase='done'; return
        raise ValueError('unsupported boundary event')

    def summary(self, end: int) -> dict[str, Any]:
        require(self.ended and self.tick+1 == end, 'missing boundary END')
        for child in self.children.values():
            death=child['death']
            child['survived_END']=death is None
            child['final_state']=('decayed before eligibility' if death is not None and death['tick'] < child['eligible_tick'] else
                'alive but not yet eligible at END' if child['released'] is None else
                'dispatched' if child['dispatches'] else 'bound but never dispatched' if child['bindings'] else
                'encountered but never bound' if child['encounters'] else 'eligible but never encountered')
            if child['released'] is None and death is not None: require(death['cause'] == 'DECAY', 'ineligible non-decay death')
        children=list(self.children.values())
        applied=sum(v['eligible_tick'] < self.horizon for v in children)
        survived=sum(v['released'] is not None for v in children)
        participated=sum(v['released'] is not None and v['encounters'] > 0 for v in children)
        productive_sources={e['source'] for e in self.source.edges if e['productive']}
        return {'policy_births':len(children),'physical_child_placements':len(self.source.edges),
            'applied_before_horizon':applied,'survived_to_eligibility':survived,
            'decayed_before_eligibility':sum(v['final_state'] == 'decayed before eligibility' for v in children),
            'released_with_participation':participated,'released_without_participation':survived-participated,
            'released_productive_sources':sorted(productive_sources & {v['id'] for v in children if v['released'] is not None}),
            'application_exposed':applied >= 100,'response_exposed':survived >= 100 and participated >= 50,
            **{f'policy_child_{key}':sum(v[key] for v in children) for key in ('encounters','bindings','dispatches')},
            'final_state_counts':dict(Counter(v['final_state'] for v in children)),
            'first_participation_latencies':[v['first_participation'] for v in children if v['first_participation'] is not None],
            'surviving_policy_children':sum(v['survived_END'] for v in children),
            'children':children,'boundary_events':dict(self.events),'boundary_errors':0,
            'occupancy_by_tick':self.occupancy,'boundary_end_ids':sorted(self.next)}


def transfer_endpoints(summary: dict[str, Any], initial_ids: set[int]) -> dict[str, Any]:
    depth: dict[int,int | None] = dict.fromkeys(initial_ids,0)
    nonrelocation: dict[int,int | None] = dict.fromkeys(initial_ids,0)
    relocation: dict[int,int] = dict.fromkeys(initial_ids,0)
    deaths={v['id']:v['death_tick'] for v in summary['identity_history']}
    edges=[]
    for edge in summary['source_edges']:
        source,child=edge['source'],edge['child']
        require(child not in depth and (source is None or source != child), 'transfer ID reuse/cycle')
        parent=depth.get(source)
        whole=edge['whole_transfer']
        depth[child]=parent+1 if parent is not None else None
        parent_nonrelocation=nonrelocation.get(source)
        nonrelocation[child]=(parent_nonrelocation+(not whole)) if parent_nonrelocation is not None else None
        relocation[child]=relocation.get(source,0)+1 if whole else 0
        edges.append({**edge,'transfer_depth':depth[child],'source_transfer_depth':parent,
            'nonrelocation_depth':nonrelocation[child],'relocation_chain_depth':relocation[child],
            'relocation':whole,'transfer_orphan':parent is None,
            'source_remnant_survived_placement':edge['offset'] > 0,
            'source_survived_END':source in summary['boundary_end_ids'],
            'source_death_tick':deaths.get(source),
            'source_remnant_survival_ticks':None if deaths.get(source) is None else deaths[source]-edge['tick'],
            'child_survived_END':child in summary['boundary_end_ids']})
    return {'transfer_edges':edges,'nonrelocation_serial_transfers':sum(not e['relocation'] and e['source_transfer_depth'] is not None and e['source_transfer_depth'] >= 1 for e in edges),
        'max_transfer_depth':max((v for v in depth.values() if v is not None),default=0),
        'max_nonrelocation_depth':max((v for v in nonrelocation.values() if v is not None),default=0),
        'max_relocation_chain_depth':max(relocation.values(),default=0)}


def analyze_run(directory: Path, expected: list[dict[str, Any]], *, policy: str, nsteps: int = 5000, exit_status: int = 0) -> dict[str, Any]:
    summary=h1.analyze_run(directory,expected,nsteps=nsteps,exit_status=exit_status)
    summary.update(m1.sequence_endpoints(summary))
    native=c.canonical_rows(directory/'lineage_events001.csv',EVENT_COLUMNS)
    initial_order=[integer(r['child_id']) for r in native if r['event']=='INIT']
    replay=BoundaryReplay(c.initial_material(expected,'histogram',0),c.canonical_rows(directory/'material_events002.csv',d.JOURNAL_COLUMNS),policy,nsteps,initial_order)
    for row in boundary_rows(directory/'scheduling_events001.csv'): replay.step(row)
    boundary=replay.summary(summary['end_timestep'])
    require(len(replay.source.edges) == summary['native_births'] and boundary['boundary_end_ids'] == sorted(replay.source.material.buffers), 'boundary/native child/END crosscheck')
    # Compare independently inferred source edges before H001 adds native roles.
    require([{k:v for k,v in e.items() if k != 'source_role'} for e in summary['source_edges']] == replay.source.edges, 'boundary/source DAG crosscheck')
    summary.update(boundary)
    summary['surviving_qualifying_descendants']=len(summary['end_surviving_qualifying_descendants'])
    summary['surviving_material_sources']=len({e['source'] for e in summary['source_edges']} & set(boundary['boundary_end_ids']))
    summary.update(transfer_endpoints(summary,replay.source.initial_ids))
    if policy == 'LOCKED': require(all(summary['policy_child_'+k] == 0 for k in ('encounters','bindings','dispatches')), 'LOCKED enforcement')
    return summary


SCALARS = (*m1.SCALARS,'surviving_policy_children','surviving_qualifying_descendants','surviving_material_sources','end_population','survived_to_eligibility','decayed_before_eligibility',
           'released_with_participation','nonrelocation_serial_transfers','max_transfer_depth',
           'max_nonrelocation_depth','max_relocation_chain_depth')


def comparison(left: Any, right: Any) -> dict[str, Any]:
    if left is None or right is None: return {'difference':None,'direction':'missing'}
    difference=left-right
    return {'difference':difference,'direction':'immediate_greater' if difference > 0 else 'delay_greater' if difference < 0 else 'tie'}


def outcomes(results: list[dict[str, Any]], failures: list[dict[str, Any]], *, mechanics: bool = True) -> dict[str, Any]:
    by_run={(r['condition'],r['seed']):r for r in results}
    locked=all(all(r.get('policy_child_'+k) == 0 for k in ('encounters','bindings','dispatches')) for r in results if r['condition'] == 'LOCKED')
    integrity=mechanics and not failures and len(results) == len(by_run) == 60 and set(by_run) == set(MATRIX) and locked and all(r.get('boundary_errors') == 0 for r in results)
    pairs: list[dict[str,Any]]=[]
    for seed in SEEDS:
        immediate,delay=(by_run.get((arm,seed)) for arm in ARMS[:2])
        distributions = {}
        for key in ('productive_length_counts','renewing_length_counts','productive_sequence_abundances','renewing_sequence_abundances','retention_distribution'):
            def distribution(row: dict[str,Any] | None) -> dict[str,int]:
                if row is None: return {}
                if key.endswith('length_counts'): return dict(row.get(key,{}))
                if key.endswith('sequence_abundances'):
                    return {f"{v['length']}:{v['visible_hex']}":v['count'] for v in row.get(key,[])}
                return dict(Counter(str(v) for v in row.get(key,[])))
            left,right=distribution(immediate),distribution(delay)
            distributions[key]={v:comparison(left.get(v,0),right.get(v,0)) if immediate and delay else comparison(None,None) for v in sorted(left.keys() | right.keys())}
        pairs.append({'seed':seed,'distribution_comparisons':distributions,'immediate':m1.renewal(immediate),'delay':m1.renewal(delay),
            'comparisons':{k:comparison(immediate.get(k) if immediate else None,delay.get(k) if delay else None) for k in SCALARS}})
    arms={arm:{'continuity_count':sum(m1.renewal(by_run.get((arm,s)))['continuity'] for s in SEEDS),
               'core_count':sum(m1.renewal(by_run.get((arm,s)))['core'] for s in SEEDS),
               'application_exposed_runs':sum(by_run.get((arm,s),{}).get('applied_before_horizon',0) >= 100 for s in SEEDS),
               'response_exposed_runs':sum(by_run.get((arm,s),{}).get('survived_to_eligibility',0) >= 100 and by_run.get((arm,s),{}).get('released_with_participation',0) >= 50 for s in SEEDS)} for arm in ARMS}
    for arm in arms.values(): arm['viable']=arm['continuity_count'] >= 16
    exposed=arms['DELAY500']['application_exposed_runs'] >= 16
    discordant=sum(p['immediate']['continuity'] and not p['delay']['continuity'] for p in pairs)
    count=arms['DELAY500']['continuity_count']
    branch=(1 if not integrity else 2 if not arms['IMMEDIATE']['viable'] else 6 if not exposed else
            3 if count >= 16 else 4 if count <= 4 and discordant >= 16 else 5)
    decisions={1:'Unevaluable integrity',2:'Valid positive-control failure',3:'Delay-robust renewal',
               4:'Strong fixed-horizon delay sensitivity',5:'Intermediate delay response',6:'Inadequate application exposure'}
    interpretations={1:'Repair only demonstrated implementation/artifact defects, retain failures, then rerun the unchanged complete matrix.',
        2:'Stop; DELAY500 has no biological interpretation and no rerun is authorized.',
        3:'Immediate scheduling within 500 ticks is not required for robust renewal under this condition. This is not equivalence.',
        4:'The total 500-tick scheduling policy, including mortality, encounters and occupancy, causally disrupts fixed-horizon renewal. No unrestricted necessity claim.',
        5:'Report magnitude and ties; neither robustness nor strong sensitivity is established.',
        6:'Retain valid total policy outcomes; no calibrated delay-response or continuation claim.'}
    def aggregate(values: list[dict[str,Any]]) -> dict[str,Any]:
        differences=[v['difference'] for v in values if v['difference'] is not None]
        return {'direction_counts':dict(Counter(v['direction'] for v in values)), 'median_difference':median(differences) if differences else None,'pair_denominator':20,'observed_pairs':len(differences)}
    distribution_summary = {}
    for key in pairs[0]['distribution_comparisons']:
        support=sorted({v for p in pairs for v in p['distribution_comparisons'][key]})
        distribution_summary[key]={v:aggregate([p['distribution_comparisons'][key].get(v,comparison(0,0) if ('IMMEDIATE',p['seed']) in by_run and ('DELAY500',p['seed']) in by_run else comparison(None,None)) for p in pairs]) for v in support}
    return {'paired_distribution_summary':distribution_summary,'decision':decisions[branch],'branch':branch,'interpretation':interpretations[branch],
        'integrity':integrity,'mechanics':mechanics,'locked_enforcement':locked,'arms':arms,
        'application_exposed':exposed,'immediate_only_continuity_pairs':discordant,
        'separate_retention_preregistration_authorized':branch in (3,4,5),
        'prospective_floor_handling_required':count <= 4,
        'post_release_competence_scope':'Only runs satisfying both frozen response-exposure counts; no additional arm threshold is imposed.',
        'prospective_response_exposure_requirement':'A separate preregistration must address inadequate per-run post-release exposure prospectively.',
        'post_release_response_exposed_runs':arms['DELAY500']['response_exposed_runs'],
        'run_denominator':60,'arm_denominator':20,'paired_denominator':20,'pairs':pairs,
        'paired_summary':{k:aggregate([p['comparisons'][k] for p in pairs]) for k in SCALARS},
        'runs':results,'failures':failures,
        'limits':'LOCKED participation is imposed, not latent incompetence. Response exposure never gates the total policy effect. Replacement admission and BFF rescue require separate prospective work.'}


def analyze_campaign(manifest: Path) -> dict[str, Any]:
    from experiments.stringmol import scheduling_workflow as w
    results: list[dict[str,Any]]=[]; failures: list[dict[str,Any]]=[]
    try:
        data=w.verify_preparation(manifest); w.verify_launch(manifest)
        require(w.read(manifest.parent/'campaign.json') == {'input_manifest':w.record(manifest),'workers':6,'launch_record':w.record(manifest.parent/'launch.json')}, 'campaign identity')
        receipts=w.read(manifest.parent/'campaign-results.json'); require(len(receipts) == 60,'incomplete campaign')
    except (ValueError,OSError,KeyError,TypeError,csv.Error,subprocess.CalledProcessError) as exc:
        return outcomes([], [{'error':str(exc)}], mechanics=False)
    for r,receipt in zip(data['runs'],receipts,strict=True):
        try:
            directory=Path(r['directory'])
            require(receipt == w.read(directory.with_suffix('.inventory.json')) and receipt['input_manifest'] == w.record(manifest),'run receipt')
            require(receipt['condition'] == r['condition'] and receipt['seed'] == r['seed'] and receipt['files'] == w.inventory(directory),'output identity/inventory')
            summary=analyze_run(directory,r['expected_initial'],policy=r['condition'],exit_status=receipt['exit_status'])
            require(set(receipt['files']) == output_names(summary['end_timestep']), 'scientific output names')
            results.append({'condition':r['condition'],'seed':r['seed'],**summary})
        except (ValueError,OSError,KeyError,TypeError,csv.Error,subprocess.CalledProcessError) as exc:
            failures.append({'condition':r['condition'],'seed':r['seed'],'error':str(exc)})
    return outcomes(results,failures)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('manifest',type=Path)
    print(json.dumps(analyze_campaign(parser.parse_args().manifest.resolve()),indent=2,sort_keys=True))
