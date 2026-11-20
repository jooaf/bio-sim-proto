"""Read-only descriptive reduction of already verified XL records; no VM/native code."""
from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Iterator, cast

Obj = dict[str, object]
Metric = int | float | None
RAW = Path('/run/media/jojo/Elements/bio-sim-results/sm-xl001-recovery-v1')
PORTABLE = Path('/run/media/jojo/Elements/bio-sim-results/verification/sm-xl001-recovery-v1')
CONTROLS = Path('/tmp/sm/xl2-c')
CELLS = ('GG', 'LG', 'GL', 'LL')
DECISION = 'f8349c017deb2f4d25d48a5cd8b05db89d6ae09ccdaa5de2540fd5dc23875eb5'
HOST = b'WWGEWLHHHRLUEUWJJJRJXUUUDYGRHJLRWWRE$BLUBO^B>C$=?>$$BLUBO%}OYHOB'


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def obj(value: object) -> Obj:
    require(isinstance(value, dict) and all(isinstance(k, str) for k in value), 'object required')
    return cast(Obj, value)


def array(value: object) -> list[object]:
    require(isinstance(value, list), 'array required')
    return cast(list[object], value)


def num(value: object) -> int:
    require(type(value) is int and value >= 0, 'nonnegative integer required')
    return cast(int, value)


def text(value: object) -> str:
    require(isinstance(value, str), 'string required')
    return cast(str, value)


def boolean(value: object) -> bool:
    require(type(value) is bool, 'boolean required')
    return cast(bool, value)


def load(path: Path) -> Obj:
    return obj(json.loads(path.read_text()))


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def ratio(n: int, d: int) -> float | None:
    require(0 <= n <= d, 'fraction bounds')
    return n / d if d else None


def visible(value: str) -> bytes:
    return bytes.fromhex(value).split(b'\0', 1)[0]


def rows(path: Path, columns: str) -> Iterator[dict[str, str]]:
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == columns.split(','), 'CSV schema: ' + str(path))
        for row in reader:
            require(None not in row and all(v is not None for v in row.values()), 'malformed CSV')
            yield row


def integer(value: str) -> int:
    require(value.isascii() and value.isdecimal(), 'invalid CSV integer')
    return int(value)


@dataclass(frozen=True)
class Birth:
    tick: int
    sequence: bytes
    participants: frozenset[int]


@dataclass
class Renewal:
    metrics: dict[str, Metric]
    births: dict[int, int]
    first: dict[int, int]
    edges: list[Obj]
    records: dict[int, Obj]


