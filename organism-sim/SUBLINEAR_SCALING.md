# Sublinear Scaling Research for Multi-Day Organism Simulations

## Executive finding

The current Rust port solves the constant-factor problem but not the population-growth problem. Its work remains approximately proportional to the number of living organisms.

A universal exact sublinear algorithm is impossible under the current rules because every organism:

- pays upkeep every tick;
- may digest every tick;
- may experience an age hazard every tick;
- acts at a positive constant rate;
- can emit heat that influences later organisms in the same tick.

If all `N` organisms perform observable work at a constant rate, any exact serial simulator has an amortized lower bound of **Ω(N)**. A faster queue cannot remove events that genuinely happen.

The recommended design therefore has two stages:

1. **Event-v2 versioned event engine:** remove avoidable scans and make work proportional to due events and active regions. It defines a new organism-phase law and counter-based RNG semantics. Per-entity decay equations and waiting-time marginals can be preserved, but the global joint law is not identical to legacy-v1 because legacy interleaves every organism's upkeep, digestion, heat, death, and action in shuffled order. It improves quiet/sparse periods but retains a linear worst case.
2. **Adaptive spatial particle-cohort engine:** protect rare and scientifically important organisms from aggregation while compressing abundant, locally homogeneous organisms and remote smooth space. Protected organisms still experience approximate cohort/field boundaries, so their trajectories are not exact. This is the route to genuinely sublinear cost in census population.

The target should be:

```text
cost proportional to represented ecological complexity,
not cost proportional to census population
```

The exact Rust engine remains the oracle and selectable reference mode.

### Empirical compressibility result

The observation-only campaign in [`COMPRESSIBILITY.md`](COMPRESSIBILITY.md) found that the design is **not yet enough for useful conservative sublinearity** in the current ecology. Across three exact runs, exact-state keys and lineage-safe representation remained 100% of census; species-safe representation had 84–98% median represented work. Only an exploratory guild-level distributional cohort reached 38–70% of final census, before implementation overheads. Every organism had an action deadline within eight ticks, and exact heat/deposit/occupancy support exceeded census in the 10,000-tick run.

The architecture below remains a research path, not an empirical performance guarantee. It requires a non-permanent rare-lineage representation, aggregate actions, bounded critical-reserve cohorts, and spatial aggregation before a sublinear claim can be retested.

---

## 1. Current complexity

Let:

- `N` = living organisms;
- `D` = deposit positions;
- `B` = batches per inventory;
- `C` = active heat chunks;
- `S` = cells per chunk;
- `A` = organisms whose actions are due;
- `Q` = local cells and occupants examined by decisions;
- `E` = active effects;
- `R` = corpses;
- `G` = species representatives.

The current native tick is approximately:

```text
O(N log N)     deterministic sort before shuffle
+ O(N)         upkeep and digestion eligibility
+ O(A + Q)     scheduled decisions and local interactions
+ O(D * B)     deposit production
+ O(D * B)     decomposition
+ O(C * S)     heat stencil
+ O(C^2)       current linear searches for neighbor source chunks
+ O(E + R)     expiry scans
+ O(births * G) species assignment
```

The occupancy hash already prevents global all-pairs behavior. The main remaining problem is mandatory whole-population work.

### Immediate exact improvements

These do not make the engine universally sublinear, but should be completed before approximation:

1. Skip Rust primary-production footprint/heat work when its rate is zero.
2. Replace heat diffusion's repeated linear neighbor search with a chunk-key index, removing the accidental `O(C²)` term.
3. Maintain the same sorted-ID shuffle input incrementally, if this can be proven to reproduce legacy-v1 exactly; otherwise move the ordering change to event-v2.
4. Replace effect and corpse scans with deadline buckets or a timing wheel.
5. Maintain deposit indexes for `has_energy`, `has_headroom`, and `heat_present`.
6. Use incremental matter/energy summaries, rolling audit shards, and full audits only at checkpoints.
7. Use a metric tree such as a VP-tree for exact nearest-species lookup if species count becomes large; the genome distance is suitable for metric indexing.
8. In event-v2/hybrid, compact dead organisms into small genealogy records rather than retaining full genomes, policies, inventories, and caches forever. This changes the current full-state digest and is not a legacy-v1 identity-preserving optimization.

These changes raise the exact-engine ceiling and make it a stronger validation oracle.

---

## 2. Why event queues alone do not solve it

A hierarchical timing wheel can dispatch due events in amortized `O(1)` time. It avoids scanning entities that have no event due.

However, current action delays are bounded and independent of population. If each organism acts every few ticks, the number of action events over `T` ticks is still `Θ(NT)`.

Therefore:

```text
exact event queue:
    excellent for expiries, sparse hazards, and quiet entities
    not sufficient for a million frequently acting organisms
```

