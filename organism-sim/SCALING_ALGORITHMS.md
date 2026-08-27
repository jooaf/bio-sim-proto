# Scaling a 100k+ Artificial-Life Run: Evidence, Literature, and Implementation Plan

## 1. Measured problem

The newest completed experiment is:

```text
runs/20260822T205647.154097Z-seed7-rust-gui-af41ca78/
```

Its JSONL trajectory was converted to structured JSON and inspected with Pi's
`data_explore` extension. The manifest and final row report:

```text
final tick                    23,484
final population             134,811
final measured throughput      0.492 ticks/s
manifest average throughput    0.518 ticks/s
births                       612,131
reproduction attempts     23,966,823
attacks                    6,592,112
living species                    24
```

This is not merely linear population scaling:

| interval | mean population | mean ticks/s | organism-ticks/s |
|---|---:|---:|---:|
| ticks 10k–11k | 1,819 | 315.5 | 573,933 |
| ticks 15k–16k | 9,277 | 51.3 | 475,708 |
| ticks 20k–21k | 62,574 | 3.40 | 212,909 |
| ticks 23k–end | 127,385 | 0.543 | 69,193 |

Work per organism therefore worsened about **8.3x** between the 10k and 23k
windows. Late-run biological work was also dense rather than event-sparse:

```text
births/tick                  119.3
deaths/tick                   96.1
attacks/tick               1,128.7
reproduction attempts/tick 4,988.5
```

The final audit retained exact integer matter. Floating energy error was
`-2.63e-5` against an initial-energy-based tolerance of `4.21e-6`; relative to
total generated energy the drift was about `7.2e-13`. The tolerance failure is
real but distinct from the throughput collapse.

## 2. Concrete current-code causes

The source audit found several avoidable asymptotic and memory costs.

### 2.1 Quadratic heat-chunk neighbor lookup

`World::diffuse_heat` copies active chunks into a vector, then performs four
linear `.find()` scans through that vector for every chunk.

```text
current: O(C^2 + C*S)
target:  O(C + C*S)
```

`C` is active chunks and `S` is cells/chunk. Because diffusion leaves positive
floating tails, nearly every generated chunk eventually remains active.

### 2.2 Disabled primary production still performs organism work

With the configured production rate of zero, every organism still:

1. constructs its footprint;
2. ensures footprint chunks;
3. allocates a temporary heat-cell vector;
4. scans the heat cells;
5. attempts a zero transfer.

This is pure overhead in the measured run.

### 2.3 Sorted shuffle input rebuilt with `O(N log N)` sorting

Every tick copies the living hash set, sorts all IDs, then shuffles. IDs are
monotonic and births/deaths are incremental, so a maintained ordered living
index can produce the identical pre-shuffle sequence in `O(N)`.

### 2.4 Genome lookup scans complete organism history

On a genome-distance cache miss, `genome_by_id` scans living organisms, then
the complete organism vector, then species. At the final tick the run had
created 612,431 organisms. A direct genome-owner index changes this from
`O(total_ever)` to `O(1)`.

The pair-distance hash is also unbounded. Mobile populations can continually
introduce new pairs, causing memory growth unrelated to living census.

### 2.5 Dead organisms retain very large inline genomes and policies

The organism vector is indexed by permanent ID and never removes dead entries.
Each entry contains large genome and phenotype policy arrays inline. At the
latest run's 612k total births/founders, this is a large cold archive mixed into
the live working set. It increases resident memory, TLB pressure, and cache
misses even though only 135k organisms are alive.

### 2.6 Per-action allocation and copying

Each due action currently allocates/clones:

- radius-one cells;
- sight cells;
- selected cell vectors;
- nearby/contact hash sets and vectors;
- cached footprint/nearby offset vectors;
- a 48-entry food-chemistry vector;
- action score and softmax-weight vectors.

At approximately five thousand reproduction attempts and more than one
thousand attacks per tick, allocator and memory-bandwidth costs are material.

### 2.7 Two complete deposit-key collections and global batch scans per tick

Deposit production and decomposition independently copy every deposit key.
Both then traverse deposits/batches. Diffusion and decomposition make tiny
positive heat/energy tails persistent, so simple “nonzero active” flags do not
shrink.

## 3. What established high-scale systems actually do

The broad problem is solved under specific representations: compact arrays,
local interactions, bounded event sets, spatial decomposition, and often GPU
execution. It is not solved by placing 100k rich, permanent-history objects
behind a faster priority queue.

### 3.1 Spatial decomposition and neighbor lists

Molecular-dynamics systems routinely process millions to billions of local
particles using cell-linked/Verlet neighbor lists, spatial domain
decomposition, compact arrays, and accelerator kernels.

- Plimpton's short-range molecular-dynamics decomposition established scalable
  spatial, force, and atom decomposition methods [12].
