# Emergent Organism Simulation — Initial Specification

## Status

The conceptual specification is complete and implementation-ready. The prototype defaults in Section 40.3 are confirmed but remain configurable. No implementation code is defined here. Python with pygame-ce is the prototype target, with batch-oriented Rust FFI reserved for measured hotspots.

## 1. Purpose

Build an interactive grid-based ecosystem in which procedurally generated organisms attempt to survive and reproduce under explicit conservation of matter and energy.

The simulation should support evolutionary and ecological emergence rather than assigning fixed strategies such as "predator" or "detoxifier." Genomes provide capabilities, costs, probability distributions, and behavioral tendencies. Environmental selection determines which combinations persist.

The initial target is hundreds of organisms so the system can be observed, debugged, and balanced interactively.

## 2. Core principles

1. Matter is neither created nor destroyed after world initialization.
2. Energy is neither created nor destroyed; it moves among chemical energy, environmental heat, stored mana, and temporary magical effects.
3. Individual elements are discrete and represented by integer counts.
4. Energy values are continuous simulation quantities.
5. Heritable distributions, realized biological traits, and mutable organism state are separate concepts.
6. Random traits create variation; environmental costs and reproductive success create emergence.
7. The first implementation favors transparent rules and auditability over chemical or biological realism.
8. Mechanics should remain replaceable so a simple behavioral policy can later become a neural policy.

## 3. World model

### 3.1 Topology

The world is a finite two-dimensional toroidal grid:

- Moving past the left edge enters from the right.
- Moving past the right edge enters from the left.
- Moving past the top enters from the bottom.
- Moving past the bottom enters from the top.
- Distance, sight, targeting, contact, pathfinding, occupied footprints, and heat diffusion all use wrapped coordinates.

There are no walls or ecologically privileged edge tiles.

### 3.2 Time

The simulation uses fixed ticks.

Organisms may act at different tick intervals according to speed and action cost. Slow organisms do not need to perform a full decision update every tick. Environmental systems such as heat diffusion may also run at configurable intervals.

### 3.3 Initial scale

The initial target is hundreds of organisms. The design must avoid all-pairs organism checks and molecule-per-object representations even at this scale.

## 4. Matter and chemistry

### 4.1 Elements

Elements are procedurally generated at the beginning of each run. An element definition includes:

- Stable run-local identifier
- Integer mass per unit
- Maximum chemical-energy contribution
- Chemical descriptors
- Initial world abundance

Elemental matter is represented by integer counts. Individual element objects are not required; inventories may store counts while preserving discreteness.

### 4.2 Molecule types

A molecule type includes:

- Stable run-local identifier
- Integer elemental composition vector
- Molecular mass derived from its elements
- Maximum chemical-energy capacity
- Chemical descriptors
- Stability
- Supported generated reaction pathways

The maximum energy capacity of one molecule is the sum of the energy contributions of its constituent elements.

### 4.3 Molecule batches

Molecules are stored in aggregated batches rather than one runtime object per molecule. A batch contains:

- Molecule type identifier
- Integer molecule count
- Continuous current chemical energy
- Location or owner

The current energy of a batch must remain between zero and the batch's maximum capacity.

This separates discrete molecular matter from continuous stored energy.

### 4.4 Reactions

The initial simulation supports generated, constrained reactions for:

- Digestion
- Metabolic energy transfer
- Waste production
- Detoxification
- Corpse decomposition

It does not initially implement unrestricted general-purpose molecule-to-molecule chemistry.

Every reaction must satisfy:

- Input element counts equal output element counts.
- Input total energy equals output chemical energy, stored mana, active-effect energy, and expelled heat.

### 4.5 Ecological molecular competition

Molecule types do not act as autonomous competing agents. Their ecological persistence is determined by:

- Initial abundance
- Organism consumption preferences
- Digestibility
- Waste production
- Detoxification products
- Corpse decomposition
- Chemical stability
- Spatial availability
- Reaction rates

Organism preferences should primarily match molecular descriptors and elemental proportions rather than hard-coded molecule identifiers. This allows organisms to react meaningfully to newly generated molecules.

## 5. Energy, heat, and mana

### 5.1 Energy reservoirs

Global energy is distributed among:

1. Chemical energy stored in molecules
2. Environmental heat stored in grid cells
3. Mana stored by organisms
4. Energy temporarily committed to active magical effects

The conservation invariant is:

`chemical energy + environmental heat + stored mana + active-effect energy = initial total energy`

### 5.2 Energy cycle

- Movement and ordinary chemical activity consume chemical energy and expel environmental heat.
- Organisms may absorb heat from tiles occupied by their footprints and convert it into stored mana.
- Imperfect heat-to-mana conversion leaves the unconverted portion as heat.
- Magical effects consume mana.
- Energy committed to a magical effect returns to environmental heat when the effect resolves.
- Passive or global mana decay converts mana into environmental heat; it does not delete energy.
- Environmental heat diffuses through neighboring cells, including across wrapped edges.

Heat remains recoverable. There is no permanently inaccessible heat reservoir in the initial design.

### 5.3 Permitted uses of mana

Mana may pay for:

- Magical abilities
- Basal metabolic maintenance
- Survival support beyond an organism's expected lifespan

Mana may not directly pay for:

- Movement
- Growth
- Structural repair material
- Reproductive material
- Creation of molecules or body mass

A heat-harvesting organism may remain alive while relatively inactive, but it still requires chemical energy and elemental matter to move, grow, repair, and reproduce.

### 5.4 Auditing

The simulation should maintain global matter and energy ledgers. Numerical energy equality may use a small tolerance because energy is represented continuously.

## 6. Biological data hierarchy

### 6.1 Global priors

Global priors are generated once per run and govern the kinds of genomes, trait distributions, molecules, and mutations that can initially occur.

### 6.2 Genome

A genome is heritable. It contains probability distributions, constraints, strategy weights, mutation behavior, and reaction capabilities.

### 6.3 Phenotype

A phenotype contains concrete traits sampled from a genome at birth. Genetically related organisms can therefore differ without having unrelated genomes.

### 6.4 Organism state

Organism state contains quantities that change during life, including position, inventories, energy, mana, age, toxins, intentions, reproductive readiness, and relationships.

### 6.5 Species state

A species record tracks ancestry, genomic distribution, reproductive compatibility, population history, and persistence. A species is not identical to one genome.

## 7. Genome trait groups

The genome covers the following trait groups. Sections 18–21 define their exact distribution representation, nested schema, phenotype sampling, and mutable organism state.

### 7.1 Morphology

- Birth-size distribution
- Adult-size distribution
- Body composition
- Shape
- Density
- Growth rate
- Structural durability
- Repair efficiency

### 7.2 Metabolism and thermal traits

- Basal metabolic-rate distribution, independent of size
- Digestion efficiency
- Chemical-energy storage capacity
- Intake rate
- Starvation tolerance
- Activity-cost curve
- Preferred reserve level
- Heat-detection capability
- Heat-absorption rate
- Heat-to-mana efficiency
- Mana capacity
- Mana leakage or decay rate

### 7.3 Locomotion and behavior

- Maximum speed
- Locomotion efficiency
- Speed preference
- Rest preference
- Exploration tendency
- Food-pursuit tendency
- Predator-avoidance tendency
- Attack tendency
- Energy-conservation tendency
- Heat-seeking tendency
- Risk tolerance
- Memory duration

### 7.4 Diet, chemistry, and toxicity

- Preferred elemental composition
- Preferred molecular descriptors
- Digestible chemical descriptors
- Capture or bite capability
- Toxicity sensitivity profile
- Digestive pathways
- Waste pathways
- Detox pathways
- Detox activation thresholds
- Detox energy costs

### 7.5 Magic

The four magical channels are fire, water, earth, and air. They are effect categories and are separate from chemical elements.

Genome traits include:

- Affinity for each channel
- Resistance to each channel
- Casting efficiency
- Offensive tendency
- Defensive tendency
- Escape tendency
- Mana reserve preference

Magic cannot create elemental matter. Any damage must leave the affected matter in the simulation as body material, fragments, corpses, or waste.

### 7.6 Aging and death

- Lifespan distribution
- Age-hazard curve
- Energy survival modifier
- Mana survival modifier
- Senescence rate
- Injury recovery rate

Death is modeled as a probability or hazard rather than a guaranteed event at an exact age. High energy or mana may reduce age-related mortality after the expected lifespan, but does not grant unconditional immortality.

### 7.7 Reproduction

- Asexual reproduction propensity
- Sexual reproduction propensity
- Minimum and preferred sexual participant count
- Sexually produced offspring-count distribution
- Maturity distribution
- Reproductive energy threshold
- Reproductive material threshold
- Compatibility sensitivity
- Mate-recognition traits
- Mutation rate and magnitude
- Recombination strength
- Parent-contribution weighting
- Offspring investment

### 7.8 Sociality and multicellularity

- Alliance tendency
- Partner-recognition profile
- Resource-sharing tendency
- Symbiosis persistence
- Specialization tendency
- Colony formation tendency
- Colony role preferences
- Cheater tolerance
- Composite reproduction tendency

### 7.9 Perception

- Base sight range
- Maximum sight range
- Sensory efficiency
- Sensory energy cost
- Food, threat, heat, mate, and magic detection strengths

Sight is determined by genome and phenotype. Species age does not grant sight improvements. Larger sight windows impose greater energy costs because more cells must be observed.

## 8. Size and spatial footprint

Body size affects the number and shape of occupied tiles. A practical initial distribution is log-normal, allowing many small organisms and a few large ones.

An organism has an anchor tile and a connected footprint mask. Footprints may cross wrapped world edges.

Size affects:

- Occupied area
- Collision and contact
- Structural material requirements
- Food capacity
- Reproductive material requirements
- Movement cost

Basal metabolism remains independently inherited. A large organism may have a low resting metabolism. Movement cost should still account for moved mass, distance, speed, and locomotion efficiency.

## 9. Behavior policy

The initial controller is a stochastic weighted-utility policy.

Each possible action receives a score based on sensed features, inherited weights, current state, and predicted energy cost. The organism normally favors higher-scoring actions while retaining some randomness.

Initial action categories include:

- Rest
- Explore
- Approach food
- Eat
- Flee
- Pursue
- Attack
- Detoxify
- Excrete
- Seek heat
- Absorb heat
- Cast magic
- Seek mates
- Reproduce
- Offer or maintain an alliance
- Share resources

This controller is intentionally compatible with a future neural policy: observations remain inputs and action categories remain outputs.

### 9.1 Implemented Rust behavior schemas

The Rust kernel exposes three executable, startup-selected treatments:

- `legacy_linear_macro_v1`: the historical 10-feature/13-macro control;
- `linear_intent_v2`: a 28-feature egocentric observation, up to 33 eligible lower-level candidates, and a developmental 451-locus direct genetic scorer;
- `recurrent_intent_v2`: the same direct scorer plus 528 hidden/recurrent loci, for 979 neural loci total, and eight units of bounded recurrent state.

V2 intent kinds are wait, one-tile move, ingest, repair, absorb heat, detox, physical attack, cast magic, reproduce, and propose alliance. The selected intent is immediately revalidated and committed under the existing serial scheduler. Invalid intents become wait without resampling.