Parallelism has the same limitation. With `P` cores it can approach `O(N/P)` wall time, but total work remains linear and eventually exceeds any fixed machine.

---

## 3. Event-v2: output-sensitive versioned event engine

This should be a new semantics version, not a silent modification to the current digest contract.

```text
legacy-v1  current serial xoshiro engine; exact trajectory oracle
event-v2   counter RNG + event queues + lazy state; deterministic within v2
hybrid-v1  aggregation-protected individuals + approximate cohorts/AMR
```

Event-v2 should promise explicitly enumerated per-entity equations and waiting-time marginals, exact matter conservation, bounded energy error, and deterministic replay within v2. It must **not** claim the same global stochastic law as legacy-v1: avoiding the full shuffled organism pass changes which earlier organisms' heat/deaths are visible to later decisions. A fully equivalent prefix-source mechanism may still require Ω(N) work and can be retained only as a validation fallback.

### 3.1 Hierarchical timing wheel

Schedule:

- organism actions;
- digestion successes;
- age-hazard events;
- effect expiry;
- corpse expiry;
- maturity and cooldown boundaries;
- deposit/heat wakeups;
- rolling audit shards.

A fixed hierarchical wheel is preferable to a calendar queue because its cascade and ordering rules are deterministic.

### Scheduler pseudocode

```text
advance_to(target_tick):
    while now < target_tick:
        barrier = min(
            wheel.next_due_tick(),
            next_required_heat_barrier(),
            next_nonlinear_sink_or_source_boundary(),
            next_output_or_audit_tick(),
            target_tick,
        )

        if environment_can_advance_as_one_valid_block(now, barrier):
            # Advance only the open interval (now, barrier): ticks now+1
            # through barrier-1. The barrier tick remains unprocessed.
            advance_open_interval_with_dated_sources(now, barrier)
            now = barrier
        else:
            now += 1                    # honest per-tick fallback to this tick

        # Required semantic order:
        # diffusion -> production -> effect expiry -> decomposition ->
        # organism events -> corpse expiry -> occupancy refresh -> audit
        for phase in PHASE_ORDER:
            events = wheel.drain(now, phase)
            events = recompute_and_reschedule_stale_events(events)
            order_by_total_event_key(events)   # radix O(A), or sort O(A log A)

            batches = build_spatially_bounded_conflict_sets(events)
            for batch in batches:
                if complete_read_write_sets_are_disjoint(batch):
                    prepare in parallel from the correct key-prefix state
                    commit in deterministic event-key order
                else:
                    process serially in deterministic event-key order
                    retry invalidated preparation after earlier commits

            enqueue resulting events

        # Newborns are ineligible until at least now+1. Movement occupancy is
        # immediate; body-size occupancy remains deferred to the refresh phase.
        if output_requested(now):
            materialize only requested state
```

Each barrier tick is then processed exactly once by `PHASE_ORDER`; block advancement must not include that tick. Event-v2's organism phase materializes only due/touched actors and dependency state, commits them by event key, and records deferred reservoir losses as dated sources. This is a new phase law rather than the legacy shuffled all-organism prefix.

Event keys should have a total order:

```text
EventKey = (
    due_tick,
    phase,
    random_priority,
    stable_entity_id,
    event_sequence,
)
```

### 3.2 Counter-based randomness

The current shared RNG couples unrelated entities: skipping one draw changes every later draw. Event simulation should instead key random numbers by event identity.

```text
random = RNG(
    master_seed,
    engine_version,
    domain,
    tick_or_epoch,
    entity_id,
    event_sequence,
    draw_index,
)
```

Use separate domains for ordering, digestion, attrition, action selection, movement, reproduction, mutation, and social events.

For a random order among organisms active at tick `t`:

```text
for each active organism id:
    priority = RNG(seed, ORDER, t, id)
sort only active events by (priority, id)
```

This has the same uniform relative-order law as restricting a random permutation to the active subset, without shuffling every living organism. It does **not** preserve legacy-v1's shared-xoshiro draw sequence or exact interleaving. Event-v2 must explicitly define whether inactive organisms' upkeep is logically materialized before the active event or represented as prefix heat/death sources. The current engine interleaves upkeep, digestion, and action in shuffled organism order, so a phase-wide lazy update would be a semantic change.

Parallel preparation is legal only when complete read/write sets are disjoint or when later events are validated against all earlier key-prefix commits. Earlier events can alter heat, occupancy, deposits, target survival, and observations used by later decisions.

### 3.3 Versioned invalidation

Predicted events become stale when an organism moves, eats, is attacked, joins a colony, changes inventory, or dies.

