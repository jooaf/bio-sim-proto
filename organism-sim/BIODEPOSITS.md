# Physical biodeposits v1

`physical-biodeposits-v1` is an opt-in Rust-kernel substrate for spatial structure left by accumulated biological matter.

It does not assign habitat, shelter, hiding, or fitness labels. Those outcomes can only follow from generic physical interactions.

## Enable

```nu
uv run organism-sim-headless \
  --engine rust \
  --ticks 10000 \
  --biodeposits
```

The same setting can be enabled in the GUI with the **Biodeposits** reset slider. GUI settings are automatically written to `runs/gui_settings.json`, including the seed, and can be reused headlessly:

```nu
uv run organism-sim-headless \
  --engine rust \
  --config runs/gui_settings.json \
  --ticks 10000
```

## Physical law

When an organism dies outside successful internalization:

1. Its body, gut, waste, and internal-guest matter return to ordinary molecule deposits distributed across its final physical footprint.
2. The molecular mass increases a scalar structural-density field across the same footprint.
3. The density is metadata about the packing/arrangement of existing matter; it does not create matter or energy.
4. Density decays as packed material loses spatial organization. The molecules remain in the ordinary deposit.
5. Eating molecules at that position erodes density by the mass removed.

Uniform decay uses a global scale factor, so each tick is O(1) rather than scanning every accumulated site. A rare renormalization removes numerically negligible entries after extreme run lengths.

Repeated deaths at one position therefore accumulate structure while isolated deaths remain relatively weak.

## Generic consequences

- **Movement:** entering packed material multiplies movement energy demand by a logarithmic function of density. Sufficiently dense fields can become effectively impassable for organisms with inadequate energy or movement efficiency.
- **Food:** the original biological molecules remain available through the normal chemistry and digestion system.
- **Physical cover:** packed matter reduces transmitted attack damage.
- **Concealment:** attacks can fail with a density-dependent probability after their energy has been committed.
- **Living mass:** nearby living organisms are also physical material. Occupancy already blocks movement, and neighboring body mass contributes cover around a target. No stationary-organism or habitat class is introduced.

## Configuration

| field | default | meaning |
|---|---:|---|
| `biodeposits_enabled` | `false` | enable the substrate |
| `biodeposit_decay_rate` | `0.001` | per-tick loss of packed structure, not matter |
| `biodeposit_movement_resistance` | `0.25` | movement-work response to density |
| `biodeposit_cover_strength` | `0.35` | attack-damage attenuation |
| `biodeposit_concealment` | `0.10` | attack-failure response to cover |

All coefficients are generic environmental physics. They never inspect species identity, genomes, roles, or population success.

## Observation and recording

The native GUI renders density in brown beneath ordinary molecule markers. Metrics expose only:

- `biodeposit_positions`
- `biodeposit_total_density`
- `biodeposit_max_density`

Rust headless `final_state.npz` includes `biodeposits_x`, `biodeposits_y`, and `biodeposits_density`.

## Performance gate

At 1,200 founders (50 warm-up + 300 measured ticks, seed 7), three disabled runs averaged 327.9 ticks/s. Five enabled runs averaged 300.2 ticks/s while ending with 1,182 rather than 1,136 organisms. Raw tick throughput was 8.4% lower; population-normalized throughput was approximately 4.7% lower. Enabled and disabled trajectories diverge, so this is not a pure scheduler-overhead comparison. A paired 1,200-founder/750-tick SDL run measured the GUI at 104.1% of its matched headless run, indicating no measurable rendering bottleneck from the density overlay at that scale.

## Conservation and limitations

- Structural density is not a second inventory and is excluded from matter/energy totals.
- All edible matter remains in the audited molecule inventory.
- Density erosion and decay alter arrangement only.
- V1 stores one scalar packing density per position rather than explicit geometry, porosity, or molecule-specific structural layers.
- The Python reference kernel rejects this Rust-only feature rather than silently approximating it.
