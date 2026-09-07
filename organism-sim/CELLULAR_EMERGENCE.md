# Stochastic cellular affordances

## Non-goal: assigning higher-level identity

The kernel never sets `is_adaptable`, `is_multicellular`, `is_organelle`, a cell role, or a group-fitness bonus. It provides only generic heritable mechanisms. Any higher-level organization must be inferred offline from persistent physical relationships and counterfactual controls.

The feature is versioned as `stochastic-cellular-affordances-v1`, disabled by default, and currently Rust-only.

## Phase 1: generic intracellular modules

Each enabled genome carries a bounded, variable-length list of generic module genes. A module contains:

- one primitive affordance: catalysis, transport, storage, signaling, or structure;
- one molecule substrate;
- one generic compartment/localization tag;
- efficiency and energetic upkeep;
- a bias and six regulatory weights.

There are no named organelles. Structural mutation can duplicate, delete, reorder, retarget, or change the primitive of modules by chance. Continuous genes also mutate through the inherited mutation rate. Module expression costs chemical energy and therefore competes with maintenance and reproduction.

Catalytic expression can increase energy capture for its matching molecule without exceeding the consumed energy. Transport expression can increase uptake of its matching molecule, with proportionally higher ingestion cost. Other primitives participate in signaling, adhesion, exchange, and future substrate extensions. Unhelpful modules still pay upkeep and can be removed by selection.

## Phase 2: physical adhesion and exchange

Cells with expressed structural modules may form local bonds probabilistically. Formation depends only on:

- physical contact;
- receptor similarity;
- expressed structural capacity;
- configured encounter probability;
- stochastic draws.

Parent/child relatedness can raise retention probability through a heritable bond-retention gene. No persistent group entity or multicellularity flag is stored: the operational composite is re-derived from the connected components of the current bond graph.

With `emergence_coordinated_components=true`, every connected component with more than one living member acts as one physical unit:

- all members still pay their own upkeep and retain their own genomes, inventories, expression, damage, and possible turnover;
- at most one ready member supplies the component action per cadence, selected by the ordinary deterministic shuffled order rather than a fixed leader role;
- the slowest current member constrains the shared next-action time;
- movement is a rigid translation of every member, paid by every member and committed atomically only if the entire translated footprint is collision-free;
- members cannot target one another as prey, mates, or alliance partners while connected;
- spontaneous bond rupture or member death physically splits the graph, so the resulting components act independently on the next tick;
- signals and conservative energy exchange continue across every retained edge.

The previous abstract colony maintenance bonus is disabled while this substrate is active.

## Phase 3: developmental regulation

Every module is controlled by a compact inherited regulatory rule. Inputs are:

1. cellular energy fraction;
2. maintenance debt;
3. toxin pressure;
4. local heat;
5. current seasonal resource state;
6. signal received through physical bonds.

Identical genomes may therefore express different modules in different local states. The simulator does not name these states or score “differentiation.” Recorded expression vectors permit that hypothesis to be tested offline.

Growth and division remain governed by physical energy/matter and reproduction laws. A bonded component can propagate only when all of its members are reproductively ready and can pay their own costs. One descendant is constructed from each member’s matter and inherited genome; the complete set is placed atomically with the parent component’s relative geometry, and its internal bond topology is reconstructed. A placement or resource failure creates no partial propagule. The event probability is the geometric mean of member-level asexual probabilities, avoiding a component-size fitness bonus. Regulation influences these outcomes indirectly through module cost, uptake, catalysis, signaling, bonding, and exchange rather than through a hardcoded developmental target.

## Phase 4: bounded internal guests

A lethal predation event may, by chance, internalize the target instead of returning its matter immediately to the environment. Probability depends on heritable host engulfment, target tolerance, relative physical mass, and the global encounter rate.

An internal guest retains source organism/genome/species identifiers, matter inventory, energy, age, and an exchange tendency. It:

- pays independent maintenance;
- may conservatively transfer energy to its host;
- can be lost and dissolved back into host matter;
- can split its existing matter/energy into another guest;
- may be partitioned into offspring without duplicating matter.

These records are not called organelles by the kernel. Persistent vertically inherited guests with beneficial exchange would be evidence for an organelle-like transition only after lesion and null-model analysis.

## Configuration

