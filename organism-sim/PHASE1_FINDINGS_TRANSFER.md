# Applying bio-sim-proto Phase 0/1 findings to organism-sim

## Executive recommendation

Use the program-soup work to transfer **experimental logic and observables**, not literal parameter values.

The strongest transferable idea is the difference between **origin** and **maintenance**:

- a new replicator class can be blocked while assembling resource-specific structure;
- an established ecology can recycle a composition close to its own demand and become much harder to disrupt.

`organism-sim` already implements several good translations: exact matter accounting, limiting-molecule counters, first-body-matter-block timing, turnover/transience summaries, matched-ecology deposits, isolated random streams, and scarcity profiles. These should be retained.

The next step is not another hand-tuned “best settings” search. It is a preregistered set of origin-versus-established interventions with matched seeds, resource-specific controls, effect sizes, and enough replicates.

---

## 1. What Phase 0/1 actually established

### High-confidence findings within the program soup

1. **Opportunity scale matters.** Larger populations create more chances for rare self-maintaining structures to appear and persist.
2. **Scarcity is resource-specific.** Total free matter can remain constant while particular required symbols become unavailable.
3. **Resource effects begin discontinuously.** Conserved and unconserved runs can match exactly until the first blocked write.
4. **Tight and loose scarcity behave differently.** Tight scarcity is broad and continuous; loose scarcity is usually silent but can produce sharp resource-specific bursts.
5. **Established ecologies recycle efficiently.** A natural replicator quasispecies had orders-of-magnitude less blocking than random soup under the same pool multiplier.
6. **Whole-run aggregation hides temporary roles.** Windowed flow networks showed adjacent-window persistence above a permutation null.
7. **Substrate details matter.** SKI did not preserve BFF's monotonic scarcity ordering.

### Promising but not final

- Excluding the known BFF replicator class's six structural symbols produced 0/5 transitions versus 3/5 controls; one-sided Fisher p = 0.083.
- Excluding six non-structural symbols still allowed 3/5 transitions, but that control had fewer total blocked writes.
- This supports a class-specific origin-filter hypothesis, but does not prove a universal law.

### Findings that must not be transferred as facts

- There is no universal mutation optimum; the complete mutation intervention was a one-seed BFF result.
- Pool multiplier 2 is not a universal “best ecology” setting.
- A non-significant contrast is not equivalence.
- Temporary flow roles are not proof of organism-like metabolism.
- BFF entropy transitions are not directly comparable to organism population growth.

---

## 2. Audit of organism-sim's existing Phase-learnings integration

## 2.1 Good translations to keep

| Existing organism-sim feature | Why it is useful |
|---|---|
| Exact element and energy audits | Preserves the central rule that resource effects cannot be ledger leaks |
| `reproduction_matter_blocks_by_molecule` and `matter_blocks` | Converts aggregate reproductive failure into resource-specific scarcity |
| `first_body_matter_block_tick` | Marks when the matter economy first becomes active |
| Birth/death turnover and transient-peak reporting | Separates a temporary boom from a held ecology |
| Independent chemistry/world/founder/runtime RNG streams | Makes paired environmental interventions interpretable |
| `deposit_match_ecology` | Provides a useful demand-matched environmental control |
| Stress/moderate/rich profiles | Supplies a starting panel for resource-economy experiments |
| Neutral chemistry-based decomposition | Avoids deleting organisms because an external evaluator calls them “bad” |

## 2.2 Claims and designs that should be revised

### A. Founder count is not an origin-of-life scale

`emergence_scale.toml` increases founders and founder lineages. That tests ecological persistence, diversification, and opportunity for mutation. It does **not** reproduce spontaneous replicator origin because organism-sim starts with functioning organisms.

Use the wording:

> “founder scale and standing variation affect persistence and diversification”

unless a genuinely unseeded origin process is added.

### B. The BFF mutation result cannot set organism-sim's reference rate

`test_mutation_multiplier_reference_is_preserved_by_default` documents that 1.0 is the current organism-sim reference. It should not imply that BFF proved this rate is optimal for organism-sim.

Keep 1.0 as a software/default reference, then test organism-sim's own mutation response across matched seeds.

### C. The scarcity profiles change both stock and flux

The current profiles jointly vary:

- `initial_deposits`—initial resource stock;
- `deposit_production_rate`—renewal flux.

That is a useful environmental-severity panel, but it cannot tell whether an outcome came from starting stock or ongoing production. Add a stock × flux factorial before assigning a mechanism.

### D. Demand-matched geology is not a closed conserved pool

