# Conserved BFF artificial-chemistry discovery phase design

**Design date:** 2026-09-12  
**Status:** phase design; no experiment below is claimed or preregistered yet

## Decision context

The original integrated Phase 2 acceptance is scientifically complete as a
**NO-GO**, not an unfinished result to tune into a pass. Its 500,000-tick BFF run
proved exact conservation, long-run liveness, and persistent local byte-level
similarity, but the frozen opcode block-beta criterion failed. The BFF parasite
candidate also failed its positive control. Those outcomes remain unchanged.

The strongest genuinely novel lead is instead the conserved chemistry's
**origin-versus-maintenance asymmetry**:

- removing the six symbols enriched in the known BFF replicator class suppressed
  origin in 0/5 runs versus 3/5 controls;
- removing unrelated symbols allowed 3/5 transitions, but generated less blocked
  write load and therefore did not fully remove generic friction as a confound;
- the same severe structural-symbol shortage did not destroy an established
  replicator ecology.

This phase tests whether compositionally conserved matter is a selective filter
on which computational organizations can originate, rather than merely a global
brake on execution. That question is closer to a publishable artificial-
chemistry discovery than additional Stage 4 positive controls.

## Discovery claim ladder

The phase advances only through the following claims:

1. **Selective origin filter:** structural-symbol deprivation suppresses
   functional replicator origin beyond a demand-matched nonspecific write-block
   control.
2. **Origin/maintenance hysteresis:** the same chemistry blocks independent
   origins but is buffered by independently established replicator ecologies.
3. **Attractor redirection:** a deprived chemistry produces a functionally
   replicating class with composition outside the known class, rather than only
   suppressing all origin.
4. **Ecological consequence:** independently identified classes coexist or
   replace one another predictably under spatially heterogeneous conserved
   chemistry.

Claim 1 or 2 would be a useful new result. Claims 3 or 4 would be the stronger
artificial-chemistry discovery. No stage may be rescued by redefining emergence,
changing symbol classes, or tuning on confirmatory seeds.

## Shared definitions

### Canonical structural class

Freeze the previously identified natural-six set:

`S = {0, 44 (,), 60 (<), 91 ([), 93 (]), 125 (})}`.

This set was defined before this phase from the established natural replicator
class. It must not be changed using new outcomes.

### Functional emergence

An origin counts only when both conditions hold at a saved callback:

1. high-order entropy is at least 1 bit/byte for ten consecutive callbacks; and
2. at least one of the 1,024 most abundant exact tapes achieves the existing
   byte-exact functional self-replication score of 64.

The first qualifying callback is the origin checkpoint. Entropy alone is not a
replicator claim. The functional evaluator and tie-breaking rule are frozen from
the paper-scale probe before confirmatory runs.

### Established ecology

An origin checkpoint is established only if its continuation remains above 1
bit/byte for 5,000 further epochs and retains at least one score-64 tape at the
end. Each qualifying seed contributes at most one independently initialized
checkpoint.

### Exact conservation

Every changed tape byte remains an atomic old-symbol return/new-symbol
withdrawal. Deliberately blocked writes change nothing, so per-symbol totals must
remain exact in every conserved run.

## AC-I001 — Demand-matched class-specific origin filter

### Confound to remove

The old unrelated-symbol control blocked fewer writes than natural-six
exclusion. A direct comparison could therefore reflect total friction rather
than symbol identity.

### Mechanics-only calibration

On calibration seeds disjoint from confirmation, run only the first 5,000 epochs
of random soups and do not calculate entropy transitions or functional scores.
Measure requested changing writes and blocked-write totals.

Compare natural-six zero-supply against a deterministic **nonspecific friction
control** that rejects changing writes by a hash-derived Bernoulli decision,
independent of requested old/new symbol and without consuming simulation RNG.
Freeze the rejection probability from a declared grid by minimum absolute median
log blocked-count difference to natural-six exclusion. Ties choose the lower
probability. Calibration selects mechanics only; it cannot inspect emergence.

### Confirmation

Use 20 new matched seeds, 32,768 tapes, 100,000 epochs, mutation 1/4,096,
multiplier 2, and three arms:

- histogram-matched conserved control;
- natural-six zero-supply;
- calibrated nonspecific friction.

