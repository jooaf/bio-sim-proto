# Stage 3 energy-ledger liveness decision

## Decision

**GO at total uniform influx 1024 energy/tick.** It was the lowest—and only—candidate satisfying every frozen mechanics criterion.

At influx 1024:

- 3/3 runs feasible, exactly matter-conserved, and invariant-clean;
- maximum relative energy-balance error `1.721e-11`, well below `1e-9`;
- median late active-interaction fraction `1.000`;
- median late successful writes `159,998`;
- median late occupancy `0.771`;
- median final mean tape energy `4.949` of capacity 10;
- median cumulative dissipated fraction `0.984`;
- starvation deaths zero.

## Rejected candidates

Influxes 64 and 256 failed only the preregistered dissipated-fraction upper bound: medians were `0.9964` and `0.9954`, above `0.99`. They remained numerically conserved and mechanically active, but are ineligible and will not be rescued by changing the frozen rule.

## Supported claim

The simulator now has an explicit, numerically closed energy ledger with external influx, conservative toroidal diffusion, local absorption, execution expenditure, decay, death dissipation, starvation state, and energy-aware birth transactions. The ledger coexists with exact per-byte matter conservation.

## Limits

The uniform field does not create differentiated producer/consumer access, trophic levels, predation, or adaptive fitness. This pilot selected accounting and liveness only. It is not evidence of ecological organization.

## Next gate

At the selected operating point, test whether a fixed parent energy requirement causally constrains otherwise identical scheduled births. The comparison must be preregistered and retain an energy-free-cost positive control. Lineage and organization outcomes remain outside energy-parameter selection.
