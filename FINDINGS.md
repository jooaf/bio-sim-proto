# Findings

## 2026-08-06 — Stage 0: bare soup

### What was built

- Deterministic, flat NumPy population of fixed-length BFF tapes with random ordered pairing.
- Plain-Python self-modifying BFF interpreter, tested against hand-worked examples for all ten opcodes.
- Explicit configuration tree and TOML round trips, single seeded `numpy.random.Generator`, stage gates, buffered raw Parquet logging, manifests, invariant log, experiment runner, and offline analysis/report pipeline.
- Raw tables: `ticks`, `interactions`, `tapes`, `lineage`, `population`, and `events`.
- Offline exact-copy inference from interaction hashes; no replication detector exists in the simulator.
- Hill effective-number diversity profiles and Stage 0 analysis skeletons for later metrics.

### Reference-semantic finding

The released `bff_noheads` implementation accompanying arXiv:2406.19108v2 wraps both data heads modulo the 128-byte joint tape. It bounds the instruction pointer, dynamically scans the current tape for brackets, wraps byte arithmetic, starts the PC and both heads at zero, and uses an 8,192-character budget. This differs from the build prompt's clamp-default statement. In accordance with the prompt's instruction to follow the paper, `head_wrap = true` is the documented Stage 0 default; clamping remains configurable.

### Acceptance results

Configuration: `experiments/configs/stage0.toml`; 20 seeds (0–19), 20,000 epochs/seed, 256 tapes, 256 interactions/epoch, 64 bytes/tape, 8,192-character budget. This produced 102,400,000 raw interaction records and approximately 5.0 GiB of run data.

1. **Replication emergence — FAIL.** Exact offline replication was found in **1/20 runs (5.0%)**, below the required 30%. Seed 18 had one event at epoch/tick **9,251**. Its inferred replicator hash reached maximum abundance **2**, so it did not take over.
2. **Distinct-hash collapse — FAIL.** All runs peaked at 256 distinct hashes. Final distinct count was 256 in 18 runs, 255 in seed 7, and 252 in seed 9 (mean **255.75**). No run crossed the report's predeclared clear-collapse threshold of 50%; the largest transient peak-to-minimum decline was **7.0%**. The one replication-positive run declined transiently by **5.469%** and finished at 256.
3. **Unattended load/report — PASS.** Every successful run loaded all six Parquet tables through `analysis/load.py`; `analysis/report.py` produced the 20-run report at `reports/stage0_batch_report.md` without manual data repair.
4. **Byte-identical deterministic Parquet — PASS.** Two independent short runs with identical seed/config produced exact byte equality for every raw Parquet file and the same aggregate SHA-256 digest: `12a44d46117095bef4502f32e0cabf111578fd904b34b8cc517e4a2f3207fb66`.

### Correctness and engineering

- Invariant violations: **0**; all 20 acceptance `invariant_log.jsonl` files were empty (0 bytes total).
- Tests: **24 passed**.
- Strict typing: `mypy --strict soup analysis` passed with **0 errors**.
- Golden short-run raw-Parquet digest: `f5cbbe69c6083390556a74c11a1ff68df6d58bd2b87105a1d767dc6e139a7906`.
- Plain-Python benchmark: **4,187,804 instruction-steps/s** (12,488,236 steps in 2.982 s), above the pre-Stage-2 target of 100,000/s. No JIT optimization was used.
- Acceptance run wall times under eight-way parallel load: min **505.52 s**, median **2,176.21 s**, max **5,624.07 s**. The wide range came from tapes entering long loops and consuming the full execution budget; this is substrate behavior, not scheduler nondeterminism.

### Diagnosis and surprise

The negative emergence result is not quantitatively comparable to the paper's ~40% result. The paper's usual soup contains **2^17 = 131,072 tapes** and executes a shuffled set of roughly population/2 disjoint interactions per epoch. The tractable Stage 0 config here contains 256 tapes and executes 256 with-replacement interactions per epoch: about **5.12 million interactions/run**, versus roughly **1.05 billion** in a 16,000-epoch paper run. The prompt did not specify Stage 0 population size or pairing-round cardinality. The lack of diversity collapse is therefore most plausibly an underpowered protocol mismatch, though it could still expose a semantic issue not covered by the paper/source verification.

No parameters were changed and no runs were discarded after observing the failure.

### What I would change (pending user decision)

Before Stage 1, choose one of:

1. define a feasible Stage 0 acceptance baseline for the 256-tape plain-Python soup;
2. reproduce the paper protocol exactly (131,072 tapes, shuffled disjoint pairs, 8,192 steps), which requires a major acceleration/compute-budget exception before Stage 1; or
3. add a configurable paper-style disjoint pairing mode and run an explicitly approved population/interaction-scale sweep to determine where the emergence rate changes.

The Stage 0 gate remains closed because criteria 1 and 2 failed. No Stage 1 mechanisms have been built.
