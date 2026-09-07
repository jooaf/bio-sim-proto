# Experiment Ideas — Living Research Backlog

This document retains the historical Phase 0/1 experiment plans and now tracks newly generated work beyond the completed Stage 3 causal phase. Completed decisions belong in [`EXPERIMENTS_EXECUTED.md`](EXPERIMENTS_EXECUTED.md); an idea listed here is not active or preregistered unless a separate frozen preregistration says so.

---

## Preliminaries: what we already know

From Stage 0 findings (FINDINGS.md):

- **256-tape scale**: replication emergence is rare (1/20 runs, 5%), and diversity collapse does not occur. The soup is underpowered — there are simply not enough interactions for replicators to find and overwrite most tapes.
- **Paper scale (131,072 tapes, 65,536 disjoint pairs/tick, 16K epochs)**: replication emerges reliably (matches arXiv:2406.19108), entropy transitions sharply, and replicators take over almost the entire population.
- **Mutation rate** (`1/4096` per byte, matching the reference implementation) is important but not sufficient to overcome population-scale limitations.
- **Runtime at 256-tape scale**: ~500–5,600 s per 20K-tick run (wide variance from tape loops consuming the full 8,192-step execution budget).
- **Runtime at paper scale with the Numba probe**: ~914 s for 16K epochs (bounded aggregate logging; no detailed interaction Parquet).

**Implication for experiment design**: 256-tape sweeps are cheap enough for broad parameter exploration. Paper-scale runs are feasible for targeted confirmation of key findings but are too expensive for dense sweeps with full interaction logging.

---

## Phase 0 — Characterizing the bare BFF soup

**Goal**: Understand the baseline replication/emergence behavior of the BFF substrate before any conservation mechanisms are added. The central question: under what conditions does the soup reliably produce replicators, and what determines the speed and character of the takeover?

All Phase 0 experiments use `stage = 0`, `pairing_mode = "shuffled_disjoint"` (the paper protocol), and no conservation/energy/dissolution.

---

### Experiment P0.1 — Population-size sweep: find the emergence threshold

**Question**: What is the minimum population size at which replication reliably emerges within 20,000 ticks?

**Motivation**: Stage 0 acceptance failed at 256 tapes but succeeded at 131,072. The threshold between "almost never" and "reliably" is unknown and determines the minimum viable experiment scale.

**Parameters**:
- `world.population_size`: sweep [256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072]
- `world.interactions_per_tick`: set to `population_size // 2` (paper protocol — every tape participates exactly once per tick)
- Hold constant: `tape_length = 64`, `max_steps = 8192`, `mutation_rate = 0.000244`, `noop_density = 0.9609375`, `n_ticks = 20000`

**Metrics to record** (from the offline analysis pipeline):
| Metric | Detection method |
|---|---|
| Replication emergence (binary) | `detect_replications()` in `analysis/report.py` — any exact copy event where B's post-hash equals A's pre-hash |
| First replication tick | min tick from replication events |
| Peak replicator abundance | max `count` in `population` table for the replicator hash |
| Final replicator fraction | `count / population_size` at last epoch for the most abundant hash |
| Distinct-hash collapse | ratio of final to peak `content_hash` count in population table |
| High-order entropy | `soup_high_order_entropy()` in `analysis/complexity.py` (the paper's transition metric) |
| Hill q=0,1,2 diversity | `epoch_hill_numbers()` in `analysis/diversity.py` |

**What to expect**: Emergence probability should increase with population size, likely crossing 50% somewhere in the 4,096–16,384 range. Below that, replicators may form but cannot spread because they encounter themselves too infrequently (at 256 tapes, a replicator that makes one copy per tick needs many ticks to saturate). The paper-scale regime may show a threshold where behavior shifts from "sporadic emergence" to "reliable takeover."

**What would be surprising**: If emergence probability is non-monotonic (e.g., peaks at an intermediate size and drops again), or if the threshold is much higher than 16,384. Also surprising: if even 131,072-tape runs sometimes fail to produce replicators within 20K ticks.

**Runtime estimate**: At the Numba probe scale, ~30–60 minutes per data point for the largest sizes. Use the Numba probe for sizes ≥ 16,384; use the detailed Python logger for ≤ 8,192 (where full interaction Parquet is still feasible). For the sweep, do 5 seeds per size at the fast sizes and 3 seeds at the large ones.

**Sweep spec**:
```toml
[sweep]
name = "p0.1_population_threshold"
base_config = "experiments/configs/stage0.toml"
n_seeds = 5
processes = 8
output_dir = "sweeps"

[parameters]
world.population_size = [256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072]
```

---

### Experiment P0.2 — Tape-length sweep: does shorter or longer promote emergence?

**Question**: How does tape length affect replication emergence and the resulting replicator size?

**Motivation**: Longer tapes mean more substrate for self-modification but also more bytes that must be correctly copied. Shorter tapes mean less room for a replicator but faster copying. The literature says replicators shrink (Amoeba, Stringmol, evoloops), but we don't know the initial-length sweet spot for emergence.

**Parameters**:
- `substrate.tape_length`: sweep [16, 32, 64, 96, 128, 256]
- `substrate.max_steps`: scale proportionally — `tape_length * 128` (maintains the same per-byte budget ratio)
- `world.population_size`: 4096 (chosen to be above the expected emergence threshold from P0.1)
- Hold constant: `mutation_rate = 0.000244`, `noop_density = 0.9609375`, `n_ticks = 20000`

**Metrics**: Same as P0.1, plus:
- **Replicator length**: `length_nonzero` from the `tapes` table for the dominant replicator hash, or `np.count_nonzero` of the hash's tape bytes
- **Replicator instruction count**: number of non-noop bytes in the dominant replicator (inferred from byte values < 256 that match BFF instructions)
- **Time to first replication vs tape length**: does longer tape slow emergence linearly or super-linearly?

**What to expect**: Emergence should be fastest at intermediate lengths. Too short (16–32 bytes) and there isn't enough genomic real estate for a self-copy loop; too long (>128) and the search space for a working replicator grows combinatorially, and each replication event takes more steps. The resulting replicators should use fewer bytes than the tape length (they need only a copy loop, not the full tape).

**What would be surprising**: If tape_length=16 still produces replicators, or if tape_length=256 produces replicators *faster* than 64 (suggesting more genomic search space helps rather than hurts). If the emergent replicators use the full tape length rather than a compact subset.

**Runtime estimate**: 256-tape Python runs at ~2,000 s median for 20K ticks. At 4,096 tapes, each run will be proportionally longer. Use the Numba probe for this sweep (~5 min per run at 4,096 tapes); 6 values × 5 seeds = 30 runs, ~2.5 hours total at paper-probe speed.

---

### Experiment P0.3 — Mutation-rate sweep: the Goldilocks zone

**Question**: What mutation rate maximizes emergence probability and steady-state diversity?

**Motivation**: The reference implementation uses `1/4096` per byte per interaction. Too little mutation and the soup freezes once a replicator takes over. Too much and replication fidelity is destroyed. Understanding the tolerance band tells us how carefully this parameter must be tuned in later stages.

**Parameters**:
- `world.mutation_rate`: sweep [0.0, 0.000061, 0.000122, 0.000244, 0.000488, 0.000977, 0.001953, 0.003906, 0.007812, 0.015625]
  - These are powers of 2 around the reference rate, covering "no mutation" to "64× reference"
- `world.population_size`: 4096 (from P0.1 expectation)
- Hold constant: `tape_length = 64`, `max_steps = 8192`, `noop_density = 0.9609375`, `n_ticks = 20000`

**Metrics**: Same as P0.1, plus:
- **Final diversity**: Hill q=1 (exponential Shannon) at the last epoch
- **Replicator takeover speed**: ticks from first replication to 50% population, as a function of mutation rate
- **Replicator mutation rate**: fraction of replication events where the copy is inexact (B's post-hash ≠ A's pre-hash)
- **Post-takeover dynamics**: does the population remain monodominant or does it diversify?

**What to expect**: A non-monotonic curve. Zero mutation should produce the fastest takeover but the least diversity. The reference rate (`1/4096`) likely sits near the sweet spot. Above ~0.008 (1/128), replication should break down — mutations destroy the copying machinery faster than it can copy itself. The shape of the diversity-vs-mutation curve is the main deliverable.

**What would be surprising**: If mutation rate has no effect below some very high threshold, or if zero-mutation soups don't produce replicators (which would suggest the reference implementation's mutation masks a substrate bug). If high mutation produces *more* replicator variants that coexist rather than destroying replication.

