# Endogenous Neuroevolution Architecture

**Status:** Stages 1–4 complete. The preregistered Stage 4 matrix found recurrent state dependence but did not support evolved ecological memory; see [`NEUROEVOLUTION_STAGE4_RESULTS.md`](NEUROEVOLUTION_STAGE4_RESULTS.md).

**Research basis:** [`NEUROEVOLUTION_RESEARCH.md`](NEUROEVOLUTION_RESEARCH.md)

## 1. Objective

Add genetically inherited neural intelligence to the Rust simulation without adding an external objective or optimizer.

Selection remains exactly ecological:

1. an organism develops one controller phenotype from inherited distributions;
2. it senses, acts, pays physical costs, survives or dies, and may reproduce;
3. reproduction invokes the existing inheritance and mutation machinery;
4. descendants inherit controller genes;
5. differential lineage persistence is the only primary selection mechanism.

The architecture must answer two separate scientific questions:

1. Does a lower-level, spatial sensorimotor interface permit more adaptive behavior than the current hand-written macro-actions?
2. Does evolvable recurrent capacity become expressed when memory has ecological value despite its chemical-energy cost?

These questions are separated into treatments so a positive result is interpretable.

## 2. Approved constraints and decisions

### 2.1 Approved

- Primary evolution is entirely endogenous.
- There is no fitness callback, episode boundary, trainer, elite archive, global parent ranking, or optimizer.
- Lower-level actions are allowed.
- Existing genome centers/spreads and sibling-level developmental sampling remain.
- The current stochastic linear macro controller remains an unchanged control.
- Richer observations precede or accompany neural complexity.
- The first neural family has fixed maximum topology.
- Memory is initially functionally dormant and becomes usable through mutation of inherited expression genes.
- Expressed hidden and recurrent capacity consumes chemical energy.
- Brain energy becomes heat at the organism's position.
- Neural implementation is Rust-first; the Python behavior path remains a legacy control.
- NEAT/odNEAT, QD, offline ES/CMA-ES, lifetime plasticity, and safe mutation are separate later experiments.

### 2.2 Explicit non-goals for version two

- No dynamic graph topology.
- No gradient descent or backpropagation.
- No externally computed fitness.
- No behavioral archive involved in reproduction.
- No lifetime synaptic-weight updates.
- No Lamarckian inheritance.
- No general tensor/ML framework.
- No topology-aware sexual crossover.
- No parallel or simultaneous action resolver in this change.
- No Python/Rust numerical parity for the new neural treatment.
- No claim that a hidden layer alone constitutes intelligence.

## 3. Versioned experimental treatments

Controller choice is a startup configuration, not an evolvable locus. Mixing controller families in one ecology would confound controller quality with genome size, initialization, and action semantics.

```text
behavior_model = "legacy_linear_macro_v1"
               | "linear_intent_v2"
               | "recurrent_intent_v2"
```

### 3.1 `legacy_linear_macro_v1`

The current implementation remains byte-for-byte behaviorally unchanged:

- 10 observations;
- 13 macro-action outputs;
- current eligibility masks;
- current stochastic softmax;
- current targeting and movement helpers;
- no new brain cost;
- existing RNG consumption order and digest behavior.

This is the historical control and default until the new treatment is explicitly selected.

### 3.2 `linear_intent_v2`

Uses the new observation, candidate, and `ActionIntent` interfaces but only the direct linear component of the new controller.

Purpose:

- isolate the effect of removing macro-actions;
- validate that founders can survive with motor-level behavior;
- establish the minimum viable policy on the same interface as the neural treatment;
- provide the residual baseline inherited by the neural treatment.

It pays the fixed V2 brain base cost but no hidden or recurrent cost.

### 3.3 `recurrent_intent_v2`

Uses the same V2 interface and the linear controller as a residual path, then adds:

- eight expression-gated hidden units;
- eight units of recurrent state;
- expression-gated recurrent input;
- evolvable retention;
- proportional hidden and recurrent energy cost.

The recurrent contribution is dormant in founders. Memory must enter through mutation and survive ecological selection.

## 4. Module boundaries

The current `decide_and_act` function mixes perception, target selection, utility calculation, stochastic choice, and state mutation. V2 separates these responsibilities.

Proposed Rust modules:

```text
rust/src/behavior/mod.rs
rust/src/behavior/legacy.rs
rust/src/behavior/observation.rs
rust/src/behavior/intent.rs
rust/src/behavior/neural.rs
```

Responsibilities:

| Module | Responsibility |
|---|---|
| `legacy` | Wrap the existing macro path without semantic changes |
| `observation` | Build fixed, normalized, immutable V2 observations |
| `intent` | Generate bounded eligible candidates and typed intents |
| `neural` | Develop, inherit, evaluate, and meter V2 controllers |
| kernel `lib.rs` | Schedule decisions, validate/commit selected intent, own authoritative mutation |

The desired decision flow is:

```text
pay sensory cost
    -> observe immutable local state
    -> generate bounded eligible candidates
    -> evaluate controller
    -> sample one candidate
    -> produce ActionIntent
    -> revalidate against authoritative state
    -> commit immediately under existing serial scheduling
```

Intent generation does not mutate world, organism, inventory, relationship, or RNG state except for the single documented action-sampling draw. Recurrent state is committed with the selected decision because it is internal organism state.

This boundary prepares future read/intent/resolve/commit parallelism without introducing it now.

## 5. V2 observations

### 5.1 Coordinate system

V2 uses an egocentric frame based on the organism's existing eight-way `facing` vector.

Movement candidates are ordered canonically:

1. forward;
2. forward-right;
3. right;
4. back-right;
5. back;
6. back-left;
7. left;
8. forward-left.

No absolute `x`, `y`, compass direction, world seed, entity ID, lineage ID, species ID, or tick number is supplied to the controller. This avoids a privileged global frame and discourages coordinate memorization.

Facing changes only after a successful move. Waiting does not rotate the organism in V2.

### 5.2 Global observation vector

The V2 global vector is fixed at `OBSERVATION_COUNT = 28` and stored as `[f32; 28]`.

All finite scalar values are clamped to `[-1, 1]` or `[0, 1]` as declared below. Conservation remains `f64`/integer; `f32` is only a lossy sensory/controller representation.

| Index | Feature | Range |
|---:|---|---|
| 0 | chemical reserve fraction | `[0, 1]` |
| 1 | hunger (`1 - reserve`) | `[0, 1]` |
| 2 | mana fraction | `[0, 1]` |
| 3 | maintenance debt / death threshold | `[0, 1]` |
| 4 | integrity fraction | `[0, 1]` |
| 5 | toxin burden / tolerance | `[0, 1]` |
| 6 | age / baseline lifespan | `[0, 1]` |
| 7 | senescence excess | `[0, 1]` |
| 8 | growth deficit | `[0, 1]` |
| 9 | reproductive reserve fraction | `[0, 1]` |
| 10 | reproductive cooldown fraction | `[0, 1]` |
| 11 | reproductive maturity/readiness | `{0, 1}` |
| 12 | normalized body mass | `[0, 1]` |
| 13 | normalized speed | `[0, 1]` |
| 14 | normalized realized sight | `[0, 1]` |
| 15 | colony membership | `{0, 1}` |
| 16 | food value currently under footprint | `[0, 1]` |
| 17 | best visible directional food signal | `[0, 1]` |
| 18 | recoverable heat under footprint | `[0, 1]` |
| 19 | best visible directional heat signal | `[0, 1]` |
| 20 | maximum visible threat | `[0, 1]` |
| 21 | maximum visible prey value | `[0, 1]` |
| 22 | best visible mate compatibility | `[0, 1]` |
| 23 | contact crowding | `[0, 1]` |
| 24 | visible crowding | `[0, 1]` |
| 25 | food-known mask | `{0, 1}` |
| 26 | organism-target-known mask | `{0, 1}` |
| 27 | heat-known mask | `{0, 1}` |

The masks distinguish “observed zero” from “not observed.” Candidate-specific unknowns are represented separately.

Normalization denominators are named constants or generated reference quantities. Every denominator has a positive floor. No normalization depends on current population extrema, which would make the controller nonlocal and nonstationary.

### 5.3 Directional sensing

V2 does not supply a hand-selected best target position. Visible cells are assigned to one of eight egocentric sectors. For each candidate movement direction, the candidate receives bounded signals from its sector.

A signal is a deterministic, distance-discounted perceptual aggregate, not a path:

```text
signal = max(observed_value / (1 + Chebyshev_distance))
```

The first design uses `max` rather than a sum so signal scale does not grow with sight-area size. Candidate generation does not search a route or choose subsequent movements.

Values exposed through directional signals are:

- food chemical value after dietary-match and toxin-risk estimates;
- recoverable heat;
- prey value;
- threat;
- mate compatibility.

Sight remains subject to the current radius-one free observation and incremental chemical sight cost. If expanded sight is unaffordable, signals are built from the contracted radius.

### 5.4 Information deliberately withheld

The controller does not receive perfect future values, exact hidden inventories, exact genome distance, or whether a candidate action will succeed after another organism acts. Estimates can be wrong.

The controller never receives reproductive success, fitness, novelty, archive position, or experiment labels.

## 6. Bounded candidate set

### 6.1 Executable V2 intent types

V2 initially exposes only mechanics already implemented in the Rust kernel:

```rust
#[repr(u8)]
enum IntentKind {
    Wait,
    Move,
    Ingest,
    Repair,
    AbsorbHeat,
    Detox,
    Attack,
    CastMagic,
    Reproduce,
    ProposeAlliance,
}
```

`IntentKind` is a model, not a string. Human-readable names exist only at configuration and snapshot boundaries.

Changes from macros:

