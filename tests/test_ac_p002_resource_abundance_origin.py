from __future__ import annotations

import pytest

from experiments.analyze_ac_p002_resource_abundance_origin import exact_one_sided


@pytest.mark.parametrize(
    ("favored", "opposite", "expected"),
    [(0, 0, 1.0), (4, 1, 0.1875), (5, 0, 0.03125), (6, 1, 0.0625)],
)
def test_exact_one_sided_discordance_test(favored: int, opposite: int, expected: float) -> None:
    assert exact_one_sided(favored, opposite) == expected