**Runtime estimate**: 10 values × 5 seeds = 50 Numba-probe runs at ~5 min each ≈ 4 hours.

---

### Experiment P0.4 — Noop-density sweep: how sparse can the instruction set be?

**Question**: At what noop density does replication stop emerging, and does lower density produce more complex replicators?

**Motivation**: The reference uses 246/256 ≈ 96.1% noop density — only ~2.5 instruction bytes per 64-byte tape. This seems incredibly sparse, but it works because the BFF instruction set is Turing-complete with just a handful of instructions. Lower noop density means more instructions per tape, which could enable more complex programs but also more chaos. The question is whether there's a floor below which replication stops, and whether complexity scales with instruction density.

**Parameters**:
- `substrate.noop_density`: sweep [0.80, 0.85, 0.90, 0.92, 0.94, 0.96, 0.98, 0.99, 0.995]
- `world.population_size`: 4096
- Hold constant: `tape_length = 64`, `max_steps = 8192`, `mutation_rate = 0.000244`

**Metrics**: Same as P0.1, plus:
- **Mean tape execution steps per interaction** (from `interactions.steps`): higher at low noop density (more instructions executed before halt)
- **Replicator instruction density**: fraction of the replicator's bytes that are BFF instructions vs. noops
- **Halt reason distribution**: `pc_overrun` vs. `budget_exhausted` — lower noop density may trigger more pc_overrun from runaway instruction pointers

**What to expect**: Replication should fail below some threshold — perhaps 0.85–0.90 — because tapes become too chaotic. Above the reference 0.96, emergence should still work but replicators may be harder to find (fewer instruction bytes to work with). The reference density is probably near-optimal: enough instructions for a copy loop, not so many that the soup is noise.

**What would be surprising**: If replication works reliably at noop_density=0.80 (meaning the BFF instruction set is more robust than expected to instruction noise). Or if no replicators emerge at noop_density=0.99, suggesting a minimum of ~1 instruction byte per tape is needed.

**Runtime estimate**: 9 values × 5 seeds = 45 Numba-probe runs ≈ 3.5 hours.

---

### Experiment P0.5 — max_steps sweep: the execution-budget sensitivity

**Question**: How does the per-interaction execution budget affect replication emergence and the character of replicators?

**Motivation**: The reference uses 8,192 steps per interaction. Longer budgets let more complex programs execute but also let runaway loops burn more time. If the budget is too short, replicators may not finish copying before they halt. If too long, non-replicators may waste compute. This is an engineering parameter with scientific consequences.

**Parameters**:
- `substrate.max_steps`: sweep [256, 512, 1024, 2048, 4096, 8192, 16384, 32768]
- `world.population_size`: 4096
- Hold constant: `tape_length = 64`, `mutation_rate = 0.000244`, `noop_density = 0.9609375`

