from __future__ import annotations

import pytest

from experiments.analyze_ac_p006_transplant import exact_sign_probability


@pytest.mark.parametrize(
    ("favored", "opposite", "expected"),
    [(0, 0, 1.0), (10, 0, 1 / 1024), (9, 1, 11 / 1024), (5, 5, 0.623046875)],
)
def test_exact_sign_probability(favored: int, opposite: int, expected: float) -> None:
    assert exact_sign_probability(favored, opposite) == expected
