# External Language Investigation: Stringmol, Funge-98, FALSE, SKI, and Primordial-Soup Forth

**Date:** 2026-08-10
**Scope:** source-level and literature investigation, plus only the executions documented below.
**Question:** which of the requested systems can currently support a defensible large-scale comparison of spontaneous self-replication from an initially random population?

## Executive result

Only the paper's **primordial-soup Forth** currently meets all of the following without changing its semantics: a released implementation, a random uniform-byte initialization, pairwise tape interactions, a published functional assay, and a practical large-population run. I ran three upstream 131,072-program trials; all produced a sharp replicator transition.

**SKI combinatory chemistry** is the strongest additional scientific candidate. Its published experiment starts only from atomic `S`, `K`, and `I` combinators and reports emergent self-reproducing structures. It is not, however, a fixed-length uniformly random byte-string soup: it is a conserved multiset of expression trees, and the published large-system result uses reactant-assemblage assistance. The public code was not executable unchanged on the present Java runtime; its test suite also fails against the current source tree.

**Stringmol** demonstrably supports programmed, pairwise, self-copying molecules and rich seeded replicator–parasite dynamics. Its distributed reference configuration is seeded with a 64-symbol replicase, while its technical report describes a 65-instruction seed. It is therefore outside the requested range, seeded rather than random-uniform, and no Turing-completeness proof was located. It is a strong ecological control, not a clean test of the stated Turing-complete-length hypothesis.

**Funge-98/Befunge-98** is Turing-complete and self-modifying, but the available self-copy evidence is a *quine* (output-to-stdout), not a verified copy-into-partner reaction. **FALSE** is a compact Forth-like language but lacks the necessary random-soup/self-replication literature and a released pair-soup semantics. Neither should be assigned an emergence probability before a new, explicitly specified chemistry is implemented and seeded validation passes.

## Comparability matrix

| System | Turing complete? | Starting state | Interaction mechanism | Known replication evidence | Direct random-soup comparison now? |
|---|---|---|---|---|---|
| Primordial-soup Forth | Yes (restricted experimental Forth variant) | uniform random bytes | concatenate two 64-byte tapes, execute, split | published and reproduced here | **Yes** |
| SKI combinatory chemistry | Yes (`S`,`K`,`I` basis) | atoms only, not random trees | reduction + cleavage/condensation in a conserved multiset | published emergent self-reproducer | **No**—different genotype and assistance mechanism |
| Stringmol | no proof found in reviewed sources | hand-crafted replicase population | complementary binding, then a molecule executes a microprogram over the pair | seeded replicases, mutation, parasites | **No**—seeded and length >60 |
| Funge-98/Befunge-98 | Yes | no population protocol found | standard program executes on its own unbounded playfield | quine / self-modifying programs | **No**—partner-write chemistry absent |
| FALSE | generally described as a powerful Forth-like language; no formal proof checked | no population protocol found | one program's stack, variables and I/O | no verified self-replicator located | **No**—partner-write chemistry absent |

A quine is not treated as a soup self-replicator: it writes a representation to its configured output stream, whereas the soup criterion is that execution of `S + F` produces an additional copy of `S` in a peer/matter substrate while retaining the relevant hereditary mechanism.

## 1. Primordial-soup Forth: reproduced at paper population scale

### Method

I used the released `cubff` binary from the paper's repository, not the local Python BFF implementation:

```text
bin/main --lang forthtrivial --num 131072 --max_epochs 2000 \
  --seed {0,1,2} --eval_selfrep --log metrics.csv --disable_output
```

Relevant upstream defaults reported by `bin/main --help` were retained: `mutation_prob = 0.00024` and `run_steps = 32768`. The program reports the paper's Brotli-based `higher_entropy` and counts tapes passing its functional self-replication threshold. The logger emits every 64 epochs; its final row is epoch 2049 even though `--max_epochs 2000` was supplied, so transition times below are bounded by that 64-epoch observation resolution.

Raw results are under `results/forth-upstream-default-131072-seed-{0,1,2}/metrics.csv` (ignored local experiment output).

### Results

| seed | first logged epoch with high-order entropy >= 1 | high-order entropy there | functional self-replicators there | final logged epoch | final high-order entropy | final functional count |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1089 | 5.540 | 122,296 | 2049 | 5.705 | 125,748 |
| 1 | 513 | 5.300 | 125,202 | 2049 | 5.832 | 121,131 |
| 2 | 257 | 5.405 | 125,829 | 2049 | 5.897 | 124,575 |

All three runs transitioned from zero counted functional self-replicators to about 92–96% of the population at the first logged high-entropy state. The three first-observation times ranged from 257 to 1089 epochs (mean 620, but this is only a three-seed descriptive statistic, not a rate estimate). This is consistent with the paper's claim that almost all Forth runs transition within roughly 1,000 epochs.

