# SM-H002 descendant sequence-order perturbation screen

**Frozen before implementation:** 2026-10-01

## Question and bounded inference

SM-H001 showed that descendants later produce children while retaining inherited
sequence, but did not test whether that sequence causes competence. SM-H002 asks:

**For a prospectively frozen panel of renewing descendant genotypes, does exact
symbol order support reproductive renewal better than a composition-preserving
shuffle, either alone or with canonical partner support?**

A pass identifies a causal effect of sequence order under the tested context.
It does not isolate whether the effect acts through binding, catalysis, templating,
execution, or cleavage; establish mutation–selection heredity or adaptation;
show autonomous reproduction outside the declared partner context; or establish
metabolism, self-maintenance, ecology, organisms, or general Stringmol superiority.

## Frozen source evidence and candidate panel

Source data are the completed SM-H001 hosts only. Pin:

- source analysis SHA-256
  `1c64913c61624ddc82800dc33620e5c3da11ae67240a6abacaf4d8e15b4bbd04`;
- source seeds `202623000`–`202623019`;
- source raw receipts, launch seal, preparation, and implementation commit
  `8c3bd74`.

For each source run, among `retained_late` renewing descendants:

1. recover the visible birth sequence from the independently verified productive
   source edge;
2. compute distance from the 64-byte canonical host as positional mismatches over
   the shared prefix plus absolute length difference;
3. select greatest distance; tie-break by earliest birth tick then lowest ID; and
4. retain source seed, ID, tick, length, retention, sequence bytes, and hash.

Deduplicate selected sequences by SHA-256, retaining all source provenances and the
lowest source seed/ID as canonical provenance. Sort the final panel by sequence
SHA-256. Calibration indicates 15 unique sequences (length 36–65), including one
canonical and 14 noncanonical genotypes; implementation must reproduce exactly
that count before any assay. This is a deliberately competence-enriched panel,
not a random sample or prevalence estimate.

## Frozen perturbation

For each exact candidate byte string, construct one deterministic
composition-preserving shuffle:

- encode `candidate_sha256` as 64 lowercase ASCII hex bytes and assign each
  indexed byte the 32-byte key
  `SHA256(b"SM-H002\0" || ASCII(candidate_sha256) || b"\0" || uint32_be(nonce) || uint32_be(index) || byte)`;
- sort indexed bytes lexicographically by `(key, original_index)`;
- concatenate bytes in that order;
- start nonce at zero and increment until shuffled bytes differ from exact;
- freeze the first differing result and nonce.

The shuffle must have identical length and exact per-symbol histogram, contain no
NUL/out-of-alphabet byte, and differ at least at two positions. Candidate and
shuffle records are sealed before launch. No outcome-dependent reshuffle is
allowed. Sequence order is the only molecular treatment; altered binding,
execution, or template motifs are possible mechanisms rather than confounds to
remove retrospectively.

## Pinned simulator and conservation

- upstream commit `15dad84da126a4f887ba945c23a13e89e827f067`;
- patches 0001–0004 unchanged;
- exact molecular + accessible-pool + waste conservation;
- histogram amount 0 and decay destination recycle;
- 40×40 grid, global interaction/placement, mutation 0.0002, decay 0.0005,
  5,000 steps, report interval 100;
- lineage and version-2 material observation enabled;
- no simulator or chemistry change.

Every assay uses 140 molecules in the canonical frozen positions and one assay
seed shared across its four-condition genotype block.

## Four-condition genotype block

For panel rank `i = 0..14`, use seed `202624000 + i`:

1. **EXACT_SELF:** 140 exact candidate copies; IDs 0–139 are candidate cohort.
2. **SHUFFLE_SELF:** 140 shuffle copies; IDs 0–139 are candidate cohort.
3. **EXACT_SUPPORT:** 70 exact candidates at positions 0–69 and 70 canonical
   hosts at positions 70–139; IDs 0–69 candidate cohort, 70–139 support cohort.
4. **SHUFFLE_SUPPORT:** identical support setup with shuffled candidate.

All molecules retain native label `Q`; cohort is analysis metadata derived only
from sealed load order and IDs. Labels or simulator behavior may not encode
cohort. Exact/shuffle pairs have identical initial per-symbol totals within each
context. SELF and SUPPORT answer different questions and need not have identical
inventories.

There are 60 scientific runs. Use six workers, all runs in the denominator, and
no resume, replacement, selective retry, or horizon extension.

## Cohort and reproductive endpoints

Independently replay the complete material journal as in SM-H001. Maintain two
separate structures:

- **qualifying source lineage:** unchanged SM-H001 productive/source-survival
  definition, depth, renewal, and whole-transfer exclusion;
