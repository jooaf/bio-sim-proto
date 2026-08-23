# Phase 1 papers explained like you’re five

## Why this guide exists

The Phase 1 final report recommends eight papers. They use different languages—computer science, chemistry, biology, information theory, and thermodynamics—to discuss closely related questions:

- How can simple pieces organize themselves?
- When is repeated activity genuinely self-reproduction or metabolism?
- What changes when building materials are limited?
- How much mutation can heredity tolerate?
- How do we identify a self-sustaining group without deciding in advance what an organism is?

This guide gives you a mental model before you read. It deliberately simplifies the papers; use it as a map, not as a replacement for the papers.

---

## The whole reading list in one story

Imagine a huge room full of **LEGO robots**.

1. **Computational Life** asks: if random LEGO robots bump into each other and can rearrange each other, will a robot that copies itself eventually appear?
2. **Combinatory Chemistry** adds a rule: there are only so many LEGO pieces. To build something, the needed pieces must be available.
3. **Self-Reproducing Metabolisms** asks whether a successful structure can repeatedly gather, transform, and reuse those limited pieces.
4. **chemSKI with tokens** puts “payment tokens” on transformations, so every computational step has a local material cost.
5. **RAF theory** asks how to identify a club of reactions that collectively makes everything the club needs.
6. **Autocatalytic Sets and Biological Specificity** asks how such a club becomes selective enough to behave more like biology than an indiscriminate reaction mess.
7. **Thermodynamics of Darwinian selection** asks how much physical driving force is needed before one copier can meaningfully outcompete another.
8. **Eigen’s error-threshold paper** asks how many copying mistakes heredity can survive before information dissolves into noise.

Our Phase 1 results sit between steps 2 and 5: we have limited pieces, explicit recycling, and many cycles, but we have not found a small, persistent, self-maintaining reaction club.

---

# 1. Combinatory Chemistry

