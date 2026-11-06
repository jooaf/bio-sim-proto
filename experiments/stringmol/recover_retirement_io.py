"""SM-B002 R2/R3: direct raw I/O, sealed controls, bounded operational recovery."""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any

from experiments.stringmol import (
    analyze_retirement as ar, conservation_workflow as c,
    diagnose_retirement_runtime as diagnostic, recover_retirement as prior,
    retirement_workflow as w, perturbation_panel as panel,
)
from experiments.stringmol.analyze_lineage import require

IMAGE = Path('/tmp/sm')
STORE = Path('/run/media/jojo/Elements/bio-sim-results')
R1_PINS = {
    'prepared/preparation.json': 'c0d67c9931fd457844b7ce7cb9f4f8552e4597c8150ff56f41c6447a073a3ed4',
    'prepared/campaign-results.json': 'd2a0762f19ae79fb3b46abe0c6996632e348d5f0173c84b5994073111e4b86be',
    'analysis.json': '4abd2254b4c9d14dd7d08657addb5a984412b9ec68ba751dda386aab9f586868',
    'analysis-repeat.json': '4abd2254b4c9d14dd7d08657addb5a984412b9ec68ba751dda386aab9f586868',
}
EXTRA = ['AGENTS.md', 'experiments/stringmol/recover_retirement_io.py',
         'experiments/stringmol/diagnose_retirement_runtime.py',
         'tests/test_stringmol_runtime_diagnostics.py', 'tests/test_stringmol_io_recovery.py',
         'reports/sm_b002_timeout_diagnostic_plan.md', 'reports/sm_b002_direct_io_recovery_addendum.md',
         'tools/run_sm_b002_io_recovery.nu']


class Failure(str, Enum):
    TIMEOUT = 'process_timeout'
    PROCESS = 'process_failure'
    INTEGRITY = 'integrity'


@dataclass(frozen=True)
class Layout:
    attempt: int
    control: Path
    portable: Path

    @classmethod
    def create(cls, attempt: int) -> Layout:
        require(attempt in (2, 3), 'bounded recovery ladder only')
        return cls(attempt, IMAGE / f'r{attempt}', STORE / f'sm-b002-r{attempt}')

    @property
    def prepared(self) -> Path:
        return self.control / 'prepared'

    def raw(self, arm: str, seed: int) -> Path:
        return self.portable / 'runs' / arm / str(seed)

    def receipt(self, arm: str, seed: int) -> Path:
        return self.prepared / 'receipts' / arm / f'{seed}.json'


def policy(attempt: int, qualified: int) -> tuple[int, int]:
    require(attempt in (2, 3) and qualified in (2, 6), 'recovery policy')
    return (qualified, 600) if attempt == 2 else (1, 3600)


def mounts() -> None:
    for path, target, kinds in ((STORE, str(STORE.parent), {'exfat'}), (IMAGE, str(IMAGE), {'fuse.ext4', 'fuse.fuse2fs'})):
        row = json.loads(subprocess.check_output(['findmnt', '--json', '--target', str(path), '--output', 'TARGET,SOURCE,FSTYPE,OPTIONS']))['filesystems'][0]
        require(row['target'] == target and row['fstype'] in kinds and 'rw' in row['options'].split(','), 'required writable external filesystem missing')
        if path == IMAGE:
            require(row['source'] == str(STORE / 'stringmol-posix.ext4'), 'wrong control image')


def source() -> dict[str, Any]:
    require(not c.command(['git', 'status', '--porcelain'], c.ROOT).strip(), 'clean committed source required')
    commit = c.command(['git', 'rev-parse', 'HEAD'], c.ROOT).decode().strip()
    files = {}
    for path in dict.fromkeys([*prior.input_files(), *(c.ROOT / name for name in EXTRA)]):
        relative = str(path.relative_to(c.ROOT))
        require(c.command(['git', 'show', f'{commit}:{relative}'], c.ROOT) == path.read_bytes(), 'uncommitted driver/scientific bytes')
        files[relative] = c.record(path)
    return {'commit': commit, 'files': files}


def progress(layout: Layout, stage: str) -> None:
    message = {'stage': stage, 'at': datetime.now(timezone.utc).isoformat(), 'attempt': layout.attempt}
    (layout.portable / 'status.json').write_bytes(prior.canonical(message))
    print(json.dumps(message), flush=True)


