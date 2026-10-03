# SM-M001 native-versus-zero mutation baseline

**Frozen before implementation:** 2026-10-03

## Question and bounded inference

Under the validated conserved-recycle canonical Stringmol host condition:

1. is native mutation required for descendant reproductive renewal; and
2. does native mutation causally increase realized descendant-sequence diversity
   or reduce inherited-sequence continuity relative to mutation disabled?

A paired difference identifies the total effect of Stringmol's `MUTATE` setting,
which jointly controls native insertion/deletion and substitution proposals. It
does not identify those mechanisms separately, prove beneficial adaptation,
assign fitness to variants, establish open-ended evolution, or compare mutation
semantics directly with BFF.

This experiment is independent of the closed SM-H003 panel gate. If both arms
retain robust renewal, a separately preregistered birth-boundary factorial becomes
eligible; that continuation does not rescue SM-H002/H003.

## Pinned system and sole treatment

Use:

- upstream commit `15dad84da126a4f887ba945c23a13e89e827f067`;
- unchanged patches 0001–0004;
- 140 canonical 64-byte hosts in the frozen positions;
- 40×40 grid, global interaction and placement;
- exact molecular + accessible-pool + waste conservation;
- free-pool multiplier 0 and native-decay destination recycle;
- decay 0.0005, 5,000 steps, report interval 100; and
- lineage plus version-2 material observation.

The paired arms differ only in the rendered `MUTATE` value:

- **NATIVE:** `0.0002`;
- **ZERO:** `0`.

`MUTATE 0` is the pinned simulator's native mutation-disabled mode. It is not a
new opcode or mutation patch. Existing conserved copy code must continue to take
the native mutation draw even when rates are zero, preserving paired RNG use until
state divergence. No simulator, chemistry, conservation, decay, placement,
interaction, representation, or observation change is allowed.

## Matrix

Run 20 paired unseen seeds `202626000`–`202626019`, NATIVE and ZERO for each seed:
40 runs total. Use at most six workers and `NUMBA_NUM_THREADS=1`. All runs remain
in the denominator. No resume, selective retry, replacement, extension, or
outcome-dependent analysis change.

## Renewal endpoints

Reuse the independently replayed SM-H001 productive-source definitions,
whole-parent exclusion, source lineage, renewal, late boundary, and positional
retention. A run has **renewal core** when the same run satisfies:

1. productive source births ≥100;
2. renewing descendants ≥10;
3. serial source births ≥50;
4. maximum source depth ≥2; and
5. late renewing descendants ≥5.

A run has **renewal with continuity** when it has renewal core and at least five
retained late renewals (birth length ≥32 and first-source positional retention
≥0.90), unchanged from SM-H001.

An arm is **viable** when at least 16/20 runs have renewal with continuity. Report
core and continuity counts separately, every component, all discordant pairs,
paired differences, and native totals. Ties remain ties.

## Sequence endpoints

The canonical reference is the frozen 64-byte host. From independently replayed
productive source edges, use each child's complete visible birth buffer and
report per run:

- productive births with exact canonical birth sequence and their fraction;
- productive births with noncanonical birth sequence and their fraction;
- number and Hill q=0 count of unique productive-birth sequences (identical here,
  retained under the explicit name `productive_unique_sequences`);
- Shannon/Hill q=1 effective productive-birth sequence diversity;
- productive-birth length distribution and unique lengths;
- the same exact/noncanonical and diversity measures for renewing descendants'
  productive birth buffers; and
- first-source retention distribution, median, minimum, and exact-retention
  fraction among renewing descendants.

A sequence is keyed by complete visible bytes plus length, not hash alone.
Repeated births count in q=1 abundance but once in q=0. Whole-parent transfers,
orphan-source events, and nonproductive births are excluded from these primary
sequence endpoints and reported separately. For an empty productive-birth set,
exact and noncanonical counts/fractions, q=0, q=1, and unique lengths are all
zero and the length distribution is empty. For an empty renewing-descendant set,
counts and fractions are zero, distributions are empty, and median/minimum
retention are JSON null. Such runs remain in every denominator.

