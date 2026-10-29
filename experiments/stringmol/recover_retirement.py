"""SM-B002-R1: fail-closed, whole-matrix recovery of the documented ENOSPC attempt.

See reports/sm_b002_artifact_recovery_addendum.md. No original scientific module
is modified. Gates, preparation, execution, replay and repeat replay run in order.
"""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from experiments.stringmol import (
    analyze_decay as ad, analyze_mutation as am, analyze_renewal as ah,
    analyze_retirement as ar, conservation_workflow as c, lineage_workflow as lw,
    mutation_workflow as mw, perturbation_panel as panel, renewal_workflow as hw,
    retirement_workflow as w, scheduling_workflow as bw,
)
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.configure_control import StringmolControlConfig, render_config

PROTOCOL = 'SM-B002-R1'
OLD_PREPARATION = '0a67c2bc01c744a1d68f45f4bd75561c673a9bcc970e4d5d842edefa3b37cb7a'
OLD_LAUNCH = '7e10894646da64ec5d0b1528a85d89bd50c4e796fbc61165ed3372738ebc1b54'
OLD_CLEANUP = '602fa9d0174d0358e280367401598564d130c8cc34061085dffdf54016ec0e9f'
H001_PREPARATION = 'e7189b1967fc3f8ad32d355fce7108a35257da51feeb9128aa03127df2f88a4f'
ORIGINAL_ROOT = Path('/var/home/jojo/bio-sim-proto')
MIN_FREE = 30 * 1024**3
WORKERS = 6
EXTRA_INPUTS = [c.ROOT / name for name in (
    'experiments/stringmol/recover_retirement.py',
    'tests/test_stringmol_recovery.py',
    'reports/sm_b002_artifact_recovery_addendum.md',
    'tools/run_sm_b002_recovery.nu',
)]


