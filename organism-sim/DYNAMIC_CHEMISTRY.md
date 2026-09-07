# Dynamic Environmental Chemistry

**Goal.** Make the artificial chemistry *dynamic* — its spatial composition should change over time — and make **organism products a causal input to local chemistry**, so that organism–environment feedback produces **niche specialization** and makes **engulfment (internal guests) selectively advantageous in specific niches**, analogous to endosymbiosis. Everything must emerge from generic energy/matter accounting; no predator/detoxifier/producer labels.

**Status:** implemented in the Rust kernel behind `dynamic_chemistry_enabled` (default `false`, with no reaction/byproduct work when off). The paired study is recorded in [`experiment_results/dynamic_chemistry/REPORT.md`](experiment_results/dynamic_chemistry/REPORT.md).

---

## Why the baseline is static

The baseline kernel already has:

- a fixed procedural **catalog** (elements → molecules) that never changes,
- **deposits** (matter + chemical energy batches) that only *gain* energy (seasonal recharge), *lose* energy (decomposition → heat), or move through organisms (eat → gut → digest → body/waste),
- a **heat** field with diffusion,
- **seasons** (exogenous global modulation of recharge/decomposition/affinities),
- **biodeposits** (a dead-biomass density field, passive cover).

Two things are missing for the goals above:

1. **The molecular *composition* of the environment never changes.** Molecule batches keep their identity; only their energy and location change. Nothing in the environment converts one molecule into another, so there is no *chemical* state to specialize against — only abundance and location.
2. **Organism products do not feed back into chemistry.** Excretion deposits matter (already), but the *chemical conditions* a neighbor experiences are independent of what neighbors have metabolized. Organisms live in an environment that is indifferent to them.

This design adds the two missing pieces with three coupled generic mechanisms, all local (per-cell), all bounded, all optional.

---

## Mechanisms

### 1. Environmental reaction network (ER)

A small set of **recombinational reactions** `A + B → C` run on deposit cells.

**Rules.** A rule is valid *by construction*: `composition(C) == composition(A) + composition(B)` exactly (element vectors, per unit). Rules are derived deterministically from the catalog at init (`Catalog::reaction_rules(max)`), capped by `reaction_rule_count` (default 6, max 32). Pairs with `A ≤ B` are allowed (dimerization included). When the feature is enabled, catalog generation reserves simple two-element compounds where space permits, ensuring the bounded catalog has a small reaction closure without adding molecule ids at runtime.

**Per-tick step** (after decomposition, before organisms act): for each deposit position, for each rule (per-cell cap 2 reactions/cell/tick), with probability

```
p = environmental_reaction_rate
    × temperature_factor      # 1 + min(heat_cell, 2·E_ref)/(2·E_ref), clamped [1, 2]
    × season_factor           # clamp(season product affinity of C, 0.25, 2)
    × catalyst_factor         # 1 + 2·min(byproduct_catalyst_cell, 1)
```

consume 1 unit of A and 1 of B (proportional energy `e_A`, `e_B`) and produce 1 unit of C with `e_C = (e_A + e_B)·(1 − reaction_thermodynamics)`; the remainder `(e_A+e_B)·reaction_thermodynamics` is released to cell heat.

**Conservation.**

- *Matter:* exact element conservation by construction (recombinational stoichiometry; integer counts).
- *Energy:* `e_A + e_B = e_C + Q` exactly per reaction; global ledger unchanged.
- No rule creates matter or energy; a reaction is only *where* chemistry happens.

**Why this is "dynamic chemistry".** The molecular composition of the world now evolves in space and time: product `C` appears where `A`, `B`, heat, season phase, and local catalyst align. Rare catalog molecules become locally abundant in specific places at specific times; precursors deplete; products decay/decompose back. The *chemistry* — not just the abundance — is now a state variable.

**Why it is heterogeneous (niche pressure).** `temperature_factor`, `season_factor`, and `catalyst_factor` are all *local and time-varying*, so reaction outcomes differ cell by cell. Different cells host different molecular regimes — the raw substrate for specialization.

