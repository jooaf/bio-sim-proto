# BUILD PROMPT — Conserved Program-Soup Evolution Simulator

**Paste this entire document to your coding agent as the opening message. It is the complete specification. Do not summarize it before pasting.**

---

## 0. Your role and how to work

You are building a research simulator, not a product. The user is exploring whether life-like organization — metabolism, individuality, multicellularity, and eventually signal-driven computation — can emerge from a substrate of self-modifying programs under conservation laws, without any external fitness function.

**This is a six-stage build. You must stop at the end of every stage, report against the acceptance criteria, and wait for the user before continuing.** Do not build ahead. Each stage is designed to fail cheaply if the design is wrong, and the user needs to see those failures.

Read this whole document before writing any code. Then confirm your understanding of the architecture and the Stage 0 acceptance criteria, and ask about anything genuinely ambiguous. Then begin Stage 0.

When you finish a stage, produce a short report containing: what you built, the acceptance-criteria results with actual numbers, any invariant violations, anything surprising, and what you'd change. Then stop.

---

## 1. Non-negotiable design principles

These are the scientific commitments of the project. Violating any of them makes the results meaningless. If you find yourself wanting to break one, stop and raise it instead.

**1.1 No external fitness function. Ever.** Nothing outside the world may rank, score, select, or cull organisms based on a notion of quality. There is no `fitness()`. There is no tournament, no elite archive, no MAP-Elites grid, no novelty search. If something reproduces more, it must be because the physics made it more likely to, not because a judge preferred it.

**1.2 Environmental pressure acts on interaction probability, not on selection.** When the environment "rewards" something, the mechanism is always: this program is more likely to be picked for an interaction, or has more energy to spend, or is in a richer patch. Never: this program's offspring count is multiplied by a score. (Rationale: arXiv:2607.09211 got function to co-evolve with replication using exactly this framing.)

**1.3 Conservation is an invariant, not a heuristic.** Every conserved quantity is checked with an assertion every single timestep in debug mode. A drift of even one unit is a bug and must halt the run. Conservation checks are your primary correctness instrument — they will catch more bugs than tests will.

**1.4 Log raw, compute metrics offline.** The simulator writes facts. It never writes conclusions. Diversity indices, complexity measures, and open-endedness metrics are computed by a separate analysis package reading the logs. The user will change their mind about metrics and must never need to re-run a simulation because of it.

