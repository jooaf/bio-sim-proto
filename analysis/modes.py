"""MODES analysis boundary.

The filtered persistent-type lineage and four MODES potentials are intentionally
not fabricated from Stage 0's fixed tape slots. They will be implemented and cited
against Dolson et al. (2019) when evolving lineage construction exists.
"""

from __future__ import annotations

import pandas as pd


def compute_modes() -> pd.DataFrame:
    """Return the explicit empty Stage 0 schema rather than simulator conclusions."""

    return pd.DataFrame(columns=["epoch", "change", "novelty", "complexity", "ecological"])
