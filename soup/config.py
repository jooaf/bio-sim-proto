"""Typed configuration tree, validation, and TOML round trips.

Every tunable value is represented here. Field metadata contains a short description
and a documented sane range (or allowed values). Stage gates are applied before a
run begins so one configuration format remains valid throughout the staged build.
"""

from __future__ import annotations

import dataclasses
import tomllib
import warnings
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar, cast

import tomli_w


T = TypeVar("T")


LIVE_TUNABLE_PATHS = frozenset(
    {
        "run.n_ticks",
        "run.debug_invariants",
        "run.invariant_check_interval",
        "substrate.max_steps",
        "substrate.head_wrap",
        "substrate.pc_wrap",
        "world.interactions_per_tick",
        "world.pairing_mode",
        "world.mutation_rate",
        "logging.tape_snapshot_interval",
        "logging.full_tape_snapshot_interval",
        "logging.interaction_log_rate",
        "logging.flush_interval",
        "logging.abundance_event_threshold",
        "viz.fps_cap",
        "viz.render_every",
        "viz.ticks_per_frame",
        "viz.colour_mode",
    }
)


class PairingMode(str, Enum):
    """Supported stage-aware interaction-sampling protocols."""

    WITH_REPLACEMENT = "with_replacement"
    SHUFFLED_DISJOINT = "shuffled_disjoint"
    LOCAL_NEIGHBORHOOD = "local_neighborhood"


def knob(description: str, sane: str) -> dict[str, str]:
    """Return standard metadata for a tunable configuration field."""

    return {"description": description, "sane_range": sane}


@dataclass(slots=True)
class RunConfig:
    seed: int = field(default=1, metadata=knob("Seed for the sole simulation RNG.", "0..2^63-1"))
    n_ticks: int = field(default=100, metadata=knob("Simulation ticks to execute.", "1..10^9"))
    epoch_length: int = field(default=1, metadata=knob("Ticks per summary epoch.", "1..10^7"))
    stage: int = field(default=0, metadata=knob("Enabled build stage.", "0..5"))
    debug_invariants: bool = field(default=True, metadata=knob("Check invariants each tick.", "true|false"))
    invariant_check_interval: int = field(default=1, metadata=knob("Non-debug invariant cadence.", "1..10^7"))
    output_dir: str = field(default="runs", metadata=knob("Parent directory for run logs.", "writable path"))


@dataclass(slots=True)
class SubstrateConfig:
    name: str = field(default="bff", metadata=knob("Execution substrate.", "bff|ski"))
    tape_length: int = field(default=64, metadata=knob("Bytes in each tape.", "8..4096"))
    max_steps: int = field(default=8192, metadata=knob("Character reads allowed per interaction.", "1..10^7"))
    head_wrap: bool = field(
        default=True,
        metadata=knob(
            "Wrap data heads. True matches arXiv:2406.19108's released bff_noheads implementation.",
            "true|false",
        ),
    )
    pc_wrap: bool = field(default=False, metadata=knob("Wrap the instruction pointer instead of halting.", "true|false"))
    separate_tapes: bool = field(default=False, metadata=knob("Keep paired tapes separate during execution.", "false in Stage 0"))
    noop_density: float = field(
        default=246.0 / 256.0,
        metadata=knob("Expected initial fraction of non-instruction bytes.", "0..1"),
    )


@dataclass(slots=True)
class WorldConfig:
    population_size: int = field(default=256, metadata=knob("Number of flat-soup tapes in Stage 0.", "2..2^20"))
    width: int = field(default=64, metadata=knob("Future lattice width.", "2..16384"))
    height: int = field(default=64, metadata=knob("Future lattice height.", "2..16384"))
    interaction_radius: int = field(default=1, metadata=knob("Future Moore-neighbourhood radius.", "1..64"))
    interactions_per_tick: int = field(default=256, metadata=knob("Ordered pairs executed per tick.", "1..10^9"))
    pairing_mode: str = field(
        default=PairingMode.WITH_REPLACEMENT.value,
        metadata=knob(
            "Protocol used to choose ordered tape pairs.",
            "with_replacement|shuffled_disjoint|local_neighborhood",
        ),
    )
    mutation_rate: float = field(
        default=0.0,
        metadata=knob("Independent pre-interaction replacement probability per tape byte.", "0..1"),
    )
    reseed_rate: float = field(default=0.0, metadata=knob("Chance to seed each free cell per tick.", "0..1"))


