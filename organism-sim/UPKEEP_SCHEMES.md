# Organism Upkeep Schemes: Research, Tradeoffs, and Recommended Mix

## Executive recommendation

Do not assign one update model to all upkeep. The current upkeep function combines four different mathematical classes:

1. **Deterministic autonomous flows** — mana decay and toxin decay.
2. **Piecewise deterministic reservoir depletion** — maintenance, debt, integrity, and age support.
3. **Stochastic hazards** — post-lifespan attrition.
4. **Spatially coupled competition** — primary production harvesting heat from footprints.

They should use different schemes:

| Process | High-fidelity event-v2 recommendation | Large-population hybrid recommendation |
|---|---|---|
| Primary production | Active-set, ordered per-tick transfer; skip completely at rate zero | Conservative tile allocation, initially `Δ<=2`; individual/fine fallback in contested regions |
| Mana decay | Lazy closed form with dated heat sources | Exact-key buckets, or binned/cohort closed form (`W`) |
| Maintenance payment | Piecewise lazy reservoir map with breakpoint events | Local state-class/cohort epochs with reserve distributions |
| Body-batch debit | Prefix debit watermark or next-nonempty index | Pooled integer inventory plus representative particles |
| Debt/integrity | Deterministic threshold events | Threshold-protected classes; never leap across death |
| Toxin damage/decay | Analytic geometric map plus threshold event | Toxin/tolerance buckets with protected tails |
| Old-age support | Coupled reserve breakpoint integration | Age-reserve state classes |
| Old-age death | Discrete cumulative-hazard clock | Bounded binomial survival for abundant classes; critical low-count classes event-sampled |
| Death finalization | Immediate critical event | Immediate integer subcohort event; never fractional or delayed |
| Colony maintenance bonus | Versioned demand coefficient and forecast invalidation | Cohort key includes bonus/membership class |

Recommended architecture:

```text
legacy-v1: exact current shuffled per-tick oracle

event-v2:
    lazy deterministic maps
    + scheduled threshold/hazard events
    + dated heat-source ledger
    + one-tick fallback when coupling is unsafe

hybrid-v1:
    event-v2 for individuals protected from aggregation
    + local state buckets/cohorts for abundant homogeneous organisms
    + adaptive split/refine/error controls
```

Naive rotating subsets, charging every organism once every eight ticks, and Poisson maintenance pulses are not recommended. They alter starvation, heat timing, action eligibility, and death timing.

### Empirical compressibility result

The exact-state campaign in [`COMPRESSIBILITY.md`](COMPRESSIBILITY.md) found no exact-state batching opportunity and no lineage-safe cohort compression. Species-safe cohorts retained 84–98% of census work, while an exploratory guild-level cohort retained 38–70% of final census before overheads. Depending on seed, 14–54% of organisms were in individually critical reserve/integrity/debt/status states. This mixed upkeep design remains necessary for a cohort prototype, but it is not by itself sufficient for practical sublinear whole-simulation execution.

---

## 1. Current upkeep semantics

For each organism, after the tick's global environment phases and in shuffled organism order:

```text
1. primary production: footprint heat -> body energy; refund excess at center
2. mana decay -> heat
3. maintenance: preferred mana share, then sorted body molecule batches -> heat
4. payment deficit -> maintenance debt and integrity damage; otherwise debt recovery
5. toxin excess damage, then toxin *= 0.999
6. after lifespan: pay support from mana/body -> heat, then draw attrition death
7. if integrity <= 0 or debt > 4*reference_energy: die
8. if alive: digestion and possibly an action occur later in the same organism turn
```

The organism loop is not simultaneous. Earlier organisms' heat, deaths, deposits, movements, and colony changes can affect later organisms during the same tick.

### Important details an accelerated model must preserve or explicitly change

- Mana decays before maintenance.
- Maintenance uses at most `demand * mana_preference` from mana. It does not use leftover mana to compensate when body energy is insufficient.
- Body energy is consumed from molecule batches in ascending molecule-ID order.
- A deficit must exceed `1e-12` to cause debt/damage.
- Debt death uses strict `debt > 4R`; integrity death uses `integrity <= 0`.
- Toxin damage uses pre-decay toxin and strict `toxin > tolerance`.
- Old-age support is paid before the death draw and is paid on the death tick.
- Death immediately releases mana to heat and transfers integer body/gut/waste inventories to deposits.
- A body with no energy headroom can still harvest heat across its footprint and refund it at its center, redistributing heat. “Full body” does not make primary production a no-op.
- Colony formation/dissolution can change the maintenance coefficient in the middle of the shuffled organism prefix.

