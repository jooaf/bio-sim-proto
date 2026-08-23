"""Deterministic stage-aware timestep scheduler."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from numpy.random import Generator

from soup.config import Config, PairingMode
from soup.dissolution import DissolutionFact, dissolve_candidates
from soup.interactions import InteractionFact, run_interaction_round, run_local_interaction_round
from soup.ledgers import SymbolPool
from soup.logging.invariants import (
    InvariantViolation,
    check_stage0,
    check_stage1,
    check_stage2,
    dump_violation,
)
from soup.logging.writer import RunWriter
from soup.placement import PlacementFact, PlacementResult, place_random_tapes
from soup.substrate.base import ExecutionBudget, Substrate
from soup.world import FlatWorld, SpatialWorld, World


class Scheduler:
    """Advance the soup in an explicit stage-dependent order.

    Stages 0/1 execute interactions, age tapes, check invariants, and log.
    Stage 2 executes local interactions, ages tapes, dissolves candidates,
    attempts pool-funded placement, checks invariants, and then logs. Energy,
    environment, and starvation remain absent until Stage 3.
    """

    def __init__(
        self,
        *,
        config: Config,
        world: World,
        substrate: Substrate,
        rng: Generator,
        writer: RunWriter,
        pool: SymbolPool | None = None,
    ) -> None:
        self.config = config
        self.world = world
        self.substrate = substrate
        self.rng = rng
        self.writer = writer
        self.pool = pool
        self._abundance_events: set[str] = set()
        self._birth_records: dict[int, tuple[int, tuple[int, int] | None, str]] = {}
        for index_value in world.occupied_indices():
            index = int(index_value)
            tape_id = int(world.tape_ids[index])
            self._birth_records[tape_id] = (
                0,
                world.cell(index),
                writer.hash_tape(world.tapes[index]),
            )
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
            dump_violation(self.writer.run_dir, tick, error, self.world, self.pool)
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
        """Advance one tick and return interaction facts for optional views."""

        dissolutions: list[DissolutionFact] = []
        placements = PlacementResult(0, 0, ())
        if isinstance(self.world, SpatialWorld):
            if self.pool is None:
                raise InvariantViolation("Stage 2 requires a symbol pool")
            facts = run_local_interaction_round(
                world=self.world,
                substrate=self.substrate,
                rng=self.rng,
                budget=self.budget,
                tick=tick,
                interactions_per_tick=self.config.world.interactions_per_tick,
                interaction_radius=self.config.world.interaction_radius,
                mutation_rate=self.config.world.mutation_rate,
                pool=self.pool,
                hash_tape=self.writer.hash_tape,
            )
            self.world.ages[self.world.occupied] += 1
            dissolutions = dissolve_candidates(
                world=self.world,
                substrate=self.substrate,
                pool=self.pool,
                config=self.config.dissolution,
                rng=self.rng,
                tick=tick,
            )
            placements = place_random_tapes(
                world=self.world,
                substrate=self.substrate,
                pool=self.pool,
                rng=self.rng,
                tick=tick,
                reseed_rate=self.config.world.reseed_rate,
            )
            self._write_lifecycle(tick, dissolutions, placements)
        else:
            facts = run_interaction_round(
                world=self.world,
                substrate=self.substrate,
                rng=self.rng,
                budget=self.budget,
                tick=tick,
                interactions_per_tick=self.config.world.interactions_per_tick,
                pairing_mode=PairingMode(self.config.world.pairing_mode),
                mutation_rate=self.config.world.mutation_rate,
                pool=self.pool,
                hash_tape=self.writer.hash_tape,
            )
            self.world.ages += 1

        if self.config.run.debug_invariants or tick % self.config.run.invariant_check_interval == 0:
            self._check_invariants()

        self._write_interactions(facts)
        self._write_tick(tick, facts, len(dissolutions))
        if tick % self.config.run.epoch_length == 0:
            epoch = tick // self.config.run.epoch_length
            self._write_epoch(epoch, tick)
        if (tick + 1) % self.config.logging.flush_interval == 0:
            self.writer.flush()
        return facts

    def _check_invariants(self) -> None:
        if isinstance(self.world, SpatialWorld):
            if self.pool is None:
                raise InvariantViolation("Stage 2 requires a symbol pool")
            check_stage2(self.world, self.pool, self.config.substrate.tape_length)
        elif self.pool is None:
            check_stage0(self.world, self.config.substrate.tape_length)
        else:
            check_stage1(self.world, self.pool, self.config.substrate.tape_length)

    def _write_lifecycle(
        self,
        tick: int,
        dissolutions: list[DissolutionFact],
        placement_result: PlacementResult,
    ) -> None:
        for death in dissolutions:
            born_tick, birth_cell, birth_hash = self._birth_records.pop(
                death.tape_id,
                (death.born_tick, death.cell, ""),
            )
            death_hash = self.writer.hash_tape(death.tape)
            self.writer.append(
                "lineage",
                {
                    "tape_id": death.tape_id,
                    "born_tick": born_tick,
                    "died_tick": death.died_tick,
                    "birth_cell": birth_cell,
                    "death_cause": death.cause,
                    "progenitor_ids": [],
                    "content_hash_at_birth": birth_hash,
                },
            )
            self.writer.append_event(
                tick=death.died_tick,
                event_type="tape_dissolved",
                tape_id=death.tape_id,
                content_hash=death_hash,
                details={"cell": list(death.cell), "cause": death.cause},
            )
        for birth in placement_result.placements:
            birth_hash = self.writer.hash_tape(birth.tape)
            self._birth_records[birth.tape_id] = (birth.born_tick, birth.cell, birth_hash)
            self.writer.append(
                "lineage",
                {
                    "tape_id": birth.tape_id,
                    "born_tick": birth.born_tick,
                    "died_tick": None,
                    "birth_cell": birth.cell,
                    "death_cause": None,
                    "progenitor_ids": [],
                    "content_hash_at_birth": birth_hash,
                },
            )
            self.writer.append_event(
                tick=birth.born_tick,
                event_type="random_tape_placed",
                tape_id=birth.tape_id,
                content_hash=birth_hash,
                details={"cell": list(birth.cell)},
            )
        if placement_result.blocked:
            self.writer.append_event(
                tick=tick,
                event_type="placement_blocked",
                details={
                    "attempted": placement_result.attempted,
                    "blocked": placement_result.blocked,
                },
            )

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
                    "a_cell": fact.a_cell,
                    "b_cell": fact.b_cell,
                    "a_mutations": fact.a_mutations,
                    "b_mutations": fact.b_mutations,
                    "mutation_writes_success": fact.mutation_writes_success,
                    "mutation_writes_blocked": fact.mutation_writes_blocked,
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

    def _write_tick(
        self,
        tick: int,
        facts: list[InteractionFact],
        dissolution_count: int,
    ) -> None:
        if "ticks" not in self.config.logging.tick_tables:
            return
        occupied = self.world.occupied_indices()
        mean_age = float(np.mean(self.world.ages[occupied])) if len(occupied) else 0.0
        self.writer.append(
            "ticks",
            {
                "tick": tick,
                "n_tapes": self.world.population_size,
                "n_free_cells": self.world.free_cells,
                "pool_total": 0 if self.pool is None else self.pool.total,
                "pool_entropy": 0.0 if self.pool is None else self.pool.entropy,
                "pool_histogram": (
                    np.zeros(256, dtype=np.int64).tolist()
                    if self.pool is None
                    else self.pool.counts.tolist()
                ),
                "energy_field_total": 0.0,
                "energy_tape_total": 0.0,
                "energy_dissipated_cum": 0.0,
                "energy_influx_cum": 0.0,
                "n_interactions": len(facts),
                "n_writes_success": sum(
                    fact.writes_success + fact.mutation_writes_success for fact in facts
                ),
                "n_writes_blocked": sum(
                    fact.writes_blocked + fact.mutation_writes_blocked for fact in facts
                ),
                "n_dissolutions": dissolution_count,
                "mean_tape_energy": 0.0,
                "mean_tape_age": mean_age,
            },
        )

    def _write_epoch(self, epoch: int, tick: int) -> None:
        occupied = self.world.occupied_indices()
        hashes = {
            int(index): self.writer.hash_tape(self.world.tapes[int(index)])
            for index in occupied
        }
        members: defaultdict[str, list[int]] = defaultdict(list)
        for index in occupied:
            index_int = int(index)
            content_hash = hashes[index_int]
            members[content_hash].append(index_int)
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
        for index_value in occupied:
            index = int(index_value)
            tape = self.world.tapes[index]
            cell = self.world.cell(index)
            cell_x, cell_y = (-1, index) if cell is None else cell
            self.writer.append(
                "tapes",
                {
                    "tick": tick,
                    "tape_id": int(self.world.tape_ids[index]),
                    "cell_x": cell_x,
                    "cell_y": cell_y,
                    "age": int(self.world.ages[index]),
                    "energy": 0.0,
                    "content_hash": hashes[index],
                    "length_nonzero": int(np.count_nonzero(tape)),
                    "byte_histogram": np.bincount(tape, minlength=256).astype(np.int64).tolist(),
                    "full_bytes": tape.tobytes() if include_full else None,
                },
            )