- `wander`, `forage`, `hunt`, `flee`, and `seek_mate` become one-tile `Move` candidates;
- `AbsorbHeat` cannot navigate to remote heat;
- `Attack` and `Reproduce` name explicit contact targets;
- `CastMagic` names one explicit visible target;
- `Wait` does not implicitly repair;
- `Repair` is explicit.

Authoritative action costs, conservation, cooldowns, occupancy, damage, and reproduction mechanics remain kernel rules.

### 6.2 Candidate limits

At most 33 candidates are evaluated per decision:

| Kind | Maximum |
|---|---:|
| wait | 1 |
| repair | 1 |
| adjacent move | 8 |
| ingest under footprint | 4 |
| absorb heat | 1 |
| detox | 1 |
| contact attack | 4 |
| visible magic target | 4 |
| asexual self + contact mates | 5 |
| contact alliance | 4 |
| **total** | **33** |

Candidate buffers use a fixed-capacity array or a reusable `Vec` preallocated once in `KernelState`; decision evaluation performs no allocation.

If more than four target candidates exist, cheap deterministic salience selects the four. Salience is used only to bound perception, never to pick the action:

- ingest: dietary value, then position/molecule ID;
- attack: estimated prey value, then organism ID;
- magic: estimated target relevance, then organism ID;
- mate: compatibility, then organism ID;
- alliance: complementarity, then organism ID.

Candidates are then ordered by `(IntentKind, egocentric direction, typed target key)`. Hash-set iteration order never determines a decision.

### 6.3 Candidate feature vector

Each candidate has `CANDIDATE_FEATURE_COUNT = 16`, stored as `[f32; 16]`.

| Index | Candidate feature | Range |
|---:|---|---|
| 0 | predicted chemical cost | `[0, 1]` |
| 1 | predicted mana cost | `[0, 1]` |
| 2 | predicted duration | `[0, 1]` |
| 3 | food/dietary value | `[0, 1]` |
| 4 | toxin risk | `[0, 1]` |
| 5 | recoverable heat | `[0, 1]` |
| 6 | prey/attack value | `[0, 1]` |
| 7 | threat estimate | `[0, 1]` |
| 8 | mate compatibility | `[0, 1]` |
| 9 | social complementarity | `[0, 1]` |
| 10 | destination crowding | `[0, 1]` |
| 11 | egocentric forward component | `[-1, 1]` |
| 12 | egocentric right component | `[-1, 1]` |
| 13 | target distance | `[0, 1]` |
| 14 | target-known mask | `{0, 1}` |
| 15 | persistence/same-kind-as-last-action | `{0, 1}` |

Irrelevant known features are zero; unknown target-derived features use zero plus a zero target-known mask. Target-specific estimates use only sensed state.

Movement candidate values include destination-cell values and directional-sector signals. This gives the controller directional sensors without code navigating on its behalf.

### 6.4 Intent structure

```rust
struct ActionIntent {
    actor_id: u32,
    kind: IntentKind,
    target: IntentTarget,
    predicted_duration_ticks: u32,
    predicted_chemical_cost: f64,
    predicted_mana_cost: f64,
}

enum IntentTarget {
    None,
    Position(Position),
    Organism(u32),
    Food { position: Position, molecule_id: u16 },
    SelfReproduction,
}
```

Candidate features are transient controller inputs and are not copied into the committed intent.

The kernel revalidates the selected intent immediately before commitment. A newly invalid intent becomes `Wait`; it is not resampled. This gives conflicts a deterministic consequence and prevents selection from repeatedly sampling until success.

## 7. Controller architecture

### 7.1 Dimensions

```text
N = 28 global observations
H = 8 hidden/recurrent units
T = 10 intent types
C = 16 candidate features
O = T + C = 26 controller outputs
```

The neural residual output is not one neuron per candidate. It consists of:

- 10 context-dependent intent-kind residuals;
- 16 context-dependent candidate-feature residual coefficients.

For candidate `c` of kind `k`, global observation `x`, and candidate features `f_c`:

```text
linear(c) = kind_bias[k]
          + dot(W_global[k], x)
          + dot(W_candidate[k], f_c)

residual(c) = kind_residual[k]
            + dot(feature_residual, f_c)

score(c) = linear(c) + residual(c)
```

`linear_intent_v2` uses only `linear(c)`, making it a genuinely linear candidate scorer. The recurrent treatment produces the residual terms from global neural context, allowing it to dynamically change how food, threat, cost, mate compatibility, direction, and other candidate properties are valued without a large fixed output head.

### 7.2 Residual recurrent network

For normalized global observation `x`, previous state `s`, hidden expression `e`, recurrent expression `r`, and retention `rho`:

```text
pre_i = hidden_bias_i
      + W_input_i x
      + r_i * (W_recurrent_i s)

active_i = e_i * tanh(pre_i)
state_next_i = rho_i * s_i + (1 - rho_i) * active_i

kind_residual = W_kind_output active
feature_residual = W_feature_output active
```

These residual terms enter the candidate-scoring equation in Section 7.1.

Constraints:

