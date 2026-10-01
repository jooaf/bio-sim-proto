"""SM-H001 qualifying source/suffix replay; no native role chooses a source.

Canonical material parsing and exact ledgers are inherited from SM-C002. This
second replay adds stable lifecycle/suffix validation and a separate, nullable
qualifying depth, and cross-checks every source edge against native observations.
"""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
from typing import Any

from experiments.stringmol import analyze_conservation as c, analyze_decay as d
from experiments.stringmol.analyze_lineage import EVENT_COLUMNS, SNAPSHOT_COLUMNS, integer, require

MATRIX = [('host', s) for s in range(202623000, 202623020)] + [('inert', s) for s in range(202623000, 202623010)]
ENDPOINTS = ('productive_source_births', 'renewing_descendants', 'serial_source_births',
             'max_source_depth', 'late_renewing_descendants', 'retained_late_renewals')
THRESHOLDS = (100, 10, 50, 2, 5, 5)


def visible(raw: bytes) -> bytes:
    return raw.split(b'\0', 1)[0]


def retention(birth: bytes, current: bytes) -> dict[str, Any]:
    require(len(birth) == len(current), 'retention buffer size')
    length = sum(b != 0 for b in birth)
    require(length > 0, 'empty productive birth buffer')
    retained = sum(b != 0 and b == now for b, now in zip(birth, current, strict=True))
    return {'birth_length': length, 'retained_bytes': retained, 'retention': retained / length}


def cleanup_orders(healed: dict[int, bytes], actual: dict[int, bytes]) -> list[int]:
    """Return possible active IDs under native active-first, single deletion.

    Material journals omit roles. Enumerate both role assignments rather than
    guessing them from sorted IDs or treating every empty-visible ID as dead.
    AgentCheckZeroLengthString returns immediately on the first empty buffer;
    when both are empty, passive (including its hidden tail) remains extant.
    """
    require(len(healed) == 2, 'cleanup requires two participants')
    possible = []
    for active in healed:
        passive = next(i for i in healed if i != active)
        expected = healed.copy()
        if not visible(healed[active]):
            del expected[active]
        elif not visible(healed[passive]):
            del expected[passive]
        if actual == expected:
            possible.append(active)
    return sorted(possible)


def suffix_cleanup_orders(before: dict[int, bytes], after: dict[int, bytes],
                          source: int, offset: int, child: int | None) -> list[int]:
    raw = before[source]
    end = len(visible(raw))
    healed = {**before, source: raw[:offset] + bytes(end - offset) + raw[end:]}
    return cleanup_orders(healed, {i: b for i, b in after.items() if i != child})


def infer_suffix(before: dict[int, bytes], after: dict[int, bytes], child: int | None) -> tuple[int, int]:
    """Explain *all* stable cleavage changes, including hidden-tail cleanup.

    A surviving source preserves every byte outside its visible suffix. A
    destroyed zero-visible parent releases its complete remaining hidden tail.
    Cleanup destroys at most one parent, active first; an empty passive may
    survive. Multiple compatible role orders do not create multiple sources.
    The child must be the ordered visible suffix at zero with a NUL-only tail.
    """
    candidates = []
    for source, raw in before.items():
        seq = visible(raw)
        for offset in range(len(seq)):
            suffix = seq[offset:]
            if child is not None and after[child] != suffix + bytes(len(raw) - len(suffix)):
                continue
            if suffix_cleanup_orders(before, after, source, offset, child):
                candidates.append((source, offset))
    require(len(candidates) == 1, 'nonunique/unexplained suffix transfer')
    return candidates[0]


