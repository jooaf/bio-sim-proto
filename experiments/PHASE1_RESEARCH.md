# Phase 1 Research Brief — Symbol Conservation in Program Soups

Supplementary reading beyond the existing design-brief and literature-review references. Each entry below is selected because it directly illuminates a Phase 1 mechanism: pool-mediated writes, blocked-write dynamics, acquire/decompose patterns, or the connection between conservation laws and emergent ecology.

---

## Core conservation references (already cited; re-read for Phase 1)

### Combinatory Chemistry: Towards a Simple Model of Emergent Evolution
- **Authors**: Germán Kruszewski, Tomas Mikolov (2020)
- **Link**: https://arxiv.org/abs/2003.07916
- **Why for Phase 1**: This is the reference implementation of symbol conservation in an algorithmic chemistry. It fixes the global count of each primitive symbol (S, K, I) and from tabula rasa produces autopoietic structures, recursive growth, and self-reproducers. The key Phase 1 insight: **conservation forces an acquire→decompose→reassemble cycle that the authors explicitly call "remarkably similar to biological metabolisms."** Read Sections 3–4 for the specific conservation mechanism (their "chemistry rules") and Section 5 for the emergent patterns table. Pay attention to how they initialize the pool and what happens when pool depletion occurs — this is the analogue of our `pool_multiplier` sweep.

### Emergence of Self-Reproducing Metabolisms as Recursive Algorithms in an Artificial Chemistry
- **Authors**: Germán Kruszewski, Tomas Mikolov (2021)
- **Link**: https://arxiv.org/abs/2103.08245
- **Why for Phase 1**: The follow-up to Combinatory Chemistry. This paper goes deeper into the *metabolic* aspect — it hypothesizes that the key property for self-reproducing metabolisms is "an auto-catalyzed subset of Turing-complete reactions." For Phase 1, this is directly relevant because our BFF substrate is Turing-complete, and the conservation law creates the same auto-catalyzed-subset dynamic. Read for: (1) how they detect and characterize metabolic cycles from the reaction graph, and (2) the "recursive algorithm" framing — their structures "acquire basic constituents from the environment and decompose them." This is exactly what we're looking for in P1.3 (acquire/decompose pattern detection).

---

## Newly identified references

### chemSKI with tokens: world building and economy in the SKI universe
- **Authors**: Marius Buliga (2023)
- **Link**: https://arxiv.org/abs/2306.00938
- **Code**: https://github.com/mbuliga/chemski
- **Why for Phase 1**: chemSKI is a graph-rewrite system that uses **tokens to make all rewrites conservative**. Each rewrite consumes a token; tokens are finite and must be acquired. This is the closest existing system to our pool-mediated write mechanism — a token is exactly analogous to a pool byte. Read for: (1) how the token economy shapes which reductions occur, (2) the concept of a "decentralized virtual machine which performs only local reductions" (maps to our interaction-radius locality), and (3) the cost model — tokens provide a built-in complexity measure. The programs repository includes interactive simulations showing how token scarcity creates ordering constraints. This paper is short and practical; the ideas are directly portable to Phase 1 analysis.

### Thermodynamics of Darwinian selection in molecular replicators
- **Authors**: Artemy Kolchinsky (2025, Phil. Trans. R. Soc. B)
- **Link**: https://arxiv.org/abs/2112.02809
- **Why for Phase 1**: This paper derives a **thermodynamic bound relating fitness, replication rate, and thermodynamic affinity** for autocatalytic molecular replicators. The bound applies to "polymer-based replicators and certain kinds of autocatalytic sets" — which describes our BFF replicators under conservation. The key result: the critical selection coefficient (minimum fitness difference visible to selection) is bounded by a function of the thermodynamic affinity (how far from equilibrium the replication reaction is). **For Phase 1, this gives a theoretical prediction**: as the pool_multiplier decreases (scarcer resources), the affinity changes, which changes the minimum detectable fitness difference. At very low multipliers, selection should become effectively neutral because no replicator can outcompete another by enough to overcome the thermodynamic bound. Read Sections 2–4 for the bound derivation, and Section 5 for the chemostat model (which is structurally similar to our fixed-population Stage 0/1 soup).

### Bridging two theoretical frameworks of autocatalysis: RAF sets and stoichiometric autocatalysis
- **Authors**: Richard Golnik, Thomas Gatter, Wim Hordijk, Peter F. Stadler, Nicola Vassena (2026)
- **Link**: https://arxiv.org/abs/2605.25523
- **Why for Phase 1**: This paper proves that **any RAF (reflexively autocatalytic and food-generated set) is stoichiometrically autocatalytic** under mild conditions. This is important for Phase 1 because it bridges the two mathematical frameworks we could use to analyze our interaction graphs: RAF theory (Hordijk & Steel) and stoichiometric network theory. The practical consequence: if we detect a closed set of tapes in the interaction graph that collectively maintains its byte composition via pool-mediated writes, that set is *both* a RAF and stoichiometrically autocatalytic, and we can use tools from either framework. Read for the formal definition of "stoichiometric autocatalysis" and the proof sketch — it tells you what you need to check to claim you've found an autocatalytic organization.