- `x`, `s`, `active`, and matrices are `f32`;
- `e_i`, `r_i`, and `rho_i` are clamped to `[0, 1]` at development;
- recurrent state is clamped to `[-1, 1]` after update;
- all non-finite intermediate values produce a deterministic safe `Wait`, increment an error counter, and clear the organism's neural state;
- no allocation, trait object dispatch, tensor shape, or sparse graph occurs in inference.

The direct path makes `linear_intent_v2` a strict ablation of the neural treatment. The neural component can initially be near zero without deleting baseline sensorimotor behavior.

### 7.3 Why eight hidden units

Eight units are deliberately small:

- sufficient for several independent internal traces or oscillatory dynamics;
- bounded at 32 bytes of runtime state per organism;
- small enough for direct genetic encoding at large populations;
- easy to lesion and visualize;
- leaves topology growth as a meaningful later experiment.

Changing `H` creates a new behavior schema version; it is not a runtime slider.

### 7.4 Memory dormancy

Founder recurrent-expression centers and spreads are exactly zero. Founder recurrent weights may be nonzero, but they cannot affect behavior while `r_i = 0`.

Mutation can increase `r_i`. Once recurrence is expressed, retention `rho_i` controls persistence. The relevant distinctions are:

- `r_i = 0`: prior state cannot affect the current decision; functionally feed-forward;
- `r_i > 0, rho_i = 0`: one-decision recurrent trace remains possible through `s = active`;
- `r_i > 0, rho_i > 0`: leaky longer-timescale memory;
- `e_i = 0`: unit is silent regardless of recurrent genes.

The simulator still updates the fixed state array for deterministic uniformity, but unexpressed recurrence has no behavioral effect and no recurrent energy cost.

### 7.5 Continuous expression versus discrete topology mutation

The first treatment uses continuous expression gates rather than add/remove-connection mutations.

| Continuous fixed-capacity expression | Discrete topology mutation |
|---|---|
| fixed memory and compute | variable memory and compute |
| ordinary scalar inheritance | innovation/alignment metadata |
| gradual mutational path from zero | potentially abrupt structural mutation |
| simple developmental sampling | topology development rules needed |
| bounded worst-case inference | sparse graph traversal |
| dormant genes can accumulate | absent genes have no hidden effects |

The primary risk of continuous gates is cryptic nonzero weights accumulating while dormant, so the first expression mutation can have a large effect. Mitigations are bounded weights, near-zero founder recurrent weights, small mutation magnitude, and telemetry. Safe/behavior-normalized mutation is reserved for a later ablation if destructive activation is observed.

A discrete recurrent-edge treatment remains scientifically valuable after the fixed-capacity result is established.

## 8. Genetic representation

### 8.1 Separate compact neural gene

Neural parameters use a compact representation because each offspring may have a distinct genome:

```rust
#[derive(Clone, Copy, Debug)]
struct NeuralGene {
    center: f32,
    spread: f32,
}
```

The existing `Gene { f64, f64 }` remains unchanged for physical traits and the legacy policy. Development samples in `f64` using the existing deterministic RNG and clamps before conversion to `f32`.

Proposed brain genome:

```rust
struct IntentBrainGenome {
    kind_bias: [NeuralGene; T],
    global_weights: [[NeuralGene; N]; T],
    candidate_weights: [[NeuralGene; C]; T],
    hidden_bias: [NeuralGene; H],
    input_weights: [[NeuralGene; N]; H],
    hidden_expression: [NeuralGene; H],
    recurrent_weights: [[NeuralGene; H]; H],
    recurrent_expression: [NeuralGene; H],
    retention: [NeuralGene; H],
    kind_output_weights: [[NeuralGene; H]; T],
    feature_output_weights: [[NeuralGene; H]; C],
    decision_temperature: NeuralGene,
}
```

Approximate size before alignment:

- 979 neural loci;
- 7,832 bytes per genome module;
- 3,916 bytes per developed `f32` phenotype module;
- 32 bytes recurrent state per living organism.

This is a material scaling cost. Benchmarks and resident-memory measurements are mandatory before claiming 100k-agent suitability.

### 8.2 Founder initialization

V2 founder archetypes receive declared weak viability priors in the direct path:

- hunger increases food-valuing coefficients;
- toxin burden decreases toxic-food and increases detox valuation;
- threat increases threat avoidance;
- maturity/reserve increases reproductive intent valuation;
- low integrity increases repair valuation;
- heat deficit and available heat increase heat absorption;
- movement cost and low reserve discourage movement.

The initialization does not select organisms or guarantee survival. Priors are fixed by schema and shared by `linear_intent_v2` and `recurrent_intent_v2`.

Required founder controls:

1. prior-initialized V2 founders;
2. fully random V2 founders;
3. legacy founders.

Initial neural residual settings:

