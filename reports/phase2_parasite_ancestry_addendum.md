# Phase 2 parasite neutral-ancestry addendum

**Frozen before ancestry-instrumented reruns:** 2026-08-26

## Trigger

The first bounded viability pilot failed its preregistered rule:

- 3/5 seeds increased above the 16 inserted near-seed tapes;
- 1/5 reached 50% near-seed occupancy;
- exact, near-seed, and frozen opcode-signature counts were zero at the final snapshot in all five seeds;
- one seed temporarily reached 51.9% near-seed and 99.0% opcode-family occupancy;
- all runs were conserved and invariant-clean.

The positive control is therefore **not validated**, and no containment comparison is permitted from those runs.

## Why add neutral ancestry

A fixed Hamming ball or opcode signature can lose descendants after extensive mutation even if those descendants arose through copying by the seeded family. Reclassifying the completed runs post hoc would be invalid, and their aggregate logs cannot reconstruct ancestry.

New runs will therefore retain every interaction and reconstruct a neutral ancestry label offline. The label has no effect on pairing, execution, mutation, dissolution, placement, or resource availability.

## Frozen offline label propagation

At initialization, the 16 explicitly overridden tape IDs are labeled parasite ancestry. Other tape IDs are unlabeled.

Process complete interaction facts in tick/round order:

- infer A→B only when A is unchanged, B changes, and B's final exact hash equals A's pre-interaction hash;
- infer B→A analogously;
- on an inferred exact overwrite, the target receives the source's ancestry state;
- ordinary partial changes and mutations preserve a tape ID's current ancestry state;
- ambiguous events where both sides change to the same hash are not treated as ancestry transfer;
- dissolution removes the dead tape ID's label;
- exogenous random placement begins unlabeled.

At each tape snapshot, ancestry abundance is the number of occupied tape IDs currently carrying the label.

This is a conservative ancestry witness: it can miss non-exact functional offspring, but it cannot spread merely because a tape happens to resemble the seed.

## New bounded diagnostic

Use the same candidate, 16×16 lattice, radius 8, 2,000 ticks, 16 inserted copies, mutation 1/4,096, and all selected liveness parameters. The only scientific-state change is none; the logging change retains 100% of interactions.

Use five new seeds: 202608280–202608284.

The ancestry diagnostic passes if:

1. ancestry abundance rises above 16 in at least 4/5 seeds;
2. ancestry reaches 50% of occupied tapes in at least one seed;
3. all runs conserve symbols exactly and have zero invariant failures.

Content-based exact, near, and opcode families remain reported and are not rewritten.

Passing this diagnostic permits preregistration of a ten-seed 32×32 large-radius validation. It does not itself validate the positive control. The original requirement—at least 90% family occupancy in at least 8/10 large-radius runs—remains unchanged and will use neutral ancestry as the primary family label, with content families secondary.

## Integrity

- New seeds prevent reuse of inspected trajectories.
- Full interaction logging is observation only.
- No simulator-side replication detector or fitness mechanism is introduced.
- Failed and negative runs remain reported.
- If this diagnostic fails, the candidate is rejected for Phase 2 containment.