**Metrics**: Same as P0.1, plus:
- **Mean steps per interaction** vs. max_steps — does it saturate or grow proportionally?
- **Halt reason distribution**: `budget_exhausted` should dominate at low max_steps; `pc_overrun` at high max_steps
- **Replicator step efficiency**: steps used by replication interactions vs. non-replication interactions

**What to expect**: A threshold around 1,024–2,048 steps below which replicators cannot complete a full copy loop. Above the threshold, emergence should be reliable. The reference 8,192 is generous; the interesting question is whether it's *necessary* or just *safe*. If replicators work at 2,048 steps, that's 4× faster runs for free.

**What would be surprising**: If max_steps=256 still produces replicators (meaning replicators can copy 64 bytes in <256 steps, which is ~4 steps/byte — possible for a tight loop). Or if max_steps has no effect above the threshold (suggesting the budget is never the bottleneck).

**Runtime estimate**: 8 values × 5 seeds = 40 runs. Wall time scales roughly linearly with max_steps, so the 32,768-step runs will be longest. Budget ~6 hours total.

---

### Experiment P0.6 — Pairing-mode comparison: with_replacement vs. shuffled_disjoint

**Question**: Does the pairing protocol meaningfully affect emergence dynamics and diversity?

**Motivation**: The paper uses shuffled disjoint pairs (every tape participates exactly once per tick). With-replacement sampling (each pair drawn independently) is simpler but lets some tapes interact many times while others sit idle. This experiment quantifies the difference and validates that the protocol choice doesn't create artifacts.

**Parameters**:
- `world.pairing_mode`: ["with_replacement", "shuffled_disjoint"]
- `world.population_size`: sweep [256, 1024, 4096] (interaction to see if the effect scales)
- For `with_replacement`: `interactions_per_tick = population_size // 2` (same raw interaction count)
- For `shuffled_disjoint`: `interactions_per_tick = population_size // 2`
- Hold constant: `tape_length = 64`, `max_steps = 8192`, `mutation_rate = 0.000244`, `noop_density = 0.9609375`, `n_ticks = 20000`

**Metrics**: Same as P0.1, plus:
- **Per-tape interaction count distribution**: from the `interactions` table, count interactions per tape ID per epoch. With-replacement will have a binomial distribution; shuffled_disjoint will be exactly uniform.
- **Replicator spread speed**: ticks from first replication to X% of population, comparing protocols

**What to expect**: At large population sizes, the difference should be minimal — a binomial with N=pop_size/2 and p=2/pop_size is approximately uniform. At small sizes (256), with-replacement may show more variance. Shuffled_disjoint is the scientifically cleaner protocol; this experiment determines whether it matters.

**What would be surprising**: If with_replacement produces systematically different emergence rates or diversity trajectories. If the replicator that "wins" differs between protocols (suggesting stochastic effects from uneven interaction exposure matter).

**Runtime estimate**: 2 protocols × 3 sizes × 5 seeds = 30 Python-logger runs. Budget ~4–6 hours.

---

### Experiment P0.7 — Time-to-emergence distribution at paper scale

**Question**: What is the distribution of first-replication times at paper scale, and does it have a characteristic timescale?

**Motivation**: The FINDINGS.md reports first replication at epoch 2,433 for seed 0 at paper scale. But we only have one data point. The emergence time distribution tells us whether there's a narrow window (deterministic process) or a broad tail (stochastic rare event). This matters for designing later-stage experiments — if emergence can take anywhere from 1,000 to 50,000 epochs, we need to budget for the worst case.

**Parameters**:
- `world.population_size`: 131072
- `world.interactions_per_tick`: 65536
- Hold constant: `tape_length = 64`, `max_steps = 8192`, `mutation_rate = 0.000244`, `noop_density = 0.9609375`, `n_ticks = 20000`
- **Seeds**: 0–29 (30 independent runs)

