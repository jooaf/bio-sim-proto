# Phase 2 parasite positive-control preregistration

**Frozen before Stage 2 parasite viability runs:** 2026-08-26

## Purpose

Before comparing local and well-mixed treatments, demonstrate that one fixed BFF copier family can spread in the large-radius Stage 2 world. Failure is an invalid positive control, not evidence that locality contains parasites.

This is positive-control development. It cannot establish containment by itself.

## Amendment to “hand-written parasite” wording

The original Phase 2 preregistration called for a labeled hand-written parasite. No compact hand-written BFF tape has yet been mechanically validated under the repository's exact 64-byte joint-tape semantics. Inserting an unvalidated design would make a failed control uninterpretable.

This protocol instead uses a **frozen naturally emerged BFF copier** from a pre-Phase-2 checkpoint. The candidate is externally inserted and labeled, so it remains the one allowed seeded-parasite exception. Its source and selection rule are fully disclosed. It is more substrate-faithful but is not described as hand-written.

No Stage 2 outcome was inspected when selecting the candidate.

## Candidate provenance and deterministic selection

Source checkpoint:

- path: `runs/paper_probe_seed0_transition.npy`;
- shape: 131,072 tapes × 64 bytes;
- checkpoint SHA-256: `7530db43af8177bc141eda022ddc037edf61d48d1d6dbd73284f64c816d3c573`;
- checkpoint predates Phase 2.

Selection rule:

1. count exact tapes in the checkpoint;
2. retain candidates scoring 64/64 under the repository's frozen `functional_selfrep_score` assay;
3. maximize checkpoint abundance;
4. break ties by lexicographically smallest 64-byte sequence.

Frozen candidate:

- checkpoint abundance: 116;
- functional self-replication score: 64/64;
- BLAKE2b-128 content hash: `81603f482497218f10250a43385710f6`;
- candidate SHA-256: `c5688eb24e41bc415ac02194eacc3b5ba93297c458aee6cdf3527283bb317f62`;
- hex bytes:

```text
cda1b9cdfcffd3e15333691611dfbb4d3160426bb9bc465b3ca72466e02c8fea3250c9187df81cd35e5df4f87dd59adb8913295267a4f52c3c5b53194db269dd
```

## Frozen parasite-family definitions

Report all three, without choosing among them after observing outcomes:

1. **Exact seed:** tape equals all 64 candidate bytes.
2. **Near-seed family:** Hamming distance from the candidate is at most 8 bytes.
3. **Candidate opcode family:** ordered BFF-opcode signature equals the candidate's ordered opcode signature.

The exact-seed outcome is the strict primary viability measure. Near-seed and opcode-family outcomes describe mutated descendants but may include convergent tapes. They are secondary.

## Neutral initialization

For every seed:

1. create the ordinary 80%-occupied random SpatialWorld using the simulation RNG;
2. sort occupied flat cell indices;
3. replace the first 16 occupied tapes with the frozen candidate before pool creation and before initial lineage logging;
4. record all overridden tape IDs/cells and candidate hashes in the run manifest/protocol;
5. create the conserved symbol pool from the final initialized tapes.

The same host soup, candidate count, and candidate cells are therefore used for every radius treatment sharing a seed. Initialization consumes no free matter because the conserved totals are defined only after the complete initial condition is assembled.

The 16 inserted tapes are 1.56% of lattice capacity and approximately 1.95% of initial occupied tapes.

## Positive-control development ladder

### Step 1 — deterministic mechanics

- 8×8 lattice;
- radius covering the torus;
- 100 ticks;
- mutation disabled for a strict exact-copy check;
- full invariants and full-byte snapshots;
- one seed.

Pass if exact-seed abundance increases above 16 without invariant failure.

### Step 2 — bounded viability pilot

If Step 1 passes:

- 16×16 lattice;
- large radius 8;
- 2,000 ticks;
- mutation 1/4,096;
- seeds 202608270–202608274;
- otherwise selected Stage 2 liveness parameters.

Pass if exact- or near-seed family abundance increases above its inserted count in at least 4/5 seeds and at least one seed reaches 50% of occupied tapes. This permits a larger confirmatory control but does not validate containment.

### Step 3 — preregistered large-radius validation

Only after the bounded pilot passes:

- 32×32 lattice;
- large radius 16;
- 5,000 ticks initially, extended by a separately frozen horizon only if all runs are still increasing at the boundary;
- ten new matched seeds;
- fixed candidate count 16 and all scientific parameters unchanged.

The positive control required by the original containment criterion is valid only if the candidate family reaches at least 90% of occupied tapes in at least 8/10 seeds. If it does not, the radius-1 comparison cannot support containment.

## Fixed Stage 2 parameters

Except where Step 1 explicitly disables mutation:

- tape length: 64;
- interaction budget: 8,192;
- initial fill: 0.8;
- pool multiplier: 16;
- spontaneous dissolution: 10⁻⁵;
- reseed: 10⁻⁵;
- structural inertness threshold: 10,000 ticks;
- maximum-age and starvation dissolution disabled;
- energy, signals, and tasks disabled;
- attempted interactions per tick: half lattice capacity;
- aggregate interaction logging;
- full-byte snapshots at a cadence appropriate to each bounded horizon.

## Integrity and interpretation rules

- Exact symbol conservation is required at every aligned snapshot.
- Invariant failure halts and fails a run.
- Seeded initialization must be represented in the manifest and raw protocol.
- No fitness bonus, special copy opcode, replication reward, or protected tape is added.
- Once initialized, candidate tapes undergo ordinary mutation, interaction, scarcity, and dissolution.
- Failed and negative runs remain in the report.
- A successful positive control shows only that this candidate can invade this world. It does not prove that it is a biological parasite or that radius 1 contains it.