```text
schedule(event):
    event.dependencies = {
        actor_version,
        optional_target_version,
        deposit_version,
        occupancy_cell_epochs,
        heat_tile_epoch,
    }
    wheel.insert(event)

dispatch(event):
    if any dependency epoch is stale:
        recompute event from current state
        reschedule it when still eligible
        return

    materialize required state to event.tick
    execute event
```

A single entity version is insufficient for spatial and environmental predictions. Stale actions, digestion, and hazards must be recomputed or explicitly canceled because eligibility disappeared; silently discarding them can lose future behavior. Tombstones are periodically compacted when their ratio exceeds a fixed deterministic threshold.

### 3.4 Lazy organism dynamics

Store:

```text
last_materialized_tick
state_version
scheduled_action
scheduled_digest
scheduled_attrition
piecewise reservoir state
```

Only materialize an organism when it acts, is observed, or is externally affected.

#### Mana decay and maintenance

For a stable interval:

```text
q = 1 - mana_decay
D = basal * reference_energy * maintenance_multiplier * (1 - colony_bonus)
M = D * mana_preference

mana[k] = q^k * mana[0] - M * (1 - q^k) / (1 - q)
```

Compute the first tick where mana can no longer pay its share, then switch to the body-energy phase. Similar piecewise formulas handle body depletion and maintenance debt.

```text
materialize_upkeep(org, target_tick):
    while org.last_tick < target_tick:
        breakpoint = earliest(
            target_tick,
            mana_threshold,
            body_batch_exhaustion,
            debt_death,
            toxin_threshold,
            age_support_transition,
        )

        analytically_advance_stable_interval(org, breakpoint)
        transfer exact source loss to dated heat ledger
        org.last_tick = breakpoint
        apply breakpoint transition
```

Closed forms change floating-point bits relative to repeated per-tick multiplication, so this belongs in event-v2, not bitwise legacy-v1.

Two couplings force explicit breakpoints or per-tick fallback:

- With positive primary production, each organism removes footprint heat every tick. Lazy upkeep is valid only when heat is proven absent or the coupled sink regime has an exact block solution.
- After lifespan, support spends mana/body energy and emits heat before each age-hazard trial. Cumulative-hazard prediction must integrate those transfers and their reserve thresholds, not schedule death from age alone.

#### Toxin and deterministic damage

With toxin decay `a = 0.999`:

```text
toxin[k] = toxin[0] * a^k

loss_above_tolerance =
    0.0015 * (toxin[0] * (1 - a^k) / (1 - a) - k * tolerance)
```

Solve the threshold crossing, check neighboring integer ticks, and schedule integrity death if necessary.

### 3.5 Waiting-time transformations

#### Digestion

Repeated Bernoulli trials with constant probability `p` can be replaced by an equivalent geometric waiting time. Event-v2 should deliberately define the conventional `u < p` Bernoulli law:

```text
schedule_next_digest(org):
    if gut_empty or p <= 0:
        return
    if p >= 1:
        wait = 1
    else:
        u = random(DIGEST_WAIT, org.id, org.digest_epoch)
        wait = floor(log(1-u) / log(1-p)) + 1

    wheel.insert(DigestEvent(now + wait, org.id, org.version))
```

The literal current code succeeds when `u <= p` because it rejects only `u > p`; with a discrete 53-bit draw, even `p=0` has a vanishingly small success probability. The `p<=0` branch is therefore an intentional event-v2 semantic correction unless the induced discrete probability is modeled exactly. Gut mutation invalidates and reschedules the event.

#### Time-varying age hazard

A sequence of independent hazards `p[t]` can be represented by cumulative hazard:

```text
schedule_attrition(org):
    u = random(ATTRITION_WAIT, org.id, org.attrition_epoch)
    threshold = -log(1-u)

    find earliest future tick t such that:
        sum(i=now+1..t, -log(1-p[i])) >= threshold

    wheel.insert(AttritionEvent(t, org.id, org.version))
```

Use piecewise formulas and monotonic search between energy/mana breakpoints. External state changes invalidate the prediction.

### 3.6 Active deposits

Maintain mutation-driven indexes:

```text
has_energy
has_headroom
heat_at_deposit

production_active = positions where heat > 1e-12 and total_headroom > 1e-12
decomposition_active = positions with positive batch energy
```

```text
on_deposit_mutation(position):
    recompute energy/headroom membership for this position
    recompute production membership using current heat

on_heat_cell_change(position, old_heat, new_heat):
    if a deposit exists at position and crossing_1e_minus_12(old_heat, new_heat):
        recompute production membership for this position

# Alternative when diffusion is block/lazy: compute the exact spatial
# intersection of headroom deposits and above-threshold deposit heat at the
# production barrier; deposit mutation alone is not enough.

produce_deposits():
    for position in production_active:
        process current production formula
        update membership

decompose():
    for position in decomposition_active:
        process batches with positive energy
        update membership
```