def renewal(summary: Obj, births: dict[int, Birth]) -> Renewal:
    edges = [obj(e) for e in array(summary['transfer_edges'])]
    depth: dict[int, int | None] = dict.fromkeys(range(140), 0)
    born: dict[int, int] = dict.fromkeys(range(140), 0)
    first: dict[int, int] = {}
    first_index: dict[int, int] = {}
    serial = qualifying = orphan = late_events = 0
    late_sources: set[int] = set()
    last_tick = last_index = 0
    for e in edges:
        source, child, tick, index = (num(e[k]) for k in ('source', 'child', 'tick', 'index'))
        require(source in depth and child not in depth and child >= 140, 'source/child identity')
        require(last_tick <= tick <= 4999 and index > last_index and born[source] <= tick, 'edge timing')
        last_tick, last_index = tick, index
        require(child in births, 'missing raw birth')
        birth = births[child]
        require(birth.tick == tick and visible(text(e['birth_buffer_hex'])) == birth.sequence, 'birth sequence/tick')
        participants = frozenset(num(p) for p in array(e['participants']))
        require(len(participants) == 2 and source in participants and participants == birth.participants
                and all(p in born and born[p] <= tick for p in participants), 'birth participants')
        whole, eligible = boolean(e['whole_transfer']), boolean(e['transfer_eligible'])
        require(not eligible or (not whole and num(e['offset']) > 0), 'whole/partial eligibility')
        parent = depth[source]
        rooted = eligible and parent is not None
        require(boolean(e['rooted_transfer']) == rooted and boolean(e['transfer_orphan']) == (eligible and not rooted), 'root flags')
        source_depth = e['source_nonrelocation_depth']
        require((None if source_depth is None else num(source_depth)) == parent, 'source ancestry')
        depth[child] = parent + 1 if rooted and parent is not None else None
        child_depth = e['nonrelocation_depth']
        require((None if child_depth is None else num(child_depth)) == depth[child], 'child ancestry')
        born[child] = tick
        qualifying += int(rooted)
        orphan += int(eligible and not rooted)
        if rooted and parent:
            require(source >= 140, 'founder renewal')
            serial += 1
            if source not in first:
                first[source], first_index[source] = tick, index
            if tick >= 2500:
                late_events += 1
                late_sources.add(source)
    require(set(births) == set(born) - set(range(140)), 'edge/raw admitted child inventory')
    records: dict[int, Obj] = {}
    birth_edges = {num(e['child']): e for e in edges}
    for value in array(summary['transfer_renewals']):
        r = obj(value)
        idx = num(r['id'])
        require(idx in first and idx not in records, 'renewal identity/duplicate')
        require(num(r['birth_tick']) == born[idx] and num(r['first_source_tick']) == first[idx], 'renewal timing')
        length, retained = num(r['birth_length']), num(r['retained_bytes'])
        require(length == sum(b != 0 for b in bytes.fromhex(text(birth_edges[idx]['birth_buffer_hex']))) and length > 0, 'birth buffer length')
        require(retained <= length and r['retention'] == retained / length, 'retention arithmetic')
        late = born[idx] >= 2500
        require(boolean(r['late']) == late and boolean(r['retained_late']) == (late and length >= 32 and 10 * retained >= 9 * length), 'late/retained definition')
        records[idx] = r
    require(set(records) == set(first), 'renewal set')
    metrics: dict[str, Metric] = {
        'qualifying_transfers': qualifying, 'transfer_renewing_descendants': len(first),
        'serial_transfers': serial, 'orphan_transfers': orphan,
        'max_nonrelocation_depth': max((d for d in depth.values() if d is not None), default=0),
        'late_transfer_renewing_descendants': sum(born[i] >= 2500 for i in first),
        'retained_late_transfer_renewals': sum(boolean(r['retained_late']) for r in records.values()),
    }
    for key, value in metrics.items():
        require(summary[key] == value, 'stored aggregate: ' + key)
    children = set(births)
    late_children = {i for i in children if born[i] >= 2500}
    rooted_children = {i for i in children if depth[i] is not None}
    late_rooted = late_children & rooted_children
    metrics.update(admitted_children=len(children), late_born_children=len(late_children),
                   rooted_children=len(rooted_children), late_born_rooted_children=len(late_rooted),
                   observed_renewal_fraction=ratio(len(first), len(children)),
                   late_born_observed_renewal_fraction=ratio(len(set(first) & late_children), len(late_children)),
                   rooted_observed_renewal_fraction=ratio(len(first), len(rooted_children)),
                   late_born_rooted_observed_renewal_fraction=ratio(len(set(first) & late_children), len(late_rooted)),
                   late_acting_serial_events=late_events, late_acting_unique_sources=len(late_sources))
    return Renewal(metrics, {i: born[i] for i in children}, first, edges, records)


SOURCE_COLUMNS = 'tick,material_index,active,passive,flow_source,flow_offset,source,offset,child,eligible_tick,decision,remnant_hex,source_x,source_y,child_x,child_y,survivor,now_before,next_before,now_after,next_after,proposals,eligible,committed'


def source_check(path: Path, r: Renewal) -> None:
    """Cross-check retained-source eligibility against existing native source records."""
    edges = {num(e['child']): e for e in r.edges}
    seen: set[int] = set()
    for row in rows(path, SOURCE_COLUMNS):
        if row['child'] == '-1':
            continue
        child = integer(row['child'])
        require(child in edges and child not in seen, 'source journal child')
        e = edges[child]
        require(integer(row['tick']) == num(e['tick']) and integer(row['material_index']) == num(e['index'])
                and integer(row['source']) == num(e['source']) and integer(row['offset']) == num(e['offset']), 'source journal link')
        require(frozenset((integer(row['active']), integer(row['passive']))) ==
                frozenset(num(v) for v in array(e['participants'])), 'source journal participants')
        eligible = num(e['offset']) > 0 and any(bytes.fromhex(row['remnant_hex'])) and not boolean(e['whole_transfer'])
        require(boolean(e['transfer_eligible']) == eligible and row['decision'] == 'RETAIN', 'retained-source eligibility')
        seen.add(child)
    require(seen == set(edges), 'missing source journal edge')