### 2. Byproduct fields (organism products → environment)

Two per-cell scalar fields, stored exactly like biodeposits (sparse maps + O(1) scale decay):

- `catalyst` — locally accumulated reactive/metabolic byproducts that *accelerate* ER and local metabolism;
- `toxin` — locally accumulated harmful byproducts that *penalize* metabolism and add internal toxin load.

**Emission** (the only new organism→environment channel):

- **Excretion** (`digest_gut` expulsion): `catalyst += e·s·(0.25 + reactivity)`, `toxin += e·s·reactivity·permeability`, where `e` is expelled chemical energy, `s = byproduct_strength`, `reactivity/permeability` are the expelled molecule's descriptors.
- **Death** (`kill`): per death cell, proportional to structural mass share: `catalyst += m·s·0.5`, `toxin += m·s·0.25`, `m` normalized by reference body mass.

**Decay:** multiplicative scale `(1 − byproduct_decay_rate)` per tick — O(1) via the scale trick; no scan.

**Why scalars, not matter.** Catalyst/toxin are *conditions*, not ledger state (like biodeposit density). They carry no mass/energy, so the conservation ledger is untouched; their *effects* are multiplicative on existing transfers (see below), which cannot create energy.

### 3. Chemistry–metabolism coupling (niche formation)

Define a **local fit** for organism `o` at cell `c`:

```
fit(o, c) = chemistry_coupling · clamp(
    catalyst_c · reactivity_mean(o.diet)          # local catalysts help reactive diets
  − toxin_c    · sensitivity_mean(o.toxin_sens),  # local toxins hurt sensitive metabolisms
  −1, 1)
```

`reactivity_mean/sensitivity_mean` are the existing phenotype vectors (diet signature reactivity, toxin sensitivity) — no new genes, no new labels.

**Where fit acts:**

1. **Digestion capture** (`digest_gut`): `capture_target ×= (1 + fit(o,c))`, clamped to `[0, product.energy]`. The remainder flows to heat + waste exactly as before → energy conserved. Fit can be *negative* (poisoned niches) as well as positive (catalyzed niches).
2. **Toxin load** (`digest_gut`): local `toxin_c` scales the internal toxin accumulation of sensitive metabolisms — environment directly stresses organisms.
3. **Observation** (V2 + legacy): `O_LOCAL_FOOD` is blended with `fit` (`local_food = clamp(local_food + 0.5·fit, 0, 1)`). The existing neural/linear controllers already weight this slot; they now *perceive* local chemistry and can learn to seek/avoid regimes. No schema change (28-dim observation is unchanged).

**Why niches emerge without labels.** Selection (already present: energy → survival/reproduction) now acts on *chemistry match*: genomes whose diet reactivity / toxin sensitivity profiles fit a local regime get more energy *there* and are *less* stressed *there*. Over generations, populations sort into chemical regimes. "Producer"/"detoxifier"/"catalyst-feeder" roles, if they appear, are *descriptions of the outcome*, never inputs.

### 4. Guest niche coupling (endosymbiosis-like engulfment)

The engulfment/guest machinery already exists (`try_internalize`, `update_internal_guests`, `exchange`). To make **engulfment selectively advantageous in specific niches** (the endosymbiosis signature: incorporation pays off under particular conditions), modulate the guest economy by the host's local chemistry:

- **Guest demand** (per-tick energy the host must pay to keep a guest): `demand ×= (1 − guest_niche_coupling·max(0, fit))` — guests are *cheaper to maintain* where local chemistry suits the host.
- **Guest exchange** (energy the guest returns to the host): `exchange ×= (1 + guest_niche_coupling·max(0, fit))` — mutualism is *stronger* where chemistry is favorable.
- **Host catalysis** (`digest_gut`): `capture_target ×= (1 + guest_niche_coupling·guest_reactivity)`, `guest_reactivity` = mean reactivity of the guest's inventory (a guest *is* an internal chemical reactor).

