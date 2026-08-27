# Genetic Intelligence / Neuroevolution Research Review

## Status and scope

This document is the research stage preceding a repository-specific design. It does not prescribe an implementation yet.

The target constraints are:

- intelligence must evolve entirely through the simulated ecology;
- no external fitness, episodic trainer, elite selection, novelty archive, or optimizer may choose primary-simulation offspring;
- lower-level sensorimotor actions may replace the current high-level movement macros;
- functional memory should itself emerge through evolution rather than being compulsory;
- genomes continue to encode distributions, and each offspring receives one developmentally sampled phenotype;
- niches, survival, mating, and reproduction provide selection;
- the current linear controller remains an explicit control treatment;
- fixed-topology networks are the first implementation family;
- NEAT, quality-diversity, and offline evolution strategies remain separate experimental arms.

## 1. What the simulator already has

The Rust kernel already implements a minimal form of neuroevolution.

`rust/src/genetics.rs` defines:

- 10 fixed observation features;
- 13 action categories;
- a `13 × 10` matrix of `Gene { center, spread }` policy weights;
- developmental sampling of every weight at birth;
- inherited mutation rate and magnitude;
- asexual and sexual inheritance;
- a stochastic softmax controller.

`rust/src/lib.rs` computes the action logits as a linear dot product and then masks ineligible actions. Therefore the current controller is a single linear neural layer, not a non-neural placeholder.

### 1.1 Current observations

The implemented features are:

1. hunger;
2. detected food value;
3. local heat;
4. strongest nearby threat;
5. presence of prey;
6. toxin burden;
7. mana fraction;
8. mate/asexual opportunity;
9. crowding;
10. hunger reused as an energy-cost proxy.

These values discard most spatial structure. They do not tell the controller where a resource, threat, or mate is, nor distinguish multiple candidates.

### 1.2 Current actions

Several outputs are high-level macros:

- `forage` selects a food target and moves toward it;
- `hunt` selects prey and moves toward it;
- `flee` selects a threat and moves away;
- `seek_mate` selects a mate and moves toward it;
- `heat` selects or absorbs from a heat location.

Consequently, hand-written code performs much of the navigation, target selection, and tactical reasoning. A deeper network over the same interface could evolve nonlinear action preferences, but it would have little opportunity to evolve spatial cognition.

### 1.3 Existing specification anticipated the needed boundary

`SPEC.md` already defines a richer, versioned observation/action contract:

- internal physiological features;
- environmental and candidate-target features;
- explicit unknown masks;
- up to eight adjacent movement candidates;
- bounded target candidates;
- an `ActionIntent` that separates decision from authoritative mutation;
- the requirement that future neural policies obey the same eligibility and conservation rules.

The implemented prototype compressed this into macro-actions. Restoring a bounded intent interface is therefore aligned with the original model rather than a new conceptual direction.

## 2. The closest algorithmic paradigm: embodied evolution

Bredèche, Haasdijk, and Prieto define embodied evolution as decentralized, online, and parallel evolution in a population of agents. Agents act in the task environment while local mating, inheritance, variation, and replacement occur without a central selector.

That paradigm maps closely to this simulation:

| Embodied-evolution concept | Current simulation |
|---|---|
| decentralized selection | no global parent ranking |
| online evolution | reproduction occurs during ordinary ticks |
| local mating | physical contact and mate readiness |
| environmental selection | food, predation, chemistry, energy, and reproduction |
| asynchronous replacement | births and deaths occur independently |
| genotype–phenotype development | genome distributions sampled once at birth |

The important lesson from the review is that selection pressure is the aggregate of agent behavior, mating mechanics, and environmental conditions. Even without an explicit objective, organisms compete through their ability to remain viable and spread their genomes.

This means the primary implementation does not need a separate genetic-algorithm training loop. The ecology is the evolutionary algorithm.

### Evidence and caveats

- Environment-only selection has produced self-sustaining behavior in embodied-evolution studies.
- Local mating changes exploration/exploitation and can preserve diversity.
- Environmental parameters that affect encounters or genome transmission can dominate evolutionary outcomes.
- Online evaluation is noisy because individuals are born into different local circumstances.
- Task performance and ecological viability can conflict.

The simulator should therefore log reproductive success and behavioral consequences but must not convert those measurements into an external fitness score.

## 3. Direct fixed-topology neuroevolution

A direct encoding stores neural weights in the genome and mutates them. It is the simplest extension of the current policy matrix.

