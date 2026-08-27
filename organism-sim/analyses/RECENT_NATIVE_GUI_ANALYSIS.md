# Recent native-GUI run analysis (2026-08-24)

## Data reviewed

The analysis covered the 24 native GUI records beginning with
`20260824T022229...` and ending with
`20260824T054610...`. Zero-tick reset records were retained as provenance but
excluded from ecological interpretation.

The most recent completed run was:

```text
runs/20260824T054610.606059Z-seed85-rust-gui-c5246f32/
```

Its final state was exactly matter-conserving and passed the configured energy
audit.

## Main observations

### 1. The newest ecology was still expanding, not equilibrated

Seed 85 grew from 50 to 5,608 organisms over 18,938 ticks. In the final 20% of
simulation time:

- mean population was 3,964;
- population trend was +35.0% per 1,000 ticks;
- births/death was 1.206.

The final population was therefore not a stable carrying-capacity estimate.
The infinite native world expanded from 18 to 786 generated chunks and from
2,027 to 177,289 deposit positions. Expansion into procedurally generated
geology remained a major resource source.

### 2. Diversity and abundance moved in opposite directions

The newest run began with three living founder species and ended with one,
even while population increased more than 100-fold. This is ecological and
species diversity collapse rather than global extinction.

The older GUI schema retained only living-species count, so dominance and
evenness could not be reconstructed for runs ending with more than one
species. New recordings now include dominant-species population and share.

### 3. Reproduction was selected frequently but rejected probabilistically

At the final tick:

- reproduction attempts: 175,918;
- successful reproductions: 30,081 (17.1%);
- probability failures: 138,789 (78.9% of attempts);
- body-matter blocks: 10,409 (5.9%);
- energy and placement blocks: zero.

This configuration did not have an energy-access reproduction bottleneck.
Changing maintenance or resource supply to increase births would target the
wrong mechanism and could worsen the ongoing population expansion.

### 4. Scale erased most interactive throughput

Median measured throughput fell from approximately 404 ticks/s in the early
10–30% tick window to 18.6 ticks/s in the final 20%, retaining 4.6%. The final
sample was 10.45 ticks/s. This is consistent with the existing finding that
rich per-organism perception/decision work dominates at large populations.

### 5. Interactive parameter provenance was missing

Several seed-78 runs have identical startup manifests but materially different
trajectories. The native GUI allowed live slider changes, but schema version 1
recorded only startup configuration. These runs cannot support causal claims
about parameter changes because the effective configuration history is
unknown.

This is the highest-confidence defect exposed by the recent data. Ecological
defaults were deliberately not retuned from confounded interactive runs.

## Implemented improvements

1. Native GUI recording schema 2 writes exact kernel-application ticks and
   values to `config_events.jsonl` for every live simulation update.
2. Native metrics now record dominant-species population and share.
3. `organism-sim-report` now discovers and summarizes compact Rust GUI/headless
   records as well as SQLite records.
4. Native reports quantify final-20%-of-ticks population trend, turnover,
   reproduction failure composition, world expansion, throughput retention,
   conservation, and configuration provenance.
5. The SQLite report's late-window calculation was corrected from the final
   80% of samples to the final 20%, and its trend is now reported in actual
   percent rather than fractional units mislabeled as percent.

These changes improve experiment interpretability without changing simulation
dynamics or retroactively choosing new ecological defaults from exploratory
runs.

## Recommended next experiment

Use schema-2 recording for a preregistered paired-seed comparison in which each
run has no live parameter changes, or in which every intended change and tick
is declared beforehand. Compare at least:

- late population trend and births/death;
- dominant-species share;
- chunks generated per 1,000 ticks;
- reproduction failure composition;
- throughput at matched population windows.

Only after replicated causal data should resource production, reproduction
probability, or species thresholds be changed globally.