Net: in rich/catalyzed niches, guests are a net energy *gain* (engulfment favored → hosts with guests dominate those niches); in poor/poisoned niches, guests are a net *cost* (engulfment disfavored). The advantage is computed from generic chemistry, not a "symbiosis" tag — this is the structural analogue of "mitochondria pay off in oxygenated niches".

---

## Config surface (Rust kernel)

| Field | Default | Range | Meaning |
|---|---:|---|---|
| `dynamic_chemistry_enabled` | `false` | bool | Master gate (zero overhead when off) |
| `reaction_rule_count` | `6` | 0..=32 | Number of recombinational rules (0 disables ER) |
| `environmental_reaction_rate` | `0.02` | 0..=1 | Base per-rule probability scale |
| `reaction_thermodynamics` | `0.10` | 0..=0.5 | Fraction of reaction energy released as heat |
| `byproduct_strength` | `0.02` | ≥0 | Emission scale (excretion + death) |
| `byproduct_decay_rate` | `0.02` | 0..=1 | Per-tick decay rate of byproduct fields |
| `chemistry_coupling` | `0.50` | 0..=1 | Local fit strength on metabolism + observation |
| `guest_niche_coupling` | `0.50` | 0..=1 | Local fit strength on guest economy |

CLI: `uv run organism-sim-headless --engine rust --dynamic-chemistry` (plus `--set` for any field).

## Performance budget

- **ER:** a sorted candidate list is built from deposit batches, then each candidate evaluates at most `min(rules, 6)` rules with a per-cell cap of 2; product insertion is staged until the cell finishes.
- **Byproducts:** O(1) decay (scale trick), O(events) emission; sparse maps, no per-chunk allocation.
- **Coupling:** diet reactivity is derived once when each phenotype is sampled; each digestion/guest update reads two local scalars.
- **Gate:** all reaction/byproduct paths are gated by `config.dynamic_chemistry_enabled`; the disabled baseline digest remains bit-identical (tested).

## Invariants (tested)

- Element conservation **exact** (recombinational stoichiometry) — `audit` element errors all zero with the feature on.
- Energy conservation within the existing relative tolerance — capture is clamped to `product.energy`; reaction `e_A+e_B = e_C+Q`.
- Determinism: same seed → same `digest()`; worker-count invariance preserved (ER runs in the sequential environment phase; guests/fit are per-organism).
- Disabled feature: `digest()` identical to a run with the feature off.

## Recorded study metrics

The runner records these observational quantities in `run_summary.csv`:

- `chemistry_regime = (catalyst - toxin) / (1 + catalyst + toxin)` at each living organism's cell;
- `chemistry_species_association`, an eta-squared-style between-species / total regime variance ratio;
- `chemistry_guest_regime_delta`, mean regime for hosts with guests minus hosts without guests;
- `guest_net_energy = cumulative guest exchange accepted by hosts − cumulative guest upkeep paid`;
- `environmental_reactions`, sparse byproduct totals/positions, generations, TPS, and conservation errors.

These are descriptive diagnostics, not evidence that a named ecological role was selected.

## Success criteria (experiments)

1. **Niche formation:** with DC on, species composition should be *more* associated with local chemical regime (catalyst/toxin/composition bins) than baseline — measured by a species–regime association index on final state.
2. **Dynamic chemistry:** molecular composition should *change over time* (reaction products appear; precursor/product ratios shift), and the change should be spatially heterogeneous.
3. **Engulfment advantage:** hosts with internal guests should be *over-represented* in high-fit niches and under-represented in low-fit niches vs. no-guest hosts — the endosymbiosis signature.
4. **No extinction regression:** DC should not make extinction *worse* than baseline (ideally better, via niche buffering).
5. **Conservation + performance:** element errors zero, energy within tolerance, ticks/sec within ~15% of baseline at 300/600/1200 founders.
