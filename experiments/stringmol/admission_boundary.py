"""SM-B003 ordered scheduling replay, forked without editing frozen B002.

Reconstructs queues, binding roles, eligibility and material lifecycle. VM/RNG
provenance and admission selection still require the separate joined verifier.
"""
from collections import Counter
from typing import Any
from experiments.stringmol import retirement_material as d
from experiments.stringmol.admission_source import SourceReplay
from experiments.stringmol.analyze_lineage import integer, require
from experiments.stringmol.analyze_scheduling import COLUMNS, DEFAULTS, DEFAULT_NUMBERS, NUMERIC, FIELDS, ordered_ids, eligibility

class BoundaryReplay:
    def __init__(self, initial: dict[str, Any], material: list[dict[str, str]], policy: str, horizon: int = 5000, initial_order: list[int] | None = None, disposition: str = "RETAIN"):
        require(disposition == "RETAIN", "admission fixes source disposition to RETAIN")
        require(policy in ('IMMEDIATE','DELAY500'), 'boundary policy')
        self.policy, self.horizon = policy, horizon
        self.source = SourceReplay(initial)
        self.evicted_dispatch = False
        self.failed = False
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
        elif row['event'] == 'EVICT':
            require(self.dispatch is not None and self.phase == 'dispatch' and self.dispatch[2] == ord('%'), 'eviction outside cleavage dispatch')
            require(not self.evicted_dispatch and len(participants) == 1, 'duplicate/invalid dispatch eviction')
            victim = participants[0]
            assert self.dispatch is not None
            require(victim not in self.dispatch[:2] and victim not in self.pairs, 'bound/participating eviction victim')
            require((victim in self.now) != (victim in self.next), 'eviction victim list ownership')
            require(self.source.material.buffers[victim][0] != 0, 'empty-visible eviction victim')
            (self.now if victim in self.now else self.next).remove(victim)
            self.evicted_dispatch = True
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
        require(not self.failed, 'boundary replay already failed')
        try:
            self._step(row)
        except Exception:
            self.failed = True
            raise

    def _step(self, row: dict[str, str]) -> None:
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
            require(self.cursor == self.dispatch_cursor+int(opcode in (ord('='),ord('%')))+int(self.evicted_dispatch), 'missing/spurious opcode material event')
            if opcode == ord('%'):
                tx = self.source.transactions[-1]
                native_alive = set(tx['after']) & set(tx['before'])
                native_removed = set(tx['before']) - native_alive
                nb = self.now.copy()
                xb = self.next + self.append + ([i for i in (a,b) if i in native_alive] if native_removed else [])
                self.list_transactions[self.transactions[-1]['index']] = dict(now_before=nb,next_before=xb,now_after=nb.copy(),next_after=xb.copy())
            self.evicted_dispatch = False
            if opcode in (0,ord('}')): self.unbind(a)
            self.append.extend(i for i in (a,b) if i in self.source.material.buffers)
            self.dispatch=None; self.phase='done'; return
        raise ValueError('unsupported boundary event')

    def summary(self, end: int) -> dict[str, Any]:
        require(not self.failed and self.ended and self.tick+1 == end, 'failed/missing boundary END')
        require(self.source.pending_eviction is None and not self.evicted_dispatch, 'unfinished replacement')
        for child in self.children.values():
            death=child['death']
            child['survived_END']=death is None
            child['final_state']=(('evicted before eligibility' if death['cause'] == 'EVICT' else 'decayed before eligibility') if death is not None and death['tick'] < child['eligible_tick'] else
                'alive but not yet eligible at END' if child['released'] is None else
                'dispatched' if child['dispatches'] else 'bound but never dispatched' if child['bindings'] else
                'encountered but never bound' if child['encounters'] else 'eligible but never encountered')
            if child['released'] is None and death is not None: require(death['cause'] in ('DECAY', 'EVICT'), 'ineligible non-removal death')
        children=list(self.children.values())
        applied=sum(v['eligible_tick'] < self.horizon for v in children)
        survived=sum(v['released'] is not None for v in children)
        participated=sum(v['released'] is not None and v['encounters'] > 0 for v in children)
        productive_sources={e['source'] for e in self.source.edges if e['productive']}
        return {'policy_births':len(children),'physical_child_placements':len(self.source.edges),
            'applied_before_horizon':applied,'survived_to_eligibility':survived,
            'decayed_before_eligibility':sum(v['final_state'] == 'decayed before eligibility' for v in children),
            'evicted_before_eligibility':sum(v['final_state'] == 'evicted before eligibility' for v in children),
            'released_with_participation':participated,'released_without_participation':survived-participated,
            'released_productive_sources':sorted(productive_sources & {v['id'] for v in children if v['released'] is not None}),
            'application_exposed':applied >= 100,'response_exposed':survived >= 100 and participated >= 50,
            **{f'policy_child_{key}':sum(v[key] for v in children) for key in ('encounters','bindings','dispatches')},
            'final_state_counts':dict(Counter(v['final_state'] for v in children)),
            'first_participation_latencies':[v['first_participation'] for v in children if v['first_participation'] is not None],
            'surviving_policy_children':sum(v['survived_END'] for v in children),
            'children':children,'boundary_events':dict(self.events),'boundary_errors':0,
            'occupancy_by_tick':self.occupancy,'boundary_end_ids':sorted(self.next)}