def retention_check(path: Path, r: Renewal) -> None:
    """Patch only renewing-source birth buffers up to first reuse; not a VM replay."""
    birth_edges = {num(e['child']): e for e in r.edges}
    target = {num(e['index']): num(e['source']) for e in r.edges
              if num(e['source']) in r.first and num(e['tick']) == r.first[num(e['source'])]}
    # Several same-tick actions: retain only the earliest material index per source.
    target = {min(k for k, v in target.items() if v == i): i for i in r.first}
    tracked = {i: bytearray.fromhex(text(birth_edges[i]['birth_buffer_hex'])) for i in r.first}
    seen: set[int] = set()
    for row in rows(path, 'tick,index,event,outcome,before_ids,after_ids,changes,proposal'):
        index = integer(row['index'])
        if index in target:
            idx = target[index]
            birth = bytes.fromhex(text(birth_edges[idx]['birth_buffer_hex']))
            retained = sum(b != 0 and b == now for b, now in zip(birth, tracked[idx], strict=True))
            require(retained == num(r.records[idx]['retained_bytes']), 'source retention bytes')
            seen.add(idx)
        for change in row['changes'].split(';') if row['changes'] else []:
            fields = change.split(':')
            require(len(fields) == 4, 'material change schema')
            idx, offset = integer(fields[0]), integer(fields[1])
            if idx in tracked and idx not in seen and index > num(birth_edges[idx]['index']):
                before, after = int(fields[2], 16), int(fields[3], 16)
                require(offset < len(tracked[idx]) and tracked[idx][offset] == before, 'source byte trace')
                tracked[idx][offset] = after
    require(seen == set(r.first), 'missing first-source material record')


EVENTS = 'event,timestep,population,child_id,active_id,passive_id,child_species,active_species,passive_species,child_label,active_label,passive_label,x,y,child_sequence_hex,active_sequence_hex,passive_sequence_hex'
SNAPS = 'tick,id,species,label,x,y,sequence_hex'


def lineage(path: Path) -> tuple[bytes, dict[int, Birth]]:
    founders: dict[int, bytes] = {}
    births: dict[int, Birth] = {}
    ended = False
    for row in rows(path, EVENTS):
        require(not ended, 'lineage after/duplicate END')
        tick = integer(row['timestep'])
        require(row['event'] in ('INIT', 'BIRTH', 'END') and tick <= 5000, 'lineage event/horizon')
        if row['event'] == 'END':
            require(tick == 5000 and row['child_id'] == '-1', 'lineage END')
            ended = True
            continue
        idx = integer(row['child_id'])
        sequence = bytes.fromhex(row['child_sequence_hex'])
        require(b'\0' not in sequence, 'visible lineage NUL')
        if row['event'] == 'INIT':
            require(tick == 0 and idx < 140 and idx not in founders, 'founder identity')
            founders[idx] = sequence
        elif row['event'] == 'BIRTH':
            require(idx >= 140 and idx not in births, 'birth identity')
            births[idx] = Birth(tick, sequence, frozenset((integer(row['active_id']), integer(row['passive_id']))))
    require(ended and set(founders) == set(range(140)) and len(set(founders.values())) == 1, 'canonical founders/END')
    require(founders[0] == HOST, 'noncanonical HOST')
    return founders[0], births