---

## 2. Fidelity levels

Every policy must declare its contract.

### Legacy exact (`L`)

Same shuffled order, shared xoshiro stream, floating operation order, strict comparisons, and digest as the current Rust kernel.

Only implementation changes proven by the complete-state digest qualify.

### Event-law/high fidelity (`E`)

Deterministic within a versioned engine; preserves declared per-entity recurrence equations, threshold ticks, and waiting-time marginals, but not legacy-v1's global joint law or floating bits.

Lazy formulas, counter-based RNG, and event clocks belong here.

### Weak/statistical (`W`)

Preserves preregistered observables within measured error bounds. Cohorts, spatial tile allocation, tau-leaping, and larger operator-split steps belong here.

### Unsafe general replacement (`U`)

Known structural bias without an adequate error controller. It may be available only in a clearly labeled exploratory mode.

Conservation alone does not imply ecological correctness.

---

## 3. Scheme catalog

## 3.1 Exact per-tick recurrence

```text
for organism in shuffled_living_order:
    run every upkeep substep
```

**Pros**

- Simple oracle.
- Preserves current ordering, RNG, and threshold behavior.
- Easy conservation reasoning.

**Cons**

- `Θ(N)` dispatch every tick.
- Repeats deterministic arithmetic for unchanged organisms.
- Cannot support multi-day million-organism runs on one machine.

**Use**

- Legacy-v1, checkpoint validation, coupled fallback, and critical edge cases.

---

## 3.2 Lazy closed-form maps

Store `last_materialized_tick` and advance deterministic state only on action, observation, mutation, or threshold.

**Pros**

- Turns many tick updates into `O(1)` or a few breakpoints.
- Particularly strong for mana and toxin decay.
- No demographic approximation is required for stable intervals.

**Cons**

- Changes floating bits relative to repeated recurrence.
- Requires precise invalidation.
- Heat cannot be lumped at the interval endpoint.
- Frequent actions can eliminate most savings.

**Use**

- Event-v2 mana, maintenance phases, toxin, debt recovery, and young stable organisms.

---

## 3.3 Breakpoint/threshold scheduling

Predict the next state-regime change rather than updating every tick.

Typical breakpoints:

```text
lifespan + 1
mana can no longer pay its target
next body batch exhaustion
body energy reaches zero
maintenance deficit branch changes
debt reaches strict 4R boundary
integrity reaches zero
toxin crosses tolerance
age-support limiter changes
raw age hazard reaches its cap
colony, position, inventory, action, output, or heat dependency changes
```

**Pros**

- Protects threshold and death timing.
- Work follows meaningful physiological transitions.
- Combines naturally with lazy formulas.

**Cons**

- Analytic crossing estimates need adjacent-tick verification.
- External mutations create stale events.
- Dense interactions can cause frequent invalidation.

**Use**

- Event-v2 maintenance, toxin, debt, support, and death.

---

## 3.4 State-class buckets

Group organisms by local upkeep drivers and process one transformation per class.

Example key:

```text
(
    spatial_leaf,
    lineage_or_trait_bin,
    colony_bonus_class,
    basal_demand_bin,
    mana_preference_bin,
    mana_regime,
    body_energy_segment,
    debt_integrity_margin,
    toxin_relative_to_tolerance,
    age_hazard_band,
    action_phase,
    status_class,
)
```

**Pros**

- Safer first aggregation than broad cohorts.
- Natural SIMD/vectorization.
- Threshold crossings move members between explicit classes.
- Can become sublinear if class count `K << N`.

**Cons**

- High-dimensional class explosion can produce `K ~= N`.
- Binning creates boundary artifacts.
- Means do not preserve reserve/toxin/age correlations.

**Use**

- First hybrid aggregation step at 30k–100k populations.

---

## 3.5 Cohort epochs

Represent many locally similar organisms with integer counts, pooled inventories, state distributions, and representative particles.

**Pros**

- The main route to census-sublinear upkeep.
- Exact pooled matter conservation is possible.
- Supports bounded stochastic event counts.

**Cons**

- Loses individual histories and correlations.
- Mean-state cohorts hide starving/toxic tails.
- Deaggregation reconstructs synthetic individuals.
- Requires rare-lineage and threshold protection.