Worst-case work is still `O(D)` if every deposit is active, and default runs may keep most deposits energetic. Lazy closed-form decomposition is useful only if its released energy is represented as a **dated per-tick heat-source series**: decomposition heat added on tick `t` first diffuses on `t+1`. Lumping all deferred heat at materialization changes production and organism behavior.

### 3.7 Sparse/dense heat

Heat diffusion is linear between sources and sinks:

```text
H(t+1) = A * H(t) + sources(t)
```

Use two representations per tile:

- sparse exact nonzero cells plus frontier;
- flat dense cells when sparse overhead becomes larger.

```text
diffuse_sparse(tile):
    load cross-tile halo values from the same old-time snapshot
    candidates = exact_nonzero_cells ∪ generated_neighbors

    for destination in canonical_order(candidates):
        center = old[destination]
        neighbors = [up, down, left, right] in fixed current order
        for a neighbor in ungenerated space:
            neighbor = center              # current no-flux rule
        value = (1 - 4*rate)*center + rate*sum(neighbors)
        new[destination] = max(0, value)   # current clamp semantics

    swap buffers

if density(tile) > dense_threshold:
    convert_to_dense(tile)
```

Do not prune small heat values in an exact mode; positive diffusion eventually makes support dense. Hybrid mode may use an error-bounded threshold or AMR.

### 3.8 Event-v2 complexity

Define:

- `A_t` = due organism events;
- `D_t` = active/touched deposits;
- `H_t` = active heat support or queried tiles;
- `Q_t` = local spatial candidates;
- `X_t` = expirations;
- `Z_t` = stale queue entries.

With a timing wheel and comparison sorting, the conservative bound is:

```text
O(A_t log A_t + conflict_partition_work
  + D_t + heat_materialization_work + Q_t + X_t + Z_t)
```

Fixed-width stable radix ordering can reduce event ordering to `O(A_t)`. A spatially bounded conflict algorithm is required before claiming linear conflict partitioning. Heat work must include every intermediate block/tile materialized across a skipped interval, not only final nonzero support.

This is sublinear only when active sets are sublinear. Its worst case remains optimal linear work.

---

## 4. Hybrid-v1: genuine sublinear census scaling

To support 100,000–1,000,000+ organisms, the engine must stop representing every abundant organism independently.

### Core rule

Protect individual representations where emergence occurs; aggregate redundant bulk. These individuals are protected **from aggregation**, but interactions with cohorts and AMR fields remain approximate.

#### Always protected from aggregation

- rare lineage clusters;
- new mutants and hybrid founders;
- young species;
- phenotype extremes;
- organisms near extinction/fixation thresholds;
- invasion fronts;
- low-count predators, prey, or mates;
- active lethal/status interactions;
- newly formed colonies or important social structures;
- user-selected organisms and focal regions.

#### Eligible for cohorts

- abundant organisms;
- same local spatial leaf;
- similar genomes and behavior responses;
- similar age/action phase and physiological state;
- safely away from maturity, toxin, integrity, energy, and species boundaries;
- locally well mixed with low gradients.

### 4.1 Cohort state

A cohort key is approximately:

```text
(
    adaptive_spatial_leaf,
    lineage_cluster,
    genotype_bin,
    behavior_bin,
    age_stage,
    action_phase,
    energy_bin,
    mana_bin,
    toxin_integrity_bin,
    status_class,
)
```

Authoritative cohort state contains:

```text
integer organism count
integer pooled molecule counts by compartment
pooled chemical energy and mana
age and action-phase histograms
selected trait/physiology means and second moments
cross-moments that drive fitness
4-16 weighted full-state representative particles
min/max or tail sketches for threshold variables
lineage/species frequency summaries
small sampled genealogy reservoir
```

Do not use one average organism. Nonlinear fitness requires representative particles and selected moments.

### 4.2 Adaptive spatial hierarchy

Attach cohorts to adaptive leaves aligned with world chunks.

- Fine leaves retain exact occupancy and discrete deposits.
- Coarse leaves retain counts, capacities, molecule totals, energy, gradients, and encounter statistics.
- Heat uses conservative finite-volume fluxes.
- Fine/coarse interfaces use refluxing so energy crossing the boundary is counted once.
- Refinement halos surround aggregation-protected organisms and interaction fronts.

This is necessary because if occupied area grows linearly with population and every cell stays fine, spatial work also remains linear.

### 4.3 Merge criteria

Initial calibration values—not permanent constants:

