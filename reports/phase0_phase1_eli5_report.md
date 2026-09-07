# Phase 0–1 results, explained simply

**Purpose:** plain-language summary of what the experiments did, what they found, which papers shaped them, and what Phase 2 is now investigating.

**Evidence cutoff:** Phase 1 closeout and Phase 2 readiness reports, 2026-08-26.

> **One-sentence version:** We put random self-editing computer programs in a bowl, first watched copying emerge, then made every byte a scarce recyclable building block. The most interesting result is that scarcity seems to matter much more when a new replicator is being born than after a replicator community is already established.

This is a synthesis of the repository's reports, not a new statistical analysis. “Novel” below means **potentially new relative to the literature reviewed for this project**, not a completed claim of priority.

---

## 1. What was built?

Imagine a very large bowl of tiny computer programs.

- A **tape** is one program: 64 bytes containing instructions and ordinary data.
- The tapes are written in **BFF**, a Brainfuck-like language in which a program can modify its own memory and the memory of its interaction partner.
- An **interaction** joins two tapes, runs the combined program, and writes the two resulting tapes back.
- Programs are not given a score, reward, or teacher. A copier becomes common only if ordinary interactions happen to make more copies of it.
- A **mutation** occasionally changes a byte.
- **High-order entropy** is a compression-like signal: when many tapes become repeated or related, the soup becomes easier to compress and this value rises.

Phase 0 was the bowl without a material budget. Phase 1 added a shared pool of byte values. The pool does not create or destroy bytes; it only holds bytes that are not currently inside tapes.

### The Phase 1 accounting rule

When a tape tries to change `old` into `new`:

1. it takes one `new` byte from the pool;
2. it returns the overwritten `old` byte to the pool;
3. if no `new` byte is available, the write is blocked.

So the invariant is:

```text
tape bytes + free-pool bytes = the same total for every byte value
```

This is a **material economy**, not an external fitness function. Energy, space, signals, and task rewards were not active in Phase 0 or Phase 1.

---

## 2. Phase 0 — can copying appear by itself?

### The first result was a useful failure

The first acceptance batch used 20 runs with only 256 tapes. It found exact copying in **1/20 runs (5%)**. The one event reached abundance only 2, and there was no meaningful population-wide takeover. The predeclared target was 30%, so the literal gate failed.

This was not a fair reproduction of the published experiment because:

- the published protocol used about **131,072 tapes**, not 256;
- the small test therefore had roughly **200 times fewer tapes** and far fewer chances to discover a rare copier;
- the initial pairing and mutation details did not yet match the released reference implementation.

The lesson was not “BFF cannot evolve.” It was “scale and protocol are part of the experiment.”

### The corrected paper-scale baseline worked

The implementation was corrected to use the paper-style shuffled disjoint pairs, the reference background mutation rate (`1/4096` per byte), and a faster aggregate probe. The probe matched the released reference implementation at the first epoch.

At the published scale—131,072 tapes for 16,000 epochs:

- **Seed 0:** crossed the high-order-entropy transition at epoch **2,433** and finished at about **6.026 bits/byte**.
- **Seed 2:** crossed at the first recorded callback near epoch **11,777** and finished at **5.649 bits/byte**.
- Seeds 1 and 3 did not cross.
- The four available reference-rate seeds therefore produced **2/4 transitions**. This is evidence that the phenomenon is reproducible, not a reliable emergence-rate estimate.

For seed 0, a functional self-replication check found that **106 of the 1,024 most abundant tapes** passed the replication threshold at the first transition and **1,023 of 1,024** passed by the end. This strengthened the interpretation that the entropy transition represented real replicator-rich behavior rather than compression alone.

### Mutation has a “just right” region—so far only for one seed

The same seed-0 starting soup was tested three ways:

| Mutation rate | Maximum high-order entropy | Final entropy | Transition? |
|---:|---:|---:|:---:|
| 0 | 0.658 | 0.482 | No |
| 1/4,096 | 6.055 | 6.026 | Yes, epoch 2,433 |
| 1/128 | 0.0127 | 0.0105 | No |

ELI5 analogy: mutation is like making spelling mistakes while copying a recipe. A few mistakes can discover a better recipe; too many destroy the recipe. Zero mutation can also prevent discovery when the starting bowl is unlucky.

This is a strong **within-seed** pattern, but not yet a universal mutation law. More seeds are needed, and the result is related to the error-threshold ideas in Eigen [7] and the “survival of the flattest” result in Wilke et al. [8].

### Population size matters

Longer follow-up runs showed that emergence became more likely as the population grew:

