"""Independent, sequential FR-P001 snapshot reconstruction and seed-zero rescoring.

Run only when outcome inspection is authorized. Runner aggregates are checked
against independently reconstructed occurrences, never accepted on checksums alone.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import struct
import tempfile
from typing import Any

import numpy as np

from experiments import fr_p001 as f
from experiments.run_fr_p001 import validate_preparation


def reconstruct(soup: f.U8, labels: f.U8, target: bytes,
                cache: sqlite3.Connection) -> tuple[bytes, list[tuple[bytes, int, int]], dict[str, Any]]:
    """Independent implementation: Python byte counts and struct serialization."""
    f.require(soup.dtype == labels.dtype == np.uint8 and soup.shape == labels.shape
              and soup.ndim == 2 and soup.shape[1] == 64 and np.all(labels <= 1), 'invalid snapshot arrays')
    counts: dict[tuple[bytes, int], int] = defaultdict(int)
    exact = 0
    for tape, provenance in zip(soup, labels, strict=True):
        raw = bytes(tape)
        exact += raw == target
        count = sum(bytes(provenance))
        if count >= 48:
            counts[raw, count] += 1
    records = [(tape, count, abundance) for (tape, count), abundance in sorted(counts.items())]
    sequences = sorted({tape for tape, _, _ in records})
    scores = {}
    # This cache is freshly created by the analyzer, never copied from the runner.
    with cache:
        for offset in range(0, len(sequences), 4096):
            for tape in sequences[offset:offset + 4096]:
                row = cache.execute('SELECT score FROM independent WHERE tape=?', (tape,)).fetchone()
                if row is None:
                    evaluator: Any = f.paper.score_selfrep_candidates
                    value = int(evaluator(np.frombuffer(tape, dtype=np.uint8).copy().reshape(1, 64), 0)[0])
                    f.require(0 <= value <= 64, 'independent evaluator invalid')
                    cache.execute('INSERT INTO independent VALUES (?,?)', (tape, value))
                else:
                    value = int(row[0])
                scores[tape] = value
    abundance = nonexact = 0
    distinct: set[bytes] = set()
    nonexact_distinct: set[bytes] = set()
    histogram = [0] * 17
    maximum = 0
    for tape, count, occurrences in records:
        if scores[tape] == 64:
            abundance += occurrences
            distinct.add(tape)
            histogram[count - 48] += occurrences
            maximum = max(maximum, count)
            if tape != target:
                nonexact += occurrences
                nonexact_distinct.add(tape)
    result = {'candidate_abundance': abundance, 'candidate_distinct': len(distinct),
              'nonexact_abundance': nonexact, 'nonexact_distinct': len(nonexact_distinct),
              'qualifying_label_histogram_48_64': histogram, 'qualifying_label_max': maximum,
              'exact_target': exact, 'evaluated_tapes': sum(counts.values()), 'evaluated_unique': len(sequences)}
    canonical = b''.join(tape + struct.pack('<BQ', count, n) for tape, count, n in records)
    return canonical, records, result


def endpoint(trajectory: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    f.require([r['epoch'] for r in trajectory] == list(f.EPOCHS), 'incomplete endpoint schedule')
    final = [r for r in trajectory if r['epoch'] in f.FINAL]
    return {'post_transient_load': sum(r['nonexact_abundance'] for r in trajectory if r['epoch'] >= 1001),
            'final_nonexact_abundance': trajectory[-1]['nonexact_abundance'],
            'sustained': all(r['nonexact_abundance'] > 0 and (arm == 'shuffle' or r['exact_target'] == 0)
                             for r in final),
            'final_exact_target': trajectory[-1]['exact_target']}


def decision(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    f.require(len(pairs) == 9, 'incomplete paired endpoints')
    witnesses = sum(p['witness']['sustained'] for p in pairs)
    controls = sum(p['shuffle']['sustained'] for p in pairs)
    wins = sum(p['witness']['post_transient_load'] > p['shuffle']['post_transient_load'] for p in pairs)
    gates = {'integrity': True, 'witness_sampled_presence': witnesses >= 7,
             'control_specificity': controls <= 1, 'paired_load': wins >= 8}
    passed = all(gates.values())
    return {'status': 'pass' if passed else 'fail_with_valid_integrity', 'gates': gates,
            'sustained_witnesses': witnesses, 'sustained_controls': controls, 'paired_wins': wins,
            'one_sided_fair_sign_tail': sum(math.comb(9, k) for k in range(wins, 10)) / 512,
            'claim': ('Supports sustained sampled presence of non-exact operational functional-descendant candidates.'
                      if passed else 'Composite persistence criterion failed. Stop BFF lineage/persistence/ecology work; '
                      'pivot to a substrate with explicit atomic reproduction and lineage identity.'),
            'limitations': 'Sampled presence is not continuous lineage continuity. Value-change provenance omits '
                          'control/address dependence and does not establish inherited-byte causation, biological '
                          'ancestry, heredity, organisms, adaptation, ecology, or organization. Non-exact changes '
                          'need not be mutation-derived. The sign probability is descriptive: selected strict '
                          'origins and repeated callbacks within pairs. A heredity experiment needs a new preregistration.'}


def analyze(output: Path, report: Path) -> dict[str, Any]:
    report.mkdir(parents=True, exist_ok=True)
    f.require(not (report / 'analysis.json').exists(), 'analyzer repair requires a fresh report directory')
    analyzer_identity = f.analysis_pins()
    f.save_sources(report, analyzer_identity)
    result: dict[str, Any]
    try:
        prepared = validate_preparation(output)
        isolation = json.loads((output / 'isolation.json').read_text())
        f.require(isolation['passed'] and isolation['run_pins'] == f.run_pins(), 'observation isolation missing/stale')
        pairs, trajectories = [], []
        with tempfile.TemporaryDirectory(prefix='fr-p001-analysis-', dir=report) as temporary:
            cache = sqlite3.connect(Path(temporary) / 'independent.sqlite')
            cache.execute('CREATE TABLE independent (tape BLOB PRIMARY KEY, score INTEGER NOT NULL) WITHOUT ROWID')
            try:
                for index, pair in enumerate(prepared['pairs']):
                    endpoints: dict[str, Any] = {'index': index}
                    for arm in ('witness', 'shuffle'):
                        directory = output / 'runs' / f'{index:02d}_{arm}'
                        complete = json.loads((directory / 'complete.json').read_text())
                        binding = {'preparation_sha256': f.sha(output / 'preparation.json'), 'index': index, 'arm': arm}
                        f.require(json.loads((directory / 'binding.json').read_text()) == binding, 'run binding mismatch')
                        f.require(all(complete[k] == v for k, v in binding.items()), 'completion binding mismatch')
                        f.require(complete['epochs'] == list(f.EPOCHS), 'completion schedule')
                        f.require(f.sha(directory / 'run.sqlite') == complete['database_sha256'], 'database checksum')
                        db = sqlite3.connect(f'file:{(directory / "run.sqlite").resolve()}?mode=ro', uri=True)
                        try:
                            f.require(db.execute('PRAGMA integrity_check').fetchone() == ('ok',), 'database integrity')
                            saved = db.execute('SELECT epoch,manifest FROM callbacks ORDER BY epoch').fetchall()
                            f.require([r[0] for r in saved] == list(f.EPOCHS), 'callback schedule')
                            target = bytes.fromhex(pair['arms'][arm]['target_hex'])
                            with np.load(output / pair['arms'][arm]['path'], allow_pickle=False) as initial:
                                pool = initial['pool']
                                totals = pool + np.bincount(initial['soup'].ravel(), minlength=256)
                            trajectory = []
                            previous_metrics: f.I64 = np.zeros(9, dtype=np.int64)
                            previous_ledgers = {k: np.zeros_like(v) for k, v in f.load_snapshot(directory / 'epoch_00001.npz')[0].arrays.items()}
                            seen: set[bytes] = set()
                            for epoch, manifest in saved:
                                record = json.loads(manifest)
                                f.require(record['epoch'] == epoch, 'callback identity mismatch')
                                state, metrics = f.verify_callback(db, directory, record, target, pool, totals)
                                f.validate_mechanics_record(state, metrics, pool, totals)
                                f.require(len(state.data) == f.POPULATION, 'snapshot population')
                                f.require(np.all(metrics >= previous_metrics), 'nonmonotone metrics')
                                for key, value in state.arrays.items():
                                    if key != 'pool':
                                        f.require(np.all(value >= previous_ledgers[key]), 'nonmonotone ledger')
                                previous_metrics, previous_ledgers = metrics, state.arrays
                                canonical, rows, values = reconstruct(state.data, state.labels, target, cache)
                                f.require(hashlib.sha256(canonical).hexdigest() == record['canonical_sha256'], 'independent audit checksum')
                                with np.load(directory / record['audit'], allow_pickle=False) as audit:
                                    f.require(audit['rows'].tobytes() == canonical, 'independent audit contents')
                                f.require(rows == db.execute('SELECT tape,labels,abundance FROM audit WHERE epoch=? ORDER BY tape,labels',
                                                            (epoch,)).fetchall(), 'independent SQLite audit')
                                for tape, _, _ in rows:
                                    seen.add(tape)
                                    independent = cache.execute('SELECT score FROM independent WHERE tape=?', (tape,)).fetchone()
                                    f.require(independent == db.execute('SELECT score FROM scores WHERE tape=?', (tape,)).fetchone(),
                                              'independent rescore mismatch')
                                f.require(all(record[k] == v for k, v in values.items()), 'independent aggregate mismatch')
                                trajectory.append({'epoch': epoch, **values})
                            f.require(db.execute('SELECT count(*) FROM scores').fetchone()[0] == len(seen), 'unobserved cache rows')
                            f.require(db.execute('SELECT DISTINCT epoch FROM audit ORDER BY epoch').fetchall()
                                      == [(r['epoch'],) for r in trajectory if r['evaluated_tapes']], 'extra audit epochs')
                            f.require(record['scores_sha256'] == f.score_digest(db), 'final score cache checksum')
                            f.require(complete['soup_sha256'] == record['soup_sha256']
                                      and complete['labels_sha256'] == record['labels_sha256'], 'final arrays mismatch')
                            endpoints[arm] = endpoint(trajectory, arm)
                            trajectories.append({'index': index, 'arm': arm, 'callbacks': trajectory})
                        finally:
                            db.close()
                    pairs.append(endpoints)
            finally:
                cache.close()
        result = {**decision(pairs), 'pairs': pairs, 'trajectories': trajectories,
                  'preparation_sha256': f.sha(output / 'preparation.json'), 'run_pins': f.run_pins()}
    except Exception as error:
        result = {'status': 'unevaluable', 'gates': {'integrity': False, 'witness_sampled_presence': None,
                  'control_specificity': None, 'paired_load': None}, 'error': repr(error),
                  'decision': 'Repair mechanics, observation, or artifact integrity only; rerun unchanged inputs.'}
    f.require(f.analysis_pins() == analyzer_identity, 'analyzer changed during validation')
    f.verify_sources(report, analyzer_identity)
    result['analysis_provenance'] = {'repair_policy': f.REPAIR_POLICY, 'analyzer_pins': analyzer_identity,
        'validation': 'passed' if result['gates']['integrity'] else 'unevaluable',
        'method': 'full snapshot reconstruction and independent individual seed-zero rescoring'}
    f.atomic_json(report / 'analysis.json', result)
    lines = ['# FR-P001 independent analysis', '', f"Status: **{result['status']}**", '',
             '| Gate | Result |', '|---|---|']
    lines += [f'| {key} | {value} |' for key, value in result['gates'].items()]
    if 'pairs' in result:
        lines += ['', '| Pair | Witness load | Shuffle load | Witness final | Shuffle final | Witness sustained | Shuffle sustained |',
                  '|---|---:|---:|---:|---:|---|---|']
        for p in result['pairs']:
            w, s = p['witness'], p['shuffle']
            lines.append(f"| {p['index']} | {w['post_transient_load']} | {s['post_transient_load']} | "
                         f"{w['final_nonexact_abundance']} | {s['final_nonexact_abundance']} | {w['sustained']} | {s['sustained']} |")
        lines += ['', f"One-sided fair-sign tail: {result['one_sided_fair_sign_tail']}", '', result['claim'], '', result['limitations'],
                  '', 'Full callback trajectories and exact-target diagnostics: `analysis.json`.']
    else:
        lines += ['', result['error'], '', result['decision']]
    (report / 'analysis.md').write_text('\n'.join(lines) + '\n')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparation', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.preparation, args.report)
    if result['status'] == 'unevaluable':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
