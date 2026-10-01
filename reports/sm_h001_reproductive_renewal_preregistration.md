# SM-H001 descendant reproductive-renewal gate

**Frozen before implementation:** 2026-09-30

## Question and claim boundary

SM-L001–SM-C002 established native birth, ancestry, exact matter conservation,
and causal decay-fed reproduction. Their descendant counts include every
noninitial individual, including products that may never reproduce. SM-H001 asks:

**Do native descendants themselves become the material source of later
population-increasing births while retaining the sequence they inherited?**

A pass establishes finite-horizon operational reproductive renewal and inherited
sequence continuity in the pinned seeded host. It does not establish that sequence
is causally necessary for function, mutation–selection heredity, adaptation,
indefinite persistence, metabolism, self-maintenance, ecology, or organisms. A
causal perturbation/transplant gate requires a separate preregistration.

## Calibration disclosure

SM-C002 is calibration only and cannot count toward confirmation. A retrospective
source-edge replay of its 20 recycle runs found:

- 11–47 noninitial descendants later served as source parent;
- 66–263 births were sourced by noninitial descendants;
- source-lineage depth was 2–4;
- 5–25 descendants born at/after tick 2,500 later served as source;
- renewing descendants had birth lengths 61–65; and
- minimum positional inherited-byte retention at first source birth was 0.984375.

These observations motivated the prospective thresholds below. SM-H001 uses
unseen seeds and a committed analyzer; no SM-C002 outcome is pooled with it.

## Pinned mechanics

- upstream commit `15dad84da126a4f887ba945c23a13e89e827f067`;
- patches 0001–0004 unchanged in order;
- conservation enabled, histogram amount 0, decay destination recycle;
- canonical 140-host positions, 40×40 grid, global interaction and placement,
  mutation 0.0002, decay 0.0005, 5,000 steps, report interval 100;
- lineage and version-2 conservation/material-journal observation enabled;
- exact molecular + pool + waste conservation and all SM-C002 safety, replay,
  launch, seed-audit, and no-resume rules inherited unchanged.

No simulator patch or chemistry change is permitted. SM-H001 adds only a separate
analysis/workflow layer and synthetic analyzer fixtures.

## Frozen source-birth representation

Derive source edges independently from stable `material_events002.csv` changes;
do not use active/passive ancestry labels to choose the source.

A **productive source birth** is a `CLEAVE/PLACED` event satisfying all of:

1. exactly one new nonempty child ID appears;
2. extant population increases by exactly one across the stable event;
3. exactly one preexisting participant loses a contiguous visible suffix and
   remains extant with a nonempty buffer; this is the source parent;
4. the child receives exactly that suffix in order starting at offset zero;
5. no source byte is simultaneously credited to pool/waste and no unexplained
   byte change occurs; and
6. all event and global per-symbol conservation checks pass.

A whole-parent transfer that destroys the source is not productive source birth,
even if native lineage logs it as BIRTH. Failed placement and no-change cleavage
are not births.

Construct the **qualifying source lineage** conservatively. Initial IDs have
source depth zero. Add `source parent -> child` only when a productive source
birth's parent is initial or already has defined qualifying depth; child depth is
`source_depth(parent) + 1`.

Native whole-parent transfers and any other nonproductive BIRTH still create valid
noninitial IDs, but those IDs have undefined qualifying depth. If one later acts
as source in an otherwise productive birth, report an **orphan-source productive
birth** and leave its child outside the qualifying source lineage. Do not count
either ID toward renewal, serial source births, late renewal, retention, or depth.
This exclusion propagates until an initial/qualifying parent is the source of a
new productive edge. Valid transfer-created IDs are never integrity failures or
silently assigned depth zero. Report their subsequent active/passive/source
participation separately. ID reuse, cycles, birth before parent, conflicting
source edges, or inconsistent origin classification are integrity failures.

A **renewing descendant** is a qualifying source-lineage child that later serves
as source parent of another productive source birth. A **serial source birth** is
a productive source birth whose source parent has qualifying depth at least one.
A **late renewing descendant** was born at `timestep >= 2500` and later becomes a
productive source parent before actual END.

For each renewing descendant, freeze its complete productive-birth buffer. Immediately before
its first productive source birth, compute positional inherited-byte retention:

`retained = count(offset where birth byte is non-NUL and current byte equals birth byte) / birth non-NUL byte count`.

Birth length is the number of non-NUL bytes in the complete birth buffer. A
**retained late renewal** is late, has birth length at least 32, and retention at
least 0.90. Retention is sequence continuity, not causal proof of function.