```text
can_merge(group):
    return (
        unprotected_count >= 128
        and local_lineage_count >= 32
        and genotype_diameter <= 0.02
        and max_action_probability_difference <= 0.03
        and hazard_driver_CV <= 0.10
        and no_threshold_is_straddled
        and normalized_heat_resource_gradient <= 0.05
        and expected_interactions_per_horizon >= 20
        and embedded_merge_error <= local_error_budget / 2
        and no_protected_object_or_active_critical_event
    )
```

Require conditions to hold for multiple adaptation windows before merging.

### 4.4 Split/refine criteria

Use hysteresis to avoid merge/split thrashing:

```text
must_split(cohort):
    return (
        count < 64
        or rare_or_novel_lineage_present
        or genotype_or_action_variation > tolerance
        or threshold_crossing_possible
        or local_gradient > 0.10
        or expected_critical_events < 20
        or attack_damage_is_large_vs_integrity_spread
        or repeated_leap_rejection
        or embedded_error > budget
        or exact_observer_enters_refinement_halo
    )
```

Deaggregation reconstructs a statistically controlled sample; it cannot recover lost individual histories. The manifest must record that fact.

---

## 5. Bulk stochastic updates

A global Gillespie SSA is not sufficient because realized event count still scales with population. Use:

- next-reaction handling exact for the derived cohort model's rare/critical channels;
- bounded tau-leaping for abundant bulk channels.

### 5.1 Critical channel classification

A channel is critical if a small number of firings could:

- exhaust a population or molecule resource;
- eliminate a rare lineage;
- cross maturity, toxin, integrity, or energy thresholds;
- create a new mutant/species;
- trigger a lethal attack or important social event.

Critical channels use exact event sampling for the **derived cohort stochastic model**. They are not exact relative to the original individual tick scheduler once aggregation has occurred.

### 5.2 Bounded cohort leap

Use binomial or multinomial draws rather than unconstrained Poisson draws so populations and resources cannot become negative.

```text
advance_cohort(cohort, tau):
    classify channels as critical or bulk
    interval_end = now + tau

    while now < interval_end:
        critical_time = next_critical_event_time()
        sub_end = min(critical_time, interval_end)

        # Leap bulk channels only up to the next critical event.
        dt = sub_end - now
        bulk_path = draw_or_reuse_counter_keyed_bulk_path(cohort, now, dt)

        for mutually_exclusive_transition_group:
            probabilities = integrated_first_transition_probabilities(dt)
            if sum(probabilities) > 1:
                reduce dt and retry using a conditional bridge
            counts = multinomial(eligible_count, probabilities + [no_transition])

        for renewal/repeated channels such as multiple actions over dt:
            use action-phase histograms and substeps, or a validated compound count law

        reserve partners, placement, molecule counts, and energy

        if reservation_failed or post_leap_error > tolerance:
            # Do not redraw an unrelated path after rejection.
            condition/split the existing random path (post-leap bridge),
            or split cohort / fall back to fine one-tick handling
            retry

        commit_integer_transfers()
        update_particles_and_moments_conditionally()
        now = sub_end

        if now == critical_time:
            process that critical event
            recompute affected propensities before continuing
```

### 5.3 Birth and mutation pseudocode

```text
bulk_reproduction(parent_cohorts, tau):
    candidate_attempts = bounded_draw(eligible_action_phase_counts)
    matched_attempts = compatibility_weighted_hypergeometric_match(candidate_attempts)

    # Convert every resource to the same unit: feasible attempted events.
    energy_feasible_attempts = count_attempts_payable_by_parent_energy(matched_attempts)
    attempts = min(matched_attempts, energy_feasible_attempts)

    # Preserve current ordering: energy is committed and cooldown begins before
    # the success draw and remains spent on probability/placement failure.
    commit_attempt_energy_to_heat(attempts)
    apply_reproduction_cooldowns(attempts)
    successes = bounded_success_draw(attempts, fertility_and_strategy_probabilities)

    matter_feasible_children = count_children_supported_by_integer_body_matter(successes)
    placement_feasible_children = count_available_child_placements(successes)
    created = min(requested_child_count(successes),
                  matter_feasible_children,
                  placement_feasible_children)

    reserve exact integer body matter for created children

    for offspring_class sampled from representative parent particles:
        child_genome = current_recombination_and_mutation_kernel(parents)

        if novel_or_rare_or_tail_or_species_boundary(child_genome):
            create individually represented, aggregation-protected child with weight 1
        else:
            add integer child count to matching cohort

    apply exact pooled matter transfers
```

Never mutate an entire cohort at once.

### 5.4 Death pseudocode

```text
bulk_death(cohort, tau):
    partition representative particles by hazard class
    death_counts = bounded_draw_per_hazard_class(tau)

    if hazard variation too large:
        split cohort and retry

    for class, deaths in death_counts:
        remove selected subcohort moments/particles
        transfer integer body/gut/waste matter to local deposits
        transfer mana and committed effect energy according to current rules
```