**Paper:** Kruszewski & Mikolov (2020), *Combinatory Chemistry: Towards a Simple Model of Emergent Evolution*
**Link:** [arXiv:2003.07916](https://arxiv.org/abs/2003.07916)

## ELI5 version

Imagine a box containing a fixed number of letter tiles: **S**, **K**, and **I**. You can join tiles into little machines. When two machines meet, rules allow them to take apart and rebuild their tile arrangements.

The important rule is:

> No new tiles may appear from nowhere, and no tile may disappear.

Therefore, if one machine wants another **S**, some **S** must come from somewhere else. A structure can grow only by finding available parts or by causing another structure to release them.

The surprising result is that this simple economy can produce structures that repeatedly gather parts, rearrange them, and make more organized structures. Some patterns resemble primitive metabolism and reproduction even though nobody assigned them a fitness score.

## The big idea

**Conservation creates an economy.**

Without conservation, copying can be free. With conservation, every structure faces material questions:

- Which parts do I need?
- Where are those parts?
- What must be dismantled to free them?
- Can I rebuild myself before competitors consume them?

## Terms you will encounter

- **Combinator:** A tiny symbolic function. S, K, and I are enough to express arbitrary computation when combined correctly.
- **Reduction:** Applying a rewrite rule that simplifies or transforms an expression.
- **Conservation law:** A rule saying the total amount of something remains fixed.
- **Autopoiesis:** A system continually producing or maintaining the organization that makes it a system.
- **Tabula rasa:** Starting from unorganized/random ingredients rather than inserting a designed reproducer.

## How it connects to our Phase 1

Their S/K/I inventory is analogous to our 256 conserved byte inventories.

| Combinatory Chemistry | Our simulator |
|---|---|
| S, K, I atoms | Byte values 0–255 |
| Free expressions/fragments | Tapes and free pool bytes |
| Conservative reaction | Atomic pool-mediated write |
| Missing atom blocks growth | Missing requested byte blocks a write |
| Acquire/decompose/reassemble | Return→pool→reacquire token paths |

Our tracing proved that bytes leave tapes, enter the pool, and later enter other tapes. However, our aggregate donor→receiver network was almost complete. That looks like a well-stirred room where everyone exchanges pieces with everyone—not yet a small metabolic organization.

## What to watch for while reading

1. How do the authors decide that a pattern is persistent rather than temporary?
2. What exact evidence makes them use the word “metabolism”?
3. Are successful patterns sparse reaction cycles or broad well-mixed turnover?
4. What role does decomposition play in supplying material?
5. How are time, abundance, and reaction pathways visualized?

## Do not overread it

The paper does not prove that conservation always creates life. The details of the reaction language matter enormously. A conserved system can also freeze, cycle randomly, or collapse into simple structures.

## One sentence to remember

> When pieces cannot be created for free, copying becomes a resource-acquisition problem—and resource acquisition is the beginning of ecology.

---

# 2. Self-Reproducing Metabolisms as Recursive Algorithms

**Paper:** Kruszewski & Mikolov (2021), *Emergence of Self-Reproducing Metabolisms as Recursive Algorithms in an Artificial Chemistry*
**Link:** [arXiv:2103.08245](https://arxiv.org/abs/2103.08245)

## ELI5 version

Think of a bakery that makes another bakery.

A cake recipe only makes a cake. A bakery-making recipe must do more:

1. find ingredients;
2. turn ingredients into useful components;
3. arrange those components into working equipment;
4. repeat the same process using the new equipment.

That repeating, nested procedure is a **recursive algorithm**. The authors argue that some reaction structures in their chemistry do not merely copy a static object. They execute a recurring process that obtains and transforms the materials needed to recreate the process.

## The big idea

A metabolism is better understood as a **self-recreating process** than as a particular pile of matter.

The individual atoms may change. What persists is the organization of reactions.

## Terms you will encounter

- **Metabolism:** A network of transformations that acquires and processes material to maintain a system.
- **Recursive algorithm:** A procedure that invokes or recreates the same kind of procedure at a smaller or later stage.
- **Autocatalysis:** A reaction or reaction network that helps produce more of its own catalysts/components.
- **Self-reproduction:** Producing another instance of the same organization, not necessarily copying every atom.
- **Reaction pathway:** An ordered sequence of transformations connecting inputs to outputs.

## How it connects to our Phase 1

Our token tracer can show a path such as:

`byte token on tape 116 → pool → tape 221 → pool → tape 226 → pool → tape 221`

That is explicit circulation, but circulation alone is like ingredients moving among random kitchens. To claim metabolism, we need evidence that a recurring subset of tapes/reactions:

- persists across time;
- preferentially exchanges material internally;
- recreates its organization;
- depends on those exchanges for persistence or reproduction.

Our almost-complete flow graph means the stronger claim is currently unsupported.

## What to watch for while reading

1. What exactly is reproduced: an expression, a reaction sequence, or an organization?
2. How do the authors separate a true recursive cycle from repeated random reactions?
3. What is the “food” supplied by the environment?
4. Which structures catalyze their own production?
5. What measurements could be copied into `analysis/organizations.py`?

## Useful question to ask after every figure

> If I shuffled the reaction partners, would this pattern still appear?

That question leads directly to the null model our next analysis needs.

## One sentence to remember

> A metabolism is not merely matter moving in circles; it is a recurring material-processing algorithm that helps recreate itself.

---

# 3. Computational Life

**Paper:** Agüera y Arcas et al. (2024), *Computational Life: How Well-formed, Self-replicating Programs Emerge from Simple Interaction*
**Link:** [arXiv:2406.19108](https://arxiv.org/abs/2406.19108)

## ELI5 version

Imagine filling a bowl with random scraps of computer code. Two scraps are repeatedly picked, joined together, allowed to modify each other, and separated again.

Most scraps do nothing useful. Occasionally, however, one random program happens to contain instructions that copy itself into its partner. Once that happens, copies can spread through the bowl.

Nobody rewards the program. It becomes common simply because its ordinary behavior makes more programs like itself.

## The big idea

**Self-replication can be surprisingly easy to discover** when programs can read and overwrite one another.

The difficult problem is not obtaining the first replicator. It is preventing the world from collapsing into a few simple, fast copiers.

## Terms you will encounter

- **Program soup:** A population of programs that repeatedly interact and modify one another.
- **BFF:** The Brainfuck-like instruction language used in our primary substrate.
- **Self-modification:** Program instructions can alter the memory containing programs themselves.
- **Functional self-replication score:** A behavioral test of whether a program reliably produces stable copies—not merely whether two hashes happen to match once.
- **High-order entropy:** Here, the gap between ordinary byte entropy and compressed bits per byte. It detects large-scale repeated structure.
- **Transition:** A sharp change from random-looking soup to correlated/compressible population structure.

## A simple entropy analogy

A bag of random letters has high ordinary entropy and is difficult to compress. A page containing `ABCABCABC...` may still use several letters, but the repetition makes it highly compressible.

When replicators spread, the soup develops repeated long patterns. High-order entropy detects that repetition.

## How it connects to our work

This paper defines Phase 0’s baseline.

- We reproduced the seed-0 transition at epoch 2,433.
- At the reference mutation rate, the final high-order entropy was about 6.026 bits/byte.
- Our smaller Phase 1 populations did not cross the 1-bit/byte transition threshold.
- The paper’s functional scoring method is the right next tool because entropy alone cannot prove that a tape reproduces.

## What to watch for while reading

1. Exact BFF execution semantics: head movement, instruction budget, mutation, pairing, and initialization.
2. Why a large population creates many more opportunities for rare replicators to appear.
3. Difference between exact-copy detection and functional replication scoring.
4. How the entropy transition is calculated.
5. What happens after replication emerges: takeover, diversity loss, and runtime growth.

## Important warning

A compressible soup is not automatically alive. Repeated inert patterns can also compress well. Entropy is a transition alarm; functional tests tell you what caused the alarm.

## One sentence to remember

> In a writable program soup, replication is cheap; maintaining diversity and growing complexity are the hard problems.

---

# 4. chemSKI with tokens

**Paper:** Marius Buliga (2023), *chemSKI with tokens: world building and economy in the SKI universe*
**Link:** [arXiv:2306.00938](https://arxiv.org/abs/2306.00938)

## ELI5 version

Imagine a puzzle made from connected pieces. You may apply a local transformation—like replacing one small arrangement of pieces with another—but only if you possess the correct payment token.

The token is not an external score. It is a physical permission slip consumed or rearranged by the transformation. Because tokens are limited, not every possible computation can happen immediately.

Computation therefore becomes an economy:

- Which rewrite can afford to happen?
- Where are the needed tokens?
- In what order can transformations occur?
- Can a process replenish the resources it needs?

## The big idea

**Conservative tokens make computational rewrites material and locally accountable.**

Instead of treating computation as free symbol manipulation, every rewrite has a resource footprint.

## Terms you will encounter

- **SKI combinators:** A tiny universal programming language made from S, K, I, and application.
- **Graph rewrite:** Replacing a small local graph pattern with another pattern.
- **Token:** A graph component/resource that makes a rewrite conservative.
- **Local reduction:** A transformation requiring only nearby information.
- **Token economy:** The constraints and flows produced by finite rewrite resources.

## How it connects to our SKI validation

Our minimal SKI substrate was a **portability fixture**, not a reproduction of chemSKI:

- ours stores prefix expressions on fixed byte tapes;
- ours applies B to A and atomically serializes the result;
- chemSKI uses local graph-rewrite dynamics and explicit rewrite tokens.

The shared lesson is atomicity. An SKI rewrite may change many serialized positions. If scarcity blocks it halfway through, the result is malformed. We therefore added `write_batch`, which checks the whole material exchange before changing anything.

## What to watch for while reading

1. What each token represents physically or computationally.
2. Whether tokens are consumed, transformed, transported, or returned.
3. How local rewriting avoids a global controller.
4. How scarcity changes possible rewrite order.
5. Which parts could inform a future graph-based substrate rather than our current tape fixture.

## Do not confuse two meanings of “token”

- In our metabolic tracer, token IDs are **bookkeeping labels** attached to physical bytes.
- In chemSKI, tokens are **parts of the rewrite chemistry**.

Our labels do not affect dynamics. chemSKI tokens do.

## One sentence to remember

> If every computational rewrite must balance its material books, computation develops costs, bottlenecks, and an economy.

---

# 5. A Concise Definition of RAF Sets and the RAF Algorithm

**Paper:** Wim Hordijk (2023), *A Concise and Formal Definition of RAF Sets and the RAF Algorithm*
**Link:** [arXiv:2303.01809](https://arxiv.org/abs/2303.01809)

## ELI5 version

Imagine a group of friends running a workshop.

- Each job in the workshop needs somebody to help it happen.
- Every helper needed by the group is made by the group or available in a basic supply box.
- Every material used by the group can ultimately be built from the supply box using the group’s own jobs.

If both statements hold, the workshop is a **RAF**.

RAF stands for:

- **Reflexively Autocatalytic:** every reaction is helped by something produced within the set.
- **Food-generated:** everything needed can be built from a basic environmental food set.

## The big idea

RAF theory gives a precise test for this question:

> Does this collection of reactions collectively have what it needs to keep producing its own reaction machinery from available food?

It defines an organization at the reaction-network level rather than assuming one tape equals one organism.

## Terms you will encounter

- **Reaction:** A transformation from reactants to products.
- **Catalyst:** Something that helps a reaction occur without being used up by that reaction.
- **Food set:** Basic materials assumed to be supplied by the environment.
- **RAF set:** A reaction subset that is autocatalytic and constructible from food.
- **maxRAF:** The largest RAF contained in a reaction network.
- **Closure:** Everything that can be produced from a starting set by repeatedly applying allowed reactions.

## Tiny example

Suppose food provides A and B.

- Reaction 1: A → C, catalyzed by D
- Reaction 2: B + C → D, catalyzed by C

C and D help produce one another, and both can ultimately be produced from A and B. Together, these reactions may form a RAF.

Neither reaction is self-sufficient alone. The **set** is the important entity.

## How it connects to our Phase 1

Our aggregate tape-flow graph had almost every possible donor→receiver edge. A dense graph is not automatically a RAF.

To apply RAF analysis, we must define:

- reaction types from logged interactions;
- reactants and products from tape content or functional families;
- catalysts—this is especially difficult in BFF;
- a food set, probably free pool bytes and/or common simple tape fragments;
- a time window, because the network changes.

The RAF algorithm can then test whether a smaller self-sustaining subset exists inside the noisy full graph.

## What to watch for while reading

1. The formal distinction between catalysis and ordinary consumption.
2. How closure from the food set is calculated.
3. Why finding one cycle is not enough.
4. What the maxRAF algorithm removes at each step.
5. Computational complexity and what data the algorithm assumes are known.

## Important warning for our system

In BFF, a tape can be program, data, catalyst, reactant, and product simultaneously. We must define a reaction abstraction carefully before applying RAF labels. Running the algorithm on a poorly defined graph would produce precise-looking nonsense.

## One sentence to remember

> A RAF is a reaction club whose members collectively make their own helpers from environmental ingredients.

---

# 6. Autocatalytic Sets and Biological Specificity

**Paper:** Hordijk, Wills & Steel (2014), *Autocatalytic Sets and Biological Specificity*
**Link:** [arXiv:1307.2860](https://arxiv.org/abs/1307.2860)

## ELI5 version

A workshop where everybody helps everybody may be self-sustaining, but it is also sloppy. Biology needs the right helper to assist the right job.

This paper asks how autocatalytic networks change when catalytic relationships become more selective and more closely tied to the actual structures being joined or split.

Think of keys and locks:

- In a nonspecific world, almost every key opens almost every lock.
- In a specific world, only certain keys open certain locks.

Greater specificity can create distinct, structured networks instead of one giant indiscriminate reaction web.

## The big idea

**Autocatalysis is necessary but not sufficient for biology-like organization. Specificity matters.**

A dense “everything helps everything” network can satisfy broad self-sustaining properties without containing meaningful individuality.

## Terms you will encounter

- **Catalytic specificity:** How selective catalysts are about which reactions they assist.
- **Binary polymer model:** A simplified chemistry where molecules are strings built from two symbol types.
- **Ligation:** Joining smaller molecules into a larger one.
- **Cleavage:** Splitting a molecule into smaller pieces.
- **RAF structure:** How RAFs contain, overlap, or decompose into smaller autocatalytic subsets.

## How it connects to our Phase 1

Our explicit token-flow graph was nearly complete and almost every tape pair had reciprocal transfers. That is the opposite of specificity.

The useful next question is not:

> Are there cycles?

There are far too many cycles. The useful questions are:

- Are some edges much stronger than expected?
- Do the same subsets exchange material repeatedly across time windows?
- Are transfers conditional on particular tape structures?
- Do those subsets disappear under shuffled-pair null models?

This paper supplies the conceptual reason those questions matter.

## What to watch for while reading

1. How specificity changes the probability and structure of RAF formation.
2. Difference between one giant RAF and multiple smaller subRAFs.
3. Role of ligation and cleavage—analogous to joining and splitting paired BFF tapes.
4. What makes a catalytic relation biologically plausible rather than randomly assigned.
5. Which model assumptions fail for self-modifying programs.

## One sentence to remember

> A giant web where everything interacts with everything is chemically busy, but biological organization begins when particular structures reliably support particular reactions.

---

# 7. Thermodynamics of Darwinian selection in molecular replicators

**Paper:** Artemy Kolchinsky, *Thermodynamics of Darwinian selection in molecular replicators*
**Link:** [arXiv:2112.02809](https://arxiv.org/abs/2112.02809)

## ELI5 version

Imagine two toy cars racing uphill.

- Car A is slightly faster than car B.
- But both cars need battery power to climb.
- If the batteries are almost empty and the road is noisy, A’s tiny speed advantage may not matter.

This paper connects the ability of natural selection to distinguish replicators with the physical driving force behind their replication.

A replicator cannot copy persistently for free. Replication is a physical reaction pushed away from equilibrium. The available thermodynamic “push” constrains which fitness differences can be maintained or detected.

## The big idea

**Selection has a physical resolution limit.**

If two replicators differ by less than that limit, selection cannot reliably favor the better one under the given thermodynamic conditions.

## Terms you will encounter

- **Replicator:** A molecular species that participates in making more of itself.
- **Selection coefficient:** A measure of one type’s reproductive advantage over another.
- **Thermodynamic affinity:** The driving force pushing a reaction away from equilibrium.
- **Equilibrium:** A state with no net directional reaction flow.
- **Nonequilibrium:** A driven state with sustained directional processes.
- **Fitness:** In this context, effective replication/growth performance—not an externally assigned score.
- **Chemostat:** A controlled flow reactor with material entering and leaving.

## How it connects to our Phase 1

Our pool multiplier controls material availability, not energy. Therefore it is **not literally thermodynamic affinity**. Still, the paper gives a useful analogy:

- at severe scarcity, many desired writes are blocked;
- behavior differences between tapes may no longer translate into replication-rate differences;
- the soup may become effectively neutral or frozen;
- at loose scarcity, replication strategies can express their differences more freely.

A future energy ledger would make the comparison more physically direct.

## What to watch for while reading

1. The exact assumptions under which the bound is derived.
2. How fitness is defined operationally.
3. Difference between kinetic speed and thermodynamic driving force.
4. Why equilibrium prevents sustained Darwinian selection.
5. Whether the model assumes clear molecular species and reactions—our tapes blur those categories.

## Important warning

Do not say our pool multiplier *is* temperature, free energy, or affinity. It is a material-stock parameter. The paper currently gives us a theoretical metaphor and future measurement target, not a directly tested equation.

## One sentence to remember

> A copier’s advantage only matters if the physical world supplies enough directional drive for that advantage to be expressed.

---

# 8. Eigen’s error threshold

**Paper:** Manfred Eigen (1971), *Selforganization of Matter and the Evolution of Biological Macromolecules*
**Link:** [DOI:10.1007/BF00623322](https://doi.org/10.1007/BF00623322)

## ELI5 version

Play the telephone game with a long message.

- If each person makes very few mistakes, the message remains recognizable.
- If the message is longer, there are more opportunities for mistakes.
- If mistakes become too common, the final message has no reliable connection to the original.

A replicating genome faces the same problem. It must be copied accurately enough for useful information to survive. Above a critical mutation level—the **error threshold**—selection cannot preserve the master sequence.

## The big idea

There is a trade-off among:

- genome length;
- copying accuracy;
- selective advantage.

Longer genomes can store more information, but they require more accurate copying. Early life therefore faces an information-capacity problem.

## Terms you will encounter

- **Quasispecies:** A cloud of related mutant sequences centered around successful sequence families, not a single perfectly copied genome.
- **Master sequence:** The sequence with the highest replication advantage in a simplified landscape.
- **Mutation rate:** Error probability per copied unit.
- **Copy fidelity:** Probability that copying is correct.
- **Error threshold:** The mutation level above which inherited sequence information cannot be maintained.
- **Hypercycle:** A proposed cycle in which different replicators catalytically support one another, potentially allowing more information collectively.
- **Fitness landscape:** A mapping from sequence types to reproductive performance.

## A useful back-of-the-envelope idea

If per-byte copying accuracy is `q` and a genome has `L` bytes, the chance of an entirely error-free copy is approximately:

`Q = q^L`

Even excellent per-byte accuracy becomes challenging as `L` grows.

This is the intuition—not the whole paper’s mathematics.

## How it connects to Phase 0 and Phase 1

Phase 0 seed 0 showed a mutation Goldilocks pattern:

- zero mutation: no transition by epoch 16,000;
- `1/4096`: strong transition and takeover;
- `1/128`: no transition and near-random behavior.

This is not a textbook Eigen curve because modest mutation helped discover the replicator in our finite stochastic soup. Mutation has two roles:

1. **innovation:** creating a replicator or useful variant;
2. **destruction:** corrupting inherited copying machinery.

Phase 1 adds a third issue: a correct write may still be blocked because its required byte is unavailable. Thus effective heredity depends on both mutation fidelity and material availability.

## What to watch for while reading

1. Difference between mutation rate per site and accuracy of the whole sequence.
2. Why sequence length matters exponentially.
3. What a quasispecies is and why evolution acts on a mutant cloud.
4. Assumptions behind a single master sequence.
5. Hypercycles as a proposed solution—and the parasite problems they invite.

## Important warning

Our observed Goldilocks result does not by itself prove an Eigen error threshold. We need replicated mutation sweeps under matched Phase 0/1 conditions and functional lineage measurements.

## One sentence to remember

> Mutation creates novelty, but beyond a critical rate it erases heredity faster than selection can preserve it.

---

# Common vocabulary cheat sheet

| Term | Plain-language meaning |
|---|---|
| **Catalyst** | Something that helps a reaction happen |
| **Autocatalytic** | Helps produce more of itself or its production network |
| **Metabolism** | A recurring network that obtains and transforms material to maintain an organization |
| **Conservation** | Nothing of the conserved kind appears or disappears; it only moves or changes allocation |
| **Turnover** | Material changes location or owner, whether or not useful organization exists |
| **Replication** | Producing another instance of a structure or process |
| **Self-maintaining** | The network replaces everything it consumes fast enough to persist |
| **Closure** | Applying reactions inside the set does not require unexplained products/processes outside it |
| **Food set** | Basic environmental ingredients assumed to be available |
| **RAF** | A reaction set whose catalysts and materials can collectively be generated from food |
| **Specificity** | Particular catalysts/structures support particular reactions rather than everything interacting equally |
| **Entropy** | A measure related to uncertainty/disorder; its exact meaning depends on what distribution is measured |
| **High-order entropy** | In this project, a compression-based measure of repeated large-scale soup structure |
| **Thermodynamic affinity** | Physical push driving a reaction away from equilibrium |
| **Error threshold** | Mutation level above which inherited information cannot be maintained |
| **Quasispecies** | A family/cloud of related mutant sequences maintained together |

---

# How to read the papers without getting lost

## First pass: ten minutes

For each paper, read only:

1. abstract;
2. first two introduction paragraphs;
3. every figure caption;
4. conclusion/discussion.

Then write three sentences:

- What is the world made of?
- What is conserved or supplied?
- What result surprised the authors?

## Second pass: understand the mechanism

Find and write down:

- state representation;
- reaction/update rule;
- source of randomness;
- source of resources;
- definition of reproduction/metabolism/organization;
- measurements and null models.

## Third pass: map it to our simulator

For every important term, complete:

> “In our simulator, the closest equivalent is ___, but the analogy breaks because ___.”

Example:

> “Thermodynamic affinity is loosely analogous to how strongly the world permits directed replication, but pool multiplier tracks material availability rather than free-energy dissipation.”

## Questions to keep beside you

1. Is the claimed organism inserted by the researchers or discovered from the dynamics?
2. Is “fitness” external, or does ordinary physics make some structures reproduce more?
3. Is matter genuinely conserved?
4. Does a cycle recreate itself, or is material merely circulating?
5. Is the network more structured than a shuffled/null network?
6. Are results replicated across seeds?
7. Does the metric detect behavior, or only visual/compressible structure?
8. Which assumptions would fail for self-modifying byte tapes?

---

# Recommended reading order

## If you want the easiest conceptual path

1. **Computational Life** — learn the soup and why replication is easy.
2. **Combinatory Chemistry** — add limited building materials.
3. **Self-Reproducing Metabolisms** — distinguish turnover from a self-recreating process.
4. **RAF Sets** — learn the formal test for collective self-support.
5. **Biological Specificity** — learn why a dense reaction web is not enough.
6. **chemSKI with tokens** — see another way to make computation conservative.
7. **Eigen** — understand mutation’s information limit.
8. **Thermodynamics of Darwinian selection** — finish with the most mathematical physical theory.

## If you want to implement the next analysis quickly

1. RAF Sets
2. Self-Reproducing Metabolisms
3. Biological Specificity
4. Combinatory Chemistry

The implementation target should be a **windowed reaction graph compared with a shuffled-pair null model**, not another whole-run aggregate graph.

---

# What understanding these papers should change in the project

After reading them, the central Phase 1 question should become more precise:

> Does conservation create a persistent, specific, self-supporting subset of reactions whose material flow and continued existence exceed what globally mixed random interactions would produce?

We have already answered the weaker questions:

- Is matter exactly conserved? **Yes.**
- Does matter explicitly return to the pool and enter another tape? **Yes.**
- Do cycles exist? **Yes—too many to be informative by themselves.**
- Does a second substrate work through the same architecture? **Yes.**

The papers help with the remaining distinction:

> **busy chemistry** versus **organized metabolism**.