@dataclass(slots=True)
class SymbolsConfig:
    pool_multiplier: float = field(default=2.0, metadata=knob("Initial per-byte pool multiple.", "0.01..10^6"))
    initial_tape_fill: float = field(default=1.0, metadata=knob("Initial occupied-cell fraction.", "0..1"))


@dataclass(slots=True)
class EnergyConfig:
    enabled: bool = field(default=False, metadata=knob("Enable energy flow ledger.", "Stage 3+"))
    influx_rate: float = field(default=1.0, metadata=knob("Energy entering per tick.", "0..10^12"))
    absorption_rate: float = field(default=0.1, metadata=knob("Maximum cell-to-tape transfer per tick.", "0..10^9"))
    tape_capacity: float = field(default=100.0, metadata=knob("Maximum tape-held energy.", ">0"))
    per_instruction: float = field(default=0.01, metadata=knob("Energy dissipated per instruction.", "0..10^6"))
    per_write: float = field(default=0.1, metadata=knob("Additional successful-write cost.", "0..10^6"))
    diffusion: float = field(default=0.1, metadata=knob("Field diffusion coefficient.", "0..0.25"))
    decay: float = field(default=0.0, metadata=knob("Field fraction dissipated each tick.", "0..1"))
    min_to_interact: float = field(default=0.0, metadata=knob("Minimum held energy for pairing.", "0..capacity"))


@dataclass(slots=True)
class DissolutionConfig:
    enabled: bool = field(default=False, metadata=knob("Enable active tape dissolution.", "Stage 2+"))
    inert_ticks: int = field(default=100, metadata=knob("Consecutive inert ticks before dissolution.", "1..10^9"))
    starved_ticks: int = field(default=100, metadata=knob("Consecutive zero-energy ticks before dissolution.", "1..10^9"))
    max_age: int = field(default=0, metadata=knob("Maximum age; zero disables age death.", "0..10^12"))
    spontaneous_rate: float = field(default=0.0, metadata=knob("Per-tape spontaneous dissolution chance.", "0..1"))


@dataclass(slots=True)
class EnvironmentConfig:
    influx_spec: str = field(default="uniform", metadata=knob("Composable energy-influx field specification.", "uniform|gradient|patches|perlin|sum"))
    correlation_length: float = field(default=8.0, metadata=knob("Spatial field correlation length in cells.", ">0"))
    modulator: str = field(default="static", metadata=knob("Temporal field modulation.", "static|sinusoidal|random_walk|switching"))
    modulator_period: int = field(default=100, metadata=knob("Temporal modulation period in ticks.", "1..10^9"))
    modulator_amplitude: float = field(default=0.0, metadata=knob("Temporal modulation amplitude.", "0..1"))


@dataclass(slots=True)
class SignalsConfig:
    enabled: bool = field(default=False, metadata=knob("Enable signal opcodes and field.", "Stage 4+"))
    tag_length: int = field(default=4, metadata=knob("Bytes compared in dispatch tags.", "1..64"))
    tag_stride: int = field(default=8, metadata=knob("Bytes between dispatch blocks.", "tag_length..tape_length"))
    signal_spec: str = field(default="uniform", metadata=knob("Initial/environmental signal field.", "field specification"))


@dataclass(slots=True)
class TaskConfig:
    enabled: bool = field(default=False, metadata=knob("Enable local task scoring.", "Stage 4+"))
    task_bonus: float = field(default=0.0, metadata=knob("Interaction-probability task multiplier.", "0..10^6"))
    task_spec: str = field(default="identity", metadata=knob("Local signal transformation task.", "registered task name"))
    switch_cost_energy: float = field(default=0.0, metadata=knob("Energy cost when changing task type.", "0..10^9"))


@dataclass(slots=True)
class LoggingConfig:
    tick_tables: list[str] = field(default_factory=lambda: ["ticks", "interactions"], metadata=knob("Raw per-tick tables to emit.", "known table names"))
    epoch_tables: list[str] = field(default_factory=lambda: ["population", "tapes"], metadata=knob("Summary tables to emit.", "known table names"))
    tape_snapshot_interval: int = field(default=1, metadata=knob("Epochs between tape census snapshots.", "1..10^9"))
    full_tape_snapshot_interval: int = field(default=100, metadata=knob("Ticks between full-byte snapshots; zero disables.", "0..10^9"))
    interaction_log_rate: float = field(default=1.0, metadata=knob("Deterministic fraction of interactions retained.", "0..1"))
    flush_interval: int = field(default=100, metadata=knob("Ticks between Parquet row-group flushes.", "1..10^7"))
    compression: str = field(default="zstd", metadata=knob("Parquet compression codec.", "zstd|snappy|none"))
    abundance_event_threshold: int = field(default=16, metadata=knob("Abundance that emits a notable-type event.", "2..population_size"))


