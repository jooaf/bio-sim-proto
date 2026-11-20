# XL existing-log role/opportunity contract — 2026-11-20

Written before extracting new role/cohort counts. POST HOC measurement, not
preregistration, confirmation, mediation, or a competence assay. All four single
histories retained; repeats only validate identity. No simulations, builds,
fixtures, native runners or VM replay. B002/B003/H003/BFF remain closed.

## Fixed outputs and denominators

Produce individual CSV/JSON, source-action CSV/JSON, cohort CSV/JSON and primary
placement contrasts GL-GG / LL-LG CSV/JSON, plus provenance/checksums/report.
Individuals include every admitted nonfounder (IDs need not be contiguous), birth
schedule tick/order, exact visible HOST at birth, rooted status and first qualifying
source renewal schedule tick/order, source active/passive role, instruction owner
and partner. Material source, active executor, passive partner, instruction-head
genome owner overlap and must not be added as disjoint successes. Instruction owner
is NOT the COPY read head. Also report first active dispatch and first successful
cleavage participation; ever-active-at-successful-cleavage differs from ever-source.

Lifecycle ends at observed death tick/order/cause or END5000 roster. Death is
competing termination, not administrative censoring. No-event survivors are
administratively right censored. Tick followup is end minus birth, even when zero;
ordered events distinguish same-tick actions. Null on zero clock denominators.

Observed opportunities: initiator searches/empty searches, encounter initiator and
selected partner, successful binding active/passive and dispatch active/passive;
copy/cleavage opcode dispatch only if source semantics identify them soundly.
Candidate count is initiator-only, not exposure of every live child. No inference
of unbound occupancy, continuous eligibility or counterfactual encounters. Counters
before first source renewal exclude its outcome and its triggering dispatch;
record total-lifetime counters separately. Repeated encounters count as events,
not independent molecules or distinct available partners.

Cohorts fixed: all, early birth<2500, late birth>=2500; optional exact-HOST birth
strata descriptive only. Include raw counts, denominators, rooted renewers,
ever-active successful cleavage, dead/no-event and alive/no-event, total followup,
and observed opportunity. No new cutoffs, tests, hazard/KM models or gates.
Summaries are within-history descriptions, never pooled technical replicates.
Preserve inherited checkpoint<t alignment (no new checkpoint reconstruction).

## Joins, custody and qualification

Inspect CSV schemas and native/replay semantics before implementing joins.
DISPATCH.material_index is preinstruction cursor, not source postmaterial_index;
link via COMPLETE and BIRTH ordering, validate participants/source/child/material
outcome. FAILED/NO_CHANGE do not create offspring. Validate START founders0..139,
all IDs, lifecycle and chronology, END roster/population, prior rooted sets and
existing aggregate counts where definitions coincide. Fail closed on corruption,
missing/duplicate joins, reused output paths and bad hashes. Stream journals.

Hash consumed inputs before/after against frozen inventory and portable copies;
bind decision f8349c017deb2f4d25d48a5cd8b05db89d6ae09ccdaa5de2540fd5dc23875eb5,
prior accepted final3/final4 and analysis, own spec/code/tests. Two fresh serial
extractions must have byte-identical scientific tables. Synthetic tests cover
passive source, owner differing from active, same-tick lifecycle, founders,
late/no-event, death versus END, repeated encounters, failed/nochange cleavage,
noncontiguous IDs, empty cohorts/zero denominator and corrupt joins. Run normal,
-O and strict mypy owned files only. Retain failures.

Storage checked before writing: /tmp/sm is Elements stringmol-posix.ext4 via
fuse.ext4, 17GiB available; Elements 1.6TiB available (above5/10GiB minima).
Owned evidence /tmp/sm/xlo-e; portable prompt-directory/export; <=1GiB/2GiB.
Shared Python read-only, one process, temporary/cache files on Elements.
First shell inspection failed at Nushell date -I parsing before extraction; no
scientific data read or changed by that command. No internal fallback permitted.

Inference boundary: observed source use is not autonomous catalysis; active
execution remains partner/context dependent. Logs cannot identify intrinsic
competence or its causal explanation. Any future competence assessment would need
controlled partners, roles, followup and opportunity, without designing or
launching such an experiment here. Parent review required; no self-approval.
