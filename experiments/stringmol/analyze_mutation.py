"""SM-M001 paired mutation baseline, using unchanged independent H001 replay."""
from __future__ import annotations

from collections import Counter
import csv
import json
import math
from pathlib import Path
from statistics import median
import subprocess
from typing import Any

from experiments.stringmol import analyze_renewal as h1, analyze_decay as decay
from experiments.stringmol.configure_control import HOST
from experiments.stringmol.analyze_lineage import require

ARMS = ('NATIVE', 'ZERO')
SEEDS = list(range(202626000, 202626020))
MATRIX = [(arm, seed) for seed in SEEDS for arm in ARMS]
COUNTS = (*h1.ENDPOINTS, 'native_births', 'whole_parent_transfers',
          'orphan_source_productive_births', 'other_nonproductive_births')
SEQUENCE_SCALARS = ('births', 'exact_births', 'exact_fraction', 'noncanonical_births',
                    'noncanonical_fraction', 'unique_sequences', 'hill_q0', 'hill_q1', 'unique_lengths')
SCALARS = (*COUNTS, *(f'{group}_{key}' for group in ('productive', 'renewing') for key in SEQUENCE_SCALARS),
           'retention_median', 'retention_minimum', 'retention_exact_fraction')


def sequence_metrics(sequences: list[bytes], prefix: str) -> dict[str, Any]:
    # Explicit complete visible bytes AND length; never a hash key.
    abundance = Counter((len(seq), seq) for seq in sequences)
    n = len(sequences)
    exact = sum(seq == HOST.encode('ascii') for seq in sequences)
    q1 = math.exp(-sum((count/n)*math.log(count/n) for count in abundance.values())) if n else 0.0
    values: dict[str, Any] = {'births': n, 'exact_births': exact, 'exact_fraction': exact/n if n else 0,
        'noncanonical_births': n-exact, 'noncanonical_fraction': (n-exact)/n if n else 0,
        'unique_sequences': len(abundance), 'hill_q0': len(abundance), 'hill_q1': q1,
        'length_distribution': sorted(map(len, sequences)), 'unique_lengths': len({len(s) for s in sequences}),
        'length_counts': {str(k): v for k, v in sorted(Counter(map(len, sequences)).items())},
        'sequence_abundances': [{'length': length, 'visible_hex': seq.hex().upper(), 'count': count}
                               for (length, seq), count in sorted(abundance.items())]}
    return {f'{prefix}_{k}': v for k, v in values.items()}


def sequence_endpoints(summary: dict[str, Any]) -> dict[str, Any]:
    edges = summary['source_edges']
    productive = {e['child']: h1.visible(bytes.fromhex(e['birth_buffer_hex'])) for e in edges
                  if e['productive'] and not e['whole_transfer'] and not e['orphan_source']}
    renewals = summary['renewals']
    require(len(productive) == sum(e['productive'] and not e['whole_transfer'] and not e['orphan_source'] for e in edges), 'duplicate productive child')
    require(len({r['id'] for r in renewals}) == len(renewals) and all(r['id'] in productive for r in renewals), 'renewal productive birth filtering')
    retentions = sorted(r['retention'] for r in renewals)
    return {**sequence_metrics(list(productive.values()), 'productive'),
            **sequence_metrics([productive[r['id']] for r in renewals], 'renewing'),
            'retention_distribution': retentions,
            'retention_median': median(retentions) if retentions else None,
            'retention_minimum': min(retentions) if retentions else None,
            'retention_exact_fraction': sum(r == 1 for r in retentions)/len(retentions) if retentions else 0,
            'excluded_sequence_births': {key: [e for e in edges if predicate(e)] for key, predicate in (
                ('whole_parent_transfers', lambda e: e['whole_transfer']),
                ('orphan_source_events', lambda e: e['orphan_source']),
                ('nonproductive_births', lambda e: not e['productive'] and not e['whole_transfer']))}}


def analyze_run(directory: Path, expected: list[dict[str, Any]], *, exit_status: int = 0) -> dict[str, Any]:
    summary = h1.analyze_run(directory, expected, exit_status=exit_status)
    return {**summary, **sequence_endpoints(summary)}


