"""Prospective SM-XL001 complete recovery. No historical CLI is dispatched.

freeze writes only a proposal at a caller-selected qualification path. Launch is
separate and requires an independently supplied, exact parent approval. No resume.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
from typing import TypedDict, cast

from experiments.stringmol import locality_pilot as p
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.configure_control import HOST, StringmolControlConfig, inoculum, render_config
from experiments.stringmol.analyze_conservation import initial_material
from experiments.stringmol.locality_models import ReplayResult
from experiments.stringmol.locality_process import FileRecord, ProcessResult, execute

CONTROL = Path('/tmp/sm/xl2-c')
RAW = Path('/run/media/jojo/Elements/bio-sim-results/sm-xl001-recovery-v1')
EXPORT = Path('/run/media/jojo/Elements/bio-sim-results/verification/sm-xl001-recovery-v1')
ORIGIN = Path('/tmp/sm/xl-e')
OLD_RAW = p.RAW
WORKTREE = Path('/tmp/sm/xl2')
APPROVAL = Path('/tmp/sm/xl2-parent-approval.json')
PREPARATION = '8c4f39d2b60e9fcc8092323ebe8511bd484678ed51df977c934e554114c2d27f'
BINARY = '7483315f653d17f8e314d116c6decdb3990126b3586b34c73cc70330cf115d1e'
KINDS = ('observed', 'repeat', 'off')
LOGS = {'stdout.txt', 'stderr.txt'}
GIB = 1024**3


class Job(TypedDict):
    arm: str
    kind: str
    command: list[str]
    environment: dict[str, str]
    directory: str


class Proposal(TypedDict):
    schema: int
    scope: str
    roots: list[str]
    policy: dict[str, int]
    jobs: list[Job]
    bindings: dict[str, FileRecord]
    native_files: dict[str, list[str]]
    observers: list[str]
    endpoints: FileRecord


def clean_path(path: Path) -> None:
    require(path.is_absolute() and '..' not in path.parts, 'nonliteral path')
    for node in (path, *path.parents):
        require(not node.is_symlink(), f'symlink/redirect: {node}')
    require(path.resolve() == path, f'redirect: {path}')


def files(root: Path) -> dict[str, FileRecord]:
    clean_path(root)
    require(root.is_dir(), f'missing tree: {root}')
    result: dict[str, FileRecord] = {}
    for path in sorted(root.rglob('*')):
        clean_path(path)
        mode = path.lstat().st_mode
        require(stat.S_ISREG(mode) or stat.S_ISDIR(mode), 'nonregular inventory')
        if stat.S_ISREG(mode):
            result[str(path.relative_to(root))] = p.record(path)
    require(bool(result), 'empty inventory')
    return result


def regular(path: Path) -> FileRecord:
    clean_path(path)
    require(path.is_file(), f'missing input: {path}')
    return p.record(path)


def encode(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()


def storage() -> None:
    mounts = Path('/proc/mounts').read_text().splitlines()
    require(any(line.split()[1:3] == ['/tmp/sm', 'fuse.ext4'] and
                line.split()[0] == '/run/media/jojo/Elements/bio-sim-results/stringmol-posix.ext4'
                for line in mounts), 'Elements ext4 image missing')
    require(any(line.split()[1] == str(p.ELEMENTS_STORAGE) for line in mounts), 'Elements missing')
    cumulative_raw = 0
    for root, anchor, budget, free in ((CONTROL, p.POSIX_STORAGE, 4, 5),
                                       (RAW, p.ELEMENTS_STORAGE, 25, 10),
                                       (EXPORT, p.ELEMENTS_STORAGE, 25, 10)):
        clean_path(root)
        require(root.is_relative_to(anchor) and root != anchor, 'storage containment')
        parent = root
        while not parent.exists():
            parent = parent.parent
        require(shutil.disk_usage(parent).free >= free*GIB, 'storage headroom')
        used = sum(r['bytes'] for r in files(root).values()) if root.exists() and any(root.iterdir()) else 0
        require(used < budget*GIB, 'cumulative budget')
        if root in (RAW, EXPORT):
            cumulative_raw += used
    require(cumulative_raw < 25*GIB, 'cumulative raw/export budget')


def proposal() -> Proposal:
    """Recompute from actual pinned inputs, not a caller's claimed digest."""
    storage()
    require(regular(ORIGIN/'preparation.json')['sha256'] == PREPARATION, 'origin eligibility')
    old = json.loads((ORIGIN/'preparation.json').read_text())
    require(regular(WORKTREE/'reports/sm_xl001_plan.md') ==
            old['implementation']['reports/sm_xl001_plan.md'], 'unchanged original endpoints')
    source = ORIGIN/'n'
    require(regular(source/'release/stringmol')['sha256'] == BINARY, 'binary eligibility')
    require(files(source/'src') == old['source'], 'full native source eligibility')
    require(regular(source/'config/ALXII.mtx') == old['matrix'], 'SUBMAT eligibility')
    bindings: dict[str, FileRecord] = {}

    def bind(path: Path) -> None:
        bindings[str(path)] = regular(path)

    for name in ('preparation.json', 'preparation.sha256.json'):
        bind(ORIGIN/name)
    for root in (source/'src', source/'config'):
        for relative in files(root):
            bind(root/relative)
    bind(source/'release/stringmol')
    # Bind the resolved interpreter explicitly; the shared venv launcher is an
    # intentional symlink, not an arbitrary unbound ambient executable.
    interpreter = Path(p.PYTHON).resolve(strict=True)
    bind(interpreter)
    for path in sorted((WORKTREE/'experiments').rglob('*.py')):
        bind(path)
    for path in sorted((WORKTREE/'tests').glob('*locality*')):
        if path.is_file():
            bind(path)
    for name in ('sm_xl001_plan.md', 'sm_xl001_recovery_plan.md',
                 'stringmol_exploration_code_review_closeout.md',
                 'stringmol_parallel_exploration_parent_review.md'):
        bind(WORKTREE/'reports'/name)
    for path in (WORKTREE/'pyproject.toml', WORKTREE/'AGENTS.md'):
        if path.exists():
            bind(path)
    gate = Path('/tmp/sm/xl2-q/QUALIFIED.json')
    bind(gate)
    gates = json.loads(gate.read_text())
    require(gates['zero_populations'] is True, 'qualification scope')
    for name in ('normal', 'optimized', 'typing'):
        receipt = Path(gates[name])
        require(receipt.parent == gate.parent, 'gate redirection')
        bind(receipt)
        require(json.loads(receipt.read_text())['exit_code'] == 0, 'failed qualification')
    bind(Path('/tmp/sm/xlr-e/logging-fixture-final'))
    bind(Path('/tmp/sm/xlr-e/native-source-binding.json'))
    require(json.loads(Path('/tmp/sm/xlr-e/native-source-binding.json').read_text())['final_source'] ==
            old['source'], 'directed fixture source binding')
    jobs: list[Job] = []
    native_files: dict[str, list[str]] = {}
    for arm, (interaction, placement) in p.ARMS.items():
        config = ORIGIN/f'{arm}.conf'
        require(config.read_text() == render_config(StringmolControlConfig('host-only', p.SEED,
                interaction, placement, mutation_rate=0), source/'config/ALXII.mtx'), 'founders/config eligibility')
        bind(config)
        for kind in KINDS:
            identity = f'{arm}-{kind}'
            receipt = OLD_RAW/f'{identity}.receipt.json'
            bind(receipt)
            prior = json.loads(receipt.read_text())
            require(prior['exit_code'] == 0 and prior.get('collection_complete', True), 'original receipt')
            require(files(OLD_RAW/identity) == prior['inventory'], 'original evidence inventory')
            expected = set(prior['inventory'])-LOGS
            require(bool(expected) and (kind == 'off' or set(p.OBS) <= expected), 'original scientific inventory')
            # Historical off is NOT a valid new off condition. Only its ordinary
            # filename set is reused; no historical off outcome substitutes.
            native_files[identity] = sorted(expected if kind != 'off' else expected-p.OBS)
            jobs.append(dict(arm=arm, kind=kind,
                command=[str(source/'release/stringmol'), '30', str(config)],
                environment=p.locality_environment(kind != 'off'), directory=str(RAW/identity)))
    return dict(schema=1, scope='complete12-native16-replay; parent review required; no retry',
                roots=list(map(str, (CONTROL, RAW, EXPORT, WORKTREE, interpreter))),
                policy=dict(workers=1, build_jobs=2, native_timeout=600, replay_timeout=1800,
                            natives=12, replays=16, posix_gib=4, raw_gib=25),
                jobs=jobs, bindings=bindings, native_files=native_files, observers=sorted(p.OBS),
                endpoints=regular(WORKTREE/'reports/sm_xl001_plan.md'))


