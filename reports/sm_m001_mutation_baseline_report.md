# SM-M001 native-versus-zero mutation baseline report

**Run date:** 2026-10-03  
**Decision:** **BOTH VIABLE; REALIZED-DIVERGENCE GATE NOT DETECTED**  
**Continuation:** birth-boundary factorial eligible

## Integrity

All 40 sealed runs completed once and reached tick 5,000. Every process,
inventory, complete material-event replay, exact per-symbol conservation,
nonnegative-ledger, source-lineage, suffix-transfer, snapshot, identity, schema,
alphabet, bounds, and END-state check passed. Independent review replayed all raw
runs, independently recomputed sequence abundance and Hill q=1, and reproduced the
complete decision.

## Renewal viability

Both arms independently passed the frozen 16/20 renewal-with-continuity gate:

| Arm | Renewal core | Renewal with continuity | Viable |
|---|---:|---:|---|
| NATIVE (`MUTATE 0.0002`) | 18/20 | 18/20 | yes |
| ZERO (`MUTATE 0`) | 18/20 | 18/20 | yes |

There were four discordant pairs: NATIVE-only passes at seeds `202626001` and
`202626012`, and ZERO-only passes at `202626008` and `202626013`. This balanced
threshold discordance does not establish equivalent performance.

Across 20 runs, NATIVE recorded 11,969 productive source births, 452 renewing
descendants, 2,386 serial source births, and 219 late retained renewals. ZERO
recorded 11,973, 419, 2,197, and 225 respectively. Paired median NATIVE-minus-ZERO
differences were −7 productive births, +1 renewing descendant, +9.5 serial births,
and −1 late renewal.

ZERO's viability demonstrates that native mutation is not required for robust
canonical reproductive renewal under these conditions.

## Realized sequence outcomes

The preregistered divergence conjunction required NATIVE to have both more unique
productive-birth sequences and a greater noncanonical productive-birth fraction
in the same at least 16/20 pairs. It held in only **7/20**, so the registered
realized-divergence effect was not detected.

Directional diagnostics were mixed:

- productive unique sequences / Hill q=0: NATIVE greater in 16 pairs, tied in 1,
  ZERO greater in 3; median difference +7;
- productive Hill q=1: NATIVE greater in 15, ZERO greater in 5; median difference
  +0.485;
- productive noncanonical fraction: NATIVE greater in 10 and ZERO greater in 10;
  median difference +0.000285;
- renewing noncanonical fraction: NATIVE greater in 14 and tied in 6; median
  difference +0.0822;
- median first-source retention tied in all 20 pairs; exact-retention fraction
  tied in 17 and favored ZERO in 3.

Thus native mutation increased some diversity summaries directionally, especially
unique sequence richness, but did not pass the frozen joint realized-divergence
gate. Substantial realized sequence diversity also arose at `MUTATE 0`, so it
cannot be attributed entirely to random mutation; native copying, partial
construction, cleavage, and lineage dynamics can generate varied products.

## Bounded conclusion

Canonical conserved-recycle Stringmol renewal remains robust with mutation
disabled. This establishes renewal without native mutation, not equivalence
between mutation settings. The preregistered evidence does not establish a broad
mutation-caused increase in realized productive-birth divergence, beneficial
variation, selection, or adaptation.

Because both arms met the operational viability rule, a separately preregistered
birth-boundary factorial separating offspring separation, parent preservation,
and admission is eligible. It cannot rescue the closed H003 panel-heredity gate.

Raw campaign:
`/home/jojo/bio-sim-results/bazzite/sm_m001_mutation_baseline/bazzite.attlocal.net/prepared`

Full analysis and publication metadata are in the sibling `analysis/` directory.