- linear kind/global/candidate weights use the same priors in linear and neural treatments;
- hidden input weights are small random values;
- hidden expression is low but nonzero;
- kind/feature residual output weights are centered near zero;
- recurrent weights are small random values;
- recurrent expression center/spread is zero;
- retention center is zero;
- decision temperature centers at the current effective temperature of `1.0`.

Every prior and distribution is named and testable. No evolved result may be used to retroactively redefine the initialization on the same evaluation seeds.

### 8.3 Mutation

Neural loci use the offspring's existing inherited mutation rate and magnitude, multiplied by `mutation_multiplier`.

Initial operators:

- independent mutation event per locus;
- additive Gaussian center mutation scaled to the locus range;
- floor-aware multiplicative spread mutation;
- hard finite bounds after mutation;
- nonzero mutation floor inherited from current trait limits;
- no gradients and no observation replay.

Floor-aware spread mutation uses a small schema constant `epsilon` inside the multiplicative transform and removes it afterward. This preserves the current log-scale character while allowing an exactly zero founder spread to evolve above zero. Without this rule, the existing purely multiplicative operator would make zero spread an absorbing state.

Suggested locus ranges:

| Locus | Range |
|---|---|
| global/candidate/input/output/recurrent weight | `[-3, 3]` |
| bias | `[-3, 3]` |
| hidden/recurrent expression | `[0, 1]` |
| retention | `[0, 0.995]` |
| decision temperature | `[0.05, 2.0]`, logarithmic |

Retention does not reach exactly one, preventing an immortal stale state.

### 8.4 Sexual inheritance

Physical and existing scalar/vector genes retain current blending.

For the complete `IntentBrainGenome`:

1. choose one parent uniformly as the brain donor;
2. copy that donor's entire brain genome;
3. mutate copied loci using the offspring mutation parameters;
4. record all biological parent IDs as today.

No per-weight arithmetic averaging occurs between hidden controllers. This avoids hidden-unit permutation damage and provides a clean baseline.

Later experiments may compare:

- coherent whole-neuron crossover;
- activation-based neuron alignment;
- NEAT-style historical markings.

### 8.5 Developmental sampling

Every neural locus retains center/spread semantics:

- the genome stores the heritable distribution;
- `Phenotype::sample` produces one fixed controller phenotype at birth;
- controller weights do not resample during life;
- recurrent state starts as all zeros;
- siblings can develop different weights, expression, retention, and temperature.

A sexual pair producing several offspring samples each offspring independently from its newly inherited genome.

### 8.6 Species distance

Brain weights do not enter primary species assignment in V2. The current `Genome::distance` already excludes policy weights, and adding approximately one thousand mutable neural loci would dominate physical compatibility.

Neural distance is logged separately for analysis. A brain-inclusive species model is a later hypothesis, not an incidental consequence of implementation.

## 9. Brain energy economy

### 9.1 Cost model

Brain cost is paid every upkeep tick, not only on decision ticks. Charging per decision would make fast organisms pay more solely because action scheduling is faster and would conflate speed with neural tissue metabolism.

For phenotype expression values `e_i` and recurrent expression values `r_i`:

```text
hidden_expression_mean = sum(e_i) / H
memory_expression_mean = sum(e_i * r_i) / H

brain_demand = reference_energy
             * brain_cost_multiplier
             * (brain_base_cost
                + brain_hidden_cost * hidden_expression_mean
                + brain_recurrent_cost * memory_expression_mean)
```

Proposed initial dimensionless defaults:

```text
brain_cost_multiplier = 1.0
brain_base_cost       = 0.001
brain_hidden_cost     = 0.002
brain_recurrent_cost  = 0.002
```

Thus:

- `linear_intent_v2` costs `0.001 × reference_energy` per tick;
- an average half-expressed feed-forward brain costs `0.002 × reference_energy` per tick;
- a fully expressed recurrent brain costs at most `0.005 × reference_energy` per tick.

These defaults are provisional until a pre-registered viability calibration verifies that the V2 founder envelope is neither automatic extinction nor effectively free. Calibration may use short dedicated seeds and may alter coefficients once before comparative evolutionary runs.

### 9.2 Payment and conservation

Brain demand is chemical-only; mana cannot pay it.

During upkeep:

1. compute physiological demand as today;
2. allow mana preference to pay only the physiological component;
3. add full brain demand to remaining chemical demand;
4. consume available body chemical energy;
5. transfer all paid chemical and mana energy to local environmental heat;
6. add any total deficit to existing maintenance debt and integrity damage.

Colony discount applies to physiological basal demand but not brain demand. Otherwise social membership would directly subsidize cognition independently of resource sharing.

Legacy mode has exactly zero added brain demand. V2 coefficients are startup-only configuration and included in experiment metadata.

### 9.3 Why cost expression rather than operations or activity

Cost is based on the developed phenotype, not wall-clock operations or instantaneous activation.

- CPU optimization must not alter simulated physics.
- An expressed but temporarily quiet brain still has tissue-maintenance cost.
- Dormant hidden/recurrent capacity can drift at low cost.
- Memory must provide sufficient ecological value to offset recurrent expression.

