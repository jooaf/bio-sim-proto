# Phase 1 closeout and Phase 2 handoff

## Decision

**Phase 1 is closed as an engineering and mechanism phase. Phase 2 design and scaffold work may proceed.**

The scientific claim remains narrower than “metabolism emerged.” Phase 1 demonstrated exact conserved matter, selective scarcity, explicit circulation, temporary windowed flow roles, and a suggestive origin-versus-maintenance asymmetry. It did not demonstrate a persistent, sparse, organism-like metabolic organization.

## Closeout checks completed

### Reproducibility freeze

- Freeze ID: `phase0-phase1-closeout-v1`
- Compact freeze manifest: `reports/phase0_phase1_freeze_manifest.json`
- Raw artifact checksum index: `reports/phase0_phase1_artifact_index.csv`
- Indexed raw files: **3,199**
- Indexed raw data: approximately **10.7 GB**
- Multi-gigabyte run directories remain outside Git and are verified by SHA-256.
- Stale Phase 0/1 PID files and generated tool-output files were removed.
- Raw-run, log, notebook-checkpoint, and PID ignore rules were added.

Historical run manifests often name the original base commit because Phase 1 was developed in an uncommitted worktree. The freeze commit captures the final source/config/report state, while the artifact index preserves exact output bytes. This is adequate for a closeout snapshot but weaker than commit-per-campaign provenance; future Phase 2 campaigns must start from a clean versioned commit.

### Statistical correction

The Spearman p-value helper had a reversed incomplete-beta symmetry expression and used an invalid zero asymptotic p-value for very small perfect correlations.

It now:

- uses the corrected beta expression for larger samples;
- uses exact label permutation for `n <= 9`;
- has regression tests for beta identities, small-sample perfect correlation, moderate Phase 1 correlation, and p-value formatting;
- avoids displaying a nonzero p-value as `0.0000`.

Corrected results:

| Test | Corrected result | Interpretation |
|---|---:|---|
| Multiplier vs maximum entropy | rho -0.302, asymptotic p 0.273 | Unsupported |
| Multiplier vs blocked rate | rho -0.945, p 1.13×10⁻⁷ | Strongly supported |
| Multiplier vs flow-persistence gap | rho -0.158, exact p 0.729 | Unsupported |
| Lag vs mean role persistence, four points | rho -1, exact p 0.0833 | Descriptive monotonic pattern, not conventionally significant |

Machine-generated and narrative reports were corrected.

## Final Phase 1 findings

1. Every retained conserved campaign had zero per-symbol conservation residual.
2. Scarcity is caused by composition-specific shortages, not disappearance of total free matter.
3. Tight scarcity is broad and chronic; loose scarcity is rare and bursty.
4. Extreme BFF blocking usually comes from one long interaction repeatedly requesting one symbol.
5. Token audits prove return-to-pool, reacquisition, cross-tape transfer, and cycles.
6. Whole-run flow is highly mixed, but adjacent 2,000-epoch windows retain role structure above a permutation null.
7. A natural replicator quasispecies has orders-of-magnitude less blocking than a random soup under similar conserved conditions.
8. Structural-symbol exclusion at origin produced 0/5 transitions versus 3/5 controls; arbitrary non-structural exclusion produced 3/5. This supports, but does not prove, a class-specific origin filter because p=0.083 and blocked-load matching was imperfect.
9. Intermediate scarcity did not reliably maximize organization.
10. SKI passed the shared conservation pipeline and showed that scarcity ordering can depend on substrate semantics.

Detailed contribution and novelty assessment:

- `reports/phase0_phase1_findings_novelty_and_phase2_readiness.md`
- `reports/phase0_phase1_simple_summary.md`

## Phase 2 semantics fixed

`reports/phase2_preregistration.md` now defines:

