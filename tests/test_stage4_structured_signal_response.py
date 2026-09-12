from __future__ import annotations

import pandas as pd

from experiments.analyze_stage4_structured_signal_response import passes_gate
from soup.config import Config
from soup.signals import SignalField
from soup.substrate.bff import BFFSubstrate
from soup.world import SpatialWorld
from soup.rng import make_rng


def test_split_x_signal_field_has_two_exact_halves() -> None:
    config = Config()
    config.world.width = 4
    config.world.height = 4
    config.symbols.initial_tape_fill = 1.0
    config.signals.signal_spec = "split_x"
    config.signals.initial_tag_hex = "aabbccdd"
    config.signals.secondary_tag_hex = "11223344"
    world = SpatialWorld.create(
        width=4,
        height=4,
        initial_tape_fill=1.0,
        substrate=BFFSubstrate(),
        rng=make_rng(7),
    )
    field = SignalField.create(world, config.signals)
    for index in range(world.capacity):
        x, _ = world.cell(index)
        assert field.tag_at(index).hex() == ("aabbccdd" if x < 2 else "11223344")


def test_structured_response_gate_accepts_exact_spatial_pattern() -> None:
    rows: list[dict[str, object]] = []
    for seed in range(202609290, 202609295):
        for arm in ("split", "uniform", "disabled"):
            enabled = arm != "disabled"
            rows.append({
                "seed": seed, "arm": arm, "all_reads_dispatch": enabled,
                "spatial_rule_exact": True, "left_all_uptake": arm != "disabled",
                "right_zero_uptake": arm != "uniform", "all_cells_uptake": arm == "uniform",
                "all_cells_zero_uptake": arm == "disabled", "signal_reads": 1600 if enabled else 0,
                "signal_dispatches": 1600 if enabled else 0,
                "left_mean_energy": 9.0 if enabled else 0.0,
                "right_mean_energy": 9.0 if arm == "uniform" else 0.0,
                "final_tapes": 16, "unchanged_tapes": True, "successful_exit": True,
                "invariant_failures": 0, "max_relative_energy_error": 1e-12,
            })
    assert passes_gate(pd.DataFrame(rows))
