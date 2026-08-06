"""Trophic graph analysis begins with the energy ledger in Stage 3."""

from __future__ import annotations

import pandas as pd


def interaction_edges(interactions: pd.DataFrame) -> pd.DataFrame:
    """Expose the future edge schema without assigning trophic meaning in Stage 0."""

    del interactions
    return pd.DataFrame(columns=["source_hash", "target_hash", "bytes_written"])