The complete V2 brain is inherited from one coherent parent during sexual reproduction, then mutated and developmentally sampled. Recurrent founders have exactly zero recurrent expression and retention; ordinary offspring mutation can activate them. Hidden expression is low but nonzero, and the neural residual begins near zero. Recurrent state is bounded to `[-1, 1]` and numerical failure deterministically clears state and selects wait.

V2 pays a chemical-only base brain cost every upkeep tick. The recurrent treatment additionally pays in proportion to developed hidden expression and `hidden_expression × recurrent_expression`; all paid energy becomes local heat. `recurrent_state_lesion` clears and withholds state while preserving expression costs. Setting `brain_recurrent_cost` to zero defines the separate zero-cost control. Founder viability priors are explicit and can be disabled with `v2_founder_priors_enabled` for random-policy controls. `memory_probe_enabled` adds RNG-free observational scoring of the same candidates with prior state versus zero state; it never commits the counterfactual.

The first preregistered replicated matrix found that recurrent state sometimes changes score argmaxes, but it did not establish a lesion-sensitive ecological benefit, beneficial delayed-food return, or replicated selection for recurrent expression. It therefore does not support an evolved-memory claim. Full design and results are in [`NEUROEVOLUTION_DESIGN.md`](NEUROEVOLUTION_DESIGN.md) and [`NEUROEVOLUTION_STAGE4_RESULTS.md`](NEUROEVOLUTION_STAGE4_RESULTS.md).

## 10. Toxicity and detoxification

Toxicity is an interaction rather than a universal molecule flag. Its effect depends on:

- Molecular descriptors
- Organism sensitivity
- Dose
- Exposure duration
- Active detox pathways
- Available energy and mana

Detoxification transforms toxic molecules into less harmful waste while preserving element counts and energy. Whether an organism activates detoxification depends on its inherited strategy, toxin load, and expected energetic benefit.

## 11. Reproduction and genomic compatibility

### 11.1 Readiness

Reproduction may require:

- Physical contact
- Maturity
- Compatible participants
- Reproductive readiness from every participant
- Sufficient chemical energy
- Sufficient elemental material
- Acceptable health and toxin load

### 11.2 Multi-participant sexual reproduction

Sexual reproduction may involve two or more organisms. A reproductive group must form a connected footprint-contact group. The first prototype resolves reproduction without gestation according to Section 22.

### 11.3 Probabilistic compatibility

There is no absolute genomic-distance cutoff. Increasing genomic distance applies a probability penalty to successful reproduction.

A conceptual success probability combines:

- Base fertility
- Participant readiness
- Health
- Resource sufficiency
- Average pairwise genomic distance
- Participant-count coordination cost

Even highly different genomes may reproduce, but with a potentially severe probability penalty.

### 11.4 Offspring genomes

For successful sexual reproduction:

1. Parent contribution weights are sampled.
2. Coherent groups of genomic traits are inherited together.
3. Parent trait distributions are recombined.
4. Mutation is applied.
5. Concrete offspring phenotypes are sampled.
6. The sexually determined offspring-count distribution is sampled.

Genomic distance should use a bounded distribution-distance measure such as Jensen-Shannon divergence rather than mutual information directly. Mutual information does not naturally express distance between two standalone genomes.

## 12. Species and speciation

Species classification combines:

- Ancestry
- Distance to a species genomic distribution
- Reproductive compatibility
- Production of viable and fertile descendants
- Persistence across generations

A novel offspring is initially a candidate lineage, not immediately a new species. It becomes a recognized species after establishing a stable cluster of similar, viable, reproducing descendants.

A species record should track:

- Species identifier
- Founders
- Parent species
- Genomic distribution centroid
- Genomic variation
- Compatibility profile
- Population
- Creation and extinction ticks
- Successful reproduction history
- Typical elemental composition

## 13. Symbiosis and multicellularity

Organisms may form alliances when their capabilities complement one another, such as energy acquisition combined with defense.

A persistent symbiotic group may become a composite or multicellular entity. The composite should be represented separately and reference its member organisms rather than flattening all members into one organism record.

A composite may reduce future operating costs through efficiency, but may not refund spent energy or create matter. Reproducing a composite still requires the matter and energy needed to construct every member.

## 14. Organism record

The eventual organism dataclass should reference a genome and contain a phenotype plus mutable nested state. This section is a high-level summary; Section 21 defines authoritative fields, derived values, registries, and caches.

### Identity

- Organism ID
- Species ID
- Lineage ID
- Genome ID
- Parent IDs
- Generation
- Birth tick

### Spatial state

- Anchor tile
- Occupied footprint tiles
- Facing
- Movement progress
- Current speed
- Previous anchor tile

### Body state

- Structural molecule inventory
- Metabolic molecule inventory
- Digestive inventory
- Waste inventory
- Reproductive inventory
- Cached elemental composition
- Cached mass
- Current size
- Integrity
- Maximum integrity

### Energy state

- Stored mana
- Maintenance debt
- Recent energy-flow accounting counters
- Recent heat absorption and expulsion counters

Usable chemical energy is derived from molecular inventories and must not be counted twice. Environmental heat belongs to world cells rather than organisms.

### Chemical and health state

- Toxin loads
- Active detox processes
- Temporary conditions
- Physical damage
- Damage by magical channel
- Starvation level

### Lifecycle state

- Age
- Sampled baseline lifespan
- Maturity age
- Senescence state
- Alive flag
- Death cause
- Death tick

### Behavior state

- Current action
- Current target
- Action timing and commitment
- Bounded recent observations
- Bounded recent action results

Hunger, threat, reproductive readiness, and similar drives are derived policy inputs rather than duplicated authoritative state.

### Reproductive state

- Cooldown
- Current mating group
- Ready-since tick
- Lifetime offspring count
- Last reproduction tick

Reproductive matter is authoritative in the reproductive inventory. The first prototype has no gestation.

### Social state

- Colony ID
- Colony role
- Bounded social memory

Alliance, symbiosis, trust, and sharing permissions are authoritative in the central relationship registry.

### Scheduling and auditing

- Last update tick
- Next action tick
- Active effects
- Cached owned energy
- Cached owned matter

## 15. Death and recycling

When an organism dies:

- Its elemental matter remains in its body or becomes corpse and waste molecules.
- Its molecular chemical energy remains associated with those molecules unless a death reaction releases some as heat.
- Its stored mana returns to environmental heat.
- Decomposition reactions make its matter available to the ecosystem.

Death therefore recycles both matter and energy rather than deleting the organism's contents.

## 16. Prototype implementation recommendation

Use Python for the first playable prototype, preferably with Pygame or pygame-ce.

Python is sufficient for hundreds of organisms if the implementation:

- Uses a spatial grid index instead of all-pairs checks
- Stores molecules in aggregated batches
- Schedules organisms only when they need to act
- Keeps observation windows bounded
- Avoids copying genomes and large inventories
- Profiles before optimizing

Python offers the shortest path to a visible and adjustable prototype. Dataclasses, fast iteration, debugging, and Pygame integration are more valuable at the current scale than Rust's maximum throughput.

Rust should be reconsidered if profiling later shows that the desired scale, reaction system, pathfinding, or neural policies cannot meet the frame budget. Proven hot systems may be exposed to Python through a narrow Rust FFI, preferably using PyO3. Domain rules and authoritative state ownership should remain on one side of each FFI boundary so that per-organism, per-tick calls do not erase the performance benefit.

## 17. Detailed design map

The remaining sections provide the implementation-level conceptual design:

- Sections 18–22: distributions, genomes, phenotypes, organism state, and reproduction
- Sections 23–30: procedural chemistry, reactions, toxicity, abundance, and chemistry controls
- Sections 31–33: units, action economy, utility policy, deterministic ticks, and conflicts
- Sections 34–36: species, magic, symbiosis, and multicellularity
- Sections 37–40: lifecycle, conservation audits, interface, replay, performance, testing, and milestones

Confirmed, replaceable prototype defaults are recorded in Section 40.3.

## 18. Trait-distribution system

### 18.1 Goals

The genome stores distributions rather than already-realized biological values. The distribution system must be:

- Small enough to inspect and serialize
- Deterministic under a supplied random seed
- Bounded so mutation cannot produce invalid traits
- Comparable for genomic-distance calculations
- Recombination-friendly for any number of parents
- Independent of Python-specific object behavior so hot paths can later move to Rust

Every heritable locus has a stable locus name, a distribution payload, a mutation scale, and a genomic-distance weight. Units and legal bounds belong to the schema rather than being repeated in every genome.

### 18.2 Scalar distribution

A scalar distribution represents continuous traits such as basal metabolism, efficiency, lifespan, or movement cost. It contains:

- `center`: expected value in transformed space
- `spread`: nonnegative standard deviation in transformed space
- `minimum`: inclusive physical lower bound
- `maximum`: inclusive physical upper bound
- `scale`: either linear or logarithmic
- `mutation_scale`: standard deviation of mutation in transformed space
- `distance_weight`: contribution to genomic distance

Sampling uses a truncated normal distribution in transformed space. Logarithmic scale produces positive, skewed physical values and is the default for size, lifespan, rates, capacities, and costs. Linear scale is the default for signed policy weights and naturally bounded efficiencies.

A probability is a scalar distribution bounded to `[0, 1]` and sampled in logit space so mutation behaves sensibly near zero and one.

### 18.3 Discrete distribution

A discrete distribution represents bounded integer or categorical outcomes. It contains:

- Ordered legal values
- Probability mass for each value
- Mutation scale applied to the logits of the probability masses
- Genomic-distance weight

It is used for:

- Body-shape category
- Sight radius
- Memory capacity
- Preferred sexual participant count
- Sexual offspring count
- Other small bounded counts

The legal value set comes from the run schema, preventing mutation from creating unsupported categories.

### 18.4 Simplex distribution

A simplex distribution represents proportions that must be nonnegative and sum to one. It contains:

- Stable dimension labels
- Mean proportion per dimension
- Positive concentration controlling individual variation
- Mutation scale in log-ratio space
- Genomic-distance weight

Sampling uses a Dirichlet distribution. It is used for:

- Target structural element composition
- Dietary element preference
- Molecular descriptor preference
- Social or colony-role preference
- Multi-channel allocation where a fixed budget must be divided

Element dimensions are run-local but stable for the duration of a run.

### 18.5 Independent vector distribution

An independent vector is a stable map from labels to scalar distributions. Its dimensions do not need to sum to one. It is used for:

- Fire, water, earth, and air affinities
- Four-channel magical resistance
- Toxin sensitivity dimensions
- Sensory channel strengths
- Resource-sharing limits

### 18.6 Policy-weight distribution

The utility policy is represented as a sparse action-by-feature matrix. Each present matrix entry is a bounded scalar distribution. An absent entry has weight zero.

The initial feature vocabulary is:

- Chemical reserve fraction
- Mana fraction
- Hunger
- Injury
- Toxin burden
- Local food quality
- Local recoverable heat
- Nearest prey value
- Nearest threat level
- Mate opportunity
- Alliance opportunity
- Crowding
- Reproductive readiness
- Distance to current target
- Previous action reward
- Exploration noise

The initial action vocabulary is the action list in Section 9. Both vocabularies are schema-versioned so future neural policies can reuse the same observation and action interfaces.

### 18.7 Pathway gene

A pathway gene represents an inheritable digestion, waste, or detox capability. It contains:

- Stable pathway template identifier
- Expression probability
- Input descriptor preference
- Input tolerance
- Output pathway template
- Throughput distribution
- Chemical-energy efficiency distribution
- Activation-threshold distribution
- Damage or toxicity reduction distribution

At birth, expression is sampled once. An expressed pathway becomes a realized phenotype pathway with fixed throughput, efficiency, threshold, and specificity.

### 18.8 Linkage modules

Traits are grouped into linkage modules so reproduction does not independently average every number. The initial modules are:

1. Morphology
2. Metabolism and thermal handling
3. Locomotion and physical interaction
4. Chemistry and pathways
5. Behavior
6. Magic
7. Aging
8. Reproduction
9. Sociality
10. Perception

Morphology and basal metabolism are deliberately separate modules. This allows large organisms with low basal metabolism to be inherited and selected without forcing a size-metabolism correlation.

### 18.9 Phenotype sampling

A phenotype is sampled exactly once at birth using a deterministic seed derived from the world seed, organism identifier, genome identifier, and birth sequence number.

Sampling rules are:

1. Sample each scalar, discrete, simplex, and vector locus.
2. Sample pathway expression and realized pathway parameters.
3. Apply cross-trait validity constraints.
4. Derive fixed secondary traits such as maximum integrity.
5. Record the sampling seed for deterministic replay.

Sampling never changes the genome.

### 18.10 Asexual inheritance

Asexual reproduction begins with a copy of the parent's genome distributions. Every locus then receives its inherited mutation probability and magnitude. The prototype produces one offspring per successful asexual event.

### 18.11 Sexual multi-parent inheritance

For two or more parents:

1. Parent contribution weights are sampled and normalized.
2. Each linkage module first chooses a source parent using those weights.
3. The source parent's module is copied as a coherent starting point.
4. Recombination strength determines the probability that individual loci blend information from all parents.
5. Blended scalar centers use weighted transformed-space means.
6. Blended spread includes both within-parent spread and between-parent disagreement.
7. Discrete probabilities blend in logit space.
8. Simplex means blend in log-ratio space.
9. Mutation is applied after recombination.

This preserves recognizable parental strategies while permitting novel combinations. Highly dissimilar parents are penalized before offspring generation but are not categorically forbidden.

### 18.12 Mutation

Mutation may affect distribution centers, spreads, probability masses, pathway expression, and policy weights. It does not mutate physical state.

The reproduction genome carries inherited mutation-rate and mutation-magnitude traits, subject to global lower and upper limits. A small global mutation floor prevents a lineage from permanently disabling all mutation.

Mutation must clamp or transform values back into their legal domains. Invalid genomes are never admitted and no retry loop may silently create or destroy reproductive energy or matter.

### 18.13 Genomic distance

Genomic distance is a weighted average of per-locus Jensen-Shannon divergences:

- Discrete loci use their probability masses directly.
- Scalar loci are converted to fixed schema-defined probability bins.
- Simplex and vector dimensions are normalized before comparison.
- Pathway presence and expression contribute a bounded capability distance.
- Policy matrices compare only schema-defined action-feature coordinates.

The result is normalized to `[0, 1]`, cached by genome pair, and used as one input to mating success and species clustering. It is a distance measure, not a hard reproductive boundary.

## 19. Exact Genome schema

A `Genome` is immutable after creation and contains the following nested records.

### 19.1 Genome identity

- `genome_id`
- `schema_version`
- `parent_genome_ids`
- `creation_tick`
- `lineage_tags`

Random-number-generator state is not stored in the genome.

### 19.2 Morphology genome

- `birth_area`: discrete distribution of occupied-tile count at birth
- `adult_area`: discrete distribution of target adult occupied-tile count
- `shape`: discrete distribution over circle-like and ellipse-like footprint templates
- `aspect_ratio`: scalar distribution
- `density`: scalar distribution of structural mass per tile
- `structural_element_profile`: simplex distribution over generated elements
- `growth_rate`: scalar distribution of structural mass added per eligible growth action
- `growth_efficiency`: probability distribution controlling usable input matter retained as structure
- `integrity_per_mass`: scalar distribution
- `repair_efficiency`: probability distribution

Birth area may not exceed adult target area after phenotype validation.

### 19.3 Metabolism and thermal genome

- `basal_maintenance_demand`: absolute maintenance-energy demand per tick, independent of body size and payable from chemical energy or mana
- `mana_maintenance_preference`: probability-like tendency to use mana for basal maintenance
- `digestion_throughput`: molecules processed per digestion action
- `assimilation_efficiency`: probability distribution
- `chemical_reserve_capacity`: scalar distribution
- `preferred_reserve_fraction`: probability distribution
- `maximum_intake`: scalar distribution
- `starvation_tolerance`: scalar distribution of survivable maintenance debt
- `heat_absorption_rate`: scalar distribution
- `heat_to_mana_efficiency`: probability distribution
- `mana_capacity`: scalar distribution
- `mana_decay_rate`: scalar distribution
- `preferred_mana_fraction`: probability distribution

### 19.4 Locomotion and physical-interaction genome

- `maximum_speed`: scalar distribution in tiles per action
- `preferred_speed_fraction`: probability distribution
- `movement_efficiency`: probability distribution
- `turn_cost`: scalar distribution
- `physical_attack_strength`: scalar distribution
- `physical_attack_efficiency`: probability distribution
- `capture_reach`: discrete distribution in tiles beyond the footprint
- `ingestion_reach`: discrete distribution

Movement cost still depends on actual mass, distance, speed, and realized efficiency.

### 19.5 Chemistry genome

- `dietary_element_preference`: simplex distribution over generated elements
- `molecular_descriptor_preference`: simplex distribution over generated descriptor dimensions
- `dietary_tolerance`: scalar distribution controlling preference breadth
- `toxin_sensitivity`: independent vector distribution over descriptor dimensions
- `toxin_tolerance`: positive scalar distribution
- `digestion_pathways`: pathway-gene collection
- `waste_pathways`: pathway-gene collection
- `detox_pathways`: pathway-gene collection
- `detox_action_bias`: scalar policy modifier
- `sequestration_tendency`: probability distribution
- `excretion_tendency`: probability distribution
- `pathway_gain_rate`: probability distribution for rare mutation to a neighboring validated catalog pathway
- `pathway_loss_rate`: probability distribution

Body composition is inherited under morphology; dietary preference is separately inherited here.

### 19.6 Behavior genome

- `utility_weights`: policy-weight distribution
- `decision_randomness`: nonnegative scalar distribution used as softmax temperature
- `action_commitment`: discrete distribution of minimum commitment ticks
- `memory_capacity`: discrete distribution of bounded observation count
- `target_persistence`: scalar distribution
- `risk_tolerance`: probability distribution

### 19.7 Magic genome

- `affinity`: independent vector over fire, water, earth, and air
- `resistance`: independent vector over the same four channels
- `casting_efficiency`: probability distribution
- `maximum_cast_fraction`: probability distribution limiting mana spent in one cast
- `casting_range`: discrete distribution
- `offense_tendency`: probability distribution
- `defense_tendency`: probability distribution
- `escape_tendency`: probability distribution
- `channel_preference`: simplex distribution over the four channels

Magic channels are effects only and cannot create molecular matter.

### 19.8 Aging genome

- `baseline_lifespan`: positive scalar distribution in ticks
- `maturity_fraction`: probability distribution applied to sampled baseline lifespan
- `hazard_shape`: positive scalar distribution controlling age-related hazard growth
- `chemical_survival_modifier`: scalar distribution
- `mana_survival_modifier`: scalar distribution
- `senescence_rate`: scalar distribution
- `recovery_efficiency`: probability distribution

### 19.9 Reproduction genome

- `asexual_propensity`: probability distribution
- `sexual_propensity`: probability distribution
- `preferred_parent_count`: discrete distribution whose legal values begin at two
- `sexual_offspring_count`: discrete distribution whose legal values begin at one
- `base_fertility`: probability distribution
- `compatibility_penalty`: scalar distribution controlling the genomic-distance penalty
- `mate_recognition_profile`: simplex distribution over recognition descriptors
- `minimum_chemical_reserve_fraction`: probability distribution
- `minimum_reproductive_mass_fraction`: probability distribution
- `offspring_investment_fraction`: probability distribution
- `reproduction_cooldown`: positive scalar distribution in ticks
- `recombination_strength`: probability distribution
- `parental_contribution_bias`: simplex distribution when participant roles are known; otherwise contributions are sampled symmetrically
- `mutation_rate`: probability distribution
- `mutation_magnitude`: positive scalar distribution

Asexual and sexual propensities are independent rather than summing to one. Context and utility-policy scores determine which eligible mode is attempted.

### 19.10 Social genome

- `alliance_propensity`: probability distribution
- `partner_recognition_profile`: simplex distribution over social descriptors
- `resource_sharing_tendency`: probability distribution
- `maximum_resource_share`: probability distribution
- `symbiosis_persistence`: scalar distribution
- `specialization_tendency`: probability distribution
- `colony_formation_propensity`: probability distribution
- `colony_role_preference`: simplex distribution over producer, defender, mover, digester, sensor, and reproducer roles
- `cheater_tolerance`: probability distribution
- `composite_reproduction_propensity`: probability distribution

### 19.11 Perception genome

- `sight_radius`: discrete distribution beginning at one tile
- `sensory_efficiency`: probability distribution
- `sensory_cost_per_cell`: positive scalar distribution
- `food_detection`: probability distribution
- `threat_detection`: probability distribution
- `heat_detection`: probability distribution
- `mate_detection`: probability distribution
- `ally_detection`: probability distribution
- `magic_detection`: probability distribution

Sight has no species-age bonus.

## 20. Exact Phenotype schema

A `Phenotype` is immutable after birth. It contains realized values, not distributions or mutable health state.

### 20.1 Phenotype identity

- `phenotype_id`
- `genome_id`
- `sampling_seed`
- `schema_version`

### 20.2 Realized morphology

- `birth_area_tiles`
- `adult_area_tiles`
- `shape_template`
- `aspect_ratio`
- `density`
- `structural_element_target`
- `growth_rate`
- `growth_efficiency`
- `integrity_per_mass`
- `repair_efficiency`

### 20.3 Realized metabolism and thermal handling

- `basal_maintenance_demand`
- `mana_maintenance_preference`
- `digestion_throughput`
- `assimilation_efficiency`
- `chemical_reserve_capacity`
- `preferred_reserve_fraction`
- `maximum_intake`
- `starvation_tolerance`
- `heat_absorption_rate`
- `heat_to_mana_efficiency`
- `mana_capacity`
- `mana_decay_rate`
- `preferred_mana_fraction`

### 20.4 Realized locomotion and interaction

- `maximum_speed`
- `preferred_speed_fraction`
- `movement_efficiency`
- `turn_cost`
- `physical_attack_strength`
- `physical_attack_efficiency`
- `capture_reach`
- `ingestion_reach`

### 20.5 Realized chemistry

- `dietary_element_preference`
- `molecular_descriptor_preference`
- `dietary_tolerance`
- `toxin_sensitivity`
- `toxin_tolerance`
- `expressed_digestion_pathways`
- `expressed_waste_pathways`
- `expressed_detox_pathways`
- `detox_action_bias`
- `sequestration_tendency`
- `excretion_tendency`