```nu
uv run organism-sim-headless \
  --engine rust \
  --ticks 10000 \
  --cellular-emergence \
  --seasons \
  --set emergence_max_modules=12 \
  --set emergence_structural_mutation_rate=0.02 \
  --set emergence_module_cost=0.002 \
  --set emergence_module_effect=0.25 \
  --set emergence_bond_rate=0.01 \
  --set emergence_bond_break_rate=0.002 \
  --set emergence_exchange_rate=0.02 \
  --set emergence_engulfment_rate=0.01 \
  --set emergence_max_internal_guests=4 \
  --set emergence_coordinated_components=true
```

The GUI exposes reset-time controls for enablement, module limit, structural mutation, bonding, and engulfment. Set **Cell affordances** to `1` and press `R` to start the feature; coordinated groups automatically select the supported serial scheduler. The sidebar explicitly reports `CELLULAR OFF` when the feature is disabled and reports current/peak joined-group size when enabled. Active bonds are drawn as bright cyan links with gold markers (and optional `GROUP ×N` labels when zoomed in); press `B` to toggle those highlights. The inspector displays only module, localization-tag, bond, and guest facts.

## Run data

`metrics.jsonl` records generic facts rather than conclusions:

- total and expressed module instances;
- primitive and localization-tag counts;
- physical bond count and bonded-cell count;
- connected-component count and largest component size;
- regulatory-expression variance;
- internal guest count;
- bond formation/breakage and energy-exchange counters;
- component actions, rigid moves, complete propagules, and propagated-cell counts;
- internalization, guest split, and guest-loss counters;
- species populations and existing ecology metrics.

`final_state.npz` includes flattened module genes/expressions with per-cell offsets, bond endpoints/strength/formation ticks, derived `component_id`/`component_size` arrays, and internal-guest identifiers, ages, energy, matter, and offsets.

No “adaptability,” “multicellularity,” “differentiation,” or “organelle” score is emitted.

## Reachability and performance gates

A 300-founder, 500-tick seed-7 smoke run with elevated encounter rates produced stochastic regulatory variation, transient physical bonds, and one internalization without any target-state assignment. It ended with 679 free cells, 2 physical bonds, 1 retained internal guest, exact matter conservation, and energy error `4.66e-10`. This demonstrates mechanism reachability, not evolved higher-level organization.

Three matched 1,200-founder release runs (50 warm-up + 300 measured ticks) averaged:

| mode | mean ticks/s | final population |
|---|---:|---:|
| disabled | 345.2 | 1,136 |
| enabled, all ecological effects zero | 315.2 | 1,136 |
| active defaults | 316.7 | 1,103 |

The zero-effect treatment preserved the physical ecology exactly and measured an 8.7% scheduler/regulation overhead. Active and disabled populations diverge, so their raw rates are not a pure overhead comparison. The kernel reuses bond, signal, edge, and living-ID scratch buffers; per-cell module vectors remain bounded by configuration.

A 300-founder, 1,200-tick high-encounter reachability run produced 2,023 component actions, 40 rigid component moves, and one complete two-cell propagule while preserving matter and energy. This demonstrates that propagation is reachable, not that it is selectively stable.

Three matched 1,200-founder release runs averaged 477.9 ticks/s with cellular affordances active but component coordination disabled and 471.6 ticks/s with coordination enabled. Raw coordination overhead was 1.3%; trajectories ended at 1,113 and 1,085 cells respectively, so population-normalized rates are not directly equivalent. A paired 1,200-founder/750-tick SDL benchmark retained **96.2%** of matched headless throughput with coordination active.

## Required scientific controls

Evidence requires replicated runs and predeclared criteria. Recommended controls include:

- feature disabled;
- enabled with zero structural/bond/engulfment rates;
- signal-disabled and exchange-disabled lesions;
- shuffled bond partners;
- guest removal and guest-exchange lesions;
- matched seasons-disabled and seasons-enabled runs.

Persistence, division of expression, mutual dependence, vertical transmission, and transition-aligned survival should be computed offline. This implementation creates reachable mechanisms; it does not claim that a higher-level organism has evolved.

## Current limitations

- Compartment tags are generic localization domains, not yet separate membrane inventories with explicit permeability.
- Component propagation is currently asexual. Contact with an external mate does not merge or pair two component topologies.
- A component has no shared inventory or shared integrity pool; exchange remains local and member death can remove or split parts.
- Rotating action authority uses one member controller per component cadence rather than aggregating all controller outputs into a vote.
- Internal guests are reduced cellular records rather than fully scheduled free-living controllers while internalized.
- Module material is represented by the cell’s conserved body inventory; module organization has explicit energy upkeep but does not yet reserve named structural molecule batches.

These limitations should be addressed only with generic physical rules, not by adding target biological identities.
