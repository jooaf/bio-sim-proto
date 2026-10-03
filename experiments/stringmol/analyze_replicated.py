"""SM-H003 replicated supported sequence order; unchanged H002 event replay."""
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path
from typing import Any

from experiments.stringmol import analyze_perturbation as h2, analyze_decay as decay
from experiments.stringmol.analyze_lineage import require

ARMS = ('EXACT_SUPPORT', 'SHUFFLE_SUPPORT')
SEEDS = list(range(202625000, 202625045))
MATRIX = [(arm, seed) for seed in SEEDS for arm in ARMS]
CANONICAL_SHA256 = '94f8c51cef8ef18d4246fb1fc6030b20f887bb0e265be59b3949be2bb69b89c5'
CONTROL = {'productive_source_births': 100, 'renewing_descendants': 10,
           'serial_source_births': 50, 'max_source_depth': 2, 'late_renewing_descendants': 5}
# Counts may be pooled across independent replicates; depth is reported separately.
COUNTS = ('productive_source_births', 'late_productive_source_births', 'renewing_descendants',
          'serial_source_births', 'late_renewing_descendants', 'retained_late_renewals',
          'whole_parent_transfers', 'orphan_source_productive_births', 'other_nonproductive_births')
analyze_run = h2.analyze_run


def control(summary: dict[str, Any]) -> dict[str, Any]:
    """The native replay already describes the union of all 140 founders."""
    components = {key: summary[key] >= threshold for key, threshold in CONTROL.items()}
    return {'metrics': {key: summary[key] for key in CONTROL},
            'components': components, 'passes': all(components.values())}


def aggregate(pairs: list[dict[str, Any] | None]) -> dict[str, Any]:
    require(len(pairs) == 3, 'three paired replicates required')
    passing = [j for j, pair in enumerate(pairs) if pair is not None and pair['passes']]
    direction = [pair is not None and pair['differences']['productive_source_births'] > 0 for pair in pairs]
    pooled = {arm: {k: sum(pair[arm][k] for pair in pairs if pair is not None) for k in COUNTS}
              for arm in ('exact', 'shuffle')}
    return {'replicates': pairs, 'specific_replicates': passing, 'productive_direction': direction,
            'same_two_of_three': len(passing) >= 2, 'all_three_direction': all(direction),
            'replicated_specificity': len(passing) >= 2 and all(direction),
            'pooled_totals': pooled,
            'pooled_differences': {k: pooled['exact'][k] - pooled['shuffle'][k] for k in COUNTS},
            'complete_pairs': sum(pair is not None for pair in pairs)}


def outcomes(results: list[dict[str, Any]], failures: list[dict[str, Any]], panel: list[dict[str, Any]], *, mechanics: bool = True) -> dict[str, Any]:
    from experiments.stringmol.replicated_workflow import verify_panel
    verify_panel(panel)
    by_run = {(r['condition'], r['seed']): r for r in results}
    integrity = mechanics and not failures and len(results) == len(by_run) == 90 and set(by_run) == set(MATRIX)
    rows = []
    canonical_replicates = []
    for candidate in panel:
        rank = candidate['rank']
        pairs = []
        for j in range(3):
            seed = 202625000 + 3 * rank + j
            exact, shuffled = (by_run.get((arm, seed)) for arm in ARMS)
            pair = h2.specificity(exact['cohorts']['candidate'], shuffled['cohorts']['candidate']) if exact and shuffled else None
            if pair is not None:
                pair.update(seed=seed, replicate=j)
                pair['differences'].update({k: pair['exact'][k] - pair['shuffle'][k] for k in COUNTS})
            pairs.append(pair)
            if candidate['sha256'] == CANONICAL_SHA256:
                canonical_replicates.append({'seed': seed, 'replicate': j, 'whole_population': control(exact) if exact else None})
        rows.append({'genotype': candidate, **aggregate(pairs)})
    canonical_ok = sum(r['whole_population'] is not None and r['whole_population']['passes'] for r in canonical_replicates) >= 2
    passing = [r['genotype']['rank'] for r in rows if r['genotype']['sha256'] != CANONICAL_SHA256 and r['replicated_specificity']]
    return {'decision': 'unevaluable' if not integrity or not canonical_ok else 'pass' if len(passing) >= 12 else 'valid non-pass',
            'integrity': integrity, 'mechanics': mechanics, 'canonical_positive_control': canonical_ok,
            'canonical_replicates': canonical_replicates, 'replicated_panel': len(passing),
            'passing_genotypes': passing, 'run_denominator': 90, 'paired_block_denominator': 45,
            'genotype_denominator': 14, 'genotypes': rows, 'runs': results, 'failures': failures,
            'descriptive_coin_tail_fraction': '106/16384', 'descriptive_coin_tail': 106 / 16384}


def analyze_campaign(manifest: Path) -> dict[str, Any]:
    from experiments.stringmol import replicated_workflow as w
    failures: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    try:
        data = w.verify_preparation(manifest)
        w.verify_launch(manifest)
        require(w.read(manifest.parent/'campaign.json') == {'input_manifest': w.record(manifest), 'workers': 6, 'launch_record': w.record(manifest.parent/'launch.json')}, 'campaign identity')
        receipts = w.read(manifest.parent/'campaign-results.json')
        require(len(receipts) == 90, 'incomplete campaign')
    except (ValueError, OSError, KeyError, TypeError, csv.Error, subprocess.CalledProcessError) as exc:
        return {'decision': 'unevaluable', 'integrity': False, 'run_denominator': 90, 'genotype_denominator': 14, 'failures': [{'error': str(exc)}]}
    for r, receipt in zip(data['runs'], receipts, strict=True):
        try:
            directory = Path(r['directory'])
            require(receipt == w.read(directory.with_suffix('.inventory.json')) and receipt['input_manifest'] == w.record(manifest), 'run receipt')
            require(receipt['condition'] == r['condition'] and receipt['seed'] == r['seed'] and receipt['files'] == w.inventory(directory), 'output identity/inventory')
            summary = analyze_run(directory, r['expected_initial'], {int(i): v for i, v in r['initial_cohorts'].items()}, exit_status=receipt['exit_status'])
            require(set(receipt['files']) == decay.output_names(summary['end_timestep']), 'scientific output filename set')
            results.append({'condition': r['condition'], 'seed': r['seed'], 'rank': r['rank'], 'replicate': r['replicate'], **summary})
        except (ValueError, OSError, KeyError, TypeError, csv.Error, subprocess.CalledProcessError) as exc:
            failures.append({'condition': r['condition'], 'seed': r['seed'], 'error': str(exc)})
    return outcomes(results, failures, data['panel'])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    print(json.dumps(analyze_campaign(parser.parse_args().manifest.resolve()), indent=2, sort_keys=True))
