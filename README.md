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

See `FINDINGS.md` for stage-gate results and semantic notes.