def qualified_workers(report: dict[str, Any]) -> int:
    profiles = report['profiles']
    expected = {name: workers for name, workers, _ in diagnostic.PROFILES}
    require(set(profiles) in (set(expected), set(expected) | {'exfat-two'}), 'complete diagnostic profile set')
    for name, workers in {**expected, **({'exfat-two': 2} if 'exfat-two' in profiles else {})}.items():
        require([row['index'] for row in profiles[name]] == list(range(workers)), 'complete diagnostic worker set')
        require(not any(row['exit_status'] == 0 and row['parity'] is not True for row in profiles[name]), 'changed successful diagnostic output')
    qualified = 6 if diagnostic.qualify(profiles['exfat-six'], 300) else 2
    require(diagnostic.qualify(profiles['exfat-serial']), 'serial reference failed')
    if qualified == 2:
        require('exfat-two' in profiles and diagnostic.qualify(profiles['exfat-two']), 'two-worker qualification missing')
    require(qualified == report['qualified_workers'], 'worker qualification mismatch')
    return qualified


def diagnostic_evidence() -> tuple[int, dict[str, Any]]:
    marker = c.read(STORE / 'timeout-diagnostics-v1/COMPLETE.json')
    report_path = IMAGE / 'timeout-diagnostics-v1/report.json'
    require(marker['report'] == str(report_path) and c.record(report_path) == marker['report_record'], 'diagnostic report seal')
    report = c.read(report_path)
    require(c.record(report_path.parent / 'plan.json') == report['plan_record'], 'diagnostic plan seal')
    plan = c.read(report_path.parent / 'plan.json')
    require(plan['development_seed'] == diagnostic.SEED and plan['driver'] == c.record(Path(diagnostic.__file__)) and plan['profiles'] == [list(row) for row in diagnostic.PROFILES] and plan['deadline_seconds'] == diagnostic.LIMIT, 'diagnostic identity/code')
    for name, group in report['profiles'].items():
        for item in group:
            require(item == c.read(report_path.parent / name / f"{item['index']}.receipt.json"), 'diagnostic receipt changed')
            require(item['files'] == c.inventory(Path(item['directory'])), 'diagnostic output changed')
    qualified = qualified_workers(report)
    require(qualified == marker['qualified_workers'], 'worker qualification marker mismatch')
    return qualified, {str(report_path): c.record(report_path), str(report_path.parent / 'plan.json'): c.record(report_path.parent / 'plan.json')}


def r1_evidence() -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    for relative, digest in R1_PINS.items():
        prior.pinned(IMAGE / 'r1' / relative, digest)
    data: dict[str, Any] = c.read(IMAGE / 'r1/prepared/preparation.json')
    require([(entry['condition'], entry['seed']) for entry in data['runs']] == ar.MATRIX, 'R1 matrix')
    gate_path = Path(data['gates_path'])
    require(c.record(gate_path) == data['gates_record'], 'R1 gate proof changed')
    gate = c.read(gate_path)
    require(gate['passed'] is True and gate['historical']['analysis_sha256'] == panel.SOURCE_SHA256, 'R1 live/historical gates')
    for relative, record in gate['source']['files'].items():
        require(c.record(c.ROOT / relative) == record, 'original scientific/recovery source changed')
    prior.check_records(gate['artifacts'])
    require(data['protocol_pin'] == w.protocol_pin(), 'unchanged biological protocol')
    receipts = c.read(IMAGE / 'r1/prepared/campaign-results.json')
    require([(entry['condition'], entry['seed']) for entry in receipts] == ar.MATRIX, 'R1 complete receipts')
    result = c.read(IMAGE / 'r1/analysis.json')
    timeouts = {(entry['condition'], entry['seed']) for entry in receipts if entry['exit_status'] == 'timeout'}
    require(result['branch'] == 1 and result['integrity'] is False and len(timeouts) == 38 and
            {(entry['condition'], entry['seed']) for entry in result['failures']} == timeouts and
            all(entry['exit_status'] in (0, 'timeout') for entry in receipts), 'documented R1 timeout-only failure required')
    known = {f"{entry['condition']}:{entry['seed']}": entry['files'] for entry in receipts if entry['exit_status'] == 0}
    assets = {str(gate_path): c.record(gate_path), str(IMAGE / 'r1/prepared/preparation.json'): c.record(IMAGE / 'r1/prepared/preparation.json')}
    for name in ('b/observer/release/stringmol', 'b/observer/config/ALXII.mtx', 'f-vendor-restored/focused.json', 'f-vendor-restored/development.conf'):
        assets[str(IMAGE / name)] = gate['artifacts'][str(IMAGE / name)]
    return data, known, assets, gate