**Use**

- Hybrid-v1 at 100k–1M populations when local states are compressible.

---

## 3.6 Cumulative-hazard clocks

Replace daily Bernoulli trials with one waiting threshold:

```text
hazard_increment[t] = -log(1 - p[t])
threshold = -log(U)
death_tick = first t where cumulative_hazard >= threshold
```

**Pros**

- Removes no-death RNG trials.
- Preserves the discrete survival product for a known hazard path.
- Natural for age attrition.

**Cons**

- Hazard depends on support, mana, body energy, and age.
- External changes invalidate the forecast.
- Legacy-v1 shared RNG trajectory is not preserved.

**Use**

- Event-v2 aging; retain residual hazard threshold across invalidations.

---

## 3.7 Rotating subsets

Update only `N/m` organisms per tick.

**Naive form**

```text
selected organisms pay m ticks of upkeep now
others do nothing
```

**Pros**

- Simple and bounded dispatch cost.
- Cache friendly.

**Cons**

- Bursty heat, debt, toxin, and death.
- Delayed thresholds grant extra actions/reproduction.
- Creates phase locking with action periods.
- Scaled payment can overdraw low reserves.

**Verdict**

Unsafe as a scientific model. Acceptable only as a dispatcher for analytically accumulated latent state, where every threshold still occurs at its represented tick.

---

## 3.8 Fixed-interval batching

Update every organism or cohort every `Δ` ticks.

**Pros**

- Vectorizable and deterministic.
- Closed forms make mana/toxin batching strong.
- Useful for cohort/state-bucket epochs.

**Cons**

- Endpoint-only heat/death is biased.
- Processes do not commute.
- Actions often force early materialization.

**Verdict**

Good implementation mechanism for autonomous deterministic maps. Approximate for spatial production and interacting populations unless clipped at every deadline and paired with error estimation.

---

## 3.9 Asynchronous Poisson clocks

**Pros**

- Appropriate for stochastic jump processes.
- Removes empty hazard polling.

**Cons**

- Deterministic maintenance is not a jump process.
- Poisson maintenance adds artificial variance.
- Constant exponential age clocks do not match age-varying hazard.

**Verdict**

Use transformed nonhomogeneous clocks for aging and geometric clocks for digestion. Do not Poissonize mana, maintenance, toxin decay, or primary production.

---

## 3.10 Continuous-time ODE / PDMP

A piecewise-deterministic Markov process uses deterministic physiological flow between discrete actions, attacks, digestion, and stochastic death jumps.

**Pros**

- Coherent mathematical mixed model.
- Supports analytic flows and event root finding.
- Natural basis for event-v2.

**Cons**

- Current model is a discrete ordered tick map.
- Generic ODE solvers may be slower than analytic maps.
- Spatial heat harvesting creates a large coupled nonlinear system.

**Verdict**

Use PDMP as the conceptual model, but implement analytic integer-boundary maps where available.

---

## 3.11 Tau-leaping

Freeze cohort propensities for a short interval and draw aggregate event counts.

**Pros**

- Strong speedup for abundant stochastic channels.
- Retains demographic variance better than deterministic expected values.

**Cons**

- Can overdraw population/resources.
- Can leap over death/rarity thresholds.
- Fresh redraw after rejection biases paths.

**Verdict**

Use bounded binomial/multinomial draws for abundant cohort hazard channels, exact event handling for critical derived-model channels, and conditional post-leap bridges.

---

## 3.12 Energy-budget epochs

Reserve upkeep energy for an interval and expose only the remainder to other systems.

**Pros**

- Explicit solvency and conservation.
- Useful internally for cohort proposals.

**Cons**

- Upkeep and actions currently share the same reservoirs.
- Upfront reservation can suppress actions that should occur before later charges.
- End reservation lets organisms spend energy already owed to upkeep.

**Verdict**

Use as an internal transactional proposal mechanism only. End the epoch before every shared-reserve mutation.

---

## 3.13 Operator splitting

Advance production, mana, maintenance, toxin, and aging as separate operators.

**Pros**

- Modular implementations and tests.
- Each transfer can remain conservative.
- Different processes can use different time resolutions.

**Cons**

- Operators do not commute: decay precedes maintenance, toxin precedes digestion, and death precedes action.
- Larger steps introduce phase-order bias.

**Verdict**