### Supporting evidence

Floreano and Keller review experiments in which small, directly encoded neural controllers evolved:

- collision-free navigation;
- homing behavior that combined position and battery state;
- predator and prey strategies and counter-strategies;
- cooperation and communication under appropriate relatedness and environmental conditions.

Many reported controllers had only a few dozen neurons. This supports beginning with a small network rather than assuming deep learning scale is necessary.

Such et al. showed that a simple genetic algorithm using additive Gaussian weight mutation could evolve networks with millions of parameters. Their algorithm used truncation selection, elitism, and explicit episode reward, so its selection mechanism is not appropriate for the primary simulation. Its relevant engineering lessons are narrower:

- direct weight evolution can scale beyond tiny networks;
- forward-only evaluation parallelizes well;
- deterministic mutation seeds can compactly represent long lineages;
- crossover is not required for successful weight evolution.

### Fit to this repository

Fixed topology is attractive because it provides:

- constant-time, branch-light inference;
- fixed storage per controller;
- deterministic genome schemas;
- simple developmental sampling;
- straightforward mutation and replay;
- direct comparison with the current linear controller.

Its main scientific limitation is a fixed ceiling on controller complexity. A fixed maximum recurrent core with evolvable expression can soften that limitation while retaining predictable execution.

## 4. Topology evolution: NEAT, rtNEAT, and odNEAT

### 4.1 NEAT

NEAT evolves weights and topology while starting from minimal networks. Its defining mechanisms are:

1. historical innovation identifiers to align genes during crossover;
2. speciation and fitness sharing to protect structural innovations;
3. incremental complexification from minimal structure.

The original paper's ablations found the mechanisms work together. NEAT directly addresses the competing-conventions problem: two networks can implement similar functions while assigning hidden functions to different neuron identities, making naive crossover destructive.

### 4.2 rtNEAT

rtNEAT adapts NEAT to continual real-time replacement rather than synchronized generations. It is relevant to asynchronous worlds, but it still uses explicit performance-based replacement and centralized population/species management.

### 4.3 odNEAT

odNEAT decentralizes online topology and weight evolution. It was demonstrated on aggregation, navigation/obstacle avoidance, and phototaxis, and approximately matched centralized rtNEAT in those settings. It maintains local evolutionary state and still relies on algorithmic parent selection and controller replacement.

### 4.4 Why these are not the first implementation

Dynamic sparse graph networks introduce:

- variable inference cost;
- pointer/index traversal and unpredictable branches;
- variable genome and phenotype storage;
- innovation bookkeeping;
- topology-aware crossover;
- species protection machinery;
- a conflict between global innovation IDs and purely biological local reproduction;
- a confound between the new sensorimotor interface and topology evolution.

NEAT and odNEAT remain valuable later comparisons. The first experiment should establish whether richer observations and a small genetic controller can evolve useful behavior under the existing ecology.

## 5. Memory and recurrent controllers

Memory can mean several different mechanisms:

1. explicit observation/action history supplied as inputs;
2. recurrent neural state;
3. continuous-time/leaky neural dynamics;
4. synaptic plasticity that changes weights during life;
5. external/social memory stored in organism state.

The user's requirement is narrower: neural memory capacity should become functional through evolution rather than being switched on for every organism.

### 5.1 CTRNN and leaky-state precedent

Evolutionary robotics frequently uses recurrent networks and continuous-time recurrent neural networks (CTRNNs). A leaky unit has a time constant controlling how quickly its state follows new input. Larger time constants retain prior state longer. This provides smooth, dynamical memory suitable for embodied control.

A fixed maximum recurrent network can still evolve memory if recurrence and retention are controlled by heritable expression parameters. If initialized at zero expression, the realized controller behaves feed-forward. Mutation can gradually increase:

- retained-state fraction;
- recurrent contribution;
- per-unit or whole-controller memory expression;
- effective time constant.

This is bounded topology expression rather than unrestricted topology evolution. It retains a fixed memory layout and predictable inference cost while allowing the phenotype to begin functionally memoryless.

### 5.2 Developmental sampling

The current genetic model represents loci as distributions. The recurrent weights, expression gates, and time constants can follow the same rule:

- genome stores centers and spreads;
- inheritance recombines distributions;
- mutation changes distributions;
- one phenotype is sampled at birth;
- recurrent runtime state begins at a defined neutral state.

Siblings can therefore inherit the same genome but realize different neural dynamics.

### 5.3 Lifetime plasticity is a different experiment