---

## 6. Conservative ledgers

Approximation must not weaken physical invariants.

### Matter

- Population and molecule counts stay integer.
- Every event is an integer stoichiometric transfer.
- Aggregation never stores authoritative fractional molecule density.
- Splits use balanced allocation so child totals equal parent totals exactly.

```text
transfer_matter(source, destination, molecule_id, requested_count):
    actual = min(requested_count, source.count[molecule_id])
    source.count[molecule_id] -= actual
    destination.count[molecule_id] += actual
    element_ledger.apply_equal_and_opposite_transfer(actual)
```

### Energy

Every transfer uses the actual source debit as the destination credit:

```text
transfer_energy(source, destination, requested):
    actual = source.debit(requested)
    destination.credit(actual)
    energy_ledger[source] -= actual
    energy_ledger[destination] += actual
```

Use deterministic compensated reductions and explicit residual buckets rather than silently clipping floating error.

### Auditing

- constant-time incremental ledgers on every mutation;
- deterministic rolling shard audit each tick/macrostep;
- full independent audit at checkpoints and run completion.

A rolling audit gives eventual full coverage without scanning all state every tick.

---

## 7. Adaptive error control

Conservation alone does not prove ecological correctness. The engine needs an explicit weak-error contract.

### Local estimators

1. **Bin error:** compare merged cohort rates with a temporary split.
2. **Particle error:** compare full representative set with half the representatives.
3. **Time error:** compare one full leap with two coupled half leaps on sampled cohorts.
4. **Spatial error:** compare a coarse leaf with temporary fine prolongation.
5. **Interaction error:** compare encounter kernels with exact shadow tiles.
6. **Rare-event risk:** estimate probability of an unrepresented tail crossing a novelty/extinction threshold.

### Adaptive macrostep

```text
choose_tau(leaf):
    tau = configured_max_tau

    loop:
        acceptable = true
        for each state variable and channel:
            # Recompute these for the current candidate tau.
            (mu, sigma2) = estimate_change_and_variance(channel, tau)
            scale = max(abs(state), state_floor)
            if abs(mu) > epsilon*scale
               or sqrt(sigma2) > epsilon*scale
               or known_boundary_occurs_before(tau):
                acceptable = false
                break

        if acceptable:
            return tau
        if tau == 1:
            split/refine, use exact derived-channel handling, or stop as out-of-contract
        tau = max(1, floor(tau / 2))
```

Start with integer `tau <= 8`; increase only after validation.

### Accuracy-budget behavior

If error exceeds the declared budget, the engine must:

1. split/refine;
2. reduce `tau`;
3. allocate more representative particles or protect more individuals from aggregation;
4. or stop and mark the run outside its approximation contract.

It must never silently merge a protected lineage to meet a performance budget.

---

## 8. Hybrid scheduler pseudocode

```text
simulate_hybrid(target_tick):
    while time < target_tick:
        process_and_drain_all_deadlines_already_due_at(time)

        # Adapt representation at deterministic epochs.
        indicators = measure_gradients_variance_rarity_and_error()
        protect_rare_novel_tail_frontier_and_critical_objects()
        refine_unsafe_leaves_and_cohorts(indicators)
        merge_only_stable_homogeneous_candidates_with_hysteresis()
        journal_adaptation_decisions()

        # Choose a proposed interval, then clip it at every mandatory deadline.
        for leaf in canonical_leaf_order:
            classify_critical_channels(leaf)
            tau[leaf] = choose_tau(leaf)

        interval_end = min(
            time + minimum_required_coupling_step(tau),
            next_effect_expiry,
            next_protected_individual_event,
            next_critical_cohort_event,
            next_predicted_resource_or_threshold_boundary,
            next_output_or_audit,
            target_tick,
        )

        # Draw aggregate cohort paths for the interval. Assign bounded event
        # counts to explicit tick/phase buckets (or dated source series), so
        # environment/status ordering is not lost. Rejected refinement reuses a
        # conditional bridge rather than drawing an unrelated path.
        assert interval_end > time
        proposals = propose_cohort_paths(time, interval_end)
        if proposals.error > budget:
            refine_or_conditionally_split_interval()
            continue

        for tick in inclusive_range(time + 1, interval_end):
            # Preserve the declared hybrid phase order at every represented tick.
            diffuse_heat_one_tick_with_conservative_AMR()
            apply_deposit_production_for_tick()
            expire_effects_and_release_energy_for_tick()
            apply_decomposition_and_record_dated_heat_sources()

            process_due_aggregation_protected_individual_events(tick)
            process_aggregate_cohort_event_buckets(tick, proposals)

            commit_capacity_bounded_movement_fluxes()
            commit_compatible_mating_and_predation_matches()
            charge_rejected_attempt_costs()
            expire_corpses_and_refresh_occupancy()

            commit_transaction_ledgers()
            reflux_AMR_boundaries()
            reconcile_population_species_and_lineages()
            run_rolling_audit_shards()

        update_full_step_vs_two_half_step_error(proposals)
        time = interval_end
        materialize_only_requested_outputs(time)
        run_full_audit_if_checkpoint(time)
```

