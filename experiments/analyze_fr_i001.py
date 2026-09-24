"""Strict FR-I001 trial classification, calibration and held-out reporting."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from experiments.fr_i001_provenance import score_reference

THRESHOLDS = (0.125, 0.25, 0.5, 0.75)
ARMS = ('original', 'shuffled', 'random')
CAVEAT = (
    'Nominal 95% Wilson intervals describe trial-level rates. The 65 trials are clustered '
    'within five selected score-64 parents and do not provide population-level independent '
    'uncertainty. Held out only from FR-I001 calibration, not prior score-64 selection. '
    'The deterministic repeat is a reproducibility check, not fresh confirmation. '
    'Score 64 is a stable-position proxy, not whole-tape agreement or proof that inherited '
    'bytes cause the phenotype. Value-change provenance excludes instruction, address and '
    'control dependencies; it is not complete informational dependence, conserved material '
    'or biological parenthood. A pass makes no persistence, heredity, organism, adaptation, '
    'ecology or organization claim.'
)


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    with path.open('x') as handle:
        json.dump(value, handle, sort_keys=True, separators=(',', ':'), allow_nan=False)
        handle.write('\n')
        handle.flush()
        import os
        os.fsync(handle.fileno())


def wilson(hits: int, total: int) -> list[float]:
    if not 0 <= hits <= total or total <= 0:
        raise ValueError('invalid binomial counts')
    z = 1.959963984540054
    p = hits / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def validate(rows: list[dict[str, Any]], indices: range) -> None:
    expected = {(w, a, t, i) for w in indices for a in ARMS for t in range(13) for i in range(2)}
    seen = set()
    for row in rows:
        key = (row['witness'], row['arm'], row['trial'], row['tape_index'])
        if key not in expected or key in seen:
            raise ValueError('unexpected or duplicate observation')
        seen.add(key)
        tape = bytes.fromhex(row['tape_hex'])
        labels = bytes.fromhex(row['labels_hex'])
        if len(tape) != 64 or len(labels) != 64 or any(v not in (0, 1) for v in labels):
            raise ValueError('invalid tape or provenance labels')
        if type(row['score']) is not int or not 0 <= row['score'] <= 64:
            raise ValueError('invalid score')
        if row['provenance_fraction'] != sum(labels) / 64:
            raise ValueError('provenance fraction mismatch')
        seed = 0xAC007 + row['witness'] * 1000 + row['trial'] * 2 + row['tape_index']
        if row['assessment_seed'] != seed:
            raise ValueError('assessment seed mismatch')
    if seen != expected:
        raise ValueError('incomplete observation matrix')


def candidate(row: dict[str, Any], threshold: float) -> bool:
    return bool(row['score'] == 64 and row['provenance_fraction'] >= threshold)


def counts(rows: list[dict[str, Any]], threshold: float) -> dict[str, int]:
    return {arm: len({(r['witness'], r['trial']) for r in rows
                      if r['arm'] == arm and candidate(r, threshold)}) for arm in ARMS}


def calibrate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    validate(rows, range(5))
    metrics = []
    for threshold in THRESHOLDS:
        hits = counts(rows, threshold)
        sensitivity = hits['original'] / 65
        fpr = (hits['shuffled'] + hits['random']) / 130
        metrics.append({'threshold': threshold, 'detections': hits, 'sensitivity': sensitivity,
                        'false_positive_rate': fpr, 'objective': sensitivity - fpr,
                        'sensitivity_wilson_95': wilson(hits['original'], 65),
                        'false_positive_wilson_95': wilson(hits['shuffled'] + hits['random'], 130),
                        'integer_objective': 2 * hits['original'] - hits['shuffled'] - hits['random']})
    selected = max(metrics, key=lambda m: (m['integer_objective'], m['threshold']))
    return {'selected_threshold': selected['threshold'], 'development_metrics': metrics}


def summarize(rows: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    def group(part: list[dict[str, Any]]) -> dict[str, Any]:
        hits = counts(part, threshold)
        n = len({(r['witness'], r['trial']) for r in part})
        return {arm: {'detections': hits[arm], 'trials': n, 'rate': hits[arm] / n,
                      'wilson_95': wilson(hits[arm], n),
                      'score_distribution': dict(sorted(Counter(r['score'] for r in part if r['arm'] == arm).items())),
                      'provenance_distribution': dict(sorted(Counter(r['provenance_fraction'] for r in part if r['arm'] == arm).items()))}
                for arm in ARMS}
    return {'pooled': group(rows), 'per_witness': {
        str(w): group([r for r in rows if r['witness'] == w]) for w in sorted({r['witness'] for r in rows})}}


def analyze(root: Path) -> dict[str, Any]:
    from experiments.run_fr_i001 import implementation_hashes

    repeats = []
    for repeat in range(2):
        directory = root / f'repeat_{repeat}'
        calibration = json.loads((directory / 'calibration.json').read_text())
        if calibration['implementation'] != implementation_hashes():
            raise ValueError('frozen implementation differs from analyzer implementation')
        development = json.loads((directory / 'development.json').read_text())
        heldout = json.loads((directory / 'heldout.json').read_text())
        seal = json.loads((directory / 'completion.json').read_text())
        if seal != {'calibration_sha256': digest(calibration), 'heldout_sha256': digest(heldout)}:
            raise ValueError('artifact digest defect')
        if calibration['development_sha256'] != digest(development):
            raise ValueError('development digest defect')
        if calibration['selection'] != calibrate(development):
            raise ValueError('development threshold selection defect')
        validate(heldout, range(5, 10))
        if calibration['parity'] != {'random_cases': 1000, 'directed_cases': 84, 'label_cases': 13}:
            raise ValueError('parity evidence defect')
        threshold = calibration['selection']['selected_threshold']
        # Independent re-assessment of every classified final tape.
        for row in development + heldout:
            if candidate(row, threshold):
                tape = np.frombuffer(bytes.fromhex(row['tape_hex']), dtype=np.uint8).copy()
                if score_reference(tape, row['assessment_seed']) != 64 or sum(bytes.fromhex(row['labels_hex'])) < threshold * 64:
                    raise ValueError('classified tape independent verification defect')
        repeats.append((calibration, development, heldout))
    deterministic = repeats[0] == repeats[1]
    calibration, development, heldout = repeats[0]
    threshold = calibration['selection']['selected_threshold']
    hits = counts(heldout, threshold)
    gates = {'parity': True, 'original': hits['original'] >= 52, 'shuffled': hits['shuffled'] <= 3,
             'random': hits['random'] <= 1, 'deterministic': deterministic, 'classified_tapes': True}
    decision = 'PASS' if all(gates.values()) else ('FAIL' if deterministic else 'UNEVALUABLE IMPLEMENTATION DEFECT')
    return {'campaign': 'FR-I001', 'decision': decision, 'gates': gates,
            'selected_threshold': threshold, 'heldout': summarize(heldout, threshold),
            'development': summarize(development, threshold), 'caveat': CAVEAT,
            'next_action': ('Eligible for separately implemented conserved-kernel mechanics parity; not implemented here.'
                            if decision == 'PASS' else 'Stop BFF lineage, persistence, maintenance and ecology experiments; pivot to explicit birth and lineage identity.'
                            if decision == 'FAIL' else 'Repair only parity, determinism or artifact defects and rerun the frozen gate.')}


def write_report(root: Path) -> dict[str, Any]:
    result = analyze(root)
    write_json(root / 'decision.json', result)
    with (root / 'report.md').open('x') as handle:
        handle.write(f"# FR-I001\n\n{result['decision']}; selected threshold {result['selected_threshold']}.\n\n")
        for arm, stats in result['heldout']['pooled'].items():
            handle.write(f"- {arm}: {stats['detections']}/65; nominal 95% Wilson {stats['wilson_95']}.\n")
        handle.write('\n' + CAVEAT + '\n\n' + result['next_action'] + '\n')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    result = write_report(args.root)
    print(json.dumps({key: result[key] for key in ('decision', 'selected_threshold', 'gates')}, sort_keys=True))


if __name__ == '__main__':
    main()