The fixed direct-path base cost represents baseline sensing and decision tissue. Incremental terms represent hidden and recurrent capacity.

## 10. Action sampling and determinism

### 10.1 Softmax

Candidate scores are sampled with phenotype temperature `tau`:

```text
p(c) proportional to exp((score(c) - max_score) / tau)
```

Scores are clamped before exponentiation. Exactly one RNG uniform is consumed for candidate selection. `tau` is bounded away from zero; deterministic argmax can be a separate later treatment.

### 10.2 Canonical ordering

All visible cells, target IDs, food batches, and candidates that can influence caps or tie-breaking are explicitly sorted. No `HashSet` or `HashMap` iteration order reaches scoring or RNG consumption.

### 10.3 Recurrent update timing

- Input uses state from the prior completed decision.
- The network computes `state_next` exactly once per scheduled decision.
- `state_next` commits even if the selected intent fails revalidation, because the organism made the decision from its observation.
- Upkeep ticks without a decision do not advance recurrent state.
- Birth and explicit numerical-failure recovery set state to zero.
- Death records do not retain recurrent state unless an analysis option explicitly samples it.

### 10.4 Legacy preservation

The legacy function and action order remain isolated. Merely compiling V2 must not change the same-seed digest of `legacy_linear_macro_v1`.

## 11. Data layout and performance

### 11.1 Cold versus hot data

Cold, immutable, shared per organism:

- `Arc<Genome>`;
- `Arc<Phenotype>`;
- developed controller matrices.

Hot mutable organism state:

- `[f32; H]` recurrent state;
- last executable intent code;
- cumulative brain energy spent;
- neural numerical-error count.

The existing entity arena remains authoritative. A later structure-of-arrays migration may move recurrent state out of `Organism`, but V2 should not combine that migration with controller semantics.

### 11.2 Inference loops

- fixed arrays and `for` loops;
- row-major weights by output/hidden unit;
- `#[inline]` only after measurement;
- no heap allocation;
- no BLAS, Burn, Candle, or ndarray dependency initially;
- no virtual `Controller` trait in the per-organism hot loop; dispatch once on simulation `BehaviorModel` outside or at the top of the decision path;
- benchmark manual loops against static `nalgebra` only if manual inference is a measured bottleneck.

The implementation may skip recurrent dot products for a row whose developed `r_i` is exactly zero. The physical cost remains based on expression and is independent of whether the compiler skips arithmetic.

### 11.3 Performance budgets

Performance acceptance is relative to the matching V2 linear treatment, not only the faster legacy macro treatment.

Initial targets on the documented benchmark machine:

- neural arithmetic adds no allocation per decision;
- recurrent evaluation adds at most 25% decision-phase wall time over `linear_intent_v2` at 1,200 founders;
- memory use is measured at 1,200, 10k, and the largest feasible synthetic population;
- legacy benchmark regression is below 3%;
- no claim about 100k support without a measured resident-memory result.

If candidate perception, rather than neural arithmetic, dominates, optimize observation construction without altering its schema or values.

## 12. Persistence, snapshots, and telemetry

The Rust kernel currently exposes snapshots rather than a full checkpoint format. V2 adds explicit schema metadata now so future persistence is not ambiguous.

Snapshot metadata:

```text
behavior_model
observation_schema_version = 2
intent_schema_version = 2
brain_schema_version = 1
brain_dimensions = { observations: 28, hidden: 8, candidate_features: 16, intent_types: 10 }
brain_cost_coefficients
```

Per-organism inspectable fields:

- developed hidden-expression mean;
- developed recurrent-expression mean;
- developed retention mean;
- developed decision temperature;
- current recurrent state;
- cumulative chemical brain energy spent;
- number of decisions;
- numerical-failure count;
- last executable intent and target type.

Aggregate telemetry by tick/sample interval:

- brain chemical energy spent;
- mean and distribution of hidden/recurrent expression;
- mean retention conditional on recurrence expression;
- intent frequencies and failures;
- population and birth/death counts by treatment/seed;
- offspring distribution by expression decile;
- controller numerical failures.

Telemetry is observational. It never affects inheritance or candidate sampling.

The deterministic digest must include:

- behavior/schema identifiers;
- complete brain genome and phenotype;
- recurrent state;
- brain energy counters if authoritative;
- V2 last-intent state.

## 13. Experimental contract

### 13.1 Primary hypotheses

**H1 — interface:** On the same lower-level interface, inherited V2 linear controllers can evolve persistent resource-seeking and avoidance behavior without macro navigation.

**H2 — nonlinear capacity:** `recurrent_intent_v2` lineages exhibit ecological outcomes not explained by `linear_intent_v2`, after accounting for their additional metabolic cost.

**H3 — memory:** In environments with temporally aliased observations, recurrent expression rises above neutral/drift controls and recurrent-state lesions reduce behavioral or reproductive performance.

### 13.2 First measurable intelligence benchmark

The first benchmark should be an ecological delayed-information niche, not an external training task.