def checkpoint_metrics(base: Path, checkpoints: list[Obj], host: bytes, r: Renewal) -> list[dict[str, Metric | str]]:
    expected = [('CHECKPOINT', t) for t in range(0, 5000, 100)] + [('END', 5000)]
    require([(text(c['event']), num(c['tick'])) for c in checkpoints] == expected, 'missing/duplicate checkpoint schedule')
    snapshots: dict[int, dict[int, tuple[int, int, bytes]]] = {}
    for row in rows(base / 'lineage_snapshots001.csv', SNAPS):
        tick, idx, x, y = (integer(row[k]) for k in ('tick', 'id', 'x', 'y'))
        require(tick in range(0, 5000, 100) and x < 40 and y < 40, 'snapshot tick/coordinate')
        require(idx < 140 or (idx in r.births and r.births[idx] < tick), 'snapshot identity/timing')
        group = snapshots.setdefault(tick, {})
        require(idx not in group, 'duplicate snapshot identity (including conflicting duplicates)')
        group[idx] = (x, y, bytes.fromhex(row['sequence_hex']))
    buffers: dict[tuple[str, int], dict[int, bytes]] = {}
    for row in rows(base / 'conservation_buffers002.csv', 'tick,event,id,full_buffer_hex'):
        key = (row['event'], integer(row['tick']))
        require(key in expected, 'buffer checkpoint key')
        group_b = buffers.setdefault(key, {})
        idx = integer(row['id'])
        require(idx not in group_b, 'duplicate buffer identity')
        require(idx < 140 or (idx in r.births and r.births[idx] < key[1]), 'buffer identity/timing')
        group_b[idx] = visible(row['full_buffer_hex'])
    output: list[dict[str, Metric | str]] = []
    for c in checkpoints:
        tick, event, population = num(c['tick']), text(c['event']), num(c['population'])
        group_b = buffers.get((event, tick), {})
        require(len(group_b) == population, 'buffer population/missing snapshot')
        if event == 'CHECKPOINT':
            group_s = snapshots.get(tick, {})
            require(len(group_s) == population and {i: v[2] for i, v in group_s.items()} == group_b, 'snapshot/buffer mismatch or missing snapshot')
            occupied = {(v[0], v[1]) for v in group_s.values()}
            require(len(occupied) == population, 'duplicate occupied coordinate')
            adjacent = sum(((x + dx) % 40, (y + dy) % 40) in occupied
                           for x, y in occupied for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)
            require(adjacent == num(c['occupied_neighbor_slots']), 'snapshot spatial numerator')
        require(num(c['neighbor_slots']) == 8 * population, 'spatial denominator')
        exact = sum(s == host for s in group_b.values())
        output.append(dict(event=event, tick=tick, population=population, exact_host=exact,
                           exact_host_fraction=ratio(exact, population),
                           occupied_neighbor_slots=num(c['occupied_neighbor_slots']), neighbor_slots=8 * population,
                           occupied_neighbor_fraction=ratio(num(c['occupied_neighbor_slots']), 8 * population),
                           cumulative_births=sum(t < tick for t in r.births.values()),
                           cumulative_renewers=sum(t < tick for t in r.first.values())))
    return output


def verify(path: Path, expected: str) -> None:
    require(digest(path) == expected, 'bad hash: ' + str(path))


def fresh(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=False)


