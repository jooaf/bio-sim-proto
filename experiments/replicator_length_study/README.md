# Replicator-length study

This directory is intentionally independent of the staged simulator work. It documents and runs the requested BFF 0D/1D/2D comparison without changing the existing experiment configurations or their outputs.

## Question

Does the availability of short functional self-replicators predict their spontaneous appearance in a uniformly initialized, self-modifying program soup?

The primary outcome is **not** the literal length of one hand-written string. Under uniform byte initialization, the relevant quantity is the density of the complete functional set:

\[
q = |R| / 256^L, \qquad I_{\mathrm{functional}}=-\log_2 q.
\]

A shortest example is a useful lower bound and a seed for validation, but it does not estimate `q`: no-op choices, operand freedom, context, and many distinct mechanisms can all enlarge `R`. Normalized compressor/Kolmogorov proxies are retained as descriptive measurements only. The paper's high-order entropy is a *population transition measurement*, not a probability that a random tape is functional.

## Candidate registry

### Directly supported by *Computational Life* (Agüera y Arcas et al., 2024)

| substrate | known example length | random-initialized outcome reported | status |
|---|---:|---|---|
| Forth long tape | 28 bytes (the illustrated full example; 7-byte functional tail) | emergence reported | positive comparator |
| RSUBLEQ4 primordial soup | 25 bytes | no transition after billions of executions | negative comparator |
| SUBLEQ primordial soup | 60 bytes | no transition after billions of executions | negative comparator |
| BFF | 64-byte tape carrier; the illustrated trace has 16 visibly active opcode sites | emergence reported | primary 0D/1D/2D substrate; not a validated 10–60 contiguous-byte minimum |
| Forth primordial soup | 1-byte trivial / 6-byte complete example | rapid emergence | below-range positive control |

Lengths above are representation-specific. In particular, the BFF example needs a 64-byte carrier/context even though most locations are no-ops, so it must not be treated as a proven 16-byte literal template.

### External scan: languages not simulated in that paper

| substrate | evidence found | decision |
|---|---|---|
| Stringmol 0.2.2 | Its distributed configuration has a **64-symbol** seeded replicase; its technical specification describes a 65-instruction seed. It is a genuine pairwise string chemistry, but the sources reviewed do not establish a Turing-completeness proof or random-from-uniform emergence. | useful later ecological control; excluded from the primary Turing-complete length comparison |
| Funge-98 / Befunge-98 | Funge-98 is Turing-complete; Code Golf's verified quine task currently has a 9-byte Befunge solution. A quine prints its source, which is not yet a pair-soup copy operation. | below-range adaptation control only; excluded until a write-to-partner semantics and an actual seeded replicator are verified |
| FALSE | Small stack language distinct from the paper's restricted Forth; public sources describe it as a powerful Forth-like language. No reproducible 10–60 byte self-replicator was located. | discovery candidate, not a claimed data point |
| SKI combinatory logic | Turing-complete combinatory system and the basis of a separate artificial-chemistry literature. Tree terms do not have a comparable fixed byte-string representation or a documented 10–60 byte copying seed. | conceptually valuable, but not a controlled byte-soup candidate |

This scan deliberately does **not** relabel a quine as a soup replicator. A quine is evidence that source copying is expressible; it is not evidence that the same source copies into a randomly paired neighbor under this study's dynamics.

## BFF dimension experiment

`run_bff_dimensions.py` uses the repository's reference `BFFSubstrate` interpreter. Every tape is initialized as uniformly random bytes. At each tick:

1. every byte receives independent background mutation;
2. tapes are paired and executed as concatenated ordered pairs;
3. a configured random sample is tested with the paper's functional self-replication proxy;
4. the complete soup is measured for high-order entropy and for exact descendants of detected functional hashes.

Pairing differs by dimension:

- **0D:** a Fisher–Yates shuffled, disjoint ordered pairing; every tape acts exactly once.
- **1D:** an open line; a randomly ordered untaken tape selects a neighbor within radius `r`. If that selected neighbor was already taken, the tape remains unmatched for that tick.
- **2D:** the paper's greedy local rule on an open `width × height` grid using a Chebyshev-radius neighborhood. As in 1D, unmatched tapes still mutate.

The open boundaries and greedy one-draw matching follow the paper's 2D description. These spatial configurations must not be called paper-scale reproductions until they are run at a comparable population, radius, execution budget, and replicate count.

## Measurements

Each run writes only to its requested output directory:

- `initial_basin_density.csv`: Monte Carlo estimate of initial functional-basin density, plus Wilson 95% upper bound.
- `metrics.csv`: high-order entropy, sampled functional count, candidate evaluations, discovery hazard estimate, and exact-hash persistence/takeover summaries.
- `discoveries.csv`: first detection, functional score, and later extinction/takeover ticks for each detected exact hash.
- `summary.json`: fully resolved protocol and aggregate results.

Definitions:

1. **Initial functional-basin density:** successes / independently sampled uniformly random 64-byte tapes. Zero successes are informative only through the reported confidence upper bound.
2. **Dynamic discovery hazard:** first functional detections after tick 0 divided by the number of functional candidate evaluations. It is an observed, sample-based hazard—not a causal proof that a particular write created the replicator.
3. **Survival / takeover:** persistence and threshold crossing of the exact content hash observed at discovery. Functional descendants with changed hashes are deliberately not folded into the same lineage; that would require a separately validated phenotype/lineage rule.
4. **High-order entropy:** byte Shannon entropy minus Brotli compressed bits/byte, matching the paper's proxy.

## Run

Smoke test (small and intended for mechanical validation only):

```nu
uv run python experiments/replicator_length_study/run_bff_dimensions.py \
  --dimension 0 --population-size 64 --ticks 32 --max-steps 256 \
  --functional-density-samples 16 --functional-sample-size 8 \
  --output-dir experiments/replicator_length_study/results/smoke-0d
```

Use `--dimension 1 --width 128` for 1D, or `--dimension 2 --width 32 --height 32` for 2D. `population-size` must equal `width` in 1D and `width * height` in 2D.

A meaningful run must be predeclared with fixed dimensions, seeds, mutation rate, radius, budget, detection cadence, and a sufficient replicate count. Do not compare raw detection counts across dimensions without normalizing by `functional_candidate_evaluations` and accounting for each configuration's executed pair count.

## Guarded-copier within-family intervention

`run_guarded_copier.py` is a deliberately minimal control prompted by the fact that
cross-language comparisons confound representation, initialization, interaction,
and replication semantics. It has a four-symbol alphabet and one active instruction:
`COPY` (symbol `3`). For every condition, an ordered pair executes the same rule:
when its first tape is functional, replace the second tape by an exact copy of the
first. A tape is functional precisely when its first symbol is `COPY` and its next
`k` symbols match that condition's fixed credential. All remaining bytes are
heritable payload and do not affect functionality.

Thus the shortest active seeded prefix has `k + 1` symbols, its functional
information is exactly `2(k + 1)` bits, and its uniform-random basin density is
exactly `4^-(k + 1)`. Credential length is the only manipulated variable. The
predeclared `run_guarded_copier_intervention.nu` runs credential lengths 2, 4, 6,
and 8 (6, 10, 14, and 18 bits) with 20 seeds each. It runs a seeded validation
phase first, then a random-initialization phase, with identical population (256),
tape length (16), shuffled-disjoint ordered pairs, mutation rate (1/4096 per byte
per tick), 16-instruction budget, 512 ticks, and replicate count.

```nu
# Review seeded validation before launching random initialization.
nu experiments/replicator_length_study/run_guarded_copier_intervention.nu seeded
nu experiments/replicator_length_study/run_guarded_copier_intervention.nu random
```

Pass `all` only when a manual gate between phases is not required. Each replicate writes `protocol.json`, per-tick `metrics.csv`, `summary.json`, and
`manifest.json` beneath `results/guarded-copier-v1/`. Seeded validation passes only
when at least one exact-copy event occurred; it tests the unchanged COPY mechanism,
not random discovery. Random runs report the initial functional count, first
functional tick, takeover tick, and total copy events. The experiment establishes a
controlled density–emergence relation for this artificial family only; it does not
attribute a result to BFF, Forth, or any other external language.

## Sources

- Agüera y Arcas et al. (2024), *Computational Life: How Well-formed, Self-replicating Programs Emerge from Simple Interaction*, arXiv:2406.19108, especially BFF, Forth, SUBLEQ, RSUBLEQ4, and spatial-soup sections.
- `https://github.com/paradigms-of-intelligence/cubff` — paper implementation and functional self-replication evaluator.
- Hickinbotham & Clark, *Specification of the Stringmol Chemical Programming Language* (Stringmol 0.2 technical report); `https://github.com/uoy-research/stringmol`.
- Funge-98 specification and Code Golf's public quine leaderboard (`https://code.golf/api/solutions-log?hole=quine&lang=befunge`).
