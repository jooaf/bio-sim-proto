"""Strict streaming existing-log measurement; no simulation/replay imports."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Iterator, cast

from experiments.stringmol import xl_renewal_synthesis as x

SCHEDULE = 'event,tick,index,id,other,active,passive,source,eligible_tick,policy,count,selected,outcome,opcode,owner,offset,material_index,ids'
MATERIAL = 'tick,index,event,outcome,before_ids,after_ids,changes,proposal'
ROLE_COUNTERS = ('source_actions_active', 'source_actions_passive', 'source_actions_owner')
COUNTERS = ('searches', 'empty_searches', 'search_candidates', 'encounter_initiator',
            'encounter_partner', 'binding_active', 'binding_passive', 'dispatch_active',
            'dispatch_passive', 'copy_active', 'copy_passive', 'cleave_active', 'cleave_passive')


def ids(value: str) -> list[int]:
    result = [x.integer(v) for v in value.split(';')] if value else []
    x.require(len(result) == len(set(result)), 'duplicate roster ID')
    return result


def stream(path: Path, columns: str) -> Iterator[dict[str, str]]:
    # Same canonical ASCII format as frozen verifier, bounded-memory parser.
    names = columns.split(',')
    with path.open('rb') as handle:
        x.require(handle.readline() == (columns + '\n').encode(), 'CSV schema: ' + str(path))
        for raw in handle:
            x.require(raw.endswith(b'\n') and b'\r' not in raw and b'"' not in raw, 'noncanonical CSV')
            fields = raw[:-1].decode('ascii').split(',')
            x.require(len(fields) == len(names), 'CSV field count')
            yield dict(zip(names, fields, strict=True))


@dataclass
class Child:
    id: int
    birth_tick: int
    birth_order: int
    host: bool
    rooted: bool
    death_tick: int | None = None
    death_order: int | None = None
    death_cause: str | None = None
    first_tick: int | None = None
    first_order: int | None = None
    active_tick: int | None = None
    active_order: int | None = None
    success_tick: int | None = None
    success_order: int | None = None
    ever_active_success: bool = False
    first_role: str | None = None
    first_owner: int | None = None
    first_partner: int | None = None
    counts: Counter[str] = field(default_factory=Counter)
    before: Counter[str] | None = None

    def row(self, end_order: int) -> x.Obj:
        end_tick = self.death_tick if self.death_tick is not None else 5000
        first_end = self.first_tick if self.first_tick is not None else end_tick
        result: x.Obj = dict(id=self.id, birth_tick=self.birth_tick, birth_order=self.birth_order,
            exact_host_birth=self.host, rooted=self.rooted, death_tick=self.death_tick,
            death_order=self.death_order, death_cause=self.death_cause,
            alive_END=self.death_tick is None, end_order=self.death_order or end_order,
            first_source_tick=self.first_tick, first_source_order=self.first_order,
            first_source_role=self.first_role, first_source_instruction_owner=self.first_owner,
            first_source_partner=self.first_partner,
            first_source_is_owner=None if self.first_owner is None else self.first_owner == self.id,
            first_source_owner_role=None if self.first_owner is None else
                ('active' if (self.first_owner == self.id) == (self.first_role == 'active') else 'passive'),
            first_active_tick=self.active_tick, first_active_order=self.active_order,
            first_success_participation_tick=self.success_tick,
            first_success_participation_order=self.success_order,
            ever_active_success=self.ever_active_success, ever_source=self.first_tick is not None,
            followup_ticks=end_tick-self.birth_tick,
            pre_first_or_end_ticks=first_end-self.birth_tick,
            no_event_termination=('renewed' if self.first_tick is not None else
                'death_competing' if self.death_tick is not None else 'END_administrative'))
        before = self.before if self.before is not None else self.counts
        for key in COUNTERS:
            result[key] = self.counts[key]
            result['pre_' + key] = before[key]
        clock = first_end-self.birth_tick
        result['pre_searches_per_tick'] = before['searches']/clock if clock else None
        return result


@dataclass(frozen=True)
class Dispatch:
    tick: int
    order: int
    active: int
    passive: int
    owner: int
    opcode: int
    cursor: int
    snapshots: dict[int, Counter[str]]


@dataclass
class Reduced:
    individuals: list[x.Obj]
    actions: list[x.Obj]
    totals: Counter[str]
    end_ids: set[int]


def reduce(schedule: Iterator[dict[str, str]], r: x.Renewal, births: dict[int, x.Birth],
           source_rows: list[dict[str, str]], cleaves: dict[int, tuple[int, str]],
           deaths: dict[int, tuple[int, str, set[int]]]) -> Reduced:
    edges = {x.num(e['child']): e for e in r.edges}
    sources: dict[int, dict[str, str]] = {}
    for s in source_rows:
        mi = x.integer(s['material_index'])
        x.require(mi not in sources, 'duplicate source material link')
        sources[mi] = s
    children: dict[int, Child] = {}
    live: set[int] = set()
    seen: set[int] = set()
    censored: set[int] = set()
    used_source: set[int] = set()
    used_death: set[int] = set()
    born: set[int] = set()
    actions: list[x.Obj] = []
    totals: Counter[str] = Counter()
    pending: Dispatch | None = None
    pending_birth: int | None = None
    pending_search: tuple[int, int, int, int, int] | None = None
    order = tick = 0
    ended = False
    started = False
    cursor = 0

    def alive(idx: int) -> None:
        x.require(idx in live, 'missing/dead participant')

    def bump(idx: int, key: str, amount: int = 1) -> None:
        alive(idx)
        if idx in children:
            children[idx].counts[key] += amount

    for row in schedule:
        event = row['event']
        t, n = x.integer(row['tick']), x.integer(row['index'])
        x.require(not ended and n == order+1 and tick <= t <= 5000, 'schedule chronology/END')
        x.require(row['policy'] == 'IMMEDIATE', 'schedule policy')
        tick, order = t, n
        idx = int(row['id'])
        if event == 'START':
            x.require(not started and n == 1 and t == 0 and set(ids(row['ids'])) == set(range(140)), 'START founders')
            live = set(ids(row['ids']))
            seen = live.copy()
            started = True
            continue
        x.require(started, 'missing START')
        x.require(pending_search is None or event == 'ENCOUNTER', 'missing immediate encounter')
        if event == 'SEARCH':
            count = x.integer(row['count'])
            other = int(row['other'])
            x.require((count == 0) == (other == -1), 'empty search partner')
            if other >= 0:
                alive(other)
                x.require(other != idx and 0 <= int(row['selected']) < count and row['outcome'] == 'SELECTED', 'search selection')
                pending_search = (t, idx, other, count, int(row['selected']))
            else:
                x.require(row['selected'] == '-1' and row['outcome'] == 'EMPTY', 'empty search fields')
            bump(idx, 'searches')
            bump(idx, 'search_candidates', count)
            if not count:
                bump(idx, 'empty_searches')
            totals['searches'] += 1
            totals['empty_searches'] += int(count == 0)
        elif event == 'ENCOUNTER':
            other = x.integer(row['other'])
            x.require(other != idx and pending_search == (t, idx, other, x.integer(row['count']), x.integer(row['selected'])), 'encounter/search join')
            pending_search = None
            bump(idx, 'encounter_initiator')
            bump(other, 'encounter_partner')
            totals['encounters'] += 1
            x.require(row['outcome'] in ('BOUND', 'UNBOUND'), 'encounter outcome')
            if row['outcome'] == 'BOUND':
                a, p = x.integer(row['active']), x.integer(row['passive'])
                x.require({a, p} == {idx, other}, 'binding roles')
                bump(a, 'binding_active')
                bump(p, 'binding_passive')
                totals['bindings'] += 1
        elif event == 'DISPATCH':
            a, p, owner, opcode, mi = (x.integer(row[k]) for k in ('active', 'passive', 'owner', 'opcode', 'material_index'))
            alive(a)
            alive(p)
            x.require(a != p and owner in (a, p) and pending is None and mi == cursor, 'dispatch join')
            pending = Dispatch(t, n, a, p, owner, opcode, mi,
                {i: children[i].counts.copy() for i in (a, p) if i in children})
            pending_birth = None
            for i, role in ((a, 'active'), (p, 'passive')):
                bump(i, 'dispatch_' + role)
                if opcode in (61, 37):
                    bump(i, ('copy_' if opcode == 61 else 'cleave_') + role)
            if a in children and children[a].active_order is None:
                children[a].active_tick, children[a].active_order = t, n
        elif event == 'BIRTH':
            x.require(pending is not None and pending.opcode == 37 and pending_birth is None, 'birth without cleavage')
            d = cast(Dispatch, pending)
            mi, source = x.integer(row['material_index']), x.integer(row['source'])
            x.require(idx not in seen and idx in edges and idx in births and idx >= 140, 'birth identity')
            e, b = edges[idx], births[idx]
            x.require((x.integer(row['active']), x.integer(row['passive'])) == (d.active, d.passive), 'birth dispatch roles')
            x.require(source in (d.active, d.passive) and source == x.num(e['source']) and
                      mi == x.num(e['index']) and t == b.tick == x.num(e['tick']) and
                      b.participants == frozenset((d.active, d.passive)), 'birth edge join')
            x.require(mi == d.cursor+1 and mi in sources and cleaves.get(mi) == (t, 'PLACED'), 'birth material disposition')
            s = sources[mi]
            x.require(int(s['child']) == idx and int(s['source']) == source, 'birth source journal')
            children[idx] = Child(idx, t, n, b.sequence == x.HOST, x.boolean(e['rooted_transfer']))
            live.add(idx)
            seen.add(idx)
            born.add(idx)
            pending_birth = idx
            totals['placed'] += 1
            if x.boolean(e['rooted_transfer']):
                action: x.Obj = dict(tick=t, birth_order=n, dispatch_order=d.order,
                    complete_order=None, material_index=mi, child=idx, source=source,
                    source_nonfounder=source >= 140, active=d.active, passive=d.passive,
                    source_role='active' if source == d.active else 'passive',
                    instruction_owner=d.owner, source_is_instruction_owner=source == d.owner,
                    instruction_owner_role='active' if d.owner == d.active else 'passive',
                    partner=d.passive if source == d.active else d.active)
                actions.append(action)
                if source in children and children[source].first_order is None:
                    c = children[source]
                    c.first_tick, c.first_order = t, n
                    c.first_role = cast(str, action['source_role'])
                    c.first_owner = d.owner
                    c.first_partner = cast(int, action['partner'])
                    c.before = d.snapshots[source]
            for i in (d.active, d.passive):
                if i in children:
                    c = children[i]
                    if c.success_order is None:
                        c.success_tick, c.success_order = t, n
                    c.ever_active_success |= i == d.active
        elif event == 'DEATH':
            mi = x.integer(row['material_index'])
            alive(idx)
            x.require(mi in deaths and deaths[mi][0:2] == (t, row['outcome']) and idx in deaths[mi][2], 'death material join')
            x.require(row['outcome'] in ('DECAY', 'CLEAVE'), 'death cause')
            used_death.add(idx)
            live.remove(idx)
            if idx in children:
                c = children[idx]
                c.death_tick, c.death_order, c.death_cause = t, n, row['outcome']
            cursor = mi
        elif event == 'COMPLETE':
            x.require(pending is not None, 'COMPLETE without dispatch')
            d = cast(Dispatch, pending)
            mi = x.integer(row['material_index'])
            x.require(t == d.tick and (int(row['active']), int(row['passive'])) == (d.active, d.passive) and mi >= d.cursor, 'COMPLETE join')
            if d.opcode == 37:
                x.require(mi in sources and mi not in used_source and d.cursor+1 in cleaves, 'cleavage source completion join')
                s = sources[mi]
                outcome = cleaves[d.cursor+1]
                x.require(outcome[0] == t and int(s['tick']) == t and
                          (int(s['active']), int(s['passive'])) == (d.active, d.passive), 'cleavage tick/roles')
                x.require((outcome[1] == 'PLACED') == (pending_birth is not None) and
                          int(s['child']) == (pending_birth if pending_birth is not None else -1), 'cleavage child/outcome')
                if pending_birth is not None:
                    for action in actions[-1:]:
                        if action['child'] == pending_birth:
                            action['complete_order'] = n
                x.require(mi == d.cursor+1, 'cleavage cursor advance')
                if pending_birth is None:
                    x.require(int(s['source']) == -1, 'failed/nochange has no admitted source')
                totals['cleave_' + outcome[1]] += 1
                used_source.add(mi)
            pending = None
            cursor = mi
        elif event == 'CENSOR':
            alive(idx)
            x.require(t == 5000 and idx in children and idx not in censored, 'CENSOR is END survivor only')
            censored.add(idx)
        elif event == 'END':
            x.require(t == 5000 and pending is None and set(ids(row['ids'])) == live and censored == live & set(children), 'END roster')
            ended = True
        else:
            x.require(event in ('TICK', 'RELEASE', 'SELECT', 'SURVIVE', 'DECAY'), 'unknown event')
            if event == 'DECAY':
                x.require(idx in used_death and idx not in live, 'DECAY follows actual death')
            elif event != 'TICK':
                alive(idx)
    x.require(pending_search is None, 'unfinished search')
    x.require(ended and born == set(edges) == set(births) and used_source == set(sources)
              and len(cleaves) == len(sources), 'incomplete lifecycle/source joins')
    x.require(used_death == set().union(*(v[2] for v in deaths.values())), 'unused material deaths')
    x.require({i for i, c in children.items() if c.first_order is not None} == set(r.first), 'prior renewer set')
    for i, c in children.items():
        x.require(c.first_tick == r.first.get(i), 'prior first-source tick')
    individual_rows = [children[i].row(order) for i in sorted(children)]
    for individual in individual_rows:
        relevant = [act for act in actions if act['source'] == individual['id']]
        individual['source_actions_active'] = sum(act['source_role'] == 'active' for act in relevant)
        individual['source_actions_passive'] = sum(act['source_role'] == 'passive' for act in relevant)
        individual['source_actions_owner'] = sum(act['source_is_instruction_owner'] is True for act in relevant)
    for scope, selected in (('all', actions), ('nonfounder', [act for act in actions if act['source_nonfounder']])):
        totals[scope+'_source_active'] = sum(act['source_role'] == 'active' for act in selected)
        totals[scope+'_source_passive'] = sum(act['source_role'] == 'passive' for act in selected)
        totals[scope+'_source_owner'] = sum(act['source_is_instruction_owner'] is True for act in selected)
    return Reduced(individual_rows, actions, totals, live)


def journals(base: Path) -> tuple[list[dict[str, str]], dict[int, tuple[int, str]], dict[int, tuple[int, str, set[int]]]]:
    sources = list(stream(base/'source_events006.csv', x.SOURCE_COLUMNS))
    cleaves: dict[int, tuple[int, str]] = {}
    deaths: dict[int, tuple[int, str, set[int]]] = {}
    last_tick = index = 0
    for row in stream(base/'material_events002.csv', MATERIAL):
        t, mi = x.integer(row['tick']), x.integer(row['index'])
        x.require(t >= last_tick and mi == index+1, 'material chronology')
        last_tick, index = t, mi
        if row['event'] == 'CLEAVE':
            x.require(row['outcome'] in ('PLACED', 'FAILED', 'NO_CHANGE'), 'cleavage disposition')
            cleaves[mi] = (t, row['outcome'])
        removed = set(ids(row['before_ids'])) - set(ids(row['after_ids']))
        if removed:
            deaths[mi] = (t, row['event'], removed)
    return sources, cleaves, deaths


def cohorts(individuals: list[x.Obj]) -> list[x.Obj]:
    result: list[x.Obj] = []
    for cohort in ('all', 'early', 'late'):
        group = [r for r in individuals if cohort == 'all' or (x.num(r['birth_tick']) >= 2500) == (cohort == 'late')]
        count = len(group)
        m: x.Obj = dict(cohort=cohort, admitted=count,
            renewers=sum(r['ever_source'] is True for r in group),
            active_success=sum(r['ever_active_success'] is True for r in group),
            rooted=sum(r['rooted'] is True for r in group),
            exact_host_birth=sum(r['exact_host_birth'] is True for r in group),
            alive_END=sum(r['alive_END'] is True for r in group),
            death=sum(r['alive_END'] is False for r in group),
            no_event_death=sum(r['no_event_termination'] == 'death_competing' for r in group),
            no_event_END=sum(r['no_event_termination'] == 'END_administrative' for r in group),
            first_source_active=sum(r['first_source_role'] == 'active' for r in group),
            first_source_passive=sum(r['first_source_role'] == 'passive' for r in group),
            first_source_is_owner=sum(r['first_source_instruction_owner'] == r['id'] for r in group),
            followup_ticks=sum(x.num(r['followup_ticks']) for r in group),
            pre_first_or_end_ticks=sum(x.num(r['pre_first_or_end_ticks']) for r in group),
            zero_followup=sum(r['followup_ticks'] == 0 for r in group))
        m['renewal_fraction'] = x.ratio(x.num(m['renewers']), count)
        m['active_success_fraction'] = x.ratio(x.num(m['active_success']), count)
        m['mean_followup_ticks'] = x.num(m['followup_ticks'])/count if count else None
        for key in ROLE_COUNTERS:
            m[key] = sum(x.num(r[key]) for r in group)
        for key in COUNTERS:
            for prefix in ('', 'pre_'):
                m[prefix+key] = sum(x.num(r[prefix+key]) for r in group)
        clock = x.num(m['pre_first_or_end_ticks'])
        m['pre_searches_per_tick'] = x.num(m['pre_searches'])/clock if clock else None
        result.append(m)
    return result


def analyze(out: Path) -> None:
    x.fresh(out)
    # Accepted prior analysis anchors all16 result identities, inventory and decision.
    prior = Path('/tmp/sm/xla-e/final3')
    prior_inputs = x.load(prior/'inputs.json')
    inputs: dict[str, str] = {}
    for name, value in prior_inputs.items():
        path = Path(name)
        if path.is_relative_to(Path('/tmp/sm/xla')):
            current = Path.cwd()/path.relative_to('/tmp/sm/xla')
            portable_code = x.PORTABLE.parent/'sm-xl001-renewal-analysis-v1/export/source'/path.name
            for code in (current, portable_code):
                x.verify(code, x.text(value))
                inputs[str(code)] = x.text(value)
            continue
        x.verify(path, x.text(value))
        inputs[str(path)] = x.text(value)
    x.verify(x.CONTROLS/'decision.json', x.DECISION)
    inventory = x.load(x.PORTABLE/'checksums.json')
    for name in ('metrics.json', 'cells.csv', 'contrasts.csv', 'checkpoints.csv', 'checkpoint_contrasts.csv'):
        a, b = prior/name, Path('/tmp/sm/xla-e/final4')/name
        expected = x.text(x.load(prior/'checksums.json')[name])
        portable = x.PORTABLE.parent/'sm-xl001-renewal-analysis-v1/export/final3'/name
        x.verify(a, expected)
        x.verify(b, expected)
        inputs[str(a)] = inputs[str(b)] = expected
        x.verify(portable, expected)
        inputs[str(portable)] = expected
    for p in (prior/'inputs.json', prior/'checksums.json'):
        inputs[str(p)] = x.digest(p)
    parent_export = x.PORTABLE.parent/'sm-xl001-renewal-parent-review-v1'
    parent_inventory = parent_export/'INVENTORY.json'
    inputs[str(parent_inventory)] = x.digest(parent_inventory)
    entries = x.obj(x.load(parent_inventory)['entries'])
    for name in ('audit.json', 'FINDINGS.md'):
        expected = x.text(x.obj(entries[name])['sha256'])
        for p in (Path('/tmp/sm/xla-parent')/name, parent_export/'files'/name):
            x.verify(p, expected)
            inputs[str(p)] = expected
    for name in ('experiments/stringmol/xl_role_analysis.py', 'tests/test_xl_role_analysis.py',
                 'reports/sm_xl001_role_analysis_spec.md', 'experiments/stringmol/xl_renewal_synthesis.py',
                 'tests/test_xl_renewal_synthesis.py', 'reports/sm_xl001_renewal_analysis_spec.md'):
        p = Path(name).resolve()
        inputs[str(p)] = x.digest(p)
    all_individuals: list[x.Obj] = []
    all_actions: list[x.Obj] = []
    all_cohorts: list[x.Obj] = []
    aggregate: x.Obj = {}
    for cell in x.CELLS:
        base = x.RAW/(cell+'-observed')
        for name in ('scheduling_events001.csv', 'source_events006.csv', 'material_events002.csv', 'lineage_events001.csv'):
            key = f'raw/{cell}-observed/{name}'
            expected = x.text(x.obj(inventory[key])['sha256'])
            for p in (base/name, x.PORTABLE/key):
                x.verify(p, expected)
                inputs[str(p)] = expected
        data = x.load(x.CONTROLS/f'{cell}-observed-replay1/result.json')
        _, births = x.lineage(base/'lineage_events001.csv')
        r = x.renewal(x.obj(data['renewal']), births)
        x.source_check(base/'source_events006.csv', r)
        source, cleaves, deaths = journals(base)
        reduced = reduce(stream(base/'scheduling_events001.csv', SCHEDULE), r, births, source, cleaves, deaths)
        for key in ('searches', 'empty_searches', 'encounters', 'bindings', 'placed'):
            x.require(reduced.totals[key] == data[key], 'verified aggregate '+key)
        x.require(reduced.totals['cleave_FAILED'] == data['failed_placement'] and
                  reduced.totals['cleave_PLACED'] == data['placed'] and
                  len(reduced.end_ids) == data['end_population'], 'verified terminal/cleavage counts')
        end_buffer_ids = {x.integer(row['id']) for row in stream(base/'conservation_buffers002.csv', 'tick,event,id,full_buffer_hex') if row['event'] == 'END'}
        x.require(reduced.end_ids == end_buffer_ids, 'END buffer roster')
        all_individuals.extend(dict(cell=cell, **row) for row in reduced.individuals)
        all_actions.extend(dict(cell=cell, **row) for row in reduced.actions)
        all_cohorts.extend(dict(cell=cell, **row) for row in cohorts(reduced.individuals))
        aggregate[cell] = dict(sorted(reduced.totals.items()))
    contrast: list[x.Obj] = []
    for left_cell, right_cell in (('GL', 'GG'), ('LL', 'LG')):
        for cohort in ('all', 'early', 'late'):
            left = next(r for r in all_cohorts if r['cell'] == left_cell and r['cohort'] == cohort)
            right = next(r for r in all_cohorts if r['cell'] == right_cell and r['cohort'] == cohort)
            row: x.Obj = dict(contrast=left_cell+'-'+right_cell, cohort=cohort)
            for key in left:
                if key not in ('cell', 'cohort'):
                    row[key] = None if left[key] is None or right[key] is None else cast(int | float, left[key])-cast(int | float, right[key])
            contrast.append(row)
    for name, rows in (('individuals', all_individuals), ('source_actions', all_actions), ('cohorts', all_cohorts), ('contrasts', contrast)):
        x.save(out/(name+'.json'), rows)
        x.csv_save(out/(name+'.csv'), rows)
    x.save(out/'aggregates.json', aggregate)
    for name, expected in inputs.items():
        x.verify(Path(name), expected)
    x.save(out/'inputs.json', inputs)
    x.save(out/'checksums.json', {p.name: x.digest(p) for p in sorted(out.iterdir())})


if __name__ == '__main__':
    x.require(len(sys.argv) == 2, 'usage: python -m experiments.stringmol.xl_role_analysis NEW_OUTPUT')
    analyze(Path(sys.argv[1]))
