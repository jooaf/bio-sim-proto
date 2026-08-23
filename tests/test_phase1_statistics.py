from __future__ import annotations

import numpy as np
import pytest

from experiments.analyze_phase1_newexperiments import (
    _betainc_regularized,
    format_p_value,
    spearman,
)


def test_regularized_beta_uses_correct_symmetry_branch() -> None:
    assert _betainc_regularized(1.0, 1.0, 0.25) == pytest.approx(0.25)
    # I_x(1/2, 1/2) = 2*asin(sqrt(x))/pi, so x=1/4 gives exactly 1/3.
    assert _betainc_regularized(0.5, 0.5, 0.25) == pytest.approx(1.0 / 3.0)


def test_p_value_format_does_not_round_nonzero_to_zero() -> None:
    assert format_p_value(1.1287e-7) == "1.13e-07"
    assert format_p_value(0.273349) == "0.2733"


def test_spearman_uses_exact_small_sample_p_value() -> None:
    rho, p_value = spearman(np.arange(4), np.arange(4))
    assert rho == pytest.approx(1.0)
    # Two extreme permutations (increasing and decreasing) among 4! labels.
    assert p_value == pytest.approx(1.0 / 12.0)


def test_spearman_moderate_large_sample_regression() -> None:
    multipliers = np.repeat(np.array([0.5, 16.0, 2.0]), 5)
    maximum_entropies = np.array(
        [
            0.50337602,
            0.46610659,
            0.43984184,
            0.42421980,
            1.22648714,
            5.95369538,
            0.33789834,
            0.33628394,
            0.36683705,
            0.41279337,
            1.63247318,
            0.75821346,
            0.46866830,
            1.06691013,
            0.47234961,
        ]
    )
    rho, p_value = spearman(multipliers, maximum_entropies)
    assert rho == pytest.approx(-0.3023715784)
    assert p_value == pytest.approx(0.2733497897)
