"""Deterministic Stage 0 timestep scheduler."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from numpy.random import Generator

from soup.config import Config
from soup.interactions import InteractionFact, run_random_round
from soup.logging.invariants import InvariantViolation, check_stage0, dump_violation
from soup.logging.writer import RunWriter
from soup.substrate.base import ExecutionBudget, Substrate
from soup.world import FlatWorld


class Scheduler:
    """Advance the bare soup in explicit tick order.

    Stage 0 order is: (1) execute a random interaction round, (2) age tapes,
    (3) check available structural invariants, (4) write raw tick facts, and
    (5) write epoch censuses when ``tick % epoch_length == 0``. Environment,
    absorption, dissolution, and placement are intentionally absent until their
    specified stages; their eventual order is not approximated here.
    """

    def __init__(
        self,
        *,
        config: Config,
        world: FlatWorld,
        substrate: Substrate,
        rng: Generator,
        writer: RunWriter,
    ) -> None:
        self.config = config
        self.world = world
        self.substrate = substrate
        self.rng = rng
        self.writer = writer
        self._abundance_events: set[str] = set()
        self.budget = ExecutionBudget(max_steps=config.substrate.max_steps)

    def run(self) -> None:
        """Run exactly the configured number of ticks or halt on an invariant."""

        for tick in range(self.config.run.n_ticks):
            self.advance(tick)

    def advance(self, tick: int) -> list[InteractionFact]:
        """Advance one checked tick for either a headless or visual runner."""

        try:
            return self.step(tick)
        except InvariantViolation as error:
            dump_violation(self.writer.run_dir, tick, error, self.world)
            self.writer.append_event(
                tick=tick,
                event_type="invariant_violation",
                details={"error_type": type(error).__name__, "message": str(error)},
            )
            raise
        except BaseException as error:
            self.writer.append_event(
                tick=tick,
                event_type="run_halted",
                details={"error_type": type(error).__name__, "message": str(error)},
            )
            raise

    def step(self, tick: int) -> list[InteractionFact]:
        """Advance one tick and return raw interaction facts for optional views."""
        facts = run_random_round(
            world=self.world,
            substrate=self.substrate,
            rng=self.rng,
            budget=self.budget,
            tick=tick,
            interactions_per_tick=self.config.world.interactions_per_tick,
            hash_tape=self.writer.hash_tape,
        )
        self.world.ages += 1

        if self.config.run.debug_invariants or tick % self.config.run.invariant_check_interval == 0:
            check_stage0(self.world, self.config.substrate.tape_length)

        self._write_interactions(facts)
        self._write_tick(tick, facts)
        if tick % self.config.run.epoch_length == 0:
            epoch = tick // self.config.run.epoch_length
            self._write_epoch(epoch, tick)
        if (tick + 1) % self.config.logging.flush_interval == 0:
            self.writer.flush()
        return facts

    def _write_interactions(self, facts: list[InteractionFact]) -> None:
        if "interactions" not in self.config.logging.tick_tables:
            return
        for fact in facts:
            if not self.writer.should_log_interaction(fact.tick, fact.round_index):
                continue
            self.writer.append(
                "interactions",
                {
                    "tick": fact.tick,
                    "round_index": fact.round_index,
                    "a_id": fact.a_id,
                    "b_id": fact.b_id,
                    "a_cell": None,
                    "b_cell": None,
                    "steps": fact.steps,
                    "energy_spent": fact.energy_spent,
                    "writes_success": fact.writes_success,
                    "writes_blocked": fact.writes_blocked,
                    "halt_reason": fact.halt_reason,
                    "a_bytes_changed": fact.a_bytes_changed,
                    "b_bytes_changed": fact.b_bytes_changed,
                    "a_hash_before": fact.a_hash_before,
                    "a_hash_after": fact.a_hash_after,
                    "b_hash_before": fact.b_hash_before,
                    "b_hash_after": fact.b_hash_after,
                },
            )

    def _write_tick(self, tick: int, facts: list[InteractionFact]) -> None:
        if "ticks" not in self.config.logging.tick_tables:
            return
        self.writer.append(
            "ticks",
            {
                "tick": tick,
                "n_tapes": self.world.population_size,
                "n_free_cells": 0,
                "pool_total": 0,
                "pool_entropy": 0.0,
                "energy_field_total": 0.0,
                "energy_tape_total": 0.0,
                "energy_dissipated_cum": 0.0,
                "energy_influx_cum": 0.0,
                "n_interactions": len(facts),
                "n_writes_success": sum(fact.writes_success for fact in facts),
                "n_writes_blocked": sum(fact.writes_blocked for fact in facts),
                "n_dissolutions": 0,
                "mean_tape_energy": 0.0,
                "mean_tape_age": float(np.mean(self.world.ages)),
            },
        )

    def _write_epoch(self, epoch: int, tick: int) -> None:
        hashes = [self.writer.hash_tape(tape) for tape in self.world.tapes]
        members: defaultdict[str, list[int]] = defaultdict(list)
        for index, content_hash in enumerate(hashes):
            members[content_hash].append(index)
            self.writer.first_seen.setdefault(content_hash, tick)

        if "population" in self.config.logging.epoch_tables:
            for content_hash in sorted(members):
                indices = members[content_hash]
                count = len(indices)
                self.writer.append(
                    "population",
                    {
                        "epoch": epoch,
                        "tick": tick,
                        "content_hash": content_hash,
                        "count": count,
                        "mean_age": float(np.mean(self.world.ages[indices])),
                        "mean_energy": 0.0,
                        "first_seen_tick": self.writer.first_seen[content_hash],
                    },
                )
                if count >= self.config.logging.abundance_event_threshold and content_hash not in self._abundance_events:
                    self._abundance_events.add(content_hash)
                    self.writer.append_event(
                        tick=tick,
                        event_type="hash_abundance_threshold_crossed",
                        content_hash=content_hash,
                        details={"count": count, "threshold": self.config.logging.abundance_event_threshold},
                    )

        if "tapes" not in self.config.logging.epoch_tables:
            return
        if epoch % self.config.logging.tape_snapshot_interval != 0:
            return
        full_interval = self.config.logging.full_tape_snapshot_interval
        include_full = full_interval > 0 and tick % full_interval == 0
        for index, tape in enumerate(self.world.tapes):
            self.writer.append(
                "tapes",
                {
                    "tick": tick,
                    "tape_id": int(self.world.tape_ids[index]),
                    "cell_x": -1,
                    "cell_y": int(index),
                    "age": int(self.world.ages[index]),
                    "energy": 0.0,
                    "content_hash": hashes[index],
                    "length_nonzero": int(np.count_nonzero(tape)),
                    "byte_histogram": np.bincount(tape, minlength=256).astype(np.int64).tolist(),
                    "full_bytes": tape.tobytes() if include_full else None,
                },
            )
