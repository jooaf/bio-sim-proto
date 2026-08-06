"""Lineage facts for tapes.

In Stage 0 tapes are fixed slots: all are born at initialization and none die.
Self-replication is deliberately not represented here; it is detected offline from
interaction hashes.
"""

from __future__ import annotations

from soup.logging.writer import RunWriter
from soup.world import FlatWorld


def write_initial_lineage(world: FlatWorld, writer: RunWriter) -> None:
    """Register every initial tape without inferring progenitors."""

    for index in range(world.population_size):
        writer.append(
            "lineage",
            {
                "tape_id": int(world.tape_ids[index]),
                "born_tick": 0,
                "died_tick": None,
                "birth_cell": None,
                "death_cause": None,
                "progenitor_ids": [],
                "content_hash_at_birth": writer.hash_tape(world.tapes[index]),
            },
        )