This first hybrid design still executes global phase barriers per tick, but cohort work is independent of census count. Later block heat/field stepping is an explicit operator-splitting approximation: it must split at every status/source/deadline, retain dated sources, and pass a full-step versus two-half-step error estimator before acceptance.

---

## 9. Complexity target

Let:

- `I` = individuals protected from aggregation;
- `K` = active cohorts;
- `L` = adaptive spatial leaves;
- `R_c` = bounded aggregate channels per cohort;
- `E_critical` = realized critical events;
- `F` = fine/coarse boundary work.

The hybrid target is:

```text
O(I + K * R_c + L + E_critical + F)
```

Memory is:

```text
O(I * individual_state
  + K * (representative_particles + moments + molecule_totals)
  + L * field_state)
```

This is sublinear in census population `N` when:

```text
I + K + L << N
```

Worst-case fallback remains `Ω(N)` when every organism is rare, distinct, or located on an interaction front. That fallback protects scientific validity.

### Important spatial limit

If density stays fixed while occupied area grows linearly with population, keeping every cell fine also produces linear spatial work. Sublinear population scaling therefore requires both:

- organism cohorts;
- adaptive coarsening of smooth remote space.

---

## 10. Scientific bias register

| Approximation | Main risk | Protection |
|---|---|---|
| One superindividual represents many | synchronized actions and oversized jumps | integer cohort event counts, not cloned actions |
| Mean organism state | Jensen bias and lost correlations | particles, moments, hazard-based splitting |
| Genotype bins | artificial neutrality and boundary artifacts | adaptive medoids, rare/tail protection, convergence tests |
| Bulk mutation | fractional or macroscopic mutants | integer mutation events; novel mutants individually represented |
| Mean-field encounters | lost clustering and repeated contacts | pair-correlation correction, shadow tiles, refined fronts |
| Tau-leaping | depletion and event-order bias | bounded draws, critical derived-model channels event-sampled, conditional post-leap checks |
| Spatial coarsening | numerical diffusion and wrong congestion | conservative AMR, refinement halos, capacity limits |
| Deaggregation | synthetic identities and pedigrees | explicit provenance; never claim recovered trajectory |
| Aggregated social graph | lost topology and motifs | individual-social capability mode |
| Forced protected-state budget cap | loss of rare diversity | stop/flag rather than silently merge protected state |

Each run manifest must record engine version, tolerances, merge/split policy, RNG scheme, field resolution, and supported observables.

---

## 11. Validation plan

The exact Rust engine is the oracle.

### Checkpoint-fork protocol

```text
run exact engine to checkpoint
fork identical state:
    branch A continues exact
    branch B enables hybrid mode
compare ensembles after the switch, not pathwise digests
```

Approximation-off hybrid mode may reproduce an event-v2 digest only if it uses identical event-v2 scheduling, RNG domains, and floating semantics. Legacy-v1 remains a separate xoshiro/serial oracle and cannot be expected to share that digest.

### Mechanism-isolation experiments

1. Neutral drift between identical labeled lineages.
2. One-mutant establishment across selective advantages.
3. Mutation-selection balance and phenotype tails.
4. Predator-prey attack and extinction distributions.
5. Sexual assortment and species branching.
6. Resource-limited reproduction and molecule-specific blocks.
7. Spatial invasion fronts and rare founder surfing.
8. Crowding, collision, and failed movement costs.
9. Heat gradients and thermophile selection across AMR boundaries.
10. Magic/effect expiry and low-count lethal outcomes.
11. Alliances, colonies, degree distributions, and motif retention.

### Primary comparison metrics

- population and turnover time series;
- extinction/fixation/establishment probability;
- species richness and Hill diversity;
- trait distributions and tail quantiles;
- lineage survival curves and abundance spectra;
- resource and energy distributions;
- spatial autocorrelation, pair correlation, and front speed;
- attack, mating, reproduction, and failure rates;
- exact matter and bounded energy conservation.

Use equivalence margins, not failure to reject a difference.

### Convergence ladder

For every scenario compare:

```text
exact
hybrid strict:     small bins, tau <= 2, fine leaves
hybrid balanced:   medium bins, tau <= 8
hybrid aggressive: large bins, tau <= 16-32, coarser leaves
```

Errors should decrease as resolution tightens. Non-monotonic convergence signals a broken estimator or interaction kernel.

### Scale campaign

