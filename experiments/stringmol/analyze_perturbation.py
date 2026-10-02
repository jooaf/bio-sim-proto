"""SM-H002 material-source cohorts over the unchanged, independent H001 replay."""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path
from typing import Any

from experiments.stringmol import analyze_renewal as h, analyze_decay as d
from experiments.stringmol.analyze_lineage import require
from experiments.stringmol.configure_control import HOST

ARMS = ('EXACT_SELF', 'SHUFFLE_SELF', 'EXACT_SUPPORT', 'SHUFFLE_SUPPORT')
MATRIX = [(arm, 202624000 + i) for i in range(15) for arm in ARMS]
LIVENESS = {'productive_source_births': 100, 'serial_source_births': 25,
            'max_source_depth': 2, 'late_productive_source_births': 50,
            'late_renewing_descendants': 5}


def cohorts(summary: dict[str, Any], initial: dict[int, str]) -> dict[str, Any]:
    """Assign every successful transfer from its inferred source, never its role.

    Qualifying depth and renewal remain exactly the H001 replay's definitions.
    Whole transfers carry cohort but do not restart a qualifying source lineage.
    """
    history = {r['id']: r for r in summary['identity_history']}
    require(len(history) == len(summary['identity_history']), 'duplicate cohort identity')
    require(set(initial) == {i for i, r in history.items() if r['origin'] == 'initial'}, 'unknown initial cohort')
    require(set(initial.values()) <= {'candidate', 'support'}, 'unknown cohort')
    assigned = initial.copy()
    edges = summary['source_edges']
    last_index = 0
    for e in edges:
        require(0 <= e['tick'] < 5000 and e['index'] > last_index, 'cohort event order/bounds')
        last_index = e['index']
        require(e['source'] in assigned and all(i in assigned for i in e['participants']), 'unknown source/partner cohort')
        require(e['child'] not in assigned and e['child'] in history, 'conflicting cohort')
        require(history[e['child']]['birth_tick'] == e['tick'], 'cohort birth history')
        assigned[e['child']] = assigned[e['source']]
    require(set(assigned) == set(history), 'incomplete cohort identity history')
    result: dict[str, Any] = {}
    surviving = set(summary['end_surviving_descendants'])
    for cohort in ('candidate', 'support'):
        selected = [e for e in edges if assigned[e['source']] == cohort]
        renewals = [r for r in summary['renewals'] if assigned[r['id']] == cohort]
        ids = {i for i, value in assigned.items() if value == cohort}
        partner_roles: Counter[str] = Counter()
        for e in selected:
            other = next(i for i in e['participants'] if i != e['source'])
            partner_roles[f"source_{e['source_role']}:partner_{assigned[other]}"] += 1
        result[cohort] = {
            'productive_source_births': sum(e['productive'] for e in selected),
            'late_productive_source_births': sum(e['productive'] and 2500 <= e['tick'] < 5000 for e in selected),
            'renewing_descendants': len(renewals),
            'serial_source_births': sum(e['productive'] and e['source_depth'] is not None and e['source_depth'] >= 1 for e in selected),
            'max_source_depth': max((history[i]['source_depth'] for i in ids if history[i]['source_depth'] is not None), default=0),
            'late_renewing_descendants': sum(2500 <= r['birth_tick'] < 5000 for r in renewals),
            'retained_late_renewals': sum(r['retained_late'] for r in renewals),
            'renewals': renewals,
            'retention_distribution': sorted(r['retention'] for r in renewals),
            'end_surviving_descendants': sorted(ids & surviving),
            'survival': [history[i] for i in sorted(ids)],
            'partner_roles': dict(partner_roles),
            'whole_parent_transfers': sum(e['whole_transfer'] for e in selected),
            'orphan_source_productive_births': sum(e['orphan_source'] for e in selected),
            'other_nonproductive_births': sum(not e['productive'] and not e['whole_transfer'] for e in selected),
        }
    return {'cohorts': result, 'material_source_cohort': {str(i): value for i, value in sorted(assigned.items())}}


def analyze_run(directory: Path, expected: list[dict[str, Any]], initial_cohorts: dict[int, str], *, exit_status: int = 0) -> dict[str, Any]:
    summary = h.analyze_run(directory, expected, exit_status=exit_status)
    return {**summary, **cohorts(summary, initial_cohorts)}


def liveness(metrics: dict[str, Any]) -> bool:
    return all(metrics[k] >= v for k, v in LIVENESS.items())


def specificity(exact: dict[str, Any], shuffle: dict[str, Any]) -> dict[str, Any]:
    differences = {k: exact[k] - shuffle[k] for k in LIVENESS}
    checks = {'productive_margin': differences['productive_source_births'] >= 100,
              'productive_ratio': exact['productive_source_births'] > 0 and exact['productive_source_births'] >= 2 * shuffle['productive_source_births'],
              'late_margin': differences['late_productive_source_births'] >= 50,
              'serial_margin': differences['serial_source_births'] >= 25,
              'exact_liveness': liveness(exact)}
    return {'exact': exact, 'shuffle': shuffle, 'differences': differences,
            'components': checks, 'passes': all(checks.values())}


