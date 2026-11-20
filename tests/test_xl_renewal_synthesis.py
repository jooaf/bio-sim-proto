"""Synthetic existing-record qualification; no native fixtures or simulations."""
from __future__ import annotations

import copy
import csv
from pathlib import Path
import tempfile
import unittest

from experiments.stringmol import xl_renewal_synthesis as x


def edge(source: int, child: int, tick: int, index: int, parent: int | None,
         depth: int | None, eligible: bool = True, whole: bool = False) -> x.Obj:
    return dict(source=source, child=child, tick=tick, index=index,
                participants=[source, 0 if source != 0 else 1], birth_buffer_hex='41420000',
                offset=2 if eligible else 0, whole_transfer=whole,
                transfer_eligible=eligible, rooted_transfer=eligible and parent is not None,
                transfer_orphan=eligible and parent is None,
                source_nonrelocation_depth=parent, nonrelocation_depth=depth)


def fixture() -> tuple[x.Obj, dict[int, x.Birth]]:
    edges = [edge(0, 140, 100, 1, 0, 1), edge(140, 141, 2600, 2, 1, 2),
             edge(140, 142, 2700, 3, 1, 2), edge(141, 143, 4999, 4, 2, 3)]
    records: list[x.Obj] = [dict(id=i, birth_tick=b, first_source_tick=f,
                               birth_length=2, retained_bytes=2, retention=1.0,
                               late=b >= 2500, retained_late=False)
                          for i, b, f in ((140, 100, 2600), (141, 2600, 4999))]
    summary: x.Obj = dict(transfer_edges=edges, transfer_renewals=records,
                         qualifying_transfers=4, transfer_renewing_descendants=2,
                         serial_transfers=3, orphan_transfers=0, max_nonrelocation_depth=3,
                         late_transfer_renewing_descendants=1, retained_late_transfer_renewals=0)
    births = {x.num(e['child']): x.Birth(x.num(e['tick']), b'AB',
              frozenset(x.num(p) for p in x.array(e['participants']))) for e in edges}
    return summary, births


def empty_summary() -> x.Obj:
    return dict(transfer_edges=[], transfer_renewals=[], qualifying_transfers=0,
                transfer_renewing_descendants=0, serial_transfers=0, orphan_transfers=0,
                max_nonrelocation_depth=0, late_transfer_renewing_descendants=0,
                retained_late_transfer_renewals=0)


def write_csv(path: Path, header: str, data: list[dict[str, str]]) -> None:
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=header.split(','))
        writer.writeheader()
        writer.writerows(data)