def execute_native(entry: dict[str, Any], timeout: int) -> dict[str, Any]:
    directory = Path(entry['directory'])
    mounts()
    require(shutil.disk_usage(STORE).free >= 2 * 1024**3 and shutil.disk_usage(IMAGE).free >= 1024**3, 'external emergency space floor')
    directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    with (directory / 'stdout.txt').open('xb') as out, (directory / 'stderr.txt').open('xb') as err:
        try:
            process = subprocess.run(entry['command'], cwd=directory, env=entry['environment'], stdout=out, stderr=err, timeout=timeout, check=False)
            status: int | str = process.returncode
        except subprocess.TimeoutExpired:
            status = 'timeout'
        except OSError as exc:
            status = f'launch failure: {exc}'
    return {'exit_status': status, 'files': c.inventory(directory), 'wall_seconds': time.monotonic() - started, 'timeout_seconds': timeout}


def qualify_arms(layout: Layout, workers: int, timeout: int, focused: dict[str, Any]) -> dict[str, Any]:
    binary = IMAGE / 'b/observer/release/stringmol'
    config = IMAGE / 'f-vendor-restored/development.conf'
    entries = []
    for arm in ar.ARMS:
        entry = w.run_input(binary.parent.parent, layout.control, diagnostic.SEED, arm)
        entry.update(config=str(config), command=[str(binary), '30', str(config)], directory=str(layout.portable / 'development' / arm))
        w.parse_config(config.read_text(), entry, binary.parent.parent)
        entries.append(entry)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda entry: execute_native(entry, timeout), entries))
    assets = {}
    for entry, result in zip(entries, results, strict=True):
        c.seal(layout.control / f"development-{entry['condition']}.json", result)
        require(result['exit_status'] == 0 and result['files'] == focused['runs'][entry['condition']]['files'], 'all-arm direct-I/O parity required')
        summary = ar.analyze_run(Path(entry['directory']), entry['expected_initial'], policy=entry['condition'])
        require(summary['zero_residual'] is True and summary['boundary_errors'] == summary['fatal_enforcement_errors'] == 0, 'all-arm development replay')
        c.seal(layout.control / f"development-{entry['condition']}-replay.json", {'sha256': c.digest(prior.canonical(summary)), 'zero_residual': True})
        assets.update({str(Path(entry['directory']) / name): record for name, record in result['files'].items()})
    return assets


def prepare(layout: Layout, workers: int, timeout: int, old: dict[str, Any], known: dict[str, Any], assets: dict[str, Any], origin: dict[str, Any], parent: dict[str, Any]) -> Path:
    saved_source = source()
    require(shutil.disk_usage(STORE).free >= 100 * 1024**3 and shutil.disk_usage(IMAGE).free >= 10 * 1024**3, 'prelaunch disk headroom')
    progress(layout, 'qualifying all four arms on direct storage')
    assets = {**assets, **qualify_arms(layout, workers, timeout, c.read(IMAGE / 'f-vendor-restored/focused.json'))}
    c.seal(layout.control / 'gates.json', {'assets': assets, 'source': saved_source, 'parent': parent, 'diagnostic': origin, 'passed': True})
    layout.prepared.mkdir()
    runs = []
    for previous, (arm, seed) in zip(old['runs'], ar.MATRIX, strict=True):
        entry = w.run_input(IMAGE / 'b/observer', layout.prepared, seed, arm)
        entry['directory'] = str(layout.raw(arm, seed))
        raw = w.custom_config(entry, IMAGE / 'b/observer')
        prior.compare_inputs(previous, entry, raw)
        w.parse_config(raw, entry, IMAGE / 'b/observer')
        config = Path(entry['config']); config.write_text(raw, encoding='ascii'); config.chmod(0o444)
        runs.append({**entry, **c.record(config), 'bytes_hex': raw.encode().hex()})
    path = layout.prepared / 'preparation.json'
    c.seal(path, {'protocol': f'SM-B002-R{layout.attempt}', 'attempt': layout.attempt, 'workers': workers, 'timeout_seconds': timeout,
                 'source': saved_source, 'control': str(layout.control), 'portable': str(layout.portable), 'runs': runs,
                 'known_completed': known, 'gates_record': c.record(layout.control / 'gates.json'), 'parent': parent,
                 'protocol_digest': c.digest(prior.canonical(w.protocol_pin()))})
    c.seal(path.with_name('preparation.sha256.json'), c.record(path))
    return path


