"""FR-P001 preparation and explicit six-process execution. No launch during preparation."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np

from experiments import fr_p001 as f
from experiments import analyze_ac_p003_functional_origin_convergence as source
from experiments.fr_i002_gate import State


def control(witness: f.U8, index: int) -> f.U8:
    f.require(witness.shape == (64,) and witness.dtype == np.uint8 and 0 <= index < 9, 'invalid control input')
    result = witness.copy()
    for j in range(63, 0, -1):
        k = f.mix(0xAC009000 ^ f.mix(index * 64 + j)) % (j + 1)
        result[j], result[k] = result[k], result[j]
    f.require(not np.array_equal(witness, result), 'unchanged frozen control')
    f.require(np.array_equal(np.bincount(witness, minlength=256), np.bincount(result, minlength=256)),
              'control composition mismatch')
    return result


def paired(witness: f.U8, shuffled: f.U8, index: int) -> tuple[f.U8, f.U8, Any, f.U8]:
    seed = 202619000 + index
    initialize: Any = f.paper.initialize_soup
    shuffle: Any = f.paper.shuffle_indices
    background = initialize(f.POPULATION, seed)
    order = np.arange(f.POPULATION, dtype=np.uint32)
    shuffle(order, seed, 0xAC009100 + index)
    indices = order[:32].copy()
    left, right = background.copy(), background.copy()
    left[indices], right[indices] = witness, shuffled
    labels = np.zeros_like(left)
    labels[indices] = 1
    f.require(np.array_equal(np.bincount(left.ravel(), minlength=256), np.bincount(right.ravel(), minlength=256)),
              'paired histogram mismatch')
    mask = np.ones(f.POPULATION, dtype=bool)
    mask[indices] = False
    f.require(np.array_equal(left[mask], right[mask]), 'paired background mismatch')
    return left, right, indices, labels


def validate_preflight(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = json.loads(path.read_text())
    f.require(record['passed'] and record['run_pins'] == f.run_pins(), 'missing/stale preflight')
    for filename, key in (('timing.json', 'timing_sha256'), ('time.txt', 'time_sha256')):
        f.require(f.sha(path.parent / filename) == record[key], 'preflight evidence checksum')
    f.require(record['artifact_version'] == f.ARTIFACT_VERSION and record['repair_policy'] == f.REPAIR_POLICY,
              'preflight version/policy mismatch')
    f.verify_sources(path.parent, record['run_pins'])
    return record


def prepare(output: Path, p001: Path, p002: Path, preflight: Path, *, output_version: str) -> dict[str, Any]:
    evidence = validate_preflight(preflight)
    output.mkdir(parents=True, exist_ok=True)
    f.require(f.resources(output, evidence['elapsed_seconds'], evidence['max_rss_bytes'])['passed'],
              'destination resources fail preflight')
    with f.campaign_coordination(output), f.lock(output / '.prepare.lock'):
        f.require(bool(output_version.strip()), 'output version is required')
        version: dict[str, Any] = {'artifact_version': f.ARTIFACT_VERSION, 'output_version': output_version,
                   'run_pins': f.run_pins(), 'repair_policy': f.REPAIR_POLICY}
        if (output / 'version.json').exists():
            f.require(json.loads((output / 'version.json').read_text()) == version,
                      'run repair requires a fresh output version and full rerun unchanged inputs')
        else:
            f.require(not any(p.name not in ('.campaign.lock', '.prepare.lock') for p in output.iterdir()),
                      'fresh output directory required for this version')
            f.atomic_json(output / 'version.json', version)
        if (output / 'preparation.json').exists():
            return validate_preparation(output)
        validated = []
        for index, seed in enumerate(f.SEEDS):
            campaign, root = ('AC-P001', p001) if index < 4 else ('AC-P002', p002)
            run = source.Run(campaign, 16, seed)
            checkpoint = source.load_checkpoint(root / run.name, run)
            witness = checkpoint.witness.copy()
            f.require(f.score(witness.tobytes()) == 64, 'held-out witness failed individual seed-0 score')
            shuffled = control(witness, index)
            value = f.score(shuffled.tobytes())
            f.require(value < 64, 'frozen control scored 64; no resampling permitted')
            validated.append((checkpoint, witness, shuffled, value, root / run.name))
        pairs = []
        for index, (checkpoint, witness, shuffled, value, source_path) in enumerate(validated):
            left, right, indices, labels = paired(witness, shuffled, index)
            pair: dict[str, Any] = {'index': index, 'source_seed': f.SEEDS[index],
                'recipient_seed': 202619000 + index, 'source_path': str(source_path.resolve()),
                'source_checksums': checkpoint.checksums, 'source_epoch': checkpoint.epoch,
                'source_rank': checkpoint.witness_rank, 'witness_score': 64, 'shuffle_score': value, 'arms': {}}
            for arm, data, target in (('witness', left, witness), ('shuffle', right, shuffled)):
                path = output / f'input_{index:02d}_{arm}.npz'
                pool = np.bincount(data.ravel(), minlength=256).astype(np.int64) * 16
                with path.with_suffix('.tmp').open('wb') as stream:
                    np.savez_compressed(stream, soup=data, labels=labels, indices=indices, pool=pool)
                    stream.flush()
                    os.fsync(stream.fileno())
                path.with_suffix('.tmp').replace(path)
                pair['arms'][arm] = {'path': path.name, 'sha256': f.sha(path),
                    'target_hex': target.tobytes().hex(), 'soup_sha256': f.digest(data.tobytes()),
                    'labels_sha256': f.digest(labels.tobytes()), 'indices_sha256': f.digest(indices.tobytes()),
                    'pool_sha256': f.digest(pool.astype('<i8').tobytes())}
            pairs.append(pair)
        f.save_sources(output, version['run_pins'])
        result = {'campaign': 'FR-P001', **version, 'preflight': evidence,
                  'preflight_path': str(preflight.resolve()), 'pairs': pairs,
                  'epochs': list(f.EPOCHS), 'workers': 6, 'numba_num_threads': 1}
        # Publish only after all nine source/control checks and all eighteen inputs succeed.
        (output / 'preparation.sha256').write_text(f.digest(f.json_bytes(result)) + '\n')
        f.atomic_json(output / 'preparation.json', result)
        return validate_preparation(output)


def validate_preparation(output: Path) -> dict[str, Any]:
    path = output / 'preparation.json'
    f.require(f.sha(path) == (output / 'preparation.sha256').read_text().strip(), 'preparation checksum')
    record: dict[str, Any] = json.loads(path.read_text())
    f.require(record['campaign'] == 'FR-P001' and record['run_pins'] == f.run_pins(), 'preparation run pins mismatch; fresh output version and full rerun required')
    f.require(record['artifact_version'] == f.ARTIFACT_VERSION and record['repair_policy'] == f.REPAIR_POLICY,
              'preparation repair policy/version mismatch')
    version = {k: record[k] for k in ('artifact_version', 'output_version', 'run_pins', 'repair_policy')}
    f.require(json.loads((output / 'version.json').read_text()) == version, 'output version binding mismatch')
    f.verify_sources(output, record['run_pins'])
    f.require(record['preflight']['run_pins'] == record['run_pins'], 'preflight run pin mismatch')
    f.require(record['epochs'] == list(f.EPOCHS) and record['workers'] == 6
              and record['numba_num_threads'] == 1, 'preparation protocol')
    f.require(len(record['pairs']) == 9 and record['preflight']['passed'], 'incomplete preparation')
    for index, pair in enumerate(record['pairs']):
        f.require(pair['index'] == index and pair['source_seed'] == f.SEEDS[index]
                  and pair['recipient_seed'] == 202619000 + index, 'pair identity')
        f.require(pair['witness_score'] == 64 and 0 <= pair['shuffle_score'] < 64, 'input scores')
        targets = [np.frombuffer(bytes.fromhex(pair['arms'][arm]['target_hex']), dtype=np.uint8)
                   for arm in ('witness', 'shuffle')]
        f.require(np.array_equal(control(targets[0], index), targets[1]), 'frozen shuffle mismatch')
        left, right, indices, labels = paired(targets[0], targets[1], index)
        for arm, expected in (('witness', left), ('shuffle', right)):
            item = pair['arms'][arm]
            f.require(item['path'] == f'input_{index:02d}_{arm}.npz', 'input path')
            f.require(f.sha(output / item['path']) == item['sha256'], 'input checksum')
            with np.load(output / item['path'], allow_pickle=False) as saved:
                for key, value in (('soup', expected), ('labels', labels), ('indices', indices),
                                   ('pool', np.bincount(expected.ravel(), minlength=256).astype(np.int64) * 16)):
                    f.require(saved[key].dtype == value.dtype and np.array_equal(saved[key], value), 'input reconstruction: ' + key)
                    f.require(f.digest(saved[key].tobytes()) == item[key + '_sha256'], 'input array checksum')
    return record


def isolation(directory: Path) -> dict[str, Any]:
    """Exercise real SQLite/snapshot observation versus no observation, including mechanics."""
    directory.mkdir(parents=True, exist_ok=True)
    initialize: Any = f.paper.initialize_soup
    shuffle: Any = f.paper.shuffle_indices
    data = initialize(32, 202619000)
    # Dense write/copy instructions and mixed provenance ensure changing state.
    data[0, :8] = np.frombuffer(b'>+}.>,+-', dtype=np.uint8)
    labels = np.ones_like(data)
    labels[16:, 48:] = 0
    pool = np.bincount(data.ravel(), minlength=256).astype(np.int64) * 16
    totals = pool + np.bincount(data.ravel(), minlength=256)
    plain = State.create(data, labels, pool)
    observed = plain.copy()
    production = plain.copy()
    cumulative = np.zeros(9, dtype=np.int64)
    db = f.database(directory / 'isolation.sqlite')
    try:
        for epoch in range(4):
            results = []
            for state, provenance in ((plain, True), (observed, True), (production, False)):
                shuffle(state.order, 202619000, epoch)
                results.append(state.epoch(provenance, 202619000, epoch, (1 << 30) // 4096, 0))
            f.require(results[0] == results[1] == results[2], 'observation mechanics metrics changed')
            cumulative += np.array(results[0], dtype=np.int64)
            f.observe(db, directory, observed, epoch + 1, cumulative, data[0].tobytes(), pool, totals)
            f.require(plain.digest(tuple(cumulative)) == observed.digest(tuple(cumulative)), 'observation altered state')
            from experiments.fr_i002_gate import equal
            equal(observed, production, 'production isolation', labels=False)
        return {'passed': True, 'epochs': 4, 'state_sha256': f.digest(observed.digest(tuple(cumulative))),
                'run_pins': f.run_pins()}
    finally:
        db.close()



def check_launch_resources(output: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    evidence = validate_preflight(Path(prepared['preflight_path']))
    f.require(evidence == prepared['preflight'], 'preflight evidence changed since preparation')
    current = f.resources(output.resolve(), evidence['elapsed_seconds'], evidence['max_rss_bytes'])
    f.require(current['passed'], 'campaign output resources fail frozen free-space/RAM requirements')
    return current


def publish_isolation(output: Path) -> dict[str, Any]:
    """Caller must hold exclusive campaign coordination before this publication."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix='isolation-', dir=output) as temp:
        evidence = isolation(Path(temp))
    f.atomic_json(output / 'isolation.json', evidence)
    return evidence


