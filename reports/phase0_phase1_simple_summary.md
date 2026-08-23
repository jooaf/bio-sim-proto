# Phase 0 and Phase 1 — simple summary

## The project in one sentence

We built a world where small computer programs change and copy each other, then added a rule that every byte of “matter” must be borrowed from and returned to a shared pool.

---

## Phase 0: can copying appear by itself?

### What we built

- A soup of random BFF programs.
- Programs interact in random pairs and can change each other.
- No fitness score tells them what to do.
- A mutation can randomly change a byte.
- Runs are repeatable when the seed and settings are the same.
- The simulator saves detailed data for later analysis.

### What we tried first

We ran 20 experiments with only 256 programs.

**Result:** copying appeared in only 1 of 20 runs, and it did not take over.

### Why that first test failed

The test was much smaller than the published experiment we were comparing against. It gave the programs far fewer chances to discover a working copier. The pairing and mutation details also needed correction.

This was mainly a **scale and protocol mismatch**, not proof that the simulator could not make replicators.

### What we changed

- Matched the published pairing method.
- Added the published background mutation rate.
- Built a faster probe so the full 131,072-program experiment was possible.
- Checked the probe against the released reference implementation.

### What happened at the correct scale

- Seed 0 produced a replication transition around epoch 2,433.
- Seed 2 also produced a transition.
- Seeds 1 and 3 did not.
- Functional tests confirmed that many common programs could really copy.

**Simple lesson:** replication is possible, but population size and the number of interaction opportunities matter a lot.

### Mutation test

For seed 0:

- no mutation: no full transition;
- mutation rate 1/4,096: strong transition;
- very high mutation: no transition.

**Simple lesson:** too much mutation destroys stable copying. A moderate amount helped this seed, but more seeds are needed before calling it a general rule.

---

## Phase 1: what happens when byte matter is conserved?

### What we added

We added a shared pool containing byte values.

When a program changes byte `old` into byte `new`:

1. it must take one `new` byte from the pool;
2. it returns the `old` byte to the pool;
3. if `new` is unavailable, the change is blocked.

The total amount of every byte value must always stay exactly the same.

### Did conservation work correctly?

**Yes.** Every reported conserved campaign had zero conservation error.

The current test suite also passes:

- **66 tests passed**;
- strict type checking passed.

### Pool-size experiments

We tried pool multipliers 0.1, 0.5, 2, 16, and 256.

| Pool size | What happened |
|---|---|
| 0.1 | Heavy blocking across many byte values |
| 0.5 | Strong scarcity |
| 2 | Moderate scarcity and useful default condition |
| 16 | Almost no blocking on average, but rare spikes |
| 256 | Effectively unlimited control |

**Simple lesson:** the pool does not run out of total matter. It runs short of particular byte values.

### Why blocking sometimes appears as a huge spike

A single program can enter a long loop and request the same missing byte many times. One interaction can therefore create most of a tick's blocked writes.

**Simple lesson:** rare blocking spikes are usually caused by one long loop, not the whole soup freezing together.

### Did bytes really move between programs?

**Yes.** We added token labels for auditing and saw bytes:

- leave one program;
- enter the pool;
- later enter another program;
- repeat this process in cycles.

But the whole network was highly mixed.

**Simple lesson:** matter circulates, but we have not yet found a small, stable, organism-like metabolism.

### Did programs keep temporary roles?

When the flow data was split into 2,000-epoch windows, some programs kept similar donor/receiver roles in nearby windows. These roles faded at longer time gaps.

**Simple lesson:** there is temporary organization, but the roles drift instead of staying fixed.

### Did medium scarcity create the most organization?

Multiplier 2 sometimes had the largest entropy value, but the result was not consistent enough.

**Result:** unresolved. Do not claim that medium scarcity is always best.

### Did conservation stop replication?

At 4,096 programs, replication transitions happened in both conserved and unconserved runs and were often temporary. At 32,768 programs, transitions happened more often and usually lasted longer.

**Simple lesson:** population size affected emergence more clearly than ordinary pool conservation did.

### What happened to an already established replicator ecology?

We took a naturally emerged Phase 0 checkpoint and continued it with conservation.

- Large pool: exactly followed the no-conservation control.
- Medium and small pools: stayed alive with extremely little blocking.
- Uniform or very small pools: also stayed alive.
- Removing free supplies of important symbols: still did not destroy it during the tested 8,000 epochs.

