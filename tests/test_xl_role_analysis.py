"""Synthetic log reductions only; no native/VM execution."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from experiments.stringmol import xl_role_analysis as a
from experiments.stringmol import xl_renewal_synthesis as x


def fixture() -> tuple[list[dict[str, str]], x.Renewal, dict[int, x.Birth], list[dict[str, str]], dict[int, tuple[int, str]], dict[int, tuple[int, str, set[int]]]]:
    rows: list[dict[str, str]] = []

    def add(event: str, tick: int = 10, **kw: object) -> None:
        row = dict.fromkeys(a.SCHEDULE.split(','), '-1')
        row.update(event=event, tick=str(tick), index=str(len(rows)+1), policy='IMMEDIATE', ids='')
        row.update({k: str(v) for k, v in kw.items()})
        rows.append(row)

    add('START', 0, ids=';'.join(map(str, range(140))))
    add('DISPATCH', active=0, passive=1, owner=1, opcode=37, material_index=0)
    add('BIRTH', id=140, active=0, passive=1, source=0, material_index=1)
    add('COMPLETE', active=0, passive=1, material_index=1)
    for _ in range(2):
        add('SEARCH', id=140, other=0, count=3, selected=0, outcome='SELECTED')
        add('ENCOUNTER', id=140, other=0, active=0, passive=140, count=3, selected=0, outcome='BOUND')
    add('DISPATCH', active=0, passive=140, owner=140, opcode=37, material_index=1)
    add('BIRTH', id=145, active=0, passive=140, source=140, material_index=2)
    add('COMPLETE', active=0, passive=140, material_index=2)
    # Same-tick observed death following action is not administrative censoring.
    add('DEATH', id=140, material_index=3, outcome='DECAY')
    add('DECAY', id=140)
    # Failed and NO_CHANGE attempts cannot create a child or source success.
    add('DISPATCH', active=0, passive=145, owner=0, opcode=37, material_index=3)
    add('COMPLETE', active=0, passive=145, material_index=4)
    add('DISPATCH', active=0, passive=145, owner=145, opcode=37, material_index=4)
    add('COMPLETE', active=0, passive=145, material_index=5)
    add('CENSOR', 5000, id=145)
    add('END', 5000, ids=';'.join(map(str, [*range(140), 145])))
    edges: list[x.Obj] = [dict(child=c, source=s, tick=10, index=i, rooted_transfer=True)
                         for c, s, i in ((140, 0, 1), (145, 140, 2))]
    r = x.Renewal({}, {140: 10, 145: 10}, {140: 10}, edges, {})
    births = {140: x.Birth(10, b'AB', frozenset((0, 1))),
              145: x.Birth(10, b'AB', frozenset((0, 140)))}
    source = [dict(material_index=str(i), tick='10', child=str(c), source=str(s), active='0', passive=str(p))
              for i, c, s, p in ((1, 140, 0, 1), (2, 145, 140, 140), (4, -1, -1, 145), (5, -1, -1, 145))]
    cleaves = {1: (10, 'PLACED'), 2: (10, 'PLACED'), 4: (10, 'FAILED'), 5: (10, 'NO_CHANGE')}
    deaths = {3: (10, 'DECAY', {140})}
    return rows, r, births, source, cleaves, deaths


def run_fixture() -> a.Reduced:
    rows, r, births, source, cleaves, deaths = fixture()
    return a.reduce(iter(rows), r, births, source, cleaves, deaths)


class Qualification(unittest.TestCase):
    def test_passive_source_owner_differs_active(self) -> None:
        result = run_fixture()
        child = result.individuals[0]
        self.assertEqual(child['first_source_role'], 'passive')
        self.assertEqual(child['first_source_instruction_owner'], 140)
        self.assertEqual(child['first_source_partner'], 0)
        self.assertFalse(child['ever_active_success'])
        self.assertTrue(child['ever_source'])
        self.assertEqual(result.actions[0]['source_nonfounder'], False)
        self.assertEqual(len(result.individuals), 2)

    def test_same_tick_action_death_clock_null(self) -> None:
        child = run_fixture().individuals[0]
        self.assertLess(int(str(child['birth_order'])), int(str(child['first_source_order'])))
        self.assertLess(int(str(child['first_source_order'])), int(str(child['death_order'])))
        self.assertEqual(child['followup_ticks'], 0)
        self.assertIsNone(child['pre_searches_per_tick'])
        self.assertEqual(child['death_cause'], 'DECAY')
        self.assertFalse(child['alive_END'])

    def test_repeated_observed_encounters_not_candidates_of_partner(self) -> None:
        c = run_fixture().individuals[0]
        self.assertEqual(c['searches'], 2)
        self.assertEqual(c['search_candidates'], 6)
        self.assertEqual(c['encounter_initiator'], 2)
        self.assertEqual(c['binding_passive'], 2)
        self.assertEqual(c['pre_dispatch_passive'], 0)
        self.assertEqual(c['dispatch_passive'], 1)

    def test_failed_nochange_noncontiguous_survivor(self) -> None:
        result = run_fixture()
        self.assertEqual(result.totals['cleave_FAILED'], 1)
        self.assertEqual(result.totals['cleave_NO_CHANGE'], 1)
        c = result.individuals[1]
        self.assertEqual(c['id'], 145)
        self.assertEqual(c['no_event_termination'], 'END_administrative')
        self.assertIsNone(c['death_tick'])
        self.assertFalse(c['ever_source'])

    def test_late_noevent_and_empty_cohort(self) -> None:
        schedule, r, births, source, cleaves, deaths = fixture()
        for row in schedule:
            if row['tick'] == '10':
                row['tick'] = '4999'
        for row in source:
            row['tick'] = '4999'
        for edge in r.edges:
            edge['tick'] = 4999
        r.first = {140: 4999}
        births = {i: x.Birth(4999, b.sequence, b.participants) for i, b in births.items()}
        cleaves = {i: (4999, outcome) for i, (_, outcome) in cleaves.items()}
        deaths = {i: (4999, cause, removed) for i, (_, cause, removed) in deaths.items()}
        rows = a.reduce(iter(schedule), r, births, source, cleaves, deaths).individuals
        late = a.cohorts(rows)[2]
        self.assertEqual(late['admitted'], 2)
        self.assertEqual(late['no_event_END'], 1)
        self.assertEqual(late['renewal_fraction'], 0.5)
        for cohort in a.cohorts([]):
            self.assertIsNone(cohort['renewal_fraction'])
            self.assertIsNone(cohort['pre_searches_per_tick'])

    def test_active_success_and_empty_search(self) -> None:
        rows, r, births, source, cleaves, deaths = fixture()
        # Reverse the second successful pair: material source remains140.
        for row in rows:
            if row['event'] in ('DISPATCH', 'BIRTH', 'COMPLETE') and row['passive'] == '140':
                row['active'], row['passive'] = '140', '0'
        source[1]['active'], source[1]['passive'] = '140', '0'
        empty = dict(rows[4], count='0', other='-1', selected='-1', outcome='EMPTY')
        rows.insert(4, empty)
        for i, row in enumerate(rows, 1):
            row['index'] = str(i)
        c = a.reduce(iter(rows), r, births, source, cleaves, deaths).individuals[0]
        self.assertTrue(c['ever_active_success'])
        self.assertEqual(c['first_source_role'], 'active')
        self.assertEqual(c['empty_searches'], 1)
        self.assertEqual(c['pre_dispatch_active'], 0)
        self.assertIsNotNone(c['first_active_order'])

    def test_founders_only(self) -> None:
        rows = fixture()[0]
        start, end = rows[0], rows[-1]
        end.update(index='2', ids=start['ids'])
        result = a.reduce(iter((start, end)), x.Renewal({}, {}, {}, [], {}), {}, [], {}, {})
        self.assertEqual(result.individuals, [])
        self.assertEqual(len(result.end_ids), 140)

    def test_death_noevent_competing(self) -> None:
        c = a.Child(150, 4999, 3, False, True, death_tick=4999, death_order=4, death_cause='DECAY')
        self.assertEqual(c.row(10)['no_event_termination'], 'death_competing')
        self.assertEqual(c.row(10)['followup_ticks'], 0)

    def test_corrupt_join_failures(self) -> None:
        for kind in ('source', 'child', 'owner', 'order', 'death', 'end', 'duplicate', 'missing', 'encounter'):
            rows, r, births, source, cleaves, deaths = copy.deepcopy(fixture())
            if kind == 'source':
                source[1]['source'] = '0'
            elif kind == 'child':
                rows[9]['source'] = '999'
            elif kind == 'owner':
                rows[1]['owner'] = '999'
            elif kind == 'order':
                rows[4]['index'] = '99'
            elif kind == 'death':
                deaths[3] = (9, 'DECAY', {140})
            elif kind == 'end':
                rows[-1]['ids'] = '0'
            elif kind == 'duplicate':
                source.append(source[0])
            elif kind == 'encounter':
                rows[5]['other'] = '1'
            else:
                source.pop()
            with self.assertRaises((ValueError, KeyError), msg=kind):
                a.reduce(iter(rows), r, births, source, cleaves, deaths)

    def test_stream_schema_hash_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'input.csv'
            p.write_text('a,b\n1,2\n')
            self.assertEqual(list(a.stream(p, 'a,b')), [dict(a='1', b='2')])
            for contents in ('b,a\n1,2\n', 'a,b\n1\n', 'a,b\n"1",2\n'):
                p.write_text(contents)
                with self.assertRaises(ValueError):
                    list(a.stream(p, 'a,b'))
            with self.assertRaises(ValueError):
                x.verify(p, '0'*64)
            out = Path(tmp)/'new'
            x.fresh(out)
            with self.assertRaises(FileExistsError):
                x.fresh(out)


if __name__ == '__main__':
    unittest.main()
