"""Frozen FR-P001 inputs, exact observation, durable callback storage and preflight.

No production module imports this experimental observer. CLI launch is separate.
"""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
from typing import Any, Callable, Iterator

import numpy as np
from numpy.typing import NDArray

from experiments import paper_probe as paper
__all__ = ["paper", "mix"]
from experiments.fr_i002_gate import State, FIELDS, mix, verify_pin

ROOT = Path(__file__).resolve().parents[1]
PREREG = 'reports/fr_p001_descendant_aware_transplant_preregistration.md'
PINS = {'experiments/phase1_probe.py': '3805a0d4987f2c24ba70fe25e9b688a9f40cb137',
        'experiments/paper_probe.py': 'ee2b67f4ce17d8f78842e5b778abf48d2e32f0e5',
        'experiments/fr_i002_provenance.py': 'ecee5b2beee62ce5a6ccddadb895540572760527',
        PREREG: '9396a1d8bfe38dec9aa3cab2edde2daa0d010fc8'}
POPULATION = 32768
EPOCHS = tuple(range(1, 10000, 100)) + (10000,)
FINAL = tuple(range(9101, 10000, 100)) + (10000,)
SEEDS = (202612001, 202612003, 202612008, 202612009,
         202613001, 202613008, 202613010, 202613013, 202613018)
RAW_BOUND = POPULATION * 64 * 2 * 101 * 18
DISK_REQUIRED = RAW_BOUND + 20 * 2**30
U8 = NDArray[np.uint8]
I64 = NDArray[np.int64]
AUDIT = np.dtype([('tape', 'V64'), ('labels', 'u1'), ('abundance', '<u8')])
METRICS = ('steps', 'execution_success', 'execution_scarcity_blocked',
           'execution_friction_blocked', 'mutation_success', 'mutation_scarcity_blocked',
           'mutation_friction_blocked', 'cross_success', 'cross_blocked')


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def atomic_json(path: Path, value: Any) -> None:
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('wb') as stream:
        stream.write(json_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def run_pins() -> dict[str, str]:
    verify_pin()
    for name, expected in PINS.items():
        data = (ROOT / name).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        require(blob == expected, f'frozen source changed: {name}')
        require(subprocess.check_output(['git', 'show', f'HEAD:{name}'], cwd=ROOT) == data,
                f'committed source mismatch: {name}')
    names = list(PINS) + ['experiments/fr_p001.py', 'experiments/run_fr_p001.py',
                         'experiments/fr_i002_gate.py',
                         'experiments/analyze_ac_p003_functional_origin_convergence.py',
                         'experiments/analyze_ac_p001_high_resource_origin_viability.py']
    return {name: sha(ROOT / name) for name in names}


ARTIFACT_VERSION = 'fr-p001-artifacts-v2'
REPAIR_POLICY = {
    'version': 1,
    'mechanics_runner_observer': 'fresh_output_version_and_full_rerun_unchanged_inputs',
    'analyzer_only': 'fresh_analysis_report_record_current_analyzer_and_validation_keep_preparation',
}


def analysis_pins() -> dict[str, str]:
    """Report implementation identity is deliberately outside the run identity."""
    name = 'experiments/analyze_fr_p001.py'
    return {name: sha(ROOT / name)}


def save_sources(directory: Path, identity: dict[str, str]) -> None:
    for name, expected in identity.items():
        data = (ROOT / name).read_bytes()
        require(digest(data) == expected, 'source changed during publication: ' + name)
        destination = directory / 'frozen_sources' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            require(sha(destination) == expected, 'frozen source copy mismatch: ' + name)
        else:
            destination.write_bytes(data)
    verify_sources(directory, identity)


def verify_sources(directory: Path, identity: dict[str, str]) -> None:
    for name, expected in identity.items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'invalid source path')
        require(sha(directory / 'frozen_sources' / name) == expected, 'frozen source copy mismatch: ' + name)