Define the preregistered **realized-divergence effect** when the same at least
16/20 pairs have both:

- NATIVE productive unique-sequence count greater than ZERO; and
- NATIVE noncanonical productive-birth fraction greater than ZERO.

Also report, without substituting for that conjunction, directional pair counts
and paired median differences for every sequence endpoint. No post-hoc threshold
on effect magnitude is allowed.

## Gates before launch

1. reproduce the source lock, patch hashes, canonical host, H001 definitions, and
   H001/H002/H003 observation parity;
2. fresh-build unchanged patches and pass upstream, isolation, lineage,
   conservation, decay-routing, renewal, perturbation, and replicated fixtures;
3. parse all 40 configs and prove exact positions, IDs, host bytes, initial
   material, commands, endpoints, environment, and equality except the one
   `MUTATE` value;
4. require exact initial per-symbol equality within every pair;
5. add synthetic fixtures for exact/noncanonical sequence classification,
   length-sensitive identity, q=0/q=1 abundance, renewal filtering, empty sets,
   retention summaries, 16/20 conjunction boundaries, discordant viability, and
   every decision branch;
6. demonstrate deterministic repeatability in both arms and statically verify
   that `MUTATE 0` preserves the pinned copy operation's baseline random draw and
   sets both mutation rates to zero. Additional native-arm draws after a mutation
   branch are treatment semantics and are allowed to desynchronize paired streams;
   no cross-arm byte-equality or identical-call-path claim is permitted;
7. commit and push implementation, directly verify committed bytes on
   `origin/main`, and repeat held-out seed audit before launch.

Any mismatch stops before assays. Changes to treatment, seeds, endpoint, threshold,
or mechanics require a new experiment ID.

## Integrity gate

All 40 runs must pass process, build/input/output inventory, exact ordered event
replay, per-symbol molecule/pool/waste conservation, nonnegative ledgers,
source-lineage and identity DAGs, suffix transfer, snapshots, counters, schema,
alphabet, bounds, and END-state checks with zero boundary errors. Integrity failure
is unevaluable rather than biological evidence.

The ZERO arm must contain no mutation-enabled config value. Because the current
journal does not label mutation proposals separately from ordinary copy writes,
SM-M001 infers mutation's total effect only from randomized arm differences in
realized sequences and renewal. It must not claim a counted number of mutation
events.

## Frozen decision ladder

Let `native_viable`, `zero_viable`, and `realized_divergence` be defined above.
Apply in order after integrity:

1. **Both viable, divergence detected:** mutation causally increases realized
   sequence divergence, while the ZERO arm independently demonstrates that native
   mutation is not required for robust renewal under these conditions.
   Birth-boundary factorial eligible. This is not an equivalence claim.
2. **Both viable, divergence not detected:** both settings independently attain
   robust renewal, so native mutation is not required under the tested ZERO arm;
   realized sequence-divergence effect is unsupported. Birth-boundary factorial
   still eligible. Do not claim equivalent renewal performance.
3. **Native only viable:** NATIVE attains the operational viability gate and ZERO
   does not. This threshold crossing alone does not prove mutation-supported
   renewal or necessity. Birth-boundary factorial not eligible under the frozen
   continuation rule.
4. **ZERO only viable:** ZERO attains the operational viability gate and NATIVE
   does not. This threshold crossing alone does not prove mutation suppression,
   although it demonstrates renewal without native mutation. Birth-boundary
   factorial not eligible.
5. **Neither viable:** valid renewal-baseline failure; stop the continuation.
6. **Unevaluable:** integrity/configuration failure; repair only implementation or
   artifact defects and rerun the unchanged complete matrix.

Report exact arm counts and all pairs regardless of branch. The 16-of-20 fair-coin
upper tail `6196/1048576 = 0.005908966064453125` is descriptive, not a p-value for
the composite gates. Both-arm viability does not establish adaptation; greater
sequence diversity does not establish that variants are functional or selected.