### Interpretation and limitation

This is a positive large-scale replication of the *published Forth system*, not evidence that its illustrated 28-byte long-tape replicator predicts the primordial-soup result. The primordial soup has a one-byte `0C` copy primitive and a six-byte complete replicator, which is a much more plausible explanation for its rapid emergence. A language-level length comparison must separate the actual primordial-soup functional mechanism from an unrelated long-tape example.

## 2. SKI combinatory chemistry

### What the published model establishes

Kruszewski and Mikolov define a chemistry over the Turing-complete `S`, `K`, `I` combinator basis. The system begins with only atomic combinators, uses mass-conserving reductions, and applies random cleavage/condensation when no reduction is available. Their reported experiment used 10,000 evenly distributed atoms, 10 runs, and 10 million reaction iterations across reactant-assemblage parameter values.

The reported self-reproducing family has:

```text
A = (SI(S(SK)I))
(AA) + 3A  ->  2(AA) + phi(A)
```

`A` contains six primitive combinator leaves; the reproducing `(AA)` structure contains **12 primitive symbols** (or more characters if parentheses and application syntax are counted). This is in/near the requested 10–60 range only under the **primitive-leaf** encoding. It is not a 12-byte uniform byte string. The construction also relies on three available `A` reactants and, in the relevant published runs, a food/reactant-assemblage mechanism for expressions up to a configured size.

### Local reproducibility check

I cloned the authors' public Clojure implementation. It exposes `--seed`, `--size`, `--time`, `--base`, `--threads`, and disk logging, which is a good basis for a future dedicated SKI experiment.

It did not run unchanged on Java 24 because its Leiningen project specifies the now-invalid JVM option `-XX:MaxJavaStackTraceDepth=-1`. In a disposable `/tmp` checkout, replacing that option with `0` allowed compilation to progress, but `lein test` then failed because `cc/test_plot.clj` refers to the unresolved function `count-reactants-by-generation-parallel`. A 10,000-atom `lein run` attempt then produced invalid nil-valued metrics and terminated with `IllegalArgumentException: Can't put nil on channel`. No SKI numerical outcome from that run is reported as scientific data.

### Decision

**Include SKI as the next implemented comparator**, but only after:

1. pinning a compatible JDK/dependency lock or repairing the public code against its own tests;
2. choosing one encoding unit (`S/K/I` leaves, serialized tree symbols, or bytes) before discussing length;
3. reporting both an atom-only protocol and the reactant-assemblage protocol separately; and
4. defining a replication assay from stoichiometric net production of `(AA)`/equivalent structures, not the BFF functional test.

## 3. Stringmol

### What the source and literature establish

Stringmol molecules are strings over a **33-symbol alphabet**: 26 template symbols and seven function symbols. A pair must first bind through complementary Smith–Waterman alignment; the active molecule then executes its microprogram over the pair, copying and cleaving a new molecule. This is a much more molecule-like interaction model than BFF.

The public `quick_test33.conf` configuration seeds 55 copies of the explicit **64-symbol** sequence:

```text
WWGEWLHHHRLUEUWJJJRJXUUUDYGRHJLRWWRE$BLUBO^B>C$=?>$$BLUBO%}OYHOB
```

The accompanying Stringmol 0.2 technical report describes a **65-instruction** seed replicase, whose reaction takes 240 steps, and reports 1,000 mutation trials from that seed. It explicitly documents seeded invasion, mutation, sweeps, and parasite dynamics rather than spontaneous appearance from uniformly random strings.

### Local reproducibility check

The public C++ source compiled after manually creating its missing `debug` and `release` output directories. Its test driver completed only after the same manual setup. I then ran the supplied seeded configuration for 1,000 steps. It completed and printed its own legacy summary, but also warned that its agent count could not be configured by a reproducible method and reverted to an older loading path. Consequently this source/configuration combination is unsuitable for a controlled new random-initialization experiment without engineering work.

### Decision

Do **not** include Stringmol in the direct 10–60-byte Turing-complete comparison. Include it later as a separate **seeded replicator–parasite ecology control**, after pinning and modernising the build/configuration path. Its correct comparison targets are seeded survival, parasite pressure, mutation-on-copy, and spatial locality—not spontaneous discovery hazard from a uniform byte soup.

## 4. Funge-98 / Befunge-98

Funge-98 (including Befunge-98) removes the fixed-space limit of Befunge-93 and is Turing-complete. It is reflective/self-modifying: programs can read and write their playfield. It is therefore a plausible *design source* for a new soup language.

The public Code Golf quine leaderboard currently records a 9-byte Befunge quine. That is below the requested range and is not a molecule-pair experiment. No peer-reviewed artificial-chemistry study or released random-pair soup protocol was located in this investigation.

### Decision

