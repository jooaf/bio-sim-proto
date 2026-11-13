"""Execution-aware freshness audit; no simulation launch or input generation.

Source-code references and non-seed data columns are not executions. Archives
are read without extraction. Exact authorized files, not subtrees, may be exempt.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import tarfile
from typing import Any, Callable, IO
import zipfile

from experiments.stringmol.analyze_lineage import require

TEXT = frozenset(('.json', '.jsonl', '.conf', '.cfg', '.csv', '.txt', '.nuon', '.yaml', '.yml', '.toml', '.stdout', '.stderr', '.log', '.ini'))
ARCHIVES = ('.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tar.xz', '.zip')
# Exact retained negative-test artifact, not a directory exemption. Its generator
# contains no native launch and uses fake reserved values. All three witnesses
# must match; any change blocks classification rather than accepting an alias.
FIXTURE = Path('/tmp/sm/sm-b003-campaign-audit-unit-v5/pytest/test_archive_metadata_alias_is0/alias.tar')
FIXTURE_PROOFS = (
    (FIXTURE, '1cb8d4d5c57cb823f01e417de4e120c9612c27c343b7a78671b35d1650ae57ed'),
    (Path('/run/media/jojo/Elements/bio-sim-results/verification/sm-b003-campaign-audit-unit-v5/qualified-test-source.py'), '848451b64156755eb390e39e9e92baa2e51e58f648a2a17db3b8423a6dbf1615'),
    (Path('/run/media/jojo/Elements/bio-sim-results/verification/sm-b003-campaign-audit-unit-v5/result.nuon'), 'd17f0471b80a7fff4919396d884ffd832c3800b39f3e9d2ef740046951ba31fe'),
)


def classified_fixture(path: Path) -> bool:
    if path != FIXTURE: return False
    for proof, expected in FIXTURE_PROOFS:
        require(hashlib.sha256(proof.read_bytes()).hexdigest() == expected, 'nonexecution fixture provenance changed')
    return True


def seed_key(key: str) -> bool:
    normalized = re.sub(r'[^a-z0-9]', '', key.lower())
    return 'seed' in normalized or normalized in ('randomstate', 'rngseed')


def sensitive_key(key: str) -> bool:
    return seed_key(key) or key.lower() in ('command', 'argv', 'args', 'config', 'configuration', 'environment')


def parameter_columns(header: list[str]) -> tuple[int, int] | None:
    normalized = [value.strip().lower() for value in header]
    if 'value' in normalized:
        for key in ('key', 'parameter', 'field', 'name'):
            if key in normalized: return normalized.index(key), normalized.index('value')
    return None


def inspect_text(raw: bytes, name: str, seeds: tuple[int, ...]) -> tuple[list[dict[str, Any]], int]:
    """Return seed-bearing/ambiguous occurrences and classified non-seed count."""
    pattern = re.compile(r'(?<![\w.])(?:'+ '|'.join(map(str, seeds)) + r')(?![\w.])')
    text = raw.decode('utf-8', errors='strict')
    if not pattern.search(text): return [], 0
    matches: list[dict[str, Any]] = []
    classified = 0
    suffix = Path(name).suffix.lower()
    if suffix == '.json':
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return [{'kind': 'ambiguous-malformed-json'}], 0
        def visit(node: Any, path: tuple[str, ...], sensitive: bool = False) -> None:
            nonlocal classified
            if isinstance(node, dict):
                for key, child in node.items():
                    # Command arguments can carry positional seeds, not just --seed.
                    flagged = sensitive_key(key)
                    visit(child, (*path, key), sensitive or flagged)
            elif isinstance(node, list):
                for i, child in enumerate(node): visit(child, (*path, str(i)), sensitive)
            else:
                found = pattern.findall(str(node))
                if found:
                    inline = isinstance(node, str) and re.search(r'(?i)\b(?:randseed|seed|random_seed)\b[\s\"\x27:=]+', node)
                    if sensitive or inline or not path:
                        matches.append({'kind': 'structured-input', 'field': '/'.join(path), 'values': found})
                    else:
                        classified += len(found)
        visit(value, ())
        return matches, classified
    if suffix == '.csv':
        rows = csv.reader(io.StringIO(text), strict=True)
        try:
            header = next(rows)
            indexes = [i for i, label in enumerate(header) if sensitive_key(label)]
            parameters = parameter_columns(header)
            for number, row in enumerate(rows, 2):
                require(len(row) == len(header), 'ambiguous CSV width: '+name)
                for i, cell in enumerate(row):
                    found = pattern.findall(cell)
                    if found:
                        if i in indexes or (parameters is not None and i == parameters[1] and sensitive_key(row[parameters[0]])):
                            matches.append({'kind': 'csv-seed-field', 'row': number, 'field': header[i], 'values': found})
                        else: classified += len(found)
        except (csv.Error, StopIteration, ValueError):
            return [{'kind': 'ambiguous-csv'}], 0
        return matches, classified
    # Full MT state is not a seed declaration. Strict layout prevents a filename
    # alone from exempting arbitrary input text.
    if Path(name).name == 'final_rng.txt':
        tokens = text.split()
        if len(tokens) == 626 and tokens[0] == 'MTI' and all(t.isdecimal() for t in tokens[1:]) and int(tokens[1]) <= 624 and all(int(t) < 2**32 for t in tokens[2:]):
            return [], len(pattern.findall(text))
    # Unknown text with a reserved integer is conservatively ambiguous. A failed
    # audit retains file records for investigation; it never guesses an exemption.
    return [{'kind': 'unclassified-text', 'values': sorted(set(pattern.findall(text)))}], 0


def audit(roots: tuple[Path, ...], seeds: tuple[int, ...], *, allowed: dict[Path, dict[str, Any]] | None = None,
          progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    require(bool(seeds) and len(set(seeds)) == len(seeds) and all(type(s) is int and s >= 0 for s in seeds), 'audit seed set')
    scopes = tuple(root.resolve(strict=True) for root in roots)
    require(all(root.is_dir() for root in scopes), 'audit scope missing directory')
    exemptions = {p.resolve(strict=True): record for p, record in (allowed or {}).items()}
    require(all(any(p.is_relative_to(root) for root in scopes) for p in exemptions), 'audit exclusion outside scope')
    pattern = re.compile(r'(?<![0-9])(?:'+ '|'.join(map(str, seeds)) + r')(?![0-9])')
    seen: set[Path] = set()
    inventory: dict[str, Any] = {}
    matches: list[dict[str, Any]] = []
    links: dict[str, str] = {}
    classified: dict[str, int] = {}
    csv_schemas: dict[str, list[str]] = {}
    found_allowed: set[Path] = set()
    literal_prefix = os.path.commonprefix([str(s) for s in seeds]).encode()
    payload_count = 0

    def payload(stream: IO[bytes], name: str, declared_size: int, *, inspect: bool = True) -> dict[str, Any]:
        nonlocal payload_count
        payload_count += 1
        if progress is not None and payload_count % 1000 == 1:
            progress({'payloads_started': payload_count, 'current': name})
        start = stream.tell()
        if inspect and Path(name).suffix.lower() == '.csv':
            line = stream.readline(65537)
            try:
                header = next(csv.reader([line.decode('utf-8')], strict=True)) if line else []
                require(len(line) <= 65536, 'oversize CSV header')
            except (UnicodeDecodeError, csv.Error, ValueError):
                matches.append({'path': name, 'kind': 'unclassifiable-csv-header'})
                return {'size': declared_size, 'header_sha256': hashlib.sha256(line).hexdigest(), 'full_content_hashed': False}
            if header and not any(sensitive_key(label) for label in header) and parameter_columns(header) is None:
                # Data columns are not seed declarations. Keep the schema proof
                # explicit; never misrepresent this as a full-file checksum.
                schema = hashlib.sha256(line).hexdigest()
                csv_schemas[schema] = header
                return {'size': declared_size, 'header_sha256': schema,
                        'classification': 'nonseed-csv-columns', 'full_content_hashed': False}
            stream.seek(start)
        digest = hashlib.sha256(); size = 0
        # Only payloads containing reserved tokens need structured parsing. Hash
        # every eligible file in chunks; do not allocate all historical CSVs.
        contains = False; tail = b''
        raw_pattern = re.compile(rb'(?<![\w.])(?:'+ b'|'.join(str(s).encode() for s in seeds) + rb')(?![\w.])')
        while chunk := stream.read(1024*1024):
            digest.update(chunk); size += len(chunk)
            if inspect:
                candidate = tail+chunk
                if literal_prefix in candidate and raw_pattern.search(candidate): contains = True
                tail = chunk[-32:]
        result = {'size': size, 'sha256': digest.hexdigest()}
        if inspect and contains:
            stream.seek(start)
            try:
                if size > 512 * 1024 * 1024:
                    hits, count = [{'kind': 'oversize-metadata-requires-review'}], 0
                else:
                    hits, count = inspect_text(stream.read(), name, seeds)
            except UnicodeDecodeError:
                hits, count = [{'kind': 'non-utf8-metadata'}], 0
            if hits: matches.extend({'path': name, **hit} for hit in hits)
            if count: classified[name] = count
        return result

    def member(stream: IO[bytes], archive: Path, name: str, size: int) -> None:
        identity = str(archive)+'!'+name
        if pattern.search(name): matches.append({'path': identity, 'kind': 'archive-input-name'})
        if Path(name).suffix.lower() in TEXT:
            require(identity not in inventory, 'duplicate archive member: '+identity)
            inventory[identity] = payload(stream, identity, size)
        elif name.lower().endswith(ARCHIVES):
            raise ValueError('nested archive requires explicit audit support: '+identity)

    for scope in scopes:
        if progress is not None: progress({'scope_started': str(scope)})
        for base, directories, names in os.walk(scope, followlinks=False):
            directories[:] = sorted(directories)
            for name in sorted([*directories, *names]):
                p = Path(base)/name
                if p.is_symlink():
                    links[str(p)] = os.readlink(p)
                    if pattern.search(str(p)) or pattern.search(links[str(p)]): matches.append({'path': str(p), 'kind': 'seed-bearing-link'})
                    target = p.resolve()
                    metadata_target = (target.is_dir() or p.suffix.lower() in TEXT or target.suffix.lower() in TEXT or
                                       p.name.lower().endswith(ARCHIVES) or target.name.lower().endswith(ARCHIVES))
                    if target.exists() and metadata_target and not any(target.is_relative_to(root) for root in scopes):
                        matches.append({'path': str(p), 'kind': 'unaudited-symlink-target'})
                    continue
                if p in seen: continue
                seen.add(p)
                if p not in exemptions and pattern.search(str(p)):
                    matches.append({'path': str(p), 'kind': 'input-name'})
                if not p.is_file(): continue
                if p.name.lower().endswith(('.zst', '.7z', '.rar')):
                    raise ValueError('unsupported archive in audit scope: '+str(p))
                archive = p.name.lower().endswith(ARCHIVES)
                if p not in exemptions and not archive and p.suffix.lower() not in TEXT: continue
                if archive and p not in exemptions:
                    record = {'size': p.stat().st_size, 'classification': 'archive-members-inspected', 'full_content_hashed': False}
                else:
                    with p.open('rb') as stream:
                        record = payload(stream, str(p), p.stat().st_size, inspect=p not in exemptions)
                synthetic_fixture = archive and classified_fixture(p)
                if synthetic_fixture:
                    record = {**record, 'classification': 'qualified-nonexecution-guard-fixture',
                              'proofs': {str(proof): digest for proof, digest in FIXTURE_PROOFS}}
                inventory[str(p)] = record
                if p in exemptions:
                    require(record == exemptions[p], 'authorized preparation bytes changed: '+str(p))
                    found_allowed.add(p)
                elif archive:
                    if p.suffix.lower() == '.zip':
                        with zipfile.ZipFile(p) as z:
                            for entry in z.infolist():
                                if stat.S_ISLNK(entry.external_attr >> 16) and Path(entry.filename).suffix.lower() in TEXT:
                                    matches.append({'path': str(p)+'!'+entry.filename, 'kind': 'unaudited-archive-alias'})
                                if not entry.is_dir():
                                    with z.open(entry) as zip_stream: member(zip_stream, p, entry.filename, entry.file_size)
                    else:
                        with tarfile.open(p, 'r:*') as tar:
                            for tar_entry in tar:
                                if (tar_entry.issym() or tar_entry.islnk()) and Path(tar_entry.name).suffix.lower() in TEXT and not synthetic_fixture:
                                    matches.append({'path': str(p)+'!'+tar_entry.name, 'kind': 'unaudited-archive-alias'})
                                if tar_entry.isfile():
                                    tar_stream = tar.extractfile(tar_entry)
                                    require(tar_stream is not None, 'unreadable archive member')
                                    assert tar_stream is not None
                                    with tar_stream: member(tar_stream, p, tar_entry.name, tar_entry.size)
    require(found_allowed == set(exemptions), 'authorized preparation absent from scope')
    return {'started_at': started, 'completed_at': datetime.now(timezone.utc).isoformat(), 'scope': [str(p) for p in scopes], 'reserved_values': list(seeds), 'inventory': inventory,
            'authorized_files': {str(p): v for p, v in exemptions.items()}, 'symlinks_not_followed': links,
            'csv_schemas': csv_schemas, 'classified_nonseed_occurrences': classified, 'matches': matches, 'passed': not matches}