Good architecture for event-v2/hybrid. At `Δ=1`, a phase-wide split is still not legacy exact: legacy interleaves each organism's production, decay, maintenance, toxin, support, death, digestion, and action before advancing to the next shuffled organism. Legacy-v1 must retain that per-organism prefix. For larger steps, declare approximation and use one-full-versus-two-half-step error estimation.

---

## 3.14 Adaptive fidelity

Select exact-tick, lazy, bucket, cohort, or leap policy by local state.

**Pros**

- Spends accuracy on rare, threshold, and spatial-front states.
- Supports one engine family from 10k to 1M.

**Cons**

- Switching creates nonstationary error.
- Deaggregation cannot restore lost identities.
- Performance pressure can encourage unsafe merging.

**Verdict**

Recommended controller, provided it fails closed to finer treatment or stops when the accuracy contract cannot be met.

---

## 4. Process-specific recommendations

## 4.1 Primary production

Current transfer:

```text
requested = reference_energy * production_rate
removed = remove heat proportionally from footprint
accepted = fill sorted body batches up to capacity
refund = removed - accepted at organism center
```

### Schemes

#### A. Disabled fast path (`L`)

When rate is exactly zero, skip footprint and heat work after proving no legacy chunk-generation side effect.

- **Pros:** exact and large constant-factor win.
- **Cons:** only applies at zero.

#### B. Active footprint subscribers (`L` only as an in-turn predicate; otherwise `E`)

Maintain a heat-cell-to-organism-footprint advisory index. For legacy fidelity, recheck exact current heat when the organism reaches its original shuffled turn. Any heat emitted by an earlier organism must update subscribers before the later turn. Skipping must also preserve any on-demand chunk-generation side effect.

- **Pros:** output-sensitive in cold regions.
- **Cons:** diffusion and every same-tick source/sink change membership; overlapping footprints remain order-coupled; full bodies remain active because refund redistributes heat. A phase-wide active pass is a new event/hybrid law.

#### C. Conservative tile epoch (`W`)

Aggregate heat and headroom demands inside a spatial tile, define an explicit allocation law, and apply bounded transfers.

- **Pros:** work scales with active tiles/cohorts.
- **Cons:** proportional allocation differs from current random sequential competition and can weaken winner-take-all selection.

### Recommendation

- Event-v2: active-set per-tick processing with ordered conflicts.
- Hybrid-v1: tile allocation at `Δ<=2` initially; fine fallback for overlapping protected organisms, steep gradients, and contested heat.

### Pseudocode

```text
# Legacy-v1 optimization: remain inside the original organism loop.
for organism in original_shuffled_prefix:
    if production_rate > 0:
        if advisory_index_maybe_hot(organism.footprint):
            if exact_current_footprint_heat(organism) > 0:
                process_current_ordered_transfer(organism)
    run_decay_maintenance_toxin_support_and_possible_action(organism)
    notify_heat_subscribers_of_every_source_or_sink()

# Event/hybrid alternative: explicitly a new E/W allocation law.
for conflict_component in active_footprint_overlap_graph:
    proposal = ordered_event_or_bounded_tile_allocation(conflict_component)
    if embedded_error > tolerance:
        refine tile or use individual event ordering
    commit one conservative heat/body transaction
```

---

## 4.2 Mana decay

For decay `d` and `q = 1-d`:

```text
mana_after_k_decay_only = q^k * mana_0
```

With constant post-decay maintenance withdrawal `M` while the same payment regime holds:

```text
mana[k] = q^k*mana[0] - M*(1-q^k)/(1-q),  q != 1
mana[k] = mana[0] - k*M,                   q == 1
```

This formula is valid only through the last tick where post-decay mana can pay `M`. Solve that crossing conservatively and verify neighboring integer ticks.

### Schemes

- Per-tick recurrence (`L`): exact oracle.
- Lazy closed form (`E`): preferred event-v2.
- Exact-key batching that retains each organism's state/breakpoints (`E`).
- Binned state buckets or pooled cohorts (`W`): preferred hybrid only with error control.
- Rotating/Poisson decay (`U`): reject.

### Heat constraint

Credit actual mana loss as a dated heat source. Endpoint lumping changes diffusion and later heat access.

```text
advance_mana(org, end_tick) -> ManaProposal:
    segment_end = min(end_tick, next_mana_credit, next_payment_regime_change)
    proposal = affine_decay_and_withdrawal_breakdown(org.mana, segment_length)
    # proposal separates actual decay debit from actual maintenance-mana debit.
    org.mana = proposal.final_mana
    return proposal
```