### A Concise and Formal Definition of RAF Sets and the RAF Algorithm
- **Authors**: Wim Hordijk (2023)
- **Link**: https://arxiv.org/abs/2303.01809
- **Why for Phase 1**: A 7-page reference that provides the complete, formal definition of RAF sets and an efficient algorithm to detect them. If you want to detect autocatalytic subsets in the interaction graph (P1.3), this is the practical algorithm reference. Shorter and more self-contained than the original Hordijk & Steel papers. The algorithm runs in polynomial time in the number of reaction types (in our case: distinct content hashes). Read this before implementing any autocatalysis detection in `analysis/organizations.py`.

### Impact of composition on the dynamics of autocatalytic sets
- **Authors**: Alessandro Ravoni (2020, BioSystems)
- **Link**: https://arxiv.org/abs/2009.05958
- **Why for Phase 1**: Studies how different **composition operations** among autocatalytic sets affect emergent dynamics. The key finding: "operations involving entities that are sources for autocatalytic sets can promote the formation of different autocatalytic subsets, opening the door to various long-term behaviours." For Phase 1, this is relevant to understanding what happens when two replicator lineages encounter each other — do they compete for the same pool bytes, do they merge into a larger autocatalytic set, or do they partition the byte pool? The composition-operations framework provides a vocabulary for classifying interaction outcomes.

---

## Network analysis & trophic structure (preview for Stage 3, relevant to Phase 1 interaction-graph analysis)

### Trophic coherence determines food-web stability
- **Authors**: Samuel Johnson, Virginia Domínguez-García, Luca Donetti, Miguel A. Muñoz (2014, PNAS)
- **Link**: https://arxiv.org/abs/1404.7728
- **Why for Phase 1**: Introduces **trophic coherence** as a measure of how neatly a directed network's nodes fall into distinct levels. The key result: trophic coherence is a better predictor of ecosystem stability than size or complexity. For Phase 1, we can compute trophic coherence on the byte-flow interaction graph (from P1.3) to quantify whether the soup under conservation develops a hierarchical structure — i.e., are there "producers" (tapes that primarily contribute bytes to the pool) and "consumers" (tapes that primarily withdraw)? This is a one-number summary that tells you whether conservation is creating ecological structure. Read the methods section for the trophic-level computation algorithm.

### Energy flow controls the stability of multitrophic ecosystems with stratified nonreciprocity
- **Authors**: Rukmani Ramachandran, Akshit Goyal (2026)
- **Link**: https://arxiv.org/abs/2601.12717
- **Why for Phase 1/Stage 3**: Shows that **energy flow across trophic levels controls stability**, with a remarkable finding: lower energy transfer efficiency expands the stable region, suggesting that the famous "10% energy transfer" in ecosystems might promote stability. For Phase 1, this is a preview of what the energy ledger (Stage 3) could produce — but the analytical framework (stratified nonreciprocity) can already be applied to the byte-flow network under conservation. The key structural insight: "the location of nonreciprocity within a complex network, not merely its magnitude, determines stability."

### How directed is a directed network?
- **Authors**: R.S. MacKay, S. Johnson, B. Sansom (2020)
- **Link**: https://arxiv.org/abs/2001.05173
- **Why for Phase 1**: Proposes a simple definition of trophic level that works on *any* directed network — no source nodes required. This is important because our interaction graphs may not have natural "source" nodes (tapes that only give bytes and never receive). The standard ecological trophic-level computation requires basal species; this paper's method doesn't. Use this algorithm in `analysis/trophic.py` when analyzing byte-flow graphs from Phase 1.

### Synergy and Complementarity: The Generative Basis of Chemical Organizations
- **Authors**: Tomas Veloz (2026)
- **Link**: https://arxiv.org/abs/2608.03541
- **Why for Phase 1**: A major advance in Chemical Organization Theory (COT). Identifies **elementary reaction closures (ERCs)** as the minimal building blocks that combine (via "synergy" and "complementarity") to form organizations. The key practical result: "the synergies and complementarities we use to generate persistent modules scale radically slower than usual combinatorial methods." For Phase 1 and beyond, this is the algorithmic breakthrough that makes COT organization detection feasible on our interaction graphs. The paper quantifies these structures across 438 biological reaction networks and finds that "larger biological networks achieve persistence through a progressively smaller and more selective set" of synergies. Read Sections 3–4 for the ERC definition and the combinatorial-scaling argument.

---

## Already-cited papers worth re-reading specifically for Phase 1

### Computational Life: How Well-formed, Self-replicating Programs Emerge from Simple Interaction
- **Authors**: Agüera y Arcas et al. (2024)
- **Link**: https://arxiv.org/abs/2406.19108
- **Why re-read for Phase 1**: The BFF substrate semantics, the emergence rate, and the high-order-entropy transition metric. Phase 1 adds conservation to exactly this system, so you need to know the baseline cold. Re-read: the BFF instruction table (verify our implementation matches), the entropy transition metric (will be used to compare Phase 0 vs Phase 1 emergence), and the functional self-replication score (could be adapted to measure how "pool-efficient" a replicator is).