The program soup has fixed global symbol totals. organism-sim can generate new geological chunks and includes chemical energy renewal. `deposit_match_ecology` is therefore a **composition-matched supply treatment**, not a literal reproduction of the closed byte economy.

This difference is acceptable but must be stated in reports.

### E. “Established ecology” needs a real checkpoint intervention

The current matched-ecology option derives weights from founders immediately. It does not compare the same naturally evolved ecology before and after a resource intervention.

The stronger Phase 1 translation requires:

1. run to a preregistered ecological checkpoint;
2. save complete deterministic state;
3. branch the same state into matched, mismatched, excluded, and control environments;
4. compare post-intervention persistence and adaptation.

The specification describes save/checkpoint semantics, but the current prototype does not yet provide a complete resume workflow. Implement that before claiming an established-ecology intervention.

### F. The report's “late window” should be checked

`src/organism_sim/report.py` currently starts its reported window near 20% of the recorded trajectory, so it uses roughly the final 80%, not the final 20%. The printed trend is labeled as a percentage but the underlying fraction is not multiplied by 100.

Fix and test these details before using late-window stability as a confirmatory endpoint.

---

## 3. Direct finding-to-design map

| Phase 0/1 finding | organism-sim interpretation | Recommended action |
|---|---|---|
| Scale changes rare-event probability | More founders/lineages provide more ecological and mutational opportunities | Sweep founder count and standing lineage count while keeping density, world area per founder, chemistry, and horizon matched |
| Mutation can be too low or too high | Heredity/variation tradeoff may be non-monotonic | Run a direct mutation sweep; do not assume the BFF reference transfers |
| Scarcity is resource-specific | Reproduction may be blocked by particular molecules/elements | Keep molecule-specific counters; add element-level demand deficit and body/gut/environment supply histograms |
| Conservation acts at first block | Average failure rate can hide a long neutral prefix | Align trajectories on first body-matter block and compare pre/post-block dynamics |
| Tight scarcity is broad; loose scarcity is bursty | Different resource regimes may cause chronic versus episodic reproductive failure | Record per-window concentration, zero-block windows, burst duration, and top limiting resource share |
| Established ecology is demand-closed | Evolved body/resource demand may fit local supply | Compare founder-matched, evolved-checkpoint-matched, uniform, and deliberately mismatched supplies |
| Structural exclusion filters origin | A guild may require a resource class that another guild does not | Exclude guild-enriched molecules/elements at founding and compare with matched-friction irrelevant-resource exclusions |
| Established ecology absorbs exclusion | Existing inventories and recycling can buffer shocks | Apply the identical exclusion after an ecology checkpoint and compare response with the origin treatment |
| Aggregate flow looks mixed | Whole-run totals erase roles | Build time-windowed nutrient-transfer, predation, and resource-sharing networks |
| Windowed roles persist then drift | Ecological roles may be temporary | Compare adjacent-window edge/role correlations with a label-permutation null and report lag decay descriptively |
| Substrates differ | Results depend on chemistry and life-cycle semantics | Treat every BFF-to-organism mapping as a hypothesis, not a copied law |

---

## 4. Highest-value organism-sim experiment

## 4.1 Question

Does resource composition filter which organism guilds establish at founding while an established ecology buffers the same intervention?

## 4.2 Required capability

Implement deterministic checkpoint/resume for the selected engine. A checkpoint must include:

- tick and RNG streams;
- world chunks, deposits, heat, and occupancy;
- organisms, genomes, phenotypes, inventories, lineages, species, colonies, corpses, and effects;
- chemistry catalog and configuration;
- conservation baselines and next-ID counters.

Replay from the same checkpoint must be exact before interventions are trusted.

## 4.3 Treatments

Use the same seeds and chemistry in all arms.

1. **Control:** normal resource composition.
2. **Demand matched:** supply proportional to the target guild/ecology's measured demand.
3. **Target-resource exclusion:** zero or strongly reduce molecules/elements enriched in the target guild.
4. **Irrelevant-resource exclusion:** exclude unrelated resources.
5. **Matched-friction control:** adjust irrelevant exclusion until total reproductive block burden overlaps the target-exclusion arm.

Run each composition treatment in two timings:

- **origin:** active from founder creation;
- **established:** introduced from the same evolved checkpoint.

The matched-friction arm is essential. Phase 1's strongest origin-filter result was limited because structural and non-structural exclusions did not produce equal blocked-write volumes.

## 4.4 Target guild definition

Define a target without using future success:

- one preregistered founder guild/archetype;
- or a guild defined by fixed diet/body-signature rules before outcomes are observed.

Measure its resource enrichment from held-out baseline runs, not from the treatment outcomes.