Measure both fixed-area and fixed-density growth:

```text
10k, 30k, 100k, 300k, 1M census organisms
```

Record:

- census compression `N / (I + K)`;
- wall time per simulated 1,000 ticks/day;
- memory high-water mark;
- exact/cohort/AMR work shares;
- refinement churn and leap rejection;
- accuracy per CPU-hour;
- conservation and cumulative error budgets.

At large scales, use stratified exact shadow tiles and short exact continuations because a full exact reference will be unavailable.

---

## 12. Recommended implementation sequence

### Phase 0 — measure compressibility

Instrument long exact runs to record:

- due actions per tick;
- gut-bearing and old-age organisms;
- active/full/cold deposits;
- sparse/dense heat support;
- local genotype/behavior variance;
- rare-lineage counts;
- occupied spatial gradients;
- species count and birth lookup cost.

Do not implement cohorts until these distributions show where compression is safe.

### Phase 1 — legacy-v1-compatible ceiling

- eliminate zero-rate Rust upkeep work;
- remove heat `O(C²)` neighbor search while retaining destination arithmetic order;
- deadline wheels for effects/corpses with identical expiry timing/order;
- active deposit sets with identical position/batch processing order;
- maintain the sorted living-ID sequence incrementally only if it reproduces the current pre-shuffle input exactly; otherwise defer this to event-v2;
- incremental ledgers and rolling audits, while retaining independent full checkpoints;
- VP-tree species lookup only after proving exact nearest/tie behavior.

### Phase 2 — event-v2

- counter-based RNG domains;
- hierarchical timing wheel;
- random priorities for active events;
- versioned invalidation;
- explicit phase-tagged action/effect/corpse events;
- compact dead records under the new event-v2 state/digest contract;
- geometric digestion and cumulative attrition hazards;
- lazy upkeep for stable organisms.

### Phase 3 — one-tick cohorts

Aggregate only homogeneous high-count upkeep, digestion, and attrition while keeping movement, reproduction, mutation, predation, and mating individually represented at fine resolution. These interactions still see aggregate boundary conditions, but this isolates cohort-state error from time and broader spatial approximation.

### Phase 4 — interaction cohorts

Add representative particles, calibrated local encounter kernels, bounded event counts, and individually represented aggregation-protected mutant births. Validate drift and rare establishment before broad ecology.

### Phase 5 — adaptive switching

Add merge/split hysteresis, error indicators, capability modes, deterministic adaptation journals, and checkpoint/fork validation.

### Phase 6 — spatial AMR

Coarsen heat first, then deposits and movement. Add conservative refluxing, refinement halos, and exact shadow tiles.

### Phase 7 — macrosteps

Enable integer tau-leaps only in quiescent leaves. Keep critical derived-model channels and mandatory discrete boundaries event-driven.

### Phase 8 — multi-day campaign

Benchmark 10k→1M populations and select settings from an accuracy-versus-resource Pareto frontier, not from throughput alone.

---

## 13. Recommended decision

Implement **event-v2 first**, because it raises the output-sensitive high-fidelity ceiling and provides scheduler, counter-RNG, invalidation, and ledger infrastructure needed by the hybrid engine. Keep legacy-v1 as the exact trajectory oracle.

Then implement **hybrid-v1** as an explicit opt-in engine:

```text
individuals protected from aggregation
+ integer particle cohorts for abundant homogeneous populations
+ bounded tau-leaping for bulk events
+ next-reaction handling for rare/critical events
+ conservative adaptive spatial fields
+ observable-aware error budgets
```

Do not claim universal logarithmic complexity. Claim:

```text
sublinear work in census population when the ecology is compressible,
with automatic individual/fine-resolution fallback where emergence makes compression unsafe
```

That is the strongest scalable design that remains defensible for evolutionary research.

---

## 14. Literature basis

Useful primary algorithm families:

- Gillespie (1976, 1977): stochastic simulation/direct method.
- Gibson and Bruck (2000): next-reaction method.
- Cao, Gillespie, and Petzold (2006): adaptive tau-leaping.
- Tian and Burrage (2004): bounded/binomial leap methods.
- Anderson (2008): post-leap checks and rejection without bias.
- Elf and Ehrenberg (2004): spatial next-subvolume methods.
- Haseltine and Rawlings (2002): hybrid stochastic/deterministic simulation.
- Scheffer et al. (1995): ecological super-individuals.
- de Roos and structured-population cohort methods.
- Berger and Colella (1989): conservative block-structured AMR and refluxing.
- Varghese and Lauck (1987): hierarchical timing wheels.
- Brown (1988): calendar queues.

These methods provide components, not proof that their combination is valid for this model. The exact Rust oracle, convergence ladder, and rare-lineage validation are mandatory.