- LAMMPS explicitly combines neighbor lists, spatial decomposition, dynamic
  load balancing, and accelerator support [13].
- GROMACS combines multi-level parallelism, SIMD-friendly kernels, and GPU
  offload [14].

**Model mapping:** organism interactions are already local and occupancy is a
cell index, which is good. The remaining problem is repeated neighborhood
materialization, AoS/cache layout, and permanent dead-state retention.

### 3.2 Data-oriented biological ABM engines

BioDynaMo reports up to three orders of magnitude over baseline systems and
billion-agent runs on one server by designing the execution engine and data
layout around hardware throughput [11]. FLAME GPU 2 minimizes data movement,
executes agent functions concurrently, and demonstrates Sugarscape with up to
16 million agents; it explicitly addresses contested movement/resource cells
through hierarchical submodels [10].

**Model mapping:** a structure-of-arrays living pool, message/intent buffers,
and deterministic conflict-resolution phases are more relevant than an
object-per-history layout. GPU execution becomes practical after this phase
separation, not before.

### 3.3 Timing wheels and event sets

Varghese and Lauck's hierarchical timing wheels provide `O(1)` timer
start/stop/maintenance over bounded ranges [2]. Brown's calendar queue targets
`O(1)` expected event-set operations in discrete-event simulation [3]. Gibson
and Bruck's next-reaction method avoids rescanning all stochastic channels [4].

**Model mapping:** these solve deadline dispatch for effects, corpses,
digestion, and event-v2 hazards. They do not remove the measured constant-rate
action volume or per-tick maintenance under legacy semantics.

### 3.4 Bounded stochastic leaps

Adaptive tau-leaping selects intervals based on propensity changes [5].
Anderson's post-leap method preserves randomness across rejected leaps and
avoids negative populations [6].

**Model mapping:** useful only after abundant organisms are represented as
integer cohorts. Applying it to current individual deterministic maintenance
would add the wrong variance.

### 3.5 Super-individuals and structured populations

Scheffer et al. attach a represented count to each simulated individual,
allowing a continuum from individual models to cohorts and reporting large
computational gains [8]. De Roos's Escalator Boxcar Train evolves cohorts for
physiologically structured populations [9].

**Model mapping:** scientifically relevant, but the measured compressibility
campaign found that permanent lineage protection eliminated all savings and
species-safe cohorts retained 84–98% of census work. A different ancestry and
rare-variant representation is required before this becomes safe here.

### 3.6 Adaptive fields

Berger and Colella's block-structured adaptive mesh refinement combines local
refinement with conservative coarse/fine flux correction [7]. Continuous
artificial-life systems such as Lenia demonstrate convolutional field dynamics
[17], and Flow-Lenia localizes conserved parameters/mass.

**Model mapping:** heat has smooth remote regions and contested local regions,
so conservative AMR is appropriate. However, the current quadratic chunk
lookup must be fixed before introducing approximation.

### 3.7 Parallel discrete-event simulation

Jefferson's Time Warp uses optimistic execution and rollback [19]. Conservative
PDES variants avoid causality violations through synchronization.

**Model mapping:** the shuffled organism prefix has extensive same-tick heat,
occupancy, attack, reproduction, and death dependencies. Parallelism requires a
new intent/conflict/commit law; Time Warp over the current fine-grained mutable
state would incur expensive rollback and is not the first intervention.

### 3.8 Artificial-life practice

Avida emphasizes an explicit digital-evolution execution platform [15].
DISHTINY evolves multicellular digital organisms using localized cell/group
interactions [16]. Lenia uses regular local field kernels [17]. Grimm et al.'s
ODD protocol emphasizes declaring scheduling and stochastic semantics for
individual-based models [18].

**Model mapping:** scalable ALife systems gain regularity from local grids,
compact execution state, or controlled scheduling. The current model's rich
ordered transactions can be retained only at a performance cost; a faster
versioned engine must publish its changed schedule explicitly.

## 4. Ranked interventions

## Tier 0 — exact behavior, implement immediately

| Intervention | Complexity change | Expected value |
|---|---|---|
| Hash index for copied heat chunks | `O(C^2+C*S) -> O(C+C*S)` | Very high late-run |
| Zero-primary-production guard | removes footprint/heat work for all `N` | Very high in measured config |
| Maintained ordered living index | `O(N log N) -> O(N + event log N)` | High at 100k+ |
| Direct genome-owner index | cache miss `O(total_ever) -> O(1)` | High in dense mating ecology |
| Bound pair-distance cache | memory bounded by policy | High long-run memory safety |
| Borrow cached offset/chemistry data | remove action/upkeep allocations | Medium/high |
| Reuse action scratch buffers | allocator traffic -> retained capacity | Medium/high |
| Collect deposit keys once/tick | remove one `O(D)` hash traversal | Medium |

