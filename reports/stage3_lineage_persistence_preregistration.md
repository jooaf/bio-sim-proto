# Stage 3 neutral lineage-patch persistence preregistration

**Frozen before execution:** 2026-09-07

## Preconditions and scope

Vacancy-first local placement caused neutral lineage clustering with exactly matched birth counts and vacancy opportunities. This experiment tests how much of that clustering remains after scheduled birth is removed. It does not test adaptation or organism persistence.

## Matrix

- arm 1: vacancy-first radius-1 scheduled birth continues through 20,000 ticks (`stop_tick = 0`);
- arm 2: identical birth stops before tick 10,000 (`stop_tick = 10000`);
- unseen matched seeds `202609160`–`202609169`;
- ten seeds per arm, 20 runs;
- energy, signals, and tasks disabled;
- selected birth rate `2e-5`; all other vacancy-controlled settings unchanged.

Only `reproduction.stop_tick` varies. A stopped mechanism consumes no reproduction RNG.

## Family and checkpoints

Use the unchanged transitive-root modulo-16 neutral families. At tape snapshots `10000`, `12000`, `15000`, and `19900`, compute radius-1 equal-family neighbor excess against 499 fixed-occupancy label permutations using analysis RNG `20260916 + run seed + checkpoint`.

Also compute exact-root neighbor excess descriptively with 199 permutations.

## Primary persistence endpoint

For each stopped run, use final checkpoint family-neighbor excess at tick 19900. Report its mean, median, 10,000-resample bootstrap interval using seed `20260916`, and exact one-sided sign-flip p-value against zero.

The switch-off patch is persistent only if:

- mean stopped-arm final excess > 0;
- bootstrap interval excludes zero positively;
- exact one-sided p ≤ 0.05;
- at least 8/10 stopped-arm final excesses are positive;
- at least 8/10 stopped-arm final within-run permutation tests have p ≤ 0.05;
- median stopped-arm retention ratio `final excess / switch-checkpoint excess` is at least 0.25;
- continued-birth positive control has positive final excess in at least 8/10 runs;
- 20/20 runs exit successfully and conserve symbols exactly;
- zero invariant failures;
- at least 8/10 runs per arm meet occupancy, interaction, writes, dissolution, random-placement, and pool-turnover feasibility.

If a switch-checkpoint excess is nonpositive, its retention ratio is undefined and the run fails the retention criterion while remaining in all other denominators.

## Secondary outcomes

Descriptive only:

- checkpoint decay curves in both arms;
- continued-minus-stopped final excess;
- exact-root excess;
- live descendant fraction and lineage depth;
- occupancy and turnover after switch-off.

## Integrity and interpretation

No checkpoint, family definition, seed, null, threshold, or endpoint may change after execution begins. A pass means a neutral lineage spatial pattern outlasts the birth process for 9,900 ticks under ongoing mutation, interactions, dissolution, and random placement. It does not imply self-maintenance by an organism.
