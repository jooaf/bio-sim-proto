# SM-L001 native Stringmol reproduction and lineage identity

## Decision

**PASS.** Observation isolation, deterministic repeat, all 20 integrity checks,
the joint host gate, and the inert negative control passed.

- Joint host criteria passed: **10/10 seeds** (required 8/10).
- Host successful births: **3,730–5,193** per run (required at least 100).
- Host maximum two-parent lineage depth: **18–70** (required at least 2).
- Host final strict non-initial descendants: **1,183–1,596**.
- Host final descendant fraction: **0.98996–0.99750** (required at least 0.5).
- Inert successful births: **0 in all 10 runs**.
- Inert maximum lineage depth: **0 in all 10 runs**.
- Integrity or process failures: **0/20**.

## Host outcomes

| Seed | Births | Two-parent depth | Passive depth | Final population | Final descendants | Descendant fraction | Passive-sequence match |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 202620000 | 4,084 | 30 | 17 | 1,538 | 1,525 | 0.99155 | 0.85872 |
| 202620001 | 4,233 | 20 | 17 | 1,600 | 1,584 | 0.99000 | 0.85637 |
| 202620002 | 4,158 | 18 | 14 | 1,600 | 1,586 | 0.99125 | 0.90404 |
| 202620003 | 4,285 | 27 | 17 | 1,600 | 1,596 | 0.99750 | 0.89218 |
| 202620004 | 3,730 | 29 | 16 | 1,195 | 1,183 | 0.98996 | 0.84290 |
| 202620005 | 4,676 | 44 | 21 | 1,570 | 1,557 | 0.99172 | 0.70787 |
| 202620006 | 4,258 | 28 | 17 | 1,600 | 1,586 | 0.99125 | 0.87506 |
| 202620007 | 4,468 | 43 | 23 | 1,596 | 1,586 | 0.99373 | 0.76007 |
| 202620008 | 5,193 | 70 | 27 | 1,373 | 1,360 | 0.99053 | 0.47872 |
| 202620009 | 4,398 | 28 | 18 | 1,599 | 1,592 | 0.99562 | 0.83038 |

Passive-sequence mismatch is descriptive and is not interpreted as mutation,
because cleavage can target either molecule and event-time copying context can
differ.

## Inert outcomes

Every one-symbol `B` run recorded zero successful cleavage births, zero lineage
depth, and zero non-initial descendants. Final populations were 33–50, reflecting
decay of initial molecules rather than reproduction.

## Integrity and isolation

The patch-0001 baseline and patch-0001+0002 observer binary produced byte-identical
shared outputs with observation disabled. Enabling observation added only the two
declared CSV files and did not alter stdout, stderr, RNG state, population,
species, configuration, or image artifacts. The enabled repeat was byte-identical.
Both fresh builds passed 79 upstream assertions in 15 test cases.

All individual IDs, event-time parent identities and labels, acyclic parent DAGs,
snapshot ordering, occupied cells, species counts, END bounds, source/build/config
pins, and complete post-run inventories verified.

## Interpretation

Pinned Spatial Stringmol now has a validated native positive control for explicit
successful cleavage birth and persistent multigenerational individual lineage,
plus a source-grounded noncopying negative control. This resolves the identity
ambiguity that blocked further BFF work.

The result is seeded and unconserved. It does not establish spontaneous origin,
conserved reproduction, energetic closure, heredity fidelity, adaptation,
self-maintenance, ecology, or organisms. Per the frozen ladder, the next eligible
step is a separately preregistered Stringmol conservation-boundary design.
