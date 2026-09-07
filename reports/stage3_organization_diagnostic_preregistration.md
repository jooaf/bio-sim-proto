# Stage 3 empirical organization identifiability preregistration

**Frozen before execution:** 2026-09-07

## Scope

This is an identifiability diagnostic followed, only if identifiable, by a bounded empirical-organization test. It cannot establish organism identity. The user explicitly waived an optional external engineering workflow review; synthetic algorithm tests remain mandatory before execution.

## Species and reactions

A species is the exact eleven-component BFF composition count vector: counts of the ten opcodes in canonical interpreter order plus aggregate non-opcode count. Counts sum to 64. No continuous clustering or tunable distance is used.

A sampled interaction records:

```text
{A_before, B_before} -> {A_after, B_after}
```

Before state is before background mutation and execution; after state is after both. Reactions are sampled by a deterministic hash of seed, tick, and round, consuming no simulation RNG.

## Campaign

- selected Stage 3 energy operating point, influx 1024;
- reproduction disabled;
- seeds `202609170`–`202609172`;
- 5,000 ticks;
- deterministic reaction sample rate 1%;
- five frozen windows: ticks 0–999, 1000–1999, 2000–2999, 3000–3999, and 4000–4999;
- three runs, 15 windows;
- all other settings identical to the selected energy-liveness profile.

## Identifiability gate

For each window report sampled and changed reactions, species count, unique-species fraction, singleton-species fraction, and fraction of species observations belonging to recurrent species.

A window is identifiable only if:

- sampled reactions ≥ 100;
- changed reactions ≥ 10;
- recurrent-observation fraction ≥ 0.50;
- singleton-species fraction ≤ 0.80.

The representation passes only if at least 12/15 windows are identifiable and every seed has at least 4/5 identifiable windows. If it fails, stop before organization inference and retain the negative result.

## Candidate algorithm

Using changed reactions only:

1. construct the undirected participant graph joining both reactants and products of each reaction;
2. take deterministic weak connected components as candidate sets;
3. evaluate empirical closure: every product of an internal observed changed reaction remains in the candidate;
4. calculate count-weighted net production by subtracting reactants and adding products;
5. call a candidate self-maintaining only when it has at least one changed internal reaction, is closed, every member participates, and every member's net production is nonnegative.

Because every reaction has two reactant and two product slots, total net production is zero; the nonnegative condition therefore requires exact observed balance across candidate species.

## Null and organization endpoint

For each identifiable window, permute product species over fixed product slots 199 times, retaining reactants, product abundance, reaction count, and window size. Use RNG seed `20260917 + run seed + window index`.

Primary endpoint is mean number of closed self-maintaining active candidates across identifiable windows. Align permutation indices across windows to form a null distribution of campaign means. Report Monte Carlo one-sided p-value `(1 + null means >= observed mean) / 200`.

Organization excess is supported only if:

- the identifiability gate passes;
- at least 8/15 windows contain an accepted candidate;
- observed campaign mean exceeds the 95th percentile of null campaign means;
- one-sided Monte Carlo p ≤ 0.05;
- 3/3 runs succeed, conserve every symbol, have maximum relative energy error ≤ `1e-9`, and record zero invariant failures.

## Integrity

Do not alter species representation, sample rate, windows, component rule, maintenance inequality, permutations, seeds, or thresholds after execution. A negative result does not license clustering composition vectors or reverting to sparse exact hashes. Any positive result remains representation- and window-dependent and would require an intervention test before a self-maintenance claim.