**1.5 Locality only.** No global coordinates visible to programs, no global broadcast, no global clock that programs can read. All addressing is relative. (Rationale: Ackley's indefinite scalability argument — global structures are the thing that stops these systems scaling.)

**1.6 Every knob is in the config.** No magic numbers in the simulation code. If a value could conceivably be tuned, it lives in the config dataclass with a documented default and a documented sane range.

**1.7 Determinism.** Given a seed and a config, a run is bit-for-bit reproducible. Use one explicit `numpy.random.Generator` threaded through the simulation. Never call the global `random` module. Never iterate over a `set` or an unordered `dict` in a way that affects simulation state.

---

## 2. Scientific background — why each mechanism exists

You need this context to make good judgement calls. Each mechanism below is here to defeat a specific documented failure mode.

**The soup produces replicators easily.** Random programs in a self-modifying instruction set spontaneously produce self-replicators with no fitness function and no noise — demonstrated in Brainfuck-variant (BFF), Forth, Z80 and 8080 instruction sets (arXiv:2406.19108, "Computational Life"), and much earlier in Pargellis' Amoeba system with a 16-opcode set at ~10⁻⁴ spontaneous emergence probability. **So getting replication is not the hard part and you should not be impressed when it happens.**

**The soup then collapses to the minimal replicator.** This is the dominant failure mode of the entire substrate family. Amoeba's organisms shrank. Stringmol's replicators shrank. Sayama's evoloops "gradually evolved toward the smallest ones." Short replicators copy faster, so absent a countervailing force, everything becomes a tiny copier and nothing interesting happens again. Amoeba conserved memory and CPU time and *still* minimized, because both of those reward being small. **Every mechanism in this design exists primarily to defeat minimization.**

**Symbol conservation creates metabolism.** Combinatory Chemistry (arXiv:2003.07916) fixes the global count of each primitive symbol. From a tabula rasa start this alone produced autopoietic structures, recursive growth patterns, and self-reproducers, via a process the authors describe as "remarkably similar to biological metabolisms" — acquire constituents from the environment, decompose them, reassemble. Scarcity of *parts* is qualitatively different from scarcity of space, because it makes decomposition of others a necessary activity, which is the root of ecology.

**Energy as a separate flowing quantity forces trophic structure.** In ecosystem models, matter cycles and energy flows — the asymmetry is what creates trophic levels rather than requiring them to be designed (PMC10756307; PLOS Comp Biol 10.1371/journal.pcbi.1014330). No existing algorithmic chemistry has an energy ledger distinct from its matter ledger. This is the novel part of this design and the part most likely to produce something unpublished.

**Dissolution prevents the clog.** Sayama's evoloops only achieved genuine Darwinian evolution after adding *structural dissolution* — a rule that erases inert debris. Without it the world fills with corpses and freezes. In this design dissolution also closes the nutrient cycle, returning bytes to the pool.

**Function co-evolves with replication if you bias interaction probability.** arXiv:2607.09211 (2026) initialized random 32-byte Z80 programs and made correct polynomial evaluation raise a program's interaction probability above baseline. Replication and problem-solving co-evolved from randomness, the pressure to compute *accelerated* the emergence of compact reproductive architectures, and programs evolved to preserve memory regions for task execution — a proto germ/soma split.

**Multicellularity needs a signal legible only above the individual scale.** DISHTINY (Moreno & Ofria, Artificial Life 2019) got reproductive division of labor, cell–cell messaging, morphological patterning and adaptive apoptosis by making resources fluctuate spatiotemporally such that coordinated groups harvest better than individuals. The eLife 2020 multicellularity paper found the same principle via gradients too large for one cell to resolve. **The lever is the correlation length of the environmental field relative to organism size.**

**Task-switching cost is the cheapest division-of-labor lever known.** Goldsby et al., PNAS 2012: impose a time cost on switching between tasks and genetically identical organisms specialize, share results by message, and lose the ability to replicate alone. One parameter, and you get an obligate transition in individuality.

**Define the organism, don't assume it.** Chemical Organization Theory (Dittrich & Speroni di Fenizio) defines an organization as a set of species that is algebraically closed and stoichiometrically self-maintaining. Using this as the definition of "organism" means multicellularity is not a special case you coded — it is what nesting looks like.

---

## 3. Architecture

### 3.1 Repository layout

```
soup/
  __init__.py
  config.py            # all dataclasses, defaults, validation, TOML load/save
  rng.py               # seeded Generator plumbing
  substrate/
    __init__.py
    base.py            # Substrate protocol (ABC)
    bff.py             # Brainfuck-derived byte-tape substrate  [PRIMARY]
    ski.py             # SKI combinator substrate                [Stage 1+, secondary]
  world.py             # lattice, occupancy, neighbourhoods
  ledgers.py           # SymbolPool, EnergyField, SpaceLedger + invariant checks
  environment.py       # env fields, influx, fluctuation, signals
  scheduler.py         # the timestep update loop
  interactions.py      # pairing, concatenation, execution, splitting
  dissolution.py       # decay, corpse detection, byte reclamation
  lineage.py           # ancestry, birth/death records
  logging/
    __init__.py
    writer.py          # buffered Parquet writer
    schemas.py         # explicit column schemas per table
    invariants.py      # per-tick conservation assertions
  viz/
    __init__.py
    app.py             # pygame application, main loop
    panels.py          # grid, timeseries, inspector, ledger panels
    controls.py        # sliders, toggles, live parameter binding
analysis/
  __init__.py
  load.py              # read a run directory into dataframes
  diversity.py         # Hill numbers, q-profiles
  modes.py             # MODES toolbox metrics
  complexity.py        # assembly index, program length/entropy
  trophic.py           # interaction graph, trophic levels
  organizations.py     # chemical-organization detection (Stage 3+)
  report.py            # per-stage acceptance report generator
experiments/
  runner.py            # single run + sweep orchestration, manifests
  configs/             # TOML configs, one per stage + variants
tests/
  ...
runs/                  # output, gitignored
```

### 3.2 Glossary — use these terms consistently

- **Tape** — one program: a fixed-length array of bytes. The unit of matter.
- **Cell** — one site on the 2D lattice. May hold zero or one tape.
- **Pool** — the global reservoir of unallocated bytes, indexed by byte value.
- **Interaction** — two tapes are concatenated, executed as a single program, and split apart. This is the only way tapes change.
- **Organism** — NOT a tape. Defined in Stage 3+ as a closed, self-maintaining set in the interaction graph. Before Stage 3, "tape" and "organism" coincide and you should say "tape."
- **Tick** — one simulation timestep. Many interactions may occur per tick.
- **Epoch** — a configurable number of ticks; the unit at which summary statistics are logged.

### 3.3 The Substrate protocol

Both substrates implement this. The simulator core must never import `bff` or `ski` directly — only `base`.

```python
class Substrate(Protocol):
    name: str
    tape_length: int                      # bytes/symbols per tape
    alphabet_size: int                    # number of distinct symbol values

    def random_tape(self, rng) -> np.ndarray: ...

    def execute(
        self,
        joint: np.ndarray,                # concatenated tape, modified in place
        pool: SymbolPool,                 # conservation-mediated writes
        budget: ExecutionBudget,          # step and energy limits
        signals: SignalView | None,       # Stage 4+; None before that
    ) -> ExecutionResult: ...

    def is_inert(self, tape: np.ndarray) -> bool: ...
    def describe(self, tape: np.ndarray) -> dict: ...   # for the inspector panel
```

`ExecutionResult` carries: steps executed, energy consumed, number of successful writes, number of writes blocked by pool scarcity, halt reason (`budget_exhausted` / `pc_overrun` / `energy_exhausted`), and — Stage 4+ — signal reads/writes performed.

### 3.4 BFF substrate specification (PRIMARY — build this first)

Byte tape of length `L` (default 64). Alphabet is the full 256 byte values; only ten are instructions, the rest are no-ops and function as data.

Execution state: an instruction pointer `pc` into the joint tape, and two data heads `h0`, `h1`, both starting at 0. The joint tape is the concatenation of two tapes, so length `2L`. **The program is the tape — self-modification is the entire point.**

| Byte | Char | Semantics |
|---|---|---|
| 0x3C | `<` | `h0 -= 1` |
| 0x3E | `>` | `h0 += 1` |
| 0x7B | `{` | `h1 -= 1` |
| 0x7D | `}` | `h1 += 1` |
| 0x2D | `-` | decrement value at `h0` (a **transmutation**, see 3.6) |
| 0x2B | `+` | increment value at `h0` (a **transmutation**) |
| 0x2E | `.` | write value at `h0` into `h1` (a **copy**) |
| 0x2C | `,` | write value at `h1` into `h0` (a **copy**) |
| 0x5B | `[` | if `joint[h0] == 0`, jump `pc` past the matching `]` |
| 0x5D | `]` | if `joint[h0] != 0`, jump `pc` back to the matching `[` |
| other | — | no-op |

Rules: all head and pc movement is **clamped, not wrapped** — a head or pc that would leave `[0, 2L)` causes the program to halt (`pc_overrun`). Bracket matching is computed over the current joint tape at the moment of the jump, since the tape is being modified during execution. If a bracket has no match, halt. Execution stops on budget exhaustion, energy exhaustion, or pc overrun.

An interaction: pick tape A and tape B, form `joint = concat(A, B)`, execute, then `A = joint[:L]`, `B = joint[L:]`. Both tapes are written back. **Note there is no notion of parent and child** — replication is what it looks like when A overwrites B with a copy of itself.

> Verify these semantics against arXiv:2406.19108 before finalizing. If the paper differs, follow the paper and tell the user what changed.

**Configurable variants** (all default off, all exposed in config): head wrapping instead of clamping; separate tapes rather than a joint tape; instruction-pointer wrapping; a `noop_density` parameter controlling the fraction of instruction bytes in the initial random tapes.

### 3.5 SKI substrate (secondary — Stage 1, after BFF works)

Matter is an SKI combinator expression stored as a binary tree, serialized to a fixed-size array. Reduction rules: `I x → x`, `K x y → x`, `S x y z → x z (y z)`. An interaction applies one expression to another and reduces for a bounded number of steps. Conservation is native: count the `S`, `K`, `I` leaves.

Build this to validate that the simulator core is genuinely substrate-agnostic. Do not spend long on it. If the core needs changes to accommodate it, that is valuable information — report it.

### 3.6 The three ledgers

This is the heart of the design. Implement `ledgers.py` first and test it in isolation before wiring anything to it.

#### Ledger 1 — Symbols (matter). Strictly conserved.

**Invariant:** for every byte value `v` in `[0, 256)`, the total count of `v` across all tapes on the lattice, plus `pool[v]`, is constant for the entire run.

Every write to a tape goes through the pool:

```
write(tape, idx, new_value):
    old = tape[idx]
    if old == new_value: return SUCCESS_NOOP
    if pool[new_value] == 0: return BLOCKED
    pool[new_value] -= 1
    tape[idx] = new_value
    pool[old] += 1
    return SUCCESS
```

A **copy** (`.` / `,`) and a **transmutation** (`+` / `-`) both use this path. They differ only in where `new_value` comes from.

**A blocked write is a no-op — execution continues.** It is not an error. Blocked writes are the central scarcity signal in the world and you must log them: a rising blocked-write rate means the pool is exhausted, which means the world is saturated and something must die before anything can be born. Track `blocked_writes` per tape per interaction and expose it in the viz.

**Initialization:** the pool starts with `pool_multiplier × (lattice_capacity × L / 256)` of each byte value, then tapes are drawn *from the pool* so the invariant holds from tick zero. Never create a tape without debiting the pool.

**Why this beats Amoeba's minimization:** replication now requires the specific bytes you want to write to be *available*. A world full of replicators exhausts the pool of exactly the bytes replicators are made of. Reproduction becomes rate-limited by decomposition of the dead. That is a nutrient cycle, and it is what makes ecology possible.

#### Ledger 2 — Energy. Flows, not conserved in stock; conserved in flow.

**Invariant:** `energy_in_field + energy_held_by_tapes + energy_dissipated_cumulative == energy_influx_cumulative + energy_initial`.

- Energy lives on a 2D scalar field aligned with the lattice.
- Tapes absorb energy from their own cell at rate `absorption_rate`, capped at `tape_energy_capacity`.
- Executing one instruction costs `energy_per_instruction`. A successful write costs an additional `energy_per_write`.
- Spent energy becomes **waste heat**: added to `energy_dissipated`, permanently removed from the world.
- A tape with insufficient energy cannot participate in an interaction. Track energy per tape.
- Influx: `energy_influx_rate` added to the field each tick, distributed according to the environment field (§3.7).
- Field energy diffuses at `energy_diffusion` and decays at `energy_decay` (decay also counts as dissipation).

**Why:** matter cycles, energy flows. Because a tape can only obtain bytes from the pool and the pool is only replenished by dissolution, but can only obtain energy from its location, tapes face two different scarcities with different spatial structures. That mismatch is what generates niches. And because computation costs energy, any complexity a tape develops must pay for itself — this is the constraint that makes "intelligence" a meaningful possibility rather than free decoration.

#### Ledger 3 — Space. Finite, with active dissolution.

- The lattice has `width × height` cells; each holds at most one tape.
- A tape is a **dissolution candidate** if any of: it has been inert (§ `is_inert`) for `inert_ticks_to_dissolve` ticks; its energy has been zero for `starved_ticks_to_dissolve` ticks; its age exceeds `max_age` (default: disabled); or spontaneously with probability `spontaneous_dissolution_rate` per tick.
- Dissolution returns **all** of the tape's bytes to the pool and its held energy to the field at its location, then frees the cell.
- **Invariant:** total occupied cells + free cells == lattice size, checked every tick.

**Why:** without this the world clogs (Sayama). With it, dissolution is also the resupply mechanism for the symbol pool, which couples death to birth and creates the nutrient cycle.

### 3.7 Environment fields

A stack of 2D float fields, all the same shape as the lattice. All are configurable and all are tunable live in the viz.

- **`energy_influx_field`** — where energy enters. Generated by a composable spec: `uniform`, `gradient`, `patches(n, radius)`, `perlin(scale, octaves)`, or `sum` of these. Has a **`correlation_length`** parameter, in lattice cells. **This is the multicellularity lever (§ Stage 5).**
- **Temporal modulation** — every field carries an optional modulator: `static`, `sinusoidal(period, amplitude)`, `random_walk(step)`, or `switching(period, states)`. Rationale: PNAS 2413930121 found the interesting regime is a narrow band of fluctuation rate, so this must be sweepable.
- **`signal_field`** (Stage 4+) — a byte-valued field that programs can read and write. Written by the environment according to its own spec, and modifiable by programs, which gives you niche construction with no extra machinery.
- **`task_field`** (Stage 4+) — defines what counts as a correct local computation (§3.8).

### 3.8 Signals and the interaction-probability bias (Stage 4+)

Two new opcodes, enabled only at Stage 4:

| Byte | Char | Semantics |
|---|---|---|
| 0x3F | `?` | read `signal_field` at the tape's own cell into `joint[h0]` (a copy, pool-mediated) |
| 0x21 | `!` | write `joint[h0]` into `signal_field` at the tape's own cell |

**Tag-based entry (poor-man's SignalGP).** When an interaction begins, the initial `pc` is not 0. Take the first `tag_length` bytes (default 4) of each `tag_stride`-byte block of the joint tape as that block's tag. Compute Hamming distance between each tag and the local signal pattern; `pc` starts at the block with the smallest distance. Ties break toward the lowest index. This gives event-driven, modular, evolvable dispatch on a flat byte tape.

**The interaction-probability bias — the critical mechanism, implement it exactly as described.** Each tape has `p_interact`, the probability it is chosen as a partner in a given interaction round:

```
p_interact(tape) = base_rate × (1 + task_bonus × task_score(tape))
```

where `task_score ∈ [0, 1]` measures how well the tape's most recent execution transformed the local signal according to `task_field`, and `task_bonus` is configurable (default 0 — disabled).

Constraints you must honour: `task_score` is computed **from side effects the tape already produced during normal execution**, never by running the tape on a separate test input. Nothing is culled, ranked, or copied because of it. It only changes who bumps into whom. This is the arXiv:2607.09211 design and it is the only sanctioned way for the environment to reward function.

**Task-switching cost** (the Goldsby PNAS lever, default disabled): if a tape performs a different task type than it did last interaction, it pays `switch_cost_energy`. One parameter, historically sufficient to produce division of labor.

### 3.9 The scheduler — exact tick order

Order matters. Use exactly this, and make it explicit in a docstring.

```
for tick in range(n_ticks):
    1. environment.step()          # modulate fields, add influx, diffuse, decay
    2. tapes.absorb_energy()       # field -> tape, capped
    3. interactions.run_round()    # see below
    4. dissolution.step()          # candidates -> pool + field, free cells
    5. placement.step()            # free cells may receive new tapes (see below)
    6. invariants.check()          # all three ledgers; halt on violation (debug mode)
    7. logging.write_tick(tick)    # buffered
    if tick % epoch_length == 0:
        logging.write_epoch(tick)  # summary stats, population census
```

**`interactions.run_round()`**: sample `interactions_per_tick` pairs. For each: pick tape A weighted by `p_interact`; pick tape B uniformly from A's neighbourhood of radius `interaction_radius` (default 1, Moore neighbourhood); skip if either lacks `min_energy_to_interact`; concatenate, execute with a budget of `max_steps` and the tapes' combined energy, split, write back. Log an interaction record.

**`placement.step()`**: free cells are seeded with new random tapes only if `reseed_rate > 0` **and** the pool has the bytes. Default `reseed_rate = 0` after initialization — a dead world should be allowed to stay dead, because that is information. Make this a config flag, not a hidden behaviour.

### 3.10 Configuration

One `Config` dataclass tree, serialized to and from TOML. Every field carries a docstring, a default, and a documented sane range. Validate on load and fail loudly.

```
[run]         seed, n_ticks, epoch_length, stage (0-5), debug_invariants, output_dir
[substrate]   name ("bff"|"ski"), tape_length, max_steps, head_wrap, pc_wrap, noop_density
[world]       width, height, interaction_radius, interactions_per_tick, reseed_rate
[symbols]     pool_multiplier, initial_tape_fill
[energy]      enabled, influx_rate, absorption_rate, tape_capacity,
              per_instruction, per_write, diffusion, decay, min_to_interact
[dissolution] enabled, inert_ticks, starved_ticks, max_age, spontaneous_rate
[environment] influx_spec, correlation_length, modulator, modulator_period, modulator_amplitude
[signals]     enabled, tag_length, tag_stride, signal_spec
[task]        enabled, task_bonus, task_spec, switch_cost_energy
[logging]     tick_tables[], epoch_tables[], full_tape_snapshot_interval, compression
[viz]         enabled, cell_px, fps_cap, colour_mode, live_tunable[]
```

**`stage` gates features.** Stage 0 forces energy, dissolution, signals and task off regardless of what else the file says, and warns if the user set them. This keeps one config format across the whole build.

---

## 4. Logging and experiment framework

Design this in Stage 0 alongside the simulator. It is not an afterthought — it is the deliverable the user cares most about.

### 4.1 Storage

One directory per run: `runs/<timestamp>_<config_hash>_<seed>/`, containing `config.toml`, `manifest.json` (git commit, versions, hostname, wall time, exit status), Parquet files per table, and `invariant_log.jsonl`.

Parquet with zstd. Buffer in memory and flush every `flush_interval` ticks. Writing must never be in the hot loop's inner path.

### 4.2 Tables

**`ticks`** (one row per tick) — tick, n_tapes, n_free_cells, pool_total, pool_entropy, energy_field_total, energy_tape_total, energy_dissipated_cum, energy_influx_cum, n_interactions, n_writes_success, n_writes_blocked, n_dissolutions, mean_tape_energy, mean_tape_age.

**`interactions`** (one row per interaction; the highest-volume table — make it samplable via `interaction_log_rate`) — tick, a_id, b_id, a_cell, b_cell, steps, energy_spent, writes_success, writes_blocked, halt_reason, a_bytes_changed, b_bytes_changed, a_hash_before, a_hash_after, b_hash_before, b_hash_after.

The before/after hashes are how you detect replication offline without defining it in the simulator: B's hash after an interaction equalling A's hash before it *is* a replication event. Do not hard-code a replication detector into the simulation.

**`tapes`** (sampled every `tape_snapshot_interval` ticks) — tick, tape_id, cell_x, cell_y, age, energy, content_hash, length_nonzero, byte_histogram (as a fixed-width array), full bytes (only every `full_tape_snapshot_interval`).

**`lineage`** (append-only) — tape_id, born_tick, died_tick, birth_cell, death_cause, progenitor_ids (the tapes present in the interaction that produced it), content_hash_at_birth.

**`population`** (one row per distinct content_hash per epoch) — epoch, content_hash, count, mean_age, mean_energy, first_seen_tick. **This is the table the diversity metrics read.**

**`organizations`** (Stage 3+) — epoch, org_id, member_hashes, closed, self_maintaining, size, nesting_depth.

**`events`** — anything notable and rare: invariant violations, pool exhaustion, extinction, first appearance of a hash that then exceeds an abundance threshold.

### 4.3 Invariants

`logging/invariants.py` runs every tick when `debug_invariants` is on, and every `invariant_check_interval` ticks otherwise:

1. Symbol conservation, per byte value, exact integer equality.
2. Energy flow conservation, within `1e-9` relative tolerance.
3. Cell occupancy accounting.
4. No tape has energy below zero or above capacity.
5. No tape_id appears in two cells.
6. Every live tape has a lineage record; every dead one has a `died_tick`.

On violation: write a full state dump, log to `invariant_log.jsonl`, and raise. Do not continue past a violated invariant.

### 4.4 Analysis package

All offline, all reading Parquet.

- **`diversity.py`** — Hill numbers over the `population` abundance vector for `q ∈ {0, 0.5, 1, 2, 3, ∞}`, reported as effective numbers of types, per epoch. Do not report bare Shannon entropy as "diversity" — use Jost's effective-numbers conversion. Also spatial beta-diversity by partitioning the lattice into blocks.
- **`modes.py`** — the four MODES metrics: change potential, novelty potential, complexity potential, ecological potential (Dolson et al., Artificial Life 25(1) 2019). Requires a filtered lineage of persistent types; implement the filtering exactly as the paper specifies and cite section numbers in comments.
- **`complexity.py`** — per-type: nonzero length, byte-histogram entropy, compressed length (zlib) as a Kolmogorov proxy, and **assembly index** approximated from the lineage graph — the minimum number of interaction events on the path from a random tape to this content hash. You have exact construction histories, which chemists do not; exploit that. Include the caveat from arXiv:2408.15108 that assembly index may reduce to compression, and report both so they can be compared.
- **`trophic.py`** — build a directed graph from `interactions` where an edge A→B is weighted by bytes A caused to be written into B, then compute trophic levels. **A nontrivial trophic level distribution is the primary success signal for Stage 3.**
- **`organizations.py`** (Stage 3+) — detect closed, self-maintaining sets. Exact computation is combinatorial; implement a documented approximation (e.g. strongly connected components of the interaction graph above a weight threshold, then a self-maintenance check on stoichiometry). Run per epoch, not per tick.
- **`report.py`** — takes a run directory and a stage number, emits a markdown report answering that stage's acceptance criteria with numbers and plots.

### 4.5 Experiment runner

`experiments/runner.py` supports: a single run from a TOML; a **sweep** from a spec listing parameters and value grids, with `n_seeds` replicates each; parallel execution via `multiprocessing`; a `sweeps/<name>/` output directory with an index Parquet mapping config hash → parameters → run directory; and resume-on-crash. Sweeps must be reproducible from the spec file alone.

---

## 5. Visualization (pygame)

Runs in-process with the simulation, at a capped frame rate, and must be disableable with zero overhead (`viz.enabled = false` for headless sweeps). The simulation must never be slowed by rendering — render every `render_every` ticks.

**Layout:** large lattice view on the left, stacked panels on the right, controls along the bottom.

**Lattice view** with switchable colour modes: occupancy; energy (tape or field); age; **content hash** (hash → hue, so identical tapes share a colour and you can see clonal patches form — this is the single most informative view); dominant opcode; blocked-write rate; signal field; organization id (Stage 3+); trophic level (Stage 3+).

**Panels:** (1) ledger readouts with a live conservation-check indicator that turns red on violation; (2) time series — population, pool total, energy stocks, blocked-write rate, distinct-hash count; (3) Hill numbers, live for q ∈ {0,1,2}, computed on a sampled window; (4) inspector — click a cell to see the tape's bytes with instructions highlighted, its age, energy, lineage, and recent interaction history; (5) event log.

**Controls:** pause / step-one-tick / step-N / resume; speed cap; a slider or numeric field for every parameter named in `viz.live_tunable`, applying at the next tick boundary and **writing a parameter-change record into the `events` table** so the log stays truthful; save-config-as; snapshot state to disk; screenshot.

Live tuning that isn't recorded in the log is a correctness bug. Every changed parameter must be reconstructible from the run directory.

---

## 6. The six stages

**At every gate: report, then stop and wait.**

---

### Stage 0 — Bare soup

**Build:** BFF substrate; flat non-spatial population (a list of tapes; no lattice yet); random pairing; no conservation, no energy, no dissolution; the complete logging framework and analysis skeleton.

**Purpose:** validate that the instruction set supports replication, and get the data pipeline right while the simulation is trivial.

**Acceptance criteria:**
- Self-replicators emerge in ≥ 30% of 20 runs within 20,000 epochs, detected offline from interaction hashes (comparable to the ~40% reported in arXiv:2406.19108).
- The `population` table shows a clear drop in distinct-hash count when replicators take over.
- A full run's logs load into `analysis/load.py` and produce a report without manual intervention.
- Two runs with the same seed and config produce byte-identical Parquet output.

**Expect:** replicators, then rapid loss of diversity, then domination by a small number of short replicators. **If diversity does not collapse, something is wrong** — that collapse is the problem the rest of the build addresses, and you need to see it clearly.

---

### Stage 1 — Symbol conservation

**Build:** `SymbolPool`, pool-mediated writes, blocked-write accounting, invariant checks. Then implement the SKI substrate to confirm the core is substrate-agnostic.

**Acceptance criteria:**
- Symbol conservation holds exactly for every tick of a 100k-tick run.
- Population growth saturates rather than filling all capacity, and saturation coincides with a rise in blocked-write rate.
- Sweep `pool_multiplier` across at least 5 values; show that the saturation population scales with it.
- Some tape lineages show the acquire/decompose pattern — bytes moving from one tape into another and back. Quantify this from the interaction table.
- SKI substrate runs through the same pipeline with no changes to `world.py`, `scheduler.py`, or `logging/`. Report any change you were forced to make.

**Expect:** replicators still appear, but the population is now rate-limited by parts availability. Watch specifically for whether minimization still happens — it probably will, and that is fine at this stage. Record how strongly.

---

### Stage 2 — Space and dissolution

**Build:** the 2D lattice, local interaction neighbourhoods, the dissolution ledger and nutrient cycle.

**Acceptance criteria:**
- A 500k-tick run completes without clogging: the free-cell count never goes to zero and stays there for more than `clog_threshold` ticks.
- Spatial structure is visible: clonal patches in the content-hash colour mode, and measurable spatial autocorrelation of content hash above a well-mixed null model.
- Beta-diversity between lattice blocks is significantly above zero.
- **Parasite containment:** seed a run with a hand-written parasite and show it does not sweep the whole lattice at `interaction_radius = 1`, but does at large radius. This validates that locality is doing its job.
- Sweep `interaction_radius` from 1 to 8 and report the effect on diversity.

**Expect:** local containment of fast replicators and parasites, and higher standing diversity than Stage 1. If diversity did not improve over Stage 1, report that clearly rather than tuning until it does.

---

### Stage 3 — The energy ledger

**This is the novel stage. Slow down here.**

**Build:** the energy field, absorption, per-instruction and per-write costs, waste-heat accounting, structured influx fields; then `trophic.py` and `organizations.py`.

**Acceptance criteria:**
- Energy flow conservation holds for a full run.
- **A nontrivial trophic structure exists**: the interaction graph has more than one trophic level, with a distribution significantly different from a degree-preserving random rewiring null model.
- Distinguishable strategies appear — tapes living mainly off field influx (autotroph-like) versus tapes whose byte gains come mainly from decomposing neighbours (heterotroph-like). Define these operationally from the logs and report the population split over time.
- Sweep `influx_rate` across at least 6 values and show a non-monotonic relationship between influx and diversity (the intermediate-resource-diversity relationship reported in the niche-construction literature). If it is monotonic, say so — that is a real negative result.
- Longest tape length and mean tape complexity stop declining, or decline more slowly than in Stage 2. **This is the direct test of whether the design defeats the minimization attractor.**

**Expect:** genuinely unknown. This combination has not been published. Both a positive and a negative result are worth having, provided the invariants held.

**If minimization is still winning here, stop and discuss with the user before proceeding.** Stages 4 and 5 assume there is standing complexity for signals to act on.

---

### Stage 4 — Signals, tags, and the interaction bias

**Build:** the `?` and `!` opcodes, `signal_field`, tag-based entry-point dispatch, `task_field` and `task_score`, the `p_interact` bias, and the task-switching cost.

**Acceptance criteria:**
- With `task_bonus = 0`, results match Stage 3 within noise. (Sanity check that the machinery is inert when disabled.)
- With `task_bonus > 0`, mean `task_score` rises significantly above a `task_bonus = 0` control across ≥ 10 seeds.
- Signal-reading opcodes are enriched in the population relative to their no-op base rate — programs are actually using the channel.
- **Memory-region preservation:** show that some tapes protect a region from overwriting during replication, replicating the arXiv:2607.09211 finding. Detect it from the per-interaction bytes-changed masks.
- Niche construction: tapes measurably modify `signal_field`, and that modification affects neighbours' behaviour. Demonstrate with a knockout — disable the `!` opcode and show the difference.
- With `switch_cost_energy > 0`, task specialization increases (measure as the entropy of tasks performed per tape lineage).

**Expect:** function co-evolving with replication. This is the "intelligence" direction, but calibrate expectations — the published result is polynomial evaluation, not cognition.

---

### Stage 5 — Signal correlation length and the multicellularity transition

**Build:** no new mechanisms. This stage is a parameter sweep and an analysis effort. Add whatever `organizations.py` needs to detect nesting.

**The experiment:** sweep `environment.correlation_length` from well below to well above the spatial extent of a single tape's influence, at several values of temporal modulation period. The hypothesis, from DISHTINY and eLife 56349: when the environmental field is legible only at a scale above the individual, coordinated groups outcompete individuals and a transition in individuality follows.

**Acceptance criteria:**
- A run of the full sweep with ≥ 10 seeds per cell, completed and analysed.
- MODES metrics computed for every cell of the sweep, with ecological potential reported as the headline.
- **Nested organizations detected**: closed, self-maintaining sets whose members are themselves closed self-maintaining sets, persisting for more than `persistence_threshold` epochs.
- A clear statement of whether correlation length affects the appearance of nesting, with effect sizes and confidence intervals — **including if the answer is no.**
- Behavioural evidence if nesting occurs: reproductive division of labour, resource sharing between members, or differential dissolution rates within a group (apoptosis-like).

**Expect:** this may not work. It is the most ambitious stage and depends on everything below it holding up. A rigorous negative result with clean data is a genuinely good outcome and should be reported as such, not tuned away.

---

## 7. Interaction protocol with the user

- **Stop at every stage gate.** Report against the criteria with real numbers, not impressions.
- **Never tune until a result appears.** If a criterion fails, report the failure and your diagnosis. The user decides whether to tune, redesign, or accept the negative result. Silently adjusting parameters until the graph looks good destroys the value of the whole project.
- **Surface surprises immediately**, even mid-stage, and especially anything that looks like a bug in a conservation law.
- **Flag any pressure to violate §1.** If you find yourself wanting a fitness function to make something work, that is a finding about the design, not a licence.
- Keep a running `FINDINGS.md` in the repo root: one dated entry per stage with the numbers, plus anything unexpected.

---

## 8. Engineering standards

- Python 3.11+. `numpy` for state, `pandas` + `pyarrow` for logs, `pygame-ce` for viz, `pytest` for tests, `tomli`/`tomli-w` for config. Keep dependencies minimal.
- Type hints everywhere. Run `mypy --strict` on `soup/` and `analysis/`.
- **Performance:** the hot loop is BFF execution. Write it in plain Python first, get it correct, benchmark it, then optimize — `numba.njit` on the execute function is the expected route. Target ≥ 10⁵ instruction-steps/second before Stage 2 and ≥ 10⁶ before Stage 3. **Do not optimize before Stage 1 is correct.** Report benchmark numbers at each gate. If it becomes the bottleneck, say so — the user plans to port to Odin eventually and needs to know when.
- **Tests:** unit tests for every opcode against hand-worked examples; property tests (Hypothesis) asserting that random write sequences never violate symbol conservation; a golden-run regression test pinning a short run's output hash; round-trip tests for config serialization.
- Structure the code so the port to a compiled language is not painful: keep state in flat numpy arrays rather than objects-per-tape, avoid deep inheritance, keep the execute function free of Python-specific idioms.

---

## 9. Anti-goals — do not do these

- Do not add a fitness function, a selection tournament, an elite archive, novelty search, or MAP-Elites. Not even "temporarily to see if it works."
- Do not hard-code a replication detector into the simulation. Detect replication offline from hashes.
- Do not hard-code what an organism is. Stage 3+ derives it from organizational closure.
- Do not seed hand-designed replicators into the population except in the explicitly-labelled Stage 2 parasite containment test.
- Do not let programs read global state — no absolute coordinates, no population counts, no tick number.
- Do not compute diversity or complexity metrics inside the simulation loop.
- Do not silently change a default. Every default change is a config commit with a note in `FINDINGS.md`.
- Do not build ahead of the current stage.

---

## 10. References

- Agüera y Arcas et al. (2024). *Computational Life: How Well-formed, Self-replicating Programs Emerge from Simple Interaction.* arXiv:2406.19108 — BFF semantics, emergence rates.
- (2026). *Co-evolution of self-replication and function in a digital primordial soup.* arXiv:2607.09211 — the interaction-probability bias; memory preservation.
- Kruszewski & Mikolov (2020). *Combinatory Chemistry.* arXiv:2003.07916 — conservation laws producing metabolism.
- Vimal, Mathis, Weimer & Forrest (2025). *Prebiotic Functional Programs: Endogenous Selection in an Artificial Chemistry.* arXiv:2509.03534.
- Mathis, Fontana et al. (2024). *Self-Organization in Computation & Chemistry: Return to AlChemy.* arXiv:2408.12137. Code: github.com/mathis-group/AlChemy
- Moreno & Ofria (2019). *Toward Open-Ended Fraternal Transitions in Individuality.* Artificial Life 25(2). Code: github.com/mmore500/dishtiny — the correlation-length lever.
- Goldsby, Knoester, Ofria & Kerr (2012). *Task-switching costs promote the evolution of division of labor and shifts in individuality.* PNAS 109(34).
- Colizzi, Vroomans & Merks (2020). *Evolution of multicellularity by collective integration of spatial information.* eLife 9:e56349.
- Dolson, Vostinar, Wiser & Ofria (2019). *The MODES Toolbox.* Artificial Life 25(1), 50–73.
- Dittrich & Speroni di Fenizio (2007). *Chemical Organization Theory.* arXiv:q-bio/0501016.
- Jost (2006). *Entropy and diversity.* Oikos 113(2) — Hill numbers, effective numbers.
- Sayama (2024). *Self-Reproduction and Evolution in Cellular Automata: 25 Years After Evoloops.* arXiv:2402.03961 — structural dissolution.
- Pargellis (2003). *Self-organizing genetic codes and the emergence of digital life.* Complexity 8(4).
- Lalejini & Ofria (2018). *Evolving Event-driven Programs with SignalGP.* arXiv:1804.05445 — tag-based dispatch.
- Sharma, Czégel, Lachmann, Kempes, Walker & Cronin (2023). *Assembly theory explains and quantifies selection and evolution.* arXiv:2206.02279. Critique: Zenil et al., arXiv:2408.15108.
- Ackley (2011). *Pursue Robust Indefinite Scalability.* HotOS XIII — locality and relative addressing.

---

**Begin by confirming your understanding of §3.6 (the three ledgers) and §6 Stage 0's acceptance criteria. Then build Stage 0.**
