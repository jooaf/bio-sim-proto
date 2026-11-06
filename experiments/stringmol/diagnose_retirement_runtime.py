"""Development-only storage/concurrency diagnosis; never executes assay seeds."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Any

from experiments.stringmol import conservation_workflow as c, retirement_workflow as w
from experiments.stringmol.analyze_lineage import require

SEED = 202620999
ARM = 'IMMEDIATE_RETAIN'
LIMIT = 1200
IMAGE = Path('/tmp/sm')
STORE = Path('/run/media/jojo/Elements/bio-sim-results')
PROFILES = (('posix-serial', 1, 'posix'), ('exfat-serial', 1, 'exfat'),
            ('exfat-six', 6, 'exfat'), ('posix-six', 6, 'posix'))
TIME_FORMAT = '{"wall_seconds":%e,"user_seconds":%U,"system_seconds":%S,"max_rss_kib":%M,"filesystem_inputs":%I,"filesystem_outputs":%O,"exit_code":%x}'


def resources(pid: int) -> dict[str, Any]:
    result: dict[str, Any] = {'pid': pid}
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        rate = os.sysconf('SC_CLK_TCK')
        result.update(state=fields[0], cpu_seconds=(int(fields[11]) + int(fields[12])) / rate)
        result['io'] = {key: int(value) for key, value in
                        (line.split(':', 1) for line in Path(f'/proc/{pid}/io').read_text().splitlines())}
    except (FileNotFoundError, ProcessLookupError):
        result['exited'] = True
    return result


def qualify(results: list[dict[str, Any]], threshold: float | None = None) -> bool:
    return bool(results) and all(r['exit_status'] == 0 and r['parity'] is True and
                                (threshold is None or r['wall_seconds'] <= threshold) for r in results)


def probe(index: int, root: Path, raw_root: Path, binary: Path, config: Path,
          expected: dict[str, Any], deadline: float = LIMIT) -> dict[str, Any]:
    directory = raw_root / str(index)
    directory.mkdir(parents=True, exist_ok=False)
    metrics = root / f'{index}.time.json'
    command = ['/usr/bin/time', '-q', '-f', TIME_FORMAT, '-o', str(metrics), str(binary), '30', str(config)]
    started = time.monotonic()
    with (directory / 'stdout.txt').open('xb') as out, (directory / 'stderr.txt').open('xb') as err, (root / f'{index}.samples.jsonl').open('x') as samples:
        process = subprocess.Popen(command, cwd=directory, env=w.environment(ARM), stdout=out, stderr=err, start_new_session=True)
        status: int | str
        while True:
            code = process.poll()
            if code is not None:
                status = code
                break
            elapsed = time.monotonic() - started
            try:
                children = Path(f'/proc/{process.pid}/task/{process.pid}/children').read_text().split()
            except FileNotFoundError:
                children = []
            samples.write(json.dumps({'elapsed': elapsed, 'children': [resources(int(pid)) for pid in children]}) + '\n')
            samples.flush()
            if elapsed >= deadline:
                # Kill time AND native child, not just the timing wrapper.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
                status = 'timeout'
                break
            time.sleep(2)
    elapsed = time.monotonic() - started
    inventory = c.inventory(directory)
    result = {'index': index, 'directory': str(directory), 'exit_status': status,
              'wall_seconds': elapsed, 'parity': status == 0 and inventory == expected,
              'files': inventory, 'command': command, 'environment': w.environment(ARM)}
    if metrics.exists() and metrics.stat().st_size:
        result['timing'] = json.loads(metrics.read_text())
    c.seal(root / f'{index}.receipt.json', result)
    print(f'{root.name}/{index}: exit={status}, elapsed={elapsed:.1f}s, parity={result["parity"]}', flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default='timeout-diagnostics-v1')
    args = parser.parse_args()
    require(args.name and Path(args.name).name == args.name and args.name not in {'.', '..'}, 'simple diagnostic name required')
    root = IMAGE / args.name
    portable = STORE / args.name
    require(not root.exists() and not portable.exists(), 'do not overwrite diagnostic attempts')
    mounted = json.loads(subprocess.check_output(['findmnt', '--json', '--target', str(IMAGE), '--output', 'TARGET,SOURCE,FSTYPE']))['filesystems'][0]
    require(mounted['target'] == str(IMAGE) and mounted['source'] == str(STORE / 'stringmol-posix.ext4') and mounted['fstype'] in {'fuse.ext4', 'fuse.fuse2fs'}, 'expected external POSIX image')
    root.mkdir(); portable.mkdir()
    (portable / 'pid').write_text(str(os.getpid()))
    gates_path = IMAGE / 'r1/preflight/gates.json'
    prepared = c.read(IMAGE / 'r1/prepared/preparation.json')
    require(c.record(gates_path) == prepared['gates_record'], 'R1 gate seal')
    require(w.protocol_pin() == prepared['protocol_pin'], 'unchanged scientific protocol')
    gates = c.read(gates_path)
    focused_path = IMAGE / 'f-vendor-restored/focused.json'
    require(c.record(focused_path) == gates['focused'], 'focused development seal')
    focused = c.read(focused_path)
    binary = IMAGE / 'b/observer/release/stringmol'
    config = IMAGE / 'f-vendor-restored/development.conf'
    require(c.record(binary) == gates['artifacts'][str(binary)] and c.record(config) == focused['config'], 'native/config bytes changed')
    expected = focused['runs'][ARM]['files']
    require(c.inventory(IMAGE / 'f-vendor-restored' / ARM) == expected, 'reference development output changed')
    sample = w.run_input(binary.parent.parent, root, SEED, ARM)
    w.parse_config(config.read_text(), sample, binary.parent.parent)
    inputs = {str(p.relative_to(c.ROOT)): c.record(p) for p in w.IMPLEMENTATION}
    require(all(gates['source']['files'][name] == value for name, value in inputs.items()), 'scientific source changed')
    plan = {'development_seed': SEED, 'arm': ARM, 'deadline_seconds': LIMIT, 'profiles': PROFILES,
            'binary': c.record(binary), 'config': c.record(config), 'source': inputs,
            'driver': c.record(Path(__file__)), 'commit': c.command(['git', 'rev-parse', 'HEAD'], c.ROOT).decode().strip()}
    c.seal(root / 'plan.json', plan)
    results: dict[str, list[dict[str, Any]]] = {}
    profiles = list(PROFILES)
    for name, workers, storage in profiles:
        path = root / name
        path.mkdir()
        raw = (root if storage == 'posix' else portable) / 'raw' / name
        (portable / 'status.json').write_text(json.dumps({'profile': name, 'workers': workers, 'storage': storage}))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            result = list(pool.map(lambda index: probe(index, path, raw, binary, config, expected), range(workers)))
        results[name] = result
        require(not any(item['exit_status'] == 0 and not item['parity'] for item in result), 'completed probe differs from frozen development bytes')
    if qualify(results['exfat-six'], 300):
        workers = 6
    else:
        path = root / 'exfat-two'; path.mkdir()
        (portable / 'status.json').write_text(json.dumps({'profile': 'exfat-two', 'workers': 2, 'storage': 'exfat'}))
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(lambda index: probe(index, path, portable / 'raw/exfat-two', binary, config, expected), range(2)))
        results['exfat-two'] = result
        require(qualify(result), 'two-worker direct-storage repair did not qualify; continue diagnosis')
        workers = 2
    require(qualify(results['exfat-serial']), 'direct-storage serial reference did not qualify')
    require(c.record(Path(__file__)) == plan['driver'], 'diagnostic code changed during execution')
    require({str(p.relative_to(c.ROOT)): c.record(p) for p in w.IMPLEMENTATION} == inputs, 'scientific code changed during diagnostic')
    report = {'qualified_workers': workers, 'qualified_raw_storage': 'direct-exfat', 'development_seed': SEED,
              'scope': 'fixed-order engineering screen, not biological replicates or randomized performance inference',
              'profiles': results, 'plan_record': c.record(root / 'plan.json')}
    c.seal(root / 'report.json', report)
    # Readable summary and all detailed metrics remain on Elements, outside native output directories.
    summary = {name: [{key: item.get(key) for key in ('index', 'exit_status', 'wall_seconds', 'parity', 'timing')} for item in group] for name, group in results.items()}
    (portable / 'summary.json').write_text(json.dumps({'qualified_workers': workers, 'profiles': summary}, indent=2) + '\n')
    (portable / 'COMPLETE.json').write_text(json.dumps({'qualified_workers': workers, 'report': str(root / 'report.json'), 'report_record': c.record(root / 'report.json')}, indent=2) + '\n')
    print(f'Qualified {workers} workers with direct exFAT raw output; no assay inputs executed.', flush=True)


if __name__ == '__main__':
    main()