| Population | Horizon | Control transitions |
|---:|---:|---:|
| 4,096 | 100,000 epochs | 1/5 |
| 16,384 | 50,000 epochs | 1/5 |
| 32,768 | 100,000 epochs | 3/5 |
| 131,072 | 16,000 epochs | 2/4 in the available reference-rate seeds |

The horizons are not identical, so this is not a clean dose-response curve. The safe conclusion is that **population scale and interaction opportunities strongly affect the chance of finding and maintaining a replicator**.

### Phase 0 takeaway

Phase 0 reproduced the important baseline from *Computational Life* [1]: random self-modifying programs can spontaneously produce functional replicators without an outside judge. It also showed why the project must separate:

- a real behavioral replication test from a compression signal;
- a protocol failure from a biological failure;
- a first replicator appearing from a replicator ecology remaining stable.

---

## 3. Phase 1 — what changes when bytes are conserved?

### Conservation worked exactly

The global pool was added without changing BFF instruction semantics. All reported conserved campaigns—including the 100,000-epoch validation, token-tracing runs, exclusion experiments, and the SKI portability runs—had **zero per-byte conservation residual**. The Phase 1 closeout also reports **66 passing tests** and successful strict type checking.

This matters because a blocked write can now be attributed to a real shortage of a requested byte, rather than to a bookkeeping bug.

### Scarcity is selective, not “the whole bowl running out”

In the 256-tape, 20,000-epoch mechanism sweep:

| Pool multiplier | Mean blocked-write rate | Peak high-order entropy | Transitions |
|---:|---:|---:|---:|
| 0.1 | 30.30% | 0.116 | 0/5 |
| 0.5 | 14.86% | 0.362 | 0/5 |
| 2 | 3.08% | 0.614 | 0/5 |
| 16 | 0.14% | 0.476 | 0/5 |
| 256 | 0% | 0.476 | 0/5 |

The total amount of free matter stays fixed. What changes is the **recipe of the free matter**. A soup can have plenty of bytes overall but be short of the particular byte a program is trying to write.

The longer 4,096-tape campaign reproduced this relationship: multiplier versus blocked fraction had Spearman `rho = -0.945`, with corrected `p = 1.13 × 10⁻⁷`.

ELI5 analogy: the supermarket is not empty; it is out of eggs. Having more total food does not help if the recipe specifically needs eggs.

### Blocking comes in two flavors

- At very low multipliers, many byte types are short and blocking is broad and nearly continuous.
- At multipliers 2–16, most epochs are quiet, but a rare long-running interaction can repeatedly request one scarce byte and create a huge spike.

In the path-tracing report, one interaction explained about **80.4%** of blocking at multiplier 0.5 and **97.8%** at multiplier 2 in the most blocked epochs. Its leading requested symbol explained **99.1%** and **99.9%**, respectively.

The likely explanation is not that every tape suddenly freezes. It is that one BFF program enters a long loop and keeps asking for the same unavailable building block.

### Bytes really circulate

Nine token-audited runs reconstructed bookkeeping paths in which bytes:

```text
tape A → pool → tape B → pool → tape C
```

Every condition showed return-to-pool, later reacquisition, cross-tape movement, reciprocal edges, and directed cycles with zero byte/token conservation errors.

That proves **matter circulation**. It does not yet prove metabolism. A busy recycling center can have many cycles without containing a small, persistent, self-maintaining “organism.”

### Time windows reveal temporary roles

The whole-run donor/receiver graph was almost completely mixed, which initially looked unlike metabolism. Looking at 2,000-epoch windows changed the picture:

- consecutive-window flow correlation: **0.193**;
- shuffled-label null: **0.011**;
- paired permutation `p = 0.0025`;
- the effect remained after excluding self-flow.

Nearby windows therefore retain some producer/receiver-like roles. Persistence fell at longer lags: approximately 0.193 at lag 1, 0.063 at lag 2, and 0.024 at lag 4. The exact four-point test gave `p = 0.0833`, so this is a **descriptive drifting-role pattern**, not a confirmed long-lived metabolism.

This distinction follows the metabolism and autocatalytic-set literature [3–6]: repeated flow is weaker evidence than a specific, persistent, self-supporting reaction set.

### Conservation does not simply stop replication

At 4,096 tapes and 100,000 epochs, control emergence was 1/5 and multiplier-2 emergence was also 1/5 (`p = 0.78`). At 32,768 tapes, control emergence was 3/5; the conservation condition did not clearly reduce takeover persistence either.

The combined conclusion is:

> **Population scale controls how often a replicator is found and whether it persists. Conservation controls the material economy.**

They are related, but they are not the same knob.