Proposed **intermittent-resource gradient**:

- normal endogenous reproduction and death;
- food-rich patches are spatially stable over medium windows but local food is intermittently exhausted;
- current radius-one observations can be identical for organisms that recently observed food in different directions;
- remembering recent directional evidence can improve return/navigation behavior;
- no reward or fitness value is supplied to the controller.

Measured post hoc:

- return probability to recently observed productive sectors after temporary loss of sight;
- chemical energy acquired per movement cost;
- survival and offspring distributions;
- recurrence expression over generations;
- within-agent replay/lesion differences with recurrent state zeroed.

A simpler pre-evolution unit scenario verifies capacity but is not used to select genomes: construct two histories ending in the same current observation and show an expressed recurrent controller can choose different intents while a linear controller cannot.

### 13.3 Treatments

Minimum comparative matrix:

1. legacy linear macro V1;
2. V2 linear intent with viability priors;
3. V2 recurrent intent with dormant founder recurrence;
4. V2 recurrent intent with recurrence forcibly clamped to zero;
5. V2 recurrent intent with zero recurrent metabolic cost;
6. V2 random-founder control.

The zero-cost arm tests whether expression is selected for function or accumulates neutrally. The clamped arm controls for the larger genome and feed-forward hidden path.

### 13.4 Replication

Before long runs, record:

- fixed seed list;
- tick budget;
- founder count and archetype count;
- extinction handling;
- coefficient version;
- environment configuration;
- metrics and analysis intervals;
- exclusion criteria limited to simulator invariant failures.

Use multiple independent seeds. Extinction is a result, not an automatically discarded run.

### 13.5 Evidence for evolved memory

Rising recurrent genes alone are insufficient. A memory claim requires converging evidence:

1. recurrent expression is heritable and rises relative to controls;
2. recurrent states contain information about prior observations after conditioning on current observation;
3. zero-state or zero-recurrence lesions change decisions in temporally ambiguous situations;
4. lesions reduce an ecological consequence such as resource efficiency, survival, or offspring count;
5. the effect replicates across seeds or independent evolved lineages;
6. the energy premium paid by recurrent organisms is reported.

No neural-complexity metric is optimized directly.

## 14. Validation plan

### 14.1 Unit tests

Observation and candidates:

- every value is finite and in its declared range;
- unknown masks distinguish absent from observed-zero;
- rotating world and facing together preserves egocentric observation/candidate values;
- radius-one observation remains when expanded sight is unaffordable;
- candidate caps and canonical ordering hold;
- no ineligible candidate is generated;
- candidate generation does not mutate authoritative state.

Controller:

- fixed input/weights produce golden outputs;
- zero neural residual exactly equals direct linear output;
- zero recurrence expression makes output independent of previous state;
- nonzero recurrence can distinguish identical current observations after different histories;
- zero hidden expression silences a unit;
- retention bounds state and decays as specified;
- softmax is finite for extreme legal weights;
- non-finite defense produces `Wait` and clears state;
- inference allocates zero times after warm-up.

Genetics:

- same genome/seed develops identical phenotype;
- different offspring samples can differ;
- founder recurrence is exactly functionally dormant;
- neural genes remain within bounds after mutation;
- sexual inheritance chooses one coherent donor brain;
- brain mutation does not mutate the donor;
- legacy policy inheritance remains unchanged.

Energy:

- brain debit equals local heat increase when fully paid;
- partial payment records only paid heat and adds exact deficit/debt;
- mana cannot pay brain cost;
- colony bonus does not discount brain cost;
- zero-expression cost equals base cost;
- full expression equals the configured maximum formula.

### 14.2 Integration tests

- legacy same-seed digest remains unchanged from a recorded golden digest;
- V2 same-seed runs have identical digests;
- changing behavior model changes schema metadata and digest;
- conservation audits pass with brain cost enabled;
- selected invalid intent deterministically degrades to `Wait`;
- births begin with zero recurrent state;
- death/removal does not leak state to reused organism slots;
- snapshots expose valid brain metadata and telemetry.

### 14.3 Property and fuzz tests

Without adding a property-test dependency initially, deterministic loops cover:

- random legal genes and observations never panic or produce non-finite outputs;
- all legal expression/cost combinations conserve energy;
- mutation/development never leave declared ranges;
- candidate caps hold under dense local populations and deposits.

Add `proptest` only if handwritten coverage becomes cumbersome.

### 14.4 Benchmarks

Add Rust criterion-free benchmark binaries or `#[bench]`-style stable harness alternatives first; avoid a dependency until needed.

Measure:

1. pure linear inference;
2. pure recurrent inference with recurrence off/on;
3. score computation for 1, 8, and 33 candidates;
4. observation/candidate generation at sight 1, 3, and 6;
5. full decision phase at 1,200 founders;
6. full ticks versus the documented legacy baseline;
7. peak RSS at growing synthetic populations.

