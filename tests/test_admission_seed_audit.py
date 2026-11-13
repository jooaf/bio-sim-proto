"""Audit tests use fake reserved values, never the actual held-out seeds."""
import io
import json
from pathlib import Path
import tarfile
import zipfile

import pytest

from experiments.admission_seed_audit import audit, inspect_text
from experiments import admission_seed_audit as module
from experiments.stringmol import conservation_workflow as c

SEEDS = (912345001, 912345002)


@pytest.mark.parametrize('value', [
    {'seed': SEEDS[0]}, {'config': {'seed': SEEDS[1]}},
    {'argv': ['simulate', str(SEEDS[0])]}, {'seeds': list(SEEDS)},
    {'note': 'RANDSEED '+str(SEEDS[0])}, SEEDS[0],
])
def test_seed_inputs_are_not_counters(value: object) -> None:
    hits, _ = inspect_text(json.dumps(value).encode(), 'input.json', SEEDS)
    assert hits


@pytest.mark.parametrize('name,raw', [
    ('output.json', b'{"returns": 912345001}'),
    ('output.csv', b'tick,returns\n1,912345001\n'),
    ('final_rng.txt', ('MTI 624\n'+'\n'.join([str(SEEDS[0])]+['0']*623)+'\n').encode()),
])
def test_nonseed_counters_and_complete_mt_state(name: str, raw: bytes) -> None:
    hits, count = inspect_text(raw, name, SEEDS)
    assert not hits and count == 1


@pytest.mark.parametrize('name,raw', [
    ('config.conf', b'RANDSEED 912345001\n'),
    ('input.csv', b'seed,count\n912345001,2\n'),
    ('input.csv', b'command\n--seed 912345001\n'),
    ('input.csv', b'parameter,value\nseed,912345001\n'),
    ('input.json', b'{"seed": 912345001'),
    ('final_rng.txt', b'912345001\n'),
])
def test_ambiguous_or_seed_bearing_metadata_blocks(name: str, raw: bytes) -> None:
    assert inspect_text(raw, name, SEEDS)[0]


def test_exact_authorization_never_exempts_subtree(tmp_path: Path) -> None:
    prepared = tmp_path/'planned.conf'
    prepared.write_text('RANDSEED '+str(SEEDS[0])+'\n')
    allowed = {prepared: c.record(prepared)}
    assert audit((tmp_path,), SEEDS, allowed=allowed)['passed']
    (tmp_path/'executed.json').write_text(json.dumps({'seed': SEEDS[1]}))
    result = audit((tmp_path,), SEEDS, allowed=allowed)
    assert not result['passed'] and len(result['matches']) == 1
    prepared.write_text('RANDSEED 9\n')
    with pytest.raises(ValueError, match='bytes changed'):
        audit((tmp_path,), SEEDS, allowed=allowed)


@pytest.mark.parametrize('extension', ['tar.gz', 'zip'])
def test_archive_metadata_is_audited_without_extraction(tmp_path: Path, extension: str) -> None:
    archive = tmp_path/('old.'+extension)
    raw = json.dumps({'seed': SEEDS[0]}).encode()
    if extension == 'zip':
        with zipfile.ZipFile(archive, 'w') as z: z.writestr('../run/config.json', raw)
    else:
        with tarfile.open(archive, 'w:gz') as t:
            entry = tarfile.TarInfo('../run/config.json'); entry.size = len(raw)
            t.addfile(entry, io.BytesIO(raw))
    result = audit((tmp_path,), SEEDS)
    assert not result['passed'] and any('!../run/config.json' in row['path'] for row in result['matches'])
    assert not (tmp_path.parent/'run/config.json').exists()


def test_archive_metadata_alias_is_not_silently_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep the adversarial alias in memory, not in the historical input corpus.
    # Real-file archive inspection is exercised separately for tar and zip.
    path = tmp_path/'alias.tar'
    with tarfile.open(path, 'w'): pass
    blob = io.BytesIO()
    with tarfile.open(fileobj=blob, mode='w') as archive:
        entry = tarfile.TarInfo('config.conf'); entry.type = tarfile.SYMTYPE; entry.linkname = '/outside/input.conf'
        archive.addfile(entry)
    real_open = tarfile.open
    def memory_archive(*args: object, **kwargs: object) -> tarfile.TarFile:
        return real_open(fileobj=io.BytesIO(blob.getvalue()), mode='r:')
    monkeypatch.setattr(tarfile, 'open', memory_archive)
    result = audit((tmp_path,), SEEDS)
    assert not result['passed'] and result['matches'][0]['kind'] == 'unaudited-archive-alias'


def test_fixture_classification_requires_exact_proofs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact, proof = tmp_path/'fixture.bin', tmp_path/'proof.txt'
    artifact.write_bytes(b'fixture'); proof.write_bytes(b'qualification')
    monkeypatch.setattr(module, 'FIXTURE', artifact)
    monkeypatch.setattr(module, 'FIXTURE_PROOFS', tuple((p, c.record(p)['sha256']) for p in (artifact, proof)))
    assert module.classified_fixture(artifact)
    assert not module.classified_fixture(tmp_path/'other.bin')
    proof.write_bytes(b'changed')
    with pytest.raises(ValueError, match='provenance changed'): module.classified_fixture(artifact)


def test_binary_runtime_link_is_not_an_input_file(tmp_path: Path) -> None:
    inside = tmp_path/'inside'; inside.mkdir()
    binary = tmp_path/'python'; binary.write_bytes(b'\x7fELF')
    (inside/'python').symlink_to(binary)
    result = audit((inside,), SEEDS)
    assert result['passed'] and str(inside/'python') in result['symlinks_not_followed']


def test_code_references_are_not_executions(tmp_path: Path) -> None:
    (tmp_path/'design.py').write_text('SEEDS = '+repr(SEEDS))
    (tmp_path/'protocol.md').write_text(str(SEEDS))
    assert audit((tmp_path,), SEEDS)['passed']


def test_csv_schema_optimization_is_explicit_and_keeps_seed_fields(tmp_path: Path) -> None:
    counter = tmp_path/'counters.csv'
    counter.write_text('tick,returns\n1,912345001\n')
    result = audit((tmp_path,), SEEDS)
    entry = result['inventory'][str(counter)]
    assert result['passed'] and entry['classification'] == 'nonseed-csv-columns'
    assert entry['full_content_hashed'] is False and 'sha256' not in entry
    params = tmp_path/'parameters.csv'
    params.write_text('parameter,value\nseed,912345001\n')
    result = audit((tmp_path,), SEEDS)
    assert not result['passed'] and result['inventory'][str(params)] == c.record(params)


def test_hidden_directory_cannot_hide_execution_metadata(tmp_path: Path) -> None:
    hidden = tmp_path/'.git'; hidden.mkdir()
    (hidden/'run.json').write_text(json.dumps({'seed': SEEDS[0]}))
    assert not audit((tmp_path,), SEEDS)['passed']


def test_missing_scope_and_external_alias_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError): audit((tmp_path/'missing',), SEEDS)
    inside = tmp_path/'inside'; inside.mkdir()
    outside = tmp_path/'outside.conf'; outside.write_text('RANDSEED 1\n')
    (inside/'input.conf').symlink_to(outside)
    result = audit((inside,), SEEDS)
    assert not result['passed'] and result['matches'][0]['kind'] == 'unaudited-symlink-target'
