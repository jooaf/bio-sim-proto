"""SM-B002 rooted transfer lineage and exact linked retirement replay."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from typing import Any
import csv
import json
import subprocess
from experiments.stringmol import analyze_scheduling as b1, analyze_renewal as h1, analyze_mutation as m1
from experiments.stringmol import analyze_conservation as c, retirement_material as d
from experiments.stringmol.analyze_lineage import EVENT_COLUMNS, SNAPSHOT_COLUMNS, integer, require
from experiments.stringmol.analyze_scheduling import COLUMNS, DEFAULTS, DEFAULT_NUMBERS, NUMERIC, FIELDS, ordered_ids, boundary_rows, eligibility
ARMS = ('IMMEDIATE_RETAIN','DELAY500_RETAIN','IMMEDIATE_RETIRE','DELAY500_RETIRE')
SEEDS = list(range(202628000,202628020))
MATRIX = [(arm,seed) for seed in SEEDS for arm in ARMS]
LOGS = {'source_events006.csv'}
SOURCE_COLUMNS = 'tick,material_index,active,passive,flow_source,flow_offset,source,offset,child,eligible_tick,decision,remnant_hex,source_x,source_y,child_x,child_y,survivor,now_before,next_before,now_after,next_after,proposals,eligible,committed'.split(',')
ENDPOINTS = ('qualifying_transfers','transfer_renewing_descendants','serial_transfers','max_nonrelocation_depth','late_transfer_renewing_descendants','retained_late_transfer_renewals')
THRESHOLDS = (100,10,50,2,5,5)

class SourceReplay(h1.SourceReplay):
    material: d.Replay
    def __init__(self, initial: dict[str,Any]):
        super().__init__(initial)
        self.material = d.Replay(initial,'recycle')
        self.transfer_depth: dict[int,int | None] = dict.fromkeys(self.initial_ids,0)
        self.relocation_depth: dict[int,int] = dict.fromkeys(self.initial_ids,0)
        self.transfer_renewals: dict[int,dict[str,Any]] = {}
        self.transactions: list[dict[str,Any]] = []

    def step(self, row: dict[str,str]) -> None:
        before = {i:self.material.buffers[i] for i in d.ids(row['before_ids'])}
        super().step(row)
        if row['event'] != 'CLEAVE': return
        after = {i:self.material.buffers[i] for i in d.ids(row['after_ids'])}
        self.transactions.append({'row':dict(row),'before':before,'after':after})
        if row['outcome'] != 'PLACED': return
        edge = self.edges[-1]; source,child = edge['source'],edge['child']
        eligible = edge['offset'] > 0 and source in after and any(after[source]) and not edge['whole_transfer']
        parent = self.transfer_depth[source]
        rooted = eligible and parent is not None
        self.transfer_depth[child] = parent+1 if rooted and parent is not None else None
        self.relocation_depth[child] = self.relocation_depth[source]+1 if edge['whole_transfer'] else 0
        edge.update(transfer_eligible=eligible, rooted_transfer=rooted, transfer_orphan=eligible and not rooted,
                    nonrelocation_depth=self.transfer_depth[child], source_nonrelocation_depth=parent,
                    relocation_depth=self.relocation_depth[child])
        if rooted and parent and source not in self.transfer_renewals:
            stats = h1.retention(self.birth_buffers[source],before[source])
            late = self.born[source] >= 2500
            self.transfer_renewals[source] = {'id':source,'birth_tick':self.born[source], 'first_source_tick':edge['tick'],**stats,
                'late':late,'retained_late':late and stats['birth_length'] >= 32 and 10*stats['retained_bytes'] >= 9*stats['birth_length']}

    def transfer_summary(self) -> dict[str,Any]:
        renewals = list(self.transfer_renewals.values())
        return {'qualifying_transfers':sum(e['rooted_transfer'] for e in self.edges),
            'transfer_renewing_descendants':len(renewals),
            'serial_transfers':sum(e['rooted_transfer'] and bool(e['source_nonrelocation_depth']) for e in self.edges),
            'max_nonrelocation_depth':max((x for x in self.transfer_depth.values() if x is not None),default=0),
            'max_relocation_depth':max(self.relocation_depth.values(),default=0),
            'late_transfer_renewing_descendants':sum(r['late'] for r in renewals),
            'retained_late_transfer_renewals':sum(r['retained_late'] for r in renewals),
            'transfer_renewals':renewals, 'transfer_edges':[{k:v for k,v in e.items() if k not in ('productive','orphan_source','source_depth','child_depth','origin')} for e in self.edges],
            'transfer_retention_distribution':sorted(r['retention'] for r in renewals),
            'transfer_birth_length_distribution':sorted(r['birth_length'] for r in renewals),
            'orphan_transfers':sum(e['transfer_orphan'] for e in self.edges)}

class BoundaryReplay:
    def __init__(self, initial: dict[str, Any], material: list[dict[str, str]], policy: str, horizon: int = 5000, initial_order: list[int] | None = None, disposition: str = "RETAIN"):
        require(disposition in ("RETAIN", "RETIRE"), "source disposition")
        require(policy in ('IMMEDIATE','DELAY500'), 'boundary policy')
        self.policy, self.horizon = policy, horizon
        self.source = SourceReplay(initial)
        self.retired_dispatch = False
        self.disposition = disposition
        self.transactions: list[dict[str, Any]] = []
        self.list_transactions: dict[int,dict[str,list[int]]] = {}
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
        elif row['event'] == 'RETIRE':
            require(self.dispatch is not None and self.phase == 'dispatch' and self.disposition == 'RETIRE', 'retirement outside dispatch/policy')
            require(not self.retired_dispatch and bool(self.transactions), 'duplicate retirement')
            transaction = self.transactions[-1]
            require(transaction['index'] == target-1 and transaction['eligible'] and participants == [transaction['source']], 'ineligible/wrong-source retirement')
            require(transaction['child'] in self.children, 'retirement before admission/BIRTH')
            self.retired_dispatch = True
        else:
            require(self.dispatch is not None and self.phase == 'dispatch', 'material outside dispatch')
            assert self.dispatch is not None
            active, passive, opcode = self.dispatch
            require(set(participants) == {active, passive} and row['event'] == ('COPY' if opcode == ord('=') else 'CLEAVE' if opcode == ord('%') else ''), 'opcode/material mismatch')
        self.source.step(row)
        if row['event'] == 'CLEAVE':
            edge = self.source.edges[-1] if row['outcome'] == 'PLACED' else None
            self.transactions.append({'index':target, 'tick':self.tick, 'active':self.dispatch[0] if self.dispatch else -1,
                'passive':self.dispatch[1] if self.dispatch else -1, 'eligible':bool(edge and edge['transfer_eligible']),
                'source':edge['source'] if edge else -1, 'child':edge['child'] if edge else -1})
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
            require(self.cursor == self.dispatch_cursor+int(opcode in (ord('='),ord('%')))+int(self.retired_dispatch), 'missing/spurious opcode material event')
            if opcode == ord('%'):
                tx = self.source.transactions[-1]
                native_alive = set(tx['after']) & set(tx['before'])
                native_removed = set(tx['before']) - native_alive
                nb = self.now.copy()
                xb = self.next + self.append + ([i for i in (a,b) if i in native_alive] if native_removed else [])
                source = self.transactions[-1]['source']
                survivor = next((i for i in (a,b) if i != source and i in native_alive),-1)
                na = [i for i in nb if i not in (source,survivor)] if self.retired_dispatch else nb.copy()
                xa = ([i for i in xb if i not in (source,survivor)] + ([survivor] if survivor >= 0 else [])) if self.retired_dispatch else xb.copy()
                self.list_transactions[self.transactions[-1]['index']] = dict(now_before=nb,next_before=xb,now_after=na,next_after=xa)
                require(bool(self.transactions), 'missing boundary transaction')
                require(self.retired_dispatch == (self.transactions[-1]['eligible'] and self.disposition == 'RETIRE'), 'eligible retirement bijection')
            self.retired_dispatch = False
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


def diagnostic_run(directory: Path, expected: list[dict[str, Any]], route: str = 'recycle', *,
                nsteps: int = 5000, exit_status: int = 0, maxl0: int = c.MAXL0) -> dict[str, Any]:
    require(route == 'recycle', 'SM-H001 requires recycle')
    inherited = d.analyze_run(directory, expected, route, nsteps=nsteps, exit_status=exit_status, maxl0=maxl0)
    # Canonicalize native CSV as well as the inherited material CSVs.
    native = c.canonical_rows(directory / 'lineage_events001.csv', EVENT_COLUMNS)
    c.canonical_rows(directory / 'lineage_snapshots001.csv', SNAPSHOT_COLUMNS)
    initial = c.initial_material(expected, 'histogram', 0, maxl0)
    buffers = c.canonical_rows(directory / 'conservation_buffers002.csv', c.BUFFER_COLUMNS)
    tick_zero = {r['id']: r['full_buffer_hex'] for r in buffers if r['tick'] == '0' and r['event'] == 'CHECKPOINT'}
    require(tick_zero == initial['buffers'], 'source tick-zero full map')
    initial['buffers'] = tick_zero
    replay = SourceReplay(initial)
    for row in c.canonical_rows(directory / 'material_events002.csv', d.JOURNAL_COLUMNS):
        replay.step(row)
    end = inherited['end_timestep']
    end_map = {integer(r['id']): c.full_buffer(r['full_buffer_hex'], maxl0) for r in buffers if r['event'] == 'END'}
    require(replay.material.buffers == end_map and len(end_map) == inherited['end_population'], 'source END full map/population')
    require(replay.material.seen == {integer(r['child_id']) for r in native if r['event'] != 'END'}, 'source/native identity history')
    replay.native_roles([r for r in native if r['event'] == 'BIRTH'])
    return {**inherited, **replay.summary(end)}


def verify_source_transactions(replay: BoundaryReplay, rows: list[dict[str,str]], native: list[dict[str,str]]) -> dict[str,Any]:
    """Independent geometry, admission order, counters and eligible/commit bijection.

    The ordered scheduling machine proves list transitions and survivor unbinding;
    the full material replay proves each intermediate buffer and each pool return.
    """
    coords = {integer(r['child_id']):(integer(r['x']),integer(r['y'])) for r in native if r['event'] != 'END'}
    require(all(0 <= x < 40 and 0 <= y < 40 for x,y in coords.values()), 'grid bounds')
    occupied = {i:coords[i] for i in replay.source.initial_ids}
    require(len(set(occupied.values())) == len(occupied), 'initial grid collision')
    require(len(rows) == len(replay.source.transactions), 'missing/duplicate source transaction')
    source_by_index = {integer(r['material_index']):r for r in rows}
    require(len(source_by_index) == len(rows), 'duplicate source transaction link')
    eligible_count = committed = proposals = 0
    roles: Counter[str] = Counter()
    remnants: list[dict[str,Any]] = []
    txs = iter(replay.source.transactions)
    for material in replay.material:
        before_ids,after_ids = set(d.ids(material['before_ids'])),set(d.ids(material['after_ids']))
        require(before_ids <= occupied.keys(), 'dead grid participant')
        new = after_ids-before_ids
        for child in new:
            require(coords[child] not in occupied.values(), 'admission from occupied/new retirement vacancy')
            occupied[child] = coords[child]
        if material['event'] == 'CLEAVE':
            tx = next(txs); r = source_by_index[integer(material['index'])]
            require(set(r) == set(SOURCE_COLUMNS), 'source schema')
            before,after = tx['before'],tx['after']
            child = next(iter(new)) if new else -1
            source,offset = h1.infer_suffix(before,after,child) if new else (-1,-1)
            eligible = child >= 0 and offset > 0 and source in after and any(after[source])
            decision = ('RETIRE' if replay.disposition == 'RETIRE' else 'RETAIN') if eligible else 'INELIGIBLE'
            proposals += 1; eligible_count += eligible; committed += decision == 'RETIRE'
            active,passive = integer(r['active']),integer(r['passive'])
            require(active != passive and {active,passive} == before_ids, 'source transaction roles')
            flow_source,flow_offset = integer(r['flow_source']),integer(r['flow_offset'])
            require(flow_source in before and flow_offset < len(before[flow_source]), 'flow proposal bounds/source')
            if material['outcome'] == 'NO_CHANGE': require(flow_offset >= len(h1.visible(before[flow_source])), 'spurious unchanged cleavage')
            else:
                inferred = h1.infer_suffix(before,after,child if new else None)
                require((flow_source,flow_offset) == inferred, 'independent proposal/source attribution')
            if new: require(active in h1.suffix_cleanup_orders(before,after,source,offset,child), 'source cleanup roles')
            survivor = next((i for i in (active,passive) if i != source and i in after),-1) if decision == 'RETIRE' else -1
            remnant = after.get(source,b'')
            dispatch = replay.transactions[proposals-1]
            expected = {'tick':integer(material['tick']),'material_index':integer(material['index']),
                'active':dispatch['active'],'passive':dispatch['passive'],
                'source':source,'offset':offset,'child':child,
                'eligible_tick':b1.eligibility(integer(material['tick']),replay.policy,replay.horizon) if new else 0,
                'source_x':coords[source][0] if source in after else -1,'source_y':coords[source][1] if source in after else -1,
                'child_x':coords[child][0] if new else -1,'child_y':coords[child][1] if new else -1,
                'survivor':survivor,'proposals':proposals,'eligible':eligible_count,'committed':committed}
            for k,v in expected.items(): require(r[k] == str(v), 'source transaction '+k)
            require(r['decision'] == decision and r['remnant_hex'] == remnant.hex().upper(), 'retirement decision/remnant')
            nb,xb,na,xa = (ordered_ids(r[k]) for k in ('now_before','next_before','now_after','next_after'))
            require({k:ordered_ids(r[k]) for k in ('now_before','next_before','now_after','next_after')} == replay.list_transactions[expected['material_index']], 'ordered boundary/source list crosscheck')
            require(not set(nb)&set(xb) and not set(na)&set(xa), 'duplicate list ownership')
            require(set(nb+xb) <= occupied.keys(), 'dead list entry before retirement')
            if decision == 'RETIRE':
                require(na == [i for i in nb if i not in (source,survivor)] and
                        xa == [i for i in xb if i not in (source,survivor)] + ([survivor] if survivor >= 0 else []), 'retirement survivor/list transition')
                require(child in xb and xa.index(child) < (xa.index(survivor) if survivor >= 0 else len(xa)), 'child-before-survivor admission order')
                roles['active' if source == active else 'passive'] += 1
                remnants.append({'source':source,'tick':expected['tick'],'full_buffer_hex':r['remnant_hex'],
                                 'histogram':d.histogram({source:remnant}),'length':sum(b != 0 for b in remnant)})
            else: require(nb == na and xb == xa, 'RETAIN changed lists')
        for idx in before_ids-after_ids: del occupied[idx]
    require(committed == replay.source.material.retirements, 'commit counter/bijection')
    returned = [sum(r['histogram'][s] for r in remnants) for s in range(33)]
    require(returned == replay.source.material.retirement_returns, 'exact full retirement return')
    require(set(occupied) == replay.source.material.buffers.keys(), 'END grid roster')
    return {'retirement_proposals':proposals,'retirement_eligible':eligible_count,'retirements':committed,
            'fatal_enforcement_errors':0,'retirement_source_roles':dict(roles),'retirement_remnants':remnants,
            'retirement_returns':returned,'retirement_exposed':eligible_count >= 100 and committed >= 100}


def analyze_run(directory: Path, expected: list[dict[str,Any]], *, policy: str, nsteps: int = 5000, exit_status: int = 0) -> dict[str,Any]:
    require(policy in ARMS, 'factorial arm')
    require(exit_status == 0, 'SM-B002 fatal process; unevaluable')
    stderr = directory/'stderr.txt'
    if stderr.exists():
        require(not any(marker in stderr.read_bytes() for marker in (b'SM-B002 fatal enforcement', b'SM-B002 unevaluable', b'SM-C001 integrity failure', b'SM-B001 boundary failure')), 'SM-B002 fatal diagnostic; unevaluable')
    schedule,disposition = policy.split('_')
    diagnostic = diagnostic_run(directory,expected,nsteps=nsteps,exit_status=exit_status)
    diagnostic.update(m1.sequence_endpoints(diagnostic))
    native = c.canonical_rows(directory/'lineage_events001.csv',EVENT_COLUMNS)
    initial_order = [integer(r['child_id']) for r in native if r['event'] == 'INIT']
    replay = BoundaryReplay(c.initial_material(expected,'histogram',0),
        c.canonical_rows(directory/'material_events002.csv',d.JOURNAL_COLUMNS),schedule,nsteps,initial_order,disposition)
    for row in boundary_rows(directory/'scheduling_events001.csv'): replay.step(row)
    boundary = replay.summary(diagnostic['end_timestep'])
    require([{k:v for k,v in e.items() if k != 'source_role'} for e in diagnostic['source_edges']] == replay.source.edges,'independent source DAG crosscheck')
    source = verify_source_transactions(replay,c.canonical_rows(directory/'source_events006.csv',SOURCE_COLUMNS),native)
    diagnostic['scheduling_released_productive_sources'] = boundary.pop('released_productive_sources')
    diagnostic['SM_B001_transfer_diagnostics'] = b1.transfer_endpoints({**diagnostic,**boundary},replay.source.initial_ids)
    # Explicitly scoped: event-local H001 credit precedes linked retirement.
    result = {'pre_retirement_H001_diagnostic_credit':diagnostic, **boundary, **source, **replay.source.transfer_summary(),
        'end_timestep':diagnostic['end_timestep'],'end_population':diagnostic['end_population'],
        'net_population_change':diagnostic['end_population']-len(expected),
        'extinction_time':diagnostic['extinction_time'],'native_births':diagnostic['native_births'],
        'native_decays':sum(r['event'] == 'DECAY' for r in replay.material),
        'end_arrays':diagnostic['end_arrays'],'end_counters':diagnostic['end_counters'],
        'surviving_material_sources':len({e['source'] for e in replay.source.edges}&set(replay.source.material.buffers)),
        'repeat_source_production':dict(Counter(e['source'] for e in replay.source.edges)),
        'zero_residual':diagnostic['zero_residual']}
    rooted = [e for e in replay.source.edges if e['rooted_transfer']]
    result.update(m1.sequence_metrics([h1.visible(bytes.fromhex(e['birth_buffer_hex'])) for e in rooted],'transfer'))
    return result


def output_names(end: int) -> set[str]:
    return b1.output_names(end) | LOGS


def continuity(row: dict[str,Any] | None) -> bool:
    return row is not None and all(row.get(k,-1) >= n for k,n in zip(ENDPOINTS,THRESHOLDS,strict=True))


SCALARS = tuple(dict.fromkeys((*ENDPOINTS,*b1.SCALARS,*(f'transfer_{k}' for k in m1.SEQUENCE_SCALARS),'retirement_proposals','retirement_eligible','retirements',
    'native_decays','net_population_change','end_population','surviving_material_sources','orphan_transfers','max_relocation_depth')))


def scalar_values(row: dict[str,Any] | None) -> dict[str,Any]:
    if row is None: return {}
    diagnostic = row.get('pre_retirement_H001_diagnostic_credit',{})
    return {**diagnostic,**diagnostic.get('SM_B001_transfer_diagnostics',{}),**row}


def comparisons(left: dict[str,Any] | None, right: dict[str,Any] | None) -> dict[str,Any]:
    l,r = scalar_values(left),scalar_values(right)
    result: dict[str,Any] = {}
    for k in SCALARS:
        delta = l[k]-r[k] if l.get(k) is not None and r.get(k) is not None else None
        result[k] = {'difference':delta,'direction':'missing' if delta is None else 'left_greater' if delta>0 else 'right_greater' if delta<0 else 'tie'}
    diagnostic_keys = set(m1.SCALARS) | {'surviving_qualifying_descendants'}
    result['pre_retirement_H001_diagnostic_credit'] = {k:result.pop(k) for k in list(result) if k in diagnostic_keys}
    return result


def distribution_comparisons(left: dict[str,Any] | None, right: dict[str,Any] | None) -> dict[str,Any]:
    result: dict[str,Any] = {}
    for key in ('productive_length_distribution','renewing_length_distribution','retention_distribution',
                'transfer_length_distribution','transfer_retention_distribution','transfer_birth_length_distribution'):
        l,r = (Counter(str(x) for x in scalar_values(row).get(key,[])) for row in (left,right))
        result[key] = {v:{'left':l[v],'right':r[v],'difference':l[v]-r[v]} for v in sorted(l.keys()|r.keys())}
    result['pre_retirement_H001_diagnostic_credit'] = {k:result.pop(k) for k in list(result) if not k.startswith('transfer_')}
    return result


def outcomes(results: list[dict[str,Any]], failures: list[dict[str,Any]], *, mechanics: bool = True) -> dict[str,Any]:
    by = {(r['condition'],r['seed']):r for r in results}
    integrity = mechanics and not failures and len(results) == len(by) == 80 and set(by) == set(MATRIX) and all(r.get('boundary_errors') == 0 and r.get('fatal_enforcement_errors') == 0 and r.get('zero_residual') is True for r in results)
    arms = {arm:{'continuity_count':sum(continuity(by.get((arm,s))) for s in SEEDS),
        'exposed_runs':sum(by.get((arm,s),{}).get('retirement_eligible',0) >= 100 and by.get((arm,s),{}).get('retirements',0) >= 100 for s in SEEDS)} for arm in ARMS}
    pairs = []
    for seed in SEEDS:
        entry: dict[str,Any] = {'seed':seed}
        for schedule in ('IMMEDIATE','DELAY500'):
            retain,retire = (by.get((schedule+'_'+d,seed)) for d in ('RETAIN','RETIRE'))
            entry[schedule] = {'retain':continuity(retain),'retire':continuity(retire),
                'retain_only':continuity(retain) and not continuity(retire),'comparisons':comparisons(retain,retire),
                'extinction_times':{'retain':retain.get('extinction_time') if retain else None,'retire':retire.get('extinction_time') if retire else None},
                'distribution_comparisons':distribution_comparisons(retain,retire),
                'pool_waste_differences':{k:[x-y for x,y in zip(retain['end_arrays'][k],retire['end_arrays'][k],strict=True)] if retain and retire and 'end_arrays' in retain and 'end_arrays' in retire else None for k in ('pool','waste')},
                'differences':{k:retain[k]-retire[k] if retain and retire else None for k in ENDPOINTS}}
        entry['scheduling_comparisons'] = {d:comparisons(by.get(('IMMEDIATE_'+d,seed)),by.get(('DELAY500_'+d,seed))) for d in ('RETAIN','RETIRE')}
        entry['interaction_differences'] = {k:entry['IMMEDIATE']['differences'][k]-entry['DELAY500']['differences'][k] if entry['IMMEDIATE']['differences'][k] is not None and entry['DELAY500']['differences'][k] is not None else None for k in ENDPOINTS}
        pairs.append(entry)
    control = all(arms[a]['continuity_count'] >= 16 for a in ARMS[:2])
    exposure = all(arms[a]['exposed_runs'] >= 16 for a in ARMS[2:])
    immediate,delayed = (arms[a]['continuity_count'] for a in ARMS[2:])
    strong_i = immediate <= 4 and sum(p['IMMEDIATE']['retain_only'] for p in pairs) >= 16
    strong_d = delayed <= 4 and sum(p['DELAY500']['retain_only'] for p in pairs) >= 16
    branch = (1 if not integrity else 2 if not control else 3 if not exposure else
              4 if immediate >= 16 and delayed >= 16 else 5 if strong_i and delayed >= 16 else
              6 if strong_d and immediate >= 16 else 7 if strong_i and strong_d else 8)
    names = ['Unevaluable integrity','Valid concurrent-control failure','Inadequate retirement exposure',
        'Retention not required across schedules','Immediate-only retention dependence','Delayed-only retention dependence',
        'Strong retention dependence across schedules','Intermediate response']
    return {'branch':branch,'decision':names[branch-1],'integrity':integrity,'arms':arms,'pairs':pairs,
        'run_denominator':80,'arm_denominator':20,'paired_denominator':20,
        'admission_design_authorized':branch >= 4,'admission_execution_authorized':False,
        'interaction_scope':'Descriptive paired difference of differences; threshold categories are not a formal interaction test.',
        'runs':results,'failures':failures}

def analyze_campaign(manifest: Path) -> dict[str, Any]:
    from experiments.stringmol import retirement_workflow as w
    results: list[dict[str,Any]]=[]; failures: list[dict[str,Any]]=[]
    try:
        data=w.verify_preparation(manifest); w.verify_launch(manifest)
        require(w.read(manifest.parent/'campaign.json') == {'input_manifest':w.record(manifest),'workers':6,'launch_record':w.record(manifest.parent/'launch.json')}, 'campaign identity')
        receipts=w.read(manifest.parent/'campaign-results.json'); require(len(receipts) == 80,'incomplete campaign')
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