These preserve the selected Rust stochastic trajectory except that cache
capacity changes only whether a deterministic distance is recomputed.

## Tier 1 — behavior-preserving dynamics, versioned state format

### Dense living arena plus compact dead genealogy

```text
living organisms: dense Vec<OrganismState>
ID -> dense index: sparse vector/hash
removal: swap-remove and repair moved ID index
archive: compact DeadRecord, not full policy/inventory/cache
```

Tick order remains sorted by ID before shuffle, so dense storage order is not
observable. Simulation behavior can remain identical, but the old complete
state digest and ability to inspect every dead genome change.

Expected benefits:

- memory proportional mainly to living census rather than all births;
- sequential upkeep over a compact working set;
- fewer TLB/cache misses;
- cheap swap removal;
- foundation for structure-of-arrays and SIMD.

This is the most important structural intervention after Tier 0.

### Structure-of-arrays phase kernels

Split hot mutable fields used by upkeep from cold genome/policy/genealogy data.
Process upkeep in dense arrays, then actions by due-ID lists. This follows the
data-oriented approach used by high-performance ABM and particle engines.

## Tier 2 — new `parallel-v3`/`hybrid-v2` law

1. Agent intent generation in parallel from a read snapshot.
2. Spatial bucket sort of intents.
3. Deterministic conflict resolution per cell/component.
4. Conservative transaction commit.
5. GPU heat/deposit kernels and agent phases.
6. Conservative AMR for remote heat.
7. Super-individual cohorts only after rare-variant validation.

This is the route to millions of agents, but it changes the current shuffled
same-tick causal law.

## 5. Selected implementation sequence

1. Add phase profiling and synthetic high-population fixtures.
2. Implement all Tier-0 exact fixes.
3. Re-run fixed-state phase benchmarks and deterministic/conservation tests.
4. Implement dense living arena/compact dead records if memory/cache remains a
   dominant term.
5. Only then prototype intent/conflict/commit parallel phases.

Acceptance for the immediate implementation:

- no Python regression-fingerprint change;
- same-seed Rust outcomes unchanged for Tier 0;
- exact integer conservation and bounded floating energy drift;
- heat diffusion no longer shows quadratic chunk scaling;
- at least 3x throughput on a late-state proxy, with phase attribution;
- no GUI-worker throughput regression at 1,200 founders.

## 6. Implementation and measured outcome

Implemented in the native Rust kernel:

- indexed `O(1)` copied-chunk neighbor lookup for diffusion;
- exact zero-primary-production guard;
- maintained canonical living-ID tree instead of per-tick sorting;
- direct genome-owner sparse index and bounded pair-distance cache;
- shared footprint/neighborhood offsets and reusable decision buffers;
- no-clone food chemistry and species-representative scans;
- one deposit-key collection per tick and allocation-free single-cell heat transfer;
- combined ordered food/heat observation traversal;
- deferred contact-mate distance computation while preserving RNG draws;
- phase and subphase profiling;
- `Arc`-separated cold genome/phenotype state;
- dense ID-mapped living arena with swap removal and compact dead records;
- chunk-local dense occupancy arrays in place of per-cell hash lookups.

A coarse 8-cell neighbor-bin implementation was also built and checked against
the fine occupancy sets. Although its sets were identical, binary-search and
candidate-filter overhead made the 4,500-tick proxy substantially slower, so
it was removed rather than retained on theoretical grounds.

### Controlled results

- The Tier-0 exact stage preserved the known 1,000-tick Rust digest.
- On the explosive seed-11 5,000-tick trajectory, Tier 0 reduced wall time from
  134.1 s to 112.2 s (**1.20x**) with the same final population, digest, matter,
  and energy.
- Synthetic phase cases improved 1.27x at 1,200 organisms, 1.43x at 10,000
  organisms, and 1.65x on a 1,024-chunk/110k-deposit field before detailed
  profiler overhead.
- The standard 1,200-founder microbenchmark reached 344 ticks/s versus the
  earlier 295 ticks/s (**1.17x**).

### Real 20,000-tick replay

The optimized replay of the latest GUI seed/config completed tick 20,000 in
302.0 seconds and ended with 23,747 organisms. Its final 500-tick interval ran
at 9.48 ticks/s. Exact integer matter and floating energy audits passed.

The old run's tick-20k window averaged 62,574 organisms and 3.40 ticks/s. These
trajectories are not directly speed-comparable because low-bit/state-layout
changes eventually produce different stochastic paths. Normalizing the two
windows gives:

```text
old:       about 212,909 organism-ticks/s
optimized: about 225,000 organism-ticks/s
```

That is only about a **6% late-window per-organism efficiency improvement**.
The apparent 2.8x tick-rate gain is largely the optimized replay's smaller
population, not an engine breakthrough.

