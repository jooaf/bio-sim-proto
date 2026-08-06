"""Chemical-organization detection begins at Stage 3."""

from __future__ import annotations

import pandas as pd


def detect_organizations() -> pd.DataFrame:
    """Return the explicit pre-Stage-3 schema."""

    return pd.DataFrame(columns=["epoch", "org_id", "member_hashes", "closed", "self_maintaining", "size", "nesting_depth"])
