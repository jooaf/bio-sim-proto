# SM-B003 development addendum: terminal VM witness

This is a prospective implementation/qualification addition, not a biological
assay or change to its endpoints. Final launch preregistration remains unsealed.
The existing `SM-B003-ADMISSION-2` row schema is unchanged.

An enabled admission observer also emits `vm_end007.csv`, exclusively created,
flushed and closed before admission END. It contains one ID-sorted row per live
molecule: tick, identity, role, partner, eligibility, coordinates, then all four
head toggles and both offsets for each head. Only active actors have meaningful
head storage: passive/unbound head fields are blank and are never read natively.

The independent replay initializes heads from independently computed binding
alignment and applies subsequent zero-mutation opcodes. It must compare its full
terminal active-head state, roles, partners, eligibility and grid coordinates
with this witness. The witness must never initialize or correct the replay state.
This closes a terminal-observation gap: a head corruption not subsequently used
by a DISPATCH or proposal would otherwise be invisible in the old streams.

Disabled execution and observation-off execution do not create this file. Healthy
parity comparisons exclude exactly the two new admission-observer outputs,
`admission_events007.csv` and `vm_end007.csv`; inherited scientific CSVs and the
complete final RNG state still must match. Any witness open/write/flush/close
failure is fatal, with no transaction rollback or scientific retry. Missing,
extra, reordered or inconsistent terminal rows fail independent replay.

This additive witness must be included in source provenance, portable export,
qualification, output inventories and final launch eligibility. It does not
relax the independently reconstructed nonempty-proposal bijection, full material
reconciliation, lifecycle joins, replacement-only ancestry, or unseen-seed audit.