## Independent reconstruction

The analyzer starts from the tick-0 full-buffer map and replays every material
event in total order. It must independently reconstruct buffers, lifecycle,
population, source/suffix mapping, pools, waste, counters, scheduled checkpoints,
and actual END. Cross-check native lineage BIRTH child/active/passive IDs,
checkpoint visible sequences, END identity history/population, and all output
inventories.

Report total native births, productive source births, whole-parent transfers,
orphan-source productive births and their later participation, failed/no-change
cleavages, renewing descendants, serial source births, qualifying source-lineage
depth, early/late renewal, birth-length and retention distributions,
active/passive role of each inferred source, descendant survival, and all inherited
SM-C002 material/lineage diagnostics.

After extinction, do not fabricate checkpoints or renewal; unexecuted future
contributions are zero.

## Mechanics and analysis gates

Before unseen execution:

1. rebuild fresh patch-0004 baseline and rerun upstream, lineage, conservation,
   decay-routing, compatibility, isolation, deterministic, directed, pytest, and
   mypy gates;
2. prove the new workflow produces no simulator/output change relative to the
   inherited SM-C002 workflow for a development host run;
3. synthetic fixtures cover active/passive source, offset-zero whole-parent
   transfer exclusion, partial suffix with source survival, hidden tails, failed
   placement, no-change cleavage, source death, ID reuse/cycles, noncontiguous or
   reordered child material, pool double credit, source depth, late boundary,
   extinction, and positional retention at 0, 0.90, and 1.0;
4. independently replay at least one development run and require exact agreement
   with native and material observations; and
5. freeze canonical serialization, hashes, complete filename sets, and launch
   remote/seed checks.

Any mismatch stops before unseen seeds. Analyzer/observer defects may be repaired
without changing definitions; representation, thresholds, matrix, or chemistry
changes require a new experiment ID.

## Frozen scientific matrix

Verify no prior use, then seal:

- **20 host runs:** seeds `202623000`–`202623019`, canonical host-only setup;
- **10 inert controls:** seeds `202623000`–`202623009`, 140 one-symbol `B`
  molecules in the otherwise identical conserved recycle setup.

Use at most six concurrent processes. All 30 runs remain in their denominators.
No resume, selective retry, replacement seed, or horizon extension is allowed.
Commit and push the protocol and implementation before launch; directly verify
`origin/main` and repeat the held-out seed audit in the launch seal.

## Integrity gate

All 30 runs must pass process, build/input/output inventory, exact event replay,
per-symbol molecular/pool/waste conservation, nonnegative ledgers, loader,
lineage-DAG, source-lineage, suffix-transfer, snapshot, identity-history, counter,
schema, alphabet, and bounds checks. Every run must record zero boundary errors.
Integrity failure makes the matrix unevaluable, not a biological failure.

## Acceptance gate

SM-H001 passes only if all integrity/mechanics gates pass, all ten inert controls
have zero native births, zero productive source births, zero renewing descendants,
and source depth zero, and the **same at least 16 of 20 host runs** satisfy all:

1. at least 100 productive source births;
2. at least 10 renewing descendants;
3. at least 50 serial source births;
4. maximum source-lineage depth at least 2;
5. at least 5 late renewing descendants; and
6. at least 5 retained late renewals.

Ties/failures remain non-passes. Report all run-level components. The frozen
16-of-20 fair-coin reference tail is `6196/1048576 = 0.005908966064453125`,
descriptive and not a p-value for the composite gate.

## Decision ladder

All scientific branches require every mechanics/integrity gate and all inert-
control criteria. Define `renewal_core` as the same at least 16/20 host runs each
satisfying requirements 1–5. Define `full_support` as the same at least 16/20 host
runs each satisfying requirements 1–6.

Apply in order:

- **Pass (`full_support`):** operational descendant reproductive renewal with
  inherited sequence continuity is supported; preregister a causal sequence
  perturbation/transplant gate before claiming functional heredity.
- **Renewal without retention (`renewal_core` true, `full_support` false):** report
  operational source renewal only. Inherited sequence continuity is unsupported;
  do not proceed to heredity claims.
- **Valid failure (`renewal_core` false):** report active/passive participation,
  orphan-source events, and every gate component only as diagnostics; make no
  transmission claim and stop the heredity branch.
- **Unevaluable:** repair only process/analyzer/artifact defects and rerun the full
  unchanged matrix; semantics or chemistry changes require a new ID.