def canonical(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('ascii')


def pinned(path: Path, expected: str) -> dict[str, Any]:
    result = c.record(path)
    require(result['sha256'] == expected, f'pin mismatch: {path}')
    return result


def input_files() -> list[Path]:
    return list(dict.fromkeys([*w.IMPLEMENTATION, *w.PATCHES, c.ROOT / w.PROTOCOL_PATH, *EXTRA_INPUTS]))


def committed_inputs() -> dict[str, Any]:
    require(not c.command(['git', 'status', '--porcelain'], c.ROOT).strip(), 'clean source required')
    commit = c.command(['git', 'rev-parse', 'HEAD'], c.ROOT).decode().strip()
    records = {}
    for path in input_files():
        relative = str(path.relative_to(c.ROOT))
        require(c.command(['git', 'show', f'{commit}:{relative}'], c.ROOT) == path.read_bytes(), 'uncommitted source')
        records[relative] = c.record(path)
    return {'commit': commit, 'files': records}


def check_source(saved: dict[str, Any]) -> None:
    require(committed_inputs() == saved, 'source changed since preflight')


def prior_attempt(predecessor: Path, cleanup: Path) -> dict[str, Any]:
    pinned(predecessor / 'preparation.json', OLD_PREPARATION)
    pinned(predecessor / 'launch.json', OLD_LAUNCH)
    pinned(cleanup, OLD_CLEANUP)
    data: dict[str, Any] = c.read(predecessor / 'preparation.json')
    require(data['protocol'] == 'SM-B002' and data['protocol_pin'] == w.protocol_pin(), 'predecessor protocol')
    require([(r['condition'], r['seed']) for r in data['runs']] == ar.MATRIX, 'predecessor matrix')
    launch = c.read(predecessor / 'launch.json')
    require(launch['input_manifest'] == c.record(predecessor / 'preparation.json'), 'old launch linkage')
    require(c.read(predecessor / 'campaign.json') == {
        'input_manifest': c.record(predecessor / 'preparation.json'), 'workers': WORKERS,
        'launch_record': c.record(predecessor / 'launch.json')}, 'old campaign linkage')
    for r in data['runs']:
        config = predecessor / Path(r['config']).name
        require(config.read_bytes().hex() == r['bytes_hex'] and c.record(config) == {k: r[k] for k in ('size', 'sha256')}, 'old config seal')
    return data


def normalized_config(raw: str) -> str:
    lines = raw.splitlines(keepends=True)
    require(sum(line.startswith('SUBMAT ') for line in lines) == 1, 'exactly one SUBMAT required')
    return ''.join('SUBMAT STORAGE_PATH\n' if line.startswith('SUBMAT ') else line for line in lines)


def compare_inputs(old: dict[str, Any], new: dict[str, Any], raw: str) -> None:
    for key in ('condition', 'seed', 'expected_initial', 'initial_material', 'environment', 'route'):
        require(old[key] == new[key], f'changed scientific input: {key}')
    require(normalized_config(bytes.fromhex(old['bytes_hex']).decode('ascii')) == normalized_config(raw), 'changed config beyond SUBMAT')


def snapshot(roots: list[Path]) -> dict[str, Any]:
    """Hash scientific/build artifacts; Git bookkeeping and Python caches are not evidence."""
    records = {}
    for root in roots:
        for path in sorted(root.rglob('*')):
            relative = path.relative_to(root)
            if any(part in {'.git', '__pycache__', '.pytest_cache', '.mypy_cache'} for part in relative.parts):
                continue
            require(not path.is_symlink(), f'symlink in gate artifacts: {path}')
            if path.is_file():
                records[str(path)] = c.record(path)
    require(bool(records), 'empty gate snapshot')
    return records


def check_records(records: dict[str, Any]) -> None:
    require(bool(records), 'empty evidence')
    for path, expected in records.items():
        require(c.record(Path(path)) == expected, f'evidence changed: {path}')


def historical_config(actual: bytes, rendered: bytes, sealed_hex: str, matrix: Path) -> None:
    # render_config resolves paths through today's mounts; archived bytes retain
    # the original lexical pathname. Validate both separately, never rewrite it.
    require(actual.hex() == sealed_hex, 'historical sealed config')
    lines = actual.decode('ascii').splitlines()
    require([line for line in lines if line.startswith('SUBMAT ')] == [f'SUBMAT {matrix}'], 'historical matrix pathname')
    require(normalized_config(actual.decode('ascii')) == normalized_config(rendered.decode('ascii')), 'historical canonical config')


def historical_replay(archive: Path, old: dict[str, Any]) -> dict[str, Any]:
    """Recreate the pinned H001 analysis from all 30 archived raw runs, not old builds."""
    manifest = archive / 'prepared/preparation.json'
    pinned(manifest, H001_PREPARATION)
    pinned(archive / 'analysis/analysis.json', panel.SOURCE_SHA256)
    data = c.read(manifest)
    audit = old['unseen_audit']['inventory']
    for name in ('preparation.json', 'preparation.sha256.json', 'launch.json', 'campaign.json', 'campaign-results.json'):
        require(c.record(archive / 'prepared' / name) == audit[f'runs/sm_h001_work/prepared/{name}'], 'archived H001 audit pin')
    launch = c.read(archive / 'prepared/launch.json')
    require(launch['commit'] == panel.SOURCE_COMMIT and launch['input_manifest'] == c.record(manifest), 'historical launch')
    for path in [*hw.IMPLEMENTATION, *hw.PATCHES, c.ROOT / hw.PROTOCOL_PATH]:
        relative = path.relative_to(c.ROOT)
        original = str(ORIGINAL_ROOT / relative)
        raw = c.command(['git', 'show', f'{panel.SOURCE_COMMIT}:{relative}'], c.ROOT)
        require(raw == path.read_bytes(), 'historical source differs from pinned implementation')
        require(launch['committed_files'][original] == {**c.record(path), 'bytes_hex': raw.hex()}, 'historical committed bytes')
    receipts = c.read(archive / 'prepared/campaign-results.json')
    require([(r['condition'], r['seed']) for r in data['runs']] == ah.MATRIX and len(receipts) == len(ah.MATRIX), 'historical complete matrix')
    results = []
    source = Path(data['build']['builds']['observer']['source'])
    for r, receipt in zip(data['runs'], receipts, strict=True):
        expected = lw.expected_initial(r['condition'])
        require(r['expected_initial'] == expected, 'historical canonical inoculum')
        config = archive / 'prepared' / Path(r['config']).name
        raw = render_config(StringmolControlConfig('host-only' if r['condition'] == 'host' else 'inert', r['seed'], 0, 0), source / 'config/ALXII.mtx').encode()
        historical_config(config.read_bytes(), raw, r['bytes_hex'], source / 'config/ALXII.mtx')
        directory = archive / 'prepared/runs' / r['condition'] / str(r['seed'])
        verify_receipt(r, receipt, directory, c.record(manifest))
        summary = ah.analyze_run(directory, expected, exit_status=receipt['exit_status'])
        require(set(receipt['files']) == ad.output_names(summary['end_timestep']), 'historical output names')
        results.append({'condition': r['condition'], 'seed': r['seed'], **summary})
        print(f"H001 replay {len(results)}/30: {r['condition']} {r['seed']}", flush=True)
    digest = c.digest(canonical(ah.outcomes(results, [])))
    require(digest == panel.SOURCE_SHA256, 'historical independent replay differs from committed analysis')
    return {'runs': len(results), 'analysis_sha256': digest, 'manifest': c.record(manifest), 'scope': 'raw empirical replay; deleted historical build artifacts not reconstructed'}


def mutation_controls(build: dict[str, Any], root: Path) -> dict[str, Any]:
    mutation_build = Path(c.read(Path(build['inherited']))['inherited'])
    data = mw.verify_build(mutation_build)
    source = Path(data['builds']['observer']['source'])
    root.mkdir(parents=True, exist_ok=False)
    results = {}
    for arm in am.ARMS:
        r = mw.run_input(source, root, 202620999, arm)
        config = Path(r['config'])
        config.write_text(mw.custom_config(r, source), encoding='ascii')
        config.chmod(0o444)
        mw.parse_config(config.read_text(), r, source)
        first = c.execute(Path(r['command'][0]), config, Path(r['directory']), r['environment'])
        repeat = c.execute(Path(r['command'][0]), config, root / f'repeat-{arm}', r['environment'])
        c.parity(first, repeat)
        summary = am.analyze_run(Path(r['directory']), r['expected_initial'], exit_status=first['exit_status'])
        require(set(first['files']) == ad.output_names(summary['end_timestep']), 'mutation control output set')
        results[arm] = {'input': r, 'first': first, 'repeat': repeat, 'summary': summary}
    return {'rng_semantics': mw.rng_semantics(source), 'arms': results, 'build': c.record(mutation_build)}


def verify_receipt(r: dict[str, Any], receipt: dict[str, Any], directory: Path, manifest_record: dict[str, Any]) -> None:
    require(receipt == c.read(directory.with_suffix('.inventory.json')), 'run receipt mismatch')
    require(receipt['condition'] == r['condition'] and receipt['seed'] == r['seed'], 'run identity mismatch')
    require(receipt['input_manifest'] == manifest_record, 'manifest mismatch')
    require(receipt['files'] == c.inventory(directory), 'raw inventory mismatch')


def preflight(args: argparse.Namespace) -> Path:
    root: Path = args.root
    root.mkdir(parents=True, exist_ok=False)
    print('Checking committed source and prior artifact failure', flush=True)
    source = committed_inputs()
    old = prior_attempt(args.predecessor, args.cleanup)
    print('Replaying all 30 archived H001 runs against the pinned analysis', flush=True)
    historical = historical_replay(args.h001, old)
    print('Verifying rebuilt native, focused and inherited scheduling gates', flush=True)
    build = w.verify_build(args.build)
    w.verify_focused_gate(args.focused, args.build)
    bw.verify_gate(args.scheduling, Path(build['inherited']))
    print('Running both canonical mutation controls and deterministic repeats', flush=True)
    controls = mutation_controls(build, root / 'mutation-controls')
    print('Snapshotting verified evidence', flush=True)
    lineage_build = bw.foundation_builds(c.read(Path(build['inherited'])))['lineage']
    artifacts = snapshot([args.build.parent, lineage_build.parent,
                          args.focused.parent, args.scheduling.parent, root / 'mutation-controls'])
    records = {str(args.predecessor / name): c.record(args.predecessor / name)
               for name in ('preparation.json', 'launch.json', 'campaign.json')}
    records[str(args.cleanup)] = c.record(args.cleanup)
    result = {'protocol': PROTOCOL, 'source': source, 'build_path': str(args.build), 'build_record': c.record(args.build),
              'focused': c.record(args.focused), 'scheduling': c.record(args.scheduling), 'historical': historical,
              'mutation': controls, 'artifacts': artifacts, 'predecessor': str(args.predecessor),
              'cleanup': str(args.cleanup), 'predecessor_records': records, 'passed': True}
    path = root / 'gates.json'
    c.seal(path, result)
    check_source(source)
    return path


def prepare(gates: Path, root: Path) -> Path:
    gate = c.read(gates)
    require(gate['protocol'] == PROTOCOL and gate['passed'] is True, 'recovery gates')
    check_source(gate['source'])
    check_records(gate['artifacts'])
    check_records(gate['predecessor_records'])
    old = prior_attempt(Path(gate['predecessor']), Path(gate['cleanup']))
    root.mkdir(parents=True, exist_ok=False)
    source = Path(c.read(Path(gate['build_path']))['builds']['observer']['source'])
    runs = []
    for previous, (arm, seed) in zip(old['runs'], ar.MATRIX, strict=True):
        r = w.run_input(source, root, seed, arm)
        raw = w.custom_config(r, source)
        compare_inputs(previous, r, raw)
        w.parse_config(raw, r, source)
        config = Path(r['config'])
        config.write_text(raw, encoding='ascii'); config.chmod(0o444)
        runs.append({**r, **c.record(config), 'bytes_hex': raw.encode().hex()})
    path = root / 'preparation.json'
    c.seal(path, {'protocol': PROTOCOL, 'recovery_kind': 'unchanged whole matrix after documented artifact failure; not unseen seeds',
                 'source': gate['source'], 'gates_path': str(gates), 'gates_record': c.record(gates),
                 'protocol_pin': w.protocol_pin(), 'workers': WORKERS, 'runs': runs})
    c.seal(root / 'preparation.sha256.json', c.record(path))
    verify_preparation(path)
    return path


def verify_preparation(path: Path) -> dict[str, Any]:
    require(not path.is_symlink() and not path.stat().st_mode & 0o222, 'immutable recovery preparation')
    digest_path = path.with_name('preparation.sha256.json')
    require(not digest_path.is_symlink() and not digest_path.stat().st_mode & 0o222, 'immutable preparation digest')
    require(c.record(path) == c.read(digest_path), 'preparation digest')
    data: dict[str, Any] = c.read(path)
    require(path.read_bytes() == canonical(data), 'canonical preparation')
    require(data['protocol'] == PROTOCOL and data['protocol_pin'] == w.protocol_pin() and data['workers'] == WORKERS, 'recovery protocol')
    check_source(data['source'])
    gates = Path(data['gates_path'])
    require(not gates.stat().st_mode & 0o222 and c.record(gates) == data['gates_record'], 'gate seal changed')
    gate = c.read(gates)
    require(gate['passed'] is True and gate['source'] == data['source'], 'gate source changed')
    check_records(gate['artifacts']); check_records(gate['predecessor_records'])
    old = prior_attempt(Path(gate['predecessor']), Path(gate['cleanup']))
    require([(r['condition'], r['seed']) for r in data['runs']] == ar.MATRIX, 'whole recovery matrix')
    source = Path(c.read(Path(gate['build_path']))['builds']['observer']['source'])
    for previous, r in zip(old['runs'], data['runs'], strict=True):
        expected = w.run_input(source, path.parent, r['seed'], r['condition'])
        config = Path(expected['config'])
        raw = w.custom_config(expected, source)
        require(not config.is_symlink() and not config.stat().st_mode & 0o222 and config.read_text() == raw, 'immutable input')
        require(r == {**expected, **c.record(config), 'bytes_hex': raw.encode().hex()}, 'input identity')
        compare_inputs(previous, expected, raw)
    return data


def execute_one(r: dict[str, Any], manifest_record: dict[str, Any]) -> dict[str, Any]:
    directory = Path(r['directory'])
    try:
        require(shutil.disk_usage(directory.parent.parent.parent).free >= 2 * 1024**3, 'emergency disk floor')
        result = c.execute(Path(r['command'][0]), Path(r['config']), directory, r['environment'])
    except (OSError, ValueError) as exc:
        result = {'exit_status': f'runner-error: {exc}', 'files': {}, 'error': str(exc)}
    result.update(condition=r['condition'], seed=r['seed'], input_manifest=manifest_record)
    directory.parent.mkdir(parents=True, exist_ok=True)
    c.seal(directory.with_suffix('.inventory.json'), result)
    print(f"Execution receipt: {r['condition']} {r['seed']} exit={result['exit_status']}", flush=True)
    return result


def run_matrix(path: Path) -> None:
    data = verify_preparation(path)
    require(not any((path.parent / name).exists() for name in ('runs', 'launch.json', 'campaign-results.json')), 'no resume or selective retry')
    require(shutil.disk_usage(path.parent).free >= MIN_FREE, 'insufficient launch disk headroom')
    observation = w.observe_remote(w.remote_target(), data['source']['commit'])
    launch = {'protocol': PROTOCOL, 'input_manifest': c.record(path), 'source': data['source'],
              'remote': observation, 'started': datetime.now(timezone.utc).isoformat(),
              'recovery_kind': data['recovery_kind'], 'workers': WORKERS}
    c.seal(path.parent / 'launch.json', launch)
    # Directories exist for the disk check; no run directory is precreated.
    (path.parent / 'runs').mkdir()
    for arm in ar.ARMS:
        (path.parent / 'runs' / arm).mkdir()
    manifest_record = c.record(path)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(lambda r: execute_one(r, manifest_record), data['runs']))
    c.seal(path.parent / 'campaign-results.json', results)


