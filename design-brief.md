# Program-Soup Substrate with Conservation Laws — Design Brief

Focused follow-up on: program-soup substrate, endogenous (non-optimizer) dynamics, conservation laws, with headroom above replication for individuality and computation.

---

## The core problem, stated precisely

Your instinct is right and the literature backs it: **replication is cheap, individuality is not.**

- [Pargellis' Amoeba](https://onlinelibrary.wiley.com/doi/abs/10.1002/cplx.10095) (1996–2003): random opcode sequences spontaneously produce replicators at ~10⁻⁴ probability. Then they get *shorter* and *simpler*, because short replicators copy faster.
- [Computational Life](https://arxiv.org/abs/2406.19108) (2024): same result across BFF, Forth, Z80, 8080.
- [Stringmol](https://direct.mit.edu/isal/proceedings/isal2020/32/753/98477): replicators appear, parasites appear, replicators shrink.
- [Evoloops at 25](https://arxiv.org/pdf/2402.03961) (Sayama): "the whole population gradually evolved toward the smallest ones."

**Every unconstrained program soup collapses toward the minimal replicator.** This is the single dominant failure mode of your chosen substrate family, and it is not subtle — it happens fast and it happens every time. Everything in this brief is, one way or another, about defeating it.

The good news: the mechanism that defeats it is exactly the mechanism you already wanted — conservation laws plus environmental signals. They aren't decoration on the design, they're the load-bearing wall.

---

## Part 1 — What conservation actually buys you, and how existing systems do it

Four distinct schemes exist. They are not interchangeable.

### Scheme A — Atom/symbol conservation (Combinatory Chemistry)

[Combinatory Chemistry](https://arxiv.org/abs/2003.07916) (Kruszewski & Mikolov, ALIFE 2020) is the reference implementation of what you're describing. Matter = combinatory logic expressions built from a small primitive set (S, K, I). **The total count of each primitive symbol in the world is fixed.** To grow, an expression must acquire primitives from the environment; to acquire them, something else must decompose.

From a tabula rasa state with no external intervention, this produces:

- autopoietic structures that maintain their own organization
- recursive structures growing as linear chains and binary-branching trees
- self-reproducers that double each generation
- and critically — **a process the authors describe as "remarkably similar to biological metabolisms"**: acquire constituents, decompose them, reassemble

That "metabolism" is the thing you don't get from unconserved soups. It's what gives organisms a *cost structure*, and a cost structure is what makes cooperation, specialization, and eventually multicellularity payable.

Follow-up worth reading: [Emergence of Self-Reproducing Metabolisms as Recursive Algorithms in an Artificial Chemistry](https://arxiv.org/pdf/2103.08245) (2021).

**Why this matters for you:** symbol conservation is trivially cheap to implement (a global counter per symbol type) and it immediately kills the "free lunch replicator" failure mode. Strong recommendation to include regardless of what else you pick.

### Scheme B — Space + memory as the conserved resource (Amoeba, Tierra, Avida)

[Amoeba](https://www.semanticscholar.org/paper/The-spontaneous-generation-of-digital-%E2%80%9CLife%E2%80%9D-Pargellis/e825dc5db262655a4d31e6db2410fe444e506b52) conserves two things: **computer memory and CPU time.** Organisms compete for both. This is enough to get emergence, and the opcode distribution self-organizes — the basis set becomes biased and short building blocks propagate through memory.

But it is *not* enough to prevent minimization, because both resources reward being small. Memory/CPU conservation alone produces a race to the bottom.

**Lesson:** conserve something that isn't monotonically better to have less of.

### Scheme C — Energy as a distinct conserved flux

[Closed ecosystems extract energy through self-organized nutrient cycles](https://pmc.ncbi.nlm.nih.gov/articles/PMC10756307/) and [Energetic constraints shape the diversity of feasible ecological networks](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1014330).

The key structural insight: **matter cycles, energy flows.** Matter is conserved and must be recycled; energy enters as a flux and must exit as waste. This asymmetry is what forces trophic levels into existence rather than requiring you to design them. If a program can only execute instructions by spending energy, and energy is only obtainable by decomposing structures that other programs built, you have a food web whether you wanted one or not.

This is the single highest-leverage addition to a program soup and, as far as I can find, nobody has combined it with an algorithmic chemistry. Program soups conserve *matter* (Combinatory Chemistry) or *space* (Amoeba) but not *energy as a separate flowing quantity*.

### Scheme D — Organizational closure as the invariant (Chemical Organization Theory)

[Chemical Organization Theory](https://arxiv.org/pdf/q-bio/0501016) (Dittrich & Speroni di Fenizio). An "organization" is a set of species that is algebraically **closed** (reactions among members produce only members) and stoichiometrically **self-maintaining** (production ≥ consumption for every member). Organizations form a lattice; the system's dynamics move between them.

This isn't a conservation law you impose — it's a formal definition of what counts as a persistent entity, derived from the reaction network. **For your purposes this is probably the right definition of "organism."** It solves the individuation problem — the thorny question of "what exactly am I logging per timestep?" — without you having to hand-wave a boundary.

Related: [Autocatalytic sets and chemical organizations](https://iopscience.iop.org/article/10.1088/1367-2630/aa9fcd), and [RAF theory](https://www.mdpi.com/2075-1729/8/4/62) (Hordijk & Steel) for detecting self-sustaining catalytic subsets algorithmically.

---

## Part 2 — Getting function and intelligence above replication

This is where the recent literature has moved, and it's directly on your question.

### The 2026 result you should read first

[Co-evolution of self-replication and function in a digital primordial soup](https://arxiv.org/abs/2607.09211). Random 32-byte Z80 assembly programs. The intervention is minimal and elegant: **correctly evaluating a polynomial raises a program's interaction probability above baseline.** That's it — no fitness function, no external selection loop, just a bias on interaction rate.

Findings:

- Self-replication and mathematical problem-solving **co-evolve from randomness**
- The pressure to compute *accelerates* the emergence of compact, robust reproductive architectures
- Programs evolve to **preserve memory for task execution** — i.e. they develop internal structure to protect their functional machinery from their replication machinery

That last point is the germ of germ-soma separation, appearing in a bare program soup. This is the closest thing in the literature to a proof that your "potentially intelligence" ambition isn't hopeless in this substrate.

The design pattern generalizes: **make the environmental signal modulate interaction probability, not fitness.** That keeps it organic — nothing outside the world decides who reproduces; some programs are simply more likely to bump into each other.

### Endogenous selection without a fitness function

[Prebiotic Functional Programs: Endogenous Selection in an Artificial Chemistry](https://arxiv.org/abs/2509.03534) (Vimal, Mathis, Weimer & Forrest, 2025). Steers AlChemy's dynamics using only features *endogenous* to the system — no external fitness function, no learning built into the dynamics — and synthesizes non-trivial lambda functions (Church addition, succession) from primitives.

This is the paper that most directly addresses your "it should happen organically" constraint. It's a worked example of how to bias a chemistry toward function without becoming an optimizer.

Background: [Self-Organization in Computation & Chemistry: Return to AlChemy](https://arxiv.org/abs/2408.12137) (Mathis, Fontana et al., 2024) — modern re-analysis of the original Fontana & Buss lambda-calculus chemistry with real compute. Finds complex stable organizations emerge *more* often than expected and resist collapse to trivial fixed points. [Code here.](https://github.com/mathis-group/AlChemy)

### Genome architecture that can actually host intelligence

If you want anything above reflex, the genome representation has to support modularity and signal-response. Raw linear instruction strings are poor at this.

[SignalGP](https://arxiv.org/abs/1804.05445) (Lalejini & Ofria, 2018): genomes organized into **modules with evolvable tags**. Environmental signals and inter-program messages trigger the module whose tag best matches. This is event-driven genetic programming and it maps exactly onto your "environment imposes signals" requirement — signals aren't sensed by polling, they *interrupt*.

[SignalGP-Lite](https://arxiv.org/abs/2108.00382) is the performance-oriented version (8–30x speedup), built for large-scale ALife.

Also relevant: [Tag-based Genetic Regulation for Genetic Programming](https://lalejini.com/Tag-based-Genetic-Regulation-for-LinearGP/) — adds gene regulation, which is the mechanism cells use for differentiation.

---

## Part 3 — Getting multicellularity, organically

The best existing system here is worth studying closely because its environmental design is the whole trick.

### DISHTINY

[Toward Open-Ended Fraternal Transitions in Individuality](https://direct.mit.edu/artl/article/25/2/117/2929/Toward-Open-Ended-Fraternal-Transitions-in) (Moreno & Ofria, *Artificial Life* 2019). [Code.](https://github.com/mmore500/dishtiny)

Design: self-replicating cells on a 2D toroidal grid harvesting **spatiotemporally fluctuating resources**. Cells that coordinate in space and time maximize harvest rate, which is directly tied to reproduction. Critically, the mechanism is designed to **keep scaling to subsequent transitions** — groups can themselves become units that group.

[Exploring Evolved Multicellular Life Histories in an Open-Ended Digital Evolution System](https://arxiv.org/pdf/2104.10081) (2021) reports what evolved when DISHTINY used SignalGP genomes: reproductive division of labor, resource sharing, cell–cell messaging, morphological patterning, gene-regulation-mediated life cycles, and **adaptive apoptosis**. All emergent.

**The transferable insight:** the environmental signal was a resource distribution that fluctuates on a scale — spatial and temporal — that a single cell cannot exploit alone. That's the same principle as the [eLife multicellularity paper](https://elifesciences.org/articles/56349) (gradients too large for one cell to read). Both say: *make the environment legible only at a scale above the individual.* That is your knob.

### Division of labor without kin selection tricks

[Task-switching costs promote the evolution of division of labor and shifts in individuality](https://www.pnas.org/doi/abs/10.1073/pnas.1202233109) (Goldsby, Knoester, Ofria & Kerr, PNAS 2012). Impose a **time cost on switching between tasks**. Genetically identical organisms evolve to specialize and share results via messages. Ofria's summary: they "started expecting each other to be there," and in isolation could no longer self-replicate — obligate multicellularity, arrived at without ever selecting for it.

This is a beautifully cheap intervention: one parameter (switching cost), no group-level selection, and you get a transition in individuality.

[The Evolutionary Origin of Somatic Cells under the Dirty Work Hypothesis](https://journals.plos.org/plosbiology/article?id=10.1371%2Fjournal.pbio.1001858) — germ-soma separation emerges when useful metabolic work has mutagenic side effects. Another one-parameter intervention with a large structural payoff.

[Division of labor promotes the entrenchment of multicellularity](https://www.biorxiv.org/content/10.1101/2023.03.15.532780.full.pdf) (2023) — why transitions become irreversible.

### Spatial substrate design

[The Movable Feast Machine](https://movablefeastmachine.org/) and [Pursue Robust Indefinite Scalability](https://www.usenix.org/legacy/event/hotos11/tech/final_files/Ackley.pdf) (Ackley, HotOS 2011). Architecture where processing, memory and communication attach to **movable bit patterns rather than fixed locations**, with purely relative spatial addressing and no global clock or global namespace.

Relevant to you for two reasons: (1) it's the most seriously-thought-through spatial substrate for indefinitely scalable computation, and (2) relative-only addressing forces genuinely local physics, which is what makes emergent boundaries meaningful. Moreno's [Practical Steps Toward Indefinite Scalability](https://mmore500.com/2020/06/23/practical-scalability.html) connects it to the OEE literature.

---

## Part 4 — A concrete substrate proposal

Synthesizing the above into one design. Every component is doing a specific job against a specific known failure mode.

**Matter.** Programs as sequences over a small opcode set, or combinator expressions. Combinators are more elegant and have the conservation story built in ([Combinatory Chemistry](https://arxiv.org/abs/2003.07916)); raw opcodes are easier to reason about and better validated ([Computational Life](https://arxiv.org/abs/2406.19108), [Amoeba](https://onlinelibrary.wiley.com/doi/abs/10.1002/cplx.10095)).

**Space.** 2D lattice, local interaction only, relative addressing, no global coordinates. Purpose: gives membranes/boundaries something to *be*, and locally contains parasites.

**Conservation — three separate ledgers.**

| Quantity | Behaviour | Job it does |
|---|---|---|
| Symbols/atoms | Strictly conserved, global count fixed per type | Kills free-lunch growth; forces metabolism (decompose to build) |
| Energy | Enters as spatial flux, spent per instruction executed, exits as unusable waste | Forces trophic structure and food webs; makes computation costly, so intelligence must pay for itself |
| Space | Finite, with active dissolution of inert structures | Prevents the clog (Sayama's structural dissolution) |

The energy ledger is the piece missing from the existing literature and the one most likely to generate something new.

**Environmental signals — all as interaction-probability modulators, never as fitness.**

- Energy influx field, spatially and temporally structured, on a **correlation length larger than a single organism** (this is the DISHTINY / eLife multicellularity lever)
- A signal channel organisms can read via tag-matched event handlers (the SignalGP mechanism) and, importantly, can also *write to* — which gives you niche construction for free
- Task-relevant structure: e.g. programs that correctly transform a signal pattern get elevated interaction probability, per the [2026 Z80 result](https://arxiv.org/abs/2607.09211)
- Optional: task-switching cost, the [Goldsby PNAS](https://www.pnas.org/doi/abs/10.1073/pnas.1202233109) lever for division of labor

**Individuation.** Don't hard-code "organism." Define it via [Chemical Organization Theory](https://arxiv.org/pdf/q-bio/0501016) — closed, self-maintaining sets — computed from the interaction graph. Then multicellularity isn't a special case you built; it's what it looks like when organizations nest.

**Diversity, organically.** No MAP-Elites, no novelty archive. Diversity should come from: conserved resources creating competition for *different* niches, spatially structured energy creating heterogeneous local environments, and niche construction making the environment a moving target. Measure it with [Hill numbers](https://nsojournals.onlinelibrary.wiley.com/doi/10.1111/j.2006.0030-1299.14714.x), don't cause it.

---

## Part 5 — Minimum viable prototype and what to check at each stage

Ordered so each stage fails fast and cheap.

**Stage 0 — bare soup.** Random programs, self-modification, no space, no conservation. *Expect:* replicators within ~10⁴ epochs. *Purpose:* validate your instruction set can support replication at all. If this fails your opcode set is wrong. Reference: [Computational Life](https://arxiv.org/abs/2406.19108).

**Stage 1 — add symbol conservation.** *Expect:* replicators still appear but growth saturates; decomposition behaviours appear. *Check:* does anything resembling metabolism show up? Reference: [Combinatory Chemistry](https://arxiv.org/abs/2003.07916).

**Stage 2 — add space + dissolution.** *Expect:* spatial patterning, local parasite containment, no clogging. *Check:* run 10x longer than Stage 1 without the world freezing.

**Stage 3 — add the energy ledger.** *Expect:* the interesting unknown. Watch for organisms that decompose others (predation) and organisms exploiting the influx directly (autotrophy). *Check:* is there a nontrivial trophic structure in the interaction graph?

**Stage 4 — add structured signals + event-driven genomes.** *Expect:* signal-responsive behaviour, then possibly coordination. *Check:* is anything doing better with the signal than without it? Reference: [SignalGP](https://arxiv.org/abs/1804.05445).

**Stage 5 — tune signal correlation length above single-organism scale.** *Expect:* the multicellularity transition, if it's going to happen. *Check:* [MODES](https://direct.mit.edu/artl/article/25/1/50/2915/The-MODES-Toolbox-Measurements-of-Open-Ended) ecological potential, and nested organizations in the COT lattice.

**Instrumentation, from Stage 0.** Per timestep: full symbol/energy ledger (conservation is your primary bug detector — if it drifts, you have a bug), abundance vector over program types, complete lineage and construction records, interaction graph edges, environmental field at reduced resolution. Compute all metrics offline from raw logs. You will change your mind about metrics; you will not want to re-run.

---

## Part 6 — Honest risks specific to this design

- **The minimization attractor is strong.** Symbol conservation alone may not beat it — Amoeba had conservation of a sort and still minimized. The energy ledger and the interaction-probability bias are your real defences, and neither is proven in combination. Test Stage 3 carefully before building further.
- **Three ledgers is a lot of coupled parameters.** Each has an influx rate, a decay rate, and a spatial scale. That's a big space to hand-tune. If it becomes unmanageable, [ASAL](https://arxiv.org/abs/2412.17799) is the automated search approach — though note that using it edges you back toward "outside optimizer," so use it to find *interesting physics*, not interesting *organisms*.
- **COT organization detection is expensive.** Computing the organization lattice is combinatorial. You'll likely need approximations or periodic rather than per-timestep computation. [Computing chemical organizations in biological networks](https://dx.doi.org/10.1093/bioinformatics/btn228) has the algorithms.
- **Nothing here guarantees intelligence.** The [Z80 co-evolution paper](https://arxiv.org/abs/2607.09211) is genuine evidence that function can co-evolve with replication, but "function" there is polynomial evaluation. Nobody has gotten anything you'd call cognition out of a program soup. Treat it as a direction, not a target.
- **Python will be too slow past Stage 2.** Plan the Odin transition around Stage 3, or prototype Stages 3+ with numpy/JAX-style vectorized updates rather than per-organism loops.

---

## Reading order for this direction

1. [Combinatory Chemistry](https://arxiv.org/abs/2003.07916) — your conservation model
2. [Co-evolution of self-replication and function in a digital primordial soup](https://arxiv.org/abs/2607.09211) — how to get function organically
3. [Toward Open-Ended Fraternal Transitions in Individuality](https://direct.mit.edu/artl/article/25/2/117/2929/Toward-Open-Ended-Fraternal-Transitions-in) (DISHTINY) — how to get multicellularity organically
4. [Prebiotic Functional Programs](https://arxiv.org/abs/2509.03534) — endogenous selection without an optimizer
5. [SignalGP](https://arxiv.org/abs/1804.05445) — genome architecture for signals
6. [Chemical Organization Theory](https://arxiv.org/pdf/q-bio/0501016) — your definition of "organism"
7. [Task-switching costs](https://www.pnas.org/doi/abs/10.1073/pnas.1202233109) — the cheapest division-of-labor lever
8. [Return to AlChemy](https://arxiv.org/abs/2408.12137) — modern re-analysis, plus working code