Detailed profiling at 23,103 organisms attributed:

```text
decision/perception   78.2% of organism-loop time
upkeep                17.4%
digestion              1.3%
ordering               0.2%
```

Deposit production was the largest non-agent phase. At this point, further
exact container tuning cannot plausibly produce 60 ticks/s at 100k+ rich
agents. That target requires the Tier-2 representation/schedule change:
parallel intent generation and conflict commit on CPU/GPU, or statistically
validated super-individuals. The literature calls these systems scalable
because they use those representations—not because a priority queue makes
100k independent rich decisions disappear.

Artifacts:

- `bench/results/tier0-seed11-5000.json`
- `bench/results/dense-arena-seed11-phase-profile.json`
- `bench/results/dense-occupancy-seed11-profile.json`
- `bench/results/scaling-replay-seed7-t20000.json`

## 7. References

1. Latest run data: `runs/20260822T205647.154097Z-seed7-rust-gui-af41ca78/metrics.jsonl`.
2. Varghese, G. & Lauck, A. (1987). *Hashed and Hierarchical Timing Wheels: Data Structures for the Efficient Implementation of a Timer Facility*. SOSP. https://doi.org/10.1145/41457.37504
3. Brown, R. (1988). *Calendar Queues: A Fast O(1) Priority Queue Implementation for the Simulation Event Set Problem*. Communications of the ACM. https://doi.org/10.1145/63039.63045
4. Gibson, M. A. & Bruck, J. (2000). *Efficient Exact Stochastic Simulation of Chemical Systems with Many Species and Many Channels*. Journal of Physical Chemistry A. https://doi.org/10.1021/jp993732q
5. Cao, Y., Gillespie, D. T. & Petzold, L. R. (2006). *Efficient Step Size Selection for the Tau-Leaping Simulation Method*. Journal of Chemical Physics. https://doi.org/10.1063/1.2159468
6. Anderson, D. F. (2008). *Incorporating Postleap Checks in Tau-Leaping*. Journal of Chemical Physics. https://doi.org/10.1063/1.2819665
7. Berger, M. J. & Colella, P. (1989). *Local Adaptive Mesh Refinement for Shock Hydrodynamics*. Journal of Computational Physics. https://doi.org/10.1016/0021-9991(89)90035-1
8. Scheffer, M. et al. (1995). *Super-Individuals: A Simple Solution for Modelling Large Populations on an Individual Basis*. Ecological Modelling. https://doi.org/10.1016/0304-3800(94)00055-M
9. de Roos, A. M. (1988). *Numerical Methods for Structured Population Models: The Escalator Boxcar Train*. Numerical Methods for Partial Differential Equations. https://doi.org/10.1002/num.1690040303
10. Richmond, P. et al. (2023). *FLAME GPU 2: A Framework for Flexible and Performant Agent Based Simulation on GPUs*. Software: Practice and Experience. https://doi.org/10.1002/spe.3207
11. Breitwieser, L. et al. (2021). *BioDynaMo: A Modular Platform for High-Performance Agent-Based Simulation*. Bioinformatics. https://doi.org/10.1093/bioinformatics/btab649
12. Plimpton, S. (1995). *Fast Parallel Algorithms for Short-Range Molecular Dynamics*. Journal of Computational Physics. https://doi.org/10.1006/jcph.1995.1039
13. Thompson, A. P. et al. (2022). *LAMMPS—A Flexible Simulation Tool for Particle-Based Materials Modeling at the Atomic, Meso, and Continuum Scales*. Computer Physics Communications. https://doi.org/10.1016/j.cpc.2021.108171
14. Abraham, M. J. et al. (2015). *GROMACS: High Performance Molecular Simulations through Multi-Level Parallelism from Laptops to Supercomputers*. SoftwareX. https://doi.org/10.1016/j.softx.2015.06.001
15. Ofria, C. & Wilke, C. O. (2004). *Avida: A Software Platform for Research in Computational Evolutionary Biology*. Artificial Life 10(2), 191–229. https://doi.org/10.1162/106454604773563612
16. Moreno, M. A. & Ofria, C. (2022). *Exploring Evolved Multicellular Life Histories in an Open-Ended Digital Evolution System*. Frontiers in Ecology and Evolution. https://doi.org/10.3389/fevo.2022.750837
17. Chan, B. W.-C. (2019). *Lenia—Biology of Artificial Life*. Complex Systems 28(3), 251–286. https://doi.org/10.25088/ComplexSystems.28.3.251
18. Grimm, V. et al. (2006). *A Standard Protocol for Describing Individual-Based and Agent-Based Models*. Ecological Modelling. https://doi.org/10.1016/j.ecolmodel.2006.04.023
19. Jefferson, D. R. (1985). *Virtual Time*. ACM TOPLAS. https://doi.org/10.1145/3916.3988