def validate_isolation(output: Path) -> dict[str, Any]:
    """Refresh campaign-bound evidence without starting any campaign run."""
    with f.campaign_coordination(output):
        prepared = validate_preparation(output)
        check_launch_resources(output, prepared)
        return publish_isolation(output)


def run_one(output: Path, index: int, arm: str) -> None:
    with f.lock(output.resolve() / '.campaign.lock', shared=True), f.admission(output):
        _run_one_admitted(output, index, arm)


def _run_one_admitted(output: Path, index: int, arm: str) -> None:
    f.require(os.environ.get('NUMBA_NUM_THREADS') == '1', 'NUMBA_NUM_THREADS must be 1')
    f.require(0 <= index < 9 and arm in ('witness', 'shuffle'), 'invalid run identity')
    record = validate_preparation(output)
    check_launch_resources(output, record)
    evidence = json.loads((output / 'isolation.json').read_text())
    f.require(evidence['passed'] and evidence['run_pins'] == f.run_pins(), 'missing/stale isolation evidence')
    directory = output / 'runs' / f'{index:02d}_{arm}'
    directory.mkdir(parents=True, exist_ok=True)
    with f.lock(directory / '.lock'):
        binding = {'preparation_sha256': f.sha(output / 'preparation.json'), 'index': index, 'arm': arm}
        if (directory / 'binding.json').exists():
            f.require(json.loads((directory / 'binding.json').read_text()) == binding, 'run input binding mismatch')
        else:
            f.require(not (directory / 'run.sqlite').exists(), 'unbound existing database')
            f.atomic_json(directory / 'binding.json', binding)
        if (directory / 'complete.json').exists():
            complete = json.loads((directory / 'complete.json').read_text())
            f.require(all(complete[k] == v for k, v in binding.items())
                      and complete['epochs'] == list(f.EPOCHS), 'completion identity mismatch')
            f.require(complete['database_sha256'] == f.sha(directory / 'run.sqlite'), 'completed database checksum')
        item = record['pairs'][index]['arms'][arm]
        with np.load(output / item['path'], allow_pickle=False) as saved:
            pool = saved['pool']
            totals = pool + np.bincount(saved['soup'].ravel(), minlength=256)
            state = State.create(saved['soup'], saved['labels'], pool)
        target = bytes.fromhex(item['target_hex'])
        metrics: f.I64 = np.zeros(9, dtype=np.int64)
        db = f.database(directory / 'run.sqlite')
        try:
            saved_callbacks = db.execute('SELECT epoch,manifest FROM callbacks ORDER BY epoch').fetchall()
            callbacks = [json.loads(row[1]) for row in saved_callbacks]
            f.require([r['epoch'] for r in callbacks] == [r[0] for r in saved_callbacks], 'callback key mismatch')
            f.require([r['epoch'] for r in callbacks] == list(f.EPOCHS[:len(callbacks)]), 'invalid resume schedule')
            for callback in callbacks:
                state, metrics = f.verify_callback(db, directory, callback, target, pool, totals)
                f.require(len(state.data) == f.POPULATION, 'resume population')
            if callbacks:
                f.require(callbacks[-1]['scores_sha256'] == f.score_digest(db), 'score cache checksum mismatch')
            else:
                f.require(db.execute('SELECT count(*) FROM scores').fetchone()[0] == 0, 'uncommitted score cache')
            f.require(db.execute('SELECT DISTINCT epoch FROM audit ORDER BY epoch').fetchall()
                      == [(r['epoch'],) for r in callbacks if r['evaluated_tapes']], 'extra audit epochs')
            start = callbacks[-1]['epoch'] if callbacks else 0
            shuffle: Any = f.paper.shuffle_indices
            for epoch in range(start, f.EPOCHS[-1]):
                shuffle(state.order, 202619000 + index, epoch)
                metrics += np.array(state.epoch(True, 202619000 + index, epoch, (1 << 30) // 4096, 0), dtype=np.int64)
                if epoch + 1 in f.EPOCHS:
                    f.observe(db, directory, state, epoch + 1, metrics, target, pool, totals)
            f.atomic_json(directory / 'complete.json', {**binding, 'epochs': list(f.EPOCHS),
                'soup_sha256': f.digest(state.data.tobytes()), 'labels_sha256': f.digest(state.labels.tobytes()),
                'database_sha256': f.sha(directory / 'run.sqlite')})
            (directory / 'failure.json').unlink(missing_ok=True)
        except Exception as error:
            f.atomic_json(directory / 'failure.json', {'status': 'unevaluable', 'error': repr(error)})
            raise
        finally:
            db.close()


def launch(output: Path) -> None:
    # Lock before validation, isolation, or any shared artifact publication.
    with f.lock(output.resolve() / '.launch.lock'), f.campaign_coordination(output) as admit_workers:
        prepared = validate_preparation(output)
        check_launch_resources(output, prepared)
        publish_isolation(output)
        env = {**os.environ, 'NUMBA_NUM_THREADS': '1'}
        def task(identity: tuple[int, str]) -> None:
            i, arm = identity
            command = [sys.executable, '-m', 'experiments.run_fr_p001', 'run-one',
                       '--output', str(output.resolve()), '--pair', str(i), '--arm', arm]
            subprocess.run(command, env=env, cwd=f.ROOT, check=True)
        # Shared coordination permits workers, but blocks another publication.
        # Every child (and every standalone run-one) acquires the same six slots.
        admit_workers()
        with ThreadPoolExecutor(max_workers=6) as workers:
            list(workers.map(task, [(i, arm) for i in range(9) for arm in ('witness', 'shuffle')]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'synthetic-worker', 'prepare', 'run-one', 'launch', 'isolation', 'validate-isolation'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--preflight', type=Path)
    parser.add_argument('--output-version')
    parser.add_argument('--p001-root', type=Path, default=Path('sweeps/ac_p001_high_resource_origin_viability/runs'))
    parser.add_argument('--p002-root', type=Path, default=Path('sweeps/ac_p002_resource_abundance_origin/runs'))
    parser.add_argument('--pair', type=int)
    parser.add_argument('--arm', choices=('witness', 'shuffle'))
    args = parser.parse_args()
    if args.action == 'preflight':
        f.preflight(args.output)
    elif args.action == 'synthetic-worker':
        f.synthetic_worker(args.output)
    elif args.action == 'prepare':
        if args.preflight is None or args.output_version is None:
            parser.error('--preflight and --output-version are required')
        prepare(args.output, args.p001_root, args.p002_root, args.preflight, output_version=args.output_version)
    elif args.action == 'run-one':
        if args.pair is None or args.arm is None:
            parser.error('--pair and --arm are required')
        run_one(args.output, args.pair, args.arm)
    elif args.action == 'validate-isolation':
        print(json.dumps(validate_isolation(args.output), indent=2))
    elif args.action == 'isolation':
        print(json.dumps(isolation(args.output), indent=2))
    else:
        launch(args.output)


if __name__ == '__main__':
    main()
