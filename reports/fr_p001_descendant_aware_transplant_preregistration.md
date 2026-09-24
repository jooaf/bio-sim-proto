# FR-P001 held-out descendant-aware transplantation preregistration

**Frozen before implementation:** 2026-09-18

## Purpose and claim boundary

AC-P006 showed strong sequence-specific exact-copy amplification followed by
complete exact-tape extinction. FR-I001 then validated an operational descendant
candidate (paper score 64 and value-change provenance fraction at least 0.75), and
FR-I002 showed that those labels can be observed without changing exact conserved
mechanics. FR-P001 asks whether fresh functional inocula show sustained sampled
presence through non-exact operational descendant candidates after exact tape
identity is absent. Non-exact changes can arise from execution writes as well as
mutation and do not by themselves prove mutation-derived descent.

This is the first prospective use of the representation in a conserved soup. It
does not reclassify AC-P006 and cannot establish biological ancestry, heredity,
organisms, adaptation, ecology, or organization.

## Frozen sources

Use nine score-64 first-origin checkpoints that were not used for FR-I001
calibration or confirmation:

- AC-P001 multiplier-16 seeds `202612001, 202612003, 202612008, 202612009`;
- AC-P002 multiplier-16 seeds `202613001, 202613008, 202613010, 202613013,
  202613018`.

Order them exactly as listed and assign global pair indices 0–8. Verify source
manifest/checkpoint checksums, first-origin epoch/rank, and the original batch
score-64 result at the frozen candidate rank. Separately evaluate each witness as
a single tape with assessment seed 0; all nine must score 64 or the whole campaign
is unevaluable with no source replacement. These witnesses are held out from
FR-I001 representation calibration and confirmation, although they were selected
in earlier preregistered origin campaigns.

For pair `i`, construct one deterministic Fisher-Yates composition-preserving
shuffle using byte swap at descending position `j` with
`splitmix64(0xAC009000 XOR splitmix64(i * 64 + j)) mod (j + 1)`. Require exact
composition equality, at least one changed position, and score below 64 at seed
0. Any failed control makes the campaign unevaluable; do not resample.

## Frozen transplantation

For pair `i`:

- recipient seed: `202619000 + i`;
- population: 32,768 tapes of 64 bytes, created exactly by production
  `initialize_soup(32768, recipient_seed)`;
- inoculum: 32 copies replacing the same deterministic recipient indices in both
  arms: initialize `order = arange(32768, uint32)`, call production
  `shuffle_indices(order, recipient_seed, 0xAC009100 + i)`, and take `order[:32]`;
- arms: exact witness and its single frozen composition-preserving shuffle;
- initial pool: exact post-replacement soup histogram times 16;
- initial ledgers/cross arrays and changing-write counter: zero; initial pairing
  order: `arange(32768, uint32)`;
- absolute execution epochs: `0..9999`; mutation rate `1/4096`; max steps 8,192;
  no added friction; production pairing/shuffle schedule and exact conserved pool
  mechanics; and
- observation callbacks after epochs `1, 101, ..., 9901, 10000`.

The two arms must have identical background bytes outside replacement indices,
initial global symbol histograms, and pool vectors. Initial provenance labels are
1 for all 64 bytes at the 32 replacement indices and 0 everywhere else, in both
arms. Carry labels with the frozen FR-I002 semantics. Save and checksum pre-run
soup, labels, replacement indices, pool, and preparation manifest before launch.
Pin and verify the production mechanics, initializer/evaluator/shuffle helpers,
and FR-I002 provenance source blobs in the preparation artifact. Run six
processes with `NUMBA_NUM_THREADS=1`.

## Prospective descendant observation

At every callback, first verify exact conservation and binary labels. For every
tape whose `sum(labels) >= 48` (equivalently, mean label at least 0.75), evaluate
each unique 64-byte sequence separately with the unchanged paper score using
assessment seed 0. Do not call a batch helper whose seed changes with candidate
index. Cache scores by exact tape bytes in a per-run disk-backed SQLite table keyed by
the 64 raw bytes, without a size cap; use bounded-memory chunks of at most 4,096
new sequences. A resource failure is unevaluable, not permission to subsample.
An occurrence is an operational functional descendant candidate exactly when its
individual seed-0 score is 64
and its label sum is at least 48. It is **non-exact** when its bytes differ from
the arm's inoculum target.

Record, without feeding observations back into mechanics:

- total and non-exact descendant-candidate abundance and distinct sequence counts;
- maximum and histogram of qualifying provenance counts 48–64;
- exact inoculum-target abundance;
- total tapes and unique sequences entering score evaluation; and
- conserved mechanics counters, ledgers, final soup checksum, and label checksum.

For every callback, save a compressed audit table containing every scored input
as exact 64-byte sequence, label count, and abundance, canonically sorted by
lexicographic bytes then ascending label count. Its canonical checksum is SHA-256
over concatenated records `64 raw bytes || uint8 label_count || little-endian
uint64 abundance`. This distinguishes occurrences of identical bytes with
different provenance counts. Also save compressed full soup and label arrays at
every callback. The analyzer must reconstruct each audit table, exact-target
count, and descendant aggregate from those snapshots and independently rescore
all unique eligible sequences; no runner aggregate is accepted on checksum alone.
Observation code must pass an isolation test showing identical bytes, pool,
order, ledgers, counters, and mechanics metrics with observation enabled and
disabled.

Before reading any source checkpoint, generate synthetic tape `i`, byte `b` as
`splitmix64(0xAC009200 XOR splitmix64(i * 64 + b)) & 0xff` for indices
0–32,767; assign every tape label count 48. Warm JIT compilation with tape 0,
then in a fresh process time exact individual-seed-0 scoring and SQLite insertion
for all 32,768 distinct tapes using `/usr/bin/time -v`. Exclude only the explicit
warm-up from elapsed time. The callback must finish within 20 minutes and maximum
RSS below 8 GiB. Project worst-case scoring wall time as `elapsed * 101 * 18 / 6`
and require at most 72 hours. Require free destination space of at least the raw
callback snapshot bound
`32768 * 64 * 2 * 101 * 18` bytes plus 20 GiB, and available RAM at least six
times measured peak RSS plus 4 GiB. Independent rescoring is sequential. If any
check fails, optimize exact computation/storage and repeat this same preflight,
without subsampling or inspecting campaign outcomes.

## Frozen outcomes

Define the post-transient window as callbacks at epochs at least 1,001. Define the
final persistence window as the ten callbacks `9101, 9201, ..., 9901, 10000`.

For each arm:

- **post-transient non-exact load:** sum of non-exact descendant-candidate
  abundance over all post-transient callbacks; and
- **final non-exact abundance:** non-exact descendant-candidate abundance at epoch
  10,000.

For witness arms, **sustained final non-exact presence** requires non-exact
candidate abundance to be positive at every final-window callback and exact
witness abundance to be zero at every one. For shuffled controls, **sustained
non-exact false-positive presence** requires non-exact candidate abundance at
every final-window callback regardless of whether the exact shuffled target is
also present. Exact-target counts cannot satisfy the witness endpoint or shield a
control false positive.

## Integrity and acceptance

The campaign passes only if all conditions hold:

1. all 18 runs complete, conserve exactly at every callback, have binary labels,
   valid frozen inputs, and pass observation isolation;
2. at least 7/9 witness arms have sustained final non-exact presence;
3. at most 1/9 shuffled-control arms have sustained non-exact false-positive
   presence;
4. witness post-transient non-exact load is strictly greater than its paired
   shuffle in at least 8/9 pairs (ties and losses both fail that pair); and
5. every callback audit-table checksum verifies, every scored input is
   independently rescored, and final soup/label artifacts match final aggregates.

Report separately the integrity, witness sampled-presence, control-specificity,
and paired-load gates, plus paired loads, final abundance, sustained status,
exact-target diagnostics, and per-callback trajectories. For the directional
paired sign result, report the frozen one-sided fair-sign tail probability; 8/9
corresponds to `10/512 = 0.01953125`. This probability is descriptive because
parents are selected strict origins and callbacks are repeated within pair.

## Decision ladder

- **Pass:** support only sustained sampled presence of non-exact operational
  functional-descendant candidates under this transplantation protocol. Presence
  at callbacks is not continuous lineage continuity; value-change provenance
  omits control/address dependence and does not show that inherited bytes cause
  the score-64 phenotype. A later heredity experiment would require a new
  perturbation and preregistration.
- **Fail with valid integrity:** report which of sampled presence, control
  specificity, or paired advantage failed; conclude only that the composite
  persistence criterion failed. Stop BFF lineage/persistence/ecology work and
  pivot to a substrate with explicit atomic reproduction and lineage identity.
- **Unevaluable:** repair only mechanics, observation, or artifact integrity and
  rerun unchanged inputs. Do not adjust the 0.75 threshold, endpoint windows,
  inoculum, horizon, or acceptance counts.