### Prebiotic Functional Programs: Endogenous Selection in an Artificial Chemistry
- **Authors**: Devansh Vimal, Cole Mathis, Westley Weimer, Stephanie Forrest (2025)
- **Link**: https://arxiv.org/abs/2509.03534
- **Why for Phase 1**: Demonstrates endogenous selection in AlChemy (a lambda-calculus artificial chemistry) without an external fitness function. For Phase 1, the key insight is **how to detect functional enrichment without defining "function" a priori**: they steer dynamics using features endogenous to the system. If Phase 1 produces acquire/decompose patterns, those patterns *are* the endogenous features we should use to characterize the system, rather than imposing external categories.

### Self-Organization in Computation & Chemistry: Return to AlChemy
- **Authors**: Cole Mathis, Fontana et al. (2024)
- **Link**: https://arxiv.org/abs/2408.12137
- **Code**: https://github.com/mathis-group/AlChemy
- **Why for Phase 1**: Modern re-analysis of Fontana & Buss's original AlChemy with real compute. Finding: "complex stable organizations emerge more often than expected and resist collapse to trivial fixed points." For Phase 1, this is directly relevant: does conservation produce complex stable organizations (closed byte-flow subnetworks) or does it just slow down the collapse to minimal replicators? The AlChemy codebase may also contain useful algorithms for detecting organizations in lambda-calculus reaction networks that could be adapted to our byte-tape interaction graphs.

---

## Theoretical framing references

### Autocatalytic Sets and Biological Specificity
- **Authors**: Wim Hordijk, Peter R. Wills, Mike Steel (2014)
- **Link**: https://arxiv.org/abs/1307.2860
- **Why for Phase 1**: Extends RAF theory to models where "the pattern of catalysis more precisely reflects the ligation and cleavage reactions involved." This is important because our BFF interactions *are* cleavage (splitting the joint tape) and ligation (concatenation). The paper shows that certain properties of these more realistic models can be predicted from simpler binary polymer models. Read for: how to model cleavage/ligation in the RAF framework, and Section 4's "new results concerning the structure of RAFs in these systems."

### Autocatalytic Sets Extended: Dynamics, Inhibition, and a Generalization
- **Authors**: Wim Hordijk, Mike Steel (2012)
- **Link**: https://arxiv.org/abs/1206.1017
- **Why for Phase 1**: Includes **dynamical simulations of molecular flow on autocatalytic sets** (Section 3). For Phase 1, this is the closest thing to simulating what happens when a pool-mediated system has a RAF: how do molecules (bytes) flow through the set? The finding that "autocatalytic sets are viable and outcompete non-autocatalytic sets" is directly testable in our system: do tapes participating in closed byte-flow cycles persist longer than those that don't?

---

## How these relate to specific Phase 1 experiments

| Experiment | Key references to consult |
|---|---|
| P1.1 (pool_multiplier sweep) | Combinatory Chemistry (Kruszewski 2020), Thermodynamics of Darwinian selection (Kolchinsky 2025) |
| P1.2 (tape-length × conservation) | Autocatalytic Sets and Biological Specificity (Hordijk 2014), chemSKI with tokens (Buliga 2023) |
| P1.3 (acquire/decompose patterns) | Self-Reproducing Metabolisms (Kruszewski 2021), RAF Sets definition (Hordijk 2023), Impact of composition (Ravoni 2020) |
| P1.4 (blocked-write time series) | chemSKI with tokens (Buliga 2023), Combinatory Chemistry (Kruszewski 2020) |
| P1.5 (conservation × minimization) | Thermodynamics of Darwinian selection (Kolchinsky 2025), Return to AlChemy (Mathis 2024) |
| P1.7 (population-size × conservation) | RAF Sets in polymer networks (Hordijk 2016), Autocatalytic Sets Extended (Hordijk 2012) |
| Interaction-graph analysis | Trophic coherence (Johnson 2014), How directed is a directed network? (MacKay 2020), Synergy and Complementarity (Veloz 2026) |
| Future Stage 3 trophic analysis | Energy flow controls stability (Ramachandran 2026), Bridging RAF and stoichiometric autocatalysis (Golnik 2026) |

---

## Quick-read priority

If you only have time for 3 of these before running Phase 1 experiments:

1. **Combinatory Chemistry** (Kruszewski & Mikolov 2020) — the reference model; re-read Sections 3–5
2. **Self-Reproducing Metabolisms as Recursive Algorithms** (Kruszewski & Mikolov 2021) — what to look for in the acquire/decompose data
3. **Thermodynamics of Darwinian selection** (Kolchinsky 2025) — gives a theoretical prediction for the pool_multiplier sweep

If you have time for 2 more:

4. **chemSKI with tokens** (Buliga 2023) — closest existing token-conservation system
5. **Synergy and Complementarity** (Veloz 2026) — the algorithmic breakthrough for organization detection