Primary outcome: functional-emergence incidence. Mandatory controls: full-run
blocked load, time to first block, functional score, entropy trajectory, final
composition, and exact conservation.

A preregistration should require a viable control, comparable blocked load, and a
predeclared incidence contrast before accepting class specificity. If blocked
load cannot be matched or the nonspecific arm is also suppressed, conclude
nonspecific friction and stop AC-I002–I004.

## AC-I002 — Independent origin/maintenance hysteresis

Proceed only if AC-I001 supports class specificity.

Use independent established checkpoints generated by the AC-I001 control arm's
frozen inclusion rule—not repeated perturbations of one checkpoint. Continue
each checkpoint under matched control, natural-six exclusion, and calibrated
nonspecific friction. Pair these maintenance outcomes with the corresponding
origin-arm outcomes.

Primary interaction: natural-six exclusion has a larger adverse effect on
functional origin than on established-ecology retention. Require exact
conservation and positive maintenance controls. Report checkpoint count as the
biological replicate count; continuation aliases are not independent origins.

If fewer than eight independent checkpoints qualify, generate a preregistered
checkpoint-acquisition extension with new seeds, without inspecting treatment
outcomes. If hysteresis fails, stop before attractor claims.

## AC-I003 — Alternative replicator attractors under deprived chemistry

Proceed only after robust hysteresis. Extend new natural-six-excluded origin runs
to a fixed longer horizon chosen before execution. Do not loosen the functional
emergence criterion.

A candidate alternative class must:

- achieve score 64 and persist through the frozen confirmation window;
- have a composition vector outside the preregistered distance envelope of the
  canonical class;
- arise in at least two independent seeds; and
- reproduce when transplanted into a fresh soup under the same deprived
  chemistry, with matched no-candidate controls.

Clustering or opcode novelty without functional replication is not an
alternative-life claim. If no class appears, conclude selective suppression,
not redirection, and stop.

## AC-I004 — Spatial chemistry and class coexistence

Proceed only if AC-I003 identifies at least two independently validated classes.
Place canonical and alternative classes into a conserved spatial soup with
predeclared complementary resource regions. Test invasion from rare frequency,
local persistence, cross-boundary matter transfer, and exact conservation.

The primary ecological endpoint must be class frequency or persistence under
matched homogeneous controls. Organization, trophic, or organism labels remain
prohibited unless a separate representation and intervention gate is passed.

## Required implementation before AC-I001

1. Add deterministic symbol-independent write rejection to `phase1_probe.py`,
   driven by a hash/counter rather than the simulation RNG.
2. Log attempted changing writes separately from scarcity and friction blocks.
3. Add callback functional-score sampling and first-qualified checkpoint saving.
4. Add resumable campaign manifests and central publication compatible with the
   current `just publish-to` workflow.
5. Unit-test that rejection leaves tapes/pools untouched, conservation remains
   exact, disabled rejection is byte-identical to legacy runs, and callback
   scoring matches the existing paper probe.
6. Benchmark 32,768×100,000 once before freezing process count and storage cost.

## Statistical and operational rules

- Preregister each gate and push it before implementation-specific confirmation
  runs begin.
- Calibration and confirmation seed ranges must be disjoint.
- Parallelize independent runs, never interactions inside one conserved run.
- Publish raw runs centrally; commit only compact manifests, tables, and reports.
- Treat failed positive controls, insufficient independent checkpoints, or any
  conservation residual as stop conditions.
- Report exact binomial/Fisher or paired permutation statistics as appropriate;
  do not call `p > 0.05` evidence of equivalence.
- Keep all old Phase 1/2 failures in the synthesis. This phase can add a new
  discovery; it cannot retroactively make the old integrated gate pass.

## Phase completion criterion

This discovery phase is complete when one of the following occurs:

- AC-I001 and AC-I002 pass, establishing a robust selective origin filter and
  origin/maintenance hysteresis; or
- any prerequisite fails and its stop rule is recorded; or
- AC-I003/004 produce a stronger validated alternative-attractor or coexistence
  result.

The recommended next action is **AC-I001 mechanics implementation and bounded
calibration preregistration**, not another spatial beta-diversity or parasite
parameter sweep.