Transfer ownership must be disjoint:

```text
decay heat       = actual mana decay debit
maintenance heat = actual maintenance mana debit + actual maintenance body debit
support heat     = actual old-age support mana debit + actual support body debit
```

The coordinator writes each actual debit exactly once to its dated heat source. A generic `old_mana - new_mana` heat credit would double-count maintenance/support if those processes also emit their own transfers.

Event-v2 should validate `0 <= mana_decay <= 1`; the current configuration accepts larger finite values even though the closed-form nonnegative-reservoir assumptions would fail.

---

## 4.3 Maintenance payment and body batches

Demand:

```text
D = basal * reference_energy * maintenance_multiplier * (1 - colony_bonus)
mana_target = D * mana_preference
```

After mana decay, use at most `mana_target`, then drain sorted body molecule batches.

### Preferred event-v2 model

1. Solve the mana-payment phase.
2. Schedule the first mana-target crossing.
3. Accumulate body debit until a batch or total-body breakpoint.
4. Emit every actual debit to the dated heat ledger.
5. Materialize before actions, digestion, reproduction, attacks, repair, or inventory mutation.

### Prefix debit watermark

For ordered initial batch energies `e[i]`, prefix sums `P[i]`, and cumulative debit `C`:

```text
remaining[i] = e[i] - min(e[i], max(0, C - P[i-1]))
```

Use a next-positive-energy index or segment tree to skip empty batches while retaining molecule-ID order.

**Pros**

- Replaces many repeated scans with batch-exhaustion events.
- Keeps actual source debit available for conservation.

**Cons**

- Alternating fills and debits require more bookkeeping.
- With at most 48 molecule types, a tree may cost more than a scan.
- Whole-prefix zeroing changes floating arithmetic and is not legacy bit exact.

### Hybrid model

Bucket/cohort by demand, mana preference, reserve regime, body-energy segment, and important correlations. Never pay upkeep from a mean reserve alone; `min(reserve,demand)` hides the starving tail.

---

## 4.4 Maintenance debt and integrity

For fixed deficit `f > 1e-12`:

```text
debt[k] = debt[0] + k*f
integrity[k] = integrity[0] - k*0.25*f/max(R,1e-9)
```

For fully paid maintenance:

```text
debt[k] = max(0, debt[0] - k*0.2*D)
```

### Recommendation

- Schedule branch change, debt zero, strict `debt > 4R`, and `integrity <= 0`.
- Verify solved crossings using neighboring integer ticks.
- Protect any cohort distribution straddling a death boundary.
- Never perform endpoint-only death checks.

```text
schedule_debt_integrity(org):
    candidate = earliest_real_crossing()
    for tick in candidate-2 .. candidate+2:
        replay_declared_one_tick_map(tick)
        if integrity <= 0 or debt > 4*R:
            schedule provisional death at tick
            return
```

The crossing tick must still run toxin, age support, and the age-hazard draw before final death, matching the selected engine's declared order.

---

## 4.5 Toxin injury and decay

Current order:

```text
if toxin > tolerance:
    integrity -= 0.0015*(toxin-tolerance)
toxin *= 0.999
```

For `a=0.999`, before external toxin/detox events:

```text
toxin[k] = a^k * toxin[0]
```

If `m` ticks remain above tolerance:

```text
integrity_loss = 0.0015 * (
    toxin[0]*(1-a^m)/(1-a) - m*tolerance
)
```

### Recommendation

- Lazy analytic threshold map for individual event-v2.
- Toxin-relative-to-tolerance buckets plus representative tails for hybrid.
- Split/materialize on digestion, detox, repair, or predicted death.
- Never compute cohort damage from mean toxin alone; positive-part damage is convex and mean toxin underestimates tail injury.

---

## 4.6 Old-age support and death hazard

Raw hazard:

```text
p0(age) = min(0.08, 0.0005*(age/lifespan)^2)
support = min(0.002*body_energy, 0.002*mana, p0*reference_energy)
```

Support is paid before the hazard draw. Normally half comes from mana and half from body, then actual spend becomes heat.

### Event-v2 cumulative hazard

