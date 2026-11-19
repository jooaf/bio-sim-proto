"""Versioned future-launch bindings; historical freeze files remain readable.

Legacy preparations deliberately cannot launch through the hardened interface.
A binding receipt records the *actual* SUBMAT dependencies and preparation bytes,
including all per-case environments, founders and settings.
"""
from __future__ import annotations

from pathlib import Path
from experiments.stringmol import xp001 as x
from experiments.stringmol.xp001_safety import Case, Founder, object_from, require


def integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError('expected integer')
    return value


def text(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError('expected nonempty string')
    return value


def mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise ValueError('expected object')
    return value


def cases_from(frozen: dict[str, object]) -> list[Case]:
    values = frozen.get('matrix')
    if not isinstance(values, list) or len(values) != 12:
        raise ValueError('expected exactly twelve frozen cases')
    cases: list[Case] = []
    for index, value in enumerate(values):
        row = mapping(value)
        require(integer(row['index']) == index, 'case indices must be ordered and unique')
        mixed = row['mixed']
        if not isinstance(mixed, bool):
            raise ValueError('mixed must be boolean')
        founders_value = row['founders']
        if not isinstance(founders_value, list):
            raise ValueError('founders must be a list')
        founders: list[Founder] = []
        for item in founders_value:
            f = mapping(item)
            founders.append(Founder(id=integer(f['id']), x=integer(f['x']), y=integer(f['y']),
                                    label=integer(f['label']), sequence_hex=text(f['sequence_hex'])))
        environment = {k: text(v) for k, v in mapping(row['environment']).items()}
        case = Case(index=index, count=integer(row['count']), mixed=mixed, seed=integer(row['seed']),
                    repeat=integer(row['repeat']), observed=integer(row['observed']), founders=founders,
                    config=text(row['config']), config_sha256=text(row['config_sha256']), environment=environment)
        require(case['count'] == len(founders) and len({f['id'] for f in founders}) == len(founders), 'founder count/IDs')
        require(case['observed'] in (0, 1) and case['repeat'] in (0, 1), 'invalid case flags')
        cases.append(case)
    return cases


def matrix_path(config: Path) -> Path:
    entries = [line.split() for line in config.read_text().splitlines() if line.split() and line.split()[0] == 'SUBMAT']
    require(len(entries) == 1 and len(entries[0]) == 2, 'one SUBMAT path required')
    path = Path(entries[0][1])
    # Relative matrices depend on execution cwd; do not guess it.
    require(path.is_absolute(), 'SUBMAT must be absolute')
    return path


def bind(control: Path, cases: list[Case]) -> None:
    native = x.EVIDENCE / 'native-v2'
    gate_path = x.RAW / 'reactions-v2/gate.json'
    gate = object_from(gate_path)
    fields = ('valid', 'deterministic', 'observation_isolation', 'canonical_positive',
              'candidate_nonproductive', 'population_authorized_by_reaction_gate')
    require(all(gate.get(k) is True for k in fields), 'reaction gate failed')
    build = object_from(native / 'build.json')
    inputs = mapping(build['inputs'])
    dependencies = {gate_path, native / 'build.json', native / 'inputs.json',
                    x.ROOT / 'reports/sm_xp001_development_plan.md',
                    x.ROOT / 'reports/sm_xp001_reaction_recovery_plan.md',
                    x.ROOT / 'reports/sm_xp001_population_launch.md'}
    for name, expected in inputs.items():
        path = native / name
        require(path.resolve().is_relative_to(native.resolve()), 'build input escapes native root')
        require(x.digest(path) == text(expected), 'build source drift')
        dependencies.add(path)
    require(object_from(native / 'inputs.json') == inputs, 'build input receipt drift')
    require(x.digest(native / 'reaction') == text(build['binary']), 'reaction binary drift')
    dependencies.add(native / 'reaction')
    # Source snapshots are bound as files, not only an unverified Git identifier.
    dependencies.update((x.ROOT / 'experiments/stringmol').glob('*.py'))
    for case in cases:
        config = Path(case['config'])
        require(x.digest(config) == case['config_sha256'], 'config drift during preparation')
        matrix = matrix_path(config)
        require(x.digest(matrix) == text(build['matrix']), 'runtime matrix differs from qualified matrix')
        dependencies.add(matrix)
    x.save(control / 'bindings-v1.json', {
        'schema': 'xp-launch-bindings-v1', 'freeze_sha256': x.digest(control / 'freeze.json'),
        'dependencies': {str(path): x.digest(path) for path in sorted(dependencies)},
    })


def verify(control: Path) -> tuple[Path, list[Case]]:
    binding = object_from(control / 'bindings-v1.json')
    require(binding.get('schema') == 'xp-launch-bindings-v1', 'unsupported prospective binding')
    require(binding.get('freeze_sha256') == x.digest(control / 'freeze.json'), 'preparation drift')
    dependencies = mapping(binding['dependencies'])
    require(bool(dependencies), 'missing dependency bindings')
    for name, expected in dependencies.items():
        require(x.digest(Path(name)) == text(expected), f'dependency drift: {name}')
    frozen = object_from(control / 'freeze.json')
    binary = Path(text(frozen['binary']))
    require(x.digest(binary) == text(frozen['binary_sha256']), 'population binary drift')
    cases = cases_from(frozen)
    for case in cases:
        config = Path(case['config'])
        require(x.digest(config) == case['config_sha256'], 'population config drift')
        require(str(matrix_path(config)) in dependencies, 'unbound SUBMAT')
    return binary, cases
