# Phase 2 Stringmol global positive-control preregistration

**Frozen before unseen-seed global runs:** 2026-08-26

## Preconditions met

Candidate R passed the preregistered host-dependence screen on ten unseen seeds:

- mixed R increased in 10/10;
- R-alone did not increase in 10/10;
- mixed-minus-alone maximum abundance was positive in 10/10;
- host-only populations persisted in 10/10;
- all 30 runs used pinned source/patch/config hashes and the explicit loader.

This establishes R as a host-dependent Stringmol parasite candidate. It does not yet validate the global positive control.

## Primary parasite-family label

Stringmol creates a cleaved offspring with the passive/template molecule's label:

```text
AgentMake(pass->label, ...)
```

The primary family is therefore the **transitive passive-parent ancestry** rooted at initial exact R species 2:

1. species 2 is in the family;
2. a child species joins the family if its logged passive parent is already in the family;
3. repeat to closure;
4. sum the exact species counts in that frozen closure at each logged tick.

This is neutral offline analysis. It does not alter binding, copying, mutation, decay, placement, or selection. Exact R abundance remains a secondary outcome.

An “either parent” ancestry is not primary because it labels active-host descendants that merely interacted with R, while upstream code explicitly inherits the passive label.

## Exploratory horizon choice disclosure

The earlier 5,000-step host-dependence runs were inspected after their confirmatory exact-R decision. Passive-parent ancestry reached 90% in 5/10 seeds by tick 4,900. This exploratory observation selected a **10,000-step** horizon for the new global control. Those inspected seeds cannot count toward the positive-control decision.

## Unseen global matrix

- seeds: **202608320–202608329**;
- condition: mixed 140 canonical hosts + 10 exact R parasites;
- 40×40 toroidal grid;
- fixed 15×10 inoculum with centered ten-cell R stripe;
- interaction radius: **0 (global)**;
- offspring-placement radius: **0 (global)**;
- horizon: 10,000 steps;
- mutation: 0.0002;
- decay: 0.0005;
- reporting every 100 steps;
- pinned ALXII matrix, source commit, binary, patch, and config hashes.

## Positive-control decision

The global positive control passes only if all hold:

1. passive-parent R ancestry reaches at least 90% of molecules in at least 8/10 seeds;
2. exact R exceeds its ten-molecule inoculum in at least 8/10 seeds;
3. total population remains nonzero through the final logged checkpoint in at least 8/10 seeds;
4. all ten processes exit successfully;
5. no run emits the reproducible-loader fallback warning;
6. source, patch, matrix, and generated-config provenance matches the lock.

Failures remain in the denominator.

## Local treatment gate

Do not launch or interpret the local treatment unless the global control passes.

If it passes, a separate committed addendum will reuse the same ten seeds, host/parasite sequences, positions, mutation, decay, horizon, and analysis, changing only:

- interaction radius: 0 → 1;
- offspring-placement radius: 0 → 1.

The focused containment outcomes will be maximum and final passive-ancestry fraction, exact R fraction, and whether 90% is reached. A mechanistic factorial separating interaction and placement locality may follow, but cannot replace the primary both-local versus both-global comparison.

## Scope

A pass would validate an external Stringmol positive control for locality experiments. It would not show that the conserved BFF soup contains a viable parasite.