Polyworld encoded neural architecture, connection density, topology, and Hebbian learning rates in the genome. Its agents had low-level move, turn, eat, mate, attack, light, and focus behavior. Natural-selection runs exhibited driven increases in neural-dynamics complexity and learning rates under some conditions, followed by stable plateaus or later transitions.

This is evidence that ecological selection can act on neural complexity and plasticity. It also warns that complexity does not increase monotonically and should not be optimized directly: Polyworld experiments that explicitly selected neural complexity produced stereotyped spinning rather than ecologically valuable behavior.

Plastic synapses introduce a second adaptation process and a Baldwin/Lamarckian question. They should follow the recurrent-memory baseline, not be conflated with it.

## 6. Mutation operators

### 6.1 Independent Gaussian mutation

For a small network, additive Gaussian perturbation remains the clearest baseline. The existing inherited mutation-rate and mutation-magnitude traits can control:

- probability that a locus mutates;
- perturbation scale;
- mutation of developmental spread;
- mutation of memory-expression genes.

A bounded activation and bounded or transformed weight domain prevent runaway values.

### 6.2 Self-adaptation

The simulator already evolves mutation rate and magnitude. This resembles self-adaptive evolutionary strategies but occurs through ordinary organism inheritance rather than an external optimizer.

A lower mutation floor is scientifically useful because completely disabling variation can create absorbing lineages. Upper bounds prevent developmental collapse.

### 6.3 Safe mutations

Lehman et al. observed that random perturbation becomes destructive in deep or recurrent networks because parameters have very different output sensitivities. They proposed:

- **SM-R:** line-search rescaling until sampled network outputs change by a target amount;
- **SM-G:** divide perturbations by output sensitivity obtained from output gradients.

These operators do not require reward gradients or additional environmental rollouts, but they do require stored representative observations and extra neural evaluation/backpropagation.

For a very small first network, this machinery is likely unnecessary. It becomes relevant if recurrent mutation frequently destroys viable behavior or the controller grows substantially.

A reward-free, lightweight alternative suitable for later testing is behavioral mutation normalization:

1. retain a bounded sample of a parent's recent observations;
2. propose an ordinary mutation;
3. compare parent and child logits on those observations;
4. rescale the perturbation to a target output divergence.

That is inspired by SM-R and preserves endogenous selection because it changes only the mutation distribution, not who reproduces.

## 7. Sexual inheritance and the competing-conventions problem

The current scalar policy genes are blended coordinate by coordinate. Hidden neural networks make that dangerous.

Hidden units are exchangeable: swapping two hidden units and the corresponding outgoing columns leaves network behavior unchanged. Two compatible parents may therefore encode similar behavior with different hidden-unit assignments. Arithmetic averaging or uniform per-weight crossover can combine incompatible internal representations.

Relevant approaches include:

- NEAT historical markings;
- neuron/graph alignment before crossover;
- inheriting coherent modules;
- choosing an entire controller from one parent and mutating it;
- asexual controller inheritance while other genome modules recombine.

Both Deep GA and the Safe Mutations experiments omitted crossover, demonstrating that weight mutation alone is a valid baseline.

For the first fixed-topology treatment, whole-controller inheritance from one contributing parent is the safest scientific control. A later ablation can compare coherent neuron-level crossover or activation-based alignment.

## 8. Novelty search and quality diversity

Novelty search rewards behavioral difference rather than task performance. Novelty is commonly computed as distance to nearest behaviors in the current population and an archive.

MAP-Elites discretizes a user-selected behavior space and stores the highest-quality individual found in each bin. Novelty Search with Local Competition and MAP-Elites are quality-diversity algorithms: they preserve behavioral diversity while improving quality within niches.

These approaches can overcome deceptive objectives and generate behavioral repertoires. However, they require:

- an externally maintained behavior archive or map;
- experimenter-chosen behavior descriptors;
- algorithmic selection or replacement;
- often a global quality measure.

Those requirements violate the primary simulation's endogenous-selection constraint. QD remains useful as:

- an offline analysis lens;
- a separate controlled search experiment;
- a diagnostic for whether ecological diversity collapses;
- a source of behavior descriptors for reporting, never reproduction.

The literature also warns that behavior descriptors can be misaligned with quality. An archive can become full of diverse but poor behaviors, and genetic diversity does not guarantee behavioral diversity.

## 9. Evolution strategies and CMA-ES

### 9.1 OpenAI-style evolution strategies

