"""SM-B002 independent material replay, extending frozen decay replay with RETIRE."""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
import re
from typing import Any

from experiments.stringmol import analyze_conservation as c
from experiments.stringmol import conservation_workflow as workflow
from experiments.stringmol.analyze_lineage import EVENT_COLUMNS, SNAPSHOT_COLUMNS, analyze_run as lineage_run, integer, require, rows

EXTRA_ARRAYS = ['waste', 'decay_removed', 'decay_to_pool', 'decay_to_waste', 'residual']
EXTRA_COUNTERS = ['waste_bytes', 'positive_growth_bytes', 'contraction_bytes', 'event_count']
COLUMNS = [*c.COLUMNS, *(f for p in EXTRA_ARRAYS for f in c.fields(p)), *EXTRA_COUNTERS]
JOURNAL_COLUMNS = ['tick', 'index', 'event', 'outcome', 'before_ids', 'after_ids', 'changes', 'proposal']
OUTCOMES = ['BOUNDARY', 'READ_NULL', 'DELETION', 'NOOP', 'ACCEPTED', 'BLOCKED']
LOGS = {'conservation002.csv', 'conservation_buffers002.csv', 'material_events002.csv'}


def ids(text: str) -> list[int]:
    result = [integer(x) for x in text.split(';')] if text else []
    require(result == sorted(set(result)), 'noncanonical journal IDs')
    return result


def histogram(buffers: dict[int, bytes]) -> list[int]:
    counts: Counter[int] = Counter()
    for b in buffers.values():
        counts.update(b)
    return [counts[ord(s)] for s in c.ALPHABET]


def change(before: dict[int, bytes], after_ids: list[int], text: str, size: int) -> dict[int, bytes]:
    result = {i: bytearray(before.get(i, bytes(size))) for i in set(before) | set(after_ids)}
    last = (-1, -1)
    for item in text.split(';') if text else []:
        require(re.fullmatch(r'(0|[1-9][0-9]*):(0|[1-9][0-9]*):[0-9A-F]{2}:[0-9A-F]{2}', item) is not None, 'invalid sparse change')
        a, o, old_hex, new_hex = item.split(':')
        idx, offset, old, new = int(a), int(o), int(old_hex, 16), int(new_hex, 16)
        require((idx, offset) > last and idx in result and offset < size - 1, 'change order/identity/bounds')
        last = (idx, offset)
        require(old != new and result[idx][offset] == old, 'change preimage/noop')
        require(new in set(c.ALPHABET.encode()) | {0}, 'change alphabet')
        result[idx][offset] = new
    require(all(not any(result[i]) for i in set(before) - set(after_ids)), 'removed buffer not zeroed')
    return {i: bytes(result[i]) for i in after_ids}


from experiments.stringmol.analyze_decay import Replay as DecayReplay