def verify(layout: Layout) -> dict[str, Any]:
    mounts()
    path = layout.prepared / 'preparation.json'
    require(not path.is_symlink() and not path.stat().st_mode & 0o222 and c.record(path) == c.read(path.with_name('preparation.sha256.json')), 'immutable preparation seal')
    data: dict[str, Any] = c.read(path)
    require(data['source'] == source() and data['attempt'] == layout.attempt and data['protocol'] == f'SM-B002-R{layout.attempt}', 'source/protocol identity')
    require(data['control'] == str(layout.control) and data['portable'] == str(layout.portable), 'storage identity')
    require((data['workers'], data['timeout_seconds']) == policy(layout.attempt, data['parent']['qualified_workers']), 'frozen operational policy')
    require(data['protocol_digest'] == c.digest(prior.canonical(w.protocol_pin())), 'biological protocol changed')
    gate = layout.control / 'gates.json'
    require(c.record(gate) == data['gates_record'] and c.read(gate)['passed'] is True, 'gate record')
    prior.check_records(c.read(gate)['assets'])
    old = c.read(IMAGE / 'r1/prepared/preparation.json')
    require([(entry['condition'], entry['seed']) for entry in data['runs']] == ar.MATRIX, 'complete unchanged matrix')
    for previous, entry in zip(old['runs'], data['runs'], strict=True):
        expected = w.run_input(IMAGE / 'b/observer', layout.prepared, entry['seed'], entry['condition'])
        expected['directory'] = str(layout.raw(entry['condition'], entry['seed']))
        config = Path(expected['config'])
        raw = w.custom_config(expected, IMAGE / 'b/observer')
        require(not config.is_symlink() and not config.stat().st_mode & 0o222 and config.read_text() == raw, 'immutable canonical config')
        require(entry == {**expected, **c.record(config), 'bytes_hex': raw.encode().hex()}, 'input identity')
        prior.compare_inputs(previous, expected, raw)
    return data


def execute_one(entry: dict[str, Any], layout: Layout, record: dict[str, Any], timeout: int) -> dict[str, Any]:
    try:
        result = execute_native(entry, timeout)
    except (OSError, ValueError) as exc:
        result = {'exit_status': f'runner error: {exc}', 'files': {}, 'error': str(exc), 'timeout_seconds': timeout}
    result.update(condition=entry['condition'], seed=entry['seed'], input_manifest=record)
    receipt = layout.receipt(entry['condition'], entry['seed']); receipt.parent.mkdir(parents=True, exist_ok=True)
    c.seal(receipt, result)
    print(f"R{layout.attempt} receipt {entry['condition']} {entry['seed']}: {result['exit_status']}", flush=True)
    return result


def run_matrix(layout: Layout) -> None:
    data = verify(layout)
    require(not any(path.exists() for path in (layout.portable / 'runs', layout.prepared / 'launch.json', layout.prepared / 'campaign-results.json')), 'no resume or selective retry')
    progress(layout, 'executing all 80 inputs')
    manifest_record = c.record(layout.prepared / 'preparation.json')
    remote = w.observe_remote(w.remote_target(), data['source']['commit'])
    c.seal(layout.prepared / 'launch.json', {'input_manifest': manifest_record, 'source': data['source'], 'remote': remote, 'workers': data['workers'], 'timeout_seconds': data['timeout_seconds']})
    with ThreadPoolExecutor(max_workers=data['workers']) as pool:
        results = list(pool.map(lambda entry: execute_one(entry, layout, manifest_record, data['timeout_seconds']), data['runs']))
    c.seal(layout.prepared / 'campaign-results.json', results)