### Established replicator communities are unusually good at recycling

A naturally emerged Phase 0 checkpoint was continued for 8,000 epochs under conservation:

- multiplier 16 was byte-identical to the no-conservation control;
- multiplier 2 remained viable with a blocked fraction of about `2.6 × 10⁻⁷`;
- multiplier 0.5 remained viable with a blocked fraction of about `5.8 × 10⁻⁶`;
- a random-soup multiplier-2 baseline had blocked fraction about `7.6 × 10⁻³`.

The established population was a **quasispecies**—a cloud of related tapes—not one perfect winner. Its byte demand was close to its own byte composition, so it could continually recycle what it already used.

Even zero free supply of six symbols enriched in this ecology was mostly absorbed as friction; about **98.6%** of blocked writes targeted the excluded symbols. This suggests a resource-efficient ecology, not an invulnerable one.

### The strongest candidate new finding: an origin filter

The most interesting intervention removed free pool supplies of six symbols used heavily by the known BFF replicator class: the null byte and five structural BFF symbols (`<`, `[`, `,`, `}`, `]`).

During random-soup emergence:

- structural exclusion: **0/5** transitions;
- no-conservation control: **3/5** transitions;
- one-sided Fisher exact `p = 0.083`;
- excluding six arbitrary non-structural symbols: **3/5** transitions.

The mechanism-level trace supports the story: ordinary and successful runs grew structural-symbol content from a random baseline of about 2.3% to roughly 11–20%, while the natural-six exclusion runs stayed near baseline or fell slightly. Excluding only the null byte also prevented emergence in 0/3 descriptive runs, suggesting that the falsy byte is important to the loop structure.

ELI5 analogy: a mature bakery may recycle its own flour successfully, but a town with no flour at the beginning may never produce its first bakery.

This is **promising but not proven**:

- five seeds is a small sample;
- `p = 0.083` does not meet a conventional 0.05 threshold;
- the arbitrary-symbol control experienced less total blocking, so friction was not perfectly matched;
- an established ecology was tested from one natural checkpoint and for only 8,000 epochs.

The careful claim is:

> In this simulator and protocol, the availability of a known replicator class’s structural symbols was associated with its origin being suppressed, while the same kind of shortage was largely tolerated by an established ecology.

### SKI showed that substrate details matter

A minimal fixed-tape SKI chemistry ran through the same world, scheduler, conservation checks, logging, and deterministic output pipeline.

- SKI expressions stayed valid.
- Conservation residuals stayed zero.
- Repeated runs produced byte-identical Parquet output.
- Scarcity was non-monotonic: mean blocked-slot fractions were 76.82% at multiplier 0.5, 89.29% at 2, and 0.55% at 16.

The intermediate pool let expressions become longer, which made them demand more scarce symbols. This is a useful warning: **a conservation rule is not a universal effect independent of the programming chemistry**. The SKI experiment validated portability; it was not a reproduction of chemSKI [4].

---

## 4. What Phase 1 did—and did not—discover

### Strong findings inside this model

- Exact, symbol-by-symbol conservation is mechanically reliable.
- Scarcity is composition-specific and tunable, not loss of total matter.
- Tight pools produce broad blocking; looser pools produce rare symbol-specific bursts.
- Long loops can dominate a whole tick’s blocking.
- Bytes return to the pool and are reacquired across tape identities.
- Adjacent time windows contain temporary flow roles above a shuffled null.
- Established replicator ecologies are much more resource-efficient than random soups.
- Different substrates respond differently to the same pool multiplier.

### Candidate novel findings to investigate further

1. **Origin-versus-maintenance asymmetry:** structural scarcity may prevent a replicator class from forming while barely disturbing an established quasispecies.
2. **Scarcity as a burst generator:** a global conserved pool can produce highly concentrated, single-loop blocking events rather than only a smooth slowdown.
3. **Hidden transient organization:** whole-run flow can look fully mixed while short time windows contain persistent roles.
4. **A conserved program soup as a bridge between program evolution and artificial chemistry:** this combines the BFF emergence baseline [1] with symbol-level conservation motivated by [2], while explicitly testing the stronger metabolism criteria in [3–6].

These should be presented as **hypotheses or candidate contributions** until larger samples, better matched controls, and a wider literature search are completed.

### Things not established

- A universal optimal mutation rate.
- A reliable “intermediate scarcity is best” law. The corrected multiplier-versus-maximum-entropy test gave `p = 0.273`.
- A persistent, sparse, organism-like metabolism.
- Open-ended evolution, increasing complexity, trophic levels, or multicellularity.
- Literal genome minimization: tapes have fixed length, so nonzero-byte count is not a valid genome-length measure.

