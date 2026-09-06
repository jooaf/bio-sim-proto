# Stage 3R neutral lineage-patch preregistration

**Frozen before execution:** 2026-09-06

## Preconditions

The non-spatial liveness pilot selected reproduction rate `2×10⁻⁵` by a frozen rule: 3/3 runs were feasible, median successful births were 71, median late occupancy was 0.835, pool blocks were zero, and median maximum lineage depth was 2. No lineage-family spatial statistic was inspected during selection.

## Scope

This experiment tests whether local offspring placement creates neutral inherited spatial patches. Scheduled copy birth is not endogenous self-replication. Neutral families are not organisms or organizationally closed units.

## Matrix

- offspring placement radius: **1 versus 8**;
- interaction radius fixed at 1;
- unseen matched seeds: **202609100–202609109**;
- ten seeds per treatment, 20 runs;
- horizon: 10,000 ticks;
- reproduction rate: 2×10⁻⁵ per live tape/tick;
- maximum births/tick: 4;
- baseline mutation, dissolution, reseed, interaction count, pool, and lattice;
- energy, tasks, and signals disabled.

Only offspring placement radius varies.

## Neutral family definition

Build the transitive one-parent lineage from recorded reproductive births. Each root tape receives family label:

```text
family = root_tape_id mod 16
```

Each reproductive child inherits its parent's root. Randomly seeded tapes are new roots. Initial tape IDs are assigned independently of lattice coordinates, so modulo family is initially spatially mixed. Family labels never affect chemistry, birth, death, interaction, or placement.

## Primary statistic

At the final tape snapshot:

1. map each live tape ID to its neutral family;
2. enumerate occupied undirected radius-1 Moore-neighbor edges;
3. calculate equal-family neighbor frequency;
4. permute family labels over fixed occupied cells 999 times;
5. report observed frequency, null mean, excess, and one-sided p-value.

Use analysis seed `20260909 + run seed`.

Primary paired effect:

```text
placement-radius-1 family-neighbor excess − placement-radius-8 excess
```

Report all ten effects, mean, median, 95% paired bootstrap interval with 10,000 resamples and seed 20260909, and exact one-sided sign-flip p-value.

The lineage-patch mechanism passes only if:

- mean effect > 0;
- bootstrap interval excludes zero positively;
- exact p ≤ 0.05;
- at least 8/10 paired effects are positive;
- at least 8/10 runs per treatment are mechanically feasible;
- median reproductive births ≥ 75 in both treatments;
- median maximum lineage depth ≥ 2 in both treatments.

## Secondary outcomes

Descriptive only:

- exact-root neighbor excess;
- live reproductive-descendant fraction;
- family abundances and Hill diversity;
- maximum lineage depth;
- births and pool/no-space blocks;
- positional byte and opcode-composition JS excess;
- occupancy and turnover.

## Mechanical feasibility

A run must succeed, conserve every symbol exactly, record no invariant failure, maintain final-window occupancy from 0.40 through 0.95, and have nonzero interactions, writes, dissolution, random placement, reproductive birth, and pool turnover. Pool-blocked births may not exceed successful births.

## Integrity rules

- Preserve all failures and extinctions.
- Do not alter family modulus, root handling, snapshot, neighbor radius, null, or thresholds.
- Do not choose a different birth rate or add seeds after inspection.
- A pass validates neutral lineage clustering caused by local placement. It does not establish organisms, endogenous replication, selection, or the energy-ledger Stage 3 gate.