def analyze_one(job: tuple[dict[str, Any], dict[str, Any], str, dict[str, Any], dict[str, Any] | None]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    entry, receipt, receipt_file, manifest_record, previous_files = job
    identity = {'condition': entry['condition'], 'seed': entry['seed']}
    try:
        sealed = Path(receipt_file)
        require(not sealed.is_symlink() and not sealed.stat().st_mode & 0o222 and receipt == c.read(sealed) and receipt['input_manifest'] == manifest_record, 'sealed run receipt')
        require(all(receipt[k] == value for k, value in identity.items()), 'run identity')
        require(receipt['files'] == c.inventory(Path(entry['directory'])), 'raw inventory')
        if receipt['exit_status'] != 0:
            kind = Failure.TIMEOUT if receipt['exit_status'] == 'timeout' else Failure.PROCESS
            return None, {**identity, 'category': kind.value, 'error': str(receipt['exit_status'])}
        if previous_files is not None:
            require(receipt['files'] == previous_files, 'completed output changed across operational recovery')
        summary = ar.analyze_run(Path(entry['directory']), entry['expected_initial'], policy=entry['condition'], exit_status=receipt['exit_status'])
        require(set(receipt['files']) == ar.output_names(summary['end_timestep']), 'scientific output set')
        return {**identity, **summary}, None
    except (OSError, ValueError, KeyError, TypeError, csv.Error, subprocess.CalledProcessError) as exc:
        return None, {**identity, 'category': Failure.INTEGRITY.value, 'error': str(exc)}


def analyze(layout: Layout, label: str) -> dict[str, Any]:
    data = verify(layout)
    manifest_record = c.record(layout.prepared / 'preparation.json')
    launch = c.read(layout.prepared / 'launch.json')
    require(launch['input_manifest'] == manifest_record and launch['source'] == data['source'] and launch['workers'] == data['workers'] and launch['timeout_seconds'] == data['timeout_seconds'], 'launch identity')
    remote = launch['remote']; target = w.remote_target()
    raw = f"{data['source']['commit']}\trefs/heads/main\n".encode()
    require(all(remote[k] == value for k, value in target.items()) and remote['observed_revision'] == data['source']['commit'] and bytes.fromhex(remote['stdout_hex']) == raw and remote['stdout_sha256'] == c.digest(raw), 'direct origin observation')
    require(remote['command'] == ['git', 'ls-remote', '--exit-code', '--refs', target['url'], target['ref']] and remote['environment'] == c.ENV, 'remote observation command')
    receipts = c.read(layout.prepared / 'campaign-results.json')
    require(len(receipts) == 80, 'complete receipt denominator')
    jobs = [(entry, receipt, str(layout.receipt(entry['condition'], entry['seed'])), manifest_record,
             data['known_completed'].get(f"{entry['condition']}:{entry['seed']}")) for entry, receipt in zip(data['runs'], receipts, strict=True)]
    try:
        with ProcessPoolExecutor(max_workers=2, max_tasks_per_child=1) as pool:
            rows = list(pool.map(analyze_one, jobs))
    except (BrokenProcessPool, OSError) as exc:
        # Analysis-only resource recovery: no experiment is rerun or omitted.
        (layout.control / f'{label}-parallel-resource-error.txt').write_text(str(exc))
        rows = [analyze_one(job) for job in jobs]
    results = [result for result, _ in rows if result is not None]
    failures = [failure for _, failure in rows if failure is not None]
    require(len(results) + len(failures) == 80, 'every input must be accounted for')
    require(data['source'] == source(), 'source changed during replay')
    return ar.outcomes(results, failures)


def timeout_only(result: dict[str, Any], receipts: list[dict[str, Any]]) -> bool:
    if result['integrity'] or result['branch'] != 1 or not result['failures']:
        return False
    identities = [(r['condition'], r['seed']) for r in receipts]
    if identities != ar.MATRIX or any(r['exit_status'] not in (0, 'timeout') for r in receipts):
        return False
    failed = {(r['condition'], r['seed']) for r in result['failures']}
    timed = {(r['condition'], r['seed']) for r in receipts if r['exit_status'] == 'timeout'}
    expected_verified = {f"{arm}:{seed}" for arm, seed in ar.MATRIX if (arm, seed) not in failed}
    return (failed == timed and len(result['failures']) == len(timed) and
            all(r.get('category') == Failure.TIMEOUT.value for r in result['failures']) and
            len(result['verified_ids']) == len(expected_verified) and set(result['verified_ids']) == expected_verified)


def export(layout: Layout, summary: dict[str, Any]) -> None:
    progress(layout, 'verified control export')
    c.seal(layout.control / 'decision.json', summary)
    (layout.control / 'REPORT.md').write_text(f"# SM-B002-R{layout.attempt}\n\nDecision: {summary['decision']}\nIntegrity: {summary['integrity']}\n\nAll 80 outcomes retained; biological duration is 5,000 ticks.\nRaw data: ../runs/. Control/provenance: this directory.\nFull and repeat analyses match byte-for-byte.\nNative binaries require platform-specific rebuilding on macOS.\nHistorical prelaunch evidence: ../../sm-b002-r1/prelaunch.tar.\n")
    c.command(['git', 'bundle', 'create', str(layout.control / 'source.bundle'), '--all'], c.ROOT)
    target = layout.portable / 'control'
    require(not target.exists(), 'no export overwrite')
    target.mkdir()
    subprocess.run(['rsync', '-rt', '--modify-window=2', str(layout.control) + '/', str(target) + '/'], check=True)
    result = subprocess.run(['rsync', '-rcn', '--delete', '--itemize-changes', str(layout.control) + '/', str(target) + '/'], check=True, capture_output=True)
    require(not result.stdout.strip(), 'portable export checksum mismatch')
    subprocess.run(['sync'], check=True)
    (layout.portable / 'COMPLETE.json').write_bytes(prior.canonical({'integrity': summary['integrity'], 'decision': summary['decision'], 'branch': summary['branch'], 'export_verified': True}))


def attempt(layout: Layout, qualified: int, old: dict[str, Any], known: dict[str, Any], assets: dict[str, Any], origin: dict[str, Any], parent: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    mounts()
    require(not layout.control.exists() and not layout.portable.exists(), 'fresh whole-matrix attempt required')
    layout.control.mkdir(); layout.portable.mkdir()
    workers, timeout = policy(layout.attempt, qualified)
    prepare(layout, workers, timeout, old, known, assets, origin, {**parent, 'qualified_workers': qualified})
    run_matrix(layout)
    progress(layout, 'independent ordered replay')
    result = analyze(layout, 'analysis')
    c.seal(layout.control / 'analysis.json', result)
    summary = {key: result[key] for key in ('branch', 'decision', 'integrity', 'arms', 'pairs', 'failures', 'run_denominator', 'arm_denominator', 'paired_denominator', 'admission_design_authorized', 'admission_execution_authorized')}
    summary['verified_ids'] = [f"{entry['condition']}:{entry['seed']}" for entry in result['runs']]
    del result
    progress(layout, 'repeat ordered replay')
    result = analyze(layout, 'analysis-repeat')
    c.seal(layout.control / 'analysis-repeat.json', result)
    del result
    require(c.record(layout.control / 'analysis.json') == c.record(layout.control / 'analysis-repeat.json'), 'repeat analysis differs')
    export(layout, summary)
    return summary, c.read(layout.prepared / 'campaign-results.json')


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    mounts()
    qualified, diagnostic_records = diagnostic_evidence()
    old, known, assets, _ = r1_evidence()
    first = Layout.create(2)
    result, receipts = attempt(first, qualified, old, known, {**assets, **diagnostic_records}, diagnostic_records, {'attempt': 'R1', 'pins': R1_PINS})
    if result['integrity']:
        print(f"Verified R2 scientific classification: {result['decision']}", flush=True)
        return
    if timeout_only(result, receipts):
        print('Only verified operational timeouts remain; automatically qualifying serial whole-matrix R3.', flush=True)
        known.update({f"{entry['condition']}:{entry['seed']}": entry['files'] for entry in receipts if entry['exit_status'] == 0})
        records = {str(first.control / name): c.record(first.control / name) for name in ('analysis.json', 'analysis-repeat.json', 'prepared/preparation.json', 'prepared/campaign-results.json')}
        result, _ = attempt(Layout.create(3), qualified, old, known, {**assets, **diagnostic_records, **records}, diagnostic_records, {'attempt': 'R2', 'records': records, 'reason': 'verified timeout-only integrity failure'})
        if result['integrity']:
            print(f"Verified R3 scientific classification: {result['decision']}", flush=True)
            return
    raise RuntimeError('Critical integrity defect after bounded operational recovery; evidence retained; investigate, never blindly or selectively retry')


if __name__ == '__main__':
    main()
