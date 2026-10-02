# SM-H002 descendant sequence-order perturbation report

**Run date:** 2026-10-02  
**Decision:** **UNEVALUABLE under the frozen positive-control rule**  
**Follow-up:** not eligible

## Execution and integrity

All 60 sealed runs completed once: 15 unique SM-H001 renewing-descendant
genotypes in exact/shuffle × self/canonical-support blocks on paired unseen seeds.
All runs passed process, complete journal replay, exact per-symbol conservation,
nonnegative-ledger, source-DAG, cohort propagation, suffix-transfer, snapshot,
identity, schema, bounds, and artifact checks. Independent review replayed all 60
raw outputs with six workers and reproduced the 547.5 MB analysis byte-for-byte.
Thus the outcome is not an implementation or integrity failure.

Raw campaign:
`/home/jojo/bio-sim-results/bazzite/sm_h002_descendant_sequence_perturbation/bazzite.attlocal.net/prepared`

Analysis and publication metadata are in the sibling `analysis/` directory so the
sealed preparation filename allowlist remains valid.

## Frozen decisions

The panel required at least 12/15 sequence-specific genotypes in a context. The
observed counts were:

| Criterion | Result |
|---|---:|
| SELF sequence-specific genotypes | 10/15 |
| SUPPORT sequence-specific genotypes | 7/15 |
| Same genotypes passing both contexts | 5/15 |
| SELF panel threshold | fail |
| SUPPORT panel threshold | fail |
| Context-general threshold | fail |

The canonical exact genotype passed SELF liveness but failed the mandatory
SUPPORT positive control. Its candidate cohort in exact SUPPORT produced 314
productive source births, 25 serial source births, depth 2, and 143 late
productive source births, while its shuffled candidate produced zero on each of
those measures. However, the exact canonical candidate had **zero late renewing
descendants**, below the frozen minimum of five. All other canonical SUPPORT
liveness components and all specificity margins passed.

The preregistration states that any canonical exact failure in either context
makes the experiment unevaluable. Therefore the panel counts cannot be promoted
to a valid biological pass or failure. There was no artifact defect to repair,
so the unchanged matrix was not rerun.

## Descriptive outcomes retained

The exact candidate cohorts often greatly exceeded their composition-preserving
shuffles, but these are descriptive under the blocked gate:

| Context / metric | Exact range (median) | Shuffle range (median) |
|---|---:|---:|
| SELF productive source births | 0–1,083 (586) | 0–247 (0) |
| SELF late productive births | 0–752 (247) | 0–0 (0) |
| SELF serial source births | 0–453 (105) | 0–122 (0) |
| SELF late renewing descendants | 0–53 (7) | 0–0 (0) |
| SUPPORT productive source births | 87–652 (322) | 0–159 (0) |
| SUPPORT late productive births | 0–391 (179) | 0–28 (0) |
| SUPPORT serial source births | 0–153 (50) | 0–69 (0) |
| SUPPORT late renewing descendants | 0–13 (6) | 0–4 (0) |

In SELF, 12/15 genotypes met the productive-birth margin and ratio components,
11/15 met late- and serial-birth margins, but only 10/15 met exact candidate
liveness and the full conjunction. In SUPPORT, productive margin and ratio held
for 13/15, late margin for 14/15, serial margin for 10/15, and exact liveness for
8/15; only 7/15 met the full conjunction.

These patterns motivate future genotype- and context-specific work, but they do
not rescue the frozen positive control or panel thresholds.

## Bounded conclusion

SM-H002 does **not** establish causal functional heredity. The experiment is
unevaluable because the canonical exact candidate failed its preregistered
supported-context late-renewal positive control. It also produced no eligible
panel-level context for the preregistered unseen-seed confirmation.

The exact-versus-shuffle differences remain evidence-generating observations that
sequence order may matter for reproductive competence in some genotypes and
contexts. They do not prove sequence-order function for the panel, partner
necessity, mutation–selection heredity, adaptation, self-maintenance, ecology,
organisms, or general Stringmol superiority over BFF. Any redesigned assay must
use a new experiment ID, seeds, and prospective positive-control/context rules;
it may not reinterpret SM-H002 or weaken its frozen thresholds.
