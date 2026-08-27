from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(slots=True)
class RandomStreams:
    """Independent deterministic streams for simulation subsystems."""

    chemistry: Random
    world: Random
    founders: Random
    dynamics: Random

    @classmethod
    def from_seed(cls, seed: int) -> RandomStreams:
        seeder = Random(seed)
        return cls(
            chemistry=Random(seeder.getrandbits(64)),
            world=Random(seeder.getrandbits(64)),
            founders=Random(seeder.getrandbits(64)),
            dynamics=Random(seeder.getrandbits(64)),
        )