def analyze(path: Path) -> dict[str, Any]:
    data = verify_preparation(path)
    launch_path = path.parent / 'launch.json'
    require(not launch_path.is_symlink() and not launch_path.stat().st_mode & 0o222, 'immutable launch')
    launch = c.read(launch_path)
    require(launch['protocol'] == PROTOCOL and launch['input_manifest'] == c.record(path) and launch['source'] == data['source'] and launch['workers'] == WORKERS, 'launch linkage')
    remote = launch['remote']
    target = w.remote_target()
    raw = f"{data['source']['commit']}\trefs/heads/main\n".encode()
    require(remote['observed_revision'] == data['source']['commit'] and bytes.fromhex(remote['stdout_hex']) == raw and remote['stdout_sha256'] == c.digest(raw), 'launch origin evidence')
    require(all(remote[k] == value for k, value in target.items()) and remote['command'] == ['git', 'ls-remote', '--exit-code', '--refs', target['url'], target['ref']] and remote['environment'] == c.ENV, 'launch remote target/command')
    receipts = c.read(path.parent / 'campaign-results.json')
    require(len(receipts) == len(data['runs']) == 80, 'complete recovery receipt matrix')
    results, failures = [], []
    for r, receipt in zip(data['runs'], receipts, strict=True):
        try:
            directory = Path(r['directory'])
            verify_receipt(r, receipt, directory, c.record(path))
            summary = ar.analyze_run(directory, r['expected_initial'], policy=r['condition'], exit_status=receipt['exit_status'])
            require(set(receipt['files']) == ar.output_names(summary['end_timestep']), 'scientific output set')
            results.append({'condition': r['condition'], 'seed': r['seed'], **summary})
        except (ValueError, OSError, KeyError, TypeError, csv.Error, subprocess.CalledProcessError) as exc:
            failures.append({'condition': r['condition'], 'seed': r['seed'], 'error': str(exc)})
        print(f'Replay {len(results) + len(failures)}/80; integrity failures so far: {len(failures)}', flush=True)
    return ar.outcomes(results, failures)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'prepare', 'run', 'analyze'))
    for name in ('root', 'build', 'focused', 'scheduling', 'predecessor', 'cleanup', 'h001', 'gates', 'manifest', 'output'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    if args.action == 'preflight':
        required = ('root', 'build', 'focused', 'scheduling', 'predecessor', 'cleanup', 'h001')
        if any(getattr(args, name) is None for name in required): parser.error('missing preflight paths')
        print(preflight(args))
    elif args.action == 'prepare' and args.gates and args.root:
        print(prepare(args.gates, args.root))
    elif args.action == 'run' and args.manifest:
        run_matrix(args.manifest)
    elif args.action == 'analyze' and args.manifest and args.output:
        c.seal(args.output, analyze(args.manifest))
        print(args.output)
    else:
        parser.error('missing required paths')


if __name__ == '__main__':
    main()
