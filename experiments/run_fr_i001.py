"""Run the frozen FR-I001 mechanics gate in two complete deterministic repeats.

Example:
  NUMBA_NUM_THREADS=1 uv run python -m experiments.run_fr_i001 \
    --source-root /path/to/p005 --p006-preparation /path/to/preparation.json \
    --output-dir runs/fr_i001

Only the ten first-origin P005 checkpoints and P006 preparation are accessed.
Each repeat saves development observations and a durable calibration artifact
before executing any held-out propagation. Output directories must be new.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from experiments import analyze_ac_p003_functional_origin_convergence as source
from experiments.analyze_fr_i001 import ARMS, calibrate, digest, write_json, write_report
from experiments.fr_i001_provenance import (
    U8, parity_gate, propagate, random_parent, score_reference, trial_noise,
)
from experiments.phase1_probe import file_sha256
from experiments.run_ac_p006_transplant import SOURCE_SEEDS, shuffled_control

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'reports/fr_i001_functional_descendant_representation_preregistration.md'
FROZEN_FILES = (
    PROTOCOL, 'experiments/fr_i001_provenance.py', 'experiments/run_fr_i001.py',
    'experiments/analyze_fr_i001.py', 'experiments/paper_probe.py',
    'experiments/run_ac_p006_transplant.py',
    'experiments/analyze_ac_p003_functional_origin_convergence.py',
    'experiments/analyze_ac_p001_high_resource_origin_viability.py',
    'experiments/phase1_probe.py', 'tests/test_fr_i001.py',
)


def implementation_hashes() -> dict[str, str]:
    return {name: file_sha256(ROOT / name) for name in FROZEN_FILES}


def load_sources(source_root: Path, preparation_path: Path) -> tuple[list[dict[str, U8]], list[dict[str, Any]]]:
    preparation = json.loads(preparation_path.read_text())
    pairs = preparation.get('pairs', [])
    if preparation.get('campaign') != 'AC-P006' or len(pairs) != 10:
        raise ValueError('expected frozen ten-pair P006 preparation')
    parents, evidence = [], []
    for w, seed in enumerate(SOURCE_SEEDS):
        pair = pairs[w]
        if pair['index'] != w or pair['source_seed'] != seed:
            raise ValueError('frozen source order mismatch')
        run = source.Run('AC-P005', 16, seed)
        checkpoint = source.load_checkpoint(source_root / (run.name + '_prectrlv1'), run)
        witness = checkpoint.witness.copy()
        shuffle = np.frombuffer(bytes.fromhex(pair['arms']['shuffle']['target_hex']), dtype=np.uint8).copy()
        if (pair['source_checksums'] != checkpoint.checksums or pair['source_epoch'] != checkpoint.epoch
                or pair['witness_rank'] != checkpoint.witness_rank or pair['witness_score'] != 64
                or pair['arms']['witness']['target_hex'] != witness.tobytes().hex()
                or not np.array_equal(shuffle, shuffled_control(witness, w))):
            raise ValueError('frozen P005 witness or P006 shuffle mismatch')
        control_score = score_reference(shuffle, 0)
        if not 0 <= control_score < 64 or pair['control_score'] != control_score:
            raise ValueError('frozen shuffle score mismatch')
        parents.append({'original': witness, 'shuffled': shuffle, 'random': random_parent(w)})
        evidence.append({'index': w, 'source_seed': seed, 'checksums': checkpoint.checksums,
                         'epoch': checkpoint.epoch, 'rank': checkpoint.witness_rank,
                         'parents': {arm: tape.tobytes().hex() for arm, tape in parents[-1].items()},
                         'p006_preparation_sha256': file_sha256(preparation_path)})
    return parents, evidence


def observe(parents: list[dict[str, U8]], indices: range) -> list[dict[str, Any]]:
    rows = []
    for w in indices:
        for arm in ARMS:
            for t in range(13):
                tapes, labels = propagate(parents[w][arm], trial_noise(w, t))
                for i in range(2):
                    seed = 0xAC007 + w * 1000 + t * 2 + i
                    rows.append({'witness': w, 'arm': arm, 'trial': t, 'tape_index': i,
                                 'assessment_seed': seed, 'score': score_reference(tapes[i], seed),
                                 'provenance_fraction': int(labels[i].sum()) / 64,
                                 'tape_hex': tapes[i].tobytes().hex(),
                                 'labels_hex': labels[i].tobytes().hex()})
    return rows


def run_gate(source_root: Path, preparation: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    frozen = implementation_hashes()
    for repeat in range(2):
        directory = output / f'repeat_{repeat}'
        directory.mkdir()
        parity = parity_gate()
        parents, sources = load_sources(source_root, preparation)
        development = observe(parents, range(5))
        calibration = {'campaign': 'FR-I001', 'implementation': frozen, 'sources': sources,
                       'parity': parity, 'selection': calibrate(development),
                       'development_sha256': digest(development)}
        if implementation_hashes() != frozen:
            raise ValueError('implementation changed before calibration freeze')
        write_json(directory / 'development.json', development)
        write_json(directory / 'calibration.json', calibration)
        # Read the durable artifact back before the first held-out assay call.
        saved = json.loads((directory / 'calibration.json').read_text())
        if saved != calibration or implementation_hashes() != frozen:
            raise ValueError('calibration freeze defect')
        heldout = observe(parents, range(5, 10))
        if (implementation_hashes() != frozen
                or json.loads((directory / 'calibration.json').read_text()) != saved):
            raise ValueError('frozen implementation/calibration changed after unblinding')
        write_json(directory / 'heldout.json', heldout)
        write_json(directory / 'completion.json', {'calibration_sha256': digest(saved),
                                                  'heldout_sha256': digest(heldout)})
    return write_report(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--p006-preparation', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    result = run_gate(args.source_root, args.p006_preparation, args.output_dir)
    print(json.dumps({'decision': result['decision'], 'selected_threshold': result['selected_threshold'],
                      'gates': result['gates']}, sort_keys=True))


if __name__ == '__main__':
    main()