def freeze(destination: Path) -> None:
    require(destination not in (CONTROL, RAW, EXPORT), 'not a proposal file')
    clean_path(destination)
    with destination.open('xb') as stream:
        stream.write(encode(proposal()))


def validate(path: Path, digest: str) -> Proposal:
    require(regular(path)['sha256'] == digest, 'parent manifest digest mismatch')
    expected = proposal()
    require(path.read_bytes() == encode(expected), 'stale/malformed/unbound proposal')
    return expected


def successful(result: ProcessResult, root: Path) -> dict[str, FileRecord]:
    require(result['exit_code'] == 0 and result['exception'] is None and
            result['collection_complete'] and result['inventory_error'] is None, 'process/evidence failure')
    current = files(root)
    require(current == result['inventory'], 'incomplete/changed inventory')
    return current


def replay_one(arm: str, kind: str, output: Path) -> None:
    require(arm in p.ARMS and kind in ('observed', 'repeat'), 'replay identity')
    from experiments.stringmol.locality_replay import replay
    coordinates, _ = inoculum()
    initial = initial_material([{'id':i, 'sequence_hex':HOST.encode().hex()} for i in range(140)], 'histogram', 0)
    initial['waste'] = [0]*33
    p.save(output, replay(RAW/f'{arm}-{kind}', initial, dict(enumerate(coordinates)), p.SEED,
                        ORIGIN/'n/config/ALXII.mtx', *p.ARMS[arm]))