```text
schedule_attrition(org):
    threshold_remaining = org.hazard_threshold - org.hazard_accumulated

    while forecast segment is valid:
        segment_end = next_reserve_or_support_limiter_breakpoint()
        hazard_series = effective_hazard_after_support(segment)
        segment_hazard = sum(-log1p(-p) for p in hazard_series)

        if segment_hazard < threshold_remaining:
            threshold_remaining -= segment_hazard
            advance forecast to segment_end
        else:
            death_tick = binary_search_first_cumulative_crossing(segment)
            verify death_tick-1 and death_tick
            schedule provisional death(death_tick, dependency_epochs)
            return
```

Retain the residual threshold across external state changes; redrawing after every invalidation defines another process.

### Hybrid cohort survival

For abundant homogeneous old-age strata, preserve represented death ticks. The simplest initial scheme is bounded per-tick binomial survival within a cohort:

```text
for tick in represented_epoch:
    apply this tick's maintenance and old-age support to every alive stratum
    deaths_at_tick ~ Binomial(alive_count, p[tick])
    select integer death subcohorts by hazard class
    finalize those deaths at tick before later actions
    alive_count -= deaths_at_tick
```

If the complete per-member hazard path is known and homogeneous, this may be compressed into a multinomial over `{death at tick t1, ..., death at tick tk, survive}`, with `P(death at t)=survival_before_t*p[t]`. A single endpoint binomial provides no death times and is insufficient. Heterogeneous reserve/age/support paths require stratification, a Poisson-binomial/particle treatment, or finer fallback.

Use reserve/age distributions or representative particles, not mean reserves. Low-count lineages and classes whose hazard varies materially remain individually represented or use critical event sampling.

### Pros and cons

- Cumulative hazard removes daily no-death draws but forecasting support is complex.
- Cohort binomial survival is census-sublinear but can erase frailty selection if reserve classes are too broad.
- Delayed death is unacceptable because it creates extra actions and offspring.

---

## 4.7 Death finalization

Death should remain immediate and critical in all scientific modes.

```text
finalize_death(entity_or_integer_subcohort, tick):
    transfer all actual remaining mana to heat
    transfer actual integer body/gut/waste batches to local deposits
    remove from living immediately
    mark occupancy dirty; remove physical occupancy at end-of-tick refresh
    update species and colony state once
    prevent later digestion/action at tick
```

Do not use fractional deaths, average corpse matter, or epoch-end death. In current Rust semantics a dead organism's occupancy can still block same-tick placement until the refresh barrier because `area_free` sees the stale ID; event-v2 should preserve this by default or explicitly version an immediate-release rule change.

---

## 4.8 Colony bonus

Treat colony membership/bonus as a maintenance-rate version.

```text
on_colony_change(member):
    materialize member to current represented prefix
    member.colony_version += 1
    invalidate maintenance, reserve, and age-hazard forecasts
    reschedule from current state
```

Legacy-v1 same-tick behavior remains order-dependent. Event-v2 must define its own total event order.

---

## 5. Mixed policy architecture

## 5.1 Typed policies

```text
ProductionPolicy =
    Disabled
  | ExactOrderedTick
  | ActiveFootprintTick
  | ConservativeTileEpoch { max_dt, allocation_law, error_tol }

ManaPolicy =
    ExactTick
  | LazyClosedForm { max_dt }
  | StateBucketFlow { bin_tol }
  | CohortFlow { representative_particles, error_tol }

MaintenancePolicy =
    ExactTick
  | LazyPiecewise { max_dt }
  | ThresholdEvents
  | CohortEpoch { max_dt, reserve_bins, error_tol }

ToxinPolicy =
    ExactTick
  | LazyAnalyticThreshold
  | StateBuckets { tolerance_relative_bins }
  | CohortFlow { representative_particles, error_tol }

AttritionPolicy =
    BernoulliTick
  | DiscreteCumulativeHazard
  | HazardBuckets { max_dt }
  | BoundedBinomialLeap { max_dt, min_expected, error_tol }

DeathPolicy = ImmediateCritical

FidelityPolicy =
    Fixed
  | Adaptive { strict, balanced, aggressive, hysteresis, fail_closed }
```

Avoid runtime trait-object dispatch in hot loops. Compile a validated policy plan into enum-specialized phases or separate kernels.

## 5.2 Compatibility rules

Reject invalid combinations at configuration load:

```text
legacy-v1 requires all ExactTick/ExactOrderedTick policies
lazy mana/maintenance requires dated heat-source support
cumulative attrition requires a compatible reserve/support forecast
cohort attrition requires authoritative age/reserve distributions
cohort maintenance requires integer pooled inventories and representative tails
positive primary production forces active heat coupling or declared tile approximation
full per-tick snapshots force materialization and remove most lazy benefit
```