Do not use standard Funge-98 as an observational data point. A valid future adaptation must state:

- whether an individual is a one-dimensional serialization or a 2D playfield patch;
- the finite memory and boundary conditions needed to make uniform initialization meaningful;
- how instructions such as playfield `get`/`put` map to self versus partner memory; and
- a seeded copy-into-partner test before any random search.

These choices create a new substrate, so results must not be described as properties of unmodified Funge-98.

## 5. FALSE

FALSE is a compact Forth-like, stack-oriented language designed by Wouter van Oortmerssen in 1993; its original compiler was 1,024 bytes of 68000 assembly. It is historically relevant because it influenced both Brainfuck and Befunge.

The reviewed primary material and web search did not locate a reproducible FALSE self-replicator with a 10–60-byte length, a random-population experiment, or a partner-memory interaction model. Standard FALSE programs operate through their own stack, variables and I/O; adopting it for this question would require an explicit new output-to-peer write semantics.

### Decision

Treat FALSE as an **unimplemented discovery candidate**, not a negative result. Its compact stack/quotation model makes it worth a future bounded interpreter, but no probability or length claim is warranted yet.

## Cross-language conclusion

The comparison currently contains one experimentally reproduced positive system (primordial-soup Forth), one strong but non-isomorphic literature comparator (SKI combinatory chemistry), one seeded artificial-chemistry control (Stringmol), and two design candidates (Funge-98, FALSE). The systems differ on all of the following axes:

- representation: fixed bytes, variable strings, expression trees, or 2D playfields;
- initialization: uniform strings, atoms-only, or seeded replicases;
- interaction: concatenated execution, binding plus microprogram, tree reduction, or no defined pair interaction;
- resource model: none, decay, strict mass conservation, or external runtime state;
- replication assay: BFF functional proxy, exact molecular production, stoichiometric net production, or only quine output.

Therefore, a pooled regression of “replicator length versus emergence” would be invalid. The defensible next experiment is a **within-family intervention**: implement a small, parameterized pair-soup instruction set whose copy mechanism is held constant while the shortest seeded replicator's functional information/basin density is varied. Run seeded validation first, then random initialization with matched population, byte budget, mutation process, execution budget, and replicate count.

## Related literature and primary sources

1. B. Agüera y Arcas et al. (2024), [*Computational Life: How Well-formed, Self-replicating Programs Emerge from Simple Interaction*](https://arxiv.org/abs/2406.19108). Primary source for BFF, Forth, SUBLEQ, RSUBLEQ4, the upstream `cubff` implementation, and the high-order-entropy/functional assays.
2. G. Kruszewski and T. Mikolov (2020), [*Combinatory Chemistry: Towards a Simple Model of Emergent Evolution*](https://arxiv.org/abs/2003.07916). Atom-only SKI initialization, conserved reductions, and emergent self-reproducing structures.
3. G. Kruszewski and T. Mikolov (2022), [*Emergence of Self-Reproducing Metabolisms as Recursive Algorithms in an Artificial Chemistry*](https://doi.org/10.1162/artl_a_00355). Journal development of the SKI chemistry and its recursive-metabolism interpretation.
4. G. Kruszewski and T. Mikolov, [public Combinatory Chemistry simulator](https://github.com/germank/combinatory-chemistry). Source checked in this investigation.
5. S. Hickinbotham et al. (2010), *Specification of the Stringmol Chemical Programming Language, version 0.2*, Technical Report YCS-2010-458. Distributed with the [Stringmol source](https://github.com/uoy-research/stringmol); establishes the 33-symbol alphabet, seeded 65-instruction replicase, binding, copy, and cleavage mechanics.
6. S. Hickinbotham et al. (2010), [*Diversity from a Monoculture: Effects of Mutation-on-Copy in a String-Based Artificial Chemistry*](https://www.cs.york.ac.uk/nature/plazzmid/external/papers/ALxii_div.pdf), ALIFE XII.
7. S. Hickinbotham et al. (2015), [*Maximising the Adjacent Possible in Automata Chemistries*](https://doi.org/10.1162/ARTL_a_00180), *Artificial Life*.
8. S. Hickinbotham and S. Stepney (2020), [*Innovation, Variation, and Emergence in an Automata Chemistry*](https://doi.org/10.1162/isal_a_00265), ISAL/ALIFE 2020. Stringmol replicator–parasite dynamics and self-modifying code.
9. C. Pressey (1998), [*Funge-98 Final Specification*](https://quuxplusone.github.io/Fungus/docs/spec98.html). Primary language specification for Funge-98.
10. W. van Oortmerssen, [*The FALSE Programming Language*](https://strlen.com/false-language/). Primary historical language documentation.
11. C. H. Moore and G. C. Leach (1970), *Forth: A Language for Interactive Computing*. Historical background for Forth; cited by the Computational Life paper.