def portable() -> None:
    storage()
    EXPORT.mkdir(parents=True, exist_ok=False)
    checksums: dict[str, FileRecord] = {}
    for name, root in (('controls', CONTROL), ('raw', RAW)):
        for relative, before in files(root).items():
            source = root/relative
            target = EXPORT/name/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open('rb') as src, target.open('xb') as dst:
                shutil.copyfileobj(src, dst)
            require(regular(source) == regular(target) == before, 'export checksum mismatch')
            checksums[f'{name}/{relative}'] = before
    frozen = cast(Proposal, json.loads((CONTROL/'launch.json').read_text()))
    for path, before in frozen['bindings'].items():
        source = Path(path)
        target = EXPORT/'inputs'/source.relative_to('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        require(regular(source) == before, 'export input drift')
        with source.open('rb') as src, target.open('xb') as dst:
            shutil.copyfileobj(src, dst)
        require(regular(target) == before, 'export input checksum')
        checksums[str(target.relative_to(EXPORT))] = before
    for name, command in (('source.tar', ['git', 'archive', '--format=tar', 'HEAD']),
                          ('source.bundle', ['git', 'bundle', 'create', str(EXPORT/'source.bundle'), 'HEAD'])):
        if name.endswith('.tar'):
            with (EXPORT/name).open('xb') as out:
                subprocess.run(command, cwd=WORKTREE, stdout=out, check=True)
        else:
            subprocess.run(command, cwd=WORKTREE, check=True)
        checksums[name] = regular(EXPORT/name)
    p.save(EXPORT/'checksums.json', checksums)
    require(all(regular(EXPORT/name) == value for name, value in checksums.items()), 'export rehash')
    storage()
    p.save(EXPORT/'VERIFIED.json', dict(verified=True, checksums=regular(EXPORT/'checksums.json')))


def workflow(data: Proposal) -> None:
    """Only launch() admits this one-shot workflow; tests replace process calls."""
    # Reservation persists across every later failure, including export failure.
    CONTROL.mkdir(exist_ok=False)
    p.save(CONTROL/'launch.json', data)
    try:
        RAW.mkdir(exist_ok=False)
        inventories: dict[str, dict[str, FileRecord]] = {}
        for job in data['jobs']:
            storage()
            require(all(regular(Path(path)) == value for path, value in data['bindings'].items()), 'binding changed')
            identity = f"{job['arm']}-{job['kind']}"
            directory = Path(job['directory']); directory.mkdir(exist_ok=False)
            logs = CONTROL/identity; logs.mkdir()
            result = execute(job['command'], cwd=directory, environment=job['environment'],
                receipt=CONTROL/f'{identity}.process.json', stdout=logs/'stdout.txt',
                stderr=logs/'stderr.txt', timeout=600, output_root=directory)
            current = successful(result, directory)
            require(sorted(current) == data['native_files'][identity], 'native file set')
            inventories[identity] = current
            if job['kind'] != 'off':
                old = json.loads((OLD_RAW/f'{identity}.receipt.json').read_text())['inventory']
                require(current == {k:v for k,v in old.items() if k not in LOGS}, 'original scientific drift')
                for name in LOGS:
                    require(regular(logs/name) == old[name], 'original process output drift')
        for arm in p.ARMS:
            on, repeat, off = (inventories[f'{arm}-{kind}'] for kind in KINDS)
            require(on == repeat, 'native repeat parity')
            require(set(on)-set(off) == p.OBS and not set(off)&p.OBS and
                    {k:v for k,v in on.items() if k not in p.OBS} == off, 'fully-off parity')
            # Stdout/stderr are process evidence, not native scientific files.
            for name in LOGS:
                require(regular(CONTROL/f'{arm}-observed'/name) ==
                        regular(CONTROL/f'{arm}-repeat'/name) ==
                        regular(CONTROL/f'{arm}-off'/name), 'ordinary process parity')
        p.save(CONTROL/'native-complete.json', dict(executions=12))
        results: dict[str, ReplayResult] = {}
        for arm in p.ARMS:
            outputs: list[bytes] = []
            for kind in ('observed', 'repeat'):
                for repetition in (1, 2):
                    storage()
                    require(all(regular(Path(path)) == value for path, value in data['bindings'].items()), 'binding changed')
                    identity = f'{arm}-{kind}-replay{repetition}'
                    directory = CONTROL/identity; directory.mkdir()
                    output = directory/'result.json'
                    env = {'PATH':'/usr/bin:/bin', 'LC_ALL':'C', 'LANG':'C', 'TZ':'UTC',
                           'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONNOUSERSITE':'1'}
                    process = execute([p.PYTHON, '-I', '-c',
                        'import sys; sys.path.insert(0, '+repr(str(WORKTREE))+'); '
                        'from experiments.stringmol.locality_recovery import replay_one; '
                        f'from pathlib import Path; replay_one({arm!r}, {kind!r}, Path({str(output)!r}))'],
                        cwd=WORKTREE, environment=env, receipt=CONTROL/f'{identity}.process.json',
                        stdout=directory/'stdout.txt', stderr=directory/'stderr.txt', timeout=1800, output_root=directory)
                    collected = successful(process, directory)
                    require(set(collected) == {'result.json', 'stdout.txt', 'stderr.txt'}, 'replay output set')
                    value = cast(ReplayResult, json.loads(output.read_text()))
                    require(type(value['end_tick']) is int and 0 <= value['end_tick'] <= 5000 and
                            (value['end_tick'] == 5000 or value['end_population'] == 0), 'invalid replay outcome')
                    outputs.append(output.read_bytes())
                    results[arm] = value
            require(all(value == outputs[0] for value in outputs), 'repeat analysis parity')
        gg = results['GG']
        pop = next((row['population'] for row in gg['checkpoints'] if row['tick'] == 4900), 0)
        positive = gg['placed'] >= 100 and pop > 0
        # Full verifier results preserve every frozen count and spatial denominator.
        p.save(CONTROL/'decision.json', dict(integrity=True, positive_control=positive,
            classification='descriptive' if positive else 'valid control-negative',
            independent_seeds_per_cell=1, technical_repeats_not_replication=True, results=results))
        portable()
        p.save(CONTROL/'complete.json', dict(native=12, replay=16, export=regular(EXPORT/'VERIFIED.json')))
    except Exception as exc:
        p.save(CONTROL/'blocked.json', dict(classification='unevaluable/blocked',
               type=type(exc).__name__, message=str(exc), no_retry=True))
        raise


def launch(path: Path, digest: str) -> None:
    data = validate(path, digest)
    approval = dict(scope=data['scope'], proposal_sha256=digest, roots=data['roots'],
                    independent_parent_review='PASS', native_budget=12)
    regular(APPROVAL)
    require(APPROVAL.read_bytes() == encode(approval), 'independent parent approval required')
    require(not any(root.exists() for root in (CONTROL, RAW, EXPORT)), 'no reuse/resume')
    require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=WORKTREE, text=True).strip(), 'commit first')
    workflow(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'launch'))
    parser.add_argument('proposal', type=Path)
    parser.add_argument('--parent-digest')
    args = parser.parse_args()
    if args.action == 'freeze':
        freeze(args.proposal)
    else:
        require(isinstance(args.parent_digest, str), 'parent digest required')
        launch(args.proposal, args.parent_digest)
