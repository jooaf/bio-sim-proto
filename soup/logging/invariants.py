"""Invariant checks and failure dumps.

Stage 0 checks flat-state shape, dtype, age, and tape-ID uniqueness. Stage 1 also
checks nonnegative pool counts and exact conservation of every byte value. The
occupancy lattice remains absent until Stage 2.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from soup.ledgers import SymbolPool
from soup.world import FlatWorld, SpatialWorld


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


def check_stage1(world: FlatWorld, pool: SymbolPool, tape_length: int) -> None:
    """Assert Stage 0 structure plus exact nonnegative per-symbol conservation."""

    check_stage0(world, tape_length)
    if pool.counts.shape != (256,) or pool.counts.dtype != np.int64:
        raise InvariantViolation("symbol pool must be an int64 vector of length 256")
    if np.any(pool.counts < 0):
        raise InvariantViolation("symbol pool contains a negative count")
    tape_counts = np.bincount(world.tapes.ravel(), minlength=256).astype(np.int64)
    observed = tape_counts + pool.counts
    if not np.array_equal(observed, pool.conserved_totals):
        changed = np.flatnonzero(observed != pool.conserved_totals)
        raise InvariantViolation(f"symbol conservation failed for byte values {changed.tolist()}")


def check_stage2(world: SpatialWorld, pool: SymbolPool, tape_length: int) -> None:
    """Assert spatial occupancy structure and exact occupied-tape conservation."""

    expected_shape = (world.capacity, tape_length)
    if world.tapes.dtype != np.uint8 or world.tapes.shape != expected_shape:
        raise InvariantViolation(f"invalid spatial tape array {world.tapes.dtype} {world.tapes.shape}")
    if world.occupied.shape != (world.capacity,) or world.occupied.dtype != np.bool_:
        raise InvariantViolation("occupancy must be a boolean capacity vector")
    for name, values in (
        ("tape_ids", world.tape_ids),
        ("ages", world.ages),
        ("inert_ticks", world.inert_ticks),
        ("born_ticks", world.born_ticks),
    ):
        if values.shape != (world.capacity,) or values.dtype != np.int64:
            raise InvariantViolation(f"{name} must be an int64 capacity vector")
    occupied_ids = world.tape_ids[world.occupied]
    if len(np.unique(occupied_ids)) != len(occupied_ids) or np.any(occupied_ids < 0):
        raise InvariantViolation("occupied tape IDs must be unique and nonnegative")
    if np.any(world.tape_ids[~world.occupied] != -1):
        raise InvariantViolation("empty cells must have tape_id -1")
    if np.any(world.born_ticks[~world.occupied] != -1):
        raise InvariantViolation("empty cells must have born_tick -1")
    if np.any(world.ages < 0) or np.any(world.inert_ticks < 0):
        raise InvariantViolation("spatial ages and inert timers must be nonnegative")
    if np.any(world.tapes[~world.occupied] != 0):
        raise InvariantViolation("empty storage rows must be zeroed")
    if len(occupied_ids) and world.next_tape_id <= int(occupied_ids.max()):
        raise InvariantViolation("next_tape_id must exceed every live tape ID")
    if pool.counts.shape != (256,) or pool.counts.dtype != np.int64 or np.any(pool.counts < 0):
        raise InvariantViolation("symbol pool must be a nonnegative int64 vector of length 256")
    tape_counts = np.bincount(world.occupied_tapes().ravel(), minlength=256).astype(np.int64)
    observed = tape_counts + pool.counts
    if not np.array_equal(observed, pool.conserved_totals):
        changed = np.flatnonzero(observed != pool.conserved_totals)
        raise InvariantViolation(f"symbol conservation failed for byte values {changed.tolist()}")
    if world.population_size + world.free_cells != world.capacity:
        raise InvariantViolation("occupied plus free cells does not equal lattice capacity")


def dump_violation(
    run_dir: Path,
    tick: int,
    error: BaseException,
    world: FlatWorld | SpatialWorld,
    pool: SymbolPool | None = None,
) -> None:
    """Persist a full state dump and append the invariant error before re-raising."""

    dump_path = run_dir / f"invariant_failure_tick_{tick}.npz"
    if isinstance(world, SpatialWorld):
        if pool is None:
            np.savez_compressed(
                dump_path,
                tapes=world.tapes,
                tape_ids=world.tape_ids,
                ages=world.ages,
                occupied=world.occupied,
                inert_ticks=world.inert_ticks,
                born_ticks=world.born_ticks,
            )
        else:
            np.savez_compressed(
                dump_path,
                tapes=world.tapes,
                tape_ids=world.tape_ids,
                ages=world.ages,
                occupied=world.occupied,
                inert_ticks=world.inert_ticks,
                born_ticks=world.born_ticks,
                pool_counts=pool.counts,
                conserved_totals=pool.conserved_totals,
            )
    elif pool is None:
        np.savez_compressed(dump_path, tapes=world.tapes, tape_ids=world.tape_ids, ages=world.ages)
    else:
        np.savez_compressed(
            dump_path,
            tapes=world.tapes,
            tape_ids=world.tape_ids,
            ages=world.ages,
            pool_counts=pool.counts,
            conserved_totals=pool.conserved_totals,
        )
    record = {"tick": tick, "error_type": type(error).__name__, "message": str(error)}
    with (run_dir / "invariant_log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
