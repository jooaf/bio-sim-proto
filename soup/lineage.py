"""Append-only tape birth facts.

Self-replication is deliberately not represented here; it is detected offline from
interaction hashes. Stage 2 deaths are emitted as lifecycle events and a terminal
lineage row by the scheduler.
"""

from __future__ import annotations

from soup.logging.writer import RunWriter
from soup.world import World


def write_initial_lineage(world: World, writer: RunWriter) -> None:
    """Register every initially occupied tape without inferring progenitors."""

    for index_value in world.occupied_indices():
        index = int(index_value)
        writer.append(
            "lineage",
            {
                "tape_id": int(world.tape_ids[index]),
                "born_tick": 0,
                "died_tick": None,
                "birth_cell": world.cell(index),
                "death_cause": None,
                "progenitor_ids": [],
                "content_hash_at_birth": writer.hash_tape(world.tapes[index]),
            },
        )