class Qualification(unittest.TestCase):
    def test_founders_only_zero_birth(self) -> None:
        r = x.renewal(empty_summary(), {})
        self.assertEqual(r.metrics['serial_transfers'], 0)
        self.assertIsNone(r.metrics['observed_renewal_fraction'])

    def test_repeated_source_late_born_vs_late_acting_and_censoring(self) -> None:
        r = x.renewal(*fixture())
        self.assertEqual(r.metrics['transfer_renewing_descendants'], 2)
        self.assertEqual(r.metrics['serial_transfers'], 3)
        self.assertEqual(r.metrics['late_acting_unique_sources'], 2)
        self.assertEqual(r.metrics['late_acting_serial_events'], 3)
        self.assertEqual(r.metrics['late_transfer_renewing_descendants'], 1)
        self.assertEqual(r.metrics['late_born_children'], 3)
        self.assertEqual(r.metrics['late_born_observed_renewal_fraction'], 1 / 3)
        self.assertNotIn(143, r.first)  # birth at4999 has essentially no follow-up

    def test_whole_and_orphan_not_renewal(self) -> None:
        s = empty_summary()
        e = [edge(0, 140, 10, 1, 0, None, False, True),
             edge(140, 141, 20, 2, None, None)]
        s.update(transfer_edges=e, orphan_transfers=1)
        births = {x.num(v['child']): x.Birth(x.num(v['tick']), b'AB',
                  frozenset(x.num(p) for p in x.array(v['participants']))) for v in e}
        r = x.renewal(s, births)
        self.assertEqual(r.metrics['qualifying_transfers'], 0)
        self.assertEqual(r.metrics['rooted_children'], 0)
        self.assertEqual(r.metrics['transfer_renewing_descendants'], 0)

    def test_whole_cannot_qualify(self) -> None:
        s, b = fixture()
        x.obj(x.array(s['transfer_edges'])[0])['whole_transfer'] = True
        with self.assertRaises(ValueError):
            x.renewal(s, b)

    def test_bad_and_missing_source_ids(self) -> None:
        for value in (999, -1, True, '0', None):
            s, b = fixture()
            x.obj(x.array(s['transfer_edges'])[0])['source'] = value
            with self.assertRaises(ValueError):
                x.renewal(s, b)
        s, b = fixture()
        del x.obj(x.array(s['transfer_edges'])[0])['source']
        with self.assertRaises(KeyError):
            x.renewal(s, b)

    def test_bad_ticks_and_ancestry(self) -> None:
        for key, value in (('tick', 5000), ('tick', -1), ('tick', '100'),
                           ('source_nonrelocation_depth', 1), ('nonrelocation_depth', 2)):
            s, b = fixture()
            x.obj(x.array(s['transfer_edges'])[0])[key] = value
            with self.assertRaises(ValueError):
                x.renewal(s, b)

    def test_duplicate_child_and_missing_birth(self) -> None:
        s, b = fixture()
        del b[142]
        with self.assertRaises(ValueError):
            x.renewal(s, b)
        s, b = fixture()
        x.obj(x.array(s['transfer_edges'])[1])['child'] = 140
        with self.assertRaises(ValueError):
            x.renewal(s, b)

    def test_bad_renewal_and_aggregates(self) -> None:
        for key, value in (('id', 0), ('birth_tick', 2500), ('first_source_tick', 4999),
                           ('late', True), ('retention', .5), ('retained_late', True)):
            s, b = fixture()
            x.obj(x.array(s['transfer_renewals'])[0])[key] = value
            with self.assertRaises(ValueError):
                x.renewal(s, b)
        s, b = fixture()
        s['serial_transfers'] = 99
        with self.assertRaises(ValueError):
            x.renewal(s, b)

    def test_fragment_not_host_and_padding(self) -> None:
        self.assertEqual(x.visible('4142000000'), b'AB')
        self.assertNotEqual(x.visible('410000'), b'AB')
        self.assertNotEqual(x.visible('4142580000'), b'AB')
        self.assertEqual(x.visible('41420058'), b'AB')  # hidden byte != visible HOST
        with self.assertRaises(ValueError):
            x.visible('ZZ')

    def test_retained_late_threshold_inherited(self) -> None:
        s, b = fixture()
        es = [copy.deepcopy(x.obj(e)) for e in x.array(s['transfer_edges'])]
        es[1]['birth_buffer_hex'] = '41' * 32 + '0000'
        b[141] = x.Birth(2600, b'A' * 32, b[141].participants)
        rs = [copy.deepcopy(x.obj(v)) for v in x.array(s['transfer_renewals'])]
        rs[1].update(birth_length=32, retained_bytes=29, retention=29 / 32, retained_late=True)
        s.update(transfer_edges=es, transfer_renewals=rs, retained_late_transfer_renewals=1)
        self.assertEqual(x.renewal(s, b).metrics['retained_late_transfer_renewals'], 1)
        rs[1].update(retained_bytes=28, retention=28 / 32, retained_late=False)
        s['retained_late_transfer_renewals'] = 0
        self.assertEqual(x.renewal(s, b).metrics['retained_late_transfer_renewals'], 0)

    def test_retention_source_trace_and_tamper(self) -> None:
        r = x.renewal(*fixture())
        data = [dict(tick=str(t), index=str(i), event='CLEAVE', outcome='PLACED',
                     before_ids='', after_ids='', changes='', proposal='')
                for t, i in ((100, 1), (2600, 2), (2700, 3), (4999, 4))]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'material.csv'
            header = 'tick,index,event,outcome,before_ids,after_ids,changes,proposal'
            write_csv(p, header, data)
            x.retention_check(p, r)
            data[0]['changes'] = '140:0:FF:41'  # ignored at birth (already birth buffer)
            data[1]['changes'] = '141:0:41:42'  # same birth also ignored
            write_csv(p, header, data)
            x.retention_check(p, r)
            data[2]['changes'] = '141:0:41:42'
            write_csv(p, header, data)
            with self.assertRaises(ValueError):
                x.retention_check(p, r)

    def checkpoints(self, population: int = 0) -> list[x.Obj]:
        return [dict(event=e, tick=t, population=population, neighbor_slots=8 * population,
                     occupied_neighbor_slots=0)
                for e, t in [('CHECKPOINT', t) for t in range(0, 5000, 100)] + [('END', 5000)]]

    def test_zero_population_explicit_checkpoints_and_missing_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            write_csv(p / 'lineage_snapshots001.csv', x.SNAPS, [])
            write_csv(p / 'conservation_buffers002.csv', 'tick,event,id,full_buffer_hex', [])
            r = x.renewal(empty_summary(), {})
            cps = self.checkpoints()
            result = x.checkpoint_metrics(p, cps, b'AB', r)
            self.assertEqual(len(result), 51)
            self.assertIsNone(result[0]['exact_host_fraction'])
            with self.assertRaises(ValueError):
                x.checkpoint_metrics(p, cps[:-1], b'AB', r)
            with self.assertRaises(ValueError):
                x.checkpoint_metrics(p, cps + [cps[-1]], b'AB', r)
            with self.assertRaises(ValueError):
                x.checkpoint_metrics(p, self.checkpoints(1), b'AB', r)

    def test_snapshot_and_end_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            snaps = [dict(tick=str(t), id='0', species='1', label='81', x='0', y='0', sequence_hex='4142')
                     for t in range(0, 5000, 100)]
            buffers = [dict(tick=str(t), event=e, id='0', full_buffer_hex='41420000')
                       for e, t in [('CHECKPOINT', t) for t in range(0, 5000, 100)] + [('END', 5000)]]
            write_csv(p / 'lineage_snapshots001.csv', x.SNAPS, snaps)
            write_csv(p / 'conservation_buffers002.csv', 'tick,event,id,full_buffer_hex', buffers)
            r = x.renewal(empty_summary(), {})
            self.assertEqual(x.checkpoint_metrics(p, self.checkpoints(1), b'AB', r)[-1]['exact_host'], 1)
            aligned = x.checkpoint_metrics(p, self.checkpoints(1), b'AB', x.renewal(*fixture()))
            self.assertEqual(aligned[1]['cumulative_births'], 0)  # checkpoint100 precedes birth100
            self.assertEqual(aligned[2]['cumulative_births'], 1)
            self.assertEqual(aligned[26]['cumulative_renewers'], 0)
            self.assertEqual(aligned[27]['cumulative_renewers'], 1)
            for bad in ('missing', 'duplicate', 'conflicting', 'bad_id', 'bad_tick', 'END'):
                altered = copy.deepcopy(snaps)
                if bad == 'missing':
                    altered.pop()
                elif bad in ('duplicate', 'conflicting'):
                    altered.append(dict(altered[0]))
                    if bad == 'conflicting':
                        altered[-1]['sequence_hex'] = '41'
                else:
                    altered[0][{'bad_id': 'id', 'bad_tick': 'tick', 'END': 'tick'}[bad]] = {'bad_id': '999', 'bad_tick': '-1', 'END': '5000'}[bad]
                write_csv(p / 'lineage_snapshots001.csv', x.SNAPS, altered)
                with self.assertRaises(ValueError, msg=bad):
                    x.checkpoint_metrics(p, self.checkpoints(1), b'AB', r)

    def test_lineage_founders_fragments_and_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'lineage.csv'
            data = [dict.fromkeys(x.EVENTS.split(','), '-1') for _ in range(142)]
            for i in range(140):
                data[i].update(event='INIT', timestep='0', child_id=str(i), child_sequence_hex=x.HOST.hex())
            data[140].update(event='BIRTH', timestep='4999', child_id='140', active_id='0', passive_id='1', child_sequence_hex='41')
            data[141].update(event='END', timestep='5000')
            write_csv(p, x.EVENTS, data)
            host, births = x.lineage(p)
            self.assertEqual(host, x.HOST)
            self.assertNotEqual(births[140].sequence, host)
            for altered in (data[:-1], data + [data[-1]], data[1:]):
                write_csv(p, x.EVENTS, altered)
                with self.assertRaises(ValueError):
                    x.lineage(p)

    def test_source_eligibility_link(self) -> None:
        s, births = fixture()
        r = x.renewal(s, births)
        data: list[dict[str, str]] = []
        for e in r.edges:
            row = dict.fromkeys(x.SOURCE_COLUMNS.split(','), '-1')
            row.update(tick=str(e['tick']), material_index=str(e['index']), source=str(e['source']),
                       offset=str(e['offset']), child=str(e['child']), decision='RETAIN', remnant_hex='41',
                       active=str(x.array(e['participants'])[0]), passive=str(x.array(e['participants'])[1]))
            data.append(row)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'source.csv'
            write_csv(p, x.SOURCE_COLUMNS, data)
            x.source_check(p, r)
            for key, value in (('remnant_hex', '0000'), ('material_index', '999'), ('source', '999')):
                altered = copy.deepcopy(data)
                altered[0][key] = value
                write_csv(p, x.SOURCE_COLUMNS, altered)
                with self.assertRaises(ValueError):
                    x.source_check(p, r)
            write_csv(p, x.SOURCE_COLUMNS, data[:-1])
            with self.assertRaises(ValueError):
                x.source_check(p, r)

    def test_hash_and_reused_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'input'
            p.write_text('test')
            x.verify(p, x.digest(p))
            with self.assertRaises(ValueError):
                x.verify(p, '0' * 64)
            new = Path(tmp) / 'out'
            x.fresh(new)
            with self.assertRaises(FileExistsError):
                x.fresh(new)

    def test_null_zero_and_malformed(self) -> None:
        self.assertIsNone(x.ratio(0, 0))
        self.assertEqual(x.ratio(0, 1), 0)
        for value in ('-1', '', '1.0', '١'):
            with self.assertRaises(ValueError):
                x.integer(value)
        with self.assertRaises(ValueError):
            x.ratio(1, 0)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bad.csv'
            p.write_text('id,tick\n0\n')
            with self.assertRaises(ValueError):
                list(x.rows(p, 'id,tick'))
            with self.assertRaises(ValueError):
                list(x.rows(p, 'tick,id'))


if __name__ == '__main__':
    unittest.main()
