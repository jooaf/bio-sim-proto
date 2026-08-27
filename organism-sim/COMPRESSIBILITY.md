# Compressibility Benchmark Results

## Question

Do the event/cohort/AMR and process-specific upkeep designs in
`SUBLINEAR_SCALING.md` and `UPKEEP_SCHEMES.md` expose enough redundancy in the
current exact ecology to make work sublinear in census population?

## Short answer

**Not under the conservative lineage- or species-preserving policies measured
here.** Exact states never merge, lineage-safe representation remains equal to
the census, and species-safe representation usually remains above 84% of the
census. Only the explicitly exploratory guild-level cohort shows moderate
compression, representing 38–70% of the final population across the three
runs.

This means the architecture remains a plausible route to conditional
sublinearity, but the current ecology does not provide enough safe redundancy
to claim it yet. Whole-engine sublinearity is further blocked by the fact that
every living organism has an action deadline within eight ticks.

## Benchmark

The observation-only Rust metric is exposed as:

```python
simulation.compressibility_metrics()
```

The campaign runner is:

```nu
uv run python bench/compressibility.py \
    --founders 1200 \
    --ticks 10000 \
    --interval 500 \
    --burn-in 1000 \
    --seed 7
```

It samples the unchanged exact Rust engine. Metric calls do not consume RNG or
mutate the digest. Observation overhead was 0.15–0.24% in the campaign.

## Representation policies

`represented_work` is:

```text
individually protected organisms
+ min(class population, representative-particle limit) for each cohort class
```

It is an opportunity estimate, not a predicted wall-clock speedup.

### Lineage-safe

- 8-cell spatial tiles.
- Exact lineage key.
- Up to eight representative particles per class.
- Individually protects rare lineages (`<=32`), organisms age `<=64`, and
  physiology-critical organisms.

### Species-safe

- 16-cell spatial tiles.
- Exact species key.
- Up to eight representative particles per class.
- Individually protects rare species (`<=32`), organisms age `<=64`, and
  physiology-critical organisms.
- Merges common lineages within a species, so it still needs neutral-drift and
  establishment validation.

### Trait-only exploratory upper bound

- 32-cell spatial tiles.
- Guild key only.
- Up to four representative particles per class.
- Protects organisms age `<=64` and physiology-critical organisms.
- Does **not** protect rare lineages and is not scientifically acceptable
  without a separate rare-variant representation.

Representative particles carry phenotype, reserve, age, toxin, and inventory
distributions. These dimensions are not independent class keys, because doing
so produced almost entirely singleton state buckets during calibration.

Physiology-critical means reserve at most two maintenance ticks, integrity at
most 10%, debt at least 87.5% of its death threshold, or an active magic
status. Toxin-threshold and post-lifespan channels remain cohort-eligible only
under the bounded toxin/attrition methods proposed in `UPKEEP_SCHEMES.md`.

## Campaign results

| seed | ticks | final population | lineage-safe median | species-safe median | trait-only median | trait-only final | theoretical final upkeep ratio |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | 10,000 | 14,166 | 100.0% | 98.4% | 51.1% | 45.4% | 2.20x |
| 11 | 5,000 | 29,742 | 100.0% | 90.9% | 66.1% | 69.5% | 1.44x |
| 23 | 5,000 | 3,438 | 100.0% | 84.4% | 44.6% | 37.7% | 2.65x |

All runs passed exact element and energy conservation audits.

Raw results:

- `bench/results/compress-full-v2-f1200-t10000-s7/`
- `bench/results/compress-replicate-f1200-t5000-s11/`
- `bench/results/compress-replicate-f1200-t5000-s23/`

## What the benchmark shows

### 1. Lazy exact state batching does not compress

`exact_policy_keys / population` was 100% in every sample. Organisms differ in
position, physiology, reserves, age, action deadline, or inventory.

Lazy event scheduling may still skip uneventful intervals, but it cannot obtain
census-sublinear behavior by merging identical current states.

### 2. Protecting current lineages prevents compression

Lineage-safe represented work was exactly 100% of census in every run.

At the final samples, organisms in globally rare lineages ranged from 16% to
79%. Even common lineages were fragmented across spatial tiles into classes
small enough that up to eight representatives cost as much as their members.

A scalable engine therefore cannot preserve every current lineage as a
permanently separate protected identity. It needs another scientifically
validated representation, such as protected recent variants plus ancestry
weights/sketches and explicit neutral-drift statistics.

### 3. Species-level cohorts are still weak

Species-safe median represented work was 84–98% of census. Its best measured
final value was 83.4% for seed 23; seed 7 ended at 95.0% and seed 11 at 93.6%.

This is not enough to offset cohort bookkeeping, split/merge, error estimation,
and transaction costs reliably.

### 4. Broad distributional cohorts provide only moderate upkeep compression

The trait-only upper bound represented 37.7–69.5% of final census. That implies
a theoretical upkeep-only reduction of about 1.4–2.7x before implementation
overheads.

This is real redundancy, but it comes from merging lineages and species-level
variation aggressively. It cannot be treated as a scientifically safe result.

### 5. Critical physiological tails are large and seed-dependent

The final fraction requiring individual physiological fallback was:

| seed | final physiology-critical fraction |
|---:|---:|
| 7 | 21.8% |
| 11 | 54.0% |
| 23 | 14.2% |

Critical reserve alone was 18.4%, 53.7%, and 11.7%, respectively. A policy that
always keeps near-depletion organisms individual can lose most cohort savings
in stressed ecologies.

Toxin and aging also require their proposed cohort algorithms:

- Seed 7 ended with 43.9% near/above toxin tolerance.
- Post-lifespan fractions ranged from 6.3% to 26.9%.

Treating all of these organisms individually would make compression worse than
the table.

### 6. Independent actions remain an amortized linear lower bound

At every sampled final state, 100% of organisms had an action deadline within
eight ticks. Therefore an individual event queue only changes dispatch timing:
it still processes `Theta(N)` actions over an eight-tick interval.

Whole-simulator sublinearity requires aggregate movement, foraging, predation,
mating, reproduction, and occupancy—not only aggregate upkeep.

### 7. Spatial state is not automatically smaller than population

For seed 7 at tick 10,000:

```text
population                 14,166
32-cell organism tiles        492
active heat cells          517,370
active deposit positions   110,365
active deposit batches     194,131
occupied cells              64,740
```

Tiles are compressible, but exact cell heat, deposits, and occupancy are larger
than census. Conservative AMR, pooled remote deposits, and aggregate occupancy
are mandatory; active sets alone are insufficient.

## Decision

The benchmark does **not** support the statement that the current research
design, implemented conservatively, is already enough to deliver useful
census-sublinear execution.

It supports a narrower statement:

> Broad local distributional cohorts can reduce upkeep representation in this
> ecology, but preserving every rare lineage and every near-threshold organism
> removes nearly all of that compression. Independent actions and exact spatial
> state remain linear or larger.

## Recommended next experiments

1. Design a rare-variant/ancestry representation that does not permanently
   protect every small lineage; validate neutral drift and mutant establishment.
2. Replace individual critical-reserve fallback with bounded reserve-class
   event counts where threshold timing can remain safe.
3. Prototype aggregate action channels; the eight-tick action lower bound is
   more important than scheduler choice.
4. Measure adaptive clustering error directly rather than relying on hard
   species/lineage keys.
5. Prototype conservative tile heat and pooled-deposit state, then measure
   represented spatial complexity.
6. Re-run this campaign with actual split/merge churn and one-step-versus-two-
   half-step errors; the current result is an optimistic representation bound.