Each expressed pathway contains fixed specificity, throughput, efficiency, and activation threshold values sampled from its pathway gene.

### 20.6 Realized behavior

- `utility_weights`
- `decision_randomness`
- `action_commitment_ticks`
- `memory_capacity`
- `target_persistence`
- `risk_tolerance`

### 20.7 Realized magic

- `affinity_by_channel`
- `resistance_by_channel`
- `casting_efficiency`
- `maximum_cast_fraction`
- `casting_range`
- `offense_tendency`
- `defense_tendency`
- `escape_tendency`
- `channel_preference`

### 20.8 Realized aging

- `baseline_lifespan_ticks`
- `maturity_age_ticks`
- `hazard_shape`
- `chemical_survival_modifier`
- `mana_survival_modifier`
- `senescence_rate`
- `recovery_efficiency`

### 20.9 Realized reproduction

- `asexual_propensity`
- `sexual_propensity`
- `preferred_parent_count`
- `sexual_offspring_count_distribution`
- `base_fertility`
- `compatibility_penalty`
- `mate_recognition_profile`
- `minimum_chemical_reserve_fraction`
- `minimum_reproductive_mass_fraction`
- `offspring_investment_fraction`
- `reproduction_cooldown_ticks`
- `recombination_strength`
- `parental_contribution_bias`
- `mutation_rate`
- `mutation_magnitude`

The sexual offspring-count distribution remains a distribution in the phenotype because it is sampled at each successful reproductive event. It is not a mutable organism state.

### 20.10 Realized social traits

- `alliance_propensity`
- `partner_recognition_profile`
- `resource_sharing_tendency`
- `maximum_resource_share`
- `symbiosis_persistence`
- `specialization_tendency`
- `colony_formation_propensity`
- `colony_role_preference`
- `cheater_tolerance`
- `composite_reproduction_propensity`

### 20.11 Realized perception

- `sight_radius`
- `sensory_efficiency`
- `sensory_cost_per_cell`
- `detection_strength_by_channel`

### 20.12 Phenotype validation

Birth sampling must enforce:

- Birth area is at least one tile and no larger than adult area.
- All efficiencies, probabilities, resistances, and affinities lie in their declared domains.
- All rates and capacities are finite and nonnegative.
- Elemental and preference profiles have valid run-local dimensions and sum to one where required.
- Sight radius and memory capacity respect prototype performance limits.
- Reproduction distributions contain only legal parent and offspring counts.

A failed validation is a schema or sampling defect. It must not be handled by repeatedly consuming parental reproductive resources.

## 21. Exact nested Organism schema

An `Organism` is mutable and references an immutable genome plus an immutable phenotype. Large collections such as genomes, molecule types, species, relationships, effects, and colonies are held in world registries and referenced by identifier.

### 21.1 Top-level organism fields

- `organism_id`
- `lineage_id`
- `genome_id`
- `phenotype`
- `species_id`, optional while a lineage is unclassified
- `candidate_lineage_id`, optional
- `parent_ids`
- `generation`
- `birth_tick`
- `spatial`
- `body`
- `energy`
- `health`
- `lifecycle`
- `behavior`
- `chemistry`
- `reproduction`
- `social`
- `schedule`
- `cache`

### 21.2 Spatial state

Authoritative fields:

- `anchor_tile`
- `facing`
- `movement_destination`, optional
- `movement_progress`
- `previous_anchor_tile`

The footprint and contact tiles are derived from anchor tile, current structural mass, phenotype density, shape template, aspect ratio, and toroidal wrapping, and are held only in the organism cache.

### 21.3 Body state

Authoritative inventories:

- `structural_inventory`
- `metabolic_inventory`
- `digestive_inventory`
- `waste_inventory`
- `reproductive_inventory`
- `sequestered_inventory` for isolated toxins or compounds

Additional authoritative fields:

- `integrity`
- `development_stage`
- `growth_commitment`, if a multi-tick growth action is active

Derived values:

- Current element counts
- Current structural mass
- Total owned mass
- Current occupied area
- Maximum integrity
- Current chemical energy
- Available metabolic energy

A molecule batch may belong to exactly one inventory at a time.

### 21.4 Energy state

Authoritative fields:

- `stored_mana`
- `maintenance_debt`

Accounting counters, reset at the selected audit interval:

- `chemical_energy_consumed`
- `mana_consumed`
- `heat_absorbed`
- `heat_expelled`

Chemical energy is authoritative in molecule batches and is not duplicated here. Environmental heat belongs to world cells and is not owned by the organism.

### 21.5 Health state

- `physical_damage_accumulator`
- `toxin_effects_by_descriptor`
- `starvation_severity`
- `active_condition_ids`
- `last_damage_source`, optional
- `last_damage_tick`, optional

Toxic molecules remain in an organism inventory. `toxin_effects_by_descriptor` records physiological consequences and does not own or duplicate toxic matter.

### 21.6 Lifecycle state

- `age_ticks`
- `alive`
- `senescence_level`
- `death_cause`, optional
- `death_tick`, optional

Maturity and baseline lifespan come from the phenotype. Current age-related death hazard is derived from age, senescence, chemical reserves, mana, health, and the phenotype's hazard modifiers.

### 21.7 Behavior state

- `current_action`
- `current_target`, optional typed entity reference
- `action_started_tick`
- `action_completion_tick`, optional
- `committed_until_tick`
- `observation_memory`, bounded by phenotype memory capacity
- `action_result_memory`, bounded
- `last_observation_tick`
- `decision_sequence_number`

Hunger, threat, food quality, reproductive readiness, and utility scores are derived observations rather than authoritative stored needs. This avoids state drifting away from the inventories and environment that define it.

### 21.8 Reproduction state

- `cooldown_until_tick`
- `ready_since_tick`, optional
- `mating_group_id`, optional
- `lifetime_offspring_count`
- `last_reproduction_tick`, optional

Reproductive material is authoritative in `body.reproductive_inventory`. Readiness is derived from maturity, cooldown, health, inventory, reserve thresholds, and current behavioral intent.

The prototype assumes no fixed sexes or genders. Any organism may participate when its genome, phenotype, compatibility, contact, and state permit it.

### 21.9 Social state

- `colony_id`, optional
- `current_colony_role`, optional
- `social_memory`, bounded map of partner identifier to trust and recent outcome

Alliances and symbioses are authoritative in a central relationship registry so both participants cannot hold contradictory relationship state.

### 21.10 Schedule state

- `next_metabolism_tick`
- `next_decision_tick`
- `next_action_tick`
- `next_aging_tick`
- `next_reaction_tick`

Separate scheduled ticks permit slow systems to avoid unnecessary per-frame work.

### 21.11 Cache state

- `element_counts`
- `structural_mass`
- `total_mass`
- `chemical_energy`
- `available_metabolic_energy`
- `footprint_tiles`
- `visible_tiles`
- `dirty_flags`

Caches are never serialized as authoritative save-state values unless they are validated or rebuilt on load.

### 21.12 Supporting state records

A molecule inventory maps molecule type identifiers to aggregated batches. Each batch contains integer molecule count and continuous total chemical energy.

A typed entity reference contains an entity category and identifier so a target can be an organism, molecule deposit, corpse, colony, or grid location without ambiguous integers.

An observation is a bounded summary of local cells and entities, not a retained copy of world objects.

An active magical effect is a world-registry entity containing its channel, source, target or area, remaining energy, start tick, and resolution tick. Its energy is removed from the caster's mana exactly once and returns to environmental heat when resolved.

### 21.13 Organism invariants

For every organism:

1. All molecule counts are nonnegative integers.
2. Molecule-batch energy is finite, nonnegative, and no greater than capacity.
3. A molecule batch is owned by one location or inventory only.
4. Stored mana is finite, nonnegative, and no greater than phenotype capacity.
5. Chemical energy is counted in inventories, never duplicated in energy state.
6. Environmental heat is counted in world cells, never in organism ownership.
7. Matter in toxins, reproduction, digestion, and waste remains part of total owned matter.
8. Cached mass and elemental composition must match authoritative inventories when audited.
9. Footprint cells are connected under toroidal adjacency.
10. Dead organisms cannot begin actions or reproduction.
11. Death transfers stored mana to heat and eventually transfers all inventories into corpse or environmental inventories.
12. Reproduction transfers existing matter and energy; it never creates either.

## 22. Prototype reproduction rules

The initial reproduction behavior is:

- There are no fixed sexes or genders.
- A successful asexual event produces one offspring.
- A successful sexual event samples its offspring count from the inherited event-level distribution.
- There is no gestation in the first prototype; birth occurs when the reproduction action resolves.
- All participating parents contribute matter from their reproductive inventories according to their sampled contribution weights.
- A connected footprint-contact group is sufficient; every participant need not touch every other participant directly.
- Offspring are placed in the nearest valid wrapped cells adjacent to the reproductive group.
- Offspring begin at their sampled birth area and may grow toward their sampled adult area.

### 22.1 Reproductive commitment point

Before committing, the action validates that every participant is ready and that the group collectively has the required reproductive matter and chemical energy. Once the group commits to reproduction:

1. Each participant immediately pays its weighted share of the attempt's chemical-energy cost.
2. Consumed chemical energy is transferred to environmental heat as the action proceeds.
3. The energy is not refunded if compatibility, fertility, offspring generation, or placement fails.
4. Failed placement therefore still has an energetic cost.
5. Reproductive matter is transferred to offspring only when an offspring is successfully created.
6. If no offspring is created, reserved reproductive matter remains with its contributing parents; only the attempt energy is lost.

This separates the nonrefundable energetic cost of attempting reproduction from the conserved physical matter required to construct successful offspring. A future failed-embryo mechanic may transform reserved matter into waste, but that is outside the first prototype.

## 23. Procedural chemistry model

### 23.1 Scope

The chemistry model is intentionally fictional and bounded. It must produce varied food webs, toxins, waste loops, and detox strategies without attempting to simulate real quantum chemistry or maintaining a dynamically unbounded reaction graph.

Chemistry is generated once from the world seed. Molecule types and reaction templates may begin latent and become ecologically visible only when a reaction first produces them.

### 23.2 Element definition

Each run generates a configurable number of element types. An `ElementDefinition` contains:

- `element_id`
- `display_symbol`
- `atomic_mass`, a positive integer
- `energy_contribution`, a finite positive continuous value
- `bond_capacity`, a small positive integer used to reject implausible compositions
- `polarity`, bounded to `[0, 1]`
- `reactivity`, bounded to `[0, 1]`
- `rigidity`, bounded to `[0, 1]`
- `chemical_signature`, a four-dimensional simplex vector
- `initial_count`, a nonnegative integer

The four chemical-signature axes are abstract run-independent coordinates rather than fire, water, earth, or air. Their only purpose is to make molecular similarity, preference, sensitivity, and pathway matching measurable.

Element identifiers and signature dimensions remain stable for the full run. Atomic mass and energy contribution are not mutated by organisms.

### 23.3 Molecule definition

A `MoleculeDefinition` contains:

- `molecule_type_id`
- `composition`, a sparse map of element identifier to positive integer count
- `total_element_units`
- `distinct_element_count`
- `molecular_mass`
- `energy_capacity_per_molecule`
- `chemical_signature`, a four-dimensional simplex vector
- `polarity`, bounded to `[0, 1]`
- `reactivity`, bounded to `[0, 1]`
- `stability`, bounded to `[0, 1]`
- `rigidity`, bounded to `[0, 1]`
- `permeability`, bounded to `[0, 1]`
- `complexity`, bounded to `[0, 1]`
- `catalog_state`, either initially present or latent

