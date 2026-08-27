# Neural SIMD performance

## Scope

The native kernel now has an opt-in `simd-neural` Cargo feature. On AArch64 it uses explicit 128-bit NEON fused multiply-add instructions for the fixed 8-, 16-, and 28-element neural dot products. Other architectures retain the scalar implementation.

The machine-local installer enables the feature by default:

```nu
nu rust/install_release.nu
```

Use the exact historical scalar floating-point path when reproducing an older recurrent run:

```nu
nu rust/install_release.nu --scalar-neural
```

The release profile still uses `opt-level=3`, fat LTO, one codegen unit, and `-C target-cpu=native`.

## Benchmark method

Machine: Apple M3 Max, AArch64; Rust 1.95.0 / LLVM 22.1.2.

The ignored Rust release microbenchmark executes 200,000 decisions and 6.6 million candidate scores:

```nu
cd rust
with-env { RUSTFLAGS: "-C target-cpu=native" } {
    cargo test --release neural_kernels_release_microbenchmark -- --ignored --nocapture
    cargo test --release --features simd-neural neural_kernels_release_microbenchmark -- --ignored --nocapture
}
```

The end-to-end benchmark used five machine-local runs per treatment with seed 7, 1,200 founders, 50 warm-up ticks, and 300 measured ticks.

## Results

### Isolated kernels

| kernel | original scalar | cached scalar | cached NEON | NEON vs original |
|---|---:|---:|---:|---:|
| linear candidate scoring | 18.0 ns/candidate | 10.7 ns/candidate | 3.0 ns/candidate | 6.0x |
| recurrent inference plus 33 residual scores | 389 ns/decision | 395 ns/decision | 186 ns/decision | 2.1x |

Caching computes the observation-dependent linear score once per intent kind instead of once per candidate. The scalar path retains the historical accumulation order and digest.

### Complete kernel

| behavior model | original mean ticks/s | NEON + cached mean ticks/s | change |
|---|---:|---:|---:|
| linear intent V2 | 327.8 | 333.8 | +1.8% |
| recurrent intent V2 | 314.5 | 323.7 | +2.9% |

The small whole-kernel gain despite large arithmetic speedups confirms that perception, candidate construction, spatial lookup, and action commitment dominate decision time.

## Numerical and replay contract

- Scalar cached execution preserves the established 300-tick digests:
  - linear V2: `16913091282173780927`
  - recurrent V2: `4397587197909303995`
- NEON linear V2 produced the same ecological digest in the measured gate because candidate choices did not change.
- NEON recurrent V2 deterministically produced digest `13674014292524321279`. Fused and reassociated floating-point accumulation changes low bits in recurrent state, although the gate retained the same final population (`962`) and passed matter and energy audits.
- Repeated runs of each build are deterministic. A SIMD build must not be mixed with a scalar build inside one experimental block.
- Unit tests compare optimized and scalar neural scores within `2e-5`; full deterministic and conservation tests remain authoritative.

## Decision

Enable NEON for machine-local optimized builds because it gives a repeatable 2–3% complete-kernel improvement and much larger isolated-kernel headroom. Keep `--scalar-neural` as the explicit compatibility mode for old recurrent trajectories. Do not add SIMD to heat diffusion yet: measured heat diffusion was about 2% of the representative 14k-organism profile, so its maximum normal-workload payoff is too small without a field-heavy benchmark requirement.
