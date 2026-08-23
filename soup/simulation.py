"""Stage-aware simulation assembly and lifecycle."""

from __future__ import annotations

from pathlib import Path

from soup.config import Config
from soup.ledgers import SymbolPool
from soup.lineage import write_initial_lineage
from soup.logging.writer import RunWriter
from soup.rng import make_rng
from soup.scheduler import Scheduler
from soup.substrate.base import Substrate
from soup.substrate.bff import BFFSubstrate
from soup.substrate.ski import SKISubstrate
from soup.world import FlatWorld, SpatialWorld, World


class Simulation:
    """Assemble and run the stage-selected flat or spatial soup."""

    def __init__(self, config: Config, run_dir: Path | None = None) -> None:
        config.apply_stage_gates()
        config.validate()
        if config.run.stage not in {0, 1, 2}:
            raise NotImplementedError("this stage gate implements only Stages 0, 1, and 2")
        self.config = config
        self.rng = make_rng(config.run.seed)
        self.substrate: Substrate
        if config.substrate.name == "bff":
            self.substrate = BFFSubstrate(
                tape_length=config.substrate.tape_length,
                head_wrap=config.substrate.head_wrap,
                pc_wrap=config.substrate.pc_wrap,
                noop_density=config.substrate.noop_density,
            )
        else:
            self.substrate = SKISubstrate(tape_length=config.substrate.tape_length)
        self.world: World
        if config.run.stage < 2:
            self.world = FlatWorld.create(config.world.population_size, self.substrate, self.rng)
        else:
            self.world = SpatialWorld.create(
                width=config.world.width,
                height=config.world.height,
                initial_tape_fill=config.symbols.initial_tape_fill,
                substrate=self.substrate,
                rng=self.rng,
            )
        initial_tapes = (
            self.world.occupied_tapes()
            if isinstance(self.world, SpatialWorld)
            else self.world.tapes
        )
        self.pool = (
            SymbolPool.from_tapes(initial_tapes, config.symbols.pool_multiplier)
            if config.run.stage >= 1
            else None
        )
        self.writer = RunWriter(config, run_dir=run_dir)
        write_initial_lineage(self.world, self.writer)
        self.scheduler = Scheduler(
            config=config,
            world=self.world,
            substrate=self.substrate,
            rng=self.rng,
            writer=self.writer,
            pool=self.pool,
        )

    def run(self) -> Path:
        """Execute and finalize the run directory, preserving failures in manifest."""

        try:
            self.scheduler.run()
        except BaseException:
            self.writer.close(exit_status="failed")
            raise
        self.writer.close(exit_status="success")
        return self.writer.run_dir