The ecology contained many related programs, not one single winning tape.

**Simple lesson:** an established replicator community is good at recycling the same kinds of bytes it already contains.

### What happened when important symbols were missing from the start?

We removed free pool supplies of six symbols used heavily by the known replicator class.

- Important-symbol exclusion: 0 of 5 runs emerged.
- No-conservation control: 3 of 5 emerged.
- Excluding six arbitrary, non-structural symbols: 3 of 5 emerged.

**Simple lesson:** the available kinds of matter may decide which replicator classes can appear in the first place.

### Important caution

This origin-filter result is promising, but not final:

- there were only five seeds per main group;
- the main Fisher test gave p = 0.083, not below 0.05;
- the arbitrary-symbol control had fewer blocked writes than the important-symbol group.

So say **“supports the origin-filter idea”**, not **“proves a universal law.”**

### What did the SKI experiment show?

A second program language, SKI, ran through the same world, scheduler, conservation checks, and logging system.

- Conservation stayed exact.
- Expressions stayed valid.
- Repeat runs were byte-identical.
- Medium pool size blocked more than the smaller pool because it allowed longer expressions to grow and demand more scarce symbols.

**Simple lesson:** the conservation system is reusable, but different program languages can react to scarcity differently.

---

## What is genuinely new here?

The published BFF work showed spontaneous replication without conservation. Other artificial chemistries used conservation in different program systems.

This project combines and tests:

- spontaneous BFF program evolution;
- exact conservation of each byte value;
- controlled pool composition;
- natural-checkpoint continuation;
- important-symbol versus arbitrary-symbol exclusion;
- explicit byte-path tracing;
- time-windowed flow analysis.

The most interesting new idea is:

> Scarce matter matters most while a replicator class is being formed. Once a replicator ecology exists, it can recycle its own material and resist the same shortage.

This appears new compared with the literature reviewed in this repository, but a broader literature search is still needed before publication.

---

## What did not work or remains unknown?

- The first 256-program Phase 0 acceptance test was too small.
- The original 20-run Phase 0 success threshold was never repeated literally at paper scale.
- Medium scarcity was not proven to maximize organization.
- We did not find a stable, sparse metabolism.
- We did not prove a universal mutation sweet spot.
- We did not prove that arbitrary-symbol exclusion is exactly equal to no conservation.
- We have not added space, dissolution, energy, signals, or multicellularity yet.
- A custom Spearman p-value bug was found and corrected. Most decisions stayed the same, but lag decay is now described as a pattern rather than a significant result.

---

## Are we ready for Phase 2?

**Yes, with conditions.** We have enough Phase 0/1 science to stop broad Phase 1 sweeps and start Phase 2 planning and scaffolding.

**Do not start the long Phase 2 experiments yet.** First:

1. commit/tag the Phase 0/1 code, reports, configs, and result summaries;
2. keep the corrected statistical helper and regenerated statements;
3. decide how empty lattice cells receive new programs;
4. make sure “no clogging” cannot pass just because everything died;
5. disable starvation death until the energy system exists in Phase 3;
6. define spatial autocorrelation and beta-diversity tests before running experiments;
7. benchmark whether a 500,000-tick spatial run is practical.

---

## What Phase 2 should do

Phase 2 adds:

- a 2D lattice;
- local interactions;
- empty and occupied cells;
- dissolution of inactive programs;
- return of dissolved bytes to the pool;
- spatial measurements.

The main questions are:

1. Does the world keep active empty space without dying out?
2. Do related programs form visible patches?
3. Is spatial similarity stronger than a mixed-up null model?
4. Does local interaction stop a parasite from taking over the whole world?
5. How does interaction radius change diversity?

---

## Recommended next actions

1. Freeze Phase 0/1 in version control.
2. Preserve the corrected statistics and final wording.
3. Write a Phase 2 preregistration.
4. Decide the birth/empty-cell rule.
5. Build and test a tiny lattice first.
6. Add spatial analysis before large experiments.
7. Run short pilots and benchmark performance.
8. Launch the full Phase 2 gate only after those checks pass.

## Final takeaway

Phase 0 showed that spontaneous copying works when the experiment is large enough.

Phase 1 showed that conserved bytes create a real resource economy. Random soups struggle when important building blocks are missing, while established replicator communities recycle their own matter very efficiently.

That is enough to move forward carefully into Phase 2.