class SourceReplay:
    def __init__(self, initial: dict[str, Any]):
        self.material = d.Replay(initial, 'recycle')
        self.initial_ids = set(self.material.buffers)
        self.depth: dict[int, int | None] = dict.fromkeys(self.initial_ids, 0)
        self.origin = dict.fromkeys(self.initial_ids, 'initial')
        self.born = dict.fromkeys(self.initial_ids, -1)
        self.birth_buffers: dict[int, bytes] = {}
        self.edges: list[dict[str, Any]] = []
        self.renewals: dict[int, dict[str, Any]] = {}
        self.participation: dict[int, Counter[str]] = {}
        self.deaths: dict[int, int] = {}
        self.failed = self.no_change = 0

    def step(self, row: dict[str, str]) -> None:
        m = self.material
        tick = integer(row['tick'])
        before = {i: m.buffers[i] for i in d.ids(row['before_ids']) if i in m.buffers}
        after_ids = d.ids(row['after_ids'])
        after = d.change(before, after_ids, row['changes'], m.size)
        new = set(after) - set(before)
        require(not new & m.seen, 'source ID reuse/cycle')
        if new:
            require(row['event'] == 'CLEAVE' and row['outcome'] == 'PLACED', 'unclassified origin')
            require(len(new) == 1 and min(new) > max(m.seen), 'source allocation ordering')
        source: int | None = None
        offset: int | None = None
        child: int | None = None
        if row['event'] == 'CLEAVE':
            if row['outcome'] == 'PLACED':
                require(len(new) == 1, 'source child count')
                child = next(iter(new))
                require(bool(visible(after[child])), 'empty placed child')
                source, offset = infer_suffix(before, after, child)
            elif row['outcome'] == 'FAILED':
                infer_suffix(before, after, None)
                self.failed += 1
            elif row['outcome'] == 'NO_CHANGE':
                self.no_change += 1
        # The inherited independent ledger must pass before crediting any edge.
        old_pool, old_waste = m.arrays['pool'].copy(), m.arrays['waste'].copy()
        population = len(m.buffers)
        m.step(row)
        require(len(m.buffers) <= 1600, 'source population bounds')
        for idx in set(before) - set(after):
            require(idx not in self.deaths, 'duplicate source death')
            self.deaths[idx] = tick
        if child is None:
            return
        if source is None or offset is None:
            raise ValueError('missing inferred source')
        require(source in self.depth and self.born[source] <= tick and child not in self.depth, 'source causal origin')
        productive = (len(m.buffers) == population + 1 and source in after and bool(visible(after[source])))
        if productive:
            require(offset > 0 and m.arrays['pool'] == old_pool and m.arrays['waste'] == old_waste,
                    'productive source double credit/discard')
            require(d.histogram(before) == d.histogram(after), 'productive event material mismatch')
        whole = offset == 0 and source not in after
        parent_depth = self.depth[source]
        qualifying = productive and parent_depth is not None
        self.depth[child] = parent_depth + 1 if qualifying and parent_depth is not None else None
        self.origin[child] = 'qualifying' if qualifying else 'orphan-source' if productive else 'whole-transfer' if whole else 'nonproductive'
        self.born[child] = tick
        self.birth_buffers[child] = after[child]
        self.edges.append({'tick': tick, 'index': integer(row['index']), 'source': source, 'child': child,
                           'offset': offset, 'productive': productive, 'whole_transfer': whole,
                           'orphan_source': productive and not qualifying, 'source_depth': parent_depth,
                           'child_depth': self.depth[child], 'origin': self.origin[child],
                           'cleanup_active_ids': suffix_cleanup_orders(before, after, source, offset, child),
                           'participants': sorted(before), 'birth_buffer_hex': after[child].hex().upper()})
        if qualifying and parent_depth is not None and parent_depth >= 1 and source not in self.renewals:
            stats = retention(self.birth_buffers[source], before[source])
            late = self.born[source] >= 2500
            self.renewals[source] = {'id': source, 'birth_tick': self.born[source], 'first_source_tick': tick,
                                     'first_source_index': integer(row['index']), 'source_depth': parent_depth,
                                     **stats, 'late': late,
                                     'retained_late': late and stats['birth_length'] >= 32 and 10 * stats['retained_bytes'] >= 9 * stats['birth_length']}

    def native_roles(self, births: list[dict[str, str]]) -> None:
        require(len(births) == len(self.edges), 'source/native birth count')
        self.participation = {i: Counter() for i in self.depth if i not in self.initial_ids}
        for edge, row in zip(self.edges, births, strict=True):
            active, passive = integer(row['active_id']), integer(row['passive_id'])
            require(integer(row['child_id']) == edge['child'] and integer(row['timestep']) == edge['tick'], 'source/native birth identity/time')
            require(active != passive and sorted((active, passive)) == edge['participants'], 'source/native parents')
            require(active in edge['cleanup_active_ids'], 'source/native cleanup order')
            edge['source_role'] = 'active' if edge['source'] == active else 'passive'
            for role, idx in (('active', active), ('passive', passive), ('source', edge['source'])):
                if idx in self.participation:
                    require(self.born[idx] <= edge['tick'], 'participation before birth')
                    self.participation[idx][role] += 1
                    if role == 'source' and edge['productive']:
                        self.participation[idx]['productive_source'] += 1

    def summary(self, end: int) -> dict[str, Any]:
        require(self.material.tick < end, 'source event at/after END')
        renewals = [{**r, 'survived_END': i in self.material.buffers, 'death_tick': self.deaths.get(i)} for i, r in sorted(self.renewals.items())]
        excluded = [{'id': i, 'origin': self.origin[i], 'birth_tick': self.born[i], 'source_depth': None,
                     'participation': dict(self.participation.get(i, {})), 'survived_END': i in self.material.buffers,
                     'death_tick': self.deaths.get(i)} for i in sorted(self.depth) if self.depth[i] is None]
        return {'native_births': len(self.edges), 'productive_source_births': sum(e['productive'] for e in self.edges),
                'whole_parent_transfers': sum(e['whole_transfer'] for e in self.edges),
                'other_nonproductive_births': sum(not e['productive'] and not e['whole_transfer'] for e in self.edges),
                'orphan_source_productive_births': sum(e['orphan_source'] for e in self.edges),
                'failed_placements': self.failed, 'no_change_cleavages': self.no_change,
                'renewing_descendants': len(renewals),
                'serial_source_births': sum(e['productive'] and e['source_depth'] is not None and e['source_depth'] >= 1 for e in self.edges),
                'max_source_depth': max((v for v in self.depth.values() if v is not None), default=0),
                'early_renewing_descendants': sum(not r['late'] for r in renewals),
                'late_renewing_descendants': sum(r['late'] for r in renewals),
                'retained_late_renewals': sum(r['retained_late'] for r in renewals),
                'birth_length_distribution': sorted(r['birth_length'] for r in renewals),
                'retention_distribution': sorted(r['retention'] for r in renewals),
                'renewals': renewals, 'source_edges': self.edges, 'excluded_descendants': excluded,
                'descendant_participation': {str(i): dict(v) for i, v in self.participation.items()},
                'source_role_counts': dict(Counter(e['source_role'] for e in self.edges if 'source_role' in e)),
                'end_surviving_descendants': sorted(set(self.material.buffers) - self.initial_ids),
                'end_surviving_qualifying_descendants': sorted(i for i in self.material.buffers if self.depth[i] is not None and i not in self.initial_ids),
                'identity_history': [{'id': i, 'origin': self.origin[i], 'source_depth': self.depth[i], 'birth_tick': self.born[i], 'death_tick': self.deaths.get(i)} for i in sorted(self.depth)]}


