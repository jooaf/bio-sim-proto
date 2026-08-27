# Latest seasonal biodeposit run analysis

## Run

```text
runs/20260825T153148.201047Z-seed24-rust-gui-b7c342d1/
```

This is the newest interpretable long native-GUI record. It used recording
schema 3, had no live configuration changes, enabled random seasons and
physical biodeposits, and left cellular affordances disabled.

Configuration highlights:

- 300 founders from 10 archetypes;
- legacy macro behavior;
- mutation multiplier 2.1;
- 700 initial deposits;
- biodeposits enabled;
- seasons enabled at strength 0.75 with approximately 4,450-tick periods.

## Results

At metric tick 39,981:

- population: 224,774;
- living species: 21, peak 21;
- dominant species share: 35.8%;
- births/death in the final 20%: 1.150;
- generated chunks: 7,407;
- biodeposit positions: 1,474,930;
- median late throughput: 1.21 ticks/s.

Reproduction was attempted 73.6 million times but succeeded only 2.1% of the
time. Resource blocks accounted for 93.2% of attempts: 55.6 million energy
blocks and 13.0 million body-matter blocks. This is not evidence that
reproduction should be made easier: successful births already exceeded deaths
and global abundance was increasing.

## Frontier expansion, not rising local density

Global population rose 227% during the final 20% of ticks, while generated
chunks rose 246%. Population per generated chunk changed from 32.10 to 30.35,
a **5.5% decline**.

The large global trajectory is therefore best interpreted as an expanding
range at approximately stable occupied-world density, not a uniformly
increasing local carrying capacity. An infinite procedurally generated world
has no finite global population equilibrium while a viable frontier continues
to spread.

This argues against adding a population cap, lowering reproduction globally,
or reducing resource recharge based on this run alone. Those interventions
would target global abundance rather than the observed spatial mechanism.

## Seasons and diversity

Eight season transitions were recorded. Resource multipliers ranged from 0.673
to 1.140 and decomposition multipliers from 0.907 to 1.218. Population remained
small through the harsh early profiles and expanded after the later richer
profiles, but one seed and one realized schedule cannot separate seasonal
causality from lineage and frontier effects.

Diversity did not collapse: living species increased from 10 to 21 and the
largest species held 35.8% of the final population. A replicated paired matrix
(seasons disabled, strength zero, and strength 0.75) is required before
changing seasonal physics.

## Conservation finding

Integer matter was exact. The old energy audit failed at an absolute error of
`1.153e-5`, but the run accounted for `1.327e7` energy units. Relative drift
was only `8.69e-13`.

The previous tolerance scaled only with the small founder-region initial
energy (`2.77e4`) even though procedural frontier generation increased the
accounted energy scale by almost 480x. Other 150k–465k-organism runs show the
same scale-dependent false failure.

The Rust audit now retains its existing absolute and initial-energy floors and
adds a stricter `5e-12` bound relative to total accounted
(initial + generated) energy. New audits also expose the accounting scale and
relative error. This fixes high-scale false negatives without changing any
simulation dynamics or conservation transfers.

## Changes made

1. Generated-energy-aware floating energy tolerance in the Rust audit.
2. Audit output now records accounting scale and relative error.
3. Native reports show population per generated chunk and its late change.
4. Reports distinguish stable-density frontier expansion from rising-density
   population growth.

## Recommendation

Do not change ecological defaults from this result. Next run a paired,
headless, multi-seed seasonal experiment at a bounded tick budget with no live
updates. Analyze per-season per-capita growth, species turnover, recovery lag,
and population per generated chunk. Profile decision and deposit phases at
matched 10k, 50k, and 200k populations before choosing the next performance
implementation.