- sparse occupancy on a toroidal 2D lattice;
- local Moore-neighborhood interactions;
- exogenous random placement funded atomically by the symbol pool;
- neutral structural dissolution returning all tape bytes;
- stable tape IDs and append-only lifecycle facts;
- starvation dissolution disabled until the Phase 3 energy ledger exists;
- anti-clogging plus anti-extinction/liveness criteria;
- categorical neighbor-identity autocorrelation against a label-permutation null;
- multiplicative block beta diversity against a permutation null;
- parasite positive-control requirements;
- a matched-seed radius sweep;
- benchmark and integrity stopping rules.

The key anti-extinction clarification is that an empty lattice cannot pass merely because it has free cells.

## Phase 2 scaffold implemented

The repository now contains a tested initial scaffold for:

- `SpatialWorld` occupancy, coordinates, toroidal neighbors, IDs, ages, and inert timers;
- `local_neighborhood` pairing;
- pool-funded whole-tape placement and atomic rejection;
- dissolution and byte reclamation;
- Stage 2 occupancy and conservation invariants;
- Stage 2 tick, interaction, tape, event, and lineage logging;
- Stage 2 mechanical reports;
- spatial neighbor-identity and beta-diversity analyses;
- deterministic Stage 2 short runs;
- smoke and benchmark configurations.

This is a scaffold, not a passed Phase 2 scientific gate. No parasite campaign, radius sweep, or 500,000-tick acceptance treatment has been completed.

## 500,000-tick benchmark

Measured aggregate-logging ladder:

| Lattice | Measured ticks | Wall time | Projected 500k wall | Projected output |
|---:|---:|---:|---:|---:|
| 8×8 | 100 | 1.37 s | 1.90 h | 0.82 GB |
| 32×32 | 1,000 | 126.82 s | 17.61 h | 0.65 GB |
| 64×64 | 1,000 | 461.64 s | 64.12 h | 1.90 GB |

All measured cases had zero invariant failures.

Files:

- `reports/stage2_benchmark.json`
- `reports/stage2_benchmark.md`
- `experiments/benchmark_stage2.py`

### Benchmark decision

A 500,000-tick 32×32 run is feasible as an overnight batch. A 64×64 run projects to about 2.7 days before spatial-analysis cost and possible replicator-rich slowdowns. The projection is not a completed gate.

Before the full acceptance treatment, choose one of:

1. schedule the preregistered 32×32 full run;
2. optimize/compile the local interaction kernel before using 64×64;
3. explicitly approve a multi-day 64×64 batch.

Do not silently shorten the 500,000-tick criterion.

## organism-sim transfer

A practical transfer report is available at:

- `organism-sim/PHASE1_FINDINGS_TRANSFER.md`

Its main recommendation is a same-checkpoint origin-versus-established resource-composition experiment with target-resource exclusion, irrelevant-resource exclusion, and a matched-friction control.

It also identifies important corrections to the current integration:

- founder scaling is persistence/diversification, not spontaneous origin;
- the one-seed BFF mutation result cannot establish organism-sim's optimal mutation rate;
- scarcity profiles currently change both initial stock and renewal flux;
- demand-matched geology is not a globally closed conserved pool;
- a true established-ecology intervention requires deterministic checkpoint/resume;
- late-window reporting should be corrected before confirmatory use.

## Remaining work before the Phase 2 scientific gate

1. Complete the final quality review and version marker.
2. Decide whether to optimize or schedule the full 500,000-tick run.
3. Preregister the pilot-selected reseed/dissolution operating point in an addendum.
4. Validate a designed parasite in the large-radius positive control.
5. Run the matched radius and parasite campaigns.
6. Report negative outcomes without post-hoc tuning.

## Bottom line

Phase 1 is complete enough to stop adding conservation-only experiment batches. Its strongest new direction is that resource composition may filter origin while an established ecology buffers the same shortage.

Phase 2 can now begin from explicit semantics, tested spatial mechanics, fixed null analyses, and a measured performance budget rather than an ambiguous long-run target.
