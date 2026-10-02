"""Frozen H001 source verification, deterministic panel and SHA-256 permutation."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.stringmol import renewal_workflow as h, analyze_renewal as a
from experiments.stringmol import analyze_conservation as c
from experiments.stringmol.conservation_workflow import ROOT, digest
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.configure_control import HOST, StringmolControlConfig, inoculum, render_config

SOURCE_ANALYSIS = ROOT/'runs/sm_h001_work/analysis/analysis.json'
SOURCE_MANIFEST = ROOT/'runs/sm_h001_work/prepared/preparation.json'
SOURCE_SHA256 = '1c64913c61624ddc82800dc33620e5c3da11ae67240a6abacaf4d8e15b4bbd04'
SOURCE_COMMIT = '8c3bd7453d75bb38da103fd462e1cae89573e5ec'


def sequence(raw: bytes) -> None:
    require(0 < len(raw) < c.MAXL0 and set(raw) <= set(c.ALPHABET.encode()), 'invalid candidate alphabet/length')


def distance(raw: bytes) -> int:
    host = HOST.encode()
    return sum(x != y for x, y in zip(raw, host)) + abs(len(raw) - len(host))


def shuffle(raw: bytes) -> dict[str, Any]:
    sequence(raw)
    require(len(set(raw)) > 1, 'no differing composition permutation exists')
    digest = hashlib.sha256(raw).hexdigest()
    for nonce in range(2**32):
        prefix = b'SM-H002\0' + digest.encode('ascii') + b'\0' + nonce.to_bytes(4, 'big')
        order = sorted(range(len(raw)), key=lambda i: (hashlib.sha256(prefix + i.to_bytes(4, 'big') + raw[i:i+1]).digest(), i))
        result = bytes(raw[i] for i in order)
        if result != raw:
            require(len(result) == len(raw) and Counter(result) == Counter(raw) and sum(x != y for x, y in zip(raw, result, strict=True)) >= 2, 'shuffle material mismatch')
            sequence(result)
            return {'nonce': nonce, 'sequence_hex': result.hex().upper(), 'sha256': hashlib.sha256(result).hexdigest()}
    raise ValueError('shuffle nonce exhausted')


def panel(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    hosts = [r for r in analysis['runs'] if r['condition'] == 'host']
    require([r['seed'] for r in hosts] == list(range(202623000, 202623020)), 'H001 source seeds/order')
    chosen: dict[str, dict[str, Any]] = {}
    for run in hosts:
        edges = {e['child']: e for e in run['source_edges']}
        require(len(edges) == len(run['source_edges']), 'source duplicate edge')
        candidates = []
        for renewal in run['renewals']:
            if not renewal['retained_late']:
                continue
            edge = edges[renewal['id']]
            require(edge['productive'] and edge['child_depth'] is not None and edge['tick'] == renewal['birth_tick'], 'source productive renewal edge')
            raw = a.visible(bytes.fromhex(edge['birth_buffer_hex']))
            sequence(raw)
            candidates.append({'source_seed': run['seed'], 'id': renewal['id'], 'birth_tick': renewal['birth_tick'],
                               'length': len(raw), 'retention': renewal['retention'], 'sequence_hex': raw.hex().upper(),
                               'sha256': hashlib.sha256(raw).hexdigest(), 'distance': distance(raw)})
        require(bool(candidates), 'source has no retained late descendant')
        selected = min(candidates, key=lambda p: (-p['distance'], p['birth_tick'], p['id']))
        digest = selected['sha256']
        if digest not in chosen:
            chosen[digest] = {k: selected[k] for k in ('sequence_hex', 'sha256', 'length', 'distance')}
            chosen[digest]['provenances'] = []
        require(chosen[digest]['sequence_hex'] == selected['sequence_hex'], 'source hash collision')
        chosen[digest]['provenances'].append(selected)
    result = []
    for rank, digest in enumerate(sorted(chosen)):
        p = chosen[digest]
        p['provenances'].sort(key=lambda r: (r['source_seed'], r['id']))
        result.append({**p, 'rank': rank, 'canonical_provenance': p['provenances'][0], 'shuffle': shuffle(bytes.fromhex(p['sequence_hex']))})
    require(len(result) == 15 and sum(p['distance'] == 0 for p in result) == 1 and min(p['length'] for p in result) == 36 and max(p['length'] for p in result) == 65, 'frozen panel calibration mismatch')
    return result



def replay_source_run(r: dict[str, Any]) -> dict[str, Any]:
    """Same H001 analyzer and row construction, with ordered process-pool results."""
    from experiments.stringmol import analyze_decay
    directory = Path(r['directory'])
    summary = a.analyze_run(directory, r['expected_initial'], exit_status=0)
    require(set(h.inventory(directory)) == analyze_decay.output_names(summary['end_timestep']), 'H001 source output names')
    return {'condition': r['condition'], 'seed': r['seed'], **summary}


def verify_source(*, replay: bool = False) -> dict[str, Any]:
    require(h.record(SOURCE_ANALYSIS)['sha256'] == SOURCE_SHA256, 'H001 analysis digest')
    data = h.verify_preparation(SOURCE_MANIFEST)
    h.verify_launch(SOURCE_MANIFEST)
    launch = h.read(SOURCE_MANIFEST.parent/'launch.json')
    require(launch['commit'] == SOURCE_COMMIT, 'H001 source implementation commitment')
    for p in [*h.IMPLEMENTATION, *h.PATCHES]:
        require(h.command(['git', 'show', SOURCE_COMMIT + ':' + str(p.relative_to(ROOT))], ROOT) == p.read_bytes(), 'H001 source implementation changed')
    require(h.read(SOURCE_MANIFEST.parent/'campaign.json') == {'input_manifest': h.record(SOURCE_MANIFEST), 'workers': 6, 'launch_record': h.record(SOURCE_MANIFEST.parent/'launch.json')}, 'H001 campaign identity')
    receipts = h.read(SOURCE_MANIFEST.parent/'campaign-results.json')
    require(len(receipts) == 30, 'H001 complete receipt set')
    for r, receipt in zip(data['runs'], receipts, strict=True):
        directory = Path(r['directory'])
        require(receipt == h.read(directory.with_suffix('.inventory.json')) and receipt['files'] == h.inventory(directory), 'H001 source raw receipt/inventory')
        require(receipt['condition'] == r['condition'] and receipt['seed'] == r['seed'] and receipt['input_manifest'] == h.record(SOURCE_MANIFEST) and receipt['exit_status'] == 0, 'H001 source receipt identity/process')
    analysis = h.read(SOURCE_ANALYSIS)
    require(analysis['integrity'] and analysis['decision'] == 'pass' and not analysis['failures'], 'H001 source analysis integrity')
    if replay:
        with ProcessPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(replay_source_run, data['runs']))
        regenerated = a.outcomes(results, [])
        raw = (json.dumps(regenerated, indent=2, sort_keys=True) + '\n').encode()
        require(digest(raw) == SOURCE_SHA256 and regenerated == analysis, 'H001 independent source analysis replay mismatch')
    return {'analysis_path': str(SOURCE_ANALYSIS), 'analysis_record': h.record(SOURCE_ANALYSIS),
            'manifest': str(SOURCE_MANIFEST), 'manifest_record': h.record(SOURCE_MANIFEST),
            'launch_record': h.record(SOURCE_MANIFEST.parent/'launch.json'),
            'receipts_record': h.record(SOURCE_MANIFEST.parent/'campaign-results.json'),
            'implementation_commit': SOURCE_COMMIT, 'panel': panel(analysis)}


def expected_initial(candidate: dict[str, Any], arm: str) -> list[dict[str, Any]]:
    from experiments.stringmol.analyze_perturbation import ARMS
    require(arm in ARMS, 'unknown H002 arm')
    raw = bytes.fromhex(candidate['shuffle']['sequence_hex'] if arm.startswith('SHUFFLE') else candidate['sequence_hex'])
    sequence(raw)
    species: dict[bytes, int] = {}
    result = []
    for i, (x, y) in enumerate(inoculum()[0]):
        seq = HOST.encode() if arm.endswith('SUPPORT') and i >= 70 else raw
        species.setdefault(seq, len(species) + 1)
        result.append({'id': i, 'species': species[seq], 'label': ord('Q'), 'x': x, 'y': y, 'sequence_hex': seq.hex().upper()})
    return result


def initial_cohorts(arm: str) -> dict[str, str]:
    return {str(i): 'support' if arm.endswith('SUPPORT') and i >= 70 else 'candidate' for i in range(140)}


def render(candidate: dict[str, Any], arm: str, seed: int, matrix: Path) -> str:
    base = render_config(StringmolControlConfig('host-only', seed, 0, 0), matrix)
    header = base[:base.index('AGENT ')]
    return header + ''.join(f"AGENT {bytes.fromhex(r['sequence_hex']).decode('ascii')} 1 Q\nGRIDPOS {r['x']} {r['y']}\n" for r in expected_initial(candidate, arm))


def parse_config(raw: str, expected: list[dict[str, Any]], seed: int, matrix: Path) -> None:
    """Independently parse loader records; IDs/species follow first-seen load order."""
    lines = raw.splitlines()
    header_end = next(i for i, line in enumerate(lines) if line.startswith('AGENT '))
    template = render_config(StringmolControlConfig('host-only', seed, 0, 0), matrix)
    require(lines[:header_end] == template.splitlines()[:header_end], 'custom config settings/header')
    records = lines[header_end:]
    require(len(records) == 280, 'custom config molecule count')
    species: dict[str, int] = {}
    parsed = []
    for i in range(140):
        agent, seq, count, label = records[2*i].split()
        pos, x, y = records[2*i+1].split()
        require((agent, count, label, pos) == ('AGENT', '1', 'Q', 'GRIDPOS'), 'custom native label/load count')
        sequence(seq.encode('ascii'))
        species.setdefault(seq, len(species) + 1)
        parsed.append({'id': i, 'species': species[seq], 'label': ord(label), 'x': int(x), 'y': int(y), 'sequence_hex': seq.encode().hex().upper()})
    require(parsed == expected, 'custom ID/load order/position/sequence mismatch')
