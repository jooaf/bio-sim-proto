# Random environment seasons

## Scientific rule

`random-environment-seasons-v1` changes the environment, never an organism or species directly.

A season profile contains:

- a global deposit-energy recharge multiplier;
- a global chemical-decomposition multiplier;
- one recharge affinity per molecule type.

Deposit matter is unchanged. Existing environmental heat is converted into chemical energy at season-dependent rates, and decomposition returns chemical energy to heat. Matter remains exact and total energy remains conserved. No season reads species IDs, genomes, guilds, phenotype traits, population, fitness, or controller state.

Consequently, “adaptability” is not a trait or bonus in this implementation. It can emerge only when inherited metabolism, food affinity, movement, memory, reproduction, or ecological interactions happen to remain viable across changing resource profiles and are selected over generations.

## Randomness and replay

Seasons use a fifth RNG stream derived independently from the run seed. Season generation therefore does not consume chemistry, world, founder, or ecological-dynamics draws.

For each season:

1. Duration is sampled uniformly from the configured inclusive bounds.
2. A climate draw correlates resource recharge and decomposition: resource-rich profiles recharge faster and decompose more slowly; harsh profiles do the reverse.
3. Molecule recharge affinities are sampled independently and normalized to mean 1.0, changing which molecule deposits recharge fastest without systematically adding energy.
4. The current profile interpolates linearly to the next profile over `season_transition_ticks`.

The complete season state and RNG are included in the native deterministic digest when seasons are enabled. Disabled seasons preserve the established scalar ecology digests. A zero-strength enabled schedule changes only season metadata and was tested to preserve the neutral physical ecology exactly.

## Configuration

Seasons are disabled by default for backward compatibility and currently require the Rust engine.

| field | default | meaning |
|---|---:|---|
| `seasons_enabled` | `false` | enable the exogenous schedule |
| `season_duration_min` | `500` | shortest season in ticks |
| `season_duration_max` | `1500` | longest season in ticks |
| `season_transition_ticks` | `100` | smooth blend duration |
| `season_strength` | `0.65` | variability from 0 (neutral) to 1 |

```nu
uv run organism-sim-headless \
  --engine rust \
  --ticks 10000 \
  --seasons \
  --season-duration-min 500 \
  --season-duration-max 1500 \
  --season-transition 100 \
  --season-strength 0.65
```

The GUI exposes startup/reset sliders for enablement, strength, duration bounds, and blend duration. These fields are intentionally not live-updateable because changing the schedule mid-run would complicate causal provenance.

## Run data

Native headless and GUI manifests point to `season_events.jsonl`. Every event is retained even when several transitions occur between metric/snapshot intervals. Event rows include:

- season index and start tick;
- transition end and next-season ticks;
- complete source and target scalar multipliers;
- complete source and target molecule-affinity vectors;
- schema version and enabled state.

`metrics.jsonl` records:

- `seasons_enabled`;
- `season_index` and transition progress;
- current resource/decomposition multipliers;
- aligned `species_ids` and `species_populations`;
- existing births, deaths, reproduction failures, population, and ecological counters.

This supports transition-aligned analyses such as per-species growth, extinction hazard, recovery time, dominance turnover, and lagged response without inventing an “adaptability score.” Any adaptability metric should be an offline analysis defined before examining outcomes.

## Efficiency

Season scheduling is O(1) except for one O(number of molecule types) interpolation per tick (48 values by default). Deposit production already visits active deposit batches; the seasonal affinity adds one indexed multiply and one accumulator to that existing loop. No per-organism seasonal branch or allocation is added.

Season events are retained at transition frequency, not tick frequency. Python recording requests only events after its previous cursor, preventing quadratic event copying during long runs.

Five 1,200-founder release runs (50 warm-up + 300 measured ticks, seed 7) averaged 343.9 ticks/s with seasons disabled and 341.2 ticks/s with a zero-strength neutral schedule, a measured overhead of about **0.8%**. Moderate strength averaged 344.7 ticks/s on its slightly different population trajectory. All treatments passed matter and energy audits.

## Recommended experiments

Use paired seeds and keep all non-season settings fixed:

1. seasons disabled;
2. seasons enabled with strength 0 (scheduler/provenance control);
3. moderate seasons (`0.4–0.65`);
4. strong seasons (`0.8–1.0`).

Do not claim evolved adaptability from a single run. Predefine replicate count, burn-in, transition-aligned response metrics, extinction handling, and whether the SIMD/scalar recurrent mode is fixed across the experiment.
