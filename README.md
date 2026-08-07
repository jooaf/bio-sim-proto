# Conserved Program-Soup Evolution Simulator

A staged research simulator for self-modifying program evolution without an external fitness function.

The repository currently implements **Stage 0 only**: a deterministic, flat BFF tape soup with random ordered interactions, raw Parquet logging, and offline analysis. Conservation, energy, dissolution, space, signals, and task bias are intentionally not active yet.

## Setup

```sh
uv sync
uv run pytest
uv run mypy --strict soup analysis
uv run soup-run run experiments/configs/stage0.toml
```

Each run is written beneath `runs/` and can be analysed with:

```sh
uv run soup-report runs/<run-directory> --stage 0
```

## Interactive Stage 0 viewer

```sh
uv sync
uv run soup-viz experiments/configs/stage0_viz.toml
```

The square arrangement is only a display grid; Stage 0 interactions remain globally random. Identical content hashes share a colour, while recently modified tapes flash yellow.

Controls: **Space** pause/resume, **Right/N** single-step, **Up/Down** change speed, **C** cycle colour mode, click a tape to inspect it, **S** save a screenshot, and **Q/Escape** quit. Closing early still finalizes truthful raw logs in `runs/`.

See `FINDINGS.md` for stage-gate results and semantic notes.