Mass and maximum energy are derived exactly:

- Molecular mass is the sum of element count multiplied by element atomic mass.
- Energy capacity is the sum of element count multiplied by element energy contribution.

All remaining descriptors are deterministic functions of composition, element descriptors, and the world seed. Composition-weighted averages provide the baseline; bounded interaction terms based on element diversity allow compounds to differ from their constituents.

There is no global `food`, `waste`, or `poison` flag. Those roles depend on an organism's pathways, preferences, sensitivity, and the molecule's current energy.

### 23.4 Composition feasibility

The prototype represents composition rather than explicit molecular bond graphs. A generated multi-element composition is accepted only when:

- Total element units are below the configured maximum.
- Every count is a positive integer.
- At least one connected bonding arrangement is plausible under the participating bond capacities.
- The canonical composition is not already present in the catalog.

A monatomic molecule type is always created for every element. These types guarantee that any conserved element vector can be represented even when no compound partition is available.

### 23.5 Molecule catalog generation

World initialization proceeds as follows:

1. Generate element definitions and exact global element counts.
2. Create one monatomic molecule type per element.
3. Generate bounded candidate compositions using the world seed.
4. Reject infeasible and duplicate compositions.
5. Derive all molecule descriptors deterministically.
6. Mark a configured subset as initially present and the remainder as latent.
7. Allocate initial molecule counts without exceeding any global element count.
8. Place all leftover elements into their monatomic molecule types.
9. Assign each initial molecule batch a continuous charged-energy fraction within capacity.
10. Generate and validate the constrained reaction catalog.

The initial recommendation is eight elements, four abstract signature dimensions, and approximately forty-eight molecule types. These are configuration defaults rather than conservation rules.

## 24. Chemical storage records

### 24.1 Molecule batch

A `MoleculeBatch` is the smallest authoritative chemical-storage record. It contains:

- `molecule_type_id`
- `count`, a nonnegative integer
- `chemical_energy`, a finite nonnegative continuous value

The batch invariant is:

`chemical_energy <= count × molecule energy capacity`

Batches of the same molecule type may be merged by adding counts and energy. Splitting a batch divides energy in proportion to molecule count unless a reaction explicitly selects a different energy-allocation rule.

### 24.2 Molecule inventory

A `MoleculeInventory` maps molecule type identifiers to batches. It owns its batches exclusively and caches no independent matter.

Inventories exist in:

- World cells
- Organism body compartments
- Corpses
- Colony-level shared stores

Transferring a batch changes ownership but does not change its matter or energy.

### 24.3 Cell chemistry

A cell's chemistry state contains:

- Environmental molecule inventory
- Recoverable heat energy
- Optional corpse identifiers
- Chemistry dirty flag

Heat is not a molecule and has no elemental composition.

### 24.4 Global chemistry registries

The world owns registries for:

- Element definitions
- Molecule definitions
- Reaction templates
- Reaction templates indexed by primary reactant and reaction kind
- Current global abundance by molecule type
- Historical production and consumption counters

Latent molecule types remain in the definition registry at zero abundance and may reappear through reactions.

## 25. Constrained reaction model

### 25.1 Reaction kinds

The first prototype supports five reaction kinds:

1. `digestion`: breaks or rearranges consumed molecules and permits chemical-energy capture
2. `assimilation`: rearranges digested matter into molecules suitable for growth, repair, or reproduction
3. `waste`: converts unusable or depleted material into excretable products
4. `detox`: converts a harmful molecule into products expected to be less harmful to the acting organism
5. `decomposition`: converts corpse or environmental molecules into smaller or more stable products

Excretion and ingestion are transfers, not reactions. Movement and magic are energy conversions, not molecular reactions.

### 25.2 Reaction template

A `ReactionTemplate` contains:

- `reaction_id`
- `reaction_kind`
- `reactants`, integer stoichiometric coefficients by molecule type
- `products`, integer stoichiometric coefficients by molecule type
- `primary_reactant_type_id`
- `input_signature`
- `base_activation_energy`
- `base_process_heat_fraction`
- `base_rate`
- `product_routes`, mapping each product to digestive, structural-candidate, waste, sequestered, or environmental inventory
- `population_hazard_change`, an informational generation-time score rather than a universal toxicity claim
- `complexity_cost`

Every coefficient is a positive integer. A template has at most two reactant types and three product types in the initial prototype.

### 25.3 Reaction conservation

Every generated template must satisfy exact element-vector equality:

`sum(reactant coefficient × reactant composition) = sum(product coefficient × product composition)`

Reaction execution additionally satisfies continuous energy conservation. No template may increase chemical energy unless an equal amount is debited from another tracked reservoir.

### 25.4 Bounded reaction generation

Reaction generation uses seeded bounded sampling rather than exhaustive chemical enumeration or an integer-programming solver:

1. Select one or two catalog reactants within arity and coefficient limits.
2. Calculate their exact combined element vector.
3. Sample candidate catalog products whose combined vector may match it.
4. Use monatomic products to complete a partially matched vector when necessary.
5. Reject the candidate unless element vectors match exactly.
6. Score the candidate for one or more reaction kinds.
7. Keep only a small configured number of high-scoring templates per primary input and kind.
8. Canonicalize and deduplicate the resulting template.

Generation has hard attempt, molecule-size, coefficient, and catalog-size limits. A bad world seed therefore cannot trigger unbounded search.

### 25.5 Reaction-kind scoring

Candidates are favored differently by kind:

- Digestion favors products that are easier to process, less complex, and compatible with metabolic energy extraction.
- Assimilation favors products close to structural element and descriptor targets.
- Waste favors stable, permeable, and relatively low-reactivity products.
- Detox favors products with lower predicted population-average hazard than the primary input while allowing species-specific exceptions.
- Decomposition favors smaller, stable products and may release some chemical energy as heat.

The scores choose catalog edges; they do not alter conservation constraints.

### 25.6 Catalog connectivity guarantees

World generation must guarantee:

- Every initially present molecule has at least one valid decomposition or monatomic fallback path.
- Every generated founder population collectively expresses at least one pathway that can process at least one initially abundant energized molecule.
- Every pathway references an existing reaction template.
- Every reaction output references an existing molecule definition.
- At least one waste or decomposition product can re-enter some founder's possible digestive pathway, creating an initial opportunity for ecological cycling.

These are population-level viability constraints, not guarantees that any individual organism survives.

## 26. Reaction execution

### 26.1 Eligibility

A reaction can run only when:

- All required integer reactant counts are present in the required inventories.
- The organism expresses a compatible pathway for non-environmental reactions.
- Pathway match exceeds its activation threshold.
- Required activation energy is available from metabolic molecule batches.
- Product routing has sufficient legal destination capacity, or overflow routing to waste is defined.

### 26.2 Pathway match

Pathway match is a bounded similarity function using:

- Distance between molecule and pathway input signatures
- Pathway input tolerance
- Molecule complexity
- Molecule permeability
- Realized pathway specificity

The result lies in `[0, 1]` and affects both throughput and energy-capture efficiency. Molecular preference affects whether an organism chooses to ingest a molecule; pathway match separately determines whether it can process what it ate.

### 26.3 Integer throughput

Reactions always process whole molecules. Realized pathway throughput has a minimum of one molecule per completed reaction action and is converted to an integer before reactants are reserved. No fractional molecular matter is created.

### 26.4 Energy partition

For one execution, let:

- `E_input` be chemical energy removed with the reactant batches.
- `E_activation` be chemical energy debited from metabolic carriers.
- `q` be pathway match.
- `e` be realized pathway efficiency.
- `h` be the template process-heat fraction after phenotype modifiers.
- `H` be available energy capacity in the organism's metabolic carriers.

The captured chemical energy is:

`E_capture = min(E_input × q × e, H)`

The remaining input energy is:

`E_remaining = E_input - E_capture`

The reaction places:

- `E_capture` into metabolic-carrier headroom.
- `E_remaining × h + E_activation` into environmental heat at occupied cells.
- `E_remaining × (1 - h)` into product molecule batches, distributed without exceeding product capacities.

Any product-capacity rounding excess becomes environmental heat. The execution ledger must verify that output chemical energy, captured energy, and heat exactly equal input plus activation energy within numerical tolerance.

A depleted metabolic-carrier molecule remains matter and may be recharged by later digestion. It is not destroyed when its energy reaches zero.

### 26.5 Matter routing

After execution:

- Digestion products remain digestive material, become structural candidates, or enter waste according to the template.
- Assimilation products enter structural, reproductive, or metabolic inventories according to the chosen action and legal composition target.
- Waste and detox products enter waste or sequestered inventories until excreted.
- Decomposition products enter the environmental inventory of the corpse's cell or cells.

Routing never changes molecular identity, count, or energy after the reaction result is created.

### 26.6 Failed reactions

Reactants and activation energy are reserved atomically. If eligibility fails before commitment, nothing is charged. If a committed reaction is interrupted, reserved matter is returned to its source inventories and any already-expended activation energy remains environmental heat.

This matches the broader rule that attempted biological work may waste energy without deleting matter.

## 27. Toxicity and detoxification details

### 27.1 Toxicity is relational

A molecule has no universal poison flag. Its effective hazard to one organism is based on:

- Exposed molecule count
- Molecule permeability
- Molecule reactivity
- Molecule stability and exposure duration
- Alignment between its chemical signature and the organism's toxin-sensitivity vector
- The organism's realized toxin tolerance
- Sequestration and active detox pathways

The organism accumulates physiological toxin effects only when effective exposure exceeds its tolerance. Toxic molecules themselves remain in digestive, body, waste, or sequestered inventories and continue to count toward mass and energy.

### 27.2 Required genome and phenotype addition

The chemistry genome includes `toxin_tolerance`, a positive scalar distribution. The phenotype contains the realized `toxin_tolerance` value.

### 27.3 Detox pathway behavior

A detox action selects the eligible expressed pathway with the highest predicted harm reduction per chemical-energy cost, modified by the organism's inherited detox action bias.

A detox product that is safe for the acting organism may remain toxic to another organism. Excreted detox products therefore create potential new niches rather than globally neutral material.

### 27.4 Strategy emergence

Organisms may evolve to:

- Avoid a molecule through preference and sensing
- Consume it despite risk because of high energy content
- Tolerate it without detoxification
- Sequester it
- Spend energy detoxifying it
- Excrete it rapidly
- Feed on another species' detox or waste products

No strategy is assigned as a species role.

## 28. Molecular choice and ecological abundance

### 28.1 Perceived food value

An organism estimates food value from sensed rather than perfect information. The estimate combines:

- Current chemical energy density
- Match to dietary element preference
- Match to molecular descriptor preference
- Known or inferred pathway compatibility
- Estimated toxin risk
- Distance and movement cost
- Current reserve deficits

Poor sensing or unexplored molecules may cause harmful ingestion.

### 28.2 Reaction selection

When several pathways can process the same input, the organism's utility controller compares expected:

- Captured chemical energy
- Useful structural matter
- Activation cost
- Heat production
- Toxicity reduction or increase
- Waste burden
- Action duration