def renewal(summary: dict[str, Any] | None) -> dict[str, Any]:
    components = {k: summary is not None and summary[k] >= t for k, t in zip(h1.ENDPOINTS, h1.THRESHOLDS, strict=True)}
    return {'components': components, 'core': all(components[k] for k in h1.ENDPOINTS[:5]),
            'continuity': all(components.values())}


def comparison(native: Any, zero: Any) -> dict[str, Any]:
    if native is None or zero is None:
        return {'difference': None, 'direction': 'missing'}
    difference = native - zero
    return {'difference': difference, 'direction': 'native_greater' if difference > 0 else 'zero_greater' if difference < 0 else 'tie'}


def outcomes(results: list[dict[str, Any]], failures: list[dict[str, Any]], *, mechanics: bool = True) -> dict[str, Any]:
    by_run = {(r['condition'], r['seed']): r for r in results}
    integrity = mechanics and not failures and len(results) == len(by_run) == 40 and set(by_run) == set(MATRIX)
    pairs = []
    for seed in SEEDS:
        native, zero = (by_run.get((arm, seed)) for arm in ARMS)
        comparisons = {k: comparison(native[k] if native else None, zero[k] if zero else None) for k in SCALARS}
        # Distribution endpoints are compared at every observed support value.
        distributions = {}
        for key in ('productive_length_counts', 'renewing_length_counts', 'productive_sequence_abundances', 'renewing_sequence_abundances', 'retention_distribution'):
            def distribution(row: dict[str, Any] | None) -> dict[str, int]:
                if row is None: return {}
                if key.endswith('length_counts'): return dict(row[key])
                if key.endswith('sequence_abundances'):
                    return {f"{v['length']}:{v['visible_hex']}": v['count'] for v in row[key]}
                return dict(Counter(str(v) for v in row[key]))
            n, z = distribution(native), distribution(zero)
            distributions[key] = {v: comparison(n.get(v, 0), z.get(v, 0)) if native and zero else comparison(None, None) for v in sorted(n.keys() | z.keys())}
        nr, zr = renewal(native), renewal(zero)
        pairs.append({'seed': seed, 'native': nr, 'zero': zr, 'comparisons': comparisons,
                      'distribution_comparisons': distributions,
                      'discordant_core': nr['core'] != zr['core'], 'discordant_continuity': nr['continuity'] != zr['continuity'],
                      'divergence': all(comparisons[k]['direction'] == 'native_greater' for k in ('productive_unique_sequences', 'productive_noncanonical_fraction'))})
    arms = {arm: {'core_count': sum(p[name]['core'] for p in pairs), 'continuity_count': sum(p[name]['continuity'] for p in pairs),
                  'viable': sum(p[name]['continuity'] for p in pairs) >= 16,
                  'totals': {k: sum(r[k] for r in results if r['condition'] == arm) for k in COUNTS}}
            for arm, name in zip(ARMS, ('native', 'zero'), strict=True)}
    nv, zv = (arms[arm]['viable'] for arm in ARMS)
    divergence_count = sum(p['divergence'] for p in pairs)
    divergence = divergence_count >= 16
    decision = ('unevaluable' if not integrity else 'both viable, divergence detected' if nv and zv and divergence else
                'both viable, divergence not detected' if nv and zv else 'native only viable' if nv else
                'ZERO only viable' if zv else 'neither viable')
    interpretation = {
        'both viable, divergence detected': 'Mutation causally increases realized sequence divergence; ZERO independently demonstrates native mutation is not required for robust renewal under these conditions. Birth-boundary factorial eligible. No equivalence claim.',
        'both viable, divergence not detected': 'Both settings independently attain robust renewal; native mutation is not required under the tested ZERO arm. Realized sequence-divergence effect unsupported. Birth-boundary factorial eligible; no equivalent-performance claim.',
        'native only viable': 'NATIVE attains operational viability and ZERO does not. Threshold crossing alone proves neither mutation-supported renewal nor necessity. Birth-boundary factorial not eligible.',
        'ZERO only viable': 'ZERO attains operational viability and NATIVE does not, demonstrating renewal without native mutation. Threshold crossing alone does not prove mutation suppression. Birth-boundary factorial not eligible.',
        'neither viable': 'Valid renewal-baseline failure; stop the continuation.',
        'unevaluable': 'Integrity/configuration failure is not biological evidence. Repair only implementation/artifact defects and rerun the unchanged complete matrix.',
    }[decision]
    def aggregate(values: list[dict[str, Any]]) -> dict[str, Any]:
        differences = [v['difference'] for v in values if v['difference'] is not None]
        return {'direction_counts': dict(Counter(v['direction'] for v in values)),
                'median_difference': median(differences) if differences else None,
                'pair_denominator': 20, 'observed_pairs': len(differences)}
    distribution_aggregates = {}
    for key in pairs[0]['distribution_comparisons']:
        support = sorted({v for p in pairs for v in p['distribution_comparisons'][key]})
        distribution_aggregates[key] = {v: aggregate([p['distribution_comparisons'][key].get(v, comparison(0, 0) if ('NATIVE', p['seed']) in by_run and ('ZERO', p['seed']) in by_run else comparison(None, None)) for p in pairs]) for v in support}
    return {'decision': decision, 'interpretation': interpretation, 'integrity': integrity, 'mechanics': mechanics, 'arms': arms,
            'realized_divergence': divergence, 'divergence_pairs': divergence_count,
            'birth_boundary_factorial_eligible': integrity and nv and zv,
            'run_denominator': 40, 'paired_denominator': 20, 'arm_denominator': 20,
            'pairs': pairs, 'discordant_pairs': [p['seed'] for p in pairs if p['discordant_core'] or p['discordant_continuity']],
            'paired_summary': {k: aggregate([p['comparisons'][k] for p in pairs]) for k in SCALARS},
            'paired_distribution_summary': distribution_aggregates, 'runs': results, 'failures': failures,
            'descriptive_coin_tail_fraction': '6196/1048576', 'descriptive_coin_tail': 6196/1048576,
            'inference_limits': 'Total effect of MUTATE only; no counted mutation events, adaptation, variant fitness, equivalence, or necessity from a threshold crossing. Both viable demonstrates renewal without native mutation; divergence requires the same 16 pairs.'}

