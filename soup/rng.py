"""Deterministic random-number generator plumbing."""

from __future__ import annotations

import numpy as np
from numpy.random import Generator


def make_rng(seed: int) -> Generator:
    """Construct the sole explicit generator used by simulation dynamics."""

    return np.random.Generator(np.random.PCG64(seed))