A small stochastic component prevents identical organisms from always choosing the same pathway.

### 28.3 Abundance-driven persistence

Global abundance changes only through validated transfers and reactions. A molecule type persists when production and recycling exceed consumption, transformation, and sequestration.

The world records per molecule type:

- Current molecule count
- Current chemical energy
- Production count by reaction kind
- Consumption count by reaction kind
- Number of organisms that ingested it
- Number of organisms that successfully processed it
- Number of associated toxin incidents
- Tick of first appearance
- Tick of most recent appearance

A molecule at zero abundance remains a latent definition and may return. Ecological extinction therefore means zero current abundance, not deletion from the catalog.

### 28.4 Computational limits

Runtime chemistry avoids all molecule-pair scans:

- Cell inventories expose only locally present molecule types.
- Reaction templates are indexed by primary reactant and kind.
- Organisms evaluate only expressed pathways relevant to present inputs.
- Global abundance counters update transactionally or in periodic batches.
- Descriptor matches may be cached by phenotype pathway and molecule type.

If chemistry becomes a performance hotspot, whole batches of reaction requests and results are suitable for Rust FFI. Python should not cross the FFI boundary once per molecule.

## 29. Chemistry integration with biological records

### 29.1 Genome chemistry integration

Section 19.5 includes toxin tolerance, sequestration, excretion, and pathway gain/loss traits alongside digestion, waste, and detox pathways. Pathway gain may only select a validated neighboring reaction template from the run catalog. It cannot invent an unbalanced reaction.

### 29.2 Phenotype chemistry integration

Section 20.5 realizes toxin tolerance, sequestration, and excretion traits. Expressed pathways contain their fixed throughput, efficiency, tolerance, threshold, and specificity.

### 29.3 Organism chemistry state

The top-level organism adds a nested `chemistry` state containing:

- `active_reaction_id`, optional
- `active_pathway_id`, optional
- `reaction_started_tick`, optional
- `reaction_completion_tick`, optional
- `reserved_reactants`, temporary exclusive batch references
- `reserved_activation_energy`
- `recent_reaction_results`, bounded for policy feedback

Authoritative toxic matter remains in body inventories. Descriptor-level toxin effects remain in health state.

### 29.4 Chemistry cache additions

The organism cache may contain:

- Eligible pathways by locally present molecule type
- Pathway-match values
- Perceived food values
- Effective toxin burden
- Metabolic-carrier energy headroom

All chemistry caches are invalidated when relevant inventories, phenotype pathways, or local cell chemistry change.

## 30. Chemistry invariants and prototype defaults

### 30.1 Invariants

1. Global count of every element equals its initialization count.
2. Every molecule count is an integer.
3. Every reaction balances exact element vectors.
4. Every molecule batch stays within its energy capacity.
5. Every energy debit has a matching chemical, mana, effect, or heat credit.
6. A molecule type's ecological role is never stored as a universal food, waste, or poison flag.
7. Latent molecule definitions own no matter or energy.
8. Reaction and pathway identifiers always reference the run's immutable registries.
9. Failed validation never partially mutates inventories.
10. Random reaction generation is deterministic under the world seed and bounded by configuration limits.

### 30.2 Recommended prototype defaults

- Eight generated element types
- Four abstract chemical-signature dimensions
- Approximately forty-eight molecule types, including monatomic fallbacks
- At most twelve element units per molecule
- At most two reactant types and three product types per reaction
- Coefficients capped at three
- One to three retained reaction templates per primary molecule and reaction kind
- A fixed run-local catalog with latent types rather than unbounded runtime molecule-type generation
- Spontaneous decomposition based on molecule stability
- No toxin-driven genome mutation in the first prototype

These are defaults rather than hard-coded constants.

### 30.3 Configurability and simulation controls

Every numerical simulation parameter must be owned by a versioned world-configuration record and expose UI metadata consisting of a display label, legal minimum, legal maximum, slider step, default value, and unit. Simulation systems and any future Rust FFI receive configuration snapshots rather than reading hidden module-level constants.

Controls are divided into two categories.

#### Pre-run generation controls

These values change registry shapes or generated content and therefore require a new world:

- World dimensions
- Element-type count
- Chemical-signature dimension count
- Molecule-catalog target size
- Initially present molecule fraction
- Maximum element units per molecule
- Maximum reactant and product arity
- Stoichiometric coefficient cap
- Reaction-template count per molecule and kind
- Initial elemental abundance and charged-energy ranges
- Founder organism count

Changing one of these sliders marks the current setup as requiring regeneration; it must not mutate an active world's chemistry registries in place.

#### Live simulation controls

Values that do not invalidate existing definitions may be adjusted while paused or running:

- Rendering and simulation speed
- Heat-diffusion multiplier
- Mana-decay multiplier
- Decomposition-rate multiplier
- Reaction-rate multiplier
- Mutation-rate multiplier applied to future births
- Environmental abundance-display thresholds
- Audit frequency

Later action, metabolism, toxicity, reproduction, and perception coefficients should follow the same rule: expose them as live controls only when changing them cannot invalidate authoritative state.

Every live change is recorded as a tick-stamped configuration event. A deterministic replay applies the same events at the same ticks. Saved runs include the initial configuration plus the configuration-event history.

## 31. Simulation units and reference scales

The simulation uses fictional but internally consistent units:

- One tick is the base time unit.
- One tile is the base distance unit.
- Element definitions supply integer mass units.
- Energy is a continuous energy unit.

Procedural worlds may have very different element energies and organism masses. Action defaults are therefore normalized against run-specific immutable reference scales:

- `reference_energy`: median full-charge energy capacity of initially present molecule types
- `reference_body_mass`: median target adult structural mass of founder organisms
- `reference_batch_count`: median nonempty initial environmental molecule-batch count

The world records these values after generation. Configuration sliders store dimensionless coefficients relative to the references. This keeps a movement-cost slider meaningful across seeds without changing conservation accounting.

All denominators use schema-defined positive floors. A zero efficiency never causes division by zero; it makes the affected action ineligible.

## 32. Action economy and utility policy

### 32.1 Executable action types

High-level goals such as seeking food or fleeing produce one of these executable actions:

1. `wait`
2. `move_one_tile`
3. `ingest`
4. `physical_attack`
5. `run_reaction`
6. `grow`
7. `repair`
8. `excrete`
9. `absorb_heat`
10. `cast_magic`
11. `reproduce`
12. `propose_relationship`
13. `accept_relationship`
14. `share_resource`
15. `join_or_form_colony`
16. `leave_colony`

Movement is one adjacent wrapped tile per completed action in the first prototype. Faster organisms move more frequently rather than skipping across intermediate collision cells.

### 32.2 Action intent

A generated `ActionIntent` contains:

- `actor_id`
- `action_type`
- `target`, optional typed entity or wrapped tile reference
- `candidate_features`, normalized policy inputs
- `predicted_duration_ticks`
- `predicted_chemical_cost`
- `predicted_mana_cost`
- `required_matter`, if any
- `commitment_tick`
- `initiative`
- `reservation_requests`

Intent generation does not mutate authoritative state. Mutation begins only when an accepted intent commits.

### 32.3 Observation vector

Every decision receives a bounded observation containing these normalized internal features:

- Chemical reserve fraction
- Mana fraction
- Maintenance debt fraction
- Hunger derived from reserve deficit
- Integrity fraction
- Toxin burden relative to tolerance
- Age relative to baseline lifespan
- Senescence level
- Growth deficit relative to adult target
- Reproductive material fraction
- Reproductive cooldown fraction
- Current action commitment

Environmental and candidate-target features are:

- Expected food chemical energy
- Structural element match
- Dietary descriptor match
- Predicted pathway match
- Predicted toxin risk
- Local recoverable heat
- Heat gradient
- Target wrapped distance
- Target relative body mass
- Target observed integrity
- Target threat estimate
- Target prey value
- Mate compatibility estimate
- Alliance complementarity estimate
- Local crowding
- Magical threat by channel
- Previous action reward
- Exploration noise

Unknown values use an explicit `unknown` mask rather than being silently treated as zero.

### 32.4 Sight and sensory cost

Every organism receives a radius-one wrapped neighborhood observation around its footprint as part of basal maintenance. Larger realized sight radii observe additional cells and incur:

`C_sense = k_sense × reference_energy × extra_visible_cell_count / sensory_efficiency`

The default `k_sense` is `0.0005`. If the organism cannot pay the incremental chemical cost, its effective sight contracts until affordable, never below radius one. Mana cannot pay incremental sight cost.

Sight uses wrapped Chebyshev distance from the organism footprint. Observation construction deduplicates cells visible from multiple footprint tiles.

### 32.5 Candidate generation

The controller generates only eligible, locally relevant candidates:

- At most eight adjacent movement candidates
- At most four candidates per targeted action type
- At most one candidate per expressed pathway and present primary reactant
- One wait candidate, which is always eligible

Targets are ranked by inexpensive perceptual estimates before full utility features are calculated. These caps are configurable performance limits.

### 32.6 Utility calculation

For each candidate intent:

`utility = inherited action-feature weighted sum + expected benefit - energy-aversion × normalized cost + persistence bonus`

Expected benefit is computed from sensed information and may be wrong. Utility values are converted into probabilities with a softmax using the phenotype's decision-randomness temperature. A deterministic per-organism random stream samples the selected intent.

A zero temperature selects the highest utility with deterministic initiative tie-breaking. Larger temperatures increase exploration. The future neural policy must produce the same action-intent interface and obey identical eligibility and conservation rules.

### 32.7 Reference action costs

The following coefficients are initial slider defaults. `R_E` is reference energy, `R_M` is reference body mass, `m` is current structural mass, and all efficiencies are realized phenotype values.

| Action | Chemical or mana commitment |
|---|---|
| Wait | Basal maintenance only |
| Incremental sight | `0.0005 × R_E × extra cells / sensory efficiency` |
| Move one tile | `0.01 × R_E × (m/R_M) × (1 + speed_fraction²) / movement efficiency` |
| Turn without moving | `0.001 × R_E × (m/R_M)` |
| Ingest | `0.002 × R_E × (molecule_count/reference_batch_count)` |
| Physical attack | `0.02 × R_E × (m/R_M) × attack_strength² / attack efficiency` |
| Run reaction | Template activation energy plus pathway-specific costs |
| Grow | `0.02 × R_E × (incorporated_mass/R_M) / growth efficiency` |
| Repair | `0.02 × R_E × (repaired_mass_equivalent/R_M) / repair efficiency` |
| Excrete | `0.002 × R_E × (expelled_mass/R_M)` |
| Absorb heat | No action chemical cost beyond maintenance and sensing |
| Cast magic | Chosen mana commitment bounded by maximum cast fraction |
| Reproduce | `0.10 × R_E × (planned_offspring_birth_mass/R_M)` |
| Relationship proposal or acceptance | `0.001 × R_E` |
| Share matter or chemical energy | `0.001 × R_E × (transferred_mass/R_M)` |
| Transfer mana | Transferred mana plus `0.001 × R_E` paid chemically |

Chemical action costs debit metabolic carriers and become environmental heat. Mana pays only basal maintenance, lifespan support, magic, or explicit mana transfer. These defaults are balancing starting points, not claims of physical realism.

### 32.8 Action durations

Initial base durations are:

- Wait: one tick
- Move: `ceil(4 / maximum_speed)` ticks, minimum one
- Ingest: two ticks
- Physical attack: three ticks
- Reaction: template duration modified by throughput
- Grow or repair: four ticks
- Excrete: two ticks
- Absorb heat: two ticks
- Cast magic: two ticks plus configured range surcharge
- Reproduce: eight ticks
- Relationship or sharing action: two ticks
- Colony formation: twelve ticks

Action duration sliders are live only for newly committed actions. Existing actions retain their committed completion tick.

### 32.9 Commitment and failure costs

Accepted intents reserve required matter and debit commitment energy atomically. Default nonrefundable fractions after interruption or resolution failure are:

- Wait: zero additional cost
- Movement blocked after commitment: 25 percent of predicted movement cost
- Lost ingestion or attack target: 50 percent
- Interrupted reaction: already-spent activation energy
- Magic cast: 100 percent after mana leaves the caster
- Reproduction: 100 percent, as specified in Section 22
- Relationship or sharing failure: 50 percent
- Colony formation failure: 100 percent

Any unspent reserved energy is returned; every nonrefundable amount becomes heat. Reserved matter is returned unless a successful result transfers it or an explicit reaction transforms it.

## 33. Deterministic tick and conflict model

### 33.1 Tick phases

Every tick executes these phases in order:

1. Apply tick-stamped configuration events.
2. Rebuild dirty spatial and chemistry indexes needed for the tick snapshot.
3. Diffuse heat and execute scheduled environmental decomposition from prior ticks.
4. Apply organism mana decay, basal maintenance, starvation, toxin effects, aging, and passive recovery.
5. Finalize upkeep deaths and create corpses.
6. Complete due observations and collect new action intents from surviving organisms.
7. Compute deterministic initiative and reserve accepted action resources.
8. Resolve movement and forced displacement.
9. Resolve ingestion, physical attacks, magic, and direct transfers.
10. Resolve digestion, assimilation, detox, waste, growth, repair, and excretion.
11. Resolve reproduction, relationship transitions, and colony transitions.
12. Finalize post-action deaths and create corpses; their contents become interactable on the next tick.
13. Update abundance counters, species statistics, schedules, and dirty caches.
14. Run configured local and global audits.
15. Publish an immutable render snapshot.

New heat produced during a tick is immediately conserved but does not diffuse until the next tick. This prevents phase-order-dependent repeated diffusion.

### 33.2 Deterministic initiative

Initiative is derived from:

- World seed
- Current tick
- Action category
- Actor identifier
- Decision sequence number
- A bounded speed contribution for movement and attacks

The seed-derived component prevents permanent low-identifier advantage. Initiative is reproducible and does not consume an organism's behavioral random stream.

### 33.3 Reservations

Matter, energy, target capacity, and destination cells use transaction-like reservations. A resource can be reserved by only one accepted transaction unless sharing is explicit. Rejected reservations do not mutate inventories.

Reserved energy and matter move into tracked escrow records so global ledgers count them exactly once.

### 33.4 Movement conflicts

Movement intents are processed by descending initiative:

- Each proposed footprint must be legal under toroidal wrapping.
- It may not overlap an accepted stationary or destination footprint unless overlap is permitted by a colony rule.
- A move may use cells vacated by a higher-initiative accepted move.
- Lower-initiative chain moves may follow already accepted vacated cells.
- Direct swaps and cyclic rotations are rejected in the first prototype.
- Rejected moves pay the configured failed-movement fraction.

Large organisms reserve the complete destination footprint atomically.

### 33.5 Interaction conflicts

Attacks, ingestion, transfers, and reproduction revalidate targets at resolution. Reservations prevent negative inventories and duplicate consumption. If multiple attackers damage one target in the same phase, all accepted damage resolves before death finalization, but a target may not act in later phases after being marked dead.

A corpse created in phase 5 may be targeted during the current tick. A corpse created in phase 12 becomes targetable on the following tick.

### 33.6 Ongoing actions

A multi-tick action stores its committed inputs, completion tick, and interruption rule. Organisms undergoing an action remain subject to attacks, toxins, maintenance, and death. Death cancels the action, returns untransformed reserved matter to the corpse, and converts nonrefundable committed energy to heat.

## 34. Species and candidate-lineage model

### 34.1 Species definition

A species is a persistent reproductive population recognized from a combination of:

- Genomic-distribution similarity
- Ancestry
- Predicted reproductive compatibility
- Observed successful reproduction
- Viable and fertile descendant persistence

Species labels summarize the evolving population; they do not alter genomes.

### 34.2 Species record

A `SpeciesRecord` contains:

- `species_id`
- `status`: active, merged, split, or extinct
- `founder_ids`
- `parent_species_ids`
- `creation_tick`
- `extinction_tick`, optional
- `genome_centroid`
- `genome_dispersion`
- `representative_genome_ids`, bounded sample
- `living_member_count`
- `generation_count`
- `successful_asexual_events`
- `successful_sexual_events`
- `failed_reproduction_events`
- `within_species_compatibility_ema`
- `cross_species_compatibility_ema`
- `typical_element_profile`
- `descendant_species_ids`

Historical records are retained after extinction, merge, or split.

### 34.3 Assignment score

For a newborn and a candidate species:

- `G = 1 - genomic distance to species centroid`
- `C = predicted compatibility with bounded species representatives`
- `A = ancestry affinity`, equal to one for a direct parent species and decaying across lineage distance

The default assignment score is:

`S = 0.55 × G + 0.25 × C + 0.20 × A`

A newborn joins the highest-scoring species when `S >= 0.70` and genomic distance is at most `0.35`. Otherwise it enters or creates a candidate lineage. Weights and thresholds are sliders applied to future assignments.

### 34.4 Candidate-lineage record

A `CandidateLineageRecord` contains:

- Candidate identifier
- Founder and parent species identifiers
- Creation tick
- Living member identifiers
- Genome centroid and dispersion
- Generations observed
- Successful reproduction events
- Internal compatibility estimate
- External compatibility estimate
- Last viable tick

Candidate lineages use the same assignment calculation but are not treated as established species for UI totals or compatibility-history bonuses.

### 34.5 Promotion defaults

A candidate lineage becomes a species when it satisfies all of these configurable defaults:

- At least five living members
- At least three represented generations
- At least three successful reproduction events
- Mean internal genomic distance at most `0.20`
- Centroid separation of at least `0.15` from every parent species
- Internal compatibility exceeding nearest external compatibility by at least `0.10`
- Conditions sustained for two species-evaluation epochs

The default species-evaluation epoch is 250 ticks. Failed candidates remain historical lineage records and their surviving members may later join another lineage or species.

### 34.6 Reproductive-history modifier

Established successful reproduction provides a bounded compatibility-history modifier:

- Same-species success increases the relevant exponential moving average.
- Cross-species success updates both species records.
- Failure lowers the corresponding estimate.
- The modifier is clamped to `[0.75, 1.25]` and multiplies, but never replaces, genome and state-based fertility.

This makes established compatible populations somewhat more likely to produce similar successful offspring without making species labels deterministic reproductive barriers.

### 34.7 Split, merge, and extinction

At species-evaluation epochs:

- A species may split when bounded representative genomes form persistent separated groups that each satisfy candidate-promotion rules.
- Species may merge when centroid distance remains below `0.10`, cross-compatibility exceeds within-species compatibility minus `0.05`, and the condition persists for three epochs.
- A merge or split creates successor species records and closes predecessor records rather than rewriting history.
- A species becomes extinct when it has no living members and no active gestation or deferred offspring state. The first prototype has no gestation, so zero living members is sufficient.

Representative samples cap periodic comparison costs. Full all-pairs clustering is not required.

## 35. Magical effects and defense

### 35.1 Shared rules

Fire, water, earth, and air are effect channels, not chemical elements. A cast:

1. Debits mana at commitment.
2. Places that energy into an active magical-effect entity.
3. Applies affinity, casting efficiency, range, and target resistance.
4. Returns blocked, dissipated, and completed effect energy to environmental heat.

Magic creates no matter and stores no untracked energy.

### 35.2 Active effect record

An `ActiveMagicEffect` contains:

- Effect identifier
- Channel
- Source organism identifier
- Target entity or wrapped area
- Committed mana energy
- Remaining effect energy
- Potency
- Start tick
- Resolution tick
- Duration ticks
- Affected entity identifiers
- Status

### 35.3 Potency and resistance

`raw_potency = committed_mana × channel_affinity × casting_efficiency`

`effective_potency = raw_potency × (1 - target_channel_resistance)`

At commitment, mana equal to `committed_mana` enters the effect transaction. The difference between committed mana and raw potency is casting loss and immediately becomes heat. The resisted share of raw potency also becomes heat at the target. Only effective potency remains stored in an ongoing effect; it becomes heat as the effect applies or expires.

Resistance is bounded to `[0, 1]`. Effect-specific caps prevent a single cast from producing invalid displacement, negative speed, or negative integrity.

### 35.4 Channel semantics

Initial channel behavior is:

- Fire: immediate integrity damage plus short damage-over-time; resolved energy becomes local heat.
- Water: temporary movement, attack, and reaction-throughput reduction.
- Earth: temporary ward or immobilization effect; the ward is an energy field and has no molecular mass.
- Air: bounded forced displacement, evasion change, or sensory interference.

The caster selects an offensive, defensive, or escape intent. Channel preference and current utility determine the channel. These semantics are configurable effect templates and may be rebalanced without changing chemical rules.

### 35.5 Defense

Passive resistance requires no mana but is limited by phenotype. An organism may also cast an active ward, paying mana normally. Overlapping defenses resolve in deterministic effect order, and every absorbed effect-energy portion becomes heat.

Forced displacement uses the normal footprint collision system. Failed displacement does not delete effect energy; it returns the unused portion to heat.

## 36. Alliances, symbiosis, and multicellularity

### 36.1 Relationship registry

Relationships are authoritative world records rather than duplicated organism flags. A `RelationshipRecord` contains:

- Relationship identifier
- Participant identifiers
- Type: proposed alliance, active alliance, symbiosis, or broken
- Creation and transition ticks
- Trust by participant
- Recent contribution balances
- Resource-sharing permissions
- Minimum duration commitment
- Last interaction tick

Formation requires mutual accepted actions. Trust changes from observed sharing, defense, exploitation, and reproduction outcomes.

### 36.2 Conserved sharing

Allies may transfer:

- Molecule batches
- Chemical energy through charged molecule batches
- Mana
- Threat and sensory observations

Matter and energy transfers use normal reservations and ledgers. Shared observations do not create energy but may reduce duplicated perception work when participants are in sensory contact.

### 36.3 Emergent symbiotic tools

The first prototype does not create a separate arbitrary tool-crafting language. Persistent complementary relationships expose derived cooperative capabilities:

- Metabolic chains in which one member consumes another's waste
- Shared sensing
- Defensive coverage
- Resource transfer
- Coordinated movement or pursuit
- Role specialization

These capabilities emerge from existing phenotypes and relationship history rather than from hard-coded species professions.

### 36.4 Colony record

A multicellular composite is represented by a `ColonyRecord` containing:

- Colony identifier
- Member organism identifiers
- Founder relationship identifiers
- Creation tick
- Member roles
- Shared molecule inventory
- Shared mana, if enabled by permissions
- Cooperation score
- Complementarity score
- Maintenance-efficiency bonus
- Shared observation cache
- Colony reproduction cooldown
- Parent colony identifiers