- **material-source cohort:** initial candidate/support assignment propagated to
  every child from the inferred suffix source across all successful transfers,
  including whole-parent transfers. Unknown/conflicting cohort is integrity
  failure. Active/passive labels never assign cohort.

For each cohort report productive source births, late productive births
(`2500 <= tick < 5000`), renewing descendants, serial source births, qualifying
depth, late renewing descendants, retention, survival, partner roles, and
whole-transfer/orphan events. Native total outcomes remain diagnostics.

A run has **exact candidate liveness** when the candidate cohort records:

- at least 100 productive source births;
- at least 25 serial source births;
- qualifying source depth at least 2;
- at least 50 late productive source births; and
- at least 5 late renewing descendants.

For one genotype/context pair, **sequence specificity** requires:

- exact candidate productive births minus shuffle candidate productive births at
  least 100 and exact at least twice shuffle;
- exact late productive births minus shuffle late productive births at least 50;
- exact serial source births minus shuffle serial source births at least 25; and
- exact candidate liveness.

If a shuffle denominator is zero, the ratio condition passes only when exact is
positive and the absolute margin passes.

## Mechanics, configuration, and analysis gates

Before unseen assays:

1. verify the complete SM-H001 source package and regenerate the exact frozen
   candidate panel deterministically;
2. fresh-build patches 0001–0004 and rerun all upstream, lineage, conservation,
   recycling, renewal, isolation, deterministic, pytest, mypy, and directed gates;
3. require a custom canonical EXACT_SELF config/output to match the inherited
   canonical-host workflow byte-for-byte on a development seed;
4. parse every generated config and prove exact ID/load order, positions,
   sequence bytes, cohort ranges, exact/shuffle histogram equality, initial totals,
   environment, command, and checksums;
5. synthetic cohort fixtures cover active/passive source, whole transfer,
   candidate/support cross-pairing, source-lineage versus cohort ancestry,
   unknown/conflicting cohort, late boundaries, extinction, and each specificity
   threshold/ratio edge;
6. logging/workflow changes add no simulator output or RNG difference; and
7. commit/push implementation, directly verify `origin/main`, and repeat the seed
   audit before launch.

Any mismatch stops before assays. Representation, perturbation, panel, threshold,
context, seed, or chemistry changes require a new experiment ID.

## Integrity gate

All 60 runs must pass process, source/panel, build/input/output inventory, exact
journal replay, per-symbol conservation, nonnegative ledgers, lineage/source-DAG,
cohort propagation, suffix transfer, snapshot, identity-history, counter, schema,
alphabet, and bounds checks. Boundary errors must be zero. Integrity failure makes
the experiment unevaluable rather than a negative biological result.

The canonical exact genotype must satisfy exact candidate liveness in both SELF
and SUPPORT; otherwise the assay is unevaluable even if other counts look
positive.

## Frozen scientific decisions

Define:

- `self_specific`: at least 12/15 genotypes pass sequence specificity in SELF;
- `support_specific`: at least 12/15 pass in SUPPORT;
- `context_general`: the same at least 12/15 genotypes pass in both contexts.

Decision ladder:

1. **Context-general pass:** `context_general`; exact order causally supports
   reproductive renewal in both contexts for a shared genotype set.
2. **Dual-context screen pass with insufficient overlap:** `self_specific` and
   `support_specific` but not `context_general`; both contexts separately meet
   the screen threshold, but fewer than 12 identical genotypes pass both. Report
   both effects without claiming genotype-general context robustness.
3. **Supported-context-only screen pass:** `support_specific` true and
   `self_specific` false; exact order is supported in the canonical-partner assay,
   while self-only did not meet its panel criterion. This does not prove partners
   are necessary.
4. **Self-context-only screen pass:** `self_specific` true and
   `support_specific` false; report sequence-specific self-context competence and
   possible support interference, without generalizing.
5. **Valid failure:** neither context passes; report genotype-level effects and
   stop before functional-heredity claims.
6. **Unevaluable:** integrity or canonical-positive-control failure; repair only
   implementation/artifact defects and rerun the unchanged complete matrix.

All 15 genotypes remain in each denominator, including duplicate-source
provenances collapsed into the canonical genotype. Report exact and shuffle raw
metrics, paired differences, genotype sequence/length/distance, and unique versus
canonical genotype strata. The 12-of-15 fair-coin upper tail is
`576/32768 = 0.017578125`, descriptive and not a p-value for the composite gate.

## Gated continuation

Any context-specific or context-general scientific pass permits a separately
preregistered replicate confirmation on new assay seeds. Confirmation may test
only the context(s) whose panel criterion passed, must retain
the full 15-genotype panel and controls, and cannot weaken thresholds after seeing
SM-H002. No energetic/ecological experiment supersedes this gate.