---

## 5. What Phase 2 is now investigating

Phase 2 adds a toroidal 2D lattice, local neighborhoods, empty cells, neutral dissolution, and pool-funded reseeding. It still does **not** add energy, signals, task bias, or an external fitness function.

| Phase 0–1 clue | Phase 2 investigation | Why it matters |
|---|---|---|
| Established ecologies recycle well in a global pool | Does locality create spatially separated resource neighborhoods and different local ecologies? | Tests whether space turns broad circulation into persistent patches. |
| Dissolution is the natural way to return scarce bytes | Can a live world stay partly empty while bytes cycle through dissolution and reseeding? | Tests the “nutrient cycle” without letting the world clog—or pass merely because everything died. |
| Windowed flow roles exist but may be content persistence | Do nearby tapes share sequence structure above a permutation null? | Separates real spatial organization from a mixed soup. |
| A dense flow graph is not enough to claim metabolism | Do local patches show block-level differentiation and persistence? | Moves from “busy chemistry” toward measurable organization. |
| Replication systems can be exploited by parasites | Does locality contain a parasite that spreads in a well-mixed world? | Tests whether space prevents global takeover. |
| Population scale strongly affects emergence | Does interaction radius change ecology independently of population size and turnover? | Tests whether locality adds a new organizing mechanism. |

### Current Phase 2 status

The early Phase 2 work is a scaffold and pilot program, not a passed final gate:

- A liveness pilot selected spontaneous dissolution `10⁻⁵` and reseeding `10⁻⁵` per tick.
- The 32×32 confirmation passed mechanically in **3/3 seeds**, with median late occupancy 0.767, 131 dissolutions, 31 placements, and zero invariant failures.
- In the five-seed radius pilot, positional byte-identity was above its within-run permutation null in **20/20 runs**. Radius 1 exceeded radius 8 in all five matched seeds; mean difference was 0.004050 with exact paired `p = 0.03125`. Radius 2 was strongest, so the response is not monotonic.
- The original exact-hash spatial metric was found to be uninformative because every final hash was unique. It was replaced, before the acceptance treatment, by positional byte identity and coarse BFF-opcode-signature beta diversity.
- The BFF parasite candidate failed its required large-radius positive control, so BFF containment cannot be claimed.
- An independently validated Spatial Stringmol host–parasite control did pass: global ancestry reached 90% in 10/10 seeds, local ancestry reached 90% in 0/10, and the global-minus-local final ancestry effect was 0.661862 (95% paired bootstrap interval [0.566007, 0.747191], exact `p = 0.000977`). This is an **external mechanism control**, not evidence of BFF parasite containment.
- The frozen 500,000-tick BFF treatment has not yet run. Phase 2 is conditionally ready to launch it, but it has not passed.

The immediate Phase 2 questions are therefore:

1. Can spatial locality produce durable structure in the conserved BFF soup?
2. Can dissolution recycle material without clogging or extinction?
3. Do spatial effects survive long-run, preregistered null-model tests?
4. Does the origin-filter effect remain when material is local rather than globally mixed?
5. Can a later energy ledger turn these spatial patches into genuine trophic or metabolic organizations?

---

## 6. Top papers behind the experiments and interpretations

### Phase 0 and Phase 1 foundations

