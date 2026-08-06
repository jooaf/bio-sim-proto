"""Invariant checks and failure dumps.

Stage 0 has no conservation ledgers or occupancy lattice. It still checks flat-state
shape, dtype, and tape-ID uniqueness every configured tick. Ledger checks are added
only when their mechanisms enter the staged build.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from soup.world import FlatWorld


class InvariantViolation(RuntimeError):
    """Raised immediately when a scientific invariant fails."""


def check_stage0(world: FlatWorld, tape_length: int) -> None:
    """Assert exact structural invariants available in the bare soup."""

    if world.tapes.dtype != np.uint8:
        raise InvariantViolation(f"tape dtype is {world.tapes.dtype}, expected uint8")
    if world.tapes.shape != (world.population_size, tape_length):
        raise InvariantViolation(f"invalid tape shape {world.tapes.shape}")
    if len(np.unique(world.tape_ids)) != world.population_size:
        raise InvariantViolation("a tape_id appears more than once")
    if np.any(world.ages < 0):
        raise InvariantViolation("negative tape age")


def dump_violation(run_dir: Path, tick: int, error: BaseException, world: FlatWorld) -> None:
    """Persist a full state dump and append the invariant error before re-raising."""

    np.savez_compressed(
        run_dir / f"invariant_failure_tick_{tick}.npz",
        tapes=world.tapes,
        tape_ids=world.tape_ids,
        ages=world.ages,
    )
    record = {"tick": tick, "error_type": type(error).__name__, "message": str(error)}
    with (run_dir / "invariant_log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