class Replay(DecayReplay):
    def __init__(self, initial: dict[str, Any], route: str):
        require(route in {'recycle', 'sequester'}, 'invalid route')
        self.route = route
        self.size = initial['maxl0']
        self.buffers = {int(i): bytes.fromhex(b) for i, b in initial['buffers'].items()}
        self.seen = set(self.buffers)
        self.molecular = initial['molecular'].copy()
        self.initial = initial
        self.arrays = {p: [0] * 33 for p in [*c.LEDGERS, *EXTRA_ARRAYS]}
        self.arrays['pool'] = initial['pool'].copy()
        self.arrays['pool_minimum'] = initial['pool'].copy()
        self.nums = dict.fromkeys([*c.COUNTERS, *EXTRA_COUNTERS], 0)
        self.tick = 0
        self.late_growth = self.late_births = self.early_contraction = self.late_contraction = 0
        self.births: list[tuple[int, int, dict[int,bytes], bytes]] = []
        self.exposure = 0
        self.retirement_returns = [0]*33
        self.retirements = 0
        self.placements: Counter[str] = Counter()

    def step(self, r: dict[str, str]) -> None:
        tick = integer(r['tick'])
        require(tick >= self.tick and integer(r['index'],0,c.LIMIT) == self.nums['event_count'] + 1, 'journal ordering/index')
        self.tick = tick
        before_ids, after_ids = ids(r['before_ids']), ids(r['after_ids'])
        require(set(before_ids) <= self.buffers.keys(), 'unknown/dead participating ID')
        before = {i: self.buffers[i] for i in before_ids}
        after = change(before, after_ids, r['changes'], self.size)
        new_ids = set(after) - set(before)
        require(not new_ids & self.seen, 'journal ID reuse')
        old, new = histogram(before), histogram(after)
        event, outcome = r['event'], r['outcome']
        pool = self.arrays['pool']
        if event == 'COPY':
            require(before_ids == after_ids and len(before_ids) == 2 and outcome in OUTCOMES, 'invalid copy participants/outcome')
            self.nums['attempts'] += 1
            self.nums[c.PARTITION[OUTCOMES.index(outcome)]] += 1
            if outcome == 'ACCEPTED':
                require(before != after and not r['proposal'], 'invalid accepted copy')
                require(sum(a != b for i in before for a,b in zip(before[i], after[i], strict=True)) <= 2, 'accepted copy exceeds distinct changed position limit')
                withdrawals, returns = [0]*33, [0]*33
                for i in before:
                    for a, b in zip(before[i], after[i], strict=True):
                        if a != b:
                            if a: returns[c.ALPHABET.index(chr(a))] += 1
                            if b: withdrawals[c.ALPHABET.index(chr(b))] += 1
                require(sum(withdrawals) <= 2 and sum(returns) <= 2, 'copy exceeds native write limit')
                for s in range(33):
                    self.arrays['copy_withdrawals'][s] += withdrawals[s]
                    self.arrays['copy_returns'][s] += returns[s]
                    pool[s] += returns[s] - withdrawals[s]
                delta = sum(new) - sum(old)
                self.nums['accepted_positive_growth'] += delta > 0
                self.nums['positive_growth_bytes'] += max(0, delta)
                self.nums['contraction_bytes'] += max(0, -delta)
                if 2500 <= tick < 5000:
                    self.late_growth += max(0, delta)
                    self.late_contraction += max(0, -delta)
                else:
                    self.early_contraction += max(0, -delta)
            elif outcome == 'BLOCKED':
                require(before == after and bool(r['proposal']), 'invalid blocked copy')
                proposed = change(before, after_ids, r['proposal'], self.size)
                target = histogram(proposed)
                require(sum(a != b for i in before for a,b in zip(before[i], proposed[i], strict=True)) <= 2, 'blocked copy exceeds write limit')
                missing = [max(0, target[s] - old[s] - pool[s]) for s in range(33)]
                require(any(missing), 'copy blocked without scarcity')
                for s in range(33): self.arrays['missing_blocked_units'][s] += missing[s]
            else:
                require(before == after and not r['proposal'], 'nonchanging copy changed')
        elif event == 'DECAY':
            require(len(before_ids) == 1 and not after_ids and outcome == 'REMOVED' and not r['proposal'], 'invalid decay')
            self.exposure += sum(old) > 0
            for s in range(33):
                self.arrays['decay_returns'][s] += old[s]
                self.arrays['decay_removed'][s] += old[s]
                self.arrays['decay_to_' + ('waste' if self.route == 'sequester' else 'pool')][s] += old[s]
                self.arrays['waste' if self.route == 'sequester' else 'pool'][s] += old[s]
        elif event == 'RETIRE':
            require(len(before_ids) == 1 and not after_ids and outcome == 'REMOVED' and not r['proposal'], 'invalid retirement')
            require(any(old), 'empty retirement')
            self.retirements += 1
            for s in range(33):
                self.retirement_returns[s] += old[s]
                pool[s] += old[s]
        elif event == 'CLEAVE':
            require(len(before_ids) == 2 and outcome in {'PLACED','FAILED','NO_CHANGE'} and not r['proposal'], 'invalid cleavage')
            self.placements[outcome] += 1
            require(len(new_ids) == (1 if outcome == 'PLACED' else 0), 'cleavage child identity')
            if outcome == 'NO_CHANGE': require(before == after, 'no-change cleavage changed')
            require(all(new[s] <= old[s] for s in range(33)), 'cleavage gain')
            if outcome == 'PLACED':
                child = next(iter(new_ids))
                self.births.append((tick, child, before, after[child]))
                self.late_births += 2500 <= tick < 5000
            for s in range(33):
                released = old[s] - new[s]
                self.arrays['cleavage_discard_returns' if outcome == 'PLACED' else 'failed_placement_returns'][s] += released
                pool[s] += released
        else:
            raise ValueError('unknown journal event')
        for i in before: del self.buffers[i]
        self.buffers.update(after)
        self.seen.update(new_ids)
        self.nums['event_count'] += 1
        for s in range(33):
            self.molecular[s] += new[s] - old[s]
        molecular = self.molecular
        for s in range(33):
            self.arrays['pool_minimum'][s] = min(self.arrays['pool_minimum'][s], pool[s])
            require(molecular[s] + pool[s] + self.arrays['waste'][s] == self.initial['total'][s], 'operation conservation')
            require(pool[s] == self.initial['pool'][s] - self.arrays['copy_withdrawals'][s] + self.arrays['copy_returns'][s] + self.arrays['decay_to_pool'][s] + self.arrays['failed_placement_returns'][s] + self.arrays['cleavage_discard_returns'][s] + self.retirement_returns[s], 'pool reconciliation')
        require(all(0 <= n <= c.LIMIT for values in self.arrays.values() for n in values), 'negative/overflow material')
        require(all(0 <= n <= c.LIMIT for n in self.nums.values()), 'counter overflow')

    def checkpoint(self, row: dict[str, str]) -> None:
        molecular = histogram(self.buffers)
        require(molecular == self.molecular, 'replay molecular inventory mismatch')
        arrays = {**self.arrays, 'molecular': molecular, 'initial': self.initial['total']}
        self.nums['waste_bytes'] = sum(arrays['waste'])
        nums = {**self.nums, 'max_residual': 0, 'molecular_bytes': sum(molecular), 'free_bytes': sum(arrays['pool'])}
        expected = {k: str(v) for k,v in nums.items()}
        expected.update({f: str(v) for p, values in arrays.items() for f,v in zip(c.fields(p), values, strict=True)})
        require({k:v for k,v in row.items() if k not in {'tick','event'}} == expected, 'aggregate differs from independent journal replay')
        require(self.nums['boundary_error'] == 0, 'boundary error')