Release mode uses the existing LTO configuration. Report CPU, compiler, feature flags, population trajectory, and sample size.

## 15. Implementation sequence and mandatory stop points

### Stage 0 — Design approval

Human approves or revises this document. No Rust changes before approval.

### Stage 1 — Scaffold only

- add behavior/schema models;
- add observation, candidate, intent, and controller data types;
- add startup config parsing and metadata;
- route legacy behavior through an unchanged branch;
- add no active V2 mechanics yet;
- prove legacy digest and benchmark stability.

**Stop for scaffold review.**

### Stage 2 — Linear intent interface

**Implementation status:** complete, pending human review.

- implement pure V2 observation construction;
- implement bounded candidate generation;
- implement direct linear scorer and softmax;
- implement immediate intent revalidation/commit;
- add brain base cost;
- add tests and telemetry;
- run viability calibration and comparison with legacy.

**Stop for behavior-interface review.**

### Stage 3 — Genetic recurrent residual

**Implementation status:** complete, pending human review.

- add compact brain genome and developmental phenotype;
- add whole-brain donor inheritance and mutation;
- add recurrent state and inference;
- add hidden/recurrent metabolic cost;
- add digest/snapshot integration;
- add lesion hooks available only to explicit analysis APIs/configured treatments.

**Stop for implementation and quality review.**

### Stage 4 — Scientific validation

**Implementation status:** complete. Sixty-seven of 72 runs passed invariants; five high-population runs were excluded under the preregistered rule. Only the interface-prior and within-agent state-dependence tests were significant. The full evolved-memory convergence criterion was not met.

- freeze schema and coefficients;
- preregister seed matrix and metrics;
- benchmark performance and memory;
- run short invariant/determinism suites;
- run replicated ecological experiments;
- report positive, null, and extinction outcomes.

No NEAT, QD, plasticity, safe mutation, or parallel resolver work enters these stages.

## 16. File-level change plan

Expected files after approval:

| Path | Planned change |
|---|---|
| `rust/src/behavior/mod.rs` | behavior model/schema dispatch |
| `rust/src/behavior/legacy.rs` | isolated legacy call path or wrapper |
| `rust/src/behavior/observation.rs` | V2 observations and directional signals |
| `rust/src/behavior/intent.rs` | candidates, typed targets, intent generation |
| `rust/src/behavior/neural.rs` | brain genes, phenotype, inference, costs |
| `rust/src/genetics.rs` | attach brain genome/phenotype and inheritance |
| `rust/src/entities.rs` | recurrent state and brain telemetry |
| `rust/src/config.rs` | startup-only behavior/cost configuration |
| `rust/src/lib.rs` | scheduling, authoritative intent commit, PyO3 metadata |
| `PERFORMANCE.md` | benchmark methodology/results |
| `SPEC.md` | record implemented V2 schema and deviations |

No existing untracked or unrelated work is deleted, formatted wholesale, or rewritten.

## 17. Risks and mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| V2 founders cannot feed before extinction | no evolutionary signal | staged linear viability treatment, declared weak priors, random control |
| richer observation remains too compressed | no spatial cognition | egocentric directional candidate signals, explicit masks, schema versioning |
| recurrence drifts without function | false memory claim | chemical cost, clamped/zero-cost controls, lesions |
| brain cost guarantees extinction | treatment unfairly fails | one-time preregistered viability calibration before frozen runs |
| neural genes dominate memory usage | poor 100k scaling | compact `f32` loci, fixed H=8, RSS benchmark, no 100k claim without evidence |
| naive crossover destroys behavior | sexual lineages fail | coherent one-parent brain inheritance |
| dormant recurrent weights activate catastrophically | recurrent innovation is selected out | bounded small weights, low mutation scale, telemetry, later safe-mutation arm |
| same-tick serial ordering dominates behavior | ecological bias | canonical intent generation now; separate future resolver version |
| candidate salience smuggles in intelligence | hand-coded behavior remains | salience only caps candidates; network chooses; random/linear controls |
| experimenter tunes for desired outcome | invalid scientific claim | freeze schema/config/seeds, report extinctions and nulls |
| legacy semantics accidentally change | control invalidated | golden digest and benchmark before each stage |
| non-finite recurrent state contaminates run | nondeterminism/collapse | bounded activations, finite checks, deterministic wait/reset |

## 18. Approval decisions requested

Approval of this design authorizes only Stage 1 scaffold work. In particular, approval accepts:

1. three separate behavior treatments;
2. a 28-input, 8-hidden, 16-candidate-feature, 10-intent fixed architecture;
3. a residual direct linear path;
4. continuous per-unit hidden/recurrent expression and retention;
5. coherent one-parent brain inheritance during sexual reproduction;
6. chemical-only per-tick brain cost with proposed normalized defaults;
7. egocentric directional sensing and one-tile movement;
8. the bounded 33-candidate interface;
9. explicit staged reviews before active V2 behavior and recurrent implementation.

Any change to those points during implementation requires returning to design review rather than silently expanding scope.