Every manifest records engine semantics, each process policy, tolerances, bin definitions, macrostep limit, RNG domains, and supported observables.

## 5.3 Proposal/transaction interface

```text
advance(process, unit, t0, t1, context) -> Proposal:
    dependency_versions
    state_delta
    integer_count_delta
    matter_transfers[]
    energy_transfers[]
    dated_heat_sources[]
    threshold_events[]
    error_estimate
    validity_conditions
```

The coordinator reserves shared resources, validates versions, and commits atomically in canonical order. Failed stochastic proposals use conditional bridges or finer treatment; they are not redrawn independently.

## 5.4 Mixed upkeep materialization

```text
# materialized_tick is the last fully processed upkeep tick.
materialize_upkeep(unit, target_tick):
    while unit.materialized_tick < target_tick:
        next_tick = unit.materialized_tick + 1
        mandatory_tick = min(
            target_tick + 1,              # sentinel when no exact tick is needed
            next_external_touch,
            next_action_or_digestion,
            next_colony_or_status_change,
            lifespan_plus_one,
            predicted_mana_regime_crossing,
            predicted_body_batch_exhaustion,
            predicted_toxin_crossing,
            predicted_support_limiter_change,
            predicted_integrity_or_debt_crossing,
            next_heat_epoch_affecting_footprint,
            next_output_or_audit,
        )

        # Lazy/cohort advancement covers only ticks before the mandatory tick.
        accelerated_end = min(target_tick, mandatory_tick - 1)
        policy = choose_policy(unit, next_tick, accelerated_end)

        if accelerated_end >= next_tick
           and policy is lazy
           and dependency_certificate_is_valid:
            proposal = advance_closed_tick_range(unit, next_tick, accelerated_end)
            proposal_end = accelerated_end
        elif accelerated_end >= next_tick and policy is cohort:
            proposal = advance_cohort_closed_tick_range(unit, next_tick, accelerated_end)
            proposal_end = accelerated_end
        else:
            proposal = replay_one_declared_upkeep_tick(unit, next_tick)
            proposal_end = next_tick

        if proposal.error > budget or dependencies_are_stale:
            split, reduce interval, or replay exactly one next_tick
            continue

        commit proposal transactions and dated heat exactly once
        enqueue threshold/hazard/death events
        unit.materialized_tick = proposal_end
```

Dated heat must be materialized before dependent diffusion, primary production, heat observations, output, or audit.

---

## 6. Adaptive policy selection

### Always protect from aggregation/fall back

- rare lineage/species/local trait class;
- new mutant or sexual hybrid founder;
- near reserve, toxin, debt, integrity, lifespan, or death threshold;
- active attack, magic, mating, reproduction, or colony transition;
- contested/steep primary-production region;
- user-selected organism or exact shadow region;
- high embedded error or repeated proposal rejection.

### Eligible for lazy individual maps

```text
coefficients and dependency versions fixed
no external mutation before barrier
all threshold ticks known
primary production inactive or certified uncoupled
heat outputs can retain correct dates
no requested output forces intermediate materialization
```

### Eligible for upkeep cohort/state bucket

Initial calibration criteria:

```text
unprotected local count >= 128
local lineage count >= 32
upkeep-rate coefficient of variation <= 0.10
max hazard-probability difference <= 0.03
no distribution straddles a critical threshold
normalized heat/resource gradient <= 0.05
expected bulk events >= 20
split-vs-merged error <= half local budget
conditions stable for multiple adaptation epochs
```

### Must split or reduce interval

```text
count < 64
rate/hazard spread exceeds tolerance
threshold-tail probability exceeds rare-event budget
resource consumption > 10% per leap
full-step vs two-half error exceeds tolerance
repeated leap rejection or class churn
```

If strict mode still fails at one tick, split to individuals or stop as out-of-contract.

---

## 7. Complexity expectations