OpenAI-style ES estimates a gradient of expected reward by evaluating many parameter perturbations. It is highly parallel and communicates compact noise seeds, but it requires a shared explicit reward and synchronized optimization distribution.

It is unsuitable for ecological inheritance in the primary simulation. It may later benchmark how learnable a fixed sensorimotor interface is under an external objective.

### 9.2 CMA-ES

CMA-ES adapts a multivariate Gaussian search distribution, including covariance between parameters. It is robust for non-differentiable black-box optimization and has useful invariance properties.

A full covariance matrix for `n` parameters stores `O(n²)` values and performs matrix updates/decompositions. This is reasonable for a centralized optimizer over a few hundred parameters, but not as per-organism ecological machinery.

Again, it is a possible external control arm, not the primary evolution law.

## 10. Sensorimotor interface findings

The literature consistently joins sensor design, morphology, and controller evolution. Agents exploit whatever information and affordances the interface exposes.

### 10.1 Directional observations

Examples in evolutionary robotics commonly use egocentric range or directional sensors. Polyworld supplied rendered first-person pixels; simpler robots used small directional distance-sensor arrays. Even fewer than 15 neurons supported cooperation in some environments.

For this grid world, a bounded directional interface is more appropriate than pixels:

- adjacent occupancy/passability by direction;
- food value and distance/gradient by direction;
- heat gradient by direction;
- prey/threat/mate signals by direction;
- explicit unknown/visibility masks;
- internal physiology and readiness.

Direction can be represented in world coordinates or relative to organism facing. Egocentric coordinates make turning and orientation meaningful; world coordinates are easier but can introduce a privileged global frame.

### 10.2 Lower-level actions

The existing specification's `ActionIntent` model is a strong target. The network should score bounded candidates such as:

- wait;
- move to one of at most eight adjacent cells;
- ingest at the current location;
- attack a contact candidate;
- absorb heat;
- detoxify;
- reproduce with a contact candidate;
- relationship/social candidates;
- magic candidates.

The network should choose an intent, but intent validation and matter/energy transactions must remain authoritative simulation rules.

This removes automatic long-range navigation without asking the neural controller to violate conservation or reason over unbounded entity lists.

### 10.3 Bootstrap risk

Moving from macros to motor-level actions makes survival harder. If all founders are uniformly random, the population may go extinct before viable sensorimotor loops evolve.

Published systems commonly use one or more of:

- minimal useful sensor–motor priors;
- simple starting structures that complexify;
- large populations;
- environments with a gentle viability envelope;
- hand-seeded but non-viable biases that evolution must improve.

Polyworld, for example, seeded tendencies to approach food-associated green and avoid aggression-associated red, while seed organisms still could not sustain the population without evolution.

A scientifically honest bootstrap should be declared, versioned, and tested against a random-controller control. It must not rank or directly reproduce organisms.

## 11. Metabolic cost of intelligence

Neural tissue and signaling are energetically expensive in biology. Attwell and Laughlin's energy budget attributes substantial neural energy to action potentials and synaptic signaling.

Polyworld explicitly charged energy for agent behavior including neural activity. Its analysis notes that complexity should be selected downward when neural cost exceeds ecological value.

If controller complexity and memory are free in this simulation, inactive or unnecessarily recurrent circuitry can drift without ecological consequence. If the goal is for memory to evolve only where useful, expressed cognition needs an in-world cost.

A possible model class—not yet a design decision—is:

- a small unavoidable base decision cost;
- incremental cost for sensed cells, already partly implemented;
- incremental cost for expressed hidden/recurrent computation;
- all chemical cost transferred to environmental heat;
- cost based on expressed phenotype, not wall-clock implementation details.

The coefficient must be configurable and tested in zero-cost, low-cost, and stress controls. Charging literal CPU operations would make implementation choices part of the physics; charging a declared biological expression cost avoids that mistake.

## 12. High-performance Rust implications

### 12.1 Workload shape

Every organism has different weights, so inference is many tiny independent matrix-vector operations—not one large shared matrix multiplication. BLAS and general tensor frameworks often lose on dispatch, shape handling, and allocation at this scale.

The current profile shows perception/decision dominates late runs, so controller arithmetic must not add allocations or dynamic graph traversal.

### 12.2 Likely representation

For a fixed small controller, the performance-oriented baseline should evaluate:

