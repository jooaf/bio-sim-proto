"""Frozen FR-I001 mechanics, assay isolation and artifact sequencing tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from experiments import analyze_ac_p003_functional_origin_convergence as source
from experiments.run_ac_p006_transplant import SOURCE_SEEDS, shuffled_control
from experiments import analyze_fr_i001 as analysis
from experiments import fr_i001_provenance as provenance
from experiments import run_fr_i001 as runner
from experiments.analyze_ac_p003_functional_origin_convergence import splitmix64


def observations(indices: range) -> list[dict[str, Any]]:
    return [{'witness': w, 'arm': a, 'trial': t, 'tape_index': i,
             'assessment_seed': 0xAC007 + w * 1000 + t * 2 + i,
             'score': 0, 'provenance_fraction': 0.0, 'tape_hex': '00' * 64,
             'labels_hex': '00' * 64}
            for w in indices for a in analysis.ARMS for t in range(13) for i in range(2)]


def test_full_parity_and_directed_labels() -> None:
    assert provenance.parity_gate() == {'random_cases': 1000, 'directed_cases': 84, 'label_cases': 13}


def test_serial_bytes_match_paper() -> None:
    for w in (0, 5, 9):
        parent = provenance.random_parent(w)
        noise = provenance.trial_noise(w, 12)
        reference = np.concatenate((parent, noise))
        provenance.execute_reference(reference, 8192)
        for _ in range(4):
            reference[:64] = reference[64:]
            reference[64:] = noise
            provenance.execute_reference(reference, 8192)
        actual, labels = provenance.propagate(parent, noise)
        assert np.array_equal(actual.ravel(), reference)
        assert set(labels.ravel()) <= {0, 1}
        assert np.array_equal(parent, provenance.random_parent(w))
        assert int(noise[63]) == splitmix64(splitmix64(0xAC007000 + w) ^ splitmix64(13 * 64 + 63)) & 255


def test_assay_budget_transfer_and_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    noise = provenance.trial_noise(5, 0)
    def execute(joint: provenance.U8, labels: provenance.U8, budget: int) -> int:
        assert budget == 8192
        assert np.array_equal(joint[64:], noise)
        assert not labels[64:].any()
        assert np.all(labels[:64] == (1 if not calls else 0))
        calls.append(1)
        return budget
    monkeypatch.setattr(provenance, 'execute_provenance', execute)
    provenance.propagate(provenance.random_parent(5), noise)
    assert len(calls) == 5


def test_threshold_grid_ties_trial_or_and_development_only() -> None:
    rows = observations(range(5))
    assert analysis.calibrate(rows)['selected_threshold'] == 0.75
    for row in rows:
        if row['arm'] == 'original':
            row.update(score=64, provenance_fraction=0.5, labels_hex='01' * 32 + '00' * 32)
    result = analysis.calibrate(rows)
    assert result['selected_threshold'] == 0.5
    assert analysis.counts(rows, 0.5)['original'] == 65  # Not 130 final tapes.
    assert not analysis.candidate(dict(rows[0], score=63), 0.125)
    assert not analysis.candidate(dict(rows[0], provenance_fraction=0.124), 0.125)
    with pytest.raises(ValueError):
        analysis.calibrate(observations(range(5, 10)))
    with pytest.raises(ValueError):
        analysis.calibrate(rows[:-1])
    with pytest.raises(ValueError):
        analysis.calibrate(rows + [rows[0]])


def test_wilson() -> None:
    assert analysis.wilson(0, 65) == pytest.approx([0, 0.05580153132285691])
    assert analysis.wilson(65, 65) == pytest.approx([0.9441984686771431, 1])
    assert analysis.wilson(52, 65) == pytest.approx([0.6872986736183406, 0.879220408], abs=1e-8)


def test_frozen_artifact_precedes_heldout_and_rerun(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / 'gate'
    monkeypatch.setattr(runner, 'load_sources', lambda *_: ([], []))
    monkeypatch.setattr(runner, 'parity_gate', lambda: {'random_cases': 1000, 'directed_cases': 84, 'label_cases': 13})
    calls: list[int] = []
    def observe(parents: Any, indices: range) -> list[dict[str, Any]]:
        repeat = len(calls) // 2
        if indices.start == 5:
            calibration = json.loads((output / f'repeat_{repeat}' / 'calibration.json').read_text())
            assert calibration['selection']['selected_threshold'] == 0.75
            assert calibration['implementation'] == runner.implementation_hashes()
        calls.append(indices.start)
        return observations(indices)
    monkeypatch.setattr(runner, 'observe', observe)
    result = runner.run_gate(tmp_path, tmp_path / 'preparation.json', output)
    assert calls == [0, 5, 0, 5]
    assert result['decision'] == 'FAIL'
    assert result['gates']['deterministic']
    assert not result['gates']['original']
    with pytest.raises(FileExistsError):
        runner.run_gate(tmp_path, tmp_path, output)
    heldout = output / 'repeat_0' / 'heldout.json'
    heldout.write_text('[]')
    with pytest.raises(ValueError, match='digest'):
        analysis.analyze(output)


def test_parity_defect_stops_before_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> dict[str, int]:
        raise ValueError('parity defect')
    monkeypatch.setattr(runner, 'parity_gate', fail)
    monkeypatch.setattr(runner, 'load_sources', lambda *_: pytest.fail('source access after parity defect'))
    with pytest.raises(ValueError, match='parity'):
        runner.run_gate(tmp_path, tmp_path, tmp_path / 'gate')


def test_observation_pairing_and_global_indices(monkeypatch: pytest.MonkeyPatch) -> None:
    noises, seeds = [], []
    def propagate(parent: provenance.U8, noise: provenance.U8) -> tuple[provenance.U8, provenance.U8]:
        noises.append(noise.copy())
        return np.zeros((2, 64), dtype=np.uint8), np.ones((2, 64), dtype=np.uint8)
    def score(tape: provenance.U8, seed: int) -> int:
        seeds.append(seed)
        return 64
    monkeypatch.setattr(runner, 'propagate', propagate)
    monkeypatch.setattr(runner, 'score_reference', score)
    parents: list[dict[str, provenance.U8]] = [{a: np.zeros(64, dtype=np.uint8) for a in analysis.ARMS} for _ in range(10)]
    rows = runner.observe(parents, range(5, 6))
    assert len(rows) == 78
    assert seeds[:26] == seeds[26:52] == seeds[52:]
    assert seeds[0] == 0xAC007 + 5000
    for i in range(13):
        assert np.array_equal(noises[i], noises[i + 13])
        assert np.array_equal(noises[i], noises[i + 26])
        assert np.array_equal(noises[i], provenance.trial_noise(5, i))
    assert all(r['provenance_fraction'] == 1 for r in rows)


@pytest.mark.parametrize(('hits', 'expected'), [((52, 3, 1), 'PASS'), ((51, 3, 1), 'FAIL'),
                                               ((52, 4, 1), 'FAIL'), ((52, 3, 2), 'FAIL')])
def test_heldout_boundaries_and_independent_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hits: tuple[int, int, int], expected: str,
) -> None:
    monkeypatch.setattr(analysis, 'score_reference', lambda *_: 64)
    development = observations(range(5))
    heldout = observations(range(5, 10))
    for row in heldout:
        arm_hits = hits[analysis.ARMS.index(row['arm'])]
        if (row['witness'] - 5) * 13 + row['trial'] < arm_hits:
            row.update(score=64, provenance_fraction=0.75, labels_hex='01' * 48 + '00' * 16)
    calibration = {'implementation': runner.implementation_hashes(), 'parity': {'random_cases': 1000, 'directed_cases': 84, 'label_cases': 13},
                   'development_sha256': analysis.digest(development), 'selection': analysis.calibrate(development)}
    for repeat in range(2):
        directory = tmp_path / f'repeat_{repeat}'
        directory.mkdir()
        for name, value in [('development', development), ('heldout', heldout), ('calibration', calibration),
                            ('completion', {'calibration_sha256': analysis.digest(calibration),
                                            'heldout_sha256': analysis.digest(heldout)})]:
            analysis.write_json(directory / f'{name}.json', value)
    result = analysis.analyze(tmp_path)
    assert result['decision'] == expected
    assert result['heldout']['pooled']['original']['detections'] == hits[0]
    monkeypatch.setattr(analysis, 'score_reference', lambda *_: 63)
    with pytest.raises(ValueError, match='independent verification'):
        analysis.analyze(tmp_path)
    monkeypatch.setattr(analysis, 'score_reference', lambda *_: 64)
    heldout[-1]['tape_hex'] = 'ff' * 64  # Even unclassified output must repeat exactly.
    (tmp_path / 'repeat_1' / 'heldout.json').write_text(json.dumps(heldout))
    (tmp_path / 'repeat_1' / 'completion.json').write_text(json.dumps({
        'calibration_sha256': analysis.digest(calibration), 'heldout_sha256': analysis.digest(heldout)}))
    assert analysis.analyze(tmp_path)['decision'] == 'UNEVALUABLE IMPLEMENTATION DEFECT'


def test_source_allowlist_and_frozen_shuffle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from experiments.analyze_ac_p003_functional_origin_convergence import Checkpoint, Run
    checkpoints = []
    pairs: list[dict[str, Any]] = []
    for w, seed in enumerate(SOURCE_SEEDS):
        tape = np.arange(64, dtype=np.uint8)
        checkpoint = Checkpoint(Run('AC-P005', 16, seed), 1001, tape.reshape(1, 64),
                                np.ones(1, dtype=np.int64), np.array([64], dtype=np.int64),
                                0, np.empty(0, dtype=np.int64), {'manifest.json': str(seed)})
        checkpoints.append(checkpoint)
        pairs.append({'index': w, 'source_seed': seed, 'source_epoch': 1001, 'witness_rank': 0,
                      'witness_score': 64, 'control_score': 0, 'source_checksums': checkpoint.checksums,
                      'arms': {'witness': {'target_hex': tape.tobytes().hex()},
                               'shuffle': {'target_hex': shuffled_control(tape, w).tobytes().hex()}}})
    accessed = []
    def load(path: Path, run: Run) -> Checkpoint:
        assert path == tmp_path / (run.name + '_prectrlv1')
        accessed.append(run.seed)
        return checkpoints[SOURCE_SEEDS.index(run.seed)]
    monkeypatch.setattr(source, 'load_checkpoint', load)
    monkeypatch.setattr(runner, 'score_reference', lambda *_: 0)
    preparation = tmp_path / 'preparation.json'
    preparation.write_text(json.dumps({'campaign': 'AC-P006', 'pairs': pairs}))
    parents, evidence = runner.load_sources(tmp_path, preparation)
    assert accessed == list(SOURCE_SEEDS)
    assert len(evidence) == len(parents) == 10
    for w, parent in enumerate(parents):
        assert np.array_equal(parent['random'], provenance.random_parent(w))
    pairs[0]['arms']['shuffle']['target_hex'] = '00' * 64
    preparation.write_text(json.dumps({'campaign': 'AC-P006', 'pairs': pairs}))
    with pytest.raises(ValueError, match='shuffle mismatch'):
        runner.load_sources(tmp_path, preparation)
    pairs[0]['source_seed'] = 202615002
    preparation.write_text(json.dumps({'campaign': 'AC-P006', 'pairs': pairs}))
    accessed.clear()
    with pytest.raises(ValueError, match='source order'):
        runner.load_sources(tmp_path, preparation)
    assert not accessed


def test_implementation_drift_stops_unblinding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, 'load_sources', lambda *_: ([], []))
    monkeypatch.setattr(runner, 'parity_gate', lambda: {})
    versions = iter([{'code': 'before'}, {'code': 'after'}])
    monkeypatch.setattr(runner, 'implementation_hashes', lambda: next(versions))
    def observe(parents: Any, indices: range) -> list[dict[str, Any]]:
        assert indices == range(5)
        return observations(indices)
    monkeypatch.setattr(runner, 'observe', observe)
    with pytest.raises(ValueError, match='implementation changed'):
        runner.run_gate(tmp_path, tmp_path, tmp_path / 'gate')
    assert not (tmp_path / 'gate' / 'repeat_0' / 'heldout.json').exists()
