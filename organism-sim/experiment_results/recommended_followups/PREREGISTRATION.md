# Recommended follow-up experiments

## Shared configuration

All experiments use 300 founders, 8 elements, 48 molecules, mutation multiplier 1.0, maintenance multiplier 0.75, maturity multiplier 0.65, reproduction drive 1.25, reproduction cooldown 0.75, asexual floor 0.20, enabled sexual floor 0.12, decomposition 0.0008, and heat diffusion 0.08 unless explicitly varied. Aggregate metrics and lifecycle events remain per-tick; detailed state is recorded every 20 ticks and spatial snapshots every 100 ticks.

The new schema splits `reproduction_resource_blocks` into mutually exclusive cumulative causes:

- `reproduction_mate_readiness_blocks`;
- `reproduction_energy_blocks`;
- `reproduction_body_matter_blocks`.

Their sum must equal the legacy aggregate resource-block count at every recorded tick.

## F1 — 10,000-tick persistence

- Condition: maintenance 0.75, sexual floor 0.12, reproduction cost 0.75, 2,600 deposits, 8 founder archetypes.
- Seeds: 50–59.
- Runs: 10.
- Duration: 10,000 ticks.

Primary outcomes: extinction fraction, final population retention, births/death, and ordinary-least-squares population slope over ticks 8,001–10,000. A run is late-stable only if it is non-extinct and its late-window slope is not strongly negative; this remains descriptive with ten runs.

## F2 — Reproduction-cost × deposits factorial

- Reproduction cost: 0.50, 0.75.
- Initial deposits: 2,600, 4,900.
- Matched seeds: 60–64.
- Runs: 20.
- Duration: 2,500 ticks.
- Founder archetypes: 8.

Primary outcomes: final retention, births/death, aggregate resource-block rate, and the energy/body/mate cause fractions per attempt. Secondary outcomes: attrition per 1,000 organism-ticks, extinction, species evenness, and colonies.

Factor effects are computed within each seed, averaging over the other factor before a paired contrast. With five independent seed blocks, exact tests cannot attain two-sided p < 0.05; report paired bootstrap intervals, direction consistency, and effect sizes without declaring significance.

Hypotheses:

- Lower reproduction cost reduces energy blocking and increases replacement.
- More deposits reduce energy/body blocking and improve retention.
- Their combination may be sub-additive if both relieve the same bottleneck.

## F3 — Founder-archetype comparison

- Founder archetypes: 8 versus 21.
- Matched seeds: 65–69.
- Runs: 10.
- Duration: 2,500 ticks.
- Reproduction cost: 0.75; deposits: 2,600.

Mutation and all ecological parameters are fixed. Primary outcomes: final living species, species evenness, population retention, births/death, and resource-block causes. Report paired effects and direction consistency; do not claim significance from five seed pairs.

## Integrity criteria

Every run must:

1. complete its configured tick count;
2. have schema version 3;
3. preserve every element exactly relative to tick zero;
4. keep maximum absolute energy error below 1e-6;
5. satisfy aggregate resource blocks = mate + energy + body-matter blocks at every tick.