def analyze_run(directory: Path, expected: list[dict[str, Any]], route: str, *, nsteps: int = 5000, exit_status: int = 0, maxl0: int = c.MAXL0) -> dict[str, Any]:
    lineage = lineage_run(directory, expected, nsteps=nsteps, exit_status=exit_status)
    require(not any((directory / n).exists() for n in ('conservation001.csv','conservation_buffers001.csv')), 'v1 files in routed run')
    aggregates = c.canonical_rows(directory / 'conservation002.csv', COLUMNS)
    raw = c.canonical_rows(directory / 'conservation_buffers002.csv', c.BUFFER_COLUMNS)
    journal = c.canonical_rows(directory / 'material_events002.csv', JOURNAL_COLUMNS)
    end = lineage['end_timestep']
    checkpoints = [(t, 'CHECKPOINT') for t in range(0, end, 100)] + [(end, 'END')]
    require([(integer(r['tick']),r['event']) for r in aggregates] == checkpoints, 'checkpoint/END set')
    buffers: dict[tuple[int,str], dict[int,bytes]] = {k:{} for k in checkpoints}
    last = (-1,-1)
    for r in raw:
        key = (integer(r['tick']), r['event'])
        require(key in buffers, 'unknown buffer checkpoint')
        idx = integer(r['id']); order = (checkpoints.index(key),idx)
        require(order > last, 'buffer ordering'); last = order
        buffers[key][idx] = c.full_buffer(r['full_buffer_hex'], maxl0)
    snapshots: dict[int, dict[int,bytes]] = {}
    for r in rows(directory / 'lineage_snapshots001.csv', SNAPSHOT_COLUMNS):
        snapshots.setdefault(integer(r['tick']), {})[integer(r['id'])] = bytes.fromhex(r['sequence_hex'])
    replay = Replay(c.initial_material(expected,'histogram',0,maxl0),route)
    pos = 0
    summaries = []
    for row,key in zip(aggregates,checkpoints,strict=True):
        while pos < len(journal) and integer(journal[pos]['tick']) < key[0]:
            replay.step(journal[pos]); pos += 1
        replay.checkpoint(row)
        require(replay.buffers == buffers[key], 'journal/buffer map mismatch')
        visible = {i:b.split(b'\0',1)[0] for i,b in replay.buffers.items()}
        require(all(visible.values()), 'zero-length extant molecule')
        if key[1] == 'CHECKPOINT': require(visible == snapshots[key[0]], 'journal/lineage snapshot mismatch')
        summaries.append({'tick':key[0], 'event':key[1], 'population':len(visible), 'molecular_bytes':sum(histogram(replay.buffers)), 'pool_bytes':sum(replay.arrays['pool']), 'waste_bytes':sum(replay.arrays['waste']), 'visible_lengths':sorted(map(len,visible.values())), 'descendant_material':sum(sum(b != 0 for b in raw) for i,raw in replay.buffers.items() if str(i) not in replay.initial['buffers']), 'full_lengths':sorted(sum(b != 0 for b in raw) for raw in replay.buffers.values())})
    require(pos == len(journal), 'journal at/after END')
    require(len(replay.buffers) == lineage['end_population'], 'END population')
    births = [r for r in rows(directory / 'lineage_events001.csv', EVENT_COLUMNS) if r['event'] == 'BIRTH']
    require(len(births) == len(replay.births), 'birth journal count')
    for r, (tick, child, parents, raw_child) in zip(births,replay.births,strict=True):
        require(integer(r['timestep']) == tick and integer(r['child_id']) == child, 'birth identity/time')
        require({integer(r['active_id']),integer(r['passive_id'])} == set(parents), 'birth parents')
        for role in ('active','passive'):
            require(bytes.fromhex(r[role+'_sequence_hex']) == parents[integer(r[role+'_id'])].split(b'\0',1)[0], 'birth parent buffer')
        require(bytes.fromhex(r['child_sequence_hex']) == raw_child.split(b'\0',1)[0], 'birth buffer')
    funding = sum(max(0,replay.arrays['copy_withdrawals'][s] - replay.arrays['copy_returns'][s] - replay.arrays['failed_placement_returns'][s] - replay.arrays['cleavage_discard_returns'][s]) for s in range(33))
    return {**lineage, 'G_late':replay.late_growth, 'B_late':replay.late_births, 'L':funding, 'decay_exposure':replay.exposure, 'extinction_time':end if lineage['end_population'] == 0 else None, 'blocked_fraction':replay.nums['scarcity_blocked']/replay.nums['attempts'] if replay.nums['attempts'] else 0.0, 'early_contraction':replay.early_contraction,'late_contraction':replay.late_contraction, 'placements':dict(replay.placements), 'end_counters':replay.nums,'end_arrays':replay.arrays,'conservation':summaries, 'zero_residual':True, 'retirements':replay.retirements, 'retirement_returns':replay.retirement_returns}