- contiguous `f32` arrays for neural weights and state;
- compile-time dimensions where practical;
- row-major output-neuron weight layout;
- stack or reusable fixed scratch arrays;
- no allocation in inference;
- no Python callback;
- immutable cold controller phenotype shared separately from hot organism state;
- a fixed-size recurrent-state array in the dense living arena.

Matter and energy accounting remains `i64`/`f64`; using `f32` for a neural phenotype does not weaken conservation.

### 12.3 Libraries surveyed

- `burn` and `candle`: capable ML frameworks, likely excessive for tiny heterogeneous networks.
- `nalgebra`: mature and supports static matrices; worth benchmarking against manual loops.
- `ndarray`/`matrixmultiply`: excellent general matrix kernels; likely better for larger batches than individual tiny heterogeneous networks.
- `wide`: explicit portable vector types; useful only if a benchmark shows autovectorization is insufficient.
- `rayon`: useful once the simulator has read-only observation/intent generation phases; unsafe to bolt onto the current mutable same-tick scheduler without changing semantics.
- `genevo`: generic GA framework; its centralized optimization loop does not match ecological reproduction.
- `radiate`: actively developed evolutionary framework with NEAT, novelty, speciation, and parallelism; useful reference or later external arm, but unnecessary for direct endogenous inheritance.
- Rust NEAT crates (`neat`, `oxineat`, `rustneat`): useful implementation references with varying maturity; adopting one would import a different evolutionary lifecycle and dynamic representation.

A custom fixed controller integrated with the existing genome is likely smaller, faster, and scientifically clearer than adopting a training framework.

### 12.4 Parallelism boundary

Pure neural inference is easy to parallelize, but current observation and action code mutates shared world state and consumes one ordered RNG stream. The existing scaling analysis already concludes that 100k+ rich agents require a versioned read-observe/intent/resolve/commit law.

The controller should therefore be designed as a pure function over:

- immutable observation/candidate data;
- immutable phenotype weights;
- previous per-organism neural state;
- a supplied deterministic random draw.

That makes it ready for future deterministic parallel intent generation without changing the first serial implementation.

## 13. Experimental methodology

No scalar intelligence fitness should be introduced. Evidence must come from ecological consequences and controlled comparisons.

### Required treatments

At minimum:

1. current linear macro controller;
2. current linear controller on the richer lower-level intent interface, if feasible;
3. fixed hidden controller without functional memory;
4. fixed maximum recurrent controller with evolvable memory expression;
5. neutral-selection or inheritance controls where practical.

### Measurements, not selection criteria

Possible post-hoc measurements include:

- population persistence and generational turnover;
- lifetime offspring distribution;
- resource acquisition and energy efficiency;
- predator/prey and diet specialization;
- action and trajectory diversity;
- niche occupancy by phenotype and behavior;
- memory-expression distributions over lineages and time;
- recurrent-state mutual information with prior observations;
- lesion tests that zero recurrent state after a run;
- counterfactual replay of sampled agents with memory disabled;
- brain expression cost versus reproductive success;
- lineage persistence and speciation;
- neural activity complexity, with the Polyworld warning that it is an observable, not an objective.

### Controls and replication

Evolutionary robotics methodology emphasizes:

- preregistered hypotheses and success/failure criteria;
- multiple seeds;
- controls that rule out drift and population-size effects;
- fixed run budgets;
- conservation and determinism audits;
- reporting negative results and extinctions;
- no post-hoc parameter tuning on the same seeds used for claims.

A result in one run establishes possibility, not prevalence.

## 14. Research conclusions

1. The simulator already has a genetic linear neural policy; the next scientific step is a richer sensorimotor boundary, not merely adding a hidden layer.
2. The primary model is best understood as embodied evolution, not offline neuroevolutionary optimization.
3. A fixed small controller is the cleanest first treatment for performance and causal attribution.
4. Memory can emerge within fixed maximum capacity through evolvable recurrent expression and retention, keeping runtime bounded.
5. Developmental sampling naturally extends to neural and memory genes.
6. Naive hidden-weight crossover is unsafe; mutation-only or coherent whole-controller inheritance is the correct baseline.
7. NEAT/odNEAT, novelty/QD, ES, CMA-ES, safe mutation, and lifetime plasticity are valuable later comparisons but should not be mixed into the first endogenous model.
8. Expressed neural complexity likely needs an ecological energy cost if memory is to be selected rather than drift freely.
9. Tiny heterogeneous inference favors fixed arrays and allocation-free custom Rust over a general ML framework, subject to benchmarks.
10. The implementation must retain the linear controller and old observation/action law as controls and version the new dynamics explicitly.