def analyze_campaign(manifest: Path) -> dict[str, Any]:
    from experiments.stringmol import mutation_workflow as w
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    try:
        data = w.verify_preparation(manifest)
        w.verify_launch(manifest)
        require(w.read(manifest.parent / 'campaign.json') == {'input_manifest': w.record(manifest), 'workers': 6, 'launch_record': w.record(manifest.parent / 'launch.json')}, 'campaign identity')
        receipts = w.read(manifest.parent / 'campaign-results.json')
        require(len(receipts) == 40, 'incomplete campaign')
    except (ValueError, OSError, KeyError, TypeError, csv.Error, subprocess.CalledProcessError) as exc:
        return outcomes([], [{'error': str(exc)}], mechanics=False)
    for r, receipt in zip(data['runs'], receipts, strict=True):
        try:
            directory = Path(r['directory'])
            require(receipt == w.read(directory.with_suffix('.inventory.json')) and receipt['input_manifest'] == w.record(manifest), 'run receipt')
            require(receipt['condition'] == r['condition'] and receipt['seed'] == r['seed'] and receipt['files'] == w.inventory(directory), 'output identity/inventory')
            summary = analyze_run(directory, r['expected_initial'], exit_status=receipt['exit_status'])
            require(set(receipt['files']) == decay.output_names(summary['end_timestep']), 'scientific output filename set')
            results.append({'condition': r['condition'], 'seed': r['seed'], **summary})
        except (ValueError, OSError, KeyError, TypeError, csv.Error, subprocess.CalledProcessError) as exc:
            failures.append({'condition': r['condition'], 'seed': r['seed'], 'error': str(exc)})
    return outcomes(results, failures)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    print(json.dumps(analyze_campaign(parser.parse_args().manifest.resolve()), indent=2, sort_keys=True))