@dataclass(slots=True)
class VizConfig:
    enabled: bool = field(default=False, metadata=knob("Enable in-process visualization.", "true|false"))
    cell_px: int = field(default=8, metadata=knob("Rendered pixels per lattice cell.", "1..64"))
    fps_cap: int = field(default=60, metadata=knob("Maximum render frames per second.", "1..240"))
    render_every: int = field(default=1, metadata=knob("Simulation ticks between renders.", "1..10^6"))
    ticks_per_frame: int = field(default=1, metadata=knob("Ticks advanced per rendered frame at normal speed.", "1..10^4"))
    colour_mode: str = field(default="content_hash", metadata=knob("Active lattice colour mapping.", "content_hash|dominant_opcode|activity"))
    live_tunable: list[str] = field(
        default_factory=lambda: sorted(LIVE_TUNABLE_PATHS),
        metadata=knob("Config paths editable at tick boundaries.", "supported live-safe config paths"),
    )


@dataclass(slots=True)
class Config:
    run: RunConfig = field(default_factory=RunConfig)
    substrate: SubstrateConfig = field(default_factory=SubstrateConfig)
    world: WorldConfig = field(default_factory=WorldConfig)
    symbols: SymbolsConfig = field(default_factory=SymbolsConfig)
    energy: EnergyConfig = field(default_factory=EnergyConfig)
    dissolution: DissolutionConfig = field(default_factory=DissolutionConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    signals: SignalsConfig = field(default_factory=SignalsConfig)
    task: TaskConfig = field(default_factory=TaskConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    viz: VizConfig = field(default_factory=VizConfig)

    def validate(self) -> None:
        """Fail loudly for invalid or currently unsupported combinations."""

        if not 0 <= self.run.stage <= 5:
            raise ValueError("run.stage must be in 0..5")
        if self.run.seed < 0 or self.run.seed >= 2**63:
            raise ValueError("run.seed must be in 0..2^63-1")
        positive_values: tuple[tuple[str, int], ...] = (
            ("run.n_ticks", self.run.n_ticks),
            ("run.epoch_length", self.run.epoch_length),
            ("run.invariant_check_interval", self.run.invariant_check_interval),
            ("substrate.tape_length", self.substrate.tape_length),
            ("substrate.max_steps", self.substrate.max_steps),
            ("world.population_size", self.world.population_size),
            ("world.width", self.world.width),
            ("world.height", self.world.height),
            ("world.interaction_radius", self.world.interaction_radius),
            ("world.interactions_per_tick", self.world.interactions_per_tick),
            ("dissolution.inert_ticks", self.dissolution.inert_ticks),
            ("dissolution.starved_ticks", self.dissolution.starved_ticks),
            ("logging.flush_interval", self.logging.flush_interval),
            ("logging.tape_snapshot_interval", self.logging.tape_snapshot_interval),
            ("viz.cell_px", self.viz.cell_px),
            ("viz.fps_cap", self.viz.fps_cap),
            ("viz.render_every", self.viz.render_every),
            ("viz.ticks_per_frame", self.viz.ticks_per_frame),
        )
        for positive_name, positive_value in positive_values:
            if positive_value <= 0:
                raise ValueError(f"{positive_name} must be positive")
        if self.world.population_size < 2:
            raise ValueError("world.population_size must be at least two")
        if self.symbols.pool_multiplier <= 0.0:
            raise ValueError("symbols.pool_multiplier must be positive")
        try:
            pairing_mode = PairingMode(self.world.pairing_mode)
        except ValueError as error:
            allowed = ", ".join(mode.value for mode in PairingMode)
            raise ValueError(f"world.pairing_mode must be one of: {allowed}") from error
        if (
            pairing_mode is PairingMode.SHUFFLED_DISJOINT
            and self.world.interactions_per_tick > self.world.population_size // 2
        ):
            raise ValueError(
                "world.interactions_per_tick cannot exceed half of world.population_size "
                "when world.pairing_mode is shuffled_disjoint"
            )
        if self.run.stage < 2 and pairing_mode is PairingMode.LOCAL_NEIGHBORHOOD:
            raise ValueError("local_neighborhood pairing requires Stage 2 or later")
        if self.run.stage >= 2 and pairing_mode is not PairingMode.LOCAL_NEIGHBORHOOD:
            raise ValueError("Stage 2 or later requires local_neighborhood pairing")
        rates: tuple[tuple[str, float], ...] = (
            ("substrate.noop_density", self.substrate.noop_density),
            ("world.mutation_rate", self.world.mutation_rate),
            ("world.reseed_rate", self.world.reseed_rate),
            ("symbols.initial_tape_fill", self.symbols.initial_tape_fill),
            ("energy.decay", self.energy.decay),
            ("dissolution.spontaneous_rate", self.dissolution.spontaneous_rate),
            ("logging.interaction_log_rate", self.logging.interaction_log_rate),
        )
        for rate_name, rate_value in rates:
            if not 0.0 <= rate_value <= 1.0:
                raise ValueError(f"{rate_name} must be in 0..1")
        if self.run.stage >= 2 and round(
            self.world.width * self.world.height * self.symbols.initial_tape_fill
        ) < 2:
            raise ValueError("Stage 2 initial_tape_fill must create at least two tapes")
        if self.substrate.name not in {"bff", "ski"}:
            raise ValueError("substrate.name must be 'bff' or 'ski'")
        if self.run.stage == 0 and self.substrate.name != "bff":
            raise ValueError("Stage 0 implements only the BFF substrate; SKI requires Stage 1 conservation")
        if self.substrate.separate_tapes:
            raise ValueError("separate_tapes is exposed but is not implemented in Stage 0")
        if self.logging.compression not in {"zstd", "snappy", "none"}:
            raise ValueError("logging.compression must be zstd, snappy, or none")
        if self.logging.full_tape_snapshot_interval < 0:
            raise ValueError("logging.full_tape_snapshot_interval must be nonnegative")
        if self.viz.colour_mode not in {"content_hash", "dominant_opcode", "activity"}:
            raise ValueError("viz.colour_mode must be content_hash, dominant_opcode, or activity")
        unknown_tunables = set(self.viz.live_tunable) - LIVE_TUNABLE_PATHS
        if unknown_tunables:
            raise ValueError(f"unsupported viz.live_tunable paths: {sorted(unknown_tunables)}")
        if len(self.viz.live_tunable) != len(set(self.viz.live_tunable)):
            raise ValueError("viz.live_tunable paths must be unique")

    def apply_stage_gates(self) -> None:
        """Force features unavailable at the selected stage off, with warnings."""

        gated: list[tuple[str, bool]] = []
        if self.run.stage < 3:
            gated.append(("energy.enabled", self.energy.enabled))
            self.energy.enabled = False
        if self.run.stage < 2:
            gated.append(("dissolution.enabled", self.dissolution.enabled))
            self.dissolution.enabled = False
        if self.run.stage < 4:
            gated.extend((("signals.enabled", self.signals.enabled), ("task.enabled", self.task.enabled)))
            self.signals.enabled = False
            self.task.enabled = False
        for name, was_enabled in gated:
            if was_enabled:
                warnings.warn(f"{name} is forced off by run.stage={self.run.stage}", stacklevel=2)

    def to_dict(self) -> dict[str, Any]:
        """Return a TOML-compatible nested mapping."""

        return asdict(self)

    def save(self, path: str | Path) -> None:
        """Validate and serialize this configuration as TOML."""

        self.validate()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(tomli_w.dumps(self.to_dict()).encode("utf-8"))

    @classmethod
    def load(cls, path: str | Path) -> Config:
        """Load, stage-gate, and validate a TOML configuration."""

        with Path(path).open("rb") as handle:
            raw = tomllib.load(handle)
        known_sections = {field_.name for field_ in dataclasses.fields(cls)}
        unknown_sections = set(raw) - known_sections
        if unknown_sections:
            raise ValueError(f"unknown config sections: {sorted(unknown_sections)}")

        def section(name: str, section_type: type[T]) -> T:
            values = raw.get(name, {})
            if not isinstance(values, dict):
                raise ValueError(f"[{name}] must be a table")
            dataclass_type = cast(Any, section_type)
            allowed = set(dataclass_type.__dataclass_fields__)
            unknown = set(values) - allowed
            if unknown:
                raise ValueError(f"unknown [{name}] fields: {sorted(unknown)}")
            return section_type(**values)

        config = cls(
            run=section("run", RunConfig),
            substrate=section("substrate", SubstrateConfig),
            world=section("world", WorldConfig),
            symbols=section("symbols", SymbolsConfig),
            energy=section("energy", EnergyConfig),
            dissolution=section("dissolution", DissolutionConfig),
            environment=section("environment", EnvironmentConfig),
            signals=section("signals", SignalsConfig),
            task=section("task", TaskConfig),
            logging=section("logging", LoggingConfig),
            viz=section("viz", VizConfig),
        )
        config.apply_stage_gates()
        config.validate()
        return config