1. **Agüera y Arcas et al. (2024), “Computational Life: How Well-formed, Self-replicating Programs Emerge from Simple Interaction.”** [arXiv:2406.19108](https://arxiv.org/abs/2406.19108)
   The direct Phase 0 comparator: BFF semantics, shuffled interactions, mutation, high-order entropy, and functional replication scoring.

2. **Kruszewski & Mikolov (2020), “Combinatory Chemistry: Towards a Simple Model of Emergent Evolution.”** [arXiv:2003.07916](https://arxiv.org/abs/2003.07916)
   The main conservation analogy: finite primitive symbols, acquire/decompose/reassemble cycles, and emergent organization from a tabula-rasa start.

3. **Kruszewski & Mikolov (2021), “Emergence of Self-Reproducing Metabolisms as Recursive Algorithms in an Artificial Chemistry.”** [arXiv:2103.08245](https://arxiv.org/abs/2103.08245)
   The standard used to avoid calling every cycle “metabolism”; it motivated explicit path tracing and the search for self-recreating processes.

4. **Buliga (2023), “chemSKI with tokens: world building and economy in the SKI universe.”** [arXiv:2306.00938](https://arxiv.org/abs/2306.00938)
   Motivated the SKI portability test and the idea that computational rewrites can have finite material costs. Its chemistry tokens are not the same as this project’s bookkeeping token labels.

5. **Hordijk (2023), “A Concise and Formal Definition of RAF Sets and the RAF Algorithm.”** [arXiv:2303.01809](https://arxiv.org/abs/2303.01809)
   Provides a future way to test whether a small reaction subset is collectively self-supporting rather than merely part of a dense interaction graph.

6. **Hordijk, Wills & Steel (2014), “Autocatalytic Sets and Biological Specificity.”** [arXiv:1307.2860](https://arxiv.org/abs/1307.2860)
   Explains why a nearly complete donor/receiver network is weak evidence and why reaction specificity and smaller sub-networks matter.

7. **Eigen (1971), “Selforganization of Matter and the Evolution of Biological Macromolecules.”** [DOI:10.1007/BF00623322](https://doi.org/10.1007/BF00623322)
   The error-threshold framework used to interpret the mutation-rate experiment and the need to balance innovation against loss of heredity.

8. **Wilke et al. (2001), “Evolution of Digital Organisms at High Mutation Rates Leads to Survival of the Flattest.”** [DOI:10.1038/35099067](https://doi.org/10.1038/35099067)
   A caution that high mutation can favor robust families rather than simply producing “no evolution”; it motivates functional family analysis beyond one master tape.

9. **Kolchinsky, “Thermodynamics of Darwinian Selection in Molecular Replicators.”** [arXiv:2112.02809](https://arxiv.org/abs/2112.02809)
   A theoretical lens for asking when resource constraints can erase meaningful differences between replicators. Pool multiplier is a material-stock parameter, not literally thermodynamic affinity, so this is an analogy and future theory target—not a direct validation of the equation.

### Phase 2 design references

10. **Sayama (2024), “Self-Reproduction and Evolution in Cellular Automata: 25 Years After Evoloops.”** [arXiv:2402.03961](https://arxiv.org/abs/2402.03961)
    Motivates structural dissolution as a principled way to prevent a finite spatial world from filling with inactive debris.

11. **Ono & Ikegami (2005), “Computational Studies on Conditions of the Emergence of Autopoietic Protocells.”** [BioSystems](https://www.sciencedirect.com/science/article/abs/pii/S030326470500050X)
    Motivates testing whether local reactions can create persistent inside/outside-like spatial organization.

12. **Hickinbotham & Stepney (2020), “Innovation, Variation, and Emergence in an Automata Chemistry.”** [Artificial Life proceedings](https://direct.mit.edu/isal/proceedings/isal2020/32/753/98477)
    Motivates parasite positive controls and the warning that replicator–parasite systems need a valid invasion control before locality can be credited with containment.

13. **Jost (2006), “Entropy and Diversity.”** [Oikos](https://nsojournals.onlinelibrary.wiley.com/doi/10.1111/j.2006.0030-1299.14714.x)
    Motivates Hill effective numbers and multiplicative alpha/beta/gamma diversity rather than treating an opaque entropy value as “number of species.”

14. **Moreno & Ofria (2019), “Toward Open-Ended Fraternal Transitions in Individuality.”** [Artificial Life](https://direct.mit.edu/artl/article/25/2/117/2929/Toward-Open-Ended-Fraternal-Transitions-in)
    Motivates asking whether locality and spatially separated opportunities can make cooperation and higher-level organization useful without an external fitness function.

---

## 7. Where to verify the details

- [Phase 0/1 findings log](../FINDINGS.md)
- [Phase 1 final report](phase1_final_report_2026-08-12.md)
- [Phase 1 new-experiment findings](phase1_newexperiments_findings.md)
- [Phase 1 campaign 2 consolidated report](phase1_campaign2_consolidated_report.md)
- [Phase 1 contribution and novelty assessment](phase0_phase1_findings_novelty_and_phase2_readiness.md)
- [Phase 1 closeout and Phase 2 handoff](phase1_closeout_and_phase2_handoff.md)
- [Phase 2 preregistration](phase2_preregistration.md)
- [Phase 2 acceptance readiness after the external control](phase2_acceptance_readiness_after_stringmol.md)

## Bottom line

Phase 0 showed that functional copying can emerge from random self-modifying programs when the protocol is large enough. Phase 1 showed that exact byte conservation creates a real, selective resource economy. The strongest candidate new idea is that this economy may act as an **origin filter** for new replicator classes while established replicator communities become unusually good at recycling their own material.

Phase 2 is testing whether space, local interaction, and dissolution turn that economy into persistent spatial organization—and whether they can contain exploitation—without quietly replacing natural dynamics with an external optimizer.