def save(path: Path, value: object) -> None:
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def csv_save(path: Path, data: list[dict[str, object]]) -> None:
    require(bool(data), 'empty output table')
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def analyze(out: Path) -> None:
    fresh(out)
    marker = PORTABLE / 'VERIFIED.json'
    verify(marker, '3d68b3f25d90ea05731f99af1e48fd061c9b998ddf97e6710110997994df045d')
    marker_data = load(marker)
    require(marker_data['verified'] is True, 'export not verified')
    inventory_path = PORTABLE / 'checksums.json'
    inventory_hash = text(obj(marker_data['checksums'])['sha256'])
    verify(inventory_path, inventory_hash)
    inventory = load(inventory_path)
    inputs: dict[str, str] = {str(inventory_path): inventory_hash, str(marker): digest(marker)}
    audit_path = Path('/tmp/sm/xl2-closeout/audit.json')
    audit_hash = '361eda6d8f8f59478ed4bcca3fe8e143ea9ca529a8feea873cbc3c3bd6f5cd83'
    verify(audit_path, audit_hash)
    audit_copy = PORTABLE.parent / 'sm-xl001-recovery-closeout-v1/files/audit.json'
    verify(audit_copy, audit_hash)
    require(load(audit_path)['passed'] is True, 'parent audit not passed')
    inputs[str(audit_path)] = audit_hash
    inputs[str(audit_copy)] = audit_hash
    for source_path in (Path(__file__), Path('tests/test_xl_renewal_synthesis.py'), Path('reports/sm_xl001_renewal_analysis_spec.md')):
        inputs[str(source_path.resolve())] = digest(source_path)

    def bound(path: Path, key: str) -> None:
        expected = text(obj(inventory[key])['sha256'])
        verify(path, expected)
        portable = PORTABLE / key
        verify(portable, expected)
        inputs[str(path)] = expected
        inputs[str(portable)] = expected

    bound(CONTROLS / 'decision.json', 'controls/decision.json')
    require(inputs[str(CONTROLS / 'decision.json')] == DECISION, 'decision frozen hash')
    decision = load(CONTROLS / 'decision.json')
    require(decision['integrity'] is True, 'decision integrity')
    results: dict[str, dict[str, Metric]] = {}
    checkpoint_rows: list[dict[str, object]] = []
    for cell in CELLS:
        reference: Obj | None = None
        for kind in ('observed', 'repeat'):
            for number in (1, 2):
                relative = f'{cell}-{kind}-replay{number}/result.json'
                path = CONTROLS / relative
                bound(path, 'controls/' + relative)
                data = load(path)
                if reference is None:
                    reference = data
                require(reference == data, 'technical identity')
        require(reference is not None, 'missing observed result')
        data = cast(Obj, reference)
        require(data == obj(decision['results'])[cell], 'decision/replay mismatch')
        base = RAW / (cell + '-observed')
        for name in ('lineage_events001.csv', 'lineage_snapshots001.csv', 'conservation_buffers002.csv', 'material_events002.csv', 'source_events006.csv'):
            bound(base / name, f'raw/{cell}-observed/{name}')
        host, births = lineage(base / 'lineage_events001.csv')
        r = renewal(obj(data['renewal']), births)
        source_check(base / 'source_events006.csv', r)
        retention_check(base / 'material_events002.csv', r)
        checkpoints = checkpoint_metrics(base, [obj(v) for v in array(data['checkpoints'])], host, r)
        m = r.metrics
        proposals, placed, failed = (num(data[k]) for k in ('proposals', 'placed', 'failed_placement'))
        require(proposals == placed + failed and placed == len(births), 'admission counts')
        m.update(admission_attempts=proposals, admission_successes=placed, admission_failures=failed,
                 admission_success_rate=ratio(placed, proposals), admission_failure_rate=ratio(failed, proposals),
                 exact_host_births=sum(b.sequence == host for b in births.values()),
                 exact_host_birth_fraction=ratio(sum(b.sequence == host for b in births.values()), placed))
        for label, cp in (('initial', checkpoints[0]), ('final', checkpoints[-1])):
            for key in ('population', 'exact_host', 'exact_host_fraction', 'occupied_neighbor_slots', 'neighbor_slots', 'occupied_neighbor_fraction'):
                m[label + '_' + key] = cast(Metric, cp[key])
        late = [cp for cp in checkpoints if 4000 <= cast(int, cp['tick']) <= 4900]
        for key in ('population', 'exact_host', 'exact_host_fraction', 'occupied_neighbor_fraction'):
            values = [cast(int | float, cp[key]) for cp in late if cp[key] is not None]
            m['late4000_4900_' + key + '_min'] = min(values) if values else None
            m['late4000_4900_' + key + '_max'] = max(values) if values else None
            m['late4000_4900_' + key + '_mean'] = sum(values) / len(values) if values else None
            m['late4000_4900_' + key + '_non_null_checkpoints'] = len(values)
        results[cell] = m
        checkpoint_rows.extend(dict(cell=cell, **cp) for cp in checkpoints)
    contrasts: dict[str, dict[str, Metric]] = {}
    for a, b in (('GL', 'GG'), ('LL', 'LG')):
        contrasts[a + '-' + b] = {k: None if results[a][k] is None or results[b][k] is None else cast(int | float, results[a][k]) - cast(int | float, results[b][k]) for k in results[a]}
    checkpoint_contrasts: list[dict[str, object]] = []
    for a, b in (('GL', 'GG'), ('LL', 'LG')):
        left = [c for c in checkpoint_rows if c['cell'] == a]
        right = [c for c in checkpoint_rows if c['cell'] == b]
        for l, rr in zip(left, right, strict=True):
            row: dict[str, object] = dict(contrast=a + '-' + b, event=l['event'], tick=l['tick'])
            for key in l.keys() - {'cell', 'event', 'tick'}:
                row[key] = None if l[key] is None or rr[key] is None else cast(int | float, l[key]) - cast(int | float, rr[key])
            checkpoint_contrasts.append(row)
    # Explicit deterministic column order (set iteration above is not scientific state).
    checkpoint_contrasts = [dict(sorted(row.items())) for row in checkpoint_contrasts]
    for input_path, expected in inputs.items():
        verify(Path(input_path), expected)
    save(out / 'inputs.json', inputs)
    save(out / 'metrics.json', dict(cells=results, primary_contrasts=contrasts))
    csv_save(out / 'cells.csv', [dict(cell=k, **v) for k, v in results.items()])
    csv_save(out / 'contrasts.csv', [dict(contrast=k, **v) for k, v in contrasts.items()])
    csv_save(out / 'checkpoints.csv', checkpoint_rows)
    csv_save(out / 'checkpoint_contrasts.csv', checkpoint_contrasts)
    save(out / 'checksums.json', {p.name: digest(p) for p in sorted(out.iterdir())})


if __name__ == '__main__':
    require(len(sys.argv) == 2, 'usage: python -m experiments.stringmol.xl_renewal_synthesis NEW_OUTPUT_DIR')
    analyze(Path(sys.argv[1]))