@contextmanager
def lock(path: Path, *, shared: bool = False) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        fcntl.flock(stream, mode | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


@contextmanager
def campaign_coordination(output: Path) -> Iterator[Callable[[], None]]:
    """Exclude launches and all workers before isolation or shared publication.

    The caller can downgrade its lock to shared after publishing, allowing worker
    entry while retaining the separate launch lock for the entire launch.
    """
    output.mkdir(parents=True, exist_ok=True)
    with (output.resolve() / '.campaign.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield lambda: fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


@contextmanager
def admission(output: Path) -> Iterator[int]:
    """One common six-slot, process-safe limit for every run-one entry point.

    Wait without allocating simulation state; flock releases a crashed worker's
    slot automatically. All paths resolve to the campaign's same lock inodes.
    """
    directory = output.resolve() / '.slots'
    directory.mkdir(exist_ok=True)
    while True:
        for index in range(6):
            stream = (directory / str(index)).open('a')
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                stream.close()
                continue
            try:
                yield index
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)
                stream.close()
            return
        time.sleep(0.05)


def score(tape: bytes) -> int:
    require(len(tape) == 64, 'score input must be 64 raw bytes')
    fn: Any = paper.score_selfrep_candidates
    value = int(fn(np.frombuffer(tape, dtype=np.uint8).reshape(1, 64).copy(), 0)[0])
    require(0 <= value <= 64, 'invalid evaluator output')
    return value


def database(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute('PRAGMA journal_mode=DELETE')
    db.execute('PRAGMA synchronous=FULL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS scores (
        tape BLOB PRIMARY KEY CHECK(length(tape)=64), score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 64)
      ) WITHOUT ROWID;
      CREATE TABLE IF NOT EXISTS callbacks (epoch INTEGER PRIMARY KEY, manifest TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS audit (
        epoch INTEGER NOT NULL, tape BLOB NOT NULL CHECK(length(tape)=64),
        labels INTEGER NOT NULL CHECK(labels BETWEEN 48 AND 64),
        abundance INTEGER NOT NULL CHECK(abundance>0),
        PRIMARY KEY(epoch,tape,labels)
      ) WITHOUT ROWID;
    ''')
    require(db.execute('PRAGMA integrity_check').fetchone() == ('ok',), 'SQLite integrity failure')
    return db


def fill_scores(db: sqlite3.Connection, sequences: list[bytes]) -> dict[bytes, int]:
    """Every miss is scored individually at seed zero; at most 4096 new rows per chunk."""
    result: dict[bytes, int] = {}
    for offset in range(0, len(sequences), 4096):
        new = []
        for tape in sequences[offset:offset + 4096]:
            row = db.execute('SELECT score FROM scores WHERE tape=?', (tape,)).fetchone()
            value = int(row[0]) if row is not None else score(tape)
            result[tape] = value
            if row is None:
                new.append((tape, value))
        db.executemany('INSERT INTO scores VALUES (?,?)', new)
    return result


def score_digest(db: sqlite3.Connection) -> str:
    h = hashlib.sha256()
    for tape, value in db.execute('SELECT tape,score FROM scores ORDER BY tape'):
        h.update(tape + bytes([value]))
    return h.hexdigest()


def audit_table(data: U8, labels: U8) -> NDArray[Any]:
    require(data.dtype == labels.dtype == np.uint8 and data.shape == labels.shape
            and data.ndim == 2 and data.shape[1] == 64, 'invalid soup/labels')
    require(np.all(labels <= 1), 'nonbinary labels')
    counts = labels.sum(axis=1)
    selected = np.flatnonzero(counts >= 48)
    table = Counter((data[i].tobytes(), int(counts[i])) for i in selected)
    rows = np.empty(len(table), dtype=AUDIT)
    for i, ((tape, count), abundance) in enumerate(sorted(table.items())):
        rows[i] = (np.void(tape), count, abundance)
    return rows


def aggregate(rows: NDArray[Any], scores: dict[bytes, int], data: U8, target: bytes) -> dict[str, Any]:
    functional = [r for r in rows if scores[r['tape'].tobytes()] == 64]
    nonexact = [r for r in functional if r['tape'].tobytes() != target]
    histogram = [sum(int(r['abundance']) for r in functional if int(r['labels']) == k)
                 for k in range(48, 65)]
    return {'candidate_abundance': sum(int(r['abundance']) for r in functional),
            'candidate_distinct': len({r['tape'].tobytes() for r in functional}),
            'nonexact_abundance': sum(int(r['abundance']) for r in nonexact),
            'nonexact_distinct': len({r['tape'].tobytes() for r in nonexact}),
            'qualifying_label_histogram_48_64': histogram,
            'qualifying_label_max': max((int(r['labels']) for r in functional), default=0),
            'exact_target': sum(row.tobytes() == target for row in data),
            'evaluated_tapes': sum(int(r['abundance']) for r in rows),
            'evaluated_unique': len(scores)}


def conservation(state: State, initial_pool: I64, totals: I64) -> None:
    a = state.arrays
    require(np.all(state.labels <= 1), 'nonbinary labels')
    require(all(v.dtype == np.int64 and np.all(v >= 0) for v in a.values()), 'invalid ledger')
    require(np.array_equal(np.bincount(state.data.ravel(), minlength=256) + a['pool'], totals),
            'conservation failure')
    require(np.array_equal(initial_pool + a['returns'] - a['withdrawals'], a['pool']), 'ledger failure')
    require(np.all(a['friction_blocked'] == 0), 'unexpected friction')
    require(int(a['counter'][0]) == int(a['withdrawals'].sum() + a['execution_blocked'].sum()
                                      + a['mutation_blocked'].sum()), 'changing-write counter mismatch')
    require(np.array_equal(np.sort(state.order), np.arange(len(state.data), dtype=np.uint32)), 'invalid order')



def validate_mechanics_record(state: State, metrics: I64, initial_pool: I64, totals: I64) -> None:
    """Common semantic validator for writing, resume, and independent analysis.

    Successful metrics include value-preserving no-ops; exchange ledgers and
    cross-copy ledgers count only actual value changes. Thus success is an upper
    bound on withdrawals, not an equality.
    """
    require(set(state.arrays) == set(FIELDS), 'mechanics ledger inventory')
    for key, value in state.arrays.items():
        require(value.shape == ((1,) if key == 'counter' else (256,)), 'mechanics ledger shape')
    conservation(state, initial_pool, totals)
    require(metrics.dtype == np.int64 and metrics.shape == (9,) and np.all(metrics >= 0), 'invalid metrics')
    steps, ex_ok, ex_block, ex_friction, mu_ok, mu_block, mu_friction, cross_ok, cross_block = map(int, metrics)
    a = state.arrays
    withdrawals = sum(map(int, a['withdrawals']))
    returns = sum(map(int, a['returns']))
    require(withdrawals == returns, 'mechanics withdrawal/return totals')
    require(ex_block == sum(map(int, a['execution_blocked']))
            and mu_block == sum(map(int, a['mutation_blocked'])), 'mechanics scarcity metrics/ledger mismatch')
    require(ex_friction == mu_friction == 0 and not np.any(a['friction_blocked']), 'mechanics nonzero friction')
    require(cross_ok == sum(map(int, a['cross_a_to_b'])) + sum(map(int, a['cross_b_to_a'])),
            'mechanics cross totals mismatch')
    require(np.all(a['cross_a_to_b'] + a['cross_b_to_a'] <= a['withdrawals']),
            'mechanics cross symbol withdrawals exceeded')
    require(cross_ok <= ex_ok and cross_block <= ex_block, 'mechanics cross metrics exceed execution')
    require(withdrawals <= ex_ok + mu_ok, 'mechanics exchanges exceed successful writes')
    require(ex_ok + ex_block <= steps, 'mechanics writes exceed execution steps')


def observe(db: sqlite3.Connection, directory: Path, state: State, epoch: int,
            metrics: I64, target: bytes, initial_pool: I64, totals: I64) -> dict[str, Any]:
    validate_mechanics_record(state, metrics, initial_pool, totals)
    rows = audit_table(state.data, state.labels)
    sequences = sorted({r['tape'].tobytes() for r in rows})
    snapshot = directory / f'epoch_{epoch:05d}.npz'
    audit = directory / f'audit_{epoch:05d}.npz'
    with db:
        scores = fill_scores(db, sequences)
        result = aggregate(rows, scores, state.data, target)
        for path, arrays in ((snapshot, {'soup': state.data, 'labels': state.labels,
                                       'order': state.order, 'metrics': metrics, **state.arrays}),
                             (audit, {'rows': rows})):
            with path.with_suffix('.tmp').open('wb') as stream:
                np.savez_compressed(stream, **arrays)
                stream.flush()
                os.fsync(stream.fileno())
            path.with_suffix('.tmp').replace(path)
        result.update(epoch=epoch, snapshot=snapshot.name, snapshot_sha256=sha(snapshot),
                      audit=audit.name, audit_sha256=sha(audit),
                      canonical_sha256=digest(rows.tobytes()),
                      soup_sha256=digest(state.data.tobytes()), labels_sha256=digest(state.labels.tobytes()),
                      scores_sha256=score_digest(db), metrics=dict(zip(METRICS, map(int, metrics))),
                      ledgers={k: v.tolist() for k, v in state.arrays.items()}, conservation_residual=0)
        db.executemany('INSERT INTO audit VALUES (?,?,?,?)',
                       [(epoch, r['tape'].tobytes(), int(r['labels']), int(r['abundance'])) for r in rows])
        db.execute('INSERT INTO callbacks VALUES (?,?)', (epoch, json.dumps(result, sort_keys=True)))
    return result


def load_snapshot(path: Path) -> tuple[State, I64]:
    with np.load(path, allow_pickle=False) as saved:
        state = State(saved['soup'], saved['labels'], {k: saved[k] for k in FIELDS}, saved['order'])
        metrics = saved['metrics']
    require(state.data.dtype == state.labels.dtype == np.uint8 and state.data.shape == state.labels.shape
            and state.data.ndim == 2 and state.data.shape[1] == 64, 'snapshot soup shape/dtype')
    require(state.order.dtype == np.uint32 and state.order.shape == (len(state.data),), 'snapshot order')
    require(metrics.dtype == np.int64 and metrics.shape == (9,) and np.all(metrics >= 0), 'snapshot metrics')
    for k, value in state.arrays.items():
        require(value.shape == ((1,) if k == 'counter' else (256,)), 'snapshot ledger shape')
    return state, metrics


def verify_callback(db: sqlite3.Connection, directory: Path, record: dict[str, Any],
                    target: bytes, initial_pool: I64, totals: I64) -> tuple[State, I64]:
    epoch = record['epoch']
    require(record['snapshot'] == f'epoch_{epoch:05d}.npz' and record['audit'] == f'audit_{epoch:05d}.npz',
            'noncanonical artifact path')
    for name in ('snapshot', 'audit'):
        require(sha(directory / record[name]) == record[name + '_sha256'], f'{name} checksum failure')
    state, metrics = load_snapshot(directory / record['snapshot'])
    validate_mechanics_record(state, metrics, initial_pool, totals)
    require(record['conservation_residual'] == 0, 'recorded conservation residual')
    rows = audit_table(state.data, state.labels)
    with np.load(directory / record['audit'], allow_pickle=False) as saved:
        require(saved['rows'].dtype == AUDIT and np.array_equal(rows, saved['rows']), 'audit reconstruction mismatch')
    require(digest(rows.tobytes()) == record['canonical_sha256'], 'canonical audit checksum')
    sql = db.execute('SELECT tape,labels,abundance FROM audit WHERE epoch=? ORDER BY tape,labels', (epoch,)).fetchall()
    require(sql == [(r['tape'].tobytes(), int(r['labels']), int(r['abundance'])) for r in rows], 'SQLite audit mismatch')
    sequences = sorted({r['tape'].tobytes() for r in rows})
    scores = {}
    for tape in sequences:
        row = db.execute('SELECT score FROM scores WHERE tape=?', (tape,)).fetchone()
        require(row is not None, 'missing cached score')
        scores[tape] = int(row[0])
    for k, v in aggregate(rows, scores, state.data, target).items():
        require(record[k] == v, f'aggregate mismatch: {k}')
    require(record['metrics'] == dict(zip(METRICS, map(int, metrics))), 'metrics mismatch')
    require(record['ledgers'] == {k: v.tolist() for k, v in state.arrays.items()}, 'ledgers mismatch')
    require(record['soup_sha256'] == digest(state.data.tobytes())
            and record['labels_sha256'] == digest(state.labels.tobytes()), 'array checksum mismatch')
    return state, metrics


def available_ram() -> int:
    fields = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    return int(fields['MemAvailable'].split()[0]) * 1024


def resources(directory: Path, elapsed: float, rss: int) -> dict[str, Any]:
    free = shutil.disk_usage(directory).free
    ram = available_ram()
    projection = elapsed * 101 * 18 / 6
    return {'elapsed_seconds': elapsed, 'max_rss_bytes': rss, 'projected_seconds': projection,
            'free_disk_bytes': free, 'required_disk_bytes': DISK_REQUIRED,
            'available_ram_bytes': ram, 'required_ram_bytes': 6 * rss + 4 * 2**30,
            'passed': 0 < elapsed <= 1200 and 0 < rss < 8 * 2**30 and projection <= 72 * 3600
                      and free >= DISK_REQUIRED and ram >= 6 * rss + 4 * 2**30}


def synthetic_worker(directory: Path) -> None:
    data = np.array([[mix(0xAC009200 ^ mix(i * 64 + b)) & 255 for b in range(64)]
                     for i in range(POPULATION)], dtype=np.uint8)
    require(len({row.tobytes() for row in data}) == POPULATION, 'synthetic tapes not distinct')
    labels = np.zeros_like(data)
    labels[:, :48] = 1
    warm_start = time.perf_counter()
    score(data[0].tobytes())
    warm_seconds = time.perf_counter() - warm_start
    start = time.perf_counter()
    db = database(directory / 'synthetic.sqlite')
    with db:
        rows = audit_table(data, labels)
        values = fill_scores(db, [r['tape'].tobytes() for r in rows])
        db.executemany('INSERT INTO audit VALUES (1,?,?,?)',
                       [(r['tape'].tobytes(), int(r['labels']), int(r['abundance'])) for r in rows])
        np.savez_compressed(directory / 'synthetic_snapshot.npz', soup=data, labels=labels)
        np.savez_compressed(directory / 'synthetic_audit.npz', rows=rows)
        require(len(values) == POPULATION, 'synthetic scoring incomplete')
    db.close()
    atomic_json(directory / 'timing.json', {'elapsed_seconds': time.perf_counter() - start,
                'warmup_seconds': warm_seconds, 'sequences': POPULATION, 'synthetic_sha256': digest(data.tobytes())})


def preflight(directory: Path) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False)
    source_pins = run_pins()
    started = time.perf_counter()
    subprocess.run(['/usr/bin/time', '-v', '-o', str(directory / 'time.txt'), sys.executable,
                    '-m', 'experiments.run_fr_p001', 'synthetic-worker', '--output', str(directory)],
                   env={**os.environ, 'NUMBA_NUM_THREADS': '1'}, cwd=ROOT, check=True)
    wall_seconds = time.perf_counter() - started
    timing = json.loads((directory / 'timing.json').read_text())
    elapsed = wall_seconds - timing['warmup_seconds']
    lines = (directory / 'time.txt').read_text().splitlines()
    rss = int(next(line.rsplit(':', 1)[1] for line in lines if 'Maximum resident set size' in line)) * 1024
    result = resources(directory, elapsed, rss)
    save_sources(directory, source_pins)
    result.update(run_pins=source_pins, artifact_version=ARTIFACT_VERSION, repair_policy=REPAIR_POLICY, total_child_wall_seconds=wall_seconds,
                  excluded_warmup_seconds=timing['warmup_seconds'], timing_sha256=sha(directory / 'timing.json'),
                  time_sha256=sha(directory / 'time.txt'), campaign='FR-P001')
    atomic_json(directory / 'preflight.json', result)
    require(result['passed'], 'FR-P001 resource preflight failed; campaign unevaluable')
    return result
