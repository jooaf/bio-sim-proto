# Existing XL renewal synthesis specification — 2026-11-20

Scoped before extraction of the new four-cell metric matrix. This is POST HOC
DESCRIPTIVE analysis, not preregistration: published abundance/admission counts and
GG renewal 25/6/6 are already known. Base 92d48ab, own analyze/sm-xl001-renewal.
No simulations, build, fixture, full replay, thresholds/gates, or new budget.
Historical failed attempt excluded; observed histories alone are scientific units;
repeat and replay files validate identity, never add observations.

## Fixed measurements

Use verified replay1 observed summaries, cross-check all 16 result files and frozen
export inventory; decision SHA256 f8349c017deb2f4d25d48a5cd8b05db89d6ae09ccdaa5de2540fd5dc23875eb5.
Hash every consumed evidence file before and after against frozen export inventory,
including matching portable copy. Stream CSVs; do not use broken data_explore.

Admission: replay proposals = placed + failed; rates placed/proposals and
failed/proposals. Failure counts are attempt events, not distinct competent losses.
Cross-check placed children with raw lineage BIRTHs and transfer edges.

Renewal: inherit analyze_retirement.SourceReplay.transfer_summary definitions,
not its robustness gates. Founders IDs0..139 have rooted depth0. Qualifying edges
are partial, positive-offset, retained nonempty-source transfers rooted through
qualifying ancestry; whole transfers/orphans do not root descendants. Recompute
root/depth/serial counts from ordered edges and validate source/child/tick and raw
birth participants/sequence. Serial events have rooted nonfounder sources;
renewers are distinct such source IDs. Repeated actions count once for renewers,
every time for serial events. Validate records' birth/first-source ticks, retention
arithmetic, late birth>=2500 and retained-late birth length>=32 and retained/birth
>=.90. Retention is inherited full birth-buffer nonzero-byte retention, NOT visible
sequence length or standardized competence. All admitted children and late-born
admitted children (birth>=2500) are denominators for respective observed-within5000
renewal fractions. Also report rooted child denominators/fractions. Report
late-ACTING serial events and distinct sources at event tick>=2500 separately.
Unequal follow-up and right censoring prohibit intrinsic competence interpretation;
source reuse need not be active execution and ancestry alone is not competence.

HOST: exact visible bytes equal canonical founder HOST (all140 founders checked).
Source replay explicitly derives lineage visible bytes as full buffer split at
first NUL; never compare padded capacity to HOST. Validate raw snapshot schema,
IDs/coordinates, totals and neighbor geometry against replay CHECKPOINT records.
Stream verified buffer checkpoint rows to cross-check visible snapshots, and get
END exact HOST from END buffers, not an invented lineage snapshot. Replay semantics
emit lineage snapshots only for CHECKPOINT, not END. Preserve event/tick keys;
reject repeated ID rows/conflicting duplicates or missing scheduled snapshots.
Expected CHECKPOINT ticks0..4900 step100 and END5000. Zero-population checkpoints
have no agent rows but must have an explicit replay record. No interpolation.
Record total/HOST/fraction at every recorded checkpoint and END, exact HOST births,
initial/final, and inherited4000..4900 min/max/mean for population, HOST and fractions.

Spatial: occupied Moore-neighbor slots / (8*population), computed from same
40x40 torus snapshot coordinates and cross-checked against replay. END spatial
numerator/denominator use existing verified replay (no END coordinate snapshot).
Alongside each checkpoint report cumulative admitted children and renewers by tick;
these are temporal descriptions, not independent observations or causal mediation.

Zero counts remain zero; zero denominator fraction is JSON null/CSV empty, never
zero competence; no births => no renewing children. Malformed/missing IDs/ticks,
invalid hashes, missing snapshots, duplicate/reused output directories fail closed.
All four cells and all metrics retained. Primary contrasts GL-GG and LL-LG for
every numeric cell summary and aligned checkpoint metric; no significance tests.
No interaction contrast is required. Summaries of snapshots are within-history
summaries, not replicates. Recommend measurement work or a narrow hypothesis from
actual mixed directions; never launch or reopen closed B002/B003/H003/BFF.

## Qualification and custody

Small strictly typed Python csv/json reader; synthetic founders-only, fragments,
root/orphan/whole, repeated sources, late-born/late-acting, end censoring, zero
population/birth, malformed/missing IDs/ticks/snapshots, bad hash/output reuse tests.
Normal and -O tests, strict mypy analyzer/tests. Two fresh analyses, byte-identical
scientific files; retain all failure logs. POSIX evidence /tmp/sm/xla-e on verified
Elements stringmol-posix.ext4 (fuse.ext4 mount); free17GiB POSIX/1.6TiB Elements at
start, exceeding5/10GiB minima. New data <=1GiB POSIX/2GiB portable. Results only on
Elements. Export new files without overwrite, verify checksums; preserve old seals.
Commit code/tests/spec/link report only; no self-approval of scientific claims.

## Timing clarification — 2026-11-20, retained intermediate outputs

Source inspection locality_replay.py confirms CHECKPOINT(t) is at TICK entry,
before actions labeled t; END5000 follows tick4999. Thus checkpoint cumulative
births/renewers include event ticks strictly less than checkpoint tick (not <=).
This corrects alignment, not a threshold selection. Intermediate attempt2 and
final1/final2 are retained but superseded for this alignment; cell summaries are
unchanged. Final accepted descriptive artifacts will be final3/final4, following
renewed normal/-O/type qualification. Source-log remnant links and material byte
patches only for renewing sources cross-check eligibility and retention without
full replay. Frozen export VERIFIED hash and parent audit hash anchor inventory.
