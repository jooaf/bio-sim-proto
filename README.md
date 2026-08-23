# Conserved Program-Soup Evolution Simulator

A staged research simulator for self-modifying program evolution without an external fitness function.

The repository implements **Stages 0 and 1** and an initial **Stage 2 spatial scaffold**. Stages 0/1 provide a deterministic flat BFF tape soup with paper-style shuffled disjoint pairs, optional background mutation, raw Parquet logging, and offline analysis. Stage 1 adds an exactly conserved global byte pool that mediates every BFF and mutation write. The Stage 2 scaffold adds a toroidal occupancy lattice, local interactions, neutral dissolution, pool-funded random placement, spatial invariants, and permutation-based spatial analyses. Energy, signals, and task bias remain intentionally inactive.

## Setup

```nu
uv sync
uv run pytest
uv run mypy --strict soup analysis
uv run soup-run run experiments/configs/stage0.toml
uv run soup-run run experiments/configs/stage1.toml --report
uv run soup-run run experiments/configs/stage1_ski.toml --report
uv run soup-run run experiments/configs/stage2_smoke.toml --report
```

Each run is written beneath `runs/` and can be analysed with:

```nu
uv run soup-report runs/<run-directory> --stage 0
uv run soup-report runs/<run-directory> --stage 1
uv run soup-report runs/<run-directory> --stage 2
uv run soup-spatial-report runs/<run-directory> --block-size 8 --permutations 999
```

## Stage 1 symbol conservation

Stage 1 initializes a global pool from the initial soup's per-symbol histogram. A write from byte `old` to `new` atomically consumes `new` from the pool and returns `old`; unavailable writes are blocked without changing either tape or pool. The invariant checker and offline report independently verify that the 256-component vector `tape histogram + pool histogram` remains exactly constant.

Stage 1 supports BFF and a minimal fixed-tape prefix SKI chemistry. SKI reductions use atomic batch exchanges so a scarcity-blocked reaction cannot leave a malformed partial expression. It runs through the same world, scheduler, invariant, Parquet, and report pipeline; it is a substrate-independence fixture rather than a reproduction of chemSKI ecology.

Explicit token-path tracing is available via `experiments/metabolic_trace_probe.py`. Token IDs are audit labels for indistinguishable byte copies and reconstruct one valid return→pool→reacquisition history without changing byte-level dynamics. See `reports/phase1_final_report_2026-08-12.md` for the complete Phase 1 findings, `reports/phase1_campaign2_consolidated_report.md` for the conserved-economy selection campaign (batches 4–7), and `reports/phase1_papers_eli5_reading_guide.md` for a plain-language guide to every recommended paper.

## Paper-scale emergence probe

Detailed raw interaction logging is intentionally used only for tractable populations. The paper protocol requires roughly one billion interactions, so the repository also provides a deterministic Numba-compiled probe with bounded aggregate logging:

```nu
uv run soup-paper-probe --population-size 131072 --epochs 16000 --seed 0 --output reports/paper_probe_seed0.csv --checkpoint runs/paper_probe_seed0_transition.npy
```

The accelerated kernel uses the released implementation's SplitMix64 initialization, shuffle, mutation, and BFF execution semantics. Short-run regression tests compare its state to the reference implementation. The output records the paper's Brotli-based high-order entropy transition metric.

The exact-conservation Phase 1 probe (`experiments/phase1_probe.py`) additionally supports pool-economy manipulations for selection experiments: `--pool-mode uniform` (composition-mismatched pools), `--pool-mode excluded_top` / `excluded_list` with `--pool-exclude-top K` / `--pool-exclude-symbols 0,60,...` (zero-supply exclusion pools, mass-preserving), `--save-final-soup PATH` (checkpoints for continuation), and soup-vs-pool JSD metrics in `aggregate.csv`. See `reports/phase1_campaign2_consolidated_report.md`.

## Stage 2 spatial scaffold

Stage 2 uses explicit sparse occupancy on a toroidal lattice. Ordered interactions are local to a Moore neighborhood, dissolution returns every tape byte to the conserved pool, and exogenous random placement succeeds only when the pool can atomically supply a complete tape. Starvation dissolution is disabled until the Stage 3 energy ledger exists.

The clarified gate requires both free space and liveness, so an extinct empty world cannot pass. Spatial structure is measured with categorical neighbor-identity excess and block Hill beta diversity against seeded label-permutation nulls. See `reports/phase2_preregistration.md` for fixed semantics and `reports/phase1_closeout_and_phase2_handoff.md` for readiness and benchmark results.

The bounded benchmark can be reproduced with:

```nu
uv run python -m experiments.benchmark_stage2
```

The 64×64 measurement projects roughly 64 hours for 500,000 ticks under aggregate logging. This is a projection, not a completed Stage 2 acceptance run.

## Interactive Stage 0 viewer

```nu
uv sync
uv run soup-viz experiments/configs/stage0_viz.toml
uv run soup-viz experiments/configs/stage1_viz.toml
```

The square arrangement is only a display grid; interactions remain global rather than spatial. Identical content hashes share a colour, while recently modified tapes flash yellow. Stage 1 additionally displays the free conserved-symbol pool.

Controls: **Space** pause/resume, **Right/N** single-step, **Tab/Shift-Tab** select a live parameter, **[ / ]** decrease/increase it, **Shift+[ / ]** adjust faster, **Up/Down** change speed, **C** cycle colour mode, click either side of a parameter row to adjust it, click a tape to inspect it, **S** save a screenshot, and **Q/Escape** quit.

The supplied profiles expose every parameter that is safe to change at a tick boundary, including execution budget, head semantics, pairing protocol, interaction count, mutation rate, logging cadence/rate, render cadence, speed, and colour. Initialization/shape parameters such as seed, stage, population size, tape length, and initial pool multiplier remain TOML inputs because changing them requires a new experiment rather than mutating an existing run.

Every run preserves its complete initial configuration in `config.toml` and final effective configuration in `effective_config.toml`. Each accepted UI change is written immediately to `parameter_changes.jsonl`, duplicated as a `parameter_changed` Parquet event, and counted in `manifest.json`. Closing early still finalizes truthful logs in `runs/`.

See `FINDINGS.md` for stage-gate results and semantic notes.
