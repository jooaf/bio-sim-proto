# SM-H003 replicated canonical-supported sequence-order assay

**Frozen before implementation:** 2026-10-02

## Question and boundary

For the complete noncanonical SM-H002 descendant panel, does exact sequence order
reproducibly support candidate-cohort renewal better than its frozen
composition-preserving shuffle when 70 canonical partners are supplied?

This is a new prospective assay, not a reinterpretation or confirmation of
unevaluable SM-H002. It addresses the cohort-partition defect diagnosed in
`reports/sm_h002_canonical_support_diagnosis.md` by using whole-population
canonical renewal only as the assay-positive control. A pass supports a causal
sequence-order effect under supplied canonical partner context. It does not prove
partner necessity, identify catalyst/template mechanism, show self-context
competence, establish adaptation, or support ecology/organism claims.

## Frozen panel and perturbation

Regenerate and verify the complete 15-genotype SM-H002 panel and shuffles from:

- H001 analysis SHA-256
  `1c64913c61624ddc82800dc33620e5c3da11ae67240a6abacaf4d8e15b4bbd04`;
- committed fixture `tests/fixtures/sm_h002_source_candidates.json`;
- SM-H002 panel selection and unambiguous SHA-256 shuffle algorithm; and
- SM-H002 preparation/analysis only as source-integrity evidence.

The sequence with SHA-256
`94f8c51cef8ef18d4246fb1fc6030b20f887bb0e265be59b3949be2bb69b89c5`
is the canonical control and is excluded prospectively from the 14-genotype
scientific denominator. No genotype is selected by its SM-H002 outcome. Exact and
shuffle bytes remain unchanged.

## Pinned mechanics

Use upstream `15dad84da126a4f887ba945c23a13e89e827f067`, unchanged patches
0001–0004, exact molecule + accessible-pool + waste conservation, free-pool
multiplier 0, recycle decay, 40×40 global interaction/placement, mutation 0.0002,
decay 0.0005, 5,000 steps, report interval 100, and lineage/material observation.
No simulator or chemistry change is allowed.

Every run has 70 focal molecules at frozen positions/IDs 0–69 and 70 canonical
partners at positions/IDs 70–139. Focal ancestry defines the candidate cohort;
canonical-partner ancestry defines support. Cohorts are observational and never
alter labels, execution, placement, RNG, or chemistry.

## Matrix and unseen seeds

For each sorted panel rank `i = 0..14` and replicate `j = 0..2`, use seed
`202625000 + 3*i + j` for one paired block:

1. **EXACT_SUPPORT:** 70 exact focal + 70 canonical support;
2. **SHUFFLE_SUPPORT:** 70 frozen shuffle focal + 70 canonical support.

There are 45 paired blocks and 90 runs. Use at most six workers with
`NUMBA_NUM_THREADS=1`. All runs remain in the denominator. No resume,
replacement, selective retry, horizon extension, or outcome-driven reshuffle.

## Endpoints

Replay source/cohort lineage exactly as SM-H002. Candidate **exact liveness** in a
run requires all:

- productive source births ≥100;
- serial source births ≥25;
- source depth ≥2;
- late productive source births ≥50; and
- late renewing descendants ≥5.

A paired replicate has **sequence specificity** when exact has candidate liveness
and, relative to shuffle:

- productive-source-birth margin ≥100 and ratio ≥2;
- late-productive-birth margin ≥50; and
- serial-source-birth margin ≥25.

Zero-denominator ratio handling is unchanged from SM-H002.

A noncanonical genotype has **replicated specificity** when:

- the same at least 2/3 replicate pairs satisfy sequence specificity; and
- exact candidate productive source births exceed shuffle in all 3 pairs.

Report every component, replicate, paired difference, pooled total, retention,
partner role, survival, whole transfer, and orphan event. Replicate is not treated
as an independent genotype for the panel denominator.

## Canonical whole-population positive control

The three canonical EXACT_SUPPORT runs are molecularly 140 canonical hosts.
Evaluate their **combined native population**, not either arbitrary founder
cohort. A canonical replicate passes when it has:

- ≥100 productive source births;
- ≥10 renewing descendants;
- ≥50 serial source births;
- source depth ≥2; and
- ≥5 late renewing descendants.

At least 2/3 canonical exact replicates must pass. Canonical candidate/support
subcohort allocations and exact-versus-shuffle effects are diagnostics only.
Failure makes SM-H003 unevaluable. This rule was frozen after diagnosing H002's
identical-population partition artifact and before any SM-H003 seed was run.

## Integrity and launch gates

Before launch:

1. reproduce source, panel, and shuffle hashes exactly;
2. fresh-build unchanged patches and pass inherited upstream, isolation, lineage,
   conservation, recycling, renewal, and SM-H002 cohort fixtures;
3. parse all 90 configs and prove load order, ID/cohort ranges, positions,
   commands, seeds, exact bytes, and exact/shuffle per-symbol material equality;
4. add fixtures for three-replicate aggregation, same-2/3 conjunction,
   all-three direction, canonical exclusion, whole-population positive control,
   threshold edges, and all decisions;
5. verify logging/workflow isolation and canonical exact config parity;
6. commit/push implementation, directly observe committed bytes on
   `origin/main`, and repeat held-out seed audit; and
7. prohibit any existing output directory or campaign/launch receipt.

All 90 runs must pass process, complete event replay, exact per-symbol
conservation, nonnegative ledgers, source/cohort DAG, suffix transfer, snapshot,
identity, counter, schema, alphabet, bounds, and artifact checks. Integrity
failure is unevaluable.

## Frozen decisions

Let `replicated_panel` be the number of the 14 noncanonical genotypes with
replicated specificity.

1. **Pass:** integrity and canonical positive control pass and
   `replicated_panel >= 12`. Exact order causally supports reproducible
   candidate renewal for this competence-enriched panel under supplied canonical
   partners. A separately preregistered catalyst/template-role assay is eligible.
2. **Valid non-pass:** integrity and canonical control pass but
   `replicated_panel < 12`. Retain genotype-level effects; no panel functional-
   heredity or catalyst/template confirmation is eligible.
3. **Unevaluable:** integrity or canonical positive control fails. Repair only
   artifact/implementation defects and rerun the unchanged full matrix; otherwise
   stop and retain diagnostics.

The fair-coin upper tail for at least 12 of 14 is `106/16384 = 0.0064697265625`,
descriptive rather than a p-value for the composite gate. SM-H002 remains
unevaluable regardless of this result.
