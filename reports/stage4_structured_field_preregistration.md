# Stage 4 structured energy-field scale preregistration

**Frozen before execution:** 2026-09-10

## Question and scope

Does normalized spatial structure in external influx create persistent local
energy-access niches when uptake is execution-mediated? This remains a
mechanics-only field-selection campaign. Lineage, reproduction, mortality,
organization, and fitness endpoints are prohibited from field selection.

## Frozen field generator

Uniform influx retains the existing exactly equal per-cell addition. A static
`patches` profile is generated without consuming simulation RNG:

1. initialize an independent PCG64 generator with `run_seed XOR 0x534634`;
2. draw one 16×16 standard-normal white-noise field;
3. Fourier-filter it by
   `exp(-0.5 * (2*pi*correlation_length)^2 * (kx^2 + ky^2))` using toroidal
   frequencies in cycles per cell;
4. standardize the filtered field to zero mean and unit variance;
5. exponentiate with frozen log-contrast 1.0; and
6. normalize positive weights to sum exactly 256.

At each tick total influx is distributed in proportion to those fixed weights.
The generator and each realized profile are saved with the run. Diffusion and
all ledger operations remain unchanged. Uniform mode must preserve prior
trajectories and consume no new RNG.

## Campaign

Use four field conditions:

- uniform;
- patches with correlation length 0.5 cells;
- patches with correlation length 2 cells;
- patches with correlation length 8 cells.

The patch scales span below, near, and above the radius-1 interaction scale. Use
five matched seeds `202609230`–`202609234`, 1,000 ticks, a 16×16 lattice at 50%
fixed occupancy, and all occupied tapes seeded with
`3a 00 00 00 00 00 00 00`. Active uptake is enabled; passive absorption,
mutation, writes, dissolution, reseeding, and reproduction are disabled. Use 128
local interactions per tick, 16 instruction reads, total influx 16, uptake amount
1, tape capacity 10, instruction cost 0.01, diffusion 0.02, decay 0.01, and
`min_to_interact = 0`.

Aggregate reached uptake executions and gross transfer by active tape cell in
each tick's uptake event. Log every tape every 10 ticks. Save the exact influx
weight profile for audit.

## Frozen metrics

For each run calculate:

- Moran's I over the cumulative per-cell gross uptake map using toroidal
  four-neighbor adjacency;
- Moran's I over final tape-held energy at occupied cells, with absent cells
  excluded through edge-wise occupied-neighbor evaluation;
- coefficient of variation of cumulative uptake across occupied cells;
- profile Moran's I and coefficient of variation;
- activity, occupancy, and maximum relative energy residual.

A constant map has Moran's I and coefficient of variation defined as zero.

The primary endpoint is, for each seed, mean patch-condition cumulative-uptake
Moran's I minus uniform Moran's I. Report all five paired differences and an
exact one-sided sign test.

## Gate

Structured energy niches are supported only if:

- the primary difference is positive in 5/5 seeds with exact one-sided
  `p <= 0.05`;
- at least two of three patch scales have median uptake Moran's I above uniform;
- mean-patch minus uniform uptake coefficient of variation is positive in 5/5
  seeds;
- mean-patch minus uniform final tape-energy Moran's I is positive in at least
  4/5 seeds;
- every patch profile is finite, strictly positive, sums to 256 within `1e-12`,
  and has positive Moran's I and coefficient of variation;
- all 20 runs complete with 128 tapes, nonzero interactions and uptake, unchanged
  tape bytes, and zero invariant failures; and
- maximum relative energy error is at most `1e-9` in every run.

## Interpretation and follow-up

A pass selects no single correlation length; it supports only the class of
static normalized patch fields and permits a separately preregistered causal
consequence experiment. A failure retains differentiated uptake under uniform
supply and stops spatial-niche claims. Do not alter the generator, scales,
contrast, seeds, field physics, metrics, thresholds, or horizon after execution
starts.