## 15. Key references

### Foundations and surveys

- Yao, X. (1999). *Evolving Artificial Neural Networks*. Proceedings of the IEEE 87(9). DOI: `10.1109/5.784219`.
- Stanley, K. O., Clune, J., Lehman, J., & Miikkulainen, R. (2019). *Designing neural networks through neuroevolution*. Nature Machine Intelligence. DOI: `10.1038/s42256-018-0006-z`.
- Doncieux, S., Bredèche, N., Mouret, J.-B., & Eiben, A. E. (2015). *Evolutionary Robotics: What, Why, and Where to*. DOI: `10.3389/frobt.2015.00004`.
- Bredèche, N., Haasdijk, E., & Prieto, A. (2018). *Embodied Evolution in Collective Robotics: A Review*. DOI: `10.3389/frobt.2018.00012`.
- Floreano, D., & Keller, L. (2010). *Evolution of Adaptive Behaviour in Robots by Means of Darwinian Selection*. DOI: `10.1371/journal.pbio.1000292`.

### Topology and online evolution

- Stanley, K. O., & Miikkulainen, R. (2002). *Evolving Neural Networks through Augmenting Topologies*. DOI: `10.1162/106365602320169811`.
- Stanley, K. O., Bryant, B. D., & Miikkulainen, R. (2005). *Real-Time Neuroevolution in the NERO Video Game*. DOI: `10.1109/TEVC.2005.856210`.
- Silva, F., Urbano, P., Correia, L., & Christensen, A. L. (2015). *odNEAT: An Algorithm for Decentralised Online Evolution of Robotic Controllers*. DOI: `10.1162/EVCO_a_00141`.
- Gauci, J., & Stanley, K. O. (2007). *Generating large-scale neural networks through discovering geometric regularities*. DOI: `10.1145/1276958.1277158`.

### Fixed weights, mutation, and optimization controls

- Such, F. P. et al. (2017). *Deep Neuroevolution: Genetic Algorithms Are a Competitive Alternative for Training Deep Neural Networks for Reinforcement Learning*. arXiv:`1712.06567`.
- Lehman, J., Chen, J., Clune, J., & Stanley, K. O. (2018). *Safe mutations for deep and recurrent neural networks through output gradients*. DOI: `10.1145/3205455.3205473`.
- Salimans, T. et al. (2017). *Evolution Strategies as a Scalable Alternative to Reinforcement Learning*. arXiv:`1703.03864`.
- Hansen, N. (2016). *The CMA Evolution Strategy: A Tutorial*. arXiv:`1604.00772`.

### Divergence and quality diversity

- Lehman, J., & Stanley, K. O. (2011). *Abandoning Objectives: Evolution Through the Search for Novelty Alone*. DOI: `10.1162/EVCO_a_00025`.
- Mouret, J.-B., & Clune, J. (2015). *Illuminating search spaces by mapping elites*. arXiv:`1504.04909`.
- Pugh, J. K., Soros, L. B., & Stanley, K. O. (2016). *Quality Diversity: A New Frontier for Evolutionary Computation*. DOI: `10.3389/frobt.2016.00040`.

### Memory, plasticity, and ecological neural complexity

- Beer, R. D. (1995). *On the dynamics of small continuous-time recurrent neural networks*. Adaptive Behavior 3(4). DOI: `10.1177/105971239500300405`.
- Risi, S., Hughes, C. E., & Stanley, K. O. (2010). *Evolving plastic neural networks with novelty search*. DOI: `10.1177/1059712310379923`.
- Miconi, T., Clune, J., & Stanley, K. O. (2018). *Differentiable plasticity: training plastic neural networks with backpropagation*. arXiv:`1804.02464`.
- Yaeger, L., Griffith, V., & Sporns, O. (2011). *Passive and Driven Trends in the Evolution of Complexity*. arXiv:`1112.4906`.
- Yaeger, L. (1994/1997). *Computational Genetics, Physiology, Metabolism, Neural Systems, Learning, Vision, and Behavior or PolyWorld: Life in a New Context*.
- Hinton, G. E., & Nowlan, S. J. (1987). *How Learning Can Guide Evolution*. Complex Systems 1.

### Neural energy

- Attwell, D., & Laughlin, S. B. (2001). *An Energy Budget for Signaling in the Grey Matter of the Brain*. DOI: `10.1097/00004647-200110000-00001`.