def outcomes(results: list[dict[str, Any]], failures: list[dict[str, Any]], panel: list[dict[str, Any]], *, mechanics: bool = True) -> dict[str, Any]:
    by_run = {(r['condition'], r['seed']): r for r in results}
    integrity = mechanics and not failures and len(results) == len(by_run) == 60 and set(by_run) == set(MATRIX)
    require(len(panel) == 15 and [p['rank'] for p in panel] == list(range(15)), 'decision panel')
    rows = []
    for p in panel:
        contexts = {}
        for context in ('SELF', 'SUPPORT'):
            exact = by_run.get(('EXACT_' + context, 202624000 + p['rank']))
            shuffled = by_run.get(('SHUFFLE_' + context, 202624000 + p['rank']))
            contexts[context] = specificity(exact['cohorts']['candidate'], shuffled['cohorts']['candidate']) if exact and shuffled else None
        rows.append({'genotype': p, 'contexts': contexts})
    canonical = [r for r in rows if r['genotype']['sequence_hex'] == HOST.encode().hex().upper()]
    control = integrity and len(canonical) == 1 and all(canonical[0]['contexts'][ctx] is not None and canonical[0]['contexts'][ctx]['components']['exact_liveness'] for ctx in ('SELF', 'SUPPORT'))
    sets = {ctx: [r['genotype']['rank'] for r in rows if r['contexts'][ctx] and r['contexts'][ctx]['passes']] for ctx in ('SELF', 'SUPPORT')}
    overlap = sorted(set(sets['SELF']) & set(sets['SUPPORT']))
    self_ok, support_ok, general = len(sets['SELF']) >= 12, len(sets['SUPPORT']) >= 12, len(overlap) >= 12
    decision = ('unevaluable' if not integrity or not control else 'context-general pass' if general else
                'dual-context screen pass with insufficient overlap' if self_ok and support_ok else
                'supported-context-only screen pass' if support_ok else 'self-context-only screen pass' if self_ok else 'valid failure')
    return {'decision': decision, 'integrity': integrity, 'mechanics': mechanics, 'canonical_positive_control': control,
            'self_specific': self_ok, 'support_specific': support_ok, 'context_general': general,
            'passing_genotypes': sets, 'shared_passing_genotypes': overlap, 'run_denominator': 60,
            'genotype_denominator_per_context': 15, 'genotypes': rows, 'runs': results, 'failures': failures,
            'strata': {'canonical': [r for r in rows if r in canonical], 'noncanonical': [r for r in rows if r not in canonical]},
            'descriptive_coin_tail_fraction': '576/32768', 'descriptive_coin_tail': 576 / 32768}


def analyze_campaign(manifest: Path) -> dict[str, Any]:
    from experiments.stringmol import perturbation_workflow as w
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    # A malformed panel is an integrity failure, never an alternative denominator.
    try:
        data = w.verify_preparation(manifest)
        panel = data['panel']
        w.verify_launch(manifest)
        require(w.read(manifest.parent/'campaign.json') == {'input_manifest': w.record(manifest), 'workers': 6, 'launch_record': w.record(manifest.parent/'launch.json')}, 'campaign identity')
        receipts = w.read(manifest.parent/'campaign-results.json')
        require(len(receipts) == 60, 'incomplete campaign')
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        return {'decision': 'unevaluable', 'integrity': False, 'run_denominator': 60, 'genotype_denominator_per_context': 15, 'failures': [{'error': str(exc)}]}
    for r, receipt in zip(data['runs'], receipts, strict=True):
        try:
            directory = Path(r['directory'])
            require(receipt == w.read(directory.with_suffix('.inventory.json')) and receipt['input_manifest'] == w.record(manifest), 'run receipt')
            require(receipt['condition'] == r['condition'] and receipt['seed'] == r['seed'] and receipt['files'] == w.inventory(directory), 'output identity/inventory')
            summary = analyze_run(directory, r['expected_initial'], {int(i): v for i, v in r['initial_cohorts'].items()}, exit_status=receipt['exit_status'])
            require(set(receipt['files']) == d.output_names(summary['end_timestep']), 'scientific output filename set')
            results.append({'condition': r['condition'], 'seed': r['seed'], **summary})
        except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
            failures.append({'condition': r['condition'], 'seed': r['seed'], 'error': str(exc)})
    return outcomes(results, failures, panel)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    print(json.dumps(analyze_campaign(parser.parse_args().manifest.resolve()), indent=2, sort_keys=True))
