"""Generate explicit reproducible Spatial Stringmol host/parasite configurations."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


HOST = "WWGEWLHHHRLUEUWJJJRJXUUUDYGRHJLRWWRE$BLUBO^B>C$=?>$$BLUBO%}OYHOB"
PARASITE_R = "WWGEWLHHHRLUERWWRE$BLUBO^B>C$=?>$$BLUBO%}OYHOB"
Condition = Literal["host-only", "parasite-only", "mixed"]


@dataclass(frozen=True, slots=True)
class StringmolControlConfig:
    condition: Condition
    seed: int
    interaction_radius: int
    placement_radius: int
    nsteps: int = 5_000
    grid_width: int = 40
    grid_height: int = 40
    mutation_rate: float = 0.0002
    decay_rate: float = 0.0005
    report_every: int = 100
    image_every: int = 1_000_000

    def validate(self) -> None:
        if self.condition not in {"host-only", "parasite-only", "mixed"}:
            raise ValueError("unknown Stringmol control condition")
        if self.seed < 0 or self.nsteps <= 0:
            raise ValueError("seed must be nonnegative and nsteps positive")
        if self.interaction_radius not in {0, 1} or self.placement_radius not in {0, 1}:
            raise ValueError("audited Stringmol radii are 0 (global) and 1 (local)")
        if self.grid_width < 15 or self.grid_height < 10:
            raise ValueError("grid must fit the fixed 15x10 inoculum")


def inoculum() -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Return 140 host cells and a centered ten-cell parasite stripe."""

    all_cells = [(x, y) for y in range(15, 25) for x in range(12, 27)]
    parasite_cells = [(19, y) for y in range(15, 25)]
    parasite_set = set(parasite_cells)
    host_cells = [cell for cell in all_cells if cell not in parasite_set]
    if len(host_cells) != 140 or len(parasite_cells) != 10:
        raise AssertionError("fixed Stringmol inoculum has the wrong size")
    return host_cells, parasite_cells


def render_config(config: StringmolControlConfig, matrix_path: Path) -> str:
    """Render one config using Stringmol's explicit one-agent-per-record loader."""

    config.validate()
    host_cells, parasite_cells = inoculum()
    agents: list[tuple[str, str, tuple[int, int]]]
    if config.condition == "host-only":
        agents = [(HOST, "Q", cell) for cell in host_cells]
    elif config.condition == "parasite-only":
        agents = [(PARASITE_R, "R", cell) for cell in parasite_cells]
    else:
        agents = [(HOST, "Q", cell) for cell in host_cells] + [
            (PARASITE_R, "R", cell) for cell in parasite_cells
        ]
    lines = [
        "%% Generated Phase 2 pinned Spatial Stringmol control",
        f"GRIDX {config.grid_width}",
        f"GRIDY {config.grid_height}",
        "CELLRAD 2500",
        "AGRAD 10",
        "ENERGY 0",
        "ESTEP 2500",
        f"NSTEPS {config.nsteps}",
        f"DECAY {config.decay_rate:.10g}",
        f"MUTATE {config.mutation_rate:.10g}",
        f"REPORTEVERY {config.report_every}",
        f"IMAGEEVERY {config.image_every}",
        f"INTERACTION_RADIUS {config.interaction_radius}",
        f"PLACEMENT_RADIUS {config.placement_radius}",
        f"RANDSEED {config.seed}",
        f"SUBMAT {matrix_path.resolve()}",
        f"NUMAGENTS {len(agents)}",
        "",
    ]
    for sequence, label, (x, y) in agents:
        lines.append(f"AGENT {sequence} 1 {label}")
        lines.append(f"GRIDPOS {x} {y}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", choices=("host-only", "parasite-only", "mixed"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--interaction-radius", type=int, choices=(0, 1), required=True)
    parser.add_argument("--placement-radius", type=int, choices=(0, 1), required=True)
    parser.add_argument("--nsteps", type=int, default=5_000)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = StringmolControlConfig(
        condition=args.condition,
        seed=args.seed,
        interaction_radius=args.interaction_radius,
        placement_radius=args.placement_radius,
        nsteps=args.nsteps,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_config(config, args.matrix), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
