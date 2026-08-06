"""Stage-aware simulation assembly and lifecycle."""

from __future__ import annotations

from pathlib import Path

from soup.config import Config
from soup.lineage import write_initial_lineage
from soup.logging.writer import RunWriter
from soup.rng import make_rng
from soup.scheduler import Scheduler
from soup.substrate.bff import BFFSubstrate
from soup.world import FlatWorld


class Simulation:
    """Assemble and run Stage 0 without importing future mechanisms."""

    def __init__(self, config: Config, run_dir: Path | None = None) -> None:
        config.apply_stage_gates()
        config.validate()
        if config.run.stage != 0:
            raise NotImplementedError("this stage gate implements Stage 0 only")
        self.config = config
        self.rng = make_rng(config.run.seed)
        self.substrate = BFFSubstrate(
            tape_length=config.substrate.tape_length,
            head_wrap=config.substrate.head_wrap,
            pc_wrap=config.substrate.pc_wrap,
            noop_density=config.substrate.noop_density,
        )
        self.world = FlatWorld.create(config.world.population_size, self.substrate, self.rng)
        self.writer = RunWriter(config, run_dir=run_dir)
        write_initial_lineage(self.world, self.writer)
        self.scheduler = Scheduler(
            config=config,
            world=self.world,
            substrate=self.substrate,
            rng=self.rng,
            writer=self.writer,
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