**Metrics** (from the Numba probe's aggregate output):
- **First-replication tick** (first tick where high-order entropy exceeds 1 bit/byte)
- **Transition entropy**: the entropy value at the transition point
- **Final entropy**: entropy at tick 20,000
- **Post-transition minimum entropy**: the lowest entropy after transition (measuring takeover completeness)

**What to expect**: Per arXiv:2406.19108, ~40% of runs produce replicators within 16K epochs. With the corrected protocol, we may see higher emergence rates (the paper's 40% may reflect pre-correction protocol). Times should be roughly log-normally distributed if emergence is a multiplicative rare-event process. The median may be around 3,000–5,000 epochs.

**What would be surprising**: If all 30 runs produce replicators (100% emergence, suggesting the 40% figure in the paper is an undercount from protocol differences). If emergence times are bimodal (suggesting two distinct pathways to replication). If some runs fail to produce replicators at all within 20K ticks.

**Runtime estimate**: 30 Numba-probe runs at ~15 min each = 7.5 hours wall time (can parallelize across 8 cores). Or use the compute-efficient approach: run them sequentially on one core (~7.5 hours).

---

### Experiment P0.8 — Replicator phenotype census

**Question**: What do the emergent replicators actually look like? Are they diverse in structure, or is there one dominant replicator architecture?

**Motivation**: The paper reports a functional self-replication score but doesn't deeply characterize the replicator phenotypes. Understanding the diversity (or lack thereof) of replicator architectures tells us whether the soup finds one solution or many, which bears on whether later stages have anything to act on.

**Parameters**:
- Run the paper-scale probe for 30 seeds (same as P0.7)
- At the first-transition checkpoint and at the end, extract the top-100 most abundant tapes

**Metrics** (computed offline from saved tape snapshots):
| Metric | Method |
|---|---|
| Replicator length (nonzero bytes) | `np.count_nonzero(tape)` |
| Instruction bytes used | count of bytes in `{0x3C, 0x3E, 0x7B, 0x7D, 0x2D, 0x2B, 0x2E, 0x2C, 0x5B, 0x5D}` |
| Copy-loop detection | scan for bracket pairs `[...]` with internal `.<>` or `,{}` patterns |
| Byte-histogram pairwise distance | Jensen-Shannon divergence between replicator byte histograms |
| Pairwise normalized compression distance (NCD) | `zlib.compress(A+B)` vs `min(zlib(A), zlib(B))` |
| Cluster count (phenotype families) | DBSCAN on NCD matrix |

**What to expect**: One or a few dominant replicator architectures across all seeds. The BFF substrate may constrain the design space enough that all working replicators are variants of the same basic copy-loop pattern. If multiple architectures exist, they may fall into 2–3 families (e.g., head-0-based copiers vs. head-1-based copiers).

**What would be surprising**: If every seed produces a structurally distinct replicator (suggesting a vast design space). If replicators do not contain a recognizable copy loop (suggesting non-trivial self-reproduction mechanisms). If replicators contain large no-op regions that are faithfully preserved (suggesting junk DNA-like dynamics).

**Runtime estimate**: Analysis-only; the runs are already done from P0.7. Budget ~1 hour of offline analysis coding.

---

## Phase 1 — Symbol conservation

**Goal**: Understand how the global symbol pool changes the dynamics established in Phase 0. The central questions: does conservation cause growth saturation, does it create acquire/decompose patterns, and does it alter the minimization trajectory?

All Phase 1 experiments use `stage = 1`, which enables the `SymbolPool` with pool-mediated writes. Energy, dissolution, and space remain disabled.

**Key Phase 1 concepts**:
- **Blocked write**: a `+`, `-`, `.`, or `,` instruction that cannot execute because the target byte value has zero pool count. Blocked writes are logged per-interaction (`writes_blocked`) and per-tick (`n_writes_blocked`).
- **Pool entropy**: Shannon entropy of the pool's byte distribution — declines when some byte values are depleted.
- **Saturation**: when population growth (or tape-content turnover) stalls because the pool cannot supply needed bytes.

---

### Experiment P1.1 — pool_multiplier sweep: the saturation curve

**Question**: How does the initial pool size affect steady-state population, diversity, and blocked-write rate?

**Motivation**: This is the foundational Phase 1 experiment. The pool_multiplier controls total available bytes: `multiplier × total_bytes_in_tapes / 256` per symbol. At multiplier=0 (pool empty), no writes can succeed — the soup freezes. At multiplier=∞ (unlimited pool), conservation is effectively off and we should recover Phase 0 behavior. The interesting physics is in between.

**Parameters**:
- `symbols.pool_multiplier`: sweep [0.1, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 64.0, 256.0]
- `world.population_size`: 4096 (above the expected emergence threshold)
- Hold constant: `tape_length = 64`, `max_steps = 8192`, `mutation_rate = 0.000244`, `noop_density = 0.9609375`, `n_ticks = 20000`, `pairing_mode = "shuffled_disjoint"`

**Metrics**:
| Metric | Detection method |
|---|---|
| Total successful writes per tick | `n_writes_success` from `ticks` table |
| Total blocked writes per tick | `n_writes_blocked` from `ticks` table |
| **Blocked-write ratio** | `n_writes_blocked / (n_writes_success + n_writes_blocked)` over time |
| Pool entropy over time | `pool_entropy` from `ticks` table |
| Pool total over time | `pool_total` from `ticks` table |
| Distinct-hash count over time | From `population` table |
| Hill q=1 diversity over time | `epoch_hill_numbers()` |
| Replication emergence (binary) | `detect_replications()` |
| Dominant hash abundance | Max `count` in `population` table |
| Per-symbol pool histogram | `pool_histogram` column — which bytes get depleted first? |

**What to expect**:
- At low multipliers (0.1–0.5): the pool is quickly exhausted, writes are mostly blocked, the soup freezes in its initial state. No replication possible.
- At intermediate multipliers (1.0–4.0): writes are periodically blocked, the pool develops a non-uniform distribution (certain bytes become scarce), population dynamics are muted.
- At high multipliers (≥16): behavior approaches Phase 0 — blocked writes are rare, replication proceeds normally.
- The saturation population (measured by turnover rate or distinct-hash count) should scale monotonically with pool_multiplier. The curve should be sigmoidal.

**What would be surprising**: If pool_multiplier=0.1 still permits replication (suggesting replication needs far fewer free bytes than expected). If the curve is non-monotonic — e.g., intermediate multipliers produce higher diversity than either extreme. If pool entropy drops uniformly across all byte values (suggesting no particular byte value is limiting) rather than selectively depleting instruction bytes.

**Runtime estimate**: 9 values × 5 seeds = 45 Python-logger runs at 4,096 tapes. At ~3,000 s median per run, budget ~37 hours. Run with `--processes 8` for ~5 hours wall time.

**Sweep spec**:
```toml
[sweep]
name = "p1.1_pool_multiplier_sweep"
base_config = "experiments/configs/stage1.toml"
n_seeds = 5
processes = 8
output_dir = "sweeps"

[parameters]
symbols.pool_multiplier = [0.1, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 64.0, 256.0]
```

---

### Experiment P1.2 — Replication under conservation: tape-length interaction

**Question**: Does symbol conservation differentially affect replication emergence at different tape lengths?

**Motivation**: Longer tapes mean more bytes to copy during replication, which means more pool withdrawals. If the pool is tight, longer replicators may be selected against even more strongly than they already are in Phase 0. This tests whether conservation intensifies the minimization attractor.

**Parameters**:
- `substrate.tape_length`: sweep [32, 64, 128]
- `symbols.pool_multiplier`: sweep [0.5, 1.0, 2.0, 4.0, 16.0] (cross with tape_length)
- `world.population_size`: 4096
- Hold constant: `max_steps = tape_length * 128`, `mutation_rate = 0.000244`, `noop_density = 0.9609375`, `n_ticks = 20000`

**Metrics**: Same as P1.1, plus:
- **Replicator length** (from `tapes` table for the dominant hash)
- **Writes per replication event**: mean `writes_success` for replication interactions vs. non-replication interactions
- **Interaction**: does the pool_multiplier × tape_length interaction predict emergence success?

**What to expect**: At the same pool_multiplier, longer tapes should experience more blocked writes (they need to withdraw more bytes from the pool per replication). This should make replication harder and slower at high tape_length × low pool_multiplier combinations. The effect should disappear at high multipliers.

**What would be surprising**: If longer tapes are *less* affected by conservation (because they have more internal byte diversity and can cannibalize their own bytes). If tape_length=32 fails to produce replicators under conservation while tape_length=64 succeeds (suggesting a minimum genomic real estate for pool-mediated replication).

**Runtime estimate**: 3 lengths × 5 multipliers × 5 seeds = 75 runs. Budget ~8–10 hours with 8-way parallelization.

---

### Experiment P1.3 — Acquire/decompose pattern detection

**Question**: Do we observe tapes acquiring bytes from other tapes and then those bytes returning to the pool, forming a nutrient cycle?

**Motivation**: Combinatory Chemistry (arXiv:2003.07916) identifies acquisition-decomposition-reassembly cycles as the signature of metabolism-like dynamics. In our system, this would manifest as bytes flowing from one tape's content into another's, with the pool mediating the exchange. This experiment does not require a positive result — detecting the *absence* of such patterns is equally informative.

**Parameters**:
- Use the P1.1 runs with `pool_multiplier ∈ {1.0, 2.0, 4.0}` (the interesting intermediate regime)
- Focus on the most active seeds

**Metrics** (computed from the `interactions` and `tapes` tables):
| Metric | Method |
|---|---|
| **Per-interaction byte flux matrix** | For each interaction, count how many old bytes from A ended up in B and vice versa. Build a 256×256 transition matrix: "byte value v in A before → byte value v' in B after" |
| **Byte residency time** | Track a byte value through time: how long does a specific byte value remain in tapes vs. the pool? Compute from `pool_histogram` time series. |
| **Recycled-byte fraction** | Fraction of successful writes where the byte value was previously in a tape (not "fresh" from initial pool). Infer from pool entropy decline: if pool entropy drops, the pool is losing diversity, meaning some byte values are being consumed and not returned. |
| **Interaction-graph byte flow** | For pairs of tapes that interact repeatedly, track net byte flow direction over time. Does tape A systematically gain bytes from B? |
| **Pool composition drift** | PCA or Jensen-Shannon divergence of `pool_histogram` snapshots at 100-tick intervals. Does the pool settle to a steady-state distribution? |

**What to expect**: At low multipliers, the pool should deplete in specific byte values (likely instruction bytes: `<`, `>`, `[`, `]`, `.`, `,`, `+`, `-`). At higher multipliers, the pool may reach a dynamic equilibrium where byte inflow (from "dead" interactions that scramble tapes) balances outflow (to replication/build events). The acquire/decompose pattern would be visible as: tape A's bytes appear in tape B after an interaction, then later re-appear in tape C, with the pool as an intermediate buffer.

**What would be surprising**: If no systematic byte flow is detectable — meaning the pool is just a uniform brake on all activity rather than a structured constraint. If certain byte values are *never* depleted (suggesting they are never used by functional programs). If the pool recovers diversity without dissolution (suggesting write-undo cycles in the substrate).

**Runtime estimate**: Analysis-only; runs already from P1.1. Budget ~2 hours of analysis coding.

---

### Experiment P1.4 — Blocked-write time-series analysis

**Question**: What is the temporal structure of blocked writes? Are they smooth, bursty, or periodic?

**Motivation**: Blocked writes are the primary scarcity signal. Their temporal pattern reveals whether the pool is a gentle constraint or a hard wall. Bursty blocking suggests replicator boom-bust cycles; smooth blocking suggests equilibrium; periodic blocking suggests some endogenous oscillator.

**Parameters**:
- Same runs as P1.1, focusing on `pool_multiplier ∈ {0.5, 1.0, 2.0, 4.0}`
- One paper-scale run at `pool_multiplier = 2.0` to check for scale effects

**Metrics**:
| Metric | Method |
|---|---|
| Blocked-write rate time series | `n_writes_blocked / (n_writes_success + n_writes_blocked)` per tick, from `ticks` table |
| Burstiness index | Coefficient of variation of inter-blocked-write intervals. CV > 1 = bursty. |
| Autocorrelation of blocked-write rate | ACF at lags 1–100 ticks |
| Cross-correlation with distinct-hash count | Does blocking precede or follow diversity changes? |
| Blocked-write per-byte-value time series | Requires extending the logger to record per-byte blocked writes (or inferring from pool_histogram changes) |

**What to expect**: At low multipliers: high blocking rate from the start, smooth decay as the pool stabilizes. At intermediate multipliers: blocking should be low initially, then spike when replication emerges (replicators consume the specific bytes they're made of), then decline as the system reaches equilibrium. At the paper scale with multiplier=2.0, the pool is large enough that blocking may never be the dominant constraint.

**What would be surprising**: If blocking is periodic with a characteristic frequency (suggesting an endogenous replication-blocking cycle — a predator-prey dynamic with the pool as the "prey"). If blocking *never* occurs except at the lowest multipliers (suggesting the pool is too generous at default settings). If blocking is concentrated on non-instruction bytes (suggesting replicators are optimizing byte usage around pool constraints).

**Runtime estimate**: Analysis-only. Budget ~1 hour.

---

### Experiment P1.5 — Does conservation intensify minimization?

**Question**: Does symbol conservation make the minimization attractor stronger (replicators shrink faster) or weaker (small replicators can't acquire enough bytes)?

**Motivation**: The design brief identifies minimization as the dominant failure mode of program soups. Conservation *should* counter it because replication requires acquiring specific bytes, and small replicators may need proportionally more pool withdrawals. But conservation could also *intensify* it because shorter replicators require fewer bytes and are thus less pool-constrained. This experiment resolves the ambiguity.

**Parameters**:
- Compare Phase 0 (pool_multiplier = ∞, effectively) vs. Phase 1 at `pool_multiplier ∈ {1.0, 2.0, 4.0}`
- `world.population_size`: 4096
- Run for 50,000 ticks (longer than standard, to give minimization time to act)

**Metrics**:
| Metric | Method |
|---|---|
| **Mean tape nonzero length over time** | `length_nonzero` from `tapes` table, averaged across population |
| **Replicator length trajectory** | For the dominant replicator hash, track its `length_nonzero` at each snapshot |
| **Mean tape instruction count over time** | From `byte_histogram`, sum counts for the 10 BFF instruction bytes |
| **Distinct-hash count** | From `population` table |
| **Hill q-profile over time** | `epoch_hill_numbers()` |

**What to expect**: Two competing hypotheses:
1. Conservation intensifies minimization: replicators that use fewer bytes experience fewer blocked writes, so they replicate faster. Mean tape length drops faster under conservation.
2. Conservation retards minimization: beyond a point, shorter tapes can't perform the copy loop (they need at least ~5–10 instruction bytes), and the pool constraint is binding on all tapes, so minimization provides no relative advantage.

The actual result is genuinely unknown and worth reporting either way.

**What would be surprising**: If mean tape length *increases* under conservation (suggesting the pool rewards tapes that can capture diverse bytes). If the replicator length trajectory is non-monotonic (shrinks then grows). If conservation produces a bimodal length distribution (some very short replicators, some very long non-replicators).

**Runtime estimate**: 4 conditions × 5 seeds × 50K ticks = 20 long runs. Using the Numba probe for speed. Budget ~8 hours with parallelization.

---

### Experiment P1.6 — Initial pool distribution: uniform vs. tape-matched

**Question**: Does the initial pool composition (uniform across all byte values vs. matching the initial tape distribution) affect dynamics?

**Motivation**: The current initializer creates the pool proportional to the initial tape byte histogram, then draws tapes from the pool. This means the pool is "pre-adapted" to the initial population. An alternative is a uniform pool (equal count of every byte value), which would create immediate selective pressure for tapes that use "available" bytes. This experiment tests whether the initialization scheme matters.

**Parameters**:
- Add a config flag for pool initialization mode (requires minor code change to `SymbolPool.from_tapes` to accept a `uniform` option)
- Compare `uniform` vs. `histogram_matched` at `pool_multiplier ∈ {1.0, 2.0, 4.0, 16.0}`
- `world.population_size`: 4096

**Metrics**: Same as P1.1, plus:
- **Early-tick pool entropy trajectory**: does the uniform pool rapidly converge to the histogram-matched distribution, or does it stay different?
- **Early-tick blocked-write rate**: expected to be higher for uniform pool (initial tapes contain bytes the pool doesn't have in abundance)

**What to expect**: The uniform pool should cause higher blocking in the first few thousand ticks, then converge toward the histogram-matched distribution as tapes die/scramble and return bytes to the pool. Long-term dynamics should be similar.

**What would be surprising**: If the initial pool composition determines the long-term attractor (path dependence). If uniform pools support higher diversity because no byte value is initially scarce. If histogram-matched pools show faster emergence because they start with "the right" bytes available.

**Runtime estimate**: Requires a small code change to `SymbolPool`. Then 2 modes × 4 multipliers × 5 seeds = 40 runs. Budget ~5 hours wall time.

---

### Experiment P1.7 — Population-size interaction with conservation

**Question**: How does the emergence threshold identified in P0.1 shift under conservation?

**Motivation**: In Phase 0, replication emergence becomes reliable above some population size (estimated 4,096–16,384 from P0.1). Conservation adds a pool-size constraint that scales with population: `pool_size = multiplier × population_size × tape_length / 256` per symbol. So larger populations have larger pools. Does the emergence threshold move up, down, or stay the same?

**Parameters**:
- `world.population_size`: sweep [256, 512, 1024, 2048, 4096, 8192, 16384]
- `symbols.pool_multiplier`: 2.0 (the default)
- Hold constant: `tape_length = 64`, `max_steps = 8192`, `mutation_rate = 0.000244`, `noop_density = 0.9609375`

**Metrics**: Same as P0.1 (replication emergence, abundance, diversity collapse), plus blocked-write rate and pool entropy.

**What to expect**: The emergence threshold should be similar to or slightly higher than Phase 0. At small populations, the pool is small enough that conservation is noticeable. At large populations, the pool is large and conservation is a weak constraint. The threshold may not shift much from Phase 0.

**What would be surprising**: If the emergence threshold drops substantially (conservation somehow promotes replication), or if it rises dramatically (conservation is a hard barrier even at large scales).

**Runtime estimate**: 7 sizes × 5 seeds = 35 runs. Use Numba probe for ≥ 4,096. Budget ~5 hours wall time.

---

### Experiment P1.8 — Pool exhaustion and recovery: no-reseed death test

**Question**: If the pool is exhausted, does the soup ever recover, or does it stay dead?

**Motivation**: In Phase 0 the population is fixed; in Phase 1, tapes can theoretically "die" by having all their bytes consumed, but death isn't implemented until Stage 2 (dissolution). Without death, pool exhaustion means the soup freezes permanently — a world of 256-tape "zombies" that can't change. This experiment intentionally triggers pool exhaustion to characterize the freezing transition and confirm it's irreversible without dissolution.

**Parameters**:
- `symbols.pool_multiplier`: [0.05, 0.1, 0.2, 0.35, 0.5] (very low, to induce exhaustion)
- `world.population_size`: 256 (small, so runs are fast)
- `n_ticks`: 10000 (enough to see exhaustion and post-exhaustion behavior)
- Hold constant: `mutation_rate = 0.000244`, `noop_density = 0.9609375`

**Metrics**:
| Metric | Method |
|---|---|
| Tick of pool exhaustion | First tick where `pool_total < threshold` (e.g., < 1% of initial) |
| Writes per tick before/after exhaustion | From `ticks` table |
| Tape content change post-exhaustion | Fraction of tapes with unchanged `content_hash` for the last N ticks |
| Pool entropy at exhaustion | Is exhaustion selective (low entropy) or uniform (high entropy)? |
| Which byte values go to zero first? | From `pool_histogram` time series |

**What to expect**: At the lowest multipliers, the pool should be exhausted within a few hundred ticks. After exhaustion, writes are 100% blocked, tapes never change, and the simulation is computationally idle. This is a clean calibration of the point at which dissolution becomes necessary (Stage 2).

**What would be surprising**: If the soup *recovers* from exhaustion — e.g., if interactions that scramble tapes (without pool-mediated writes) somehow return bytes to the pool. This would indicate a bug or an unanticipated substrate dynamic. If the pool is never fully exhausted even at multiplier=0.05 (suggesting the system finds an equilibrium with very low pool levels).

**Runtime estimate**: 5 values × 3 seeds = 15 fast runs at 256 tapes. Budget ~1 hour.

---

## Cross-cutting experimental design notes

### When to use the Numba probe vs. the full Python logger

| Scale | Tool | What you get | Limitation |
|---|---|---|---|
| ≤ 8,192 tapes | Full Python logger | Complete interaction Parquet, tape snapshots, population census | Disk I/O; ~5 GiB per 20K-tick run at 256 tapes |
| ≥ 16,384 tapes | Numba probe | Aggregate entropy, epoch summaries, tape snapshots at transitions | No per-interaction records; can't detect replication from hashes offline |
| Paper scale (131K) | Numba probe only | Entropy trajectory, transition detection, checkpoint saves | No detailed analysis possible without re-running a window with the logger |

**Recommendation**: Use the Python logger for Phases 0–1 sweeps at ≤ 4,096 tapes (the expected emergence threshold). Use the Numba probe for confirmation at larger scales. For P0.7 and P0.8, use the Numba probe with checkpoint saves.

### Deterministic seeding strategy

The experiment runner already supports `--n-seeds` with sequential seeds from `--start-seed`. For all sweeps:
- Use seeds 0–(n_seeds−1) for the primary sweep
- If a parameter cell shows anomalous behavior, add seeds 100–104 as a targeted follow-up

### Logging configuration

For sweeps, set `logging.interaction_log_rate` appropriately:
- Phase 0 sweeps at ≤ 4,096 tapes: `interaction_log_rate = 1.0` (keep all interactions)
- Larger-scale runs: `interaction_log_rate = 0.01` (sample 1% of interactions) if using the Python logger
- For the Numba probe, interaction logging is not applicable

### Analysis deliverables for each experiment

Each experiment should produce:
1. A summary CSV or Parquet file with one row per (parameter combination, seed)
2. A markdown report with key plots and statistical tests
3. Raw run directories for reproducibility

### Statistical rigor

For sweep experiments with ≥ 5 seeds per cell:
- Report means with 95% bootstrap confidence intervals
- Use Mann-Whitney U for pairwise comparisons (emergence is not normally distributed)
- Use Spearman rank correlation for monotonic relationships (e.g., pool_multiplier vs. saturation population)
- Explicitly report non-significant results rather than omitting them

---

## Priority ordering

If compute budget is limited, run experiments in this order:

**Phase 0 (must-do)**:
1. **P0.1** — Population-size sweep (foundational; determines scale for all other experiments)
2. **P0.3** — Mutation-rate sweep (calibrates a key parameter for later stages)
3. **P0.7** — Time-to-emergence distribution (characterizes the baseline for Phase 1 comparisons)

**Phase 0 (nice-to-do)**:
4. **P0.4** — Noop-density sweep
5. **P0.2** — Tape-length sweep
6. **P0.5** — max_steps sweep
7. **P0.6** — Pairing-mode comparison
8. **P0.8** — Replicator phenotype census

**Phase 1 (must-do)**:
1. **P1.1** — pool_multiplier sweep (foundational for Phase 1)
2. **P1.5** — Does conservation intensify minimization? (directly addresses the design brief's core concern)
3. **P1.3** — Acquire/decompose pattern detection (the signature of metabolism)

**Phase 1 (nice-to-do)**:
4. **P1.2** — Tape-length interaction with conservation
5. **P1.4** — Blocked-write time-series analysis
6. **P1.8** — Pool exhaustion test
7. **P1.7** — Population-size interaction with conservation
8. **P1.6** — Initial pool distribution comparison

---

## What success looks like

By the end of Phase 0 experiments, we should be able to state:
- The minimum population size for reliable replication emergence
- The mutation-rate range that supports replication
- The noop-density range that supports replication
- The characteristic timescale for replication emergence
- Whether the pairing protocol matters
- The diversity of replicator architectures

By the end of Phase 1 experiments, we should be able to state:
- How pool_multiplier controls the saturation behavior
- Whether blocked writes are bursty or smooth
- Whether acquire/decompose patterns are detectable
- Whether conservation intensifies or retards minimization
- What the pool exhaustion threshold is
- Whether the Phase 0 emergence threshold shifts under conservation

---

## Stage 4 frontier — behaviorally accessible energy and ecology

These ideas were generated from the completed Stage 3 results. Stage 3 established exact matter/energy accounting, vacancy-controlled lineage clustering, and energy-constrained **scheduled** birth. It also produced three constraints that Stage 4 must respect: byte-exact BFF copy triggers were absent, continued scheduled birth clogged at 20,000 ticks, and empirical organizations occurred in only 5/15 windows. None of the ideas below may retroactively rescue those NO-GOs.

### S4-I001 — Active energy-uptake positive control

**Question:** Can tape execution, rather than passive occupancy, control access to environmental energy?

**Mechanism idea:** Reserve one currently inert BFF byte as an energy-uptake instruction. Execution transfers a bounded amount from the active tape’s local field cell into that tape, pays an instruction cost, and cannot create energy. Disable passive absorption in the treatment. The exact opcode, transfer cap, seeds, and positive-control tape must be frozen before outcomes are inspected.

**First test:** A mutation-free mechanics assay comparing a deliberately seeded uptake-capable tape with a byte-matched no-uptake control under the same field. Require exact energy balance, nonzero uptake only after opcode execution, and no effect when the feature is disabled.

**Why now:** Uniform passive absorption made energy explicit but could not create differentiated ecological roles.

### S4-I002 — Structured energy-field scale

**Question:** Once uptake is behaviorally accessible, does spatial resource structure generate stable local energy niches?

**Mechanism idea:** Replace uniform influx with a normalized static patch field whose total influx is unchanged. Compare a small preregistered set of correlation lengths spanning below, near, and above the radius-1 interaction scale. Do not select a field by lineage or organization outcomes.

**Endpoints:** Energy acquisition inequality, uptake-event spatial autocorrelation, tape-energy distance decay, occupancy/liveness, and opcode-composition locality. Organization and lineage outcomes remain confirmatory follow-ups, not field-selection metrics.

**Prerequisite:** S4-I001 must provide a viable uptake positive control.

### S4-I003 — Conserved decomposition/predation transaction

**Question:** Can an executed action reclaim a neighbor’s symbols and thereby produce an auditable trophic interaction?

**Mechanism idea:** Add an explicit local decomposition instruction or interaction result that atomically dissolves a target, returns all target bytes to the conserved pool, dissipates or transfers energy by a frozen ledger rule, and records actor/target lineage facts. Failed eligibility must leave both ledgers unchanged.

**Positive controls:** A seeded decomposer must act on an eligible target but not on an ineligible/no-op target. The first campaign is mechanics-only and cannot be called predation until actor-dependent resource acquisition is demonstrated.

**Endpoints:** Directed decomposition graph, actor energy change, reclaimed-symbol flow, target mortality, and mass/energy residuals.

### S4-I004 — Mechanistic population regulation

**Question:** Can resource-limited birth plus starvation/decomposition prevent the continued-birth clog observed at 20,000 ticks?

**Test idea:** After S4-I001 or S4-I003 passes, compare the new resource-coupled ecology with its disabled-mechanism control at the already selected Stage 3 birth settings. Use the original 0.95 occupancy ceiling and a frozen 20,000-tick horizon.

**Rule:** Do not lower the prior birth rate or raise the occupancy ceiling. A pass must come from the newly motivated regulation mechanism, not parameter rescue.

### S4-I005 — Organization-analysis positive-control benchmark

**Question:** Does the empirical organization pipeline recover known persistent organizations and reject matched non-organized reaction streams?

**Test idea:** Feed the unchanged composition-reaction analyzer synthetic balanced cycles, deliberately leaky cycles, count-imbalanced components, and time-shuffled controls at campaign-scale sample counts. Then evaluate a separately established artificial-chemistry organization if a compatible trace is available.

**Purpose:** Calibrate sensitivity and false-positive behavior before any new simulator organization claim. This does not reopen the failed Stage 3 prevalence endpoint.

### S4-I006 — Independently viable replication substrate in the conserved spatial world

**Question:** Does an independently demonstrated copying chemistry retain viable reproduction when coupled to exact matter and energy accounting?

**Candidate direction:** Use a substrate with a preregistered exact-copy positive control—such as the pinned Stringmol mechanism or a validated primordial-soup Forth copier—rather than tuning BFF after its zero-trigger result.

**Required separation:** First establish copying under the substrate’s native semantics, then add conservation, then energy. External Stringmol parasite containment remains external evidence until the mechanism is actually integrated.

### S4-I007 — Patch decay under successful population regulation

**Question:** If S4-I004 prevents clogging and raises turnover, do lineage patches still persist after their causal birth input stops?

**Test idea:** Reuse the frozen modulo-family and exact-root measurements, switch birth off at a preregistered checkpoint, and retain the prior 0.95 occupancy ceiling. This is a new mechanism test, not a rerun or reinterpretation of the Stage 3 persistence NO-GO.

## Stage 4 priority and dependencies

1. **S4-I001** — active uptake mechanics and positive control.
2. **S4-I003** — explicit decomposition transaction.
3. **S4-I004** — test whether those mechanisms regulate population without tuning the failed Stage 3 campaign.
4. **S4-I002** — structured field scale, only after active uptake is viable.
5. **S4-I005** — organization-analysis calibration before another organization claim.
6. **S4-I006** — independently viable replication substrate; separate model-development track.
7. **S4-I007** — lineage persistence only after regulation passes.

## Explicitly closed or deferred ideas

- Do not weaken or extend the frozen BFF exact-copy trigger campaign.
- Do not change the Stage 3 organization species definition, windows, or 8/15 prevalence threshold to rescue its NO-GO.
- Do not tune the completed continued-birth arm’s rate or occupancy ceiling.
- Do not launch a 500,000-tick matched-radius run unless a future gate names a specifically temporal uncertainty that bounded experiments cannot answer.