def analyze_run(directory: Path, expected: list[dict[str, Any]], route: str = 'recycle', *,
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


def outcomes(results: list[dict[str, Any]], failures: list[dict[str, Any]], *, mechanics: bool = True) -> dict[str, Any]:
    by_run = {(r['condition'], r['seed']): r for r in results}
    integrity = mechanics and not failures and len(results) == len(by_run) == 30 and set(by_run) == set(MATRIX)
    inert_ok = integrity and all(all(by_run[('inert', s)][k] == 0 for k in ('native_births', 'productive_source_births', 'renewing_descendants', 'max_source_depth')) for s in range(202623000, 202623010))
    hosts: list[dict[str, Any]] = []
    for seed in range(202623000, 202623020):
        row = by_run.get(('host', seed))
        components = {k: row is not None and row[k] >= threshold for k, threshold in zip(ENDPOINTS, THRESHOLDS, strict=True)}
        hosts.append({'seed': seed, 'components': components, 'renewal_core': all(list(components.values())[:5]), 'full_support': all(components.values())})
    core = inert_ok and sum(h['renewal_core'] for h in hosts) >= 16
    full = inert_ok and sum(h['full_support'] for h in hosts) >= 16
    decision = 'unevaluable' if not integrity else 'inert-control failure' if not inert_ok else 'pass' if full else 'renewal without retention' if core else 'valid failure'
    return {'decision': decision, 'integrity': integrity, 'mechanics': mechanics, 'inert_controls': inert_ok,
            'renewal_core': core, 'full_support': full, 'host_denominator': 20, 'inert_denominator': 10,
            'run_denominator': 30, 'hosts': hosts, 'runs': results, 'failures': failures,
            'descriptive_coin_tail_fraction': '6196/1048576', 'descriptive_coin_tail': 6196 / 1048576}


def analyze_campaign(manifest: Path) -> dict[str, Any]:
    from experiments.stringmol import renewal_workflow as w
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    try:
        data = w.verify_preparation(manifest)
        w.verify_launch(manifest)
        require(w.read(manifest.parent / 'campaign.json') == {'input_manifest': w.record(manifest), 'workers': 6, 'launch_record': w.record(manifest.parent / 'launch.json')}, 'campaign identity')
        receipts = w.read(manifest.parent / 'campaign-results.json')
        require(len(receipts) == 30, 'incomplete campaign')
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        return outcomes([], [{'error': str(exc)}], mechanics=False)
    for r, receipt in zip(data['runs'], receipts, strict=True):
        try:
            directory = Path(r['directory'])
            require(receipt == w.read(directory.with_suffix('.inventory.json')) and receipt['input_manifest'] == w.record(manifest), 'run receipt')
            require(receipt['condition'] == r['condition'] and receipt['seed'] == r['seed'] and receipt['files'] == w.inventory(directory), 'output identity/inventory')
            summary = analyze_run(directory, r['expected_initial'], exit_status=receipt['exit_status'])
            require(set(receipt['files']) == d.output_names(summary['end_timestep']), 'scientific output filename set')
            results.append({'condition': r['condition'], 'seed': r['seed'], **summary})
        except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
            failures.append({'condition': r['condition'], 'seed': r['seed'], 'error': str(exc)})
    return outcomes(results, failures)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    print(json.dumps(analyze_campaign(parser.parse_args().manifest.resolve()), indent=2, sort_keys=True))