| Scheme | Target upkeep cost | Limitation |
|---|---|---|
| Current exact | `O(N)` per tick | mandatory whole-organism pass |
| Rotating scheduler + lazy state | `O(N/m + touches + breakpoints)` | naive form biased; frequent touches restore linear work |
| Fixed analytic batch | `O(N/Δ + touches + breakpoints)` | actions and heat barriers shorten intervals |
| Event-v2 threshold clocks | `O(events + breakpoints + touches)` | per-capita actions remain linear over long horizons |
| State buckets | `O(K + class crossings)` | high-dimensional classes can approach `N` |
| Cohort upkeep | `O(K*R + critical events)` | unsafe heterogeneity forces splitting |
| Adaptive hybrid | `O(I + K*R + L + critical + boundaries)` | worst-case ecology correctly falls back to linear |

For 10k organisms, event-v2 lazy/threshold policies may be enough. For 100k–1M, state buckets/cohorts and spatial aggregation are required.

---

## 8. Validation plan

### Deterministic mechanism tests

Compare each accelerated map against repeated one-tick event-v2 updates over randomized states and external-event schedules:

1. mana-only decay;
2. mana-target crossing;
3. mixed mana/body maintenance;
4. sorted multi-batch depletion;
5. debt recovery and strict death threshold;
6. toxin threshold and cumulative damage;
7. old-age support limiter changes;
8. shared-footprint production;
9. death-before-digestion/action ordering;
10. colony formation/dissolution invalidation.

### Bias stress tests

- Rotating period commensurate with action delays.
- Equal-mean cohorts with different reserve/toxin variance.
- Many producers sharing one hot patch.
- Organisms one tick from debt/integrity death.
- Mixed old-age reserve classes and frailty selection.
- One rare mutant or last lineage member.

### Statistical acceptance

Use checkpoint forks from the exact Rust oracle and compare ensembles:

- survival and age-at-death curves;
- support spending and reserve distributions;
- starvation/toxin/age mortality;
- actions, reproduction, and failed-resource rates;
- lineage extinction and mutant establishment;
- heat/resource spatial spectra;
- exact matter and bounded energy conservation.

Use equivalence margins, not “no statistically significant difference.” Require convergence as `Δ`, bins, and cohort thresholds tighten.

### Scale campaign

Run fixed-area and fixed-density scenarios at:

```text
10k, 30k, 100k, 300k, 1M organisms
```

Record compression, wall time, memory, fallback rate, class churn, error, and accuracy per CPU-hour.

---

## 9. Recommended implementation order

1. Instrument reserve regimes, threshold margins, old-age counts, heat contention, external-touch frequency, and potential bucket compression.
2. Add the exact Rust zero-primary-production guard and heat-neighbor indexing.
3. Add typed policy configuration, counter RNG, dependency epochs, timing wheel, and dated transaction ledger.
4. Implement event-v2 mana, maintenance, toxin, and threshold maps.
5. Add cumulative age hazard with support/reserve invalidation.
6. Add one-tick state buckets while interactions remain individually represented.
7. Add local upkeep cohorts with pooled integer inventories and representative reserve/toxin/age particles.
8. Add bounded cohort attrition.
9. Add conservative spatial primary-production epochs.
10. Add adaptive switching, then conduct the 10k→1M convergence campaign.

---

## 10. Bottom line

Use different upkeep models by process:

```text
mana and toxin:
    lazy analytic maps

maintenance, debt, integrity, and support:
    piecewise maps + breakpoint events

old-age stochastic death:
    cumulative hazard for individuals
    bounded binomial survival for abundant cohorts

primary production:
    active-set per-tick transfer where contested
    conservative tile model only under explicit approximation/error control

death:
    always immediate, integer, and critical
```

This mixed design is scientifically stronger and faster than uniformly batching all organisms. It remains honest about the limit: event-v2 is output-sensitive but not universally sublinear; true census-sublinear upkeep requires state buckets/cohorts when the population is locally redundant.

---

## 11. Literature basis

Relevant algorithm families:

- Gillespie stochastic simulation and Gibson–Bruck next-reaction methods.
- Cumulative intensity/time-change methods for nonhomogeneous hazards.
- Davis piecewise-deterministic Markov processes.
- Cao–Gillespie–Petzold adaptive tau-leaping.
- Tian–Burrage bounded/binomial leap methods.
- Anderson post-leap conditional checks.
- de Roos structured-population cohort methods.
- Scheffer et al. ecological super-individuals.
- Lie/Strang operator splitting.
- Berger–Colella conservative AMR.
- Varghese–Lauck hierarchical timing wheels.

These methods provide tools, not proof of validity for this model. The exact Rust oracle, mechanism tests, convergence ladders, and rare-event validation remain mandatory.
