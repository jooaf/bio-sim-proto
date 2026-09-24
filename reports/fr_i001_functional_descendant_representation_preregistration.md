# FR-I001 functional-descendant representation mechanics gate

**Frozen before implementation:** 2026-09-18

## Motivation and scope

AC-P006 showed strong early exact-copy amplification but complete exact-tape
extinction by epoch 1,001. Exact byte identity therefore cannot distinguish true
functional-lineage loss from propagation through altered descendants. FR-I001 is
a stop-limited mechanics gate for a prospective descendant representation. It is
not a reanalysis of AC-P006 and makes no persistence claim.

The representation combines a strict functional phenotype (existing score 64)
with explicit byte-level informational provenance from a seeded parent. If this
controlled gate fails, stop BFF lineage/ecology work and pivot to a substrate
with atomic reproduction and lineage identity.

## Frozen source split

Use the ten verified AC-P005 score-64 witnesses in source-seed order:

`202615001, 202615004, 202615006, 202615007, 202615008, 202615011,
202615014, 202615015, 202615017, 202615018`.

The first five are development witnesses used only for threshold calibration.
The last five are held-out confirmation witnesses. Use the frozen deterministic
composition-preserving shuffled controls from AC-P006. Do not replace a witness
or shuffle.

## Provenance semantics

Implement a separate observational BFF executor carrying one provenance label per
byte. It must reproduce the existing unconserved `execute_bff` byte state and
step count exactly.

Initialize all parent-witness bytes with label 1 and all noise bytes with label 0.
For successful writes:

- `.` and `,` copy the source byte's provenance label to the destination only
  when the destination byte value changes;
- `+` and `-` retain the destination byte's existing label because the new value
  is informationally transformed from that byte;
- every equal-value no-op takes precedence and retains the destination label,
  even when source and destination labels differ; and
- head movement, loops, and control flow do not alter labels.

This is value-change data provenance. It excludes instruction, address, and
control dependencies and is not complete informational dependence, conserved
material, or biological parenthood.

The functional assay contains no mutations. Between serial propagation rounds,
move the right output tape and its labels into the left half exactly as the paper
evaluator moves bytes; reset the right half to the original trial noise and zero
labels. Every interaction uses the paper evaluator's fixed 8,192-step budget.

## Parity gate

Before classifier calibration, require exact equality of output bytes and step
counts between the existing `execute_bff` and provenance executor for 1,000
joint tapes. Generate byte `b` of case `c` as
`splitmix64(0xAC007200 XOR splitmix64(c * 128 + b)) & 0xff`; cycle maximum-step
values over `1, 2, 16, 128, 1024, 8192`. Add directed byte/step parity fixtures
for copy in both directions, arithmetic wraparound, head wrapping, nested and
unmatched brackets, self-modifying code, and budget boundaries.

Separately verify labels for both copy directions, equal-value copies with
opposing labels, arithmetic writes, and serial right-to-left label transfer plus
noise reset. Any mismatch stops implementation; do not tune provenance rules
around classifier outcomes.

## Frozen propagation observations

Number witnesses globally 0–9, trials 0–12, final tapes 0–1, and bytes 0–63.
For witness index `w`, set paper-noise base seed to `0xAC007000 + w` for every
arm. Generate its 13 trial-noise tapes with the existing evaluator formula:
`local = splitmix64(base_seed)` and noise byte `b` in trial `t` is
`splitmix64(local XOR splitmix64((t + 1) * 64 + b)) & 0xff`.

For each witness and trial:

1. run the unchanged initial interaction plus four serial propagation rounds;
2. retain both final 64-byte tapes and provenance arrays;
3. score each final tape with the unchanged functional evaluator using assessment
   seed `0xAC007 + w * 1000 + t * 2 + tape_index`; and
4. record provenance fraction (label-1 bytes / 64).

Use identical noise and assessment seeds across original, shuffled, and random
arms. Generate random-parent byte `b` as
`splitmix64(0xAC007100 XOR splitmix64(w * 64 + b)) & 0xff`. Random and shuffled
parents receive label 1 at input, so specificity cannot pass merely because
controls lack provenance.

A final tape is classified as an operational functional-descendant candidate only
if its unchanged paper score-64 proxy is 64 and its provenance fraction is at
least the frozen threshold. A trial is detected if either final tape is
classified. Score 64 is the existing stable-position proxy: it does not require
whole-tape agreement, identity with the input, or prove that inherited bytes
cause the phenotype.

## Frozen threshold calibration

Evaluate thresholds `{0.125, 0.25, 0.5, 0.75}` on the five development witnesses.
For each threshold compute original-witness trial sensitivity and pooled
shuffled-plus-random trial false-positive rate. These are operational arm-
detection rates; there is no independent biological descendant ground truth.
Select the threshold maximizing `sensitivity - false_positive_rate`; ties choose
the higher threshold.

Freeze implementation, parity evidence, selected threshold, and development
metrics in a calibration artifact before unblinding any held-out output. After
unblinding, only documented parity/determinism/artifact repairs are permitted;
no classifier or assay change may be made.

## Held-out acceptance gate

After freezing the selected threshold, evaluate the five held-out witnesses
(65 trials per arm). The representation passes only if all conditions hold:

1. executor parity passed 1,000/1,000 cases;
2. original-witness detection is at least 52/65 trials;
3. shuffled-control detection is at most 3/65 trials;
4. random-control detection is at most 1/65 trials;
5. results and selected threshold are deterministic across two complete reruns;
   and
6. every classified tape independently satisfies score 64 and the selected
   provenance threshold.

Report per-witness operational sensitivity, control detections, score
distributions, provenance distributions, and selected threshold. Report nominal
95% Wilson binomial intervals for trial-level rates while explicitly noting that
65 trials are clustered within five selected score-64 parents and do not provide
population-level independent uncertainty. The deterministic repeat is a
reproducibility check, not fresh confirmation. These witnesses are held out only
from FR-I001 threshold calibration, not from prior score-64 selection.
Development outcomes cannot substitute for held-out failures.

## Decision ladder

- **Pass:** implement the same frozen provenance semantics in the exact conserved
  soup kernel, first under a mechanics parity gate that compares bytes, pool,
  write ledgers/counters, scarcity blocks, friction blocks/counter stream, and
  interaction outputs. Blocked and no-op writes must retain labels. Successful
  mutation writes must reset the destination label to 0; this mutation rule is
  frozen now but not exercised by FR-I001. Only after conserved parity passes may
  new held-out descendant-aware transplantation be preregistered.
- **Fail:** stop BFF lineage, persistence, maintenance, and ecology experiments.
  Retain strict origin, composition convergence, and transient exact-copy
  amplification as bounded results, and pivot to a substrate with explicit birth
  and lineage identity.
- **Unevaluable implementation defect:** repair only byte/step parity,
  determinism, or artifact defects and rerun the frozen gate; do not alter source
  tapes, controls, trial count, threshold grid, or acceptance criteria.

A pass validates only a controlled descendant representation. It does not itself
show persistence, heredity, organisms, adaptation, ecology, or organization.
