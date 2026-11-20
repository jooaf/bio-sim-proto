"""Typed boundary records for canonical locality evidence (old receipts readable)."""
from typing import TypedDict
from experiments.stringmol.locality_process import FileRecord


class Checkpoint(TypedDict):
    tick: int
    event: str
    population: int
    occupied_neighbor_slots: int
    neighbor_slots: int


class Edge(TypedDict):
    transfer_eligible: bool
    source: int


class Renewal(TypedDict):
    transfer_edges: list[Edge]


class ReplayResult(TypedDict):
    end_tick: int
    end_population: int
    rng_draws: int
    searches: int
    empty_searches: int
    encounters: int
    bindings: int
    proposals: int
    placed: int
    failed_placement: int
    vacancy_sum: int
    checkpoints: list[Checkpoint]
    renewal: Renewal


class ReplayReceipt(TypedDict):
    kind: str
    exit_code: int | str
    log: FileRecord
    result: FileRecord | None


class Diagnostic(TypedDict):
    native_exit_codes: dict[str, int | str]
    inventories: dict[str, bool]
    replays: list[ReplayReceipt]
    exact_repeat: bool
    common_file_parity: bool
    disabled_streams: list[str]
    full_observer_off: bool


class Diagnostics(TypedDict):
    arms: dict[str, Diagnostic]


class Summary(TypedDict, total=False):
    arm: str
    seed: int
    independent_seeds: int
    native_executions: int
    native_successes: int
    repeat_bytes: bool
    partial_observer_parity: bool
    full_observer_off: bool
    replay_passes: int
    end_tick: int
    end_population: int
    population4900: int
    births: int
    partial_transfers: int
    nonfounder_sources: int
    searches: int
    empty_searches: int
    encounters: int
    bindings: int
    nonempty_cleavage_attempts: int
    failed_placements: int
    vacancy_sum: int