Members remain organisms with their own genomes, phenotypes, inventories, damage, and death state.

### 36.5 Colony formation defaults

A group may attempt colony formation when:

- It forms a connected active symbiotic contact group.
- Every participant accepts the action.
- Every participant has sexual propensity at or below `0.10` and asexual propensity at or above `0.50`.
- The relationship has persisted for the configured minimum duration.
- Collective reproductive matter and action energy are available.

The sexuality thresholds are prototype sliders. Colony formation is probabilistic and uses the members' colony-formation traits, trust, compatibility, and specialization complementarity.

### 36.6 Efficiency bonus

The colony's maintenance bonus is:

`bonus = min(max_bonus, cooperation_score × complementarity_score × size_factor)`

The default maximum is 15 percent. The bonus reduces future summed basal maintenance and duplicated perception costs; it does not refund past energy and does not reduce the matter required for growth or reproduction.

Saved energy simply remains in the members' tracked reservoirs. Conservation therefore remains intact.

### 36.7 Composite reproduction

A composite reproduces asexually as a coordinated event:

1. Each member contributes reproductive matter and chemical attempt energy.
2. Each member produces one mutated asexual descendant.
3. The descendants form a new colony preserving the parental role template with mutation.
4. The complete offspring footprint must fit.
5. Attempt energy is nonrefundable after commitment.
6. Matter transfers only for successfully created descendants.

A member's death does not automatically destroy the colony. Cooperation, complementarity, and bonuses are recalculated; the colony dissolves when it no longer satisfies minimum membership or connectivity.

## 37. Maintenance, death, corpses, and decomposition

### 37.1 Basal maintenance

At each due maintenance update:

1. Calculate phenotype basal maintenance demand, modified by colony efficiency and active effects.
2. Pay from chemical carriers and mana according to mana-maintenance preference.
3. Convert paid energy to local environmental heat.
4. Add unpaid demand to maintenance debt.
5. Apply starvation damage when debt exceeds phenotype tolerance.

Mana cannot pay movement, growth, repair material, or reproduction costs.

### 37.2 Age hazard

Baseline age hazard uses a discrete Weibull-style cumulative hazard. For age `a`, update interval `d`, lifespan `L`, and hazard shape `k`:

`p_age = 1 - exp(-(((a + d)/L)^k - (a/L)^k))`

Chemical reserves and mana permit an organism to attempt active lifespan support according to its phenotype survival modifiers. Before the mortality roll, the organism may commit chemical energy, mana, or both from available reserves. Committed support energy becomes local heat. The resulting hazard reduction depends on committed energy, age, and the corresponding phenotype modifier and is capped at 95 percent by default. Merely owning a large reserve does not provide a free reduction; it provides the capacity to pay for support.

Toxin, starvation, injury, and senescence increase total mortality. Survival beyond baseline lifespan is possible but never guaranteed.

### 37.3 Death conditions

An organism dies when any of these occurs:

- Integrity reaches zero
- A deterministic seeded mortality roll succeeds
- Maintenance debt exceeds the fatal threshold
- A toxic or magical condition explicitly reaches a fatal threshold

Death is finalized only in phases 5 or 12 of Section 33.

### 37.4 Corpse creation

Death performs one atomic transaction:

- Mark the organism dead and cancel future scheduled actions.
- Return reserved untransformed matter to the dying organism's inventories.
- Convert nonrefundable committed energy and all stored mana to heat.
- Transfer every molecule batch into a new corpse record.
- Preserve exact footprint and death location.
- Remove the organism from living spatial and species counts.

A `CorpseRecord` contains corpse identifier, source organism identifier, footprint, creation tick, molecule inventory, current chemical energy, decomposition schedule, and consumer reservations.

### 37.5 Decomposition

Corpse batches decompose according to molecule stability, environmental modifiers, and the global decomposition multiplier. Decomposition uses validated templates from Section 25. Products remain in corpse cells as environmental molecule batches and released energy becomes heat.

Corpses may be consumed before decomposition. When all matter is transferred or decomposed, the corpse record becomes a historical tombstone and releases its spatial occupancy.

## 38. Conservation ledgers and audits

### 38.1 Matter ledger

The global matter ledger stores an exact integer vector by element across:

- Environmental cell inventories
- Living organism inventories
- Corpse inventories
- Colony shared inventories
- Transaction escrows

For each element, the current total must equal the world-initialization total exactly.

### 38.2 Energy ledger

The energy ledger totals finite 64-bit floating-point values in:

- Molecule-batch chemical energy
- Organism and colony mana
- Environmental heat
- Active magical effects
- Transaction escrows

Accounting counters such as lifetime expenditure are excluded because they describe flow rather than owned energy.

### 38.3 Transaction delta

Every state-changing transaction produces a bounded audit record containing:

- Tick and phase
- Transaction type
- Actor and target identifiers
- Element-vector deltas by reservoir
- Energy deltas by reservoir
- Result status
- Configuration version

Matter deltas must sum to exactly zero. Energy deltas must sum to zero within tolerance.

### 38.4 Numerical tolerance

Energy summation uses deterministic identifier order and compensated summation. The default global tolerance is:

`max(1e-9 energy units, initial_total_energy × 1e-12)`

Local transaction checks use a tighter scale-relative tolerance. Tolerances are diagnostic thresholds, not permission to create or delete energy intentionally.

### 38.5 Audit levels

- Level 0: counters only, intended for maximum-speed runs
- Level 1: local transaction checks and periodic global totals
- Level 2: every transaction plus per-tick global totals
- Level 3: full ownership, cache, registry, deterministic-order, and conservation validation

The UI exposes audit level. Test runs use Level 3. Interactive default is Level 1.

### 38.6 Violation handling

An audit violation:

1. Pauses the simulation.
2. Captures the failing transaction and recent event window.
3. Writes matter and energy reservoir differences.
4. Identifies dirty caches and ownership conflicts.
5. Never silently corrects authoritative state.

## 39. UI, save/replay, performance, and testing

### 39.1 Pygame interface

The initial interface includes:

- Toroidal world view with pan and zoom
- Organism footprints colored by species or selected trait
- Optional molecule-abundance, heat, mana, toxin, and magic overlays
- Pause, single-step, speed, restart, and seed controls
- Pre-run generation sliders and live sliders
- Selected organism genome, phenotype, inventory, energy, policy, ancestry, and relationship inspector
- Population, species, energy-reservoir, conservation-error, and molecule-abundance charts
- Event log filters for birth, death, speciation, reaction, magic, and audit events

Rendering consumes immutable snapshots and never mutates simulation state.

### 39.2 Save state

A save contains:

- Schema and engine version
- World seed and current tick
- Initial and current configuration versions
- Configuration-event history
- Immutable element, molecule, reaction, genome, phenotype, and species registries
- All authoritative world, organism, corpse, colony, relationship, effect, and escrow state
- Deterministic random-stream counters
- Ledger totals and state checksum

Caches and render snapshots are rebuilt after loading.

### 39.3 Replay guarantees

Within the same engine version and backend, replaying the same seed and tick-stamped user events must produce the same state checksums. Python and Rust backends must satisfy the same invariants and statistical behavior; bit-for-bit cross-backend identity is not required unless parity tests later prove it practical.

Checkpoints permit replay to resume without simulating from tick zero. Any nondeterministic UI timing is converted into an explicit target tick before entering the simulation event stream.

### 39.4 Performance budgets

Initial acceptance targets on the development machine are:

- Default world: 128 by 128 wrapped tiles
- 300 founder organisms and at least 500 concurrent living organisms
- Approximately 48 molecule types
- Interactive simulation: 20 simulation ticks per second
- Rendering: 60 frames per second when not fast-forwarding
- 95th-percentile simulation tick below 50 milliseconds at the 500-organism target
- Memory below 500 MB for a one-hour interactive run excluding optional detailed event archives
- Headless fast-forward at least five times interactive tick rate

Performance sliders may exceed these targets, but failure outside the acceptance configuration is not initially a defect.

### 39.5 Profiling and Rust FFI threshold

Python remains authoritative until profiling identifies a subsystem consuming at least 20 percent of tick time and a batch-oriented interface can isolate it. Likely candidates are reaction matching, visibility calculations, genome-distance batches, and heat diffusion.

Rust FFI calls must process arrays or batches, release the Python GIL where safe, return explicit deltas or results, and pass Python parity tests. Object-by-object FFI calls are prohibited in hot loops.

### 39.6 Required tests

The implementation test plan includes:

- Distribution bounds, deterministic sampling, inheritance, and mutation tests
- Toroidal distance, footprint, sight, and heat-diffusion tests
- Exact per-element reaction balancing tests
- Property-based reaction and inventory conservation tests
- Energy partition and capacity tests
- Failed movement, reaction, magic, and reproduction commitment tests
- Toxicity and detox relational-behavior tests
- Species assignment, promotion, split, merge, and extinction tests
- Relationship and colony conservation tests
- Death and corpse-transfer tests
- Save/load and deterministic replay checksums
- Cache invalidation and registry ownership tests
- Python/Rust parity tests for every migrated subsystem
- Long-running seeded integration tests with Level 3 audits

## 40. Implementation milestones and specification status

### 40.1 Milestones

1. Headless foundations: configuration, IDs, registries, deterministic random streams, inventories, transactions, and ledgers
2. World generation: toroidal grid, elements, molecule catalog, heat, reactions, and render shell
3. Basic life: organism creation, phenotype sampling, movement, sensing, maintenance, eating, digestion, waste, death, corpses, and asexual reproduction
4. Ecology: growth, repair, predation, toxicity, detoxification, heat harvesting, and mana
5. Magic: four effect channels, defenses, effects, and heat return
6. Sexual evolution: multi-parent reproduction, genomic distance, candidate lineages, and species records
7. Cooperation: alliances, symbiosis, resource sharing, colonies, and composite reproduction
8. Productization: complete sliders, inspectors, charts, save/load, replay, profiling, and optional Rust acceleration

Every milestone must maintain matter and energy conservation; conservation is not deferred until final integration.

### 40.2 Definition of implementation-ready

The specification is implementation-ready because:

- The prototype defaults below are confirmed.
- Every authoritative record has one owner.
- Every state-changing operation maps to a transaction and tick phase.
- All generated structures have hard bounds.
- Acceptance performance and audit targets are agreed.
- Implementation may be staged without violating later data-model requirements.

### 40.3 Confirmed prototype defaults

The confirmed initial defaults are:

1. Radius-one perception is free beyond basal maintenance; larger views cost chemical energy per extra cell.
2. Movement is one tile per action; speed changes action frequency.
3. Direct movement swaps and cyclic rotations are initially disallowed.
4. Fire damages, water slows, earth wards or immobilizes, and air displaces or disrupts sensing.
5. Colony eligibility initially requires sexual propensity at most `0.10` and asexual propensity at least `0.50` for every member.
6. Colony efficiency affects basal maintenance and duplicated perception, capped at 15 percent.
7. Species defaults use the assignment and promotion thresholds in Section 34.
8. Performance acceptance uses the 128×128, 500-organism, 20-tick-per-second target in Section 39.

All eight values are configuration defaults or replaceable effect templates rather than permanent engine restrictions.
