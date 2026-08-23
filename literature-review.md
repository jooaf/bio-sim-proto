# Substrate-Based Evolution Simulators — Literature Map

What's been tried, what worked, what reliably fails, and where the open ground is.

Your design has three separable decisions. The literature treats them as three separate research communities, and most projects fail because they pick a good answer to one and a bad answer to the other two.

1. **Substrate** — what "matter" is made of, and how it composes into higher structures.
2. **Environmental signals** — what the world imposes, and what the tunable knobs are.
3. **The information-theoretic layer** — whether it *measures* diversity or *causes* it. These are very different systems.

---

## Part 1 — Substrate families

There are roughly five, and they trade off along one axis: **how easy is it to get replication started** vs. **how much room is left above replication for anything interesting to happen.**

### 1a. Algorithmic / program-soup chemistries

Matter = strings of instructions. Reactions = one program executing on another. No spatial physics at all.

| Paper | What it showed |
|---|---|
| [Computational Life: How Well-formed, Self-replicating Programs Emerge from Simple Interaction](https://arxiv.org/abs/2406.19108) (Agüera y Arcas et al., 2024) | Random Brainfuck-variant programs in a soup, no fitness function, no noise — self-replicators emerge in ~40% of runs within 16k epochs. Also replicated in Forth, Z80, and 8080 instruction sets. This is the single most important recent result for you: replication is *cheap* if your substrate lets programs read and write each other. |
| [Combinatory Chemistry](https://arxiv.org/abs/2003.07916) (Kruszewski & Mikolov, ALIFE 2020) | Combinatory logic as the chemistry, with **conservation laws** on atom counts. From tabula rasa: autopoietic structures, recursive growth patterns, and self-reproducers. The conservation law is doing enormous work here — it's what turns "anything can grow" into an economy. |
| [Stringmol](https://alife.org/encyclopedia/artificial-chemistry/stringmol/) / [Innovation, Variation, and Emergence in an Automata Chemistry](https://direct.mit.edu/isal/proceedings/isal2020/32/753/98477) (Hickinbotham & Stepney) | Seeded with a hand-built replicator; parasites appear almost immediately, replicators shrink, then evolve *anti-parasite* mechanisms. Best-documented example of an evolutionary arms race in an artificial chemistry. |
| [Chemlambda](https://arxiv.org/pdf/2007.10288) (Buliga) | Molecules = graphs; reactions = local graph rewrites, asynchronous and random. Turing-universal. Interesting to you because the substrate is *topological*, not sequential — structure has shape. |
| [Tierra / Avida](https://alife.org/encyclopedia/digital-evolution/avida/) | The classical ancestors. Worth reading for what they *didn't* get: both plateau. Complexity stops growing. Understanding why is more useful than understanding how they work. |

**Verdict:** fastest path to a working prototype, and the 2024 result de-risks it. The known failure mode is that the ceiling is low — you get replicators and parasites, then not much else, because there is no spatial or energetic structure for cells and multicellularity to be *about*.

### 1b. Spatial particle / reaction-diffusion chemistries

Matter = typed particles in 2D/3D space with bonding rules. This is the family where membranes and cells appear, because "inside vs. outside" is a real thing.

| Paper | What it showed |
|---|---|
| [Ono & Ikegami, artificial chemistry protocells](https://link.springer.com/content/pdf/10.1007/3-540-44811-X_20.pdf) and [Computational studies on conditions of the emergence of autopoietic protocells](https://www.sciencedirect.com/science/article/abs/pii/S030326470500050X) | Membrane / catalyst / resource / waste / water particles diffusing on a lattice. Self-maintaining, self-reproducing protocells emerge from a *random* start, and more stable cells are then selected for. The cleanest existing demonstration of "cells emerge from matter, unprompted." |
| [Squirm3 / Evolvable Self-Replicating Molecules in an Artificial Chemistry](https://direct.mit.edu/artl/article/8/4/341/2413/Evolvable-Self-Replicating-Molecules-in-an) (Hutton, 2002) | Template-based replication in a spatial soup — a DNA analogue that emerges spontaneously. Mutated copies can outcompete parents. Simple enough to reimplement in a weekend. |
| [Cellular Evolution in a 3D Lattice Artificial Chemistry](https://www.researchgate.net/publication/37811108_Cellular_Evolution_in_a_3D_Lattice_Artificial_Chemistry) | The 3D extension. Mostly a warning about compute cost. |

**Verdict:** this is where your "building blocks of matter" instinct actually pays off. The cost is that you must hand-design a reaction table, and the design of that table quietly determines everything downstream.

### 1c. Continuous CA / field substrates

Matter = continuous density fields updated by convolution kernels. No discrete particles, no discrete organisms — individuality is itself emergent.

| Paper | What it showed |
|---|---|
| [Lenia: Mathematical Foundations of Continuous Cellular Automata](https://arxiv.org/pdf/1812.05433) and [Lenia and Expanded Universe](https://arxiv.org/pdf/2005.03742) (Chan) | 400+ distinct self-organizing "species." Multi-channel Lenia produces individuality, self-replication, growth by ingestion, and "virtual eukaryotes" with internal division of labor. |
| [Flow-Lenia](https://arxiv.org/abs/2212.07906) (Plantec et al., ALIFE 2023) | The key upgrade: **mass conservation** plus **parameter localization** — each patch of matter carries its own update-rule parameters, which flow and mix with neighbours. This means different "species" can coexist in one world and their rules can recombine. Effectively makes the physics itself the genome. |
| [Flow-Lenia: Emergent evolutionary dynamics in mass conservative continuous CA](https://arxiv.org/pdf/2506.08569) (2025 follow-up) | Intrinsic evolutionary dynamics without an external selection loop. |
| [Particle Lenia perturbation-response analysis](https://arxiv.org/pdf/2305.16706) | Particle formulation — cheaper, and easier to attach per-organism logging to, which matters for your data framework. |

**Verdict:** the most *unconventional* option and the closest fit to "unusual medium with emergent properties." Flow-Lenia in particular is probably the single most relevant paper in this whole document for what you described. Downside: identifying discrete "organisms" for per-organism logging is a segmentation problem you'd have to solve yourself.

### 1d. Morphogenetic / neural substrates

Matter = cells running a shared learned update rule, differentiated by local state.

| Paper | What it showed |
|---|---|
| [Growing Neural Cellular Automata](https://distill.pub/2020/growing-ca/) (Mordvintsev et al., 2020) | Single seed cell grows into a target organism, with regeneration. Establishes that a local learned rule can encode a global body plan. |
| [Biomaker CA](https://arxiv.org/abs/2307.09320) (Randazzo & Mordvintsev, 2023) | Explicitly the thing you're describing: nutrient-starved environment, seeds must grow into plant-like organisms, survive, and reproduce with variation to sustain a biome. JAX/GPU. Open source. Includes environmental harshness as a tunable. |
| [Simulating an Artificial Biome of Plants with Biomaker CA](https://direct.mit.edu/isal/proceedings/isal2024/36/120/123522) (2024) | Follow-up with biome-level dynamics. |
| [Neural Cellular Automata Can Respond to Signals](https://arxiv.org/pdf/2305.12971) (Stovold) | Directly relevant to "environment imposes signals": NCAs can be trained/evolved to respond to external signal channels. |

**Verdict:** Biomaker CA is the closest existing codebase to your stated goal. Worth reading its limitations section carefully — it will tell you which of your ideas are already known to be hard.

### 1e. Self-replicating structures in discrete CA

| Paper | What it showed |
|---|---|
| [Self-Reproduction and Evolution in Cellular Automata: 25 Years After Evoloops](https://arxiv.org/pdf/2402.03961) (Sayama, 2024) | Retrospective on evoloops — first CA system with genuine Darwinian evolution of self-reproducers. The critical mechanism was **structural dissolution**: a rule that erases inactive debris. Without it the world clogs. This is a design lesson you will otherwise learn the hard way. |

---

## Part 2 — Environmental signals: what the world can impose

### Signals with evidence behind them

**Resource localization → multicellularity.** [In silico transitions to multicellularity](https://arxiv.org/pdf/1403.3217) (Duran-Nebreda et al.) and [Evolution of multicellularity by collective integration of spatial information](https://elifesciences.org/articles/56349) (Colizzi, Vroomans & Merks, eLife 2020). The eLife paper is the strongest: multicellularity evolves *because* a group of cells can integrate a spatial gradient that a single cell cannot resolve. The environmental signal is a gradient the organism is too small to read — a beautifully clean tunable.

**Environmental fluctuation → complexity and evolvability.** [Evolution takes multiple paths to evolvability when facing environmental change](https://www.pnas.org/doi/10.1073/pnas.2413930121) (PNAS 2024) — Avida populations under stable vs. cyclic vs. random environmental regimes over ~30k generations. Fluctuation rate is your knob; too fast gives noise, too slow gives stasis, and the interesting band is narrow.

**Energetic closure → self-organized nutrient cycles.** [Closed ecosystems extract energy through self-organized nutrient cycles](https://pmc.ncbi.nlm.nih.gov/articles/PMC10756307/) and [Energetic constraints shape the diversity of feasible ecological networks](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1014330). If matter is conserved and energy flows through, food webs and trophic levels become *forced* rather than designed. Strongly recommended: conserve mass, let energy in as a flux, require it to leave as waste heat.

**Niche construction → intrinsic drive for complexity.** [Niche Construction and the Evolution of Complexity](https://www.tim-taylor.com/paper-details/taylor2004niche.html) (Taylor, ALIFE IX) — organisms modifying their own environment produces an intrinsic drive toward more genes. [Dynamics of niche construction in adaptable populations evolving in diverse environments](https://direct.mit.edu/isal/proceedings/isal2023/35/63/116908) (ALIFE 2023) is the current version. This is the mechanism that keeps the environment from being a static backdrop, which is the standard reason these sims plateau.

**Minimal criterion instead of fitness.** [Identifying Necessary Conditions for Open-Ended Evolution through the Artificial Life World of Chromaria](https://pdfs.semanticscholar.org/4671/423a1b65f3e35dce603f8746e72ae31193dc.pdf) (Soros & Stanley, 2014). Four proposed necessary conditions, of which the load-bearing one for you is: **individuals must meet a minimal criterion to reproduce, and evolution must create novel opportunities to meet that criterion.** Plus [How the Strictness of the Minimal Criterion Impacts Open-Ended Evolution](https://www.uvm.edu/neurobotics/pubs/pdf/2016_SorosCheneyStanley_HowTheStrictnessOfTheMinimalCriterionImpactsOpenEndedEvolution_ALIFE.pdf) (2016), which sweeps the strictness parameter. Directly gives you a knob.

---

## Part 3 — The information-theoretic layer

Important distinction that will save you months: there are two entirely different things you might mean, and only one of them is compatible with "natural selection does the rest."

### Type A — Extrinsic: an outside optimizer rewards diversity

Novelty search, MAP-Elites, quality-diversity. [Quality Diversity: A New Frontier for Evolutionary Computation](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2016.00040/full) (Pugh, Soros & Stanley, 2016) is the canonical overview.

These work extremely well as *search algorithms* but they are not part of the world — an external process picks who reproduces. If you add MAP-Elites on top of your substrate, you no longer have an evolving world; you have an optimizer with a physics-flavoured genotype-phenotype map. That may be fine, but be deliberate about it.

Relevant middle ground: [Minimal Criterion Coevolution](http://www.cmap.polytechnique.fr/~nikolaus.hansen/proceedings/2017/GECCO/proceedings/proceedings_files/pap140s3-file1.pdf) (Brant & Stanley, GECCO 2017) — coevolving populations each gate the other's reproduction, so the "objective" is endogenous. And [Adaptive Exploration in Lenia with Intrinsic Multi-Objective Ranking](https://arxiv.org/pdf/2506.02990) (2025) applies this style of search directly to a Lenia substrate.

### Type B — Intrinsic: information-theoretic quantities are what organisms *do*

This is the more unconventional and, I think, more interesting fit for your framing.

**Empowerment** — channel capacity from an agent's actuators to its own future sensors. [Empowerment — An Introduction](https://arxiv.org/pdf/1310.1863) (Salge, Glackin & Polani), [Empowerment for continuous agent–environment systems](https://journals.sagepub.com/doi/10.1177/1059712310392389) (Jung, Polani & Stone), [Changing the Environment Based on Empowerment as Intrinsic Motivation](https://www.mdpi.com/1099-4300/16/5/2789) — the last one is niche construction expressed information-theoretically, which is exactly the bridge you'd want. [Process empowerment for robust intrinsic motivation](https://iopscience.iop.org/article/10.1088/2632-072X/adf2ec) (2025) is the current version.

**Predictive information / homeokinesis** — maximize mutual information between past and future states. Produces exploratory, self-maintaining behavior with no reward function.

**Assembly Theory** — [Assembly Theory Explains and Quantifies the Emergence of Selection and Evolution](https://arxiv.org/abs/2206.02279) (Sharma, Czégel, Lachmann, Kempes, Walker & Cronin). Assembly index = minimum steps to build an object from primitives; assembly = index combined with copy number. This is *made for* a substrate simulator — you have perfect construction histories, so you can compute assembly index exactly, which chemists cannot. **Read the criticism too:** [Assembly Theory Reduced to Shannon Entropy and Rendered Redundant by Naive Statistical Algorithms](https://arxiv.org/pdf/2408.15108) (Zenil et al.) argues it collapses to compression. The controversy is unresolved; treat AT as a well-defined observable rather than a theory you're committing to.

**Ecological diversity done properly** — [Entropy and diversity](https://nsojournals.onlinelibrary.wiley.com/doi/10.1111/j.2006.0030-1299.14714.x) (Jost, 2006) and [Entropy and Diversity: The Axiomatic Approach](https://arxiv.org/pdf/2012.02113) (Leinster). Use **Hill numbers** (effective number of species, parameterized by *q*), not raw Shannon entropy. Shannon entropy doesn't behave sensibly under community merging; Hill numbers do. For a logging framework this matters: record the abundance vector at every timestep and compute the whole *q*-profile offline, rather than committing to one index up front.

---

## Part 4 — Instrumentation (do this early, not late)

You said you want per-timestep data on all organisms and the environment. There are established metrics; using them means your results are comparable to published work instead of anecdotal.

- **[The MODES Toolbox: Measurements of Open-Ended Dynamics in Evolving Systems](https://direct.mit.edu/artl/article/25/1/50/2915/The-MODES-Toolbox-Measurements-of-Open-Ended)** (Dolson, Vostinar, Wiser & Ofria, *Artificial Life* 2019). Four metrics: change potential, novelty potential, complexity potential, ecological potential. Includes algorithms. Validated on NK landscapes and Avida. **Start here.** Also read [Assessing the ability of the MODES toolbox to detect open-endedness](https://direct.mit.edu/isal/proceedings-pdf/isal2024/36/10/2461111/isal_a_00721.pdf) (ALIFE 2024) for the caveats.
- **Evolutionary activity statistics** (Bedau & Packard) — how long components persist beyond neutral expectation. Underlies MODES.
- **[Open-Ended Evolution: Perspectives from the OEE Workshop in York](https://hal.science/hal-01371116v1/document)** (Taylor et al., *Artificial Life* 2016) and the [2024 OEE special issue editorial](https://dx.doi.org/10.1162/artl_e_00445). Read for the hallmark/mechanism distinction — hallmarks are what you measure, mechanisms are what you build.
- **[Automating the Search for Artificial Life with Foundation Models](https://arxiv.org/abs/2412.17799)** (Kumar, Lu, Kirsch, Tang, Stanley, Isola & Ha; [code](https://github.com/SakanaAI/asal)) — uses a vision-language model as the interestingness metric to search substrate parameter space. Works across Lenia, Boids, Particle Life, Game of Life, NCA. If you get a substrate with many tunable parameters, this is how you search it without hand-tuning forever.

**Concrete logging schema suggestion:** per timestep, record (a) full abundance vector over whatever your "type" abstraction is, (b) per-organism construction/lineage history — this is what lets you compute assembly index and evolutionary activity retroactively, (c) environmental field state at reduced resolution, (d) mass/energy ledger for conservation checks. Keep raw; compute all metrics offline. You will change your mind about the metrics and you don't want to re-run.

---

## Part 5 — Explorations worth doing, ranked by originality × tractability

**1. Flow-Lenia with an imposed environmental signal field.** Flow-Lenia already gives localized, mixable, mass-conserving rule parameters. Nobody has systematically added an exogenous, spatially structured, temporally cycling signal field that organisms must track. Combines [Flow-Lenia](https://arxiv.org/abs/2212.07906) + the fluctuation results from [PNAS 2024](https://www.pnas.org/doi/10.1073/pnas.2413930121). Highest novelty-per-unit-effort in this list.

**2. Assembly index as a live, in-world quantity.** Compute assembly index continuously over the whole population from exact construction histories and use it as an observable — or, more aggressively, let the *environment* respond to it (e.g. resource influx modulated by population assembly). This turns an information-theoretic measure into a genuine selection pressure without an external optimizer. As far as I can tell nobody has done AT as a closed feedback loop inside a simulator. [Sharma et al.](https://arxiv.org/abs/2206.02279), with [Zenil et al.](https://arxiv.org/pdf/2408.15108) as the check.

**3. Program-soup substrate + spatial structure + conservation.** [Computational Life](https://arxiv.org/abs/2406.19108) has no space and no conservation; [Combinatory Chemistry](https://arxiv.org/abs/2003.07916) has conservation but no space; [Ono & Ikegami](https://www.sciencedirect.com/science/article/abs/pii/S030326470500050X) have space but hand-designed reactions. The union — self-modifying programs on a lattice with conserved atom counts — is a real gap, and it's the configuration most likely to produce membranes *and* heredity in the same system.

**4. Empowerment maximization as the substrate-level dynamic.** Instead of organisms being selected for empowerment, make local empowerment estimation the *update rule* for matter. Speculative, possibly incoherent, but it's the most direct reading of "information-theoretic system that drives diversity." [Polani et al.](https://arxiv.org/pdf/1310.1863) for the machinery, [Changing the Environment Based on Empowerment](https://www.mdpi.com/1099-4300/16/5/2789) for the niche-construction connection.

**5. Minimal-criterion strictness as a tunable environmental signal.** Take [Soros & Stanley's](https://pdfs.semanticscholar.org/4671/423a1b65f3e35dce603f8746e72ae31193dc.pdf) minimal criterion but make it *spatially heterogeneous and time-varying* — different regions demand different things to reproduce, and the demands drift. Cheap to implement, directly tests whether their conditions hold in a substrate-based world rather than a hand-designed one.

**6. Spatial-information-integration pressure for multicellularity.** Reproduce the [eLife 2020](https://elifesciences.org/articles/56349) mechanism in a substrate world: impose gradients on a length scale larger than any single unit can sense. Multicellularity becomes an information-processing solution rather than a stickiness parameter. Well-grounded, lower novelty, but the most likely of these to actually produce the transition you want.

---

## Part 6 — Failure modes with names

- **The clog.** Debris accumulates and the world freezes. Sayama's fix was structural dissolution. Budget for a decay/dissolution mechanism from day one.
- **The plateau.** Tierra, Avida, and Stringmol all reach a complexity ceiling. Current best diagnosis: the environment is static, so once it's solved there's nothing left to do. Niche construction and coevolution are the standard antidotes.
- **The parasite collapse.** Stringmol gets parasites within minutes. Spatial structure is the classic stabilizer — parasites can't spread if dispersal is local.
- **The free-lunch replicator.** Without conservation, one lineage discovers unbounded growth and the run is over. Conservation laws are not optional; both Combinatory Chemistry and Flow-Lenia made them central for this reason.
- **Metric theatre.** It is very easy to build something that *looks* alive and measure nothing meaningful. MODES exists precisely to prevent this.

---

## Suggested reading order

1. [Computational Life](https://arxiv.org/abs/2406.19108) — 2024, readable, will calibrate your expectations about how cheap replication is
2. [Flow-Lenia](https://arxiv.org/abs/2212.07906) — the most relevant substrate design
3. [MODES Toolbox](https://direct.mit.edu/artl/article/25/1/50/2915/The-MODES-Toolbox-Measurements-of-Open-Ended) — design your logging around this before writing simulator code
4. [Biomaker CA](https://arxiv.org/abs/2307.09320) — closest working system to your description; read its limitations
5. [Soros & Stanley, Chromaria](https://pdfs.semanticscholar.org/4671/423a1b65f3e35dce603f8746e72ae31193dc.pdf) — the conditions framework
6. [Assembly Theory](https://arxiv.org/abs/2206.02279) + [the critique](https://arxiv.org/pdf/2408.15108) — your information-theoretic layer
7. [Evoloops at 25](https://arxiv.org/pdf/2402.03961) — hard-won design lessons