## 4.5 Primary outcomes

- probability the target guild persists to the final window;
- final and maximum target-guild share;
- births/deaths and replacement ratio by guild;
- first body-matter block tick;
- molecule- and element-specific blocked-attempt distributions;
- body composition and environmental-supply divergence over time;
- extinction and checkpoint survival;
- conservation residuals.

Use at least 10 matched seeds per cell for screening and more if the observed event rates make Fisher intervals too wide. Report effect sizes and confidence intervals, not only p-values.

---

## 5. Supporting experiments

## 5.1 Stock × renewal-flux scarcity factorial

The existing scarcity profiles confound stock and flux. Cross:

- initial deposits: low / medium / high;
- deposit production: low / medium / high.

Hold world area, founders, lineages, chemistry, mutation, and all other settings fixed. This distinguishes one-time shortage from sustained carrying capacity.

Primary outputs:

- chronic versus bursty body-matter blocks;
- limiting-resource effective count;
- zero-block window fraction;
- births/death and extinction;
- species/guild Hill diversity.

## 5.2 Mutation response

Suggested first panel: mutation multiplier `{0.25, 0.5, 1, 2, 4}` with matched seeds.

Primary outputs:

- lineage persistence;
- generation depth;
- phenotype/genome novelty;
- extinction;
- species Hill diversity;
- reproductive success.

Do not expect a BFF-shaped curve in advance. Record whether the relationship is monotonic, peaked, flat, or seed-dependent.

## 5.3 Founder opportunity scale

Cross founder count with founder-lineage count while preserving:

- founders per unit area;
- deposits and production per unit area;
- chemistry seed and founder draws through isolated streams;
- run horizon.

Call the result persistence/diversification scale, not spontaneous emergence.

## 5.4 Windowed ecological-role networks

Build directed weighted networks per fixed window from:

- predation matter transfer;
- parental matter transfer;
- colony/resource sharing;
- molecule consumption and excretion, represented as organism↔resource-class edges.

Compare adjacent-window edge weights and node roles against:

- label-permutation nulls;
- degree/strength-preserving nulls when feasible;
- content/phenotype persistence controls.

A persistent network is not automatically metabolism. Require closure, reproducibility, and function before making that claim.

---

## 6. Recording and analysis changes

### Keep

- exact lifecycle events;
- exact conservation totals;
- molecule-specific block counters;
- first-block timing;
- isolated RNG streams;
- compact Rust long-run recording.

### Add

1. Element-level as well as molecule-level reproductive deficits.
2. Per-guild body, gut, waste, and environmental composition histograms.
3. Supply-versus-demand Jensen–Shannon divergence by window.
4. First block by resource and by guild.
5. Windowed block concentration and burst duration.
6. Guild/species Hill q-profiles rather than richness alone.
7. Windowed matter-transfer edge tables.
8. Deterministic checkpoint IDs and parent-checkpoint provenance.
9. Explicit exploratory/confirmatory labels in reports.
10. Confidence intervals for extinction, persistence, and replacement outcomes.

---

## 7. What not to do

- Do not copy pool multipliers 0.5/2/16 as if deposit counts had the same physical meaning.
- Do not call founder scaling spontaneous replication emergence.
- Do not claim mutation multiplier 1 is optimal because one BFF seed favored its reference rate.
- Do not interpret p=1 as proof of equality.
- Do not use aggregate resource blocks without naming limiting resources.
- Do not call dense or persistent flow a metabolism without a null and closure test.
- Do not tune exclusion sets after observing which treatment wins.
- Do not add an external fitness score to force the expected guild response.

---

## 8. Recommended order

1. Correct and test late-window reporting.
2. Implement exact checkpoint/resume for the selected engine.
3. Add per-guild/resource composition and deficit telemetry.
4. Run the stock × flux factorial.
5. Run the origin-versus-established exclusion experiment with a matched-friction control.
6. Run the organism-specific mutation sweep.
7. Add windowed ecological-role networks only after transfer events are recorded cleanly.
8. Update defaults only from replicated, held-out confirmation—not from the discovery seeds.

---

## Bottom line

The existing `organism-sim` integration already captures several valuable Phase 1 lessons. The main missing contribution is a true **same-state origin-versus-established resource intervention**.

That experiment would test whether the program-soup headline generalizes:

> resource composition filters what can become established, while an existing ecology can buffer and recycle through the same shortage.

If organism-sim does not reproduce that pattern, the negative result is equally useful. It would show that explicit organisms, chemistry, energy renewal, behavior, and spatial acquisition change the resource-economy mechanism rather than merely rescaling it.
