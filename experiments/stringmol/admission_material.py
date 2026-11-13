"""SM-B003 material replay; frozen B002 analysis remains untouched.

The event kernel is intentionally forked from its validated predecessor: eviction
has its own return ledger and RETIRE is illegal. Shared decoding/checkpoint helpers
never see an eviction relabeled as decay or source retirement.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any
from experiments.stringmol.admission_design import histogram as validate_buffer
from experiments.stringmol import admission_design as design, admission_journal as journal
from experiments.stringmol import analyze_conservation as c
from experiments.stringmol.analyze_lineage import integer, require
from experiments.stringmol.retirement_material import Replay as FrozenReplay, ids, change, histogram, OUTCOMES, JOURNAL_COLUMNS


class Replay(FrozenReplay):
    def __init__(self, initial: dict[str, Any], route: str = "recycle"):
        require(route == "recycle", "admission requires exact recycling")
        require(type(initial['maxl0']) is int and initial['maxl0'] == c.MAXL0, 'admission buffer size')
        for key in ('pool', 'molecular', 'total'):
            require(len(initial[key]) == len(c.ALPHABET) and
                    all(type(n) is int and 0 <= n <= c.LIMIT for n in initial[key]), 'initial material vector')
        for key, raw in initial['buffers'].items():
            require(isinstance(key, str) and str(integer(key, 0, 2**31 - 1)) == key, 'initial identity')
            validate_buffer(bytes.fromhex(raw))
        super().__init__(deepcopy(initial), route)
        require(histogram(self.buffers) == self.molecular, 'initial molecular histogram')
        require(all(m + p == t for m, p, t in zip(self.molecular, self.arrays['pool'], self.initial['total'], strict=True)),
                'initial conservation')
        self.failed = False
        self.eviction_returns = [0] * 33
        self.evictions = 0

    def checkpoint(self, row: dict[str, str]) -> None:
        require(not self.failed, 'replay already failed')
        try:
            super().checkpoint(row)
        except Exception:
            self.failed = True
            raise

    def step(self, r: dict[str, str]) -> None:
        require(not self.failed, 'replay already failed')
        try:
            self._step(r)
        except Exception:
            self.failed = True
            raise

    def _step(self, r: dict[str, str]) -> None:
        require(set(r) == set(JOURNAL_COLUMNS), "material event schema")
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
        elif event == 'EVICT':
            require(len(before_ids) == 1 and not after_ids and outcome == 'REMOVED' and not r['proposal'], 'invalid eviction')
            require(before[before_ids[0]][0] != 0, 'empty-visible eviction')
            self.evictions += 1
            for s in range(33):
                self.eviction_returns[s] += old[s]
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
            require(pool[s] == self.initial['pool'][s] - self.arrays['copy_withdrawals'][s] + self.arrays['copy_returns'][s] + self.arrays['decay_to_pool'][s] + self.arrays['failed_placement_returns'][s] + self.arrays['cleavage_discard_returns'][s] + self.eviction_returns[s], 'pool reconciliation')
        require(all(0 <= n <= c.LIMIT for values in self.arrays.values() for n in values), 'negative/overflow material')
        require(all(0 <= n <= c.LIMIT for n in self.nums.values()), 'counter overflow')
        require(all(0 <= n <= c.LIMIT for n in self.eviction_returns) and 0 <= self.evictions <= c.LIMIT,
                'eviction ledger/counter overflow')


def check_transaction(replay: Replay, begin: journal.Row, resolved: journal.Row,
                      header: journal.Header, state: journal.SelectionState,
                      events: list[dict[str, str]]) -> Replay:
    """Join one proposal to material and queue effects from independent input state.

    Returns a new replay only after all checks pass. The caller must independently
    reconstruct VM/RNG provenance and lifecycle streams; this is not a run verdict.
    """
    require(not replay.failed, 'replay already failed')
    plan = journal.check_selection(begin, header, state)
    journal.check_native_cleanup(begin, resolved, state)
    require(resolved['disposition'] == plan.disposition.value, 'joined disposition')
    before = {slot.actor.identity: slot.actor.buffer for slot in state.slots if slot.actor is not None}
    require(replay.buffers == before and replay.nums['event_count'] == state.material_index, 'joined material prestate')
    admitted = plan.disposition in (design.Disposition.VACANCY, design.Disposition.REPLACEMENT)
    replaced = plan.disposition is design.Disposition.REPLACEMENT
    require([row['event'] for row in events] == (['EVICT', 'CLEAVE'] if replaced else ['CLEAVE']), 'joined event sequence')
    require(all(integer(row['tick']) == state.tick for row in events), 'joined event tick')
    expected = before.copy()
    if replaced:
        if plan.incumbent is None:
            raise ValueError('joined victim missing')
        require(events[0]['before_ids'] == str(plan.incumbent), 'joined eviction victim')
        require(journal.number(resolved['eviction_material_index']) == state.material_index + 1, 'joined eviction index')
        del expected[plan.incumbent]
    else:
        require(resolved['eviction_material_index'] == '', 'spurious joined eviction')
    cleave = events[-1]
    require(ids(cleave['before_ids']) == sorted((state.active, state.passive)), 'joined cleavage participants')
    require(cleave['outcome'] == ('PLACED' if admitted else 'FAILED'), 'joined cleavage outcome')
    source = expected[state.source]
    visible = source.split(b'\0', 1)[0]
    expected[state.source] = source[:state.offset] + bytes(len(visible) - state.offset) + source[len(visible):]
    removed = next((actor for actor in (state.active, state.passive) if not expected[actor][0]), None)
    if removed is not None:
        del expected[removed]
    if admitted:
        suffix = visible[state.offset:]
        expected[state.child] = suffix.ljust(c.MAXL0, b'\0')
    trial = deepcopy(replay)
    for event in events:
        trial.step(event)
    require(trial.buffers == expected, 'joined post-cleavage buffers')
    require(journal.number(resolved['material_index']) == journal.number(resolved['cleave_material_index']) ==
            trial.nums['event_count'], 'joined completion material index')
    require(journal.vector(resolved['eviction_returns']) == tuple(trial.eviction_returns), 'joined eviction ledger')
    require(journal.number(resolved['eviction_total']) == trial.evictions, 'joined eviction count')
    require(not {state.active, state.passive} & set((*state.now, *state.next_ids)), 'dispatch participants still queued')
    victim = plan.incumbent if replaced else None
    now = tuple(i for i in state.now if i != victim)
    next_ids = tuple(i for i in state.next_ids if i != victim)
    if admitted:
        next_ids += (state.child,)
    next_ids += tuple(i for i in (state.active, state.passive) if i != removed)
    require(journal.ids(resolved['now_ids']) == now and journal.ids(resolved['next_ids']) == next_ids,
            'joined completed queue order')
    require(journal.number(resolved['population']) == len(expected), 'joined completed population')
    return trial

